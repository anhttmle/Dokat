# F05 — Gửi Ảnh (Multi-Recipient / Broadcast) — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F04 / F11 / F05 / F09)

F05 là tính năng **end-to-end** đầu tiên có cả client lẫn backend
+ DB. Nó nhận artifact `CapturedPhoto` từ F04 (DL-F04-01), lấy
metadata vị trí qua `LocationService` của F11 (DL-F11-01), upload
ảnh lên S3 bằng presigned URL, rồi tạo `posts` + `post_recipients`
trong PostgreSQL.

Ranh giới với các feature lân cận:

- **F04 — Capture (client-only):** kết thúc ở artifact
  `CapturedPhoto` (ảnh đã nén). F05 **không** sửa
  `CaptureService`/`CameraScreen` (đã seal — DL-F04-01).
- **F11 — Location (client-only):** cung cấp
  `LocationService.getCurrentLocation()` + `buildLocationPayload()`.
  F05 là **consumer**: gọi hai hàm này khi dựng body `POST /posts`
  và **hiện thực** hai cột `posts.latitude/longitude` mà F11 đặc tả
  (F11 Design §2.3, DL-F11-01).
- **F06 — Feed / F07 — Seen / F08 — History:** đọc `posts` +
  `post_recipients`. F05 **chỉ tạo** dữ liệu; các endpoint đọc
  thuộc các feature đó. Cột `post_recipients.seen_at` được F05 tạo
  sẵn (chỗ ở tự nhiên) nhưng **logic seen** thuộc F07 (DL-F05-04).
- **F09 — Notifications:** F05 tạo post + recipients và để lại
  **điểm tích hợp** (sau khi commit recipients) cho F09 cắm push
  "new photo" vào. F05 **không** gửi notification (DL-F05-05).

> Bảng dữ liệu chính tên là **`posts`** (không phải `photos` stub
> của F02). Xem `decision_log.md` → **DL-F05-01** cho quyết định
> tên bảng và quan hệ với stub `photos`.

---

## 1. Architecture Overview

```
┌──────────────────────────── React Native Client ───────────────────────────┐
│                                                                             │
│  (F04) CapturedPhoto ──┐                                                     │
│                        ▼                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                       RecipientSelectorScreen                          │ │
│  │  - load friends (SocialService.getFriends) — mặc định chọn HẾT (FR-2) │ │
│  │  - toggle subset (FR-3) · nút "Gửi" luôn bật, kể cả 0 người (FR-4)     │ │
│  │  - sau khi gửi xong → discard ảnh (one-shot, FR-10)                    │ │
│  └───────────────────────────────┬───────────────────────────────────────┘ │
│                                   │ send(photo, recipientIds)                │
│  ┌────────────────────────────────▼──────────────────────────────────────┐ │
│  │                              SendService                               │ │
│  │  1. getUploadUrl(content_type)         → POST /posts/upload-url        │ │
│  │  2. uploadToS3(uploadUrl, fileUri)     → PUT (retry tối đa 3, FR-13)   │ │
│  │  3. getCurrentLocation()+buildPayload  → (F11)                         │ │
│  │  4. confirm(object_key, cdn_url, ids, latlng) → POST /posts           │ │
│  └───────┬───────────────────────────────────────────────┬───────────────┘ │
│          │ presigned + confirm (HTTPS)                    │ PUT (S3 direct)  │
└──────────┼────────────────────────────────────────────────┼─────────────────┘
           ▼                                                ▼
┌──────────────────── FastAPI Backend ────────────────┐   ┌──────── S3 ───────┐
│  POST /posts/upload-url → storage_service            │   │ posts/{uid}/{ts}. │
│      presigned PUT URL (key do server cấp)           │   │   jpg (binary)    │
│  POST /posts → post_service.create_post              │   └───────────────────┘
│      - INSERT posts (expires_at = now()+24h)         │
│      - INSERT post_recipients (0..N)                 │
│      - [hook F09: new-photo push]  (DL-F05-05)       │
│                                                      │
│  posts(id, user_id, s3_key, cdn_url, expires_at,     │
│        latitude, longitude, created_at)              │
│  post_recipients(id, post_id, recipient_id,          │
│        seen_at, created_at)                           │
└──────────────────────────────────────────────────────┘
```

### 1.1 Luồng chính — Gửi broadcast tới tất cả bạn bè (AC-F05-1, AC-F05-2)

1. F04 handoff `CapturedPhoto` → mở `RecipientSelectorScreen`.
2. Screen gọi `SocialService.getFriends()`; **chọn sẵn toàn bộ**
   bạn bè làm người nhận (FR-1, FR-2, AC-F05-1).
