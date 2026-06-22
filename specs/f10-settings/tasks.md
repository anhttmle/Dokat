# F10 — Settings — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** FastAPI (backend) + React Native/TypeScript (client).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F10 thêm 2 bảng (`blocked_users`, `reports`) + router `/users`, và
> **điền** hook block-aware F06 (DL-F10-04). Liên kết (link) dùng lại
> `POST /auth/link` (F01) — F10 chỉ thêm *unlink* (DL-F10-01). Block
> là **silent** và xoá friendship (DL-F10-03).

---

## 1. Bootstrap F10 structure + test runner

_Tiên quyết cho mọi task. Không có dependency ngoài._

**Làm:**
- Tạo file skeleton backend (`raise NotImplementedError`/`pass`):
  ```
  backend/app/models/block.py
  backend/app/models/report.py
  backend/app/schemas/settings.py
  backend/app/services/block_service.py
  backend/app/services/report_service.py
  backend/app/services/account_service.py
  backend/app/routers/settings.py
  backend/tests/test_service_block.py
  backend/tests/test_service_report.py
  backend/tests/test_service_account.py
  backend/tests/test_service_feed_block.py
  backend/tests/test_router_settings.py
  backend/tests/test_migration_settings.py
  backend/tests/integration/test_block_report_flow.py
  ```
- Tạo file skeleton client:
  ```
  src/services/SettingsService.ts
  src/services/__mocks__/SettingsService.ts
  src/components/AccountLinkRow.tsx
  src/components/ReportDialog.tsx
  src/screens/SettingsScreen.tsx
  src/__tests__/settings/SettingsService.test.ts
  src/__tests__/settings/AccountLinkRow.test.tsx
  src/__tests__/settings/ReportDialog.test.tsx
  src/__tests__/settings/SettingsScreen.test.tsx
  ```
- Định nghĩa kiểu client: `OAuthProviderName`, `ReportReason`,
  `BlockedUserItem` (Design §2.4).

**Verify:** `pytest --collect-only` thấy 7 file test backend mới;
`npx jest --listTests` liệt kê 4 file test client mới;
`npx tsc --noEmit` không lỗi type.

**Refs:** Design §4.1, §4.2

---

## 2. Models + migration `blocked_users` & `reports`

_Phụ thuộc Task 1._

**Test trước:** `backend/tests/test_migration_settings.py` (theo tiền
lệ migration F05):
- `test_blocked_users_table_exists` — upgrade tạo bảng + UNIQUE
  `blocked_users_unique_pair` (§2.1).
- `test_reports_table_exists` — upgrade tạo bảng + enum
  `report_reason` (§2.2).
- `test_downgrade_drops_tables` — downgrade gỡ cả 2 bảng.

**Làm:**
- `models/block.py`: `BlockedUser` (`id`, `blocker_id`, `blocked_id`,
  `created_at`, `UniqueConstraint(blocker_id, blocked_id)`) — §2.1,
  §2.3.
- `models/report.py`: `ReportReason(StrEnum)` + `Report` (`id`,
  `reporter_id`, `reported_user_id`, `reason`, `created_at`) — §2.2,
  §2.3.
- Re-export trong `app/models/__init__.py`.
- Migration `alembic/versions/*_create_blocked_users_and_reports.py`
  (down_revision = migration F05 mới nhất): tạo 2 bảng + index
  `idx_blocked_users_blocker`, `idx_blocked_users_blocked`,
  `idx_reports_reporter`, `idx_reports_reported`.

**Verify:** 3 test migration pass.

**Refs:** Design §2.1, §2.2, §2.3, §6.6; FR-4, FR-6, FR-7;
DL-F10-03, DL-F10-06, DL-F10-11

---

## 3. `block_service` — block / unblock / list / blocked-ids

_Phụ thuộc Task 2._

**Test trước:** `backend/tests/test_service_block.py` (SQLite, seed
users + friendships, theo tiền lệ `test_service_friend.py`):
- `test_block_deletes_friendship` (FR-4, AC-F10-3).
- `test_block_inserts_row`.
- `test_block_requires_friendship` → `NotFriendsError` (FR-4,
  AC-F10-4).
