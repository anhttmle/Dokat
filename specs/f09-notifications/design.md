# F09 — Notification System — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F03 / F05 / F09 / F10)

F09 là feature **infrastructure** thêm hai luồng push notification:
(1) **new-photo push** trigger ngay sau khi `POST /posts` commit
recipients, và (2) **daily reminder** gửi theo lịch YAML do App Owner
cấu hình.

Ranh giới với các feature lân cận:

- **F03 — Social Graph (đã xong):** `users.fcm_token` và
  `NotificationService` (stub) đã có. F09 **mở rộng**
  `notification_service.py` thêm `send_new_photo()` và
  `send_reminder()` — không tạo file mới (DL-F09-01). `PUT
  /users/fcm-token` (F03) được **mở rộng** để nhận thêm field
  `timezone` (IANA string) — backward-compatible, timezone là
  optional (DL-F09-02).
- **F05 — Send Photo (đã xong):** `post_service.create_post` đã có
  comment `# F09 hook` sau commit recipients (DL-F05-05). F09
  **điền** hook này bằng lệnh gọi
  `notification_service.send_new_photo()` — không sửa logic tạo
  post.
- **F10 — Settings (đã xong):** Block là **silent** (FR-5,
  DL-F10-03): new-photo push **không** gửi đến recipient bị block.
  `notification_service.send_new_photo()` kiểm tra `blocked_users`
  trước khi gọi FCM. Logout xoá `fcm_token` (DL-F10-07) — F09
  **không** cần xử lý thêm.
- **F10 — Settings UI:** Toggle reminder trong **F09** thêm vào
  `SettingsScreen` của F10 (DL-F09-03) — F09 là owner của backend
  preferences API và client preference toggle rows.

> Reminder schedule được khai báo trong
> `backend/config/reminders.yaml`; thay đổi lịch yêu cầu redeploy.
> Người dùng **không** tự cài giờ — chỉ bật/tắt loại reminder.

---

## 1. Architecture Overview

