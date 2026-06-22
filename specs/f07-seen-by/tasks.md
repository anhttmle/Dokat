# F07 — Seen By — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** FastAPI (backend) + React Native/TypeScript (client).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F07 ghi/đọc `post_recipients.seen_at` (do F05 tạo) — **không**
> thêm migration (DL-F07-07). `mark_seen` idempotent, first-seen
> wins (DL-F07-02). F07 điền hook `FeedService.markSeen` (DL-F07-05);
> gắn `SeenByList` vào History thuộc F08 (DL-F07-06).

---

## 1. Bootstrap F07 structure + test runner

_Tiên quyết cho mọi task. Không có dependency ngoài._

**Làm:**
- Tạo file skeleton backend (`raise NotImplementedError`/`pass`):
  ```
  backend/app/schemas/seen.py
  backend/app/services/seen_service.py
  backend/app/routers/seen.py
  backend/tests/test_service_seen.py
  backend/tests/test_router_seen.py
  backend/tests/integration/test_seen_flow.py
  ```
- Tạo file skeleton client:
  ```
  src/services/SeenService.ts
  src/services/__mocks__/SeenService.ts
  src/components/SeenByList.tsx
  src/__tests__/seen/SeenService.test.ts
  src/__tests__/seen/SeenByList.test.tsx
  src/__tests__/seen/FeedServiceMarkSeen.test.ts
  ```
- Định nghĩa interface client: `SeenViewer`, `SeenByResult`
  (Design §2.1).

**Verify:** `pytest --collect-only` thấy 3 file test backend mới;
`npx jest --listTests` liệt kê 3 file test client mới;
`npx tsc --noEmit` không lỗi type.

**Refs:** Design §4.1, §4.2

---

## 2. `seen_service.mark_seen` — đánh dấu đã xem (idempotent)

_Phụ thuộc Task 1._

**Test trước:** `backend/tests/test_service_seen.py` (SQLite +
`Base.metadata.create_all`, seed users/friendships/posts/recipients
theo tiền lệ `test_service_post.py`):
- `test_mark_seen_sets_seen_at` — recipient mark → `seen_at` được
  đặt (FR-1, FR-2, AC-F07-1).
- `test_mark_seen_idempotent` — mark lần 2 → `seen_at` không đổi
  (first-seen wins) (AC-F07-3, DL-F07-02).
- `test_mark_seen_non_recipient_raises` — viewer không phải
  recipient → `NotRecipientError` (DL-F07-03).
- `test_mark_seen_post_not_found_raises` — post không tồn tại →
  `PostNotFoundError`.

**Làm:**
- `seen_service.py`:
  - Exceptions `PostNotFoundError`, `NotRecipientError`,
    `NotSenderError`.
  - `mark_seen(db, *, post_id, viewer_id) -> datetime`: nạp post
    (thiếu → `PostNotFoundError`); nạp edge
    `post_recipients(post_id, viewer_id)` (thiếu → `NotRecipientError`);
    nếu `seen_at is None` → set `now()` + commit; trả `seen_at`.

**Verify:** 4 test mark-seen pass.

**Refs:** Design §1.1, §1.3, §2, §4.1; FR-1, FR-2, FR-6;
AC-F07-1, AC-F07-3; DL-F07-01, DL-F07-02, DL-F07-03

---

## 3. `seen_service.get_seen_by` — danh sách + đếm người xem

_Phụ thuộc Task 2._

**Test trước:** `backend/tests/test_service_seen.py` (bổ sung):
- `test_seen_by_lists_viewers` — trả recipients đã xem +
  `display_name`/`avatar_url`/`seen_at` (FR-3).
- `test_seen_by_count_aggregates` — nhiều người xem → `seen_count`
  đúng (FR-4).
- `test_seen_by_excludes_unseen` — recipient chưa xem → không trong
  `viewers`, không tính count.
- `test_seen_by_orders_recent_first` — `viewers` sắp theo `seen_at`
  giảm dần.
- `test_seen_by_not_sender_raises` — viewer không phải sender →
  `NotSenderError` (DL-F07-04).
