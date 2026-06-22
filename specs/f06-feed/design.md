# F06 — Feed & App View — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F05 / F06 / F07 / F10)

F06 là tính năng **chỉ-đọc** (read-only) đầu tiên trên dữ liệu mà
F05 tạo ra. Nó thêm một endpoint `GET /feed` đọc `posts` +
`post_recipients` và trả về danh sách ảnh người dùng **nhận được**
trong 24 giờ gần nhất, sắp theo thời gian giảm dần. Client hiển thị
danh sách này ở `FeedScreen` (màn hình chính sau đăng nhập).

Ranh giới với các feature lân cận:

- **F05 — Send (đã xong):** F06 **không** tạo/sửa `posts` hay
  `post_recipients`; chỉ `SELECT`. Bảng + cột (`expires_at`,
  `seen_at`, `cdn_url`, ...) đã do F05 đặc tả (F05 Design §2.1,
  §2.2). F06 **không** thêm migration nào (DL-F06-06).
- **F07 — Seen By (kế tiếp):** FR-5 yêu cầu "đánh dấu đã xem khi mở
  full-screen". Cột `post_recipients.seen_at` thuộc F07 (DL-F05-04)
  và endpoint `POST /posts/{id}/seen` cũng thuộc F07. F06 **đọc**
  `seen_at` để suy ra cờ `seen` cho mỗi feed item (FR-6) và để lại
  **điểm tích hợp** `markSeen` ở client cho F07 cắm network call
  vào (DL-F06-02).
- **F10 — Block/Report (sau F06):** FR-10 yêu cầu loại trừ ảnh từ
  người bị block. Bảng `blocked_users` chưa tồn tại ở thời điểm
  F06. Feed query đã **block-aware** qua helper
  `_blocked_sender_ids(...)` trả về tập rỗng cho đến khi F10 hiện
  thực (DL-F06-03) — tránh phải sửa query về sau.
- **F08 — History (sau F07):** dùng lại pattern đọc `posts` nhưng
  cho luồng "đã gửi/đã nhận" + filter 24h. F06 chỉ phụ trách feed
  "đã nhận" của người dùng hiện tại.

> Feed **không xoá** post hết hạn; chỉ ẩn bằng filter
> `expires_at > now()` (DL-F05-03, DL-F06-04). Không có widget,
> không infinite scroll, không ranking (Non-goals).

---

## 1. Architecture Overview

