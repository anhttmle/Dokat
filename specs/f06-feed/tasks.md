# F06 — Feed & App View — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** FastAPI (backend) + React Native/TypeScript (client).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F06 là feature **đọc-only** trên dữ liệu F05 (DL-F06-01). Không
> thêm migration (DL-F06-06). Persist seen thuộc F07 (DL-F06-02);
> loại trừ block thực thuộc F10 (DL-F06-03).

---

## 1. Bootstrap F06 structure + test runner

_Tiên quyết cho mọi task. Không có dependency ngoài._

**Làm:**
- Tạo file skeleton backend (`raise NotImplementedError`/`pass`):
  ```
  backend/app/schemas/feed.py
  backend/app/services/feed_service.py
  backend/app/routers/feed.py
  backend/tests/test_service_feed.py
  backend/tests/test_service_feed_cursor.py
  backend/tests/test_router_feed.py
  backend/tests/integration/test_feed_flow.py
  ```
- Tạo file skeleton client:
  ```
  src/services/FeedService.ts
  src/services/__mocks__/FeedService.ts
  src/components/FeedItem.tsx
  src/components/relativeTime.ts
  src/screens/FeedScreen.tsx
  src/__tests__/feed/FeedService.test.ts
  src/__tests__/feed/relativeTime.test.ts
  src/__tests__/feed/FeedItem.test.tsx
  src/__tests__/feed/FeedScreen.test.tsx
  ```
- Định nghĩa interface client: `FeedItem`, `FeedResult` (Design
  §2.1).

**Verify:** `pytest --collect-only` thấy 4 file test backend mới;
`npx jest --listTests` liệt kê 4 file test client mới;
`npx tsc --noEmit` không lỗi type.

**Refs:** Design §4.1, §4.2

---

## 2. `feed_service.get_feed` — query, filter, seen, metadata

_Phụ thuộc Task 1._

**Test trước:** `backend/tests/test_service_feed.py` (SQLite +
`Base.metadata.create_all`, seed users/friendships/posts/recipients
+ pet_profiles, theo tiền lệ `test_service_post.py`):
- `test_feed_returns_received_posts` — viewer là recipient → thấy;
  non-recipient → không (FR-2).
- `test_feed_orders_newest_first` — `created_at` giảm dần
  (AC-F06-1, AC-F06-6).
- `test_feed_excludes_expired` — `expires_at <= now()` bị ẩn (FR-3,
  AC-F06-2).
- `test_feed_seen_flag` — `seen_at` null → `seen=False`; có giá trị
  → `seen=True` (FR-6, DL-F06-09).
- `test_feed_includes_sender_and_pet` — item có
  `sender_display_name`, `pet_name` (FR-4).
- `test_feed_pet_name_null_when_no_pet` — sender chưa có pet →
  `pet_name=None` (FR-4).
- `test_feed_empty_when_no_received` — viewer chưa nhận → `[]`
  (AC-F06-4).
- `test_feed_excludes_blocked_sender` — sender trong
  `_blocked_sender_ids` bị loại (FR-10; hook rỗng = no-op).

**Làm:**
- `feed_service.py`:
  - Hằng `FEED_PAGE_SIZE = 20`, `FEED_MAX_PAGE_SIZE = 50`.
  - `_blocked_sender_ids(db, viewer_id) -> set` → `set()` (hook F10
    — DL-F06-03).
  - `get_feed(db, *, viewer_id, cursor=None, limit=FEED_PAGE_SIZE)`:
    JOIN `posts`↔`post_recipients`(viewer)↔`users`, LEFT JOIN
    `pet_profiles`; WHERE `expires_at > now()` AND sender ∉
    blocked; ORDER `created_at DESC, posts.id DESC`; map mỗi row →
    dict item với `seen = seen_at is not None`. (Cursor xử lý ở
    Task 3 — task này lấy trang đầu, không cursor.)

**Verify:** 8 test service pass.

**Refs:** Design §1.1, §2, §4.1; FR-2, FR-3, FR-4, FR-6, FR-10;
AC-F06-1, AC-F06-2, AC-F06-4, AC-F06-6;
DL-F06-01, DL-F06-03, DL-F06-04, DL-F06-09

---

## 3. `feed_service` cursor pagination

_Phụ thuộc Task 2._

**Test trước:** `backend/tests/test_service_feed_cursor.py`:
- `test_feed_first_page_limit` — `limit=N` → ≤ N item +
  `next_cursor` khi còn dữ liệu.
