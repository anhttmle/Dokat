# F07 — Seen By — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F05 / F06 / F07 / F08)

F07 là tính năng **ghi + đọc** trạng thái "đã xem" trên dữ liệu mà
F05 tạo ra. Nó hiện thực hai endpoint:

- `POST /posts/{id}/seen` — Recipient đánh dấu đã xem một ảnh
  (ghi `post_recipients.seen_at`).
- `GET /posts/{id}/seen-by` — Sender xem danh sách những người đã
  xem ảnh của mình + tổng số người xem.

Ngoài ra F07 **điền** hook `FeedService.markSeen` mà F06 để lại
(DL-F06-02) và cung cấp thành phần client `SeenByList` +
`SeenService` để F08 (History) hiển thị danh sách người đã xem.

Ranh giới với các feature lân cận:

- **F05 — Send (đã xong):** đã tạo bảng `posts`, `post_recipients`
  và cột `post_recipients.seen_at` (nullable) như "chỗ ở tự nhiên"
  của logic seen (DL-F05-04). F07 **không** thêm migration nào —
  chỉ ghi/đọc cột `seen_at` đã có (DL-F07-07). Ràng buộc `UNIQUE
  (post_id, recipient_id)` (`post_recipients_unique_pair`) đã do
  F05 đặt (F05 Design §2.2) ⇒ mỗi cặp (post, viewer) là một dòng
  duy nhất, không cần bảng "seen events" riêng (DL-F07-01).
- **F06 — Feed (đã xong):** đọc `seen_at` để suy ra cờ `seen` cho
  mỗi feed item (DL-F06-09) và để lại **điểm tích hợp**
  `FeedService.markSeen(postId)` (no-op) cho F07 (DL-F06-02). F07
  **điền** hook đó thành network `POST /posts/{id}/seen` qua
  `SeenService.markSeen` (DL-F07-05). F07 **không** sửa logic feed.
- **F08 — History (kế tiếp):** màn hình History "Đã gửi" sẽ tap một
  ảnh → mở full-screen → render `SeenByList` (FR-3, FR-4). F07 cung
  cấp **component** `SeenByList` + `SeenService.getSeenBy`; việc
  **gắn** chúng vào màn hình History và filter 24h thuộc F08
  (DL-F07-06) — cùng kiểu boundary như hook `markSeen` của F06.

> F07 **không** tạo bảng/cột/migration, **không** có reaction /
> comment / reply, **không** notify riêng từng lần seen (Non-goals).
> Seen được ghi **ngay** khi ảnh render full-screen, không có ngưỡng
> thời gian (FR-1, Technical Constraint).

---

## 1. Architecture Overview