```
┌──────────────────────────── React Native Client ───────────────────────────┐
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                              FeedScreen                                 │ │
│  │  - useEffect → FeedService.getFeed()   (FR-1, AC-F06-1)               │ │
│  │  - FlatList, sắp xếp mới→cũ (server)   (FR-2, AC-F06-6)               │ │
│  │  - pull-to-refresh → getFeed()         (FR-7, AC-F06-5)               │ │
│  │  - empty state khi items rỗng          (FR-9, AC-F06-4)               │ │
│  │  - tap item → full-screen → markSeen() (FR-5; F07 persist)           │ │
│  └───────────────────────────────┬───────────────────────────────────────┘ │
│         renderItem │              │ getFeed(cursor?) / markSeen(postId)      │
│  ┌─────────────────▼───┐  ┌───────▼──────────────────────────────────────┐ │
│  │      FeedItem        │  │                 FeedService                  │ │
│  │ - sender, pet name   │  │  getFeed(cursor?) → GET /feed?cursor=&limit= │ │
│  │ - formatRelativeTime │  │  markSeen(id)     → hook F07 (DL-F06-02)     │ │
│  │ - seen/unseen viền   │  │  HTTP fetch injectable/mockable              │ │
│  │ - CDN img + holder   │  └───────┬──────────────────────────────────────┘ │
│  └──────────────────────┘          │ GET /feed (HTTPS, Firebase ID token)    │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                       ▼
┌──────────────────────────── FastAPI Backend ───────────────────────────────┐
│  GET /feed → feed_service.get_feed(db, viewer_id, cursor, limit)            │
│    SELECT posts p                                                           │
│      JOIN post_recipients pr ON pr.post_id=p.id AND pr.recipient_id=viewer  │
│      JOIN users u            ON u.id=p.user_id            (sender)          │
│      LEFT JOIN pet_profiles  ON pet.user_id=p.user_id     (tên thú cưng)    │
│    WHERE p.expires_at > now()                            (FR-3, AC-F06-2)   │
│      AND p.user_id NOT IN _blocked_sender_ids(viewer)    (FR-10 → F10)      │
│      AND (cursor filter)                                 (pagination)       │
│    ORDER BY p.created_at DESC, p.id DESC                 (FR-2, AC-F06-6)   │
│    LIMIT (limit + 1)                                     (next_cursor)      │
│                                                                             │
│  seen = (pr.seen_at IS NOT NULL)                         (FR-6)            │
│  (đọc-only; không INSERT/UPDATE — DL-F06-01)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng chính — Mở app, xem feed (AC-F06-1, AC-F06-6)

1. Sau đăng nhập, `FeedScreen` mount → `FeedService.getFeed()`
   (không cursor) → `GET /feed` kèm Firebase ID token.
2. Backend resolve `firebase_uid` → viewer UUID (giống
   `_get_user_id` của `routers/posts.py`); nếu chưa có user row →
   **404 `USER_NOT_FOUND`** (DL-F06-05).
3. `feed_service.get_feed` chạy query (§1 sơ đồ): lọc post mà
   viewer là **người nhận**, `expires_at > now()`, loại sender bị
   block, sắp `created_at DESC` → trả tối đa `limit` item + có thể
   kèm `next_cursor`.
4. Mỗi item gồm metadata sender (`display_name`, `avatar_url`),
   `pet_name` (nếu có — FR-4), `cdn_url`, `created_at` (ISO), và cờ
   `seen` (FR-6).
5. Client render `FeedItem`: ảnh CDN + placeholder (FR-8), tên +
   thời gian tương đối tính ở client từ `created_at` (DL-F06-07),
   viền "chưa xem" nếu `seen == false`.

### 1.2 Luồng — Pull-to-refresh (AC-F06-5)

- Người dùng kéo xuống → `FeedScreen` gọi lại
  `FeedService.getFeed()` (reset cursor) → thay thế danh sách bằng
  kết quả mới nhất; item mới (nếu có) nằm đầu (FR-7).

### 1.3 Luồng — Phân trang cursor (Technical Constraint)

- Khi danh sách dài hơn một trang, response trả `next_cursor`
  (opaque). `FeedScreen` (tuỳ chọn) nạp thêm bằng
  `getFeed(next_cursor)`. Cursor mã hoá `(created_at, post_id)` của
  item cuối; trang sau lấy các post "cũ hơn" theo thứ tự DESC
  (DL-F06-08). Trong 24h, dữ liệu có giới hạn nên thường chỉ một
  trang (Non-goal: infinite scroll).

### 1.4 Luồng — Đánh dấu đã xem khi mở full-screen (FR-5, AC-F06-3)

- Tap một item → mở ảnh full-screen → `FeedScreen` cập nhật
  **optimistic** `seen = true` cho item đó và gọi
  `FeedService.markSeen(postId)`. Ở F06, `markSeen` là **điểm tích
  hợp** cho F07 (network `POST /posts/{id}/seen`); F06 chỉ đảm bảo
  cập nhật trạng thái UI cục bộ (DL-F06-02). Lần `getFeed` kế tiếp,
  cờ `seen` sẽ phản ánh đúng từ DB sau khi F07 đã persist.

### 1.5 Luồng — Empty state (AC-F06-4)

- `getFeed` trả `items: []` (chưa có bạn, hoặc không nhận ảnh nào
  trong 24h) → `FeedScreen` hiển thị empty state với hướng dẫn
  "Thêm bạn bè để xem ảnh thú cưng của họ" (FR-9).

---

## 2. Data Models / Schema

F06 **không tạo bảng/cột mới** (DL-F06-06). Nó đọc các bảng F05/F02
đã có:

| Bảng | Cột dùng | Vai trò trong feed |
|---|---|---|
| `posts` | `id`, `user_id`, `cdn_url`, `expires_at`, `created_at` | Nguồn ảnh; filter 24h + sort |
| `post_recipients` | `post_id`, `recipient_id`, `seen_at` | Lọc theo viewer; suy ra `seen` |
| `users` | `id`, `display_name`, `avatar_url` | Metadata người gửi (FR-4) |
| `pet_profiles` | `user_id`, `name` | Tên thú cưng người gửi (FR-4) |

- Index đã có đủ cho query: `idx_post_recipients_recipient`
  (`recipient_id`) cho lọc viewer, `idx_posts_expires_at` cho filter
  24h, PK `posts.id` cho sort/cursor tiebreak (F05 Design §2.1,
  §2.2).
- `seen` **không** là cột — là giá trị suy ra
  `post_recipients.seen_at IS NOT NULL` (DL-F06-09).

### 2.1 Client — kiểu dữ liệu (TypeScript)

```typescript
/** Một mục trên feed (đã nhận). */
interface FeedItem {
  post_id: string;
  sender_id: string;
  sender_display_name: string | null;
  sender_avatar_url: string | null;
  pet_name: string | null;          // FR-4; null nếu sender chưa có pet
  cdn_url: string;
  created_at: string;               // ISO 8601 (thời gian gửi)
  seen: boolean;                     // FR-6
}

