# F09 — Notification System — Tasks

**Đọc trước khi thực thi:**
- `specs/f09-notifications/requirements.md`
- `specs/f09-notifications/design.md`
- `specs/f09-notifications/decision_log.md` (nếu có)

**Thứ tự thực thi:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

---

## T1 — Bootstrap + test runner

**Mục tiêu:** Thiết lập cấu trúc file và môi trường test cho F09.

### T1.1 — Tạo cấu trúc thư mục và file placeholder

Tạo (chưa implement logic):

**Backend:**
- `backend/app/models/notification_pref.py` — `ReminderType` enum +
  `NotificationPreference` ORM (stub)
- `backend/app/schemas/notification.py` — `SetPreferenceRequest`,
  `PreferencesResponse` (stub)
- `backend/app/services/notification_pref_service.py` — placeholder
- `backend/app/routers/notifications.py` — placeholder
- `backend/app/reminder_scheduler.py` — placeholder
- `backend/config/reminders.yaml` — file YAML với schema đầy đủ
  (các entry dog/cat, 4 loại reminder, giờ theo design §2.3)

**Client:**
- `src/services/NotificationService.ts` — stub export
- `src/components/NotificationPreferenceSection.tsx` — stub
- `src/__tests__/notifications/NotificationService.test.ts` —
  file test rỗng có `describe` block
- `src/__tests__/notifications/NotificationPreferenceSection.test.tsx`
  — file test rỗng có `describe` block

### T1.2 — Đăng ký router vào `main.py`

Thêm import + `app.include_router(notifications_router, prefix=
"/notifications", tags=["notifications"])` vào
`backend/app/main.py`.

**Verify:** `pytest backend/tests/ -x` pass (không có test mới
thất bại do import lỗi).

---

## T2 — Migration: `users.timezone` + bảng `notification_preferences`

**Refs:** Design §2.1, §2.2; DL-F09-02, DL-F09-06

### T2.1 — Viết test migration trước (TDD)

File: `backend/tests/test_f09_migration.py`

Test cases (Design §6.1):
- `test_users_timezone_column` — `users.timezone` tồn tại, nullable
- `test_notif_pref_table_exists` — bảng `notification_preferences`
  tồn tại
- `test_notif_pref_columns` — đủ cột: `id, user_id, reminder_type,
  enabled, updated_at`
- `test_notif_pref_unique_pair` — `UNIQUE (user_id, reminder_type)`

Dùng SQLite in-memory + Alembic `run_migrations()` theo tiền lệ F03.

### T2.2 — Tạo Alembic migration

File: `backend/alembic/versions/*_f09_add_timezone_and_notif_prefs.py`

- `ALTER TABLE users ADD COLUMN timezone TEXT;`
- `CREATE TABLE notification_preferences (id UUID PK, user_id UUID
  FK→users CASCADE, reminder_type VARCHAR NOT NULL, enabled BOOLEAN
  NOT NULL DEFAULT TRUE, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, reminder_type));`
- Index: `idx_notif_pref_user (user_id)`

### T2.3 — Cập nhật ORM `NotificationPreference`

`backend/app/models/notification_pref.py`:
- `ReminderType(enum.StrEnum)`: `feeding, sleeping, bathing, playing`
- `NotificationPreference(Base)`: đủ columns + `UniqueConstraint`
- Re-export qua `backend/app/models/__init__.py`

Thêm `timezone: Mapped[str | None]` vào `User` ORM
(`backend/app/models/user.py`).

**Verify:** `pytest backend/tests/test_f09_migration.py` — tất cả
pass.

---

## T3 — `notification_pref_service` + API preferences

**Refs:** Design §3.2, §3.3, §4.1; AC-F09-4, AC-F09-5; DL-F09-06

### T3.1 — Viết test service trước (TDD)

File: `backend/tests/test_notif_pref_service.py`

Test cases (Design §6.2):
- `test_get_prefs_no_rows_defaults_all_true`
- `test_set_preference_creates_row`
- `test_set_preference_updates_existing`
- `test_set_preference_idempotent`
- `test_get_prefs_mixed`

### T3.2 — Implement `notification_pref_service.py`

- `get_preferences(db, user_id) -> dict[ReminderType, bool]`
  — query `notification_preferences WHERE user_id=X`; loại không
  có row → `True`; trả dict 4 key.
- `set_preference(db, user_id, reminder_type, enabled) -> None`
  — upsert: INSERT … ON CONFLICT (user_id, reminder_type) DO UPDATE
  SET enabled=excluded.enabled, updated_at=now().

### T3.3 — Viết test router trước (TDD)

File: `backend/tests/test_router_notifications.py`

Test cases (Design §6.4):
- `test_get_preferences_default_all_true`
- `test_put_preference_204`
- `test_put_preference_idempotent`
- `test_put_preference_invalid_type_422`
- `test_get_prefs_reflects_update`

### T3.4 — Implement `routers/notifications.py`

