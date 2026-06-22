# F08 — History / Timeline (1 ngày) — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F05 / F06 / F07 / F08)

F08 là tính năng **chỉ-đọc** (read-only) trên dữ liệu mà F05 tạo
ra. Nó thêm hai endpoint dưới prefix `/history`:

- `GET /history/sent` — Danh sách ảnh người dùng **đã gửi** trong
  24h, kèm `recipient_count` + `seen_count` (FR-2, FR-3).
- `GET /history/received` — Danh sách ảnh người dùng **đã nhận**
  trong 24h, kèm metadata người gửi + cờ `seen` (FR-2, FR-3).

Client hiển thị hai danh sách này trong `HistoryScreen` với hai
section riêng "Đã gửi" / "Đã nhận" (FR-1, FR-3), truy cập từ bottom
navigation. Tap một ảnh → mở full-screen; với ảnh **đã gửi** render
`SeenByList` (do F07 cung cấp) qua `SeenService.getSeenBy` (FR-5,
DL-F07-06, DL-F08-08).

Ranh giới với các feature lân cận:

- **F05 — Send (đã xong):** F08 **không** tạo/sửa `posts` hay
  `post_recipients`; chỉ `SELECT`. Cột (`expires_at`, `seen_at`,
  `cdn_url`, ...) đã do F05 đặc tả. F08 **không** thêm migration nào
  (DL-F08-02).
- **F06 — Feed (đã xong):** `GET /history/received` dùng lại đúng
  pattern query của `GET /feed` (join `posts`↔`post_recipients`
  ↔`users`, LEFT JOIN `pet_profiles`, filter 24h, cờ `seen`). F08
  **tái dùng** cursor helpers + hằng số của `feed_service`
  (`_encode_cursor`, `_decode_cursor`, `InvalidCursorError`,
  `FEED_PAGE_SIZE`, `FEED_MAX_PAGE_SIZE`) thay vì viết lại (DRY —
  DL-F08-04), và block hook `_blocked_sender_ids` (DL-F08-06). Khác
  biệt: feed chỉ "đã nhận"; F08 thêm chiều "đã gửi".
- **F07 — Seen By (đã xong):** F07 cung cấp **component**
  `SeenByList` + `SeenService.getSeenBy`/`markSeen` và cố ý để lại
  việc **gắn** chúng vào màn hình History cho F08 (DL-F07-06). F08
  **không** thêm endpoint seen nào — chỉ gọi lại `SeenService`. Với
  ảnh "đã gửi" mở full-screen → `SeenService.getSeenBy(postId)` →
  `SeenByList`; với ảnh "đã nhận" mở full-screen → idempotent
  `SeenService.markSeen(postId)` (DL-F08-08).

> History **không xoá** post hết hạn; chỉ ẩn bằng filter
> `expires_at > now()` (DL-F08-03). Không hỗ trợ >24h, không
> download/share, không "On this day" (Non-goals).

---

## 1. Architecture Overview