/** Kết quả GET /feed. */
interface FeedResult {
  items: FeedItem[];
  next_cursor: string | null;       // opaque; null khi hết trang
}
```

### 2.2 Hằng số

```python
# Kích thước trang mặc định + trần (DL-F06-08).
FEED_PAGE_SIZE = 20
FEED_MAX_PAGE_SIZE = 50
```

---

## 3. API Contracts

Endpoint yêu cầu Firebase ID token (middleware hiện có).
`firebase_uid` → viewer UUID (theo `_get_user_id` của
`routers/posts.py`).

### 3.1 `GET /feed` — danh sách ảnh đã nhận (24h)

**Query params**

| Param | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `cursor` | `string` | KHÔNG | Opaque; trang sau từ item cuối. Bỏ trống = trang đầu. |
| `limit` | `int` | KHÔNG | Số item/trang; mặc định `FEED_PAGE_SIZE`, trần `FEED_MAX_PAGE_SIZE`. |

**Response 200**

```jsonc
{
  "items": [
    {
      "post_id": "<uuid>",
      "sender_id": "<uuid>",
      "sender_display_name": "Anh",
      "sender_avatar_url": "https://cdn.pawsnap.app/avatars/...jpg",
      "pet_name": "Mướp",
      "cdn_url": "https://cdn.pawsnap.app/posts/.../...jpg",
      "created_at": "2026-06-22T07:00:00Z",
      "seen": false
    }
  ],
  "next_cursor": "eyJjcmVhdGVkX2F0Ijoi..."   // hoặc null khi hết trang
}
```

- Item sắp theo `created_at` giảm dần, tiebreak `post_id` giảm dần
  (AC-F06-6).
- Chỉ post mà viewer là **người nhận** và `expires_at > now()`
  (FR-3, AC-F06-2). Post từ sender bị block bị loại (FR-10 → F10).
- `cursor` sai định dạng → **400 `INVALID_CURSOR`** (DL-F06-08).
- `firebase_uid` chưa có user row → **404 `USER_NOT_FOUND`**
  (DL-F06-05).

### 3.2 Không thuộc F06

- `POST /posts/{id}/seen`, `GET /posts/{id}/seen-by`: thuộc F07.
- `GET /history/sent`, `GET /history/received`: thuộc F08.
- `POST /users/block`, danh sách block thực: thuộc F10 (F06 chỉ
  chừa hook `_blocked_sender_ids` — DL-F06-03).

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/app/
├── schemas/
│   └── feed.py            # FeedItemResponse, FeedResponse
├── services/
│   └── feed_service.py    # get_feed (+ cursor encode/decode, block hook)
└── routers/
    └── feed.py            # GET /feed
```

| Component | Trách nhiệm |
|---|---|
| `schemas/feed.py` | `FeedItemResponse` (đúng §2.1), `FeedResponse { items, next_cursor }`. |
| `feed_service.get_feed(db, *, viewer_id, cursor, limit)` | Build query (join, filter 24h, block hook, cursor), sort, lấy `limit+1` để tính `next_cursor`; map sang item (`seen` từ `seen_at`). |
| `feed_service._blocked_sender_ids(db, viewer_id)` | Trả `set()` cho đến khi F10 hiện thực (DL-F06-03). |
| `feed_service._encode_cursor / _decode_cursor` | Mã hoá/giải mã `(created_at, post_id)`; sai định dạng → `InvalidCursorError` (DL-F06-08). |
| `routers/feed.py` | `GET /feed`; resolve viewer (404 `USER_NOT_FOUND`); map `InvalidCursorError` → 400; trả `FeedResponse`. Đăng ký trong `main.py`. |

### 4.2 Client (React Native)