```
┌────────────────────────────── React Native Client ──────────────────────────┐
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         SettingsScreen (F10, extended)               │   │
│  │  NotificationPreferenceSection                                        │   │
│  │    toggle per ReminderType (feeding/sleeping/bathing/playing)         │   │
│  └────────────────────────────────┬─────────────────────────────────────┘   │
│                                   │ PUT /notifications/preferences/{type}    │
│  ┌────────────────────────────────▼─────────────────────────────────────┐   │
│  │                         NotificationService (client)                  │   │
│  │  registerToken(fcmToken, timezone)  → PUT /users/fcm-token            │   │
│  │  setPreference(type, enabled)       → PUT /notifications/preferences/{type} │
│  │  getPreferences()                   → GET /notifications/preferences  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┬────────────────────────┘
                                                       ▼  HTTPS + Firebase ID token
┌────────────────────────────── FastAPI Backend ──────────────────────────────┐
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  post_service.create_post                                               │ │
│  │    ... commit post + recipients ...                                     │ │
│  │    [F09 hook] notification_service.send_new_photo(post, recipients)    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────────────┐   ┌────────────────────────────────────────────┐  │
│  │  routers/            │   │  services/                                  │  │
│  │  notifications.py    │   │  notification_service.py (extended)         │  │
│  │  GET  /notifications/│   │    send_new_photo(post, recipients, db)    │  │
│  │    preferences       │   │    send_reminder(users, reminder_type, db) │  │
│  │  PUT  /notifications/│   │    _is_blocked(sender, recipient, db)      │  │
│  │    preferences/{type}│   │                                            │  │
│  └──────────┬───────────┘   └──────────────────────┬─────────────────────┘  │
│             │                                       │                         │
│  ┌──────────▼───────────────────────────────────────▼─────────────────────┐  │
│  │  services/notification_pref_service.py                                  │  │
│  │    get_preferences(user_id) → dict[ReminderType, bool]                  │  │
│  │    set_preference(user_id, reminder_type, enabled)                      │  │
│  └───────────────────────────────┬─────────────────────────────────────────┘  │
│                                  │                                              │
│  ┌───────────────────────────────▼──────────────────────────────────────────┐  │
│  │  reminder_scheduler.py  (APScheduler, chạy trong startup event)          │  │
│  │    job runs every minute → load reminders.yaml → per-species per-type    │  │
│  │    → query users (has pet + fcm_token + enabled + timezone matches)      │  │
│  │    → notification_service.send_reminder(users, type, db)                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  PostgreSQL                       Firebase FCM (Admin SDK)                      │
│  users (+ timezone)               push to device tokens                         │
│  notification_preferences         (best-effort, best-of-1 per recipient)        │
│  blocked_users (F10)                                                             │
│  pet_profiles   (F02)                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng — New-photo push (AC-F09-1, AC-F09-2)

1. `post_service.create_post` INSERT `posts` + `post_recipients`,
   gọi `db.commit()`.
2. Sau commit, `create_post` gọi
   `notification_service.send_new_photo(post=post, db=db)`.
3. `send_new_photo` đọc danh sách recipients từ `post_recipients`
   (lọc `post_id = post.id`).
4. Với mỗi recipient:
   - Bỏ qua nếu `_is_blocked(sender=post.user_id, recipient, db)` →
     True (DL-F09-04).
   - Đọc `user.fcm_token`; bỏ qua nếu NULL.
   - Gọi Firebase Admin SDK `messaging.send()`:
     - `title`: tên sender (display_name hoặc "Ai đó")
     - `body`: "đã gửi ảnh thú cưng mới cho bạn"
     - `image`: `post.cdn_url` (thumbnail)
     - `data`: `{ "post_id": "<uuid>", "screen": "FeedDetail" }`
       → deep link (AC-F09-2)
5. Tất cả lỗi FCM đều catch + log WARNING, **không** raise (best-
   effort — DL-F05-05). Kết quả của `create_post` không phụ thuộc
   FCM.

### 1.2 Luồng — Daily reminder (AC-F09-3, AC-F09-4, AC-F09-6)

1. App startup: `reminder_scheduler.start()` khởi động
   `APScheduler BackgroundScheduler`.
2. Một job duy nhất chạy mỗi **1 phút** (`interval`).
3. Job tải `reminders.yaml` (cache trong bộ nhớ, reload khi
   file thay đổi hoặc startup).
4. Với mỗi entry `(species, reminder_type, hour, minute)` trong
   YAML:
   a. Lấy DB session từ `SessionLocal()`.
   b. Query users:
      ```
      users JOIN pet_profiles ON pet_profiles.user_id = users.id
      WHERE pet_profiles.species = <species>
        AND users.fcm_token IS NOT NULL
        AND users.timezone IS NOT NULL
      ```
   c. Với mỗi user: convert UTC now sang user's `timezone`; so sánh
      `local_hour == hour AND local_minute == minute`.
   d. Đọc `notification_preferences` cho user + `reminder_type`:
      không có row hoặc `enabled = True` → gửi (opt-out model,
      AC-F09-4).
   e. Gọi `notification_service.send_reminder(user, pet_name,
      reminder_type)`:
      - `title`: "Nhắc nhở thú cưng"
      - `body`: f"Đến giờ {reminder_label} cho {pet_name} rồi!"
        (AC-F09-3)
      - FCM best-effort (DL-F09-05).
5. Job đóng DB session sau mỗi run.

### 1.3 Luồng — Toggle reminder (AC-F09-5)

1. User mở SettingsScreen → thấy `NotificationPreferenceSection`
   với 4 toggle (feeding, sleeping, bathing, playing).
2. `NotificationService.getPreferences()` → `GET
   /notifications/preferences` → trả `{ feeding: true, sleeping:
   true, bathing: false, playing: true }`.
3. User tắt toggle "Tắm" → `NotificationService.setPreference(
   "bathing", false)` → `PUT /notifications/preferences/bathing`
   `{ "enabled": false }`.
4. Backend upsert `notification_preferences (user_id, reminder_type,
   enabled=false)` → **204**.
5. Kể từ lần job chạy tiếp theo, user không còn nhận reminder
   "bathing" (AC-F09-5).

---

## 2. Data Models / Schema

### 2.1 Mở rộng bảng `users` — thêm `timezone`

| Cột | Kiểu | Null | Mô tả |
|---|---|---|---|
| `timezone` | `TEXT` | YES | IANA timezone string (e.g. `"Asia/Ho_Chi_Minh"`); NULL nếu chưa cung cấp → bỏ qua reminder |

Migration: `ALTER TABLE users ADD COLUMN timezone TEXT;`

`timezone` được cập nhật cùng với `fcm_token` qua endpoint `PUT
/users/fcm-token` (F03, mở rộng backward-compatible — DL-F09-02).

### 2.2 Bảng `notification_preferences` — trạng thái opt-out

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` | |
| `user_id` | UUID | FK `users.id` ON DELETE CASCADE, NOT NULL | |
| `reminder_type` | ENUM `reminder_type` | NOT NULL | `feeding \| sleeping \| bathing \| playing` |
| `enabled` | BOOLEAN | NOT NULL, default `true` | `false` = opt-out |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