- `test_block_self_raises` → `SelfBlockError` (DL-F10-11).
- `test_block_idempotent` — block 2 lần → 1 row (DL-F10-03).
- `test_block_is_silent` — không gọi `NotificationService` (FR-5).
- `test_unblock_removes_row` (AC-F10-3).
- `test_unblock_idempotent` (DL-F10-05).
- `test_unblock_does_not_restore_friendship` (DL-F10-05).
- `test_list_blocked_returns_profiles` (DL-F10-09).
- `test_blocked_ids_bidirectional` — ids hai chiều (DL-F10-04).

**Làm:**
- `block_service.py`:
  - Exceptions: `NotFriendsError`, `SelfBlockError`.
  - `block_user(db, *, blocker_id, blocked_id)`: validate self +
    friendship; `friend_service.delete_friendship` + upsert
    `BlockedUser`; **không** gọi notification (DL-F10-03).
  - `unblock_user(db, *, blocker_id, blocked_id)`: xoá row nếu có
    (idempotent — DL-F10-05).
  - `list_blocked(db, blocker_id) -> list[dict]`: JOIN `users`
    (DL-F10-09).
  - `get_blocked_user_ids(db, user_id) -> set`: hai chiều
    (blocked ∪ blocked_by — DL-F10-04).

**Verify:** 11 test service pass.

**Refs:** Design §1.2, §1.3, §4.1, §6.1; FR-4, FR-5, FR-8;
AC-F10-3, AC-F10-4; DL-F10-03, DL-F10-04, DL-F10-05, DL-F10-09,
DL-F10-11

---

## 4. `report_service` + `account_service`

_Phụ thuộc Task 2._

**Test trước:**
- `backend/tests/test_service_report.py`:
  - `test_report_inserts_row` (AC-F10-5).
  - `test_report_invalid_reason` → `InvalidReasonError` (DL-F10-06).
  - `test_report_self_raises` → `SelfReportError`.
  - `test_report_does_not_block` (AC-F10-5).
- `backend/tests/test_service_account.py` (seed user + providers):
  - `test_unlink_removes_provider` (FR-3).
  - `test_unlink_last_provider_raises` → `LastProviderError`
    (AC-F10-2).
  - `test_unlink_not_linked_raises` → `ProviderNotLinkedError`.
  - `test_clear_device_token` — `fcm_token=None` (DL-F10-07).

**Làm:**
- `report_service.py`: `InvalidReasonError`, `SelfReportError`;
  `report_user(db, *, reporter_id, reported_user_id, reason)` →
  insert `Report` (DL-F10-06).
- `account_service.py`: `LastProviderError`,
  `ProviderNotLinkedError`; `unlink_provider(db, *, user_id,
  provider)` guard ≥1 provider còn lại (DL-F10-02);
  `clear_device_token(db, user_id)` (DL-F10-07).

**Verify:** 4 + 4 test service pass.

**Refs:** Design §1.1, §1.4, §1.5, §4.1, §6.2, §6.3; FR-3, FR-6,
FR-7, FR-9; AC-F10-2, AC-F10-5, AC-F10-6;
DL-F10-02, DL-F10-06, DL-F10-07

---

## 5. Điền hook block-aware của `feed_service`

_Phụ thuộc Task 3._

**Test trước:** `backend/tests/test_service_feed_block.py` (seed
posts/recipients + block, theo tiền lệ `test_service_feed.py`):
- `test_feed_excludes_blocked_sender` — A block B → ảnh B biến mất
  khỏi feed A (FR-8, DL-F10-04).
- `test_feed_excludes_when_blocked_by` — B block A → ảnh B vẫn ẩn
  khỏi feed A (hai chiều, DL-F10-04).

**Làm:**
- Sửa thân `feed_service._blocked_sender_ids` để gọi
  `block_service.get_blocked_user_ids(db, viewer_id)` thay vì trả
  `set()` rỗng. **Không** đổi cấu trúc query feed (DL-F10-04,
  DL-F06-03).

**Verify:** 2 test mới pass; toàn bộ test F06 (`test_service_feed*`,
`test_router_feed`) vẫn xanh.