3. Sender giữ nguyên mặc định, nhấn "Gửi" → gọi
   `SendService.send(photo, recipientIds)`.
4. `SendService` lấy presigned URL: `POST /posts/upload-url`
   `{ content_type: "image/jpeg" }` → `{ upload_url, object_key,
   cdn_url }` (Technical Constraint — presigned S3).
5. `SendService` `PUT` file lên `upload_url` (upload **một lần**,
   FR-5; retry tối đa 3 — FR-13, AC-F05-6).
6. `SendService` lấy toạ độ: `LocationService.getCurrentLocation()`
   → `buildLocationPayload()` (F11).
7. `SendService` confirm: `POST /posts` `{ s3_key: object_key,
   cdn_url, recipient_ids, ...latlng }`.
8. Backend `create_post`: INSERT `posts` (`expires_at =
   now()+24h` — DL-F05-03) + INSERT `post_recipients` cho từng
   recipient (quan hệ M-N, FR-6) → trả `{ post_id, expires_at,
   recipient_count, created_at }` (201).
9. Sau commit recipients, backend chạy **hook F09** gửi push tới
   từng recipient (DL-F05-05). Sender thấy trạng thái "Đã gửi"
   (FR-12); ảnh bị **discard** (FR-10, AC-F05-5).

### 1.2 Luồng — Gửi cho một subset (AC-F05-3)

- Bước 1–2 như trên; Sender **bỏ chọn** bớt → `recipientIds` là
  subset (FR-3). Backend chỉ tạo `post_recipients` cho subset đó →
  chỉ những người này thấy ảnh ở feed (F06) và nhận push (F09).

### 1.3 Luồng — 0 người nhận (AC-F05-4)

- `recipientIds = []` (chưa có bạn, hoặc bỏ chọn hết). Nút "Gửi"
  vẫn bật (FR-4). Backend **vẫn** INSERT `posts` (FR-5, FR-7),
  **không** tạo `post_recipients`, **không** gửi push (FR-9). Post
  vẫn vào History "Đã gửi" của Sender (F08).

### 1.4 Luồng — Lỗi mạng & retry (AC-F05-6, AC-F05-7)

- Bước upload S3 (1.1 §5) bọc retry tối đa **3 lần** với backoff
  ngắn (FR-13). Nếu khôi phục mạng trong thời gian retry → upload
  thành công, không cần Sender thao tác (AC-F05-6).
- Sau 3 lần thất bại → `SendService` throw lỗi; screen hiển thị
  thông báo rõ ràng. **Chưa** gọi `POST /posts` ⇒ không có `posts`
  hay `post_recipients` nào được tạo (AC-F05-7).

---

## 2. Data Models / Schema

### 2.1 Backend — bảng `posts`

| Cột | Kiểu | Null | Mô tả |
|---|---|---|---|
| `id` | `UUID` PK | NO | `gen_random_uuid()` |
| `user_id` | `UUID` FK→users CASCADE | NO | Sender; indexed |
| `s3_key` | `TEXT` | NO | Object key trên S3 (server cấp — DL-F05-02) |
| `cdn_url` | `TEXT` | NO | URL CloudFront công khai |
| `expires_at` | `TIMESTAMPTZ` | NO | `created_at + 24h` (DL-F05-03); index cho filter feed/history |
| `latitude` | `DECIMAL(11, 8)` | YES | Vĩ độ — contract F11 (AC-F11-2 → NULL khi từ chối quyền) |
| `longitude` | `DECIMAL(12, 8)` | YES | Kinh độ — contract F11 |
| `created_at` | `TIMESTAMPTZ` | NO | `now()`; timestamp gửi (FR-11) |

- `latitude/longitude` **chỉ dùng nội bộ**, không expose ở bất kỳ
  response nào (F11 AC-F11-3).
- Index: `idx_posts_user_id (user_id)` (History "Đã gửi"),
  `idx_posts_expires_at (expires_at)` (filter 24h ở feed/history).

### 2.2 Backend — bảng `post_recipients`