- `UNIQUE (user_id, reminder_type)` (`notif_pref_unique_pair`)
  — upsert idempotent.
- **Opt-out model:** không có row = enabled. Row chỉ tồn tại khi
  user thay đổi preference (DL-F09-06).
- Index: `idx_notif_pref_user (user_id)`.

### 2.3 Config file `backend/config/reminders.yaml`

```yaml
# Lịch reminder cho từng loại thú cưng.
# hour/minute theo múi giờ của thiết bị user (timezone-aware job).
reminders:
  dog:
    - type: feeding
      hour: 7
      minute: 0
    - type: feeding
      hour: 18
      minute: 0
    - type: sleeping
      hour: 22
      minute: 0
    - type: bathing
      hour: 10
      minute: 0
    - type: playing
      hour: 17
      minute: 0
  cat:
    - type: feeding
      hour: 7
      minute: 30
    - type: feeding
      hour: 18
      minute: 30
    - type: sleeping
      hour: 23
      minute: 0
    - type: bathing
      hour: 10
      minute: 30
    - type: playing
      hour: 16
      minute: 0
```

Thay đổi YAML → yêu cầu redeploy (Technical Constraints
requirements.md).

### 2.4 ORM Model — `NotificationPreference`

```python
# app/models/notification_pref.py
class ReminderType(enum.StrEnum):
    feeding  = "feeding"
    sleeping = "sleeping"
    bathing  = "bathing"
    playing  = "playing"

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "reminder_type",
            name="notif_pref_unique_pair",
        ),
    )
    # id, user_id, reminder_type, enabled, updated_at
```

### 2.5 Client — TypeScript types

```typescript
type ReminderType = 'feeding' | 'sleeping' | 'bathing' | 'playing';

/** Map loại reminder → trạng thái enabled. */
type NotificationPreferences = Record<ReminderType, boolean>;

/** Body gửi lên PUT /notifications/preferences/{type}. */
interface SetPreferenceBody {
  enabled: boolean;
}

/** Body gửi lên PUT /users/fcm-token (mở rộng F03). */
interface RegisterTokenBody {
  fcm_token: string;
  timezone?: string;   // IANA string; optional, backward-compat
}
```

---

## 3. API Contracts

Tất cả endpoint yêu cầu Firebase ID token (middleware hiện có).

### 3.1 `PUT /users/fcm-token` — cập nhật device token + timezone

Mở rộng endpoint F03 (backward-compatible — DL-F09-02).

**Request** (thêm field `timezone`)

```jsonc
{
  "fcm_token": "cXV4eW...",
  "timezone": "Asia/Ho_Chi_Minh"   // optional
}
```

**Response**

- **204** khi upsert thành công.
- **422** nếu `fcm_token` rỗng (như trước).
- `timezone` không hợp lệ (không trong `zoneinfo`) → **422
  `INVALID_TIMEZONE`** (DL-F09-02).
- `timezone` vắng mặt → giữ nguyên giá trị cũ (hoặc NULL nếu chưa
  có).

### 3.2 `GET /notifications/preferences` — lấy trạng thái preferences

**Response 200**

```jsonc
{
  "feeding":  true,
  "sleeping": true,
  "bathing":  true,
  "playing":  true
}
```

- Trả **tất cả 4 loại** (DL-F09-06); loại không có row → `true`
  (mặc định bật).

### 3.3 `PUT /notifications/preferences/{reminder_type}` — bật/tắt

`reminder_type` ∈ {`feeding`, `sleeping`, `bathing`, `playing`}.

**Request**

```jsonc
{ "enabled": false }
```

**Response**

- **204** khi upsert thành công (idempotent).
- **422** nếu `reminder_type` không hợp lệ.

### 3.4 Không thuộc F09

- Push notification "new friend" (F03): giữ nguyên.
- Deep link routing (`FeedDetail` screen): thuộc F06.
- Toggle UI layout trong SettingsScreen: F09 chỉ thêm
  `NotificationPreferenceSection` component; layout chính thuộc F10.

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/
├── app/
│   ├── models/
│   │   └── notification_pref.py          # NotificationPreference ORM
│   ├── schemas/
│   │   └── notification.py               # SetPreferenceRequest/Response
│   ├── services/
│   │   ├── notification_service.py       # mở rộng: send_new_photo, send_reminder
│   │   └── notification_pref_service.py  # get/set preferences (opt-out logic)
│   ├── routers/
│   │   └── notifications.py              # GET/PUT /notifications/preferences
│   └── reminder_scheduler.py             # APScheduler job setup
├── config/
│   └── reminders.yaml                    # lịch reminder do App Owner cấu hình
└── alembic/versions/
    └── *_f09_add_timezone_and_notif_prefs.py