```
┌──────────────────────────── React Native Client ───────────────────────────┐
│                                                                             │
│  (F06) FeedScreen / (F08) HistoryScreen                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Mở ảnh full-screen (Recipient)                                         │ │
│  │   → optimistic seen=true (F06) → FeedService.markSeen(postId)          │ │
│  │       └── delegate ──▶ SeenService.markSeen(postId)  (DL-F07-05)       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Sender tap ảnh trong History → SeenByList                              │ │
│  │   → SeenService.getSeenBy(postId) → render "N người đã xem" + danh sách│ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│         markSeen │  POST /posts/{id}/seen        getSeenBy │ GET .../seen-by │
│  ┌───────────────▼───────────────────────────┐  ┌──────────▼───────────────┐ │
│  │                SeenService                 │  │        SeenByList         │ │
│  │  markSeen(id)   → POST /posts/{id}/seen    │  │  viewers + seen_count     │ │
│  │  getSeenBy(id)  → GET  /posts/{id}/seen-by │  │  "N người đã xem"         │ │
│  └───────────────┬────────────────────────────┘  └───────────────────────────┘ │
└──────────────────┼───────────────────────────────────────────────────────────┘
                   ▼ HTTPS + Firebase ID token
┌──────────────────────────── FastAPI Backend ───────────────────────────────┐
│  POST /posts/{id}/seen → seen_service.mark_seen(db, post_id, viewer_id)     │
│    - load post (404 POST_NOT_FOUND nếu thiếu)                              │
│    - load post_recipients(post_id, viewer)  (403 NOT_RECIPIENT nếu thiếu)  │
│    - nếu seen_at IS NULL → seen_at = now(); commit  (first-seen wins)       │
│    - idempotent: gọi lại không đổi seen_at, không nhân bản (DL-F07-02)      │
│                                                                             │
│  GET /posts/{id}/seen-by → seen_service.get_seen_by(db, post_id, viewer_id)│
│    - load post (404 POST_NOT_FOUND nếu thiếu)                              │
│    - chỉ sender (post.user_id == viewer) — 403 FORBIDDEN nếu không (DL-07-04)│
│    - SELECT post_recipients pr JOIN users u                                 │
│        WHERE pr.post_id = id AND pr.seen_at IS NOT NULL                     │
│        ORDER BY pr.seen_at DESC                                             │
│    - trả viewers[] + seen_count (đếm trên tất cả recipients — FR-4)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng — Recipient đánh dấu đã xem (FR-1, FR-2, AC-F07-1)

1. Recipient mở ảnh full-screen ở Feed (F06) hoặc History (F08).
   Ảnh render đầy đủ → client gọi `FeedService.markSeen(postId)`
   (đã có ở F06) → **delegate** sang `SeenService.markSeen(postId)`
   (DL-F07-05).
2. `SeenService.markSeen` gọi `POST /posts/{id}/seen` kèm Firebase
   ID token. Không có ngưỡng thời gian — ghi **ngay** khi render
   (FR-1, Technical Constraint).
3. Backend resolve `firebase_uid` → viewer UUID (như `_get_user_id`
   của `routers/posts.py`); thiếu user row → **404 `USER_NOT_FOUND`**
   (DL-F07-09).
4. `seen_service.mark_seen` nạp post (404 `POST_NOT_FOUND` nếu
   thiếu), nạp dòng `post_recipients(post_id, viewer_id)`; nếu
   viewer không phải recipient → **403 `NOT_RECIPIENT`** (DL-F07-03).
5. Nếu `seen_at IS NULL` → đặt `seen_at = now()` và commit; nếu đã
   có → giữ nguyên (first-seen wins — DL-F07-02). Trả `{ post_id,
   seen_at }` (200).

### 1.2 Luồng — Sender xem danh sách "đã xem" (FR-3, FR-4, AC-F07-2)

1. Sender tap ảnh của mình trong History (F08) → `SeenByList` gọi
   `SeenService.getSeenBy(postId)` → `GET /posts/{id}/seen-by`.
2. Backend resolve viewer; nạp post (404 nếu thiếu); **chỉ sender**
   được xem — viewer ≠ `post.user_id` → **403 `FORBIDDEN`**
   (DL-F07-04).
3. Service trả các recipient có `seen_at IS NOT NULL` (mỗi người
   gồm `display_name`, `avatar_url`, `seen_at`) sắp theo `seen_at`
   giảm dần, kèm `seen_count` tổng hợp trên tất cả recipients (FR-4,
   DL-F07-08).
4. `SeenByList` render "N người đã xem" + danh sách tên (FR-4). Khi
   Sender refresh, gọi lại endpoint để cập nhật (FR-5).

### 1.3 Luồng — Mở lại ảnh đã xem (AC-F07-3)

- Recipient mở lại ảnh đã xem → client lại gọi `markSeen` →
  `POST /posts/{id}/seen`. Vì `seen_at` đã khác NULL, backend
  **không** ghi đè và **không** tạo dòng mới (ràng buộc unique pair
  của F05 + first-seen wins) ⇒ `seen_count` không tăng (DL-F07-02,
  AC-F07-3). Endpoint idempotent.

---

## 2. Data Models / Schema

F07 **không tạo bảng/cột mới** (DL-F07-07). Nó ghi/đọc cột
`seen_at` mà F05 đã tạo:

| Bảng | Cột dùng | Vai trò trong F07 |
|---|---|---|
| `posts` | `id`, `user_id` | Xác thực post tồn tại + chỉ sender xem seen-by |
| `post_recipients` | `post_id`, `recipient_id`, `seen_at` | Ghi `seen_at` (mark seen); đọc để liệt kê người xem + đếm |
| `users` | `id`, `display_name`, `avatar_url` | Metadata người đã xem (FR-3, FR-4) |

- "Seen event" **không** là bảng riêng: mỗi cặp (post, recipient)
  đã là một dòng duy nhất nhờ `post_recipients_unique_pair` (F05
  Design §2.2). Đánh dấu seen = `UPDATE seen_at` trên dòng đó ⇒
  không bao giờ trùng (DL-F07-01, AC-F07-3).
- Index đã đủ: `idx_post_recipients_post (post_id)` cho cả mark
  seen lẫn liệt kê seen-by (F05 Design §2.2).
- `seen_count` = số dòng `post_recipients` của post có
  `seen_at IS NOT NULL` (DL-F07-08).

### 2.1 Client — kiểu dữ liệu (TypeScript)

```typescript
/** Một người đã xem ảnh (cho Sender). */
interface SeenViewer {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  seen_at: string;                 // ISO 8601 (lần xem đầu tiên)
}