- `test_feed_second_page_continues` — trang sau (cursor) chỉ chứa
  post cũ hơn, không trùng trang đầu (DL-F06-08).
- `test_feed_last_page_cursor_none` — trang cuối → `next_cursor`
  None.
- `test_feed_invalid_cursor_raises` — cursor hỏng →
  `InvalidCursorError` (DL-F06-08).
- `test_feed_limit_clamped_to_max` — `limit > FEED_MAX_PAGE_SIZE` →
  clamp.

**Làm:**
- `feed_service.py`:
  - `class InvalidCursorError(Exception)`.
  - `_encode_cursor(created_at, post_id) -> str` (base64 JSON);
    `_decode_cursor(cursor) -> (datetime, uuid)` → sai →
    `InvalidCursorError`.
  - Trong `get_feed`: clamp `limit` về `FEED_MAX_PAGE_SIZE`; nếu có
    `cursor`, thêm filter `(created_at, id)` "nhỏ hơn" theo DESC;
    lấy `limit + 1` row để xác định `next_cursor` (item thứ
    `limit+1` → còn trang) → trả `(items, next_cursor)`.

**Verify:** 5 test cursor pass (Task 2 vẫn xanh).

**Refs:** Design §1.3, §2.2, §3.1, §4.1; Technical Constraint
(cursor pagination); DL-F06-08

---

## 4. `routers/feed.py` — `GET /feed`

_Phụ thuộc Task 3. Đăng ký router trong `main.py`._

**Test trước:** `backend/tests/test_router_feed.py` (theo tiền lệ
`test_router_posts.py`, mock/seed service):
- `test_feed_200` — 200 + `{ items, next_cursor }` đúng schema.
- `test_feed_user_not_found_404` — viewer chưa có row → 404
  `USER_NOT_FOUND` (DL-F06-05).
- `test_feed_invalid_cursor_400` — cursor hỏng → 400
  `INVALID_CURSOR`.
- `test_feed_empty_200` — feed rỗng → 200 `items=[]` (AC-F06-4).

**Làm:**
- `schemas/feed.py`: `FeedItemResponse` (đúng §2.1),
  `FeedResponse { items: list[FeedItemResponse], next_cursor:
  str | None }`.
- `routers/feed.py` (prefix `/feed`):
  - `GET ""` → resolve viewer (`_get_user_id` như
    `routers/posts.py`); None → 404 `USER_NOT_FOUND`.
  - Query params `cursor: str | None`, `limit: int | None`.
  - Gọi `feed_service.get_feed`; bắt `InvalidCursorError` → 400
    `INVALID_CURSOR`; trả `FeedResponse`.
- `main.py`: `app.include_router(feed_router)`.

**Verify:** 4 test router pass.

**Refs:** Design §3.1, §4.1, §5; FR-1; AC-F06-4;
DL-F06-05, DL-F06-08

---

## 5. `FeedService` client — `getFeed` + `markSeen` hook

_Phụ thuộc Task 1 (client). Độc lập với backend tasks._

**Test trước:** `src/__tests__/feed/FeedService.test.ts`
(mock `fetch`, `AuthService.getIdToken`):
- `test_get_feed_returns_items` — gọi `GET /feed`, parse
  `items/next_cursor` (AC-F06-1).
- `test_get_feed_passes_cursor` — có cursor → query `?cursor=`
  (DL-F06-08).
- `test_get_feed_attaches_auth` — header `Authorization: Bearer`
  (như `SocialService`).
- `test_mark_seen_calls_hook` — `markSeen(id)` gọi đúng điểm tích
  hợp F07 (DL-F06-02).

**Làm:**
- `FeedService.ts`:
  - `getFeed(cursor?: string): Promise<FeedResult>` → `GET /feed`
    (+ `?cursor=` nếu có), auth header qua `AuthService.getIdToken`.
  - `markSeen(postId: string): Promise<void>` — điểm tích hợp F07
    (DL-F06-02); F06 chỉ định nghĩa boundary (no-op/stub network),
    để F07 cắm `POST /posts/{id}/seen`.
- `__mocks__/FeedService.ts`: manual mock cho test screen.

**Verify:** 4 test pass.

**Refs:** Design §1.1, §2.1, §4.2, §5; FR-1, FR-5;
AC-F06-1; DL-F06-02, DL-F06-08

---

## 6. `relativeTime` util + `FeedItem` component

_Phụ thuộc Task 1 (client)._