```
┌──────────────────────────── React Native Client ───────────────────────────┐
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                            HistoryScreen                                │ │
│  │  - useEffect → HistoryService.getSent() + getReceived()  (FR-1, FR-2)  │ │
│  │  - 2 section: "Đã gửi" / "Đã nhận"        (FR-3, AC-F08-2)            │ │
│  │  - pull-to-refresh → reload cả hai section                            │ │
│  │  - empty state khi cả hai rỗng            (FR-6, AC-F08-4)            │ │
│  │  - tap ảnh → full-screen                  (FR-5, AC-F08-3)            │ │
│  │      • Đã gửi    → SeenService.getSeenBy → <SeenByList/>  (F07)        │ │
│  │      • Đã nhận   → SeenService.markSeen (idempotent)      (F07)        │ │
│  └───────────────┬───────────────────────────────────────┬───────────────┘ │
│      renderItem  │ getSent()/getReceived(cursor?)         │ getSeenBy(id)    │
│  ┌───────────────▼─────────────┐                ┌─────────▼───────────────┐ │
│  │        HistoryList          │                │   SeenByList (F07)       │ │
│  │  section title + items      │                │  "N người đã xem" + list │ │
│  │  - sent:  seen_count/total  │                └──────────────────────────┘ │
│  │  - recv:  sender + seen     │                                              │
│  └───────────────┬─────────────┘                                              │
│                  │ getSent / getReceived                                       │
│  ┌───────────────▼───────────────────────────────────────────────────────┐ │
│  │                          HistoryService                                 │ │
│  │  getSent(cursor?)     → GET /history/sent?cursor=&limit=               │ │
│  │  getReceived(cursor?) → GET /history/received?cursor=&limit=           │ │
│  │  Auth header qua AuthService.getIdToken() (như FeedService)            │ │
│  └───────────────┬───────────────────────────────────────────────────────┘ │
└──────────────────┼───────────────────────────────────────────────────────────┘
                   ▼ HTTPS + Firebase ID token
┌──────────────────────────── FastAPI Backend ───────────────────────────────┐
│  GET /history/sent → history_service.get_sent(db, viewer_id, cursor, limit) │
│    SELECT posts p                                                           │
│      LEFT JOIN post_recipients pr ON pr.post_id = p.id                      │
│    WHERE p.user_id = viewer  AND p.expires_at > now()    (FR-2, FR-4)       │
│      AND (cursor filter)                                 (pagination)       │
│    GROUP BY p.id                                                            │
│    → recipient_count = COUNT(pr.id)                                         │
│      seen_count      = COUNT(pr.seen_at)                                    │
│    ORDER BY p.created_at DESC, p.id DESC                 (FR-2)             │
│                                                                             │
│  GET /history/received → history_service.get_received(...)                  │
│    (giống GET /feed: viewer là recipient, expires_at > now(),               │
│     seen = seen_at IS NOT NULL, block-aware via _blocked_sender_ids)        │
│  (đọc-only; không INSERT/UPDATE — DL-F08-01)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng — Mở màn hình History (FR-1, FR-2, AC-F08-2)

1. User mở tab History → `HistoryScreen` mount → gọi song song
   `HistoryService.getSent()` và `HistoryService.getReceived()`
   (không cursor) → `GET /history/sent` + `GET /history/received`
   kèm Firebase ID token.
2. Backend resolve `firebase_uid` → viewer UUID (giống
   `_get_user_id` của `routers/posts.py`/`routers/feed.py`); chưa
   có user row → **404 `USER_NOT_FOUND`** (DL-F08-07).
3. `get_sent` trả các post viewer là **tác giả**, `expires_at >
   now()` (DL-F08-03), sắp `created_at DESC`, mỗi item kèm
   `recipient_count` + `seen_count` (DL-F08-05). `get_received` trả
   các post viewer là **người nhận** (như feed), kèm metadata người
   gửi + cờ `seen` (DL-F08-06).
4. Client render hai section qua `HistoryList`: "Đã gửi" và "Đã
   nhận" (FR-3, AC-F08-2).

### 1.2 Luồng — Filter 24h (FR-4, AC-F08-1)

- Cả hai endpoint lọc `expires_at > now()`. Vì F05 đặt
  `expires_at = created_at + 24h` (DL-F05-03), điều kiện này tương
  đương `created_at >= now() - 24h` (Requirements Technical
  Constraint) nhưng tái dùng được index `idx_posts_expires_at` và
  nhất quán với F05/F06 (DL-F08-03). Ảnh cũ hơn 24h không xuất hiện
  ở cả hai section (AC-F08-1).

### 1.3 Luồng — Xem ảnh full-screen từ History (FR-5, AC-F08-3)

1. Tap một ảnh trong section **"Đã gửi"** → mở full-screen → gọi
   `SeenService.getSeenBy(post_id)` (F07) → render `SeenByList`
   ("N người đã xem" + danh sách). Đây là phần **gắn** mà F07 để
   lại cho F08 (DL-F07-06, DL-F08-08).
2. Tap một ảnh trong section **"Đã nhận"** → mở full-screen hiển
   thị thông tin người gửi; gọi `SeenService.markSeen(post_id)`
   (idempotent — DL-F07-02) để đánh dấu đã xem nếu chưa.

### 1.4 Luồng — Empty state (FR-6, AC-F08-4)

- Nếu cả `getSent` và `getReceived` trả `items: []` (không gửi/nhận
  ảnh nào trong 24h) → `HistoryScreen` hiển thị empty state (FR-6).
  Nếu chỉ một section rỗng, section đó hiển thị nhãn rỗng riêng,
  section còn lại vẫn render bình thường.

### 1.5 Luồng — Phân trang cursor (Technical Constraint)

- Mỗi endpoint trả `next_cursor` (opaque) khi còn dữ liệu, dùng lại
  cơ chế cursor `(created_at, post_id)` của `feed_service`
  (DL-F08-04). Trong 24h dữ liệu giới hạn nên thường chỉ một trang.

---

## 2. Data Models / Schema

F08 **không tạo bảng/cột mới** (DL-F08-02). Nó đọc các bảng F05/F02
đã có:

| Bảng | Cột dùng | Vai trò trong History |
|---|---|---|
| `posts` | `id`, `user_id`, `cdn_url`, `expires_at`, `created_at` | Nguồn ảnh; filter 24h + sort; "đã gửi" = `user_id == viewer` |
| `post_recipients` | `post_id`, `recipient_id`, `seen_at` | "Đã nhận" lọc theo viewer + cờ `seen`; "Đã gửi" đếm `recipient_count`/`seen_count` |
| `users` | `id`, `display_name`, `avatar_url` | Metadata người gửi (received) |
| `pet_profiles` | `user_id`, `name` | Tên thú cưng người gửi (received) |

- Index đã đủ: `idx_posts_user_id` (`posts.user_id`) cho "đã gửi";
  `idx_post_recipients_recipient` (`recipient_id`) cho "đã nhận";
  `idx_post_recipients_post` (`post_id`) cho đếm seen; PK
  `posts.id` cho sort/cursor tiebreak (F05 Design §2.1, §2.2).
- `seen` (received) là giá trị suy ra `seen_at IS NOT NULL`
  (DL-F06-09). `seen_count` (sent) = số dòng `post_recipients` của
  post có `seen_at IS NOT NULL` (DL-F08-05).

### 2.1 Client — kiểu dữ liệu (TypeScript)

```typescript
/** Một ảnh đã gửi trong 24h (section "Đã gửi"). */
interface SentHistoryItem {
  post_id: string;
  cdn_url: string;
  created_at: string;               // ISO 8601 (thời gian gửi)
  recipient_count: number;          // tổng người nhận (FR-3)
  seen_count: number;               // số người đã xem (FR-3, FR-5)
}