| Cột | Kiểu | Null | Mô tả |
|---|---|---|---|
| `id` | `UUID` PK | NO | `gen_random_uuid()` |
| `post_id` | `UUID` FK→posts CASCADE | NO | indexed |
| `recipient_id` | `UUID` FK→users CASCADE | NO | indexed |
| `seen_at` | `TIMESTAMPTZ` | YES | F07 ghi khi xem (DL-F05-04); F05 chỉ tạo cột |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` |

- `UNIQUE (post_id, recipient_id)` — một người nhận chỉ xuất hiện
  một lần cho mỗi post (`post_recipients_unique_pair`).
- Bảng có thể **rỗng** đối với một post (0 người nhận — FR-6,
  AC-F05-4).
- Index: `idx_post_recipients_post (post_id)`,
  `idx_post_recipients_recipient (recipient_id)` (feed của người
  nhận — F06).

### 2.3 Client — kiểu dữ liệu (TypeScript)

```typescript
/** Kết quả presigned URL từ POST /posts/upload-url. */
interface UploadUrlResult {
  upload_url: string;   // presigned S3 PUT
  object_key: string;   // s3_key authoritative do server cấp
  cdn_url: string;
}

/** Body gửi lên POST /posts. */
interface CreatePostBody {
  s3_key: string;
  cdn_url: string;
  recipient_ids: string[];   // 0..N user UUID
  latitude?: number;         // F11, optional
  longitude?: number;        // F11, optional
}