- `test_seen_by_empty_when_nobody_seen` — chưa ai xem →
  `seen_count=0`, `viewers=[]`.

**Làm:**
- `seen_service.py`:
  - `get_seen_by(db, *, post_id, viewer_id) -> (list, int)`: nạp
    post (thiếu → `PostNotFoundError`); nếu
    `post.user_id != viewer_id` → `NotSenderError` (DL-F07-04);
    SELECT `post_recipients` của post có `seen_at IS NOT NULL` JOIN
    `users`, sắp `seen_at DESC`; map mỗi row → dict viewer; trả
    `(viewers, len(viewers))` (DL-F07-08).

**Verify:** 6 test seen-by pass (Task 2 vẫn xanh).

**Refs:** Design §1.2, §2, §4.1; FR-3, FR-4, FR-5;
AC-F07-2; DL-F07-04, DL-F07-08

---

## 4. `routers/seen.py` — `POST /posts/{id}/seen` + `GET /posts/{id}/seen-by`

_Phụ thuộc Task 3. Đăng ký router trong `main.py`._

**Test trước:** `backend/tests/test_router_seen.py` (theo tiền lệ
`test_router_posts.py`, seed service):
- `test_mark_seen_200` — 200 + `{ post_id, seen_at }` (AC-F07-1).
- `test_mark_seen_idempotent_200` — gọi 2 lần → cùng `seen_at`,
  vẫn 200 (AC-F07-3).
- `test_mark_seen_non_recipient_403` — 403 `NOT_RECIPIENT`.
- `test_mark_seen_post_not_found_404` — 404 `POST_NOT_FOUND`.
- `test_mark_seen_user_not_found_404` — viewer chưa có row → 404
  `USER_NOT_FOUND` (DL-F07-09).
- `test_seen_by_200` — sender → 200 + `{ post_id, seen_count,
  viewers }` (AC-F07-2).
- `test_seen_by_not_sender_403` — 403 `FORBIDDEN` (DL-F07-04).
- `test_seen_by_post_not_found_404` — 404 `POST_NOT_FOUND`.
- `test_seen_by_empty_200` — chưa ai xem → 200 `seen_count=0`.

**Làm:**
- `schemas/seen.py`: `SeenResponse { post_id, seen_at }`;
  `SeenViewerResponse` (đúng §2.1);
  `SeenByResponse { post_id, seen_count, viewers }`.
- `routers/seen.py` (prefix `/posts`):
  - `POST "/{post_id}/seen"` → resolve viewer (`_get_user_id` như
    `routers/posts.py`; None → 404 `USER_NOT_FOUND`); gọi
    `seen_service.mark_seen`; map `PostNotFoundError` → 404,
    `NotRecipientError` → 403 `NOT_RECIPIENT`; trả `SeenResponse`.
  - `GET "/{post_id}/seen-by"` → resolve viewer; gọi
    `seen_service.get_seen_by`; map `PostNotFoundError` → 404,
    `NotSenderError` → 403 `FORBIDDEN`; trả `SeenByResponse`.
- `main.py`: `app.include_router(seen_router)`.

**Verify:** 9 test router pass.

**Refs:** Design §3.1, §3.2, §4.1, §5; FR-1, FR-3;
AC-F07-1, AC-F07-2, AC-F07-3; DL-F07-03, DL-F07-04, DL-F07-09

---

## 5. `SeenService` client + nối hook `FeedService.markSeen`

_Phụ thuộc Task 1 (client). Độc lập với backend tasks._

**Test trước:**
- `src/__tests__/seen/SeenService.test.ts` (mock `fetch`,
  `AuthService.getIdToken`):
  - `test_mark_seen_posts_to_endpoint` — `markSeen(id)` →
    `POST /posts/{id}/seen` (AC-F07-1).
  - `test_mark_seen_attaches_auth` — header `Authorization: Bearer`.
  - `test_get_seen_by_returns_result` — `getSeenBy(id)` → parse
    `{ post_id, seen_count, viewers }` (AC-F07-2).
  - `test_get_seen_by_attaches_auth` — header `Authorization: Bearer`.