/** Một ảnh đã nhận trong 24h (section "Đã nhận"). */
interface ReceivedHistoryItem {
  post_id: string;
  sender_id: string;
  sender_display_name: string | null;
  sender_avatar_url: string | null;
  pet_name: string | null;          // null nếu sender chưa có pet
  cdn_url: string;
  created_at: string;               // ISO 8601
  seen: boolean;                     // seen_at IS NOT NULL (DL-F06-09)
}

/** Kết quả GET /history/sent | /history/received. */
interface HistoryResult<TItem> {
  items: TItem[];
  next_cursor: string | null;       // opaque; null khi hết trang
}
```

### 2.2 Hằng số

Tái dùng `FEED_PAGE_SIZE = 20` và `FEED_MAX_PAGE_SIZE = 50` của
`feed_service` (DL-F08-04). F08 **không** định nghĩa hằng riêng để
tránh trùng lặp.

---

## 3. API Contracts

Cả hai endpoint yêu cầu Firebase ID token (middleware hiện có).
`firebase_uid` → viewer UUID (theo `_get_user_id` của
`routers/feed.py`). Hai endpoint nằm dưới prefix `/history`.

### 3.1 `GET /history/sent` — ảnh đã gửi (24h)

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
      "cdn_url": "https://cdn.pawsnap.app/posts/.../...jpg",
      "created_at": "2026-06-22T07:00:00Z",
      "recipient_count": 3,
      "seen_count": 2
    }
  ],
  "next_cursor": "eyJjcmVhdGVkX2F0Ijoi..."   // hoặc null khi hết trang
}
```

- Chỉ post mà `user_id == viewer` và `expires_at > now()` (FR-2,
  FR-4, AC-F08-1). Sắp `created_at DESC`, tiebreak `post_id DESC`.
- `recipient_count`/`seen_count` đếm trên `post_recipients`
  (DL-F08-05). Post 0 người nhận → cả hai = 0 (vẫn hiển thị).