/** Kết quả GET /posts/{id}/seen-by. */
interface SeenByResult {
  post_id: string;
  seen_count: number;              // tổng người đã xem (FR-4)
  viewers: SeenViewer[];           // sắp theo seen_at giảm dần
}
```

---

## 3. API Contracts

Cả hai endpoint yêu cầu Firebase ID token (middleware hiện có).
`firebase_uid` → viewer UUID (theo `_get_user_id` của
`routers/posts.py`). Hai endpoint nằm dưới prefix `/posts`.

### 3.1 `POST /posts/{post_id}/seen` — đánh dấu đã xem

**Path param:** `post_id` (`UUID`).
**Request body:** không có.

**Response 200**

```jsonc
{
  "post_id": "<uuid>",
  "seen_at": "2026-06-22T07:05:00Z"   // lần xem đầu tiên (giữ nguyên nếu gọi lại)
}
```

- Idempotent: chỉ đặt `seen_at` khi đang NULL; gọi lại trả cùng
  `seen_at` cũ, không tăng `seen_count` (FR-6, AC-F07-3, DL-F07-02).
- Viewer **không** phải recipient của post → **403 `NOT_RECIPIENT`**
  (DL-F07-03).
- `post_id` không tồn tại → **404 `POST_NOT_FOUND`**.
- `firebase_uid` chưa có user row → **404 `USER_NOT_FOUND`**
  (DL-F07-09).
- `post_id` sai định dạng UUID → **422** (FastAPI path validation).

### 3.2 `GET /posts/{post_id}/seen-by` — danh sách người đã xem (chỉ Sender)

**Path param:** `post_id` (`UUID`).

**Response 200**

```jsonc
{
  "post_id": "<uuid>",
  "seen_count": 2,
  "viewers": [
    {
      "user_id": "<uuid>",
      "display_name": "Châu",
      "avatar_url": "https://cdn.pawsnap.app/avatars/...jpg",
      "seen_at": "2026-06-22T07:05:00Z"
    },
    {
      "user_id": "<uuid>",
      "display_name": "Bình",
      "avatar_url": null,
      "seen_at": "2026-06-22T07:02:00Z"
    }
  ]
}
```

- `viewers` chỉ gồm recipient có `seen_at IS NOT NULL`, sắp theo
  `seen_at` giảm dần; `seen_count == len(viewers)` (FR-4,
  DL-F07-08).
- Chưa ai xem → `seen_count: 0`, `viewers: []` (200, không lỗi).
- Viewer **không** phải Sender của post → **403 `FORBIDDEN`**
  (FR-3, DL-F07-04).
- `post_id` không tồn tại → **404 `POST_NOT_FOUND`**.
- `firebase_uid` chưa có user row → **404 `USER_NOT_FOUND`**
  (DL-F07-09).

### 3.3 Không thuộc F07

- `GET /feed`: thuộc F06.
- `GET /history/sent`, `GET /history/received`: thuộc F08; việc
  **gắn** `SeenByList` vào màn hình History cũng thuộc F08
  (DL-F07-06).
- Push/notify khi có người xem: **không** thuộc MVP (Non-goal).

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/app/
├── schemas/
│   └── seen.py             # SeenResponse, SeenViewerResponse, SeenByResponse
├── services/
│   └── seen_service.py     # mark_seen, get_seen_by (+ exceptions)
└── routers/
    └── seen.py             # POST /posts/{id}/seen, GET /posts/{id}/seen-by
```

| Component | Trách nhiệm |
|---|---|
| `schemas/seen.py` | `SeenResponse { post_id, seen_at }`; `SeenViewerResponse` (đúng §2.1); `SeenByResponse { post_id, seen_count, viewers }`. |
| `seen_service.mark_seen(db, *, post_id, viewer_id) -> datetime` | Nạp post (`PostNotFoundError`); nạp edge `(post_id, viewer)` (`NotRecipientError`); set `seen_at = now()` nếu NULL (first-seen wins — DL-F07-02); trả `seen_at`. |
| `seen_service.get_seen_by(db, *, post_id, viewer_id)` | Nạp post (`PostNotFoundError`); chỉ sender (`NotSenderError` — DL-F07-04); SELECT recipients có `seen_at` not null JOIN users, sắp `seen_at DESC`; trả `(viewers, seen_count)`. |
| `seen_service` exceptions | `PostNotFoundError`, `NotRecipientError`, `NotSenderError`. |
| `routers/seen.py` (prefix `/posts`) | Resolve viewer (404 `USER_NOT_FOUND`); map exceptions → 403/404; trả `SeenResponse` / `SeenByResponse`. Đăng ký trong `main.py`. |