**Test trước:**
- `src/__tests__/feed/relativeTime.test.ts`:
  - `test_just_now` — < 1 phút → "vừa xong".
  - `test_minutes_ago` — 3 phút → "3 phút trước" (AC-F06-1).
  - `test_hours_ago` — 2 giờ → "2 giờ trước".
- `src/__tests__/feed/FeedItem.test.tsx` (RNTL):
  - `test_renders_sender_and_pet` — hiển thị tên sender + pet
    (FR-4).
  - `test_unseen_indicator` — `seen=false` → indicator "chưa xem"
    (FR-6, AC-F06-3).
  - `test_seen_no_indicator` — `seen=true` → không indicator
    (AC-F06-3).

**Làm:**
- `components/relativeTime.ts`: `formatRelativeTime(iso, now)` pure
  → chuỗi tiếng Việt (DL-F06-07).
- `components/FeedItem.tsx`: nhận `FeedItem` prop; render ảnh CDN +
  placeholder (FR-8), tên sender + pet (FR-4),
  `formatRelativeTime(created_at)`, indicator theo `seen` (FR-6).

**Verify:** 3 + 3 test pass.

**Refs:** Design §4.2; FR-4, FR-6, FR-8; AC-F06-1, AC-F06-3;
DL-F06-07, DL-F06-09

---

## 7. `FeedScreen` — FlatList + refresh + empty + open→seen

_Phụ thuộc Task 5 và Task 6._

**Test trước:** `src/__tests__/feed/FeedScreen.test.tsx`
(mock `FeedService`):
- `test_loads_feed_on_mount` — mount → `FeedService.getFeed` được
  gọi (FR-1).
- `test_renders_items_newest_first` — giữ thứ tự server (FR-2,
  AC-F06-6).
- `test_pull_to_refresh_reloads` — refresh → gọi lại `getFeed`
  (FR-7, AC-F06-5).
- `test_empty_state_when_no_items` — `items=[]` → empty state với
  hướng dẫn thêm bạn (FR-9, AC-F06-4).
- `test_open_marks_seen` — tap item → optimistic `seen=true` +
  `FeedService.markSeen` được gọi (FR-5, AC-F06-3).

**Làm:**
- `screens/FeedScreen.tsx`:
  - `useEffect` → `FeedService.getFeed()` lưu vào state (FR-1).
  - `FlatList` render `FeedItem`, giữ thứ tự server (FR-2).
  - `refreshing` + `onRefresh` → `getFeed()` reset (FR-7).
  - Empty state khi `items.length === 0` (FR-9).
  - Tap item → mở full-screen (ảnh), set `seen=true` cục bộ +
    `FeedService.markSeen(post_id)` (FR-5, DL-F06-02).

**Verify:** 5 test pass.

**Refs:** Design §1.1, §1.2, §1.4, §1.5, §4.2; FR-1, FR-2, FR-5,
FR-7, FR-9; AC-F06-3, AC-F06-4, AC-F06-5, AC-F06-6;
DL-F06-02

---

## 8. Integration test — end-to-end feed flow

_Phụ thuộc Task 4 (router + service)._

**Test trước = nội dung task:**
`backend/tests/integration/test_feed_flow.py` (theo tiền lệ
`tests/integration/`, seed users + friendships, tạo post qua
`post_service` rồi đọc qua `GET /feed`):
- `test_received_post_appears_on_feed` — A gửi cho B → feed B chứa
  post (AC-F06-1).
- `test_expired_post_hidden` — post `expires_at` quá khứ → không
  trên feed (AC-F06-2).
- `test_feed_chronological_order` — nhiều post → mới nhất đầu
  (AC-F06-6).
- `test_non_recipient_does_not_see` — C không phải recipient → feed
  C không chứa post (FR-2).

**Verify:** 4 integration test pass.

**Refs:** Design §6.8, §6.9; FR-2; AC-F06-1, AC-F06-2, AC-F06-6;
DL-F06-01, DL-F06-04

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **Persist seen** (`POST /posts/{id}/seen`, danh sách "seen by"):
  hiện thực + test trong **F07** tại điểm hook `FeedService.markSeen`
  (DL-F06-02).
- **Loại trừ block thực**: bảng `blocked_users` + điền
  `_blocked_sender_ids` thuộc **F10**; F06 chỉ chừa hook rỗng
  (DL-F06-03).
- **History "đã gửi/đã nhận"** (`GET /history/*`): thuộc **F08**.
- **Tải/cache ảnh CDN native + full-screen viewer hoàn chỉnh**: task
  triển khai native sau (DL-F06-07).
- **Migration**: F06 không tạo bảng/cột nào (DL-F06-06).
