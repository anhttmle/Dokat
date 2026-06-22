# F10 — Settings (Liên kết tài khoản, Block/Report, Logout) — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F01 / F03 / F06 / F10)

F10 gom các tác vụ **cài đặt tài khoản** cho MVP: liên kết/hủy liên
kết provider, chặn/báo cáo người dùng, và đăng xuất. Đây là feature
**ghi-nhẹ**: thêm 2 bảng (`blocked_users`, `reports`) và một router
`/users`, đồng thời **điền** hook block-aware mà F06 đã chừa sẵn.

Ranh giới với các feature lân cận:

- **F01 — Auth (đã xong):** Liên kết provider **dùng lại**
  `POST /auth/link` (F01) và đọc trạng thái provider từ
  `POST /auth/session` (trường `providers`). F10 **chỉ thêm**
  endpoint *hủy* liên kết `DELETE /users/providers/{provider}`
  (DL-F10-01). Việc thực thi unlink phía Firebase do client gọi
  Firebase Auth API; backend chỉ xoá row `user_providers`
  (DL-F10-02).
- **F03 — Social Graph (đã xong):** Block **xoá friendship** bằng
  `friend_service.delete_friendship` rồi ghi `blocked_users`
  (DL-F10-03). Vì friendship bị xoá, người bị block **tự động**
  biến mất khỏi danh sách bạn bè — F10 **không** sửa
  `friend_service` (DL-F10-10).
- **F06 — Feed (đã xong):** Feed query đã block-aware qua hook
  `feed_service._blocked_sender_ids` trả `set()` rỗng (DL-F06-03).
  F10 **điền** hook này bằng `block_service.get_blocked_user_ids`
  để loại ảnh hai chiều (DL-F10-04) — **không** sửa cấu trúc
  query feed.
- **F09 — Notifications (sau F10):** Block ở chế độ **silent** —
  không gửi notification cho người bị block (FR-5, DL-F10-03).
  Logout chỉ xoá `fcm_token` để chặn push tới thiết bị đã đăng
  xuất (DL-F10-07).

> Out-of-scope (Non-goals): privacy nâng cao, hide post/user, xoá
> tài khoản, cache cleaning. Không cho block người **không** phải
> bạn bè (FR-4, AC-F10-4). Unblock **không** khôi phục friendship
> (DL-F10-05).

---

## 1. Architecture Overview