- `cursor` sai định dạng → **400 `INVALID_CURSOR`** (DL-F08-04).
- `firebase_uid` chưa có user row → **404 `USER_NOT_FOUND`**
  (DL-F08-07).

### 3.2 `GET /history/received` — ảnh đã nhận (24h)

**Query params:** giống §3.1 (`cursor`, `limit`).

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
      "seen": true
    }
  ],
  "next_cursor": null
}
```

- Chỉ post mà viewer là **người nhận** và `expires_at > now()`
  (FR-2, FR-4). Sender bị block bị loại qua
  `_blocked_sender_ids` (DL-F08-06). Sắp `created_at DESC`,
  tiebreak `post_id DESC`.
- `seen = seen_at IS NOT NULL` (DL-F06-09).
- `cursor` sai → **400 `INVALID_CURSOR`**; `firebase_uid` chưa có
  user row → **404 `USER_NOT_FOUND`**.

### 3.3 Không thuộc F08

- `POST /posts/{id}/seen`, `GET /posts/{id}/seen-by`: thuộc F07
  (F08 chỉ **gọi lại** `SeenService` ở client — DL-F08-08).
- `GET /feed`: thuộc F06.
- History >24h / premium: ngoài MVP (Non-goal).

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/app/
├── schemas/
│   └── history.py          # SentHistoryItem/Received... + responses
├── services/
│   └── history_service.py  # get_sent, get_received (reuse feed cursor)
└── routers/
    └── history.py          # GET /history/sent, GET /history/received
```

| Component | Trách nhiệm |
|---|---|
| `schemas/history.py` | `SentHistoryItemResponse` (§2.1), `ReceivedHistoryItemResponse` (§2.1), `SentHistoryResponse { items, next_cursor }`, `ReceivedHistoryResponse { items, next_cursor }`. |
| `history_service.get_sent(db, *, viewer_id, cursor, limit)` | SELECT `posts` của viewer (author), LEFT JOIN `post_recipients`, GROUP BY post; `recipient_count = count(pr.id)`, `seen_count = count(pr.seen_at)`; filter `expires_at > now()`; cursor + sort; trả `(items, next_cursor)`. |
| `history_service.get_received(db, *, viewer_id, cursor, limit)` | Như `feed_service.get_feed` (viewer là recipient, block-aware, `seen`); trả `(items, next_cursor)`. |
| `history_service` cursor | Import lại `_encode_cursor`, `_decode_cursor`, `InvalidCursorError`, `FEED_PAGE_SIZE`, `FEED_MAX_PAGE_SIZE`, `_blocked_sender_ids` từ `feed_service` (DRY — DL-F08-04, DL-F08-06). |
| `routers/history.py` (prefix `/history`) | Resolve viewer (404 `USER_NOT_FOUND`); map `InvalidCursorError` → 400 `INVALID_CURSOR`; trả response schema. Đăng ký trong `main.py`. |

### 4.2 Client (React Native)

```
src/
├── services/
│   ├── HistoryService.ts                  # getSent, getReceived
│   └── __mocks__/HistoryService.ts        # manual mock cho test screen
├── components/
│   └── HistoryList.tsx                    # 1 section (title + items)
├── screens/
│   └── HistoryScreen.tsx                  # 2 section + refresh + empty + open
└── __tests__/history/
    ├── HistoryService.test.ts
    ├── HistoryList.test.tsx
    └── HistoryScreen.test.tsx
```