```
src/
├── services/
│   ├── FeedService.ts                 # getFeed, markSeen (hook F07)
│   └── __mocks__/FeedService.ts       # manual mock cho test screen
├── components/
│   ├── FeedItem.tsx                   # 1 dòng feed (seen/unseen, time, ảnh)
│   └── relativeTime.ts                # formatRelativeTime (pure util)
├── screens/
│   └── FeedScreen.tsx                 # FlatList + refresh + empty + open
└── __tests__/feed/
    ├── FeedService.test.ts
    ├── relativeTime.test.ts
    ├── FeedItem.test.tsx
    └── FeedScreen.test.tsx
```

| Component | Trách nhiệm |
|---|---|
| `FeedService` | `getFeed(cursor?)` → `GET /feed`; `markSeen(postId)` → hook F07 (DL-F06-02). Auth header qua `AuthService.getIdToken()` (như `SocialService`). HTTP `fetch` mock được. |
| `relativeTime.formatRelativeTime(iso, now)` | Pure util → chuỗi tiếng Việt ("vừa xong", "3 phút trước", "2 giờ trước") (FR-4, DL-F06-07). |
| `FeedItem` | Render ảnh CDN + placeholder (FR-8), tên sender + tên pet (FR-4), thời gian tương đối, viền/indicator theo `seen` (FR-6). |
| `FeedScreen` | `getFeed` khi mount (FR-1); `FlatList` giữ thứ tự server (FR-2); pull-to-refresh (FR-7); empty state (FR-9); tap → full-screen + optimistic `seen=true` + `markSeen` (FR-5). |

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| `firebase_uid` chưa có user row | Backend | 404 `USER_NOT_FOUND` (DL-F06-05) |
| `cursor` sai định dạng | Backend | 400 `INVALID_CURSOR` (DL-F06-08) |
| `limit` vượt trần | Backend | clamp về `FEED_MAX_PAGE_SIZE` (không lỗi) |
| Sender bị block | Backend | loại khỏi kết quả (FR-10 → hook F10, DL-F06-03) |
| Post hết hạn 24h | Backend | filter `expires_at > now()` ẩn khỏi feed (AC-F06-2) |
| Feed rỗng | Client | empty state (AC-F06-4); **không** lỗi |
| Ảnh CDN tải chậm/lỗi | Client | placeholder khi loading (FR-8); item vẫn render |
| `getFeed` lỗi mạng | Client | giữ danh sách cũ, không crash; refresh thử lại |

**Nguyên tắc:** `GET /feed` là **đọc-only**, idempotent — gọi lại
(refresh) luôn an toàn (DL-F06-01). Đánh dấu seen là tác vụ phụ,
optimistic ở UI; thất bại không chặn việc hiển thị feed (DL-F06-02).

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory cho service/router, theo tiền lệ
F05). Client: Jest + RNTL, viết test TRƯỚC implementation (TDD).
F06 **không** có test migration (không tạo bảng — DL-F06-06).

### 6.1 `feed_service` — `test_service_feed.py`

| Test case | Mô tả |
|---|---|
| `test_feed_returns_received_posts` | Viewer là recipient → post xuất hiện; non-recipient → không (FR-2) |
| `test_feed_orders_newest_first` | created_at giảm dần (AC-F06-1, AC-F06-6) |
| `test_feed_excludes_expired` | `expires_at <= now()` bị ẩn (FR-3, AC-F06-2) |
| `test_feed_seen_flag` | `seen_at` null → `seen=false`; có giá trị → `seen=true` (FR-6) |
| `test_feed_includes_sender_and_pet` | item có `sender_display_name`, `pet_name` (FR-4) |
| `test_feed_pet_name_null_when_no_pet` | sender chưa có pet → `pet_name=None` (FR-4) |
| `test_feed_empty_when_no_received` | viewer chưa nhận gì → `items=[]` (AC-F06-4) |
| `test_feed_excludes_blocked_sender` | sender trong `_blocked_sender_ids` bị loại (FR-10; hook rỗng = no-op) |

### 6.2 `feed_service` cursor — `test_service_feed_cursor.py`

| Test case | Mô tả |
|---|---|
| `test_feed_first_page_limit` | `limit=N` → tối đa N item + `next_cursor` khi còn dữ liệu |
| `test_feed_second_page_continues` | trang sau (cursor) chỉ chứa post cũ hơn, không trùng (DL-F06-08) |
| `test_feed_last_page_cursor_none` | trang cuối → `next_cursor=None` |
| `test_feed_invalid_cursor_raises` | cursor hỏng → `InvalidCursorError` (DL-F06-08) |
| `test_feed_limit_clamped_to_max` | `limit > FEED_MAX_PAGE_SIZE` → clamp |