```
┌──────────────────────────── React Native Client ───────────────────────────┐
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                            SettingsScreen                               │ │
│  │  - AccountLinkRow × N   provider status + link/unlink (FR-1,2,3)        │ │
│  │  - BlockedUsersSection  list + unblock           (FR-8; AC-F10-3)       │ │
│  │  - Logout button → confirm                       (FR-9,10; AC-F10-6)    │ │
│  └───────────────┬───────────────────────────┬───────────────────────────┘ │
│   link/unlink    │           block/report     │   logout                     │
│  ┌───────────────▼───┐  ┌────────────────────▼──┐  ┌───────────────────────┐ │
│  │   AuthService     │  │     SettingsService    │  │   AuthService.signOut │ │
│  │ linkWithProvider  │  │ unlinkProvider         │  │ + LocalStorage clear  │ │
│  │ (F01, reused)     │  │ blockUser/unblockUser  │  │ + SettingsService.    │ │
│  └───────────────────┘  │ listBlocked/reportUser │  │   logout (clear token)│ │
│                         │ logout                 │  └───────────────────────┘ │
│                         └───────────┬────────────┘                            │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                       ▼  HTTPS + Firebase ID token
┌──────────────────────────── FastAPI Backend ───────────────────────────────┐
│  routers/settings.py (prefix /users)                                        │
│    DELETE /users/providers/{provider} → account_service.unlink_provider     │
│      guard: phải còn ≥1 provider khác (FR-3, AC-F10-2)                       │
│    POST   /users/block        → block_service.block_user                    │
│      guard: phải là bạn bè (FR-4) → xoá friendship + insert block (silent)  │
│    DELETE /users/block/{id}   → block_service.unblock_user (idempotent)     │
│    GET    /users/block        → block_service.list_blocked                  │
│    POST   /users/report       → report_service.report_user                  │
│    POST   /users/logout       → account_service.clear_device_token          │
│                                                                             │
│  feed_service._blocked_sender_ids ← block_service.get_blocked_user_ids      │
│      (điền hook F06; loại ảnh hai chiều — DL-F10-04)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng — Liên kết / hủy liên kết provider (AC-F10-1, AC-F10-2)

1. `SettingsScreen` đọc `providers` hiện có (từ `AuthService` /
   session F01) → render mỗi provider (Apple/Google/Facebook) với
   trạng thái "Đã liên kết" / "Chưa liên kết" (FR-1).
2. **Liên kết:** nhấn "Liên kết Google" → `AuthService.
   linkWithProvider("google")` (native OAuth + Firebase) → client
   gọi `POST /auth/link` (F01) để đồng bộ `user_providers` →
   refresh UI (FR-2, AC-F10-1). F10 **không** thêm endpoint link
   mới (DL-F10-01).
3. **Hủy liên kết:** nhấn "Hủy liên kết" →
   `SettingsService.unlinkProvider(provider)` →
   `DELETE /users/providers/{provider}`. Backend kiểm tra user còn
   ≥1 provider khác; nếu provider là **duy nhất** → **422
   `LAST_PROVIDER`**, không xoá (FR-3, AC-F10-2, DL-F10-02). Thành
   công → client gọi Firebase unlink + refresh UI.

### 1.2 Luồng — Block user (silent) (AC-F10-3, AC-F10-4)

1. Từ ngữ cảnh bạn bè, người dùng A chọn "Chặn B" →
   `SettingsService.blockUser(B)` → `POST /users/block {user_id:B}`.
2. Backend `block_service.block_user(db, blocker=A, blocked=B)`:
   - Nếu `A == B` → **422 `SELF_BLOCK`** (DL-F10-11).
   - Nếu A và B **không** là bạn bè → **422 `NOT_FRIENDS`** (FR-4,
     AC-F10-4, DL-F10-03).
   - Ngược lại: `delete_friendship(A, B)` (F03) + upsert
     `blocked_users(blocker_id=A, blocked_id=B)` (idempotent).
   - **Không** gửi bất kỳ notification nào (silent — FR-5).
3. Hệ quả: B biến mất khỏi danh sách bạn bè A và A khỏi danh sách
   của B (do friendship đã xoá — DL-F10-10); cả hai **không** gửi
   ảnh cho nhau (recipient phải là bạn bè — F05); ảnh cũ của B bị
   loại khỏi feed A (và ngược lại) qua hook (DL-F10-04).

### 1.3 Luồng — Unblock (AC-F10-3)

- `DELETE /users/block/{id}` → xoá row `blocked_users` nếu có
  (idempotent → 204). Unblock **không** tự khôi phục friendship;
  hai người phải kết bạn lại qua QR (F03) (DL-F10-05).

### 1.4 Luồng — Report user (AC-F10-5)

1. `SettingsService.reportUser(B, reason)` →
   `POST /users/report {user_id:B, reason}`.
2. Backend `report_service.report_user` lưu
   `reports(reporter_id, reported_user_id, reason, created_at)` →
   **201**. `reason` thuộc enum cố định (`spam`,
   `inappropriate`, `harassment`, `other` — DL-F10-06).
3. Report **không** tự ẩn/khoá B (AC-F10-5); chỉ lưu cho
   Admin/Moderation xử lý. Client hiển thị "Cảm ơn bạn đã báo cáo".

### 1.5 Luồng — Logout (AC-F10-6)

1. Người dùng nhấn "Đăng xuất" → xác nhận →
   `SettingsService.logout()` → `POST /users/logout` xoá
   `users.fcm_token` (chặn push tới thiết bị — DL-F10-07).
2. Client `AuthService.signOut()` (Firebase) + xoá
   `LocalStorageService` (firebase_uid, session) → điều hướng về
   màn hình **Onboarding** (FR-9, FR-10).

---

## 2. Data Models / Schema

F10 thêm **2 bảng mới**; không sửa schema bảng cũ (`users`,
`friendships`, `user_providers` giữ nguyên — DL-F10-01, DL-F10-10).

### 2.1 `blocked_users` — quan hệ chặn (một chiều, hiệu lực hai chiều)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `blocker_id` | UUID | FK `users.id` ON DELETE CASCADE, NOT NULL, index |
| `blocked_id` | UUID | FK `users.id` ON DELETE CASCADE, NOT NULL, index |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

- `UNIQUE (blocker_id, blocked_id)` (`blocked_users_unique_pair`) —
  chặn trùng; block là idempotent ở service (DL-F10-03).
- Record **một chiều** (`blocker → blocked`) nhưng hiệu lực
  **hai chiều** ở feed: A block B thì cả hai không thấy ảnh nhau
  (DL-F10-04). Không có `CHECK (blocker_id <> blocked_id)` (SQLite
  không đồng nhất); service từ chối self-block (DL-F10-11).
- Index `idx_blocked_users_blocker` (lọc theo A) +
  `idx_blocked_users_blocked` (chiều ngược cho hook feed).

### 2.2 `reports` — báo cáo người dùng

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `reporter_id` | UUID | FK `users.id` ON DELETE CASCADE, NOT NULL, index |
| `reported_user_id` | UUID | FK `users.id` ON DELETE CASCADE, NOT NULL, index |
| `reason` | ENUM `report_reason` | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

- `report_reason` ∈ {`spam`, `inappropriate`, `harassment`,
  `other`} (DL-F10-06). Không UNIQUE — cho phép report nhiều lần.

### 2.3 ORM models (SQLAlchemy)

```python
# app/models/block.py
class BlockedUser(Base):
    __tablename__ = "blocked_users"
    __table_args__ = (
        UniqueConstraint(
            "blocker_id", "blocked_id", name="blocked_users_unique_pair"
        ),
    )
    # id, blocker_id, blocked_id, created_at