### 4.2 Client (React Native)

```
src/
├── services/
│   ├── SeenService.ts                  # markSeen, getSeenBy
│   ├── __mocks__/SeenService.ts        # manual mock cho test component
│   └── FeedService.ts                  # markSeen hook → delegate SeenService (DL-F07-05)
├── components/
│   └── SeenByList.tsx                  # "N người đã xem" + danh sách
└── __tests__/seen/
    ├── SeenService.test.ts
    ├── SeenByList.test.tsx
    └── FeedServiceMarkSeen.test.ts
```

| Component | Trách nhiệm |
|---|---|
| `SeenService` | `markSeen(postId)` → `POST /posts/{id}/seen`; `getSeenBy(postId)` → `GET /posts/{id}/seen-by` (parse `SeenByResult`). Auth header qua `AuthService.getIdToken()` (như `FeedService`). HTTP `fetch` mock được. |
| `FeedService.markSeen` (sửa) | Thay no-op (DL-F06-02) bằng `SeenService.markSeen(postId)`; giữ nguyên signature để F06 `FeedScreen` không đổi (DL-F07-05). |
| `SeenByList` | Nhận `SeenByResult` (hoặc gọi `SeenService.getSeenBy`); render "N người đã xem" (FR-4) + danh sách tên/avatar; rỗng → "Chưa có ai xem". Dùng bởi F08 History (DL-F07-06). |

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| `firebase_uid` chưa có user row | Backend | 404 `USER_NOT_FOUND` (DL-F07-09) |
| `post_id` không tồn tại | Backend | 404 `POST_NOT_FOUND` |
| Mark seen nhưng không phải recipient | Backend | 403 `NOT_RECIPIENT` (DL-F07-03) |
| Xem seen-by nhưng không phải sender | Backend | 403 `FORBIDDEN` (FR-3, DL-F07-04) |
| Mark seen lần 2 (đã seen) | Backend | giữ `seen_at` cũ, 200, count không tăng (AC-F07-3, DL-F07-02) |
| Chưa ai xem | Backend | 200 `seen_count: 0`, `viewers: []`; **không** lỗi |
| `markSeen` lỗi mạng | Client | best-effort: optimistic UI ở F06 giữ nguyên, không crash (DL-F06-02) |
| `getSeenBy` lỗi mạng | Client | `SeenByList` hiển thị trạng thái lỗi nhẹ; Sender refresh thử lại (FR-5) |

**Nguyên tắc:** `POST /posts/{id}/seen` **idempotent** — gọi lại an
toàn, không nhân bản (DL-F07-02). `GET /posts/{id}/seen-by` là
đọc-only. Đánh dấu seen là tác vụ phụ ở client (optimistic), thất
bại không chặn việc xem ảnh (kế thừa DL-F06-02).

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory cho service/router, theo tiền lệ
F05/F06). Client: Jest + RNTL, viết test TRƯỚC implementation (TDD).
F07 **không** có test migration (không tạo bảng — DL-F07-07).

### 6.1 `seen_service` — `test_service_seen.py`

| Test case | Mô tả |
|---|---|
| `test_mark_seen_sets_seen_at` | recipient mark → `seen_at` được đặt (FR-1, FR-2, AC-F07-1) |
| `test_mark_seen_idempotent` | mark lần 2 → `seen_at` không đổi (first-seen wins) (AC-F07-3, DL-F07-02) |
| `test_mark_seen_non_recipient_raises` | viewer không phải recipient → `NotRecipientError` (DL-F07-03) |
| `test_mark_seen_post_not_found_raises` | post không tồn tại → `PostNotFoundError` |
| `test_seen_by_lists_viewers` | trả recipients đã xem + `display_name`/`avatar_url`/`seen_at` (FR-3) |
| `test_seen_by_count_aggregates` | nhiều người xem → `seen_count` đúng (FR-4) |
| `test_seen_by_excludes_unseen` | recipient chưa xem → không trong `viewers`, không tính `seen_count` |
| `test_seen_by_orders_recent_first` | `viewers` sắp theo `seen_at` giảm dần |
| `test_seen_by_not_sender_raises` | viewer không phải sender → `NotSenderError` (DL-F07-04) |
| `test_seen_by_empty_when_nobody_seen` | chưa ai xem → `seen_count=0`, `viewers=[]` |