- `GET /notifications/preferences` → `notification_pref_service.
  get_preferences(db, current_user.id)` → 200 `PreferencesResponse`
- `PUT /notifications/preferences/{reminder_type}` → validate enum
  → `set_preference(...)` → 204

**Verify:** `pytest backend/tests/test_notif_pref_service.py
backend/tests/test_router_notifications.py` — tất cả pass.

---

## T4 — Mở rộng `PUT /users/fcm-token` với `timezone`

**Refs:** Design §3.1; DL-F09-02; AC-F09-6

### T4.1 — Viết test mở rộng trước (TDD)

File: `backend/tests/test_fcm_token_timezone.py`

Test cases (Design §6.6):
- `test_put_fcm_token_with_timezone`
- `test_put_fcm_token_without_timezone`
- `test_put_fcm_token_invalid_timezone`

### T4.2 — Mở rộng schema `FcmTokenRequest`

`backend/app/schemas/profile.py` (hoặc `auth.py` tuỳ tiền lệ):
thêm `timezone: str | None = None` vào request body.

### T4.3 — Cập nhật handler `PUT /users/fcm-token`

- Nếu `timezone` có mặt: validate bằng `zoneinfo.available_timezones()`
  → ngoài tập → 422 `INVALID_TIMEZONE`.
- Nếu hợp lệ: `user.timezone = request.timezone; db.commit()`.
- Nếu không có `timezone`: giữ nguyên giá trị cũ.

**Verify:** `pytest backend/tests/test_fcm_token_timezone.py` —
tất cả pass.

---

## T5 — Mở rộng `notification_service` — `send_new_photo`

**Refs:** Design §1.1, §4.1, §5; AC-F09-1, AC-F09-2; DL-F09-01,
DL-F09-04, DL-F05-05

### T5.1 — Viết test `notification_service` trước (TDD)

File: `backend/tests/test_notification_service.py`

Test cases (Design §6.3):
- `test_send_new_photo_calls_fcm_per_recipient`
- `test_send_new_photo_skips_null_token`
- `test_send_new_photo_skips_blocked`
- `test_send_new_photo_fcm_error_no_raise`
- `test_send_reminder_calls_fcm`
- `test_send_reminder_fcm_error_no_raise`

Mock Firebase Admin SDK `messaging.send` bằng `unittest.mock.patch`.

### T5.2 — Implement `send_new_photo` trong `notification_service.py`

Thêm method `send_new_photo(self, post, db)`:
1. Query `post_recipients WHERE post_id = post.id`.
2. Với mỗi recipient: kiểm tra `_is_blocked(sender_id, recipient_id,
   db)` → skip nếu True.
3. Đọc `user.fcm_token`; skip nếu NULL.
4. Gọi `firebase_admin.messaging.send(Message(...))` với payload
   (title, body, image=cdn_url, data={post_id, screen}).
5. Wrap trong `try/except Exception` → log WARNING, không raise.

Thêm helper `_is_blocked(sender_id, recipient_id, db) -> bool`:
query `blocked_users WHERE (blocker_id=sender AND blocked_id=recipient)
OR (blocker_id=recipient AND blocked_id=sender)`.

### T5.3 — Điền F09 hook trong `post_service.create_post`

`backend/app/services/post_service.py`: sau `db.commit()`, thay
comment `# F09 hook` bằng lệnh gọi:

```python
NotificationService(db).send_new_photo(post, db)
```

**Verify:** `pytest backend/tests/test_notification_service.py` —
tất cả pass; `pytest backend/tests/test_service_post.py` vẫn pass
(không regression).

---

## T6 — YAML loader + `reminder_scheduler` (APScheduler)

**Refs:** Design §1.2, §2.3, §4.1; AC-F09-3, AC-F09-5, AC-F09-6;
DL-F09-05

### T6.1 — Implement `send_reminder` trong `notification_service.py`

Thêm method `send_reminder(self, user, pet_name, reminder_type)`:
- Gọi FCM với `title="Nhắc nhở thú cưng"`,
  `body=f"Đến giờ {REMINDER_LABELS[reminder_type]} cho {pet_name} rồi!"`.
- Best-effort: wrap trong `try/except`, log WARNING nếu lỗi.

```python
REMINDER_LABELS = {
    ReminderType.feeding:  "cho ăn",
    ReminderType.sleeping: "ngủ",
    ReminderType.bathing:  "tắm",
    ReminderType.playing:  "chơi",
}
```

### T6.2 — Viết test `reminder_scheduler` trước (TDD)

File: `backend/tests/test_reminder_scheduler.py`

Test cases (Design §6.5):
- `test_load_reminders_yaml_valid`
- `test_load_reminders_yaml_invalid_type`
- `test_job_sends_to_matching_timezone_user`
- `test_job_skips_non_matching_timezone`
- `test_job_skips_disabled_preference`
- `test_job_skips_null_timezone_user`
- `test_job_skips_null_fcm_token`

Mock `notification_service.send_reminder`; mock `datetime.now(UTC)`;
dùng SQLite in-memory.