# app/models/report.py
class ReportReason(enum.StrEnum):
    spam = "spam"
    inappropriate = "inappropriate"
    harassment = "harassment"
    other = "other"

class Report(Base):
    __tablename__ = "reports"
    # id, reporter_id, reported_user_id, reason, created_at
```

Đăng ký re-export trong `app/models/__init__.py` (theo tiền lệ).

### 2.4 Client — kiểu dữ liệu (TypeScript)

```typescript
type OAuthProviderName = 'apple' | 'google' | 'facebook';
type ReportReason = 'spam' | 'inappropriate' | 'harassment' | 'other';

interface BlockedUserItem {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  blocked_at: string; // ISO 8601
}
```

---

## 3. API Contracts

Mọi endpoint yêu cầu Firebase ID token (middleware hiện có).
`firebase_uid` → caller UUID theo `_get_user_id` (như
`routers/friends.py` / `routers/posts.py`); chưa có user row →
**404 `USER_NOT_FOUND`** (DL-F10-08).

### 3.1 `DELETE /users/providers/{provider}` — hủy liên kết

`provider` ∈ {`apple`, `google`, `facebook`}.

- **204** khi xoá thành công row `user_providers`.
- **422 `LAST_PROVIDER`** nếu đây là provider **duy nhất** còn lại
  (tránh khóa tài khoản — FR-3, AC-F10-2, DL-F10-02).
- **404 `PROVIDER_NOT_LINKED`** nếu provider chưa được liên kết.

### 3.2 `POST /users/block` — chặn người dùng (silent)

**Request**

```jsonc
{ "user_id": "<uuid của người bị chặn>" }
```

- **201** `{ "blocked_user_id": "<uuid>" }` (idempotent: block lại
  cùng người vẫn 201).
- **422 `SELF_BLOCK`** nếu `user_id` là chính caller (DL-F10-11).
- **422 `NOT_FRIENDS`** nếu hai người không phải bạn bè (FR-4,
  AC-F10-4, DL-F10-03).
- **404 `USER_NOT_FOUND`** nếu `user_id` không tồn tại.
- **Hệ quả:** friendship bị xoá; **không** notification (FR-5).

### 3.3 `DELETE /users/block/{user_id}` — bỏ chặn

- **204** (idempotent; không khôi phục friendship — DL-F10-05).

### 3.4 `GET /users/block` — danh sách đã chặn

Phục vụ UI quản lý/bỏ chặn (DL-F10-09).

```jsonc
{ "blocked": [
    { "user_id": "<uuid>", "display_name": "B",
      "avatar_url": "https://...", "blocked_at": "2026-06-22T07:00:00Z" }
  ], "total": 1 }
```

### 3.5 `POST /users/report` — báo cáo người dùng

**Request**

```jsonc
{ "user_id": "<uuid bị báo cáo>", "reason": "spam" }
```

- **201** `{ "report_id": "<uuid>" }` (AC-F10-5).
- **422 `INVALID_REASON`** nếu `reason` ngoài enum (DL-F10-06).
- **422 `SELF_REPORT`** nếu báo cáo chính mình.
- **404 `USER_NOT_FOUND`** nếu `user_id` không tồn tại.
- Report **không** ẩn/khoá người bị báo cáo (AC-F10-5).

### 3.6 `POST /users/logout` — xoá device token

- **204**; xoá `users.fcm_token` của caller (DL-F10-07). Idempotent
  (token đã null vẫn 204).

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/app/
├── models/
│   ├── block.py            # BlockedUser
│   └── report.py           # ReportReason, Report
├── schemas/
│   └── settings.py         # BlockRequest, ReportRequest, Blocked* responses
├── services/
│   ├── block_service.py    # block_user, unblock_user, list_blocked,
│   │                       #   get_blocked_user_ids
│   ├── report_service.py   # report_user
│   └── account_service.py  # unlink_provider, clear_device_token
└── routers/
    └── settings.py         # /users/* endpoints
```