```

| Component | Trách nhiệm |
|---|---|
| `notification_service.send_new_photo` | Đọc recipients, kiểm tra block, gọi FCM, best-effort. |
| `notification_service.send_reminder` | Gọi FCM cho một user với reminder message, best-effort. |
| `notification_pref_service` | Upsert/get preferences; opt-out logic (no row = enabled). |
| `routers/notifications.py` | Map GET/PUT preferences; xác thực `reminder_type`. |
| `reminder_scheduler.py` | `BackgroundScheduler` (APScheduler); job 1 phút; load YAML; timezone-aware. |
| Migration | Thêm `users.timezone TEXT`; tạo `notification_preferences`. |

### 4.2 Client (React Native)

```
src/
├── services/
│   └── NotificationService.ts          # registerToken, get/setPreference
├── components/
│   └── NotificationPreferenceSection.tsx  # 4 toggle rows
└── __tests__/notifications/
    ├── NotificationService.test.ts
    └── NotificationPreferenceSection.test.tsx
```

| Component | Trách nhiệm |
|---|---|
| `NotificationService.registerToken` | Gọi `PUT /users/fcm-token` với `fcm_token` + `timezone` (từ `Intl.DateTimeFormat().resolvedOptions().timeZone`). |
| `NotificationService.getPreferences` | `GET /notifications/preferences` → `NotificationPreferences`. |
| `NotificationService.setPreference` | `PUT /notifications/preferences/{type}` → `{ enabled }`. |
| `NotificationPreferenceSection` | 4 Toggle rows (feeding/sleeping/bathing/playing); gọi `setPreference` khi toggle; hiển thị label tiếng Việt. |

`NotificationPreferenceSection` được **nhúng** vào
`SettingsScreen` (F10) — F09 không tạo màn hình riêng (DL-F09-03).

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| FCM send thất bại (new-photo) | Backend | Catch + log WARNING; không ảnh hưởng 201 của `POST /posts` |
| FCM send thất bại (reminder) | Backend | Catch + log WARNING; job tiếp tục với user tiếp theo |
| `fcm_token` NULL khi gửi | Backend | Bỏ qua silently (log DEBUG) |
| `timezone` NULL khi chạy job | Backend | Bỏ qua user đó (không gửi reminder); log DEBUG |
| `timezone` không hợp lệ (`PUT /users/fcm-token`) | Backend | 422 `INVALID_TIMEZONE` |
| `reminder_type` không hợp lệ (`PUT /preferences/{type}`) | Backend | 422 (Pydantic enum) |
| Recipient bị block (new-photo) | Backend | Bỏ qua, không gửi; không báo lỗi (silent — F10 FR-5) |
| User đã logout (fcm_token=NULL) | Backend | Bỏ qua silently (DL-F10-07) |
| APScheduler crash | Backend | Log ERROR; restart không tự động trong MVP |

**Nguyên tắc:** Notification là best-effort trong mọi trường hợp.
FCM failure **không** rollback post creation và **không** trả lỗi
cho client (DL-F05-05).

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory cho model/service/migration).
Client: Jest + RNTL, TDD.

### 6.1 Migration — `test_f09_migration.py`

| Test case | Mô tả |
|---|---|
| `test_users_timezone_column` | `users.timezone` tồn tại, nullable |
| `test_notif_pref_table_exists` | Bảng `notification_preferences` tồn tại |
| `test_notif_pref_columns` | Đủ cột: `user_id, reminder_type, enabled, updated_at` |
| `test_notif_pref_unique_pair` | `UNIQUE (user_id, reminder_type)` |

### 6.2 `notification_pref_service` — `test_notif_pref_service.py`

| Test case | Mô tả |
|---|---|
| `test_get_prefs_no_rows_defaults_all_true` | Không có row → tất cả 4 loại trả `true` (AC-F09-4) |
| `test_set_preference_creates_row` | Upsert lần đầu tạo row mới |
| `test_set_preference_updates_existing` | Upsert lần 2 update row cũ |
| `test_set_preference_idempotent` | Set `enabled=false` 2 lần → không lỗi, vẫn `false` |
| `test_get_prefs_mixed` | 1 row `bathing=false`, 3 loại còn lại `true` |

### 6.3 `notification_service` — `test_notification_service.py`

| Test case | Mô tả |
|---|---|
| `test_send_new_photo_calls_fcm_per_recipient` | N recipients → N FCM calls (mock SDK) |
| `test_send_new_photo_skips_null_token` | recipient.fcm_token=NULL → không gọi FCM |
| `test_send_new_photo_skips_blocked` | recipient bị block bởi sender → không gọi FCM (DL-F09-04) |
| `test_send_new_photo_fcm_error_no_raise` | FCM throw → warning log, không raise (best-effort) |
| `test_send_reminder_calls_fcm` | Gọi FCM với message đúng format (AC-F09-3) |
| `test_send_reminder_fcm_error_no_raise` | FCM throw → warning log, không raise |

### 6.4 Router — `test_router_notifications.py`

| Test case | Mô tả |
|---|---|
| `test_get_preferences_default_all_true` | GET khi không có row → `{feeding:true,...}` (AC-F09-4) |
| `test_put_preference_204` | PUT `bathing` `{enabled:false}` → 204 |
| `test_put_preference_idempotent` | PUT 2 lần → 204 cả hai |
| `test_put_preference_invalid_type_422` | `reminder_type=unknown` → 422 |
| `test_get_prefs_reflects_update` | PUT rồi GET → giá trị mới |

### 6.5 `reminder_scheduler` — `test_reminder_scheduler.py`

| Test case | Mô tả |
|---|---|
| `test_load_reminders_yaml_valid` | Load YAML hợp lệ → list entries đủ species + type + hour + minute |
| `test_load_reminders_yaml_invalid_type` | `type: unknown` → raise `ValueError` |
| `test_job_sends_to_matching_timezone_user` | User ở timezone khớp giờ YAML → `send_reminder` được gọi (AC-F09-6) |
| `test_job_skips_non_matching_timezone` | User ở timezone không khớp → không gọi `send_reminder` |
| `test_job_skips_disabled_preference` | User có `enabled=false` → không gọi `send_reminder` (AC-F09-5) |
| `test_job_skips_null_timezone_user` | User `timezone=NULL` → bỏ qua |
| `test_job_skips_null_fcm_token` | `fcm_token=NULL` → bỏ qua |

### 6.6 `PUT /users/fcm-token` mở rộng — `test_fcm_token_timezone.py`

| Test case | Mô tả |
|---|---|
| `test_put_fcm_token_with_timezone` | Gửi `fcm_token + timezone` → 204, `users.timezone` được lưu |
| `test_put_fcm_token_without_timezone` | Gửi chỉ `fcm_token` → 204, `timezone` không đổi |
| `test_put_fcm_token_invalid_timezone` | `timezone="invalid/tz"` → 422 `INVALID_TIMEZONE` |

### 6.7 Client — `NotificationService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_register_token_sends_timezone` | `registerToken` truyền `timezone` từ `Intl` vào body |
| `test_get_preferences_parses_response` | Response API → `NotificationPreferences` object |
| `test_set_preference_calls_put` | `setPreference("bathing", false)` → PUT đúng URL + body |

### 6.8 Client — `NotificationPreferenceSection.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_renders_4_toggles` | 4 toggle rows hiển thị |
| `test_toggle_off_calls_set_preference` | Tắt toggle "Tắm" → `setPreference("bathing", false)` |
| `test_toggle_reflects_preference_state` | Props `preferences` ảnh hưởng trạng thái toggle |

### 6.9 Integration — `test_f09_notification_flow.py`

| Test case | Mô tả |
|---|---|
| `test_new_photo_push_sent_to_recipients` | POST /posts với N friends → FCM mock nhận N calls (AC-F09-1) |
| `test_new_photo_no_push_zero_recipients` | 0 recipients → FCM không được gọi |
| `test_new_photo_blocked_recipient_skipped` | sender block recipient → FCM bỏ qua recipient đó |
| `test_preference_toggle_affects_reminder_job` | Set `bathing=false` → job không gửi bathing reminder (AC-F09-5) |

### 6.10 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F09-1 | `test_new_photo_push_sent_to_recipients`, `test_send_new_photo_calls_fcm_per_recipient` |
| AC-F09-2 | `test_send_new_photo_calls_fcm_per_recipient` (data.post_id + screen trong payload) |
| AC-F09-3 | `test_send_reminder_calls_fcm`, `test_job_sends_to_matching_timezone_user` |
| AC-F09-4 | `test_get_prefs_no_rows_defaults_all_true`, `test_get_preferences_default_all_true` |
| AC-F09-5 | `test_job_skips_disabled_preference`, `test_preference_toggle_affects_reminder_job` |
| AC-F09-6 | `test_job_sends_to_matching_timezone_user`, `test_job_skips_non_matching_timezone` |
