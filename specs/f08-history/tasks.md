# F08 — History / Timeline — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** FastAPI (backend) + React Native/TypeScript (client).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F08 là feature **đọc-only** trên dữ liệu F05/F07 (DL-F08-01).
> Không thêm migration (DL-F08-02). Filter 24h bằng
> `expires_at > now()` (DL-F08-03). Tái dùng cursor + block hook của
> `feed_service` (DL-F08-04, DL-F08-06). Gắn `SeenByList` của F07
> vào full-screen "Đã gửi" (DL-F08-08).

---

## 1. Bootstrap F08 structure + test runner

_Tiên quyết cho mọi task. Không có dependency ngoài._

**Làm:**
- Tạo file skeleton backend (`raise NotImplementedError`/`pass`):
  ```
  backend/app/schemas/history.py
  backend/app/services/history_service.py
  backend/app/routers/history.py
  backend/tests/test_service_history_sent.py
  backend/tests/test_service_history_received.py
  backend/tests/test_service_history_cursor.py
  backend/tests/test_router_history.py
  backend/tests/integration/test_history_flow.py
  ```
- Tạo file skeleton client:
  ```
  src/services/HistoryService.ts
  src/services/__mocks__/HistoryService.ts
  src/components/HistoryList.tsx
  src/screens/HistoryScreen.tsx
  src/__tests__/history/HistoryService.test.ts
  src/__tests__/history/HistoryList.test.tsx
  src/__tests__/history/HistoryScreen.test.tsx
  ```
- Định nghĩa interface client: `SentHistoryItem`,
  `ReceivedHistoryItem`, `HistoryResult<TItem>` (Design §2.1).

**Verify:** `pytest --collect-only` thấy 5 file test backend mới;
`npx jest --listTests` liệt kê 3 file test client mới;
`npx tsc --noEmit` không lỗi type.

**Refs:** Design §4.1, §4.2

---

## 2. `history_service.get_sent` — ảnh đã gửi + đếm seen/recipient

_Phụ thuộc Task 1._

**Test trước:** `backend/tests/test_service_history_sent.py` (SQLite
+ `Base.metadata.create_all`, seed users/friendships/posts/
recipients theo tiền lệ `test_service_post.py`):
- `test_sent_returns_authored_posts` — viewer là author → thấy;
  post người khác → không (FR-2).
- `test_sent_orders_newest_first` — `created_at` giảm dần (FR-2,
  AC-F08-1).
- `test_sent_excludes_expired` — `expires_at <= now()` bị ẩn (FR-4,
  AC-F08-1).
- `test_sent_counts_recipients_and_seen` — `recipient_count`/
  `seen_count` đúng (FR-3, FR-5, DL-F08-05).
- `test_sent_zero_recipients` — post 0 người nhận → cả hai count
  = 0, vẫn trả.
- `test_sent_empty_when_none` — chưa gửi gì → `items=[]`
  (AC-F08-4).

**Làm:**
- `history_service.py`:
  - Import `_blocked_sender_ids`, `_encode_cursor`,
    `_decode_cursor`, `InvalidCursorError`, `FEED_PAGE_SIZE`,
    `FEED_MAX_PAGE_SIZE` từ `feed_service` (DL-F08-04).
  - `get_sent(db, *, viewer_id, cursor=None, limit=FEED_PAGE_SIZE)`:
    SELECT `posts` WHERE `user_id == viewer` AND
    `expires_at > now()`; LEFT JOIN `post_recipients`; GROUP BY
    `posts.id`; `recipient_count = count(pr.id)`,
    `seen_count = count(pr.seen_at)`; ORDER `created_at DESC,
    posts.id DESC`; map mỗi row → dict item (§2.1). (Cursor xử lý ở
    Task 4 — task này lấy trang đầu.)

**Verify:** 6 test sent pass.

**Refs:** Design §1.1, §1.2, §2, §3.1, §4.1; FR-2, FR-3, FR-4, FR-5;
AC-F08-1, AC-F08-4; DL-F08-01, DL-F08-03, DL-F08-05