| Component | Trách nhiệm |
|---|---|
| `models/block.py` | `BlockedUser` (§2.1, §2.3). |
| `models/report.py` | `ReportReason` enum + `Report` (§2.2, §2.3). |
| `block_service.block_user(db, *, blocker_id, blocked_id)` | Validate self/friendship; `delete_friendship` + upsert block; silent (DL-F10-03). |
| `block_service.unblock_user(db, *, blocker_id, blocked_id)` | Xoá row nếu có; idempotent (DL-F10-05). |
| `block_service.list_blocked(db, blocker_id)` | JOIN `users` → list `BlockedUserItem` (DL-F10-09). |
| `block_service.get_blocked_user_ids(db, user_id)` | Trả `set()` hai chiều (people user blocked ∪ people who blocked user) cho hook feed (DL-F10-04). |
| `report_service.report_user(db, *, reporter_id, reported_user_id, reason)` | Validate self/enum/user; insert `Report` (DL-F10-06). |
| `account_service.unlink_provider(db, *, user_id, provider)` | Guard ≥1 provider còn lại; xoá `UserProvider` (DL-F10-02). |
| `account_service.clear_device_token(db, user_id)` | Set `fcm_token=None` (DL-F10-07). |
| `routers/settings.py` | 6 endpoint §3; resolve caller (`_get_user_id`); map exception → mã lỗi; đăng ký `main.py`. |
| `feed_service._blocked_sender_ids` | **Sửa** thân: gọi `block_service.get_blocked_user_ids` (điền hook F06 — DL-F10-04). |

### 4.2 Client (React Native)

```
src/
├── services/
│   ├── SettingsService.ts             # unlink/block/unblock/list/report/logout
│   └── __mocks__/SettingsService.ts
├── components/
│   ├── AccountLinkRow.tsx             # 1 provider: status + link/unlink
│   └── ReportDialog.tsx               # chọn reason → reportUser
├── screens/
│   └── SettingsScreen.tsx             # account + blocked list + logout
└── __tests__/settings/
    ├── SettingsService.test.ts
    ├── AccountLinkRow.test.tsx
    ├── ReportDialog.test.tsx
    └── SettingsScreen.test.tsx
```

| Component | Trách nhiệm |
|---|---|
| `SettingsService` | `unlinkProvider`, `blockUser`, `unblockUser`, `listBlocked`, `reportUser`, `logout` → endpoints §3; auth header qua `AuthService.getIdToken` (như `SocialService`). |
| `AccountLinkRow` | Hiển thị trạng thái 1 provider (FR-1); nút link (gọi `AuthService.linkWithProvider` + `/auth/link`) / unlink (gọi `SettingsService.unlinkProvider`); chặn unlink provider cuối → hiển thị lỗi (AC-F10-2). |
| `ReportDialog` | Picker reason cố định (DL-F10-06) → `SettingsService.reportUser`; xác nhận "Cảm ơn bạn đã báo cáo" (AC-F10-5). |
| `SettingsScreen` | Render `AccountLinkRow` cho 3 provider (FR-1,2,3); danh sách đã chặn + unblock (FR-8); nút Đăng xuất → confirm → `SettingsService.logout` + `AuthService.signOut` + clear storage + nav Onboarding (FR-9,10). |

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| `firebase_uid` chưa có user row | Backend | 404 `USER_NOT_FOUND` (DL-F10-08) |
| Unlink provider duy nhất | Backend | 422 `LAST_PROVIDER`, không xoá (AC-F10-2) |
| Unlink provider chưa liên kết | Backend | 404 `PROVIDER_NOT_LINKED` |
| Block chính mình | Backend | 422 `SELF_BLOCK` (DL-F10-11) |
| Block người không phải bạn bè | Backend | 422 `NOT_FRIENDS` (AC-F10-4) |
| Block lại người đã chặn | Backend | idempotent → 201 (DL-F10-03) |
| Unblock người chưa chặn | Backend | idempotent → 204 (DL-F10-05) |
| Report reason ngoài enum | Backend | 422 `INVALID_REASON` (DL-F10-06) |
| Report/Block `user_id` không tồn tại | Backend | 404 `USER_NOT_FOUND` |
| Logout khi `fcm_token` đã null | Backend | idempotent → 204 (DL-F10-07) |
| Lỗi mạng khi block/report/unlink | Client | giữ UI, hiển thị thông báo lỗi; không crash |
| Notification cho người bị block | — | **không** gửi (silent — FR-5) |