**Refs:** Design §0, §4.1, §6.4; FR-8; DL-F10-04; DL-F06-03

---

## 6. `routers/settings.py` — endpoint `/users/*`

_Phụ thuộc Task 3 và Task 4. Đăng ký router trong `main.py`._

**Test trước:** `backend/tests/test_router_settings.py` (theo tiền lệ
`test_router_friends.py`, override `get_db`):
- `test_block_201`, `test_block_not_friends_422`,
  `test_block_self_422` (AC-F10-3, AC-F10-4).
- `test_unblock_204`, `test_list_blocked_200`.
- `test_report_201`, `test_report_invalid_reason_422` (AC-F10-5).
- `test_unlink_204`, `test_unlink_last_provider_422` (FR-3,
  AC-F10-2).
- `test_logout_204` (AC-F10-6).
- `test_user_not_found_404` (DL-F10-08).

**Làm:**
- `schemas/settings.py`: `BlockRequest {user_id}`, `ReportRequest
  {user_id, reason}`, `BlockedUserItem`, `BlockListResponse {blocked,
  total}`.
- `routers/settings.py` (prefix `/users`, helper `_get_user_id`):
  - `DELETE /providers/{provider}` → `account_service.unlink_provider`;
    map `LastProviderError`→422 `LAST_PROVIDER`,
    `ProviderNotLinkedError`→404 `PROVIDER_NOT_LINKED`.
  - `POST /block` → `block_service.block_user`; map
    `SelfBlockError`→422 `SELF_BLOCK`, `NotFriendsError`→422
    `NOT_FRIENDS`.
  - `DELETE /block/{user_id}` → `unblock_user` → 204.
  - `GET /block` → `list_blocked` → `BlockListResponse`.
  - `POST /report` → `report_service.report_user`; map
    `InvalidReasonError`→422, `SelfReportError`→422 `SELF_REPORT`.
  - `POST /logout` → `account_service.clear_device_token` → 204.
- `main.py`: `app.include_router(settings_router)`.

**Verify:** 11 test router pass.

**Refs:** Design §3, §4.1, §5, §6.5; FR-3, FR-4, FR-6, FR-9;
AC-F10-2, AC-F10-3, AC-F10-4, AC-F10-5, AC-F10-6;
DL-F10-08

---

## 7. `SettingsService` client

_Phụ thuộc Task 1 (client). Độc lập với backend tasks._

**Test trước:** `src/__tests__/settings/SettingsService.test.ts`
(mock `fetch`, `AuthService.getIdToken`):
- `test_block_user_posts` — `POST /users/block` body `{user_id}`.
- `test_unblock_user_deletes` — `DELETE /users/block/{id}`.
- `test_list_blocked_parses` — parse `{blocked,total}` (DL-F10-09).
- `test_report_user_posts` — `POST /users/report` (AC-F10-5).
- `test_unlink_provider_deletes` — `DELETE /users/providers/{p}`.
- `test_logout_posts` — `POST /users/logout`.
- `test_attaches_auth` — header `Authorization: Bearer` (như
  `SocialService`).

**Làm:**
- `SettingsService.ts`: `blockUser`, `unblockUser`, `listBlocked`,
  `reportUser`, `unlinkProvider`, `logout` → endpoints §3; auth
  header qua `AuthService.getIdToken`.
- `__mocks__/SettingsService.ts`: manual mock cho test screen.

**Verify:** 7 test pass.

**Refs:** Design §3, §4.2, §6.7; FR-3, FR-6, FR-8, FR-9;
AC-F10-5; DL-F10-01, DL-F10-09

---

## 8. `AccountLinkRow` + `ReportDialog` components

_Phụ thuộc Task 7._

**Test trước:**
- `src/__tests__/settings/AccountLinkRow.test.tsx` (RNTL):
  - `test_shows_linked_status` — đã link → "Đã liên kết" (FR-1).
  - `test_shows_unlinked_status` — chưa link → nút "Liên kết"
    (FR-1, AC-F10-1).
  - `test_unlink_last_shows_error` — unlink provider cuối → lỗi
    (AC-F10-2).