---

## 3. `history_service.get_received` — ảnh đã nhận + cờ seen

_Phụ thuộc Task 1. Độc lập với Task 2._

**Test trước:** `backend/tests/test_service_history_received.py`:
- `test_received_returns_received_posts` — viewer là recipient →
  thấy; non-recipient → không (FR-2).
- `test_received_orders_newest_first` — `created_at` giảm dần
  (AC-F08-1).
- `test_received_excludes_expired` — `expires_at <= now()` bị ẩn
  (FR-4, AC-F08-1).
- `test_received_seen_flag` — `seen_at` null → `seen=False`; có →
  `seen=True` (DL-F06-09).
- `test_received_includes_sender_and_pet` — item có
  `sender_display_name`, `pet_name`.
- `test_received_excludes_blocked_sender` — sender trong
  `_blocked_sender_ids` bị loại (DL-F08-06; hook rỗng = no-op).
- `test_received_empty_when_none` — chưa nhận gì → `items=[]`
  (AC-F08-4).

**Làm:**
- `history_service.py`:
  - `get_received(db, *, viewer_id, cursor=None,
    limit=FEED_PAGE_SIZE)`: như `feed_service.get_feed` — JOIN
    `posts`↔`post_recipients`(viewer)↔`users`, LEFT JOIN
    `pet_profiles`; WHERE `expires_at > now()` AND sender ∉
    `_blocked_sender_ids`; ORDER `created_at DESC, posts.id DESC`;
    map mỗi row → dict item với `seen = seen_at is not None`
    (§2.1). (Cursor ở Task 4.)

**Verify:** 7 test received pass.

**Refs:** Design §1.1, §1.2, §2, §3.2, §4.1; FR-2, FR-4;
AC-F08-1, AC-F08-4; DL-F08-03, DL-F08-06

---

## 4. `history_service` cursor pagination (sent + received)

_Phụ thuộc Task 2 và Task 3._

**Test trước:** `backend/tests/test_service_history_cursor.py`:
- `test_sent_first_page_limit` — `limit=N` → ≤ N item +
  `next_cursor` khi còn dữ liệu.
- `test_sent_second_page_continues` — trang sau (cursor) chỉ chứa
  post cũ hơn, không trùng (DL-F08-04).
- `test_received_invalid_cursor_raises` — cursor hỏng →
  `InvalidCursorError` (DL-F08-04).
- `test_limit_clamped_to_max` — `limit > FEED_MAX_PAGE_SIZE` →
  clamp.

**Làm:**
- `history_service.py`: trong cả `get_sent` và `get_received`:
  - clamp `limit` về `FEED_MAX_PAGE_SIZE`;
  - nếu có `cursor`, `_decode_cursor` + thêm filter
    `(created_at, id)` "nhỏ hơn" theo DESC;
  - lấy `limit + 1` row để xác định `next_cursor`
    (`_encode_cursor` của item cuối) → trả `(items, next_cursor)`.

**Verify:** 4 test cursor pass (Task 2, 3 vẫn xanh).

**Refs:** Design §1.5, §2.2, §3.1, §3.2, §4.1; Technical Constraint
(cursor pagination); DL-F08-04

---

## 5. `routers/history.py` — `GET /history/sent` + `GET /history/received`

_Phụ thuộc Task 4. Đăng ký router trong `main.py`._

**Test trước:** `backend/tests/test_router_history.py` (theo tiền lệ
`test_router_feed.py`, seed service):
- `test_sent_200` — 200 + `{ items, next_cursor }` đúng schema
  (AC-F08-2).
- `test_received_200` — 200 + `{ items, next_cursor }` đúng schema
  (AC-F08-2).
- `test_sent_user_not_found_404` — viewer chưa có row → 404
  `USER_NOT_FOUND` (DL-F08-07).