| Component | Trách nhiệm |
|---|---|
| `HistoryService` | `getSent(cursor?)` → `GET /history/sent`; `getReceived(cursor?)` → `GET /history/received` (parse `HistoryResult`). Auth header qua `AuthService.getIdToken()` (như `FeedService`). HTTP `fetch` mock được. |
| `HistoryList` | Nhận `{ title, items, mode }`; render tiêu đề section + danh sách. `mode="sent"` → hiển thị "{seen_count}/{recipient_count} đã xem" + thời gian (dùng lại `formatRelativeTime` của F06). `mode="received"` → tên người gửi + pet + cờ `seen`. Rỗng → nhãn rỗng riêng. |
| `HistoryScreen` | Mount → `getSent` + `getReceived` (FR-1); render 2 section qua `HistoryList` (FR-3); pull-to-refresh reload cả hai; empty state khi cả hai rỗng (FR-6); tap ảnh → full-screen: sent → `SeenService.getSeenBy` + `<SeenByList/>` (FR-5, DL-F08-08), received → `SeenService.markSeen`. |

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| `firebase_uid` chưa có user row | Backend | 404 `USER_NOT_FOUND` (DL-F08-07) |
| `cursor` sai định dạng | Backend | 400 `INVALID_CURSOR` (DL-F08-04) |
| `limit` vượt trần | Backend | clamp về `FEED_MAX_PAGE_SIZE` (không lỗi) |
| Post hết hạn 24h | Backend | filter `expires_at > now()` ẩn (AC-F08-1) |
| Sender bị block (received) | Backend | loại khỏi kết quả (hook F10 — DL-F08-06) |
| Sent post 0 người nhận | Backend | `recipient_count=0`, `seen_count=0`; vẫn trả |
| Cả hai section rỗng | Client | empty state (AC-F08-4); **không** lỗi |
| `getSent`/`getReceived` lỗi mạng | Client | giữ danh sách cũ, không crash; refresh thử lại |
| `getSeenBy` lỗi mạng (full-screen) | Client | `SeenByList` hiển thị trạng thái lỗi nhẹ (kế thừa F07) |

**Nguyên tắc:** Cả hai endpoint là **đọc-only**, idempotent — gọi
lại (refresh) luôn an toàn (DL-F08-01). Việc đánh dấu seen khi mở
ảnh "đã nhận" là tác vụ phụ idempotent của F07 (DL-F07-02), thất
bại không chặn việc xem ảnh.

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory cho service/router, theo tiền lệ
F05/F06). Client: Jest + RNTL, viết test TRƯỚC implementation (TDD).
F08 **không** có test migration (không tạo bảng — DL-F08-02).

### 6.1 `history_service` sent — `test_service_history_sent.py`

| Test case | Mô tả |
|---|---|
| `test_sent_returns_authored_posts` | viewer là author → thấy; post của người khác → không (FR-2) |
| `test_sent_orders_newest_first` | `created_at` giảm dần (FR-2, AC-F08-1) |
| `test_sent_excludes_expired` | `expires_at <= now()` bị ẩn (FR-4, AC-F08-1) |
| `test_sent_counts_recipients_and_seen` | `recipient_count`/`seen_count` đúng (FR-3, FR-5, DL-F08-05) |
| `test_sent_zero_recipients` | post 0 người nhận → cả hai count = 0, vẫn trả |
| `test_sent_empty_when_none` | chưa gửi gì trong 24h → `items=[]` (AC-F08-4) |

### 6.2 `history_service` received — `test_service_history_received.py`

| Test case | Mô tả |
|---|---|
| `test_received_returns_received_posts` | viewer là recipient → thấy; non-recipient → không (FR-2) |
| `test_received_orders_newest_first` | `created_at` giảm dần (AC-F08-1) |
| `test_received_excludes_expired` | `expires_at <= now()` bị ẩn (FR-4, AC-F08-1) |
| `test_received_seen_flag` | `seen_at` null → `seen=False`; có → `seen=True` (DL-F06-09) |
| `test_received_includes_sender_and_pet` | item có `sender_display_name`, `pet_name` |
| `test_received_excludes_blocked_sender` | sender trong `_blocked_sender_ids` bị loại (DL-F08-06) |
| `test_received_empty_when_none` | chưa nhận gì → `items=[]` (AC-F08-4) |

### 6.3 `history_service` cursor — `test_service_history_cursor.py`

| Test case | Mô tả |
|---|---|
| `test_sent_first_page_limit` | `limit=N` → ≤ N item + `next_cursor` khi còn dữ liệu |
| `test_sent_second_page_continues` | trang sau chỉ chứa post cũ hơn, không trùng (DL-F08-04) |
| `test_received_invalid_cursor_raises` | cursor hỏng → `InvalidCursorError` (DL-F08-04) |
| `test_limit_clamped_to_max` | `limit > FEED_MAX_PAGE_SIZE` → clamp |

### 6.4 Router — `test_router_history.py`