### 6.2 Router — `test_router_seen.py`

| Test case | Mô tả |
|---|---|
| `test_mark_seen_200` | 200 + `{ post_id, seen_at }` (AC-F07-1) |
| `test_mark_seen_idempotent_200` | gọi 2 lần → cùng `seen_at`, vẫn 200 (AC-F07-3) |
| `test_mark_seen_non_recipient_403` | không phải recipient → 403 `NOT_RECIPIENT` |
| `test_mark_seen_post_not_found_404` | post thiếu → 404 `POST_NOT_FOUND` |
| `test_mark_seen_user_not_found_404` | viewer chưa có row → 404 `USER_NOT_FOUND` (DL-F07-09) |
| `test_seen_by_200` | sender → 200 + `{ post_id, seen_count, viewers }` (AC-F07-2) |
| `test_seen_by_not_sender_403` | không phải sender → 403 `FORBIDDEN` (DL-F07-04) |
| `test_seen_by_post_not_found_404` | post thiếu → 404 `POST_NOT_FOUND` |
| `test_seen_by_empty_200` | chưa ai xem → 200 `seen_count=0`, `viewers=[]` |

### 6.3 Client — `SeenService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_mark_seen_posts_to_endpoint` | `markSeen(id)` → `POST /posts/{id}/seen` (AC-F07-1) |
| `test_mark_seen_attaches_auth` | header `Authorization: Bearer` (như FeedService) |
| `test_get_seen_by_returns_result` | `getSeenBy(id)` → parse `{ post_id, seen_count, viewers }` (AC-F07-2) |
| `test_get_seen_by_attaches_auth` | header `Authorization: Bearer` |

### 6.4 Client — `FeedServiceMarkSeen.test.ts`

| Test case | Mô tả |
|---|---|
| `test_feed_mark_seen_delegates_to_seen_service` | `FeedService.markSeen(id)` gọi `SeenService.markSeen(id)` (DL-F07-05) |

### 6.5 Client — `SeenByList.test.tsx` (RNTL)

| Test case | Mô tả |
|---|---|
| `test_renders_seen_count` | `seen_count=2` → hiển thị "2 người đã xem" (FR-4, AC-F07-2) |
| `test_renders_viewer_names` | liệt kê `display_name` của từng viewer (FR-3, AC-F07-2) |
| `test_empty_state_no_viewers` | `viewers=[]` → "Chưa có ai xem" |

### 6.6 Integration — `test_seen_flow.py`

| Test case | Mô tả |
|---|---|
| `test_recipient_seen_appears_for_sender` | B xem ảnh A → `GET seen-by` của A chứa B (AC-F07-1, AC-F07-2) |
| `test_seen_no_duplicate_on_repeat` | B xem 2 lần → `seen_count` vẫn 1 (AC-F07-3) |
| `test_multiple_viewers_counted` | B, C xem; D chưa → `seen_count=2`, D không có (AC-F07-2) |
| `test_non_sender_cannot_view_seen_by` | B gọi `seen-by` của A → 403 (DL-F07-04) |

### 6.7 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F07-1 | `test_mark_seen_sets_seen_at`, `test_mark_seen_200`, `test_mark_seen_posts_to_endpoint`, `test_recipient_seen_appears_for_sender` |
| AC-F07-2 | `test_seen_by_lists_viewers`, `test_seen_by_count_aggregates`, `test_seen_by_200`, `test_get_seen_by_returns_result`, `test_renders_seen_count`, `test_renders_viewer_names`, `test_multiple_viewers_counted` |
| AC-F07-3 | `test_mark_seen_idempotent`, `test_mark_seen_idempotent_200`, `test_seen_no_duplicate_on_repeat` |

### 6.8 Ghi chú Test

- **Gắn `SeenByList` vào màn hình History** + filter 24h được phủ ở
  **F08** (DL-F07-06); F07 chỉ test component render độc lập +
  `SeenService`.
- **Optimistic UI khi mở full-screen** đã test ở **F06**
  (`test_open_marks_seen`); F07 chỉ verify hook `FeedService.markSeen`
  delegate sang `SeenService.markSeen` (DL-F07-05).
- F07 không test migration (không tạo bảng — DL-F07-07); ràng buộc
  unique pair đã test ở F05 (`test_post_recipients_unique_pair`).