- `src/__tests__/seen/FeedServiceMarkSeen.test.ts` (mock
  `SeenService`):
  - `test_feed_mark_seen_delegates_to_seen_service` —
    `FeedService.markSeen(id)` gọi `SeenService.markSeen(id)`
    (DL-F07-05).

**Làm:**
- `SeenService.ts`:
  - `markSeen(postId): Promise<void>` → `POST /posts/{id}/seen`,
    auth header qua `AuthService.getIdToken`.
  - `getSeenBy(postId): Promise<SeenByResult>` →
    `GET /posts/{id}/seen-by`, parse kết quả.
- `FeedService.markSeen` (sửa): thay thân no-op (DL-F06-02) bằng
  `SeenService.markSeen(postId)`; giữ nguyên signature (DL-F07-05).
- `__mocks__/SeenService.ts`: manual mock cho test component.

**Verify:** 4 + 1 test pass; test F06 (`FeedService.test.ts`,
`FeedScreen.test.tsx`) vẫn xanh.

**Refs:** Design §1.1, §1.2, §4.2, §5; FR-1, FR-3, FR-4;
AC-F07-1, AC-F07-2; DL-F07-05

---

## 6. `SeenByList` component

_Phụ thuộc Task 1 (client)._

**Test trước:** `src/__tests__/seen/SeenByList.test.tsx` (RNTL):
- `test_renders_seen_count` — `seen_count=2` → "2 người đã xem"
  (FR-4, AC-F07-2).
- `test_renders_viewer_names` — liệt kê `display_name` từng viewer
  (FR-3, AC-F07-2).
- `test_empty_state_no_viewers` — `viewers=[]` → "Chưa có ai xem".

**Làm:**
- `components/SeenByList.tsx`: nhận `SeenByResult` (prop); render
  "{seen_count} người đã xem" (FR-4) + danh sách tên/avatar (FR-3);
  rỗng → empty state. Component thuần hiển thị; F08 chịu trách
  nhiệm gọi `SeenService.getSeenBy` + gắn vào History (DL-F07-06).

**Verify:** 3 test pass.

**Refs:** Design §4.2; FR-3, FR-4; AC-F07-2; DL-F07-06

---

## 7. Integration test — end-to-end seen flow

_Phụ thuộc Task 4 (router + service)._

**Test trước = nội dung task:**
`backend/tests/integration/test_seen_flow.py` (theo tiền lệ
`tests/integration/`, seed users + friendships, tạo post qua
`post_service`, mark seen + đọc seen-by qua API):
- `test_recipient_seen_appears_for_sender` — B xem ảnh A →
  `GET seen-by` của A chứa B (AC-F07-1, AC-F07-2).
- `test_seen_no_duplicate_on_repeat` — B xem 2 lần → `seen_count`
  vẫn 1 (AC-F07-3).
- `test_multiple_viewers_counted` — B, C xem; D chưa →
  `seen_count=2`, D không có (AC-F07-2).
- `test_non_sender_cannot_view_seen_by` — B gọi `seen-by` của A →
  403 (DL-F07-04).

**Verify:** 4 integration test pass.

**Refs:** Design §6.6, §6.7; FR-2, FR-3, FR-4;
AC-F07-1, AC-F07-2, AC-F07-3; DL-F07-02, DL-F07-04

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **Gắn `SeenByList` vào màn hình History** + filter 24h: thuộc
  **F08** (DL-F07-06); F07 chỉ cung cấp component + `SeenService`.
- **Optimistic UI khi mở full-screen**: đã hiện thực + test ở
  **F06** (`test_open_marks_seen`); F07 chỉ nối hook
  `FeedService.markSeen` → `SeenService.markSeen` (DL-F07-05).
- **Migration / schema**: F07 không tạo bảng/cột nào; ghi/đọc
  `post_recipients.seen_at` của F05 (DL-F07-07). Ràng buộc unique
  pair đã test ở F05.
- **Reaction / comment / reply / notify từng lần seen**: ngoài MVP
  (Non-goals).