**Nguyên tắc:** Block/unblock/logout là idempotent — gọi lại an
toàn. Report luôn tạo record mới (không idempotent). Mọi guard kiểm
ở service layer; router chỉ map exception → mã lỗi (như
`routers/friends.py`).

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory + `Base.metadata.create_all`,
theo tiền lệ F03/F05). Client: Jest + RNTL, viết test TRƯỚC
implementation (TDD). F10 **có** test migration (tạo 2 bảng mới).

### 6.1 `block_service` — `test_service_block.py`

| Test case | Mô tả |
|---|---|
| `test_block_deletes_friendship` | A,B là bạn → block → friendship bị xoá (FR-4, AC-F10-3) |
| `test_block_inserts_row` | block → `blocked_users(A,B)` tồn tại |
| `test_block_requires_friendship` | A,X không phải bạn → `NotFriendsError` (FR-4, AC-F10-4) |
| `test_block_self_raises` | A block A → `SelfBlockError` (DL-F10-11) |
| `test_block_idempotent` | block 2 lần → 1 row, không lỗi (DL-F10-03) |
| `test_block_is_silent` | block không gọi `NotificationService` (FR-5) |
| `test_unblock_removes_row` | unblock → row biến mất (AC-F10-3) |
| `test_unblock_idempotent` | unblock người chưa chặn → no-op (DL-F10-05) |
| `test_unblock_does_not_restore_friendship` | sau unblock vẫn không là bạn (DL-F10-05) |
| `test_list_blocked_returns_profiles` | list trả `user_id`, `display_name` (DL-F10-09) |
| `test_blocked_ids_bidirectional` | A block B → ids(A) chứa B **và** ids(B) chứa A (DL-F10-04) |

### 6.2 `report_service` — `test_service_report.py`

| Test case | Mô tả |
|---|---|
| `test_report_inserts_row` | report → `reports` có row đúng reason (AC-F10-5) |
| `test_report_invalid_reason` | reason ngoài enum → `InvalidReasonError` (DL-F10-06) |
| `test_report_self_raises` | report chính mình → `SelfReportError` |
| `test_report_does_not_block` | report **không** tạo `blocked_users` (AC-F10-5) |

### 6.3 `account_service` — `test_service_account.py`

| Test case | Mô tả |
|---|---|
| `test_unlink_removes_provider` | còn ≥2 provider → unlink xoá 1 row (FR-3) |
| `test_unlink_last_provider_raises` | provider duy nhất → `LastProviderError` (AC-F10-2) |
| `test_unlink_not_linked_raises` | provider chưa link → `ProviderNotLinkedError` |
| `test_clear_device_token` | logout → `fcm_token` = None (DL-F10-07) |

### 6.4 `feed_service` block hook — `test_service_feed_block.py`

| Test case | Mô tả |
|---|---|
| `test_feed_excludes_blocked_sender` | A block B → ảnh B biến mất khỏi feed A (FR-8, DL-F10-04) |
| `test_feed_excludes_when_blocked_by` | B block A → ảnh B vẫn ẩn khỏi feed A (hai chiều, DL-F10-04) |

### 6.5 Router — `test_router_settings.py`

| Test case | Mô tả |
|---|---|
| `test_block_201` | block bạn bè → 201 + friendship xoá (AC-F10-3) |
| `test_block_not_friends_422` | không phải bạn → 422 `NOT_FRIENDS` (AC-F10-4) |
| `test_block_self_422` | block chính mình → 422 `SELF_BLOCK` |
| `test_unblock_204` | unblock → 204 (AC-F10-3) |
| `test_list_blocked_200` | 200 `{ blocked, total }` |
| `test_report_201` | report hợp lệ → 201 (AC-F10-5) |
| `test_report_invalid_reason_422` | reason sai → 422 `INVALID_REASON` |
| `test_unlink_204` | còn ≥2 provider → 204 (FR-3) |
| `test_unlink_last_provider_422` | provider duy nhất → 422 `LAST_PROVIDER` (AC-F10-2) |
| `test_logout_204` | 204 + `fcm_token` null (AC-F10-6) |
| `test_user_not_found_404` | caller chưa có row → 404 `USER_NOT_FOUND` (DL-F10-08) |