- `test_received_user_not_found_404` — viewer chưa có row → 404
  `USER_NOT_FOUND`.
- `test_invalid_cursor_400` — cursor hỏng → 400 `INVALID_CURSOR`.
- `test_sent_empty_200` — chưa gửi gì → 200 `items=[]` (AC-F08-4).

**Làm:**
- `schemas/history.py`: `SentHistoryItemResponse`,
  `ReceivedHistoryItemResponse` (đúng §2.1),
  `SentHistoryResponse { items, next_cursor }`,
  `ReceivedHistoryResponse { items, next_cursor }`.
- `routers/history.py` (prefix `/history`):
  - `_get_user_id` (như `routers/feed.py`); None → 404
    `USER_NOT_FOUND`.
  - `GET "/sent"` → query params `cursor`, `limit`; gọi
    `history_service.get_sent`; bắt `InvalidCursorError` → 400
    `INVALID_CURSOR`; trả `SentHistoryResponse`.
  - `GET "/received"` → tương tự với `get_received` →
    `ReceivedHistoryResponse`.
- `main.py`: `app.include_router(history_router)`.

**Verify:** 6 test router pass.

**Refs:** Design §3.1, §3.2, §4.1, §5; FR-1, FR-2;
AC-F08-2, AC-F08-4; DL-F08-04, DL-F08-07

---

## 6. `HistoryService` client — `getSent` + `getReceived`

_Phụ thuộc Task 1 (client). Độc lập với backend tasks._

**Test trước:** `src/__tests__/history/HistoryService.test.ts`
(mock `fetch`, `AuthService.getIdToken`):
- `test_get_sent_returns_items` — gọi `GET /history/sent`, parse
  `items/next_cursor` (AC-F08-2).
- `test_get_received_returns_items` — gọi `GET /history/received`,
  parse kết quả (AC-F08-2).
- `test_history_passes_cursor` — có cursor → query `?cursor=`
  (DL-F08-04).
- `test_history_attaches_auth` — header `Authorization: Bearer`
  (như `FeedService`).

**Làm:**
- `HistoryService.ts`:
  - `getSent(cursor?: string): Promise<HistoryResult<SentHistoryItem>>`
    → `GET /history/sent` (+ `?cursor=` nếu có), auth header qua
    `AuthService.getIdToken`.
  - `getReceived(cursor?: string):
    Promise<HistoryResult<ReceivedHistoryItem>>` →
    `GET /history/received`, parse kết quả.
- `__mocks__/HistoryService.ts`: manual mock cho test screen.

**Verify:** 4 test pass.

**Refs:** Design §1.1, §2.1, §4.2, §5; FR-1, FR-2; AC-F08-2;
DL-F08-04

---

## 7. `HistoryList` component (section "Đã gửi" / "Đã nhận")

_Phụ thuộc Task 1 (client). Tái dùng `formatRelativeTime` (F06)._

**Test trước:** `src/__tests__/history/HistoryList.test.tsx` (RNTL):
- `test_sent_renders_seen_over_total` — mode sent → hiển thị
  "{seen_count}/{recipient_count}" (FR-3, FR-5).
- `test_received_renders_sender` — mode received → hiển thị tên
  người gửi + pet (FR-3).
- `test_empty_section_label` — `items=[]` → nhãn rỗng của section.

**Làm:**
- `components/HistoryList.tsx`: nhận `{ title, items, mode,
  onOpen }`; render tiêu đề section + danh sách ảnh.
  - `mode="sent"`: mỗi item hiển thị ảnh CDN +
    "{seen_count}/{recipient_count} đã xem" +
    `formatRelativeTime(created_at)` (FR-3, FR-5).
  - `mode="received"`: ảnh CDN + tên người gửi + pet + cờ `seen`
    (FR-3).
  - `items=[]` → nhãn rỗng riêng của section.

**Verify:** 3 test pass.

**Refs:** Design §4.2; FR-3, FR-5; AC-F08-2, AC-F08-3; DL-F08-05