- `src/__tests__/settings/ReportDialog.test.tsx`:
  - `test_renders_reason_options` — 4 reason cố định (DL-F10-06).
  - `test_submit_calls_report` — gửi → `reportUser` (AC-F10-5).
  - `test_shows_confirmation` — "Cảm ơn bạn đã báo cáo" (AC-F10-5).

**Làm:**
- `components/AccountLinkRow.tsx`: props `{provider, linked,
  isOnlyProvider}`; link → `AuthService.linkWithProvider` +
  `/auth/link`; unlink → `SettingsService.unlinkProvider`; nếu
  `isOnlyProvider` → hiển thị lỗi không cho unlink (AC-F10-2).
- `components/ReportDialog.tsx`: picker 4 reason (DL-F10-06) →
  `SettingsService.reportUser` → confirmation (AC-F10-5).

**Verify:** 3 + 3 test pass.

**Refs:** Design §4.2, §6.8, §6.9; FR-1, FR-2, FR-3, FR-6;
AC-F10-1, AC-F10-2, AC-F10-5; DL-F10-01, DL-F10-02, DL-F10-06

---

## 9. `SettingsScreen`

_Phụ thuộc Task 8._

**Test trước:** `src/__tests__/settings/SettingsScreen.test.tsx`
(mock `SettingsService`, `AuthService`, navigation):
- `test_renders_three_providers` — 3 `AccountLinkRow` (FR-1).
- `test_renders_blocked_list` — danh sách đã chặn + nút bỏ chặn
  (FR-8).
- `test_unblock_calls_service` — bỏ chặn → `SettingsService.
  unblockUser` (AC-F10-3).
- `test_logout_flow` — Đăng xuất → confirm → `logout` + `signOut` +
  clear storage + nav Onboarding (FR-9, FR-10, AC-F10-6).

**Làm:**
- `screens/SettingsScreen.tsx`:
  - Render `AccountLinkRow` cho Apple/Google/Facebook từ
    `providers` (FR-1,2,3).
  - `SettingsService.listBlocked()` → danh sách + nút bỏ chặn
    (FR-8).
  - Nút "Đăng xuất" → confirm → `SettingsService.logout()` +
    `AuthService.signOut()` + clear `LocalStorageService` + nav
    Onboarding (FR-9, FR-10, DL-F10-07).

**Verify:** 4 test pass.

**Refs:** Design §1.1, §1.3, §1.5, §4.2, §6.10; FR-1, FR-2, FR-3,
FR-8, FR-9, FR-10; AC-F10-3, AC-F10-6; DL-F10-07

---

## 10. Integration test — block/report/logout end-to-end

_Phụ thuộc Task 5 và Task 6._

**Test trước = nội dung task:**
`backend/tests/integration/test_block_report_flow.py` (seed users +
friendships, tạo post qua `post_service`):
- `test_block_then_feed_hidden` — A,B bạn bè; B gửi ảnh cho A → A
  block B → `GET /feed` của A không còn ảnh B (AC-F10-3, FR-8).
- `test_block_then_not_friends` — block → `GET /friends` của A không
  còn B (AC-F10-3, DL-F10-10).
- `test_report_persists` — report B → row `reports` tồn tại; B vẫn
  bình thường (AC-F10-5).

**Verify:** 3 integration test pass.

**Refs:** Design §6.11, §6.12; FR-4, FR-7, FR-8; AC-F10-3, AC-F10-5;
DL-F10-04, DL-F10-10

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **Liên kết (link)** dùng lại `POST /auth/link` (F01) — không tạo
  endpoint link mới; test link thuộc F01 (DL-F10-01).
- **Firebase unlink/signOut + clear secure storage native**: client
  chỉ verify gọi đúng `AuthService`/`SettingsService`; phần native
  không unit-test (DL-F10-02, DL-F10-07).
- **Gửi FCM thực + daily reminder**: thuộc F09; F10 chỉ đảm bảo
  block là **silent** (FR-5).
- **Privacy nâng cao, hide post/user, xoá tài khoản, cache
  cleaning**: Non-goals — ngoài phạm vi MVP.