### T6.3 — Implement `reminder_scheduler.py`

- `load_reminders(yaml_path) -> list[ReminderEntry]`: parse YAML,
  validate `type` ∈ ReminderType, raise `ValueError` nếu không hợp lệ.
- `run_reminder_job(db_factory, reminders)`: hàm job chính, chạy mỗi
  1 phút.
  - Mỗi entry: query users có pet loại `species`, `fcm_token NOT NULL`,
    `timezone NOT NULL`.
  - Với mỗi user: `zoneinfo.ZoneInfo(user.timezone)` → local time;
    so sánh `hour:minute` với entry.
  - Check `notification_pref_service.get_preferences(db, uid)[type]`
    → True → gọi `send_reminder`.
- `start(app)`: khởi động `BackgroundScheduler`, thêm
  `interval(minutes=1)` job, `scheduler.start()` trong FastAPI
  `startup` event.

**Verify:** `pytest backend/tests/test_reminder_scheduler.py` —
tất cả pass.

---

## T7 — Client: `NotificationService.ts` + `NotificationPreferenceSection`

**Refs:** Design §2.5, §4.2; AC-F09-4, AC-F09-5

### T7.1 — Viết test client trước (TDD)

Files:
- `src/__tests__/notifications/NotificationService.test.ts`
  (Design §6.7): `test_register_token_sends_timezone`,
  `test_get_preferences_parses_response`,
  `test_set_preference_calls_put`
- `src/__tests__/notifications/NotificationPreferenceSection.test.tsx`
  (Design §6.8): `test_renders_4_toggles`,
  `test_toggle_off_calls_set_preference`,
  `test_toggle_reflects_preference_state`

### T7.2 — Implement `NotificationService.ts`

```typescript
// src/services/NotificationService.ts
export const NotificationService = {
  registerToken,    // PUT /users/fcm-token + timezone
  getPreferences,   // GET /notifications/preferences
  setPreference,    // PUT /notifications/preferences/{type}
};
```

- `registerToken(fcmToken, timezone?)`: gọi `PUT /users/fcm-token`
  với body `{ fcm_token, timezone }` (timezone từ
  `Intl.DateTimeFormat().resolvedOptions().timeZone`).
- `getPreferences()`: `GET /notifications/preferences` → parse
  `NotificationPreferences`.
- `setPreference(type, enabled)`: `PUT /notifications/preferences/
  {type}` → `{ enabled }`.
- HTTP injectable/mockable (theo tiền lệ DL-F03-11, DL-F04-03).

### T7.3 — Implement `NotificationPreferenceSection.tsx`

Component render 4 hàng Toggle:

| Key | Label (tiếng Việt) |
|---|---|
| `feeding` | Cho ăn |
| `sleeping` | Ngủ |
| `bathing` | Tắm |
| `playing` | Chơi |

Props: `preferences: NotificationPreferences`, `onToggle: (type:
ReminderType, enabled: boolean) => void`.

Parent `SettingsScreen` (F10) gọi `NotificationService.setPreference`
trong `onToggle`.

**Verify:** `npx jest src/__tests__/notifications/` — tất cả pass.

---

## T8 — Integration tests end-to-end + Acceptance Criteria

**Refs:** Design §6.9; AC-F09-1, AC-F09-5; FR-6, FR-7

### T8.1 — Viết integration tests

File: `backend/tests/test_f09_notification_flow.py`

Test cases (Design §6.9):
- `test_new_photo_push_sent_to_recipients` — POST /posts với N
  friends → FCM mock nhận N calls (AC-F09-1)
- `test_new_photo_no_push_zero_recipients` — 0 recipients → FCM
  không được gọi (FR-7)
- `test_new_photo_blocked_recipient_skipped` — sender block recipient
  → FCM bỏ qua recipient (DL-F09-04, F10 FR-5)
- `test_preference_toggle_affects_reminder_job` — PUT preference
  `bathing=false` → job không gửi bathing reminder (AC-F09-5)

Mock FCM với `unittest.mock.patch("firebase_admin.messaging.send")`.
Dùng TestClient (FastAPI) + SQLite in-memory.

**Verify:** `pytest backend/tests/test_f09_notification_flow.py` —
tất cả pass.

### T8.2 — Regression check toàn bộ test suite

```
pytest backend/tests/ -x --tb=short
```

Đảm bảo không regression ở F01–F10. Nếu có lỗi import hoặc schema
conflict → fix trước khi kết thúc.

---

## Acceptance Criteria Coverage Summary

| AC | Task phủ |
|---|---|
| AC-F09-1 — New-photo push trong 5s | T5, T8.1 |
| AC-F09-2 — Deep link từ notification | T5 (data payload) |
| AC-F09-3 — Daily reminder đúng giờ | T6 |
| AC-F09-4 — Reminder mặc định bật | T3, T7 |
| AC-F09-5 — Tắt reminder hoạt động | T3, T6, T7, T8 |
| AC-F09-6 — Timezone đúng | T4, T6 |