---

## 8. `HistoryScreen` — 2 section + refresh + empty + open→seen

_Phụ thuộc Task 6 và Task 7. Tái dùng `SeenService`/`SeenByList`
(F07)._

**Test trước:** `src/__tests__/history/HistoryScreen.test.tsx`
(mock `HistoryService`, `SeenService`):
- `test_loads_both_sections_on_mount` — mount → `getSent` +
  `getReceived` được gọi (FR-1).
- `test_renders_two_sections` — hiển thị "Đã gửi" và "Đã nhận"
  (FR-3, AC-F08-2).
- `test_empty_state_when_both_empty` — cả hai rỗng → empty state
  (FR-6, AC-F08-4).
- `test_open_sent_shows_seen_by_list` — tap ảnh đã gửi →
  `SeenService.getSeenBy` được gọi + render `SeenByList` (FR-5,
  AC-F08-3, DL-F08-08).
- `test_open_received_marks_seen` — tap ảnh đã nhận →
  `SeenService.markSeen` được gọi (FR-5).

**Làm:**
- `screens/HistoryScreen.tsx`:
  - `useEffect` → `HistoryService.getSent()` +
    `getReceived()` lưu state (FR-1).
  - Render 2 section qua `HistoryList` ("Đã gửi" / "Đã nhận")
    (FR-3).
  - `refreshing` + `onRefresh` → reload cả hai section.
  - Empty state khi cả hai `items.length === 0` (FR-6).
  - Tap ảnh → full-screen: sent → `SeenService.getSeenBy(post_id)`
    + `<SeenByList/>` (FR-5, DL-F08-08); received →
    `SeenService.markSeen(post_id)` + hiển thị thông tin người gửi.

**Verify:** 5 test pass.

**Refs:** Design §1.1, §1.3, §1.4, §4.2; FR-1, FR-3, FR-5, FR-6;
AC-F08-2, AC-F08-3, AC-F08-4; DL-F08-08

---

## 9. Integration test — end-to-end history flow

_Phụ thuộc Task 5 (router + service)._

**Test trước = nội dung task:**
`backend/tests/integration/test_history_flow.py` (theo tiền lệ
`tests/integration/`, seed users + friendships, tạo post qua
`post_service`, mark seen qua `seen_service`, đọc qua API):
- `test_sent_photo_appears_in_sent_history` — A gửi cho B →
  `GET /history/sent` của A chứa post (AC-F08-2).
- `test_received_photo_appears_in_received_history` — A gửi cho B →
  `GET /history/received` của B chứa post (AC-F08-2).
- `test_expired_photo_hidden_in_history` — post `expires_at` quá
  khứ → không trong cả hai (AC-F08-1).
- `test_sent_seen_count_reflects_viewers` — B xem ảnh A →
  `seen_count` của A = 1 (FR-5, AC-F08-3).

**Verify:** 4 integration test pass.

**Refs:** Design §6.8, §6.9; FR-2, FR-5;
AC-F08-1, AC-F08-2, AC-F08-3; DL-F08-01, DL-F08-05

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **`SeenByList` render độc lập + `SeenService`** (markSeen/
  getSeenBy): hiện thực + test ở **F07**; F08 chỉ **gắn** vào
  full-screen "Đã gửi"/"Đã nhận" (DL-F07-06, DL-F08-08).
- **Loại trừ block thực**: bảng `blocked_users` + điền
  `_blocked_sender_ids` thuộc **F10**; F08 received chỉ tái dùng
  hook rỗng (DL-F08-06).
- **Tải/cache ảnh CDN native + full-screen viewer hoàn chỉnh**: task
  triển khai native sau (kế thừa DL-F06-07).
- **Migration / schema**: F08 không tạo bảng/cột nào; đọc
  `posts`/`post_recipients`/`users`/`pet_profiles` (DL-F08-02).
- **History >24h / premium / download / "On this day"**: ngoài MVP
  (Non-goals).