| Test case | Mô tả |
|---|---|
| `test_sent_200` | 200 + `{ items, next_cursor }` đúng schema (AC-F08-2) |
| `test_received_200` | 200 + `{ items, next_cursor }` đúng schema (AC-F08-2) |
| `test_sent_user_not_found_404` | viewer chưa có row → 404 `USER_NOT_FOUND` (DL-F08-07) |
| `test_received_user_not_found_404` | viewer chưa có row → 404 `USER_NOT_FOUND` |
| `test_invalid_cursor_400` | cursor hỏng → 400 `INVALID_CURSOR` |
| `test_sent_empty_200` | chưa gửi gì → 200 `items=[]` (AC-F08-4) |

### 6.5 Client — `HistoryService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_get_sent_returns_items` | gọi `GET /history/sent`, parse `items/next_cursor` (AC-F08-2) |
| `test_get_received_returns_items` | gọi `GET /history/received`, parse kết quả (AC-F08-2) |
| `test_history_passes_cursor` | có cursor → query `?cursor=` (DL-F08-04) |
| `test_history_attaches_auth` | header `Authorization: Bearer` (như FeedService) |

### 6.6 Client — `HistoryList.test.tsx` (RNTL)

| Test case | Mô tả |
|---|---|
| `test_sent_renders_seen_over_total` | mode sent → hiển thị "{seen_count}/{recipient_count}" (FR-3, FR-5) |
| `test_received_renders_sender` | mode received → hiển thị tên người gửi + pet (FR-3) |
| `test_empty_section_label` | `items=[]` → nhãn rỗng của section |

### 6.7 Client — `HistoryScreen.test.tsx` (RNTL)

| Test case | Mô tả |
|---|---|
| `test_loads_both_sections_on_mount` | mount → `getSent` + `getReceived` được gọi (FR-1) |
| `test_renders_two_sections` | hiển thị section "Đã gửi" và "Đã nhận" (FR-3, AC-F08-2) |
| `test_empty_state_when_both_empty` | cả hai rỗng → empty state (FR-6, AC-F08-4) |
| `test_open_sent_shows_seen_by_list` | tap ảnh đã gửi → `SeenService.getSeenBy` + `SeenByList` (FR-5, AC-F08-3, DL-F08-08) |
| `test_open_received_marks_seen` | tap ảnh đã nhận → `SeenService.markSeen` (FR-5) |

### 6.8 Integration — `test_history_flow.py`

| Test case | Mô tả |
|---|---|
| `test_sent_photo_appears_in_sent_history` | A gửi cho B → `GET /history/sent` của A chứa post (AC-F08-2) |
| `test_received_photo_appears_in_received_history` | A gửi cho B → `GET /history/received` của B chứa post (AC-F08-2) |
| `test_expired_photo_hidden_in_history` | post `expires_at` quá khứ → không trong cả hai (AC-F08-1) |
| `test_sent_seen_count_reflects_viewers` | B xem ảnh A → `seen_count` của A = 1 (FR-5, AC-F08-3) |

### 6.9 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F08-1 | `test_sent_excludes_expired`, `test_received_excludes_expired`, `test_sent_orders_newest_first`, `test_received_orders_newest_first`, `test_expired_photo_hidden_in_history` |
| AC-F08-2 | `test_sent_200`, `test_received_200`, `test_get_sent_returns_items`, `test_get_received_returns_items`, `test_renders_two_sections`, `test_sent_photo_appears_in_sent_history`, `test_received_photo_appears_in_received_history` |
| AC-F08-3 | `test_sent_counts_recipients_and_seen`, `test_open_sent_shows_seen_by_list`, `test_sent_seen_count_reflects_viewers` |
| AC-F08-4 | `test_sent_empty_when_none`, `test_received_empty_when_none`, `test_sent_empty_200`, `test_empty_state_when_both_empty` |

### 6.10 Ghi chú Test

- **`SeenByList` render độc lập + `SeenService`** đã test ở **F07**;
  F08 chỉ verify việc **gắn** vào full-screen "Đã gửi" (gọi
  `getSeenBy`) (DL-F07-06, DL-F08-08).
- **Loại trừ block thực** test ở **F10**; F08 chỉ verify hook
  `_blocked_sender_ids` được áp dụng cho received (no-op rỗng).
- **Tải/cache ảnh CDN native + full-screen viewer hoàn chỉnh**: task
  triển khai native sau (kế thừa DL-F06-07).
- F08 không test migration (không tạo bảng — DL-F08-02).