### 6.6 Migration — `test_migration_settings.py`

| Test case | Mô tả |
|---|---|
| `test_blocked_users_table_exists` | upgrade tạo bảng + UNIQUE pair (§2.1) |
| `test_reports_table_exists` | upgrade tạo bảng + enum reason (§2.2) |
| `test_downgrade_drops_tables` | downgrade gỡ cả 2 bảng |

### 6.7 Client — `SettingsService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_block_user_posts` | `blockUser(id)` → `POST /users/block` body `{user_id}` |
| `test_unblock_user_deletes` | `unblockUser(id)` → `DELETE /users/block/{id}` |
| `test_list_blocked_parses` | `listBlocked()` → parse `{blocked,total}` (DL-F10-09) |
| `test_report_user_posts` | `reportUser(id,reason)` → `POST /users/report` (AC-F10-5) |
| `test_unlink_provider_deletes` | `unlinkProvider(p)` → `DELETE /users/providers/{p}` |
| `test_logout_posts` | `logout()` → `POST /users/logout` |
| `test_attaches_auth` | mọi request có `Authorization: Bearer` (như SocialService) |

### 6.8 Client — `AccountLinkRow.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_shows_linked_status` | provider đã link → nhãn "Đã liên kết" (FR-1) |
| `test_shows_unlinked_status` | chưa link → nút "Liên kết" (FR-1, AC-F10-1) |
| `test_unlink_last_shows_error` | unlink provider cuối → hiển thị lỗi (AC-F10-2) |

### 6.9 Client — `ReportDialog.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_renders_reason_options` | hiển thị 4 reason cố định (DL-F10-06) |
| `test_submit_calls_report` | chọn reason + gửi → `reportUser` được gọi (AC-F10-5) |
| `test_shows_confirmation` | sau gửi → "Cảm ơn bạn đã báo cáo" (AC-F10-5) |

### 6.10 Client — `SettingsScreen.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_renders_three_providers` | render 3 `AccountLinkRow` (FR-1) |
| `test_renders_blocked_list` | hiển thị danh sách đã chặn + nút bỏ chặn (FR-8) |
| `test_unblock_calls_service` | bỏ chặn → `SettingsService.unblockUser` (AC-F10-3) |
| `test_logout_flow` | nhấn Đăng xuất → confirm → `logout` + `signOut` + clear storage + nav Onboarding (FR-9,10, AC-F10-6) |

### 6.11 Integration — `test_block_report_flow.py`

| Test case | Mô tả |
|---|---|
| `test_block_then_feed_hidden` | A,B bạn bè; B gửi ảnh cho A → A block B → `GET /feed` của A không còn ảnh B (AC-F10-3, FR-8) |
| `test_block_then_not_friends` | block → `GET /friends` của A không còn B (AC-F10-3) |
| `test_report_persists` | report B → row `reports` tồn tại; B vẫn xuất hiện bình thường (AC-F10-5) |

### 6.12 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F10-1 | `test_shows_unlinked_status` (+ link reuse `/auth/link` của F01) |
| AC-F10-2 | `test_unlink_last_provider_raises`, `test_unlink_last_provider_422`, `test_unlink_last_shows_error` |
| AC-F10-3 | `test_block_deletes_friendship`, `test_unblock_removes_row`, `test_block_201`, `test_unblock_204`, `test_block_then_feed_hidden`, `test_block_then_not_friends` |
| AC-F10-4 | `test_block_requires_friendship`, `test_block_not_friends_422` |
| AC-F10-5 | `test_report_inserts_row`, `test_report_does_not_block`, `test_report_201`, `test_submit_calls_report`, `test_report_persists` |
| AC-F10-6 | `test_clear_device_token`, `test_logout_204`, `test_logout_flow` |

### 6.13 Ghi chú Test

- **Liên kết (link)** dùng lại `POST /auth/link` (F01) — test link
  thuộc F01; F10 chỉ test *unlink* + hiển thị trạng thái
  (DL-F10-01).
- **Firebase unlink/signOut native** không unit-test; client chỉ
  verify gọi đúng `AuthService` + `SettingsService` (DL-F10-02,
  DL-F10-07).
- Gửi FCM thực thuộc F09; F10 chỉ assert block là **silent**
  (không gọi notification — FR-5).