### 6.3 Router — `test_router_feed.py`

| Test case | Mô tả |
|---|---|
| `test_feed_200` | 200 + `{ items, next_cursor }` đúng schema |
| `test_feed_user_not_found_404` | viewer chưa có row → 404 `USER_NOT_FOUND` (DL-F06-05) |
| `test_feed_invalid_cursor_400` | cursor hỏng → 400 `INVALID_CURSOR` |
| `test_feed_empty_200` | feed rỗng → 200 `items=[]` (AC-F06-4) |

### 6.4 Client — `FeedService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_get_feed_returns_items` | gọi `GET /feed`, parse `items/next_cursor` (AC-F06-1) |
| `test_get_feed_passes_cursor` | có cursor → query string `?cursor=` (DL-F06-08) |
| `test_get_feed_attaches_auth` | header `Authorization: Bearer` (như SocialService) |
| `test_mark_seen_calls_hook` | `markSeen(id)` gọi đúng điểm tích hợp F07 (DL-F06-02) |

### 6.5 Client — `relativeTime.test.ts`

| Test case | Mô tả |
|---|---|
| `test_just_now` | < 1 phút → "vừa xong" |
| `test_minutes_ago` | 3 phút → "3 phút trước" (AC-F06-1) |
| `test_hours_ago` | 2 giờ → "2 giờ trước" |

### 6.6 Client — `FeedItem.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_renders_sender_and_pet` | hiển thị tên sender + tên pet (FR-4) |
| `test_unseen_indicator` | `seen=false` → có indicator "chưa xem" (FR-6, AC-F06-3) |
| `test_seen_no_indicator` | `seen=true` → không indicator (AC-F06-3) |

### 6.7 Client — `FeedScreen.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_loads_feed_on_mount` | mount → `FeedService.getFeed` được gọi (FR-1) |
| `test_renders_items_newest_first` | giữ thứ tự server (FR-2, AC-F06-6) |
| `test_pull_to_refresh_reloads` | refresh → gọi lại `getFeed` (FR-7, AC-F06-5) |
| `test_empty_state_when_no_items` | `items=[]` → empty state (FR-9, AC-F06-4) |
| `test_open_marks_seen` | tap item → optimistic `seen=true` + `markSeen` (FR-5, AC-F06-3) |

### 6.8 Integration — `test_feed_flow.py`

| Test case | Mô tả |
|---|---|
| `test_received_post_appears_on_feed` | A gửi cho B → `GET /feed` của B chứa post (AC-F06-1) |
| `test_expired_post_hidden` | post `expires_at` quá khứ → không trên feed (AC-F06-2) |
| `test_feed_chronological_order` | nhiều post → mới nhất đầu (AC-F06-6) |
| `test_non_recipient_does_not_see` | C không phải recipient → feed C không chứa post (FR-2) |

### 6.9 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F06-1 | `test_feed_orders_newest_first`, `test_get_feed_returns_items`, `test_minutes_ago`, `test_received_post_appears_on_feed` |
| AC-F06-2 | `test_feed_excludes_expired`, `test_expired_post_hidden` |
| AC-F06-3 | `test_feed_seen_flag`, `test_unseen_indicator`, `test_seen_no_indicator`, `test_open_marks_seen` |
| AC-F06-4 | `test_feed_empty_when_no_received`, `test_feed_empty_200`, `test_empty_state_when_no_items` |
| AC-F06-5 | `test_pull_to_refresh_reloads` |
| AC-F06-6 | `test_feed_orders_newest_first`, `test_feed_chronological_order`, `test_renders_items_newest_first` |

### 6.10 Ghi chú Test

- **Persist seen** (`POST /posts/{id}/seen`) test ở **F07**; F06 chỉ
  verify cờ `seen` đọc đúng + optimistic UI + gọi hook (DL-F06-02).
- **Loại trừ block thực** test ở **F10**; F06 chỉ verify hook
  `_blocked_sender_ids` được áp dụng (no-op rỗng) (DL-F06-03).
- Tải ảnh CDN thực + cache (FR-8, Technical Constraint) là tích hợp
  native, không cover bằng unit test (DL-F06-07).