/** Kết quả tạo post. */
interface CreatePostResult {
  post_id: string;
  expires_at: string;        // ISO 8601
  recipient_count: number;
  created_at: string;        // ISO 8601
}
```

### 2.4 Hằng số

```python
# Thời gian sống của post (free tier MVP — DL-F05-03).
POST_EXPIRY_HOURS = 24
```

```typescript
// Số lần retry upload S3 trước khi báo lỗi (FR-13, AC-F05-7).
const MAX_UPLOAD_RETRIES = 3;
```

---

## 3. API Contracts

Tất cả endpoint yêu cầu Firebase ID token (middleware hiện có).
`firebase_uid` → user UUID nội bộ (theo `_get_user_id` của
`routers/friends.py`).

### 3.1 `POST /posts/upload-url` — lấy presigned URL

**Request**

```jsonc
{ "content_type": "image/jpeg" }   // bắt buộc; thuộc ALLOWED_CONTENT_TYPES
```

**Response 200**

```jsonc
{
  "upload_url": "https://pawsnap.s3...&X-Amz-Signature=...",
  "object_key": "posts/{user_id}/{timestamp}.jpg",
  "cdn_url": "https://cdn.pawsnap.app/posts/{user_id}/{timestamp}.jpg",
  "expires_in": 300
}
```

- Reuse `storage_service.generate_upload_url(user_id,
  prefix="posts", content_type)`. Key do **server** cấp
  (DL-F05-02).
- `content_type` ∉ `ALLOWED_CONTENT_TYPES` → **400**
  `INVALID_CONTENT_TYPE` (giống `profile.create_avatar_upload_url`).

### 3.2 `POST /posts` — tạo post + recipients

**Request**

```jsonc
{
  "s3_key": "posts/{user_id}/{timestamp}.jpg",
  "cdn_url": "https://cdn.pawsnap.app/posts/.../...jpg",
  "recipient_ids": ["<uuid>", "<uuid>"],   // [] hợp lệ (FR-4)
  "latitude": 10.77621500,                  // optional (F11)
  "longitude": 106.69505800                 // optional (F11)
}
```

Validate (Pydantic — DL-F05-06):
- `s3_key`, `cdn_url`: non-empty string.
- `recipient_ids`: list UUID (có thể rỗng); phần tử trùng → de-dup.
- `latitude` ∈ [-90, 90], `longitude` ∈ [-180, 180] nếu có mặt
  → ngoài khoảng ⇒ **422** (F11 §3.1).

**Response 201**

```jsonc
{
  "post_id": "<uuid>",
  "expires_at": "2026-06-23T00:43:00Z",
  "recipient_count": 2,
  "created_at": "2026-06-22T00:43:00Z"
}
```

- **Không** field `latitude/longitude` trong response (F11
  AC-F11-3).
- Người nhận **không phải bạn bè** của Sender → **422**
  `INVALID_RECIPIENT` (DL-F05-07).

### 3.3 Không thuộc F05

- `GET /feed`, `GET /history/*`, `POST /posts/{id}/seen`,
  `GET /posts/{id}/seen-by`: thuộc F06/F07/F08.
- Push notification "new photo": thuộc F09 (DL-F05-05).

---

## 4. Component Breakdown

### 4.1 Backend (FastAPI)

```
backend/app/
├── models/
│   ├── post.py                 # Post ORM
│   └── post_recipient.py       # PostRecipient ORM
├── schemas/
│   └── post.py                 # CreatePostRequest/Response, UploadUrl*
├── services/
│   └── post_service.py         # create_post (+ validate recipients)
├── routers/
│   └── posts.py                # POST /posts/upload-url, POST /posts
└── alembic/versions/
    └── *_create_posts_and_post_recipients.py
```

| Component | Trách nhiệm |
|---|---|
| `Post` | ORM bảng `posts` (§2.1). |
| `PostRecipient` | ORM bảng `post_recipients` (§2.2). |
| `schemas/post.py` | `CreatePostRequest` (validate lat/lng, recipient_ids), `CreatePostResponse`, `PostUploadUrlRequest` (reuse `PresignedUrlResponse`). |
| `post_service.create_post` | Validate recipients là bạn bè; INSERT post (`expires_at`); INSERT recipients (de-dup); trả post + count. |
| `routers/posts.py` | Map request → service; xử lý 400/422; để lại hook F09 sau commit. |

### 4.2 Client (React Native)

```
src/
├── screens/
│   └── RecipientSelectorScreen.tsx   # chọn người nhận + "Gửi"
├── services/
│   ├── SendService.ts                # orchestrate upload → confirm
│   └── __mocks__/SendService.ts      # manual mock cho test screen
└── __tests__/send/
    ├── SendService.test.ts
    └── RecipientSelectorScreen.test.tsx
```

| Component | Trách nhiệm |
|---|---|
| `RecipientSelectorScreen` | Load friends; mặc định chọn hết (FR-2); toggle (FR-3); nút "Gửi" luôn bật (FR-4); gọi `SendService.send`; discard ảnh sau khi gửi (FR-10). |
| `SendService` | `getUploadUrl` → `uploadToS3` (retry 3 — FR-13) → `getCurrentLocation`+`buildLocationPayload` (F11) → `confirm` (`POST /posts`). Backend HTTP injectable/mockable (theo tiền lệ DL-F03-11/DL-F04-03). |

- Upload S3 thực (PUT file binary) abstract sau một hàm
  `uploadBackend` injectable; native fetch/upload tích hợp sau
  (DL-F05-08).

---

## 5. Error Handling Strategy

| Tình huống | Tầng | Xử lý |
|---|---|---|
| `content_type` không hỗ trợ | Backend | 400 `INVALID_CONTENT_TYPE` |
| `latitude/longitude` ngoài khoảng | Backend | 422 (Pydantic) |
| `recipient_id` không phải bạn bè | Backend | 422 `INVALID_RECIPIENT` (DL-F05-07) |
| `recipient_id` trùng lặp | Backend | de-dup, không lỗi |
| 0 người nhận | Backend | Tạo post, không tạo recipients, không push (AC-F05-4) |
| Upload S3 fail tạm thời | Client | retry ≤ 3 (AC-F05-6) |
| Upload S3 fail sau 3 lần | Client | throw → UI báo lỗi; **không** gọi `POST /posts` (AC-F05-7) |
| Push notification fail | Backend (F09) | best-effort, không chặn 201 (DL-F05-05) |

**Nguyên tắc:** `POST /posts` chỉ được gọi **sau khi** upload S3
thành công ⇒ không bao giờ có `posts` trỏ tới object S3 không tồn
tại (AC-F05-7). Notification là best-effort, không ảnh hưởng kết
quả tạo post.

---

## 6. Test Strategy

Backend: `pytest` (SQLite in-memory cho model/service/migration,
theo tiền lệ F03). Client: Jest + RNTL, viết test TRƯỚC
implementation (TDD).

### 6.1 Migration — `test_posts_migration.py`

| Test case | Mô tả |
|---|---|
| `test_posts_table_exists` | Bảng `posts` tồn tại |
| `test_posts_columns` | Đủ cột §2.1 (gồm `latitude`, `longitude`, `expires_at`) |
| `test_posts_fk_to_users` | `user_id` → users |
| `test_post_recipients_table_exists` | Bảng `post_recipients` tồn tại |
| `test_post_recipients_columns` | Đủ cột §2.2 (gồm `seen_at`) |
| `test_post_recipients_fks` | `post_id`→posts, `recipient_id`→users |
| `test_post_recipients_unique_pair` | UNIQUE `(post_id, recipient_id)` |

### 6.2 `post_service` — `test_service_post.py`

| Test case | Mô tả |
|---|---|
| `test_create_post_sets_expiry_24h` | `expires_at ≈ created_at + 24h` (DL-F05-03) |
| `test_create_post_inserts_recipients` | N recipients → N rows `post_recipients` (FR-6, AC-F05-2) |
| `test_create_post_subset` | Chỉ subset được tạo (AC-F05-3) |
| `test_create_post_zero_recipients` | 0 recipient → post tạo, 0 row recipients (FR-7, AC-F05-4) |
| `test_create_post_dedup_recipients` | recipient_ids trùng → de-dup |
| `test_create_post_rejects_non_friend` | recipient không phải bạn → raise `InvalidRecipientError` (DL-F05-07) |
| `test_create_post_stores_latlng` | lat/lng lưu đúng độ chính xác 8 chữ số (F11 AC-F11-1) |
| `test_create_post_null_latlng` | Không truyền lat/lng → cột NULL (F11 AC-F11-2) |

### 6.3 Router — `test_router_posts.py`

| Test case | Mô tả |
|---|---|
| `test_upload_url_returns_presigned` | 200 + `upload_url/object_key/cdn_url` (prefix `posts/`) |
| `test_upload_url_invalid_content_type` | 400 `INVALID_CONTENT_TYPE` |
| `test_create_post_201` | 201 + `post_id/expires_at/recipient_count/created_at` |
| `test_create_post_no_latlng_in_response` | Response **không** chứa lat/lng (F11 AC-F11-3) |
| `test_create_post_zero_recipients_201` | 0 người nhận vẫn 201, `recipient_count = 0` (AC-F05-4) |
| `test_create_post_bad_latlng_422` | lat/lng ngoài khoảng → 422 (F11 §3.1) |
| `test_create_post_non_friend_422` | recipient không phải bạn → 422 `INVALID_RECIPIENT` |

### 6.4 Client — `SendService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_send_happy_path` | gọi upload-url → PUT S3 → POST /posts theo đúng thứ tự, trả `CreatePostResult` (AC-F05-2) |
| `test_send_retries_upload_up_to_3` | upload fail 2 lần rồi thành công → 1 lần `POST /posts` (FR-13, AC-F05-6) |
| `test_send_fails_after_3_retries` | upload fail 3 lần → throw, **không** gọi `POST /posts` (AC-F05-7) |
| `test_send_zero_recipients` | `recipient_ids: []` vẫn gọi `POST /posts` (AC-F05-4) |
| `test_send_merges_location_payload` | có toạ độ → body chứa lat/lng; null → không có field (F11) |

### 6.5 Client — `RecipientSelectorScreen.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_all_friends_selected_by_default` | Mở screen → toàn bộ bạn bè được chọn (FR-2, AC-F05-1) |
| `test_toggle_deselects_recipient` | Bỏ chọn 1 người → không nằm trong danh sách gửi (FR-3, AC-F05-3) |
| `test_send_button_enabled_zero_recipients` | Bỏ chọn hết → nút "Gửi" vẫn bật, gọi `send([])` (FR-4, AC-F05-4) |
| `test_send_invokes_send_service` | Nhấn "Gửi" → `SendService.send(photo, ids)` được gọi |

### 6.6 Integration — `test_post_send_flow.py`

| Test case | Mô tả |
|---|---|
| `test_broadcast_creates_post_and_recipients` | POST /posts với N bạn → 1 post + N recipients (AC-F05-2) |
| `test_subset_creates_only_selected` | subset → chỉ recipients đã chọn (AC-F05-3) |
| `test_zero_recipient_persists_post` | 0 người nhận → post tồn tại, 0 recipients (AC-F05-4) |
| `test_latlng_persisted_not_exposed` | lat/lng lưu DB (8 chữ số) nhưng không có trong response (F11 AC-F11-1, AC-F11-3) |

### 6.7 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F05-1 | `test_all_friends_selected_by_default` |
| AC-F05-2 | `test_create_post_inserts_recipients`, `test_send_happy_path`, `test_broadcast_creates_post_and_recipients`; (push → F09) |
| AC-F05-3 | `test_create_post_subset`, `test_toggle_deselects_recipient`, `test_subset_creates_only_selected` |
| AC-F05-4 | `test_create_post_zero_recipients`, `test_create_post_zero_recipients_201`, `test_send_zero_recipients`, `test_send_button_enabled_zero_recipients`, `test_zero_recipient_persists_post` |
| AC-F05-5 | One-shot/discard kiểm tra ở `RecipientSelectorScreen` (sau gửi không còn ảnh để gửi lại) — xác minh hành vi UI |
| AC-F05-6 | `test_send_retries_upload_up_to_3` |
| AC-F05-7 | `test_send_fails_after_3_retries` |

### 6.8 Ghi chú Test

- Push notification (AC-F05-2 phần "nhận push") được phủ trong
  **F09** (DL-F05-05); F05 chỉ verify post + recipients được tạo.
- Upload S3 thực không test bằng unit; `uploadBackend` được mock
  (DL-F05-08).
- "Trong vòng 5 giây" (AC-F05-2) là yêu cầu hiệu năng end-to-end,
  không cover bằng unit test.
