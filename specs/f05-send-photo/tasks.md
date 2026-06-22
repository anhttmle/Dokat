# F05 — Gửi Ảnh (Multi-Recipient / Broadcast) — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** FastAPI (backend) + React Native/TypeScript (client).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F05 là feature end-to-end đầu tiên (cả client + backend). Tên
> bảng là `posts`/`post_recipients` (DL-F05-01). Push notification
> thuộc F09 (DL-F05-05); F11 cung cấp `LocationService` cho client.

---

## 1. Bootstrap F05 structure + test runner

_Tiên quyết cho mọi task. Không có dependency ngoài._

**Làm:**
- Tạo file skeleton backend (`throw`/`pass` TODO):
  ```
  backend/app/models/post.py
  backend/app/models/post_recipient.py
  backend/app/schemas/post.py
  backend/app/services/post_service.py
  backend/app/routers/posts.py
  backend/tests/migrations/test_posts_migration.py
  backend/tests/test_service_post.py
  backend/tests/test_router_posts.py
  backend/tests/integration/test_post_send_flow.py
  ```
- Tạo file skeleton client:
  ```
  src/services/SendService.ts
  src/services/__mocks__/SendService.ts
  src/screens/RecipientSelectorScreen.tsx
  src/__tests__/send/SendService.test.ts
  src/__tests__/send/RecipientSelectorScreen.test.tsx
  ```
- Định nghĩa interface client: `UploadUrlResult`, `CreatePostBody`,
  `CreatePostResult` (Design §2.3).

**Verify:** `pytest --collect-only` thấy 4 file test backend mới;
`npx jest --listTests` liệt kê 2 file test client mới;
`npx tsc --noEmit` không lỗi type.

**Refs:** Design §4.1, §4.2

---

## 2. Migration + ORM models `posts` & `post_recipients`

_Phụ thuộc Task 1._

**Test trước:** `backend/tests/migrations/test_posts_migration.py`
(SQLite in-memory + `Base.metadata.create_all`, theo tiền lệ
`test_friendships_migration.py`):
- `test_posts_table_exists`, `test_posts_columns` (gồm `latitude`,
  `longitude`, `expires_at`), `test_posts_fk_to_users`.
- `test_post_recipients_table_exists`, `test_post_recipients_columns`
  (gồm `seen_at`), `test_post_recipients_fks`,
  `test_post_recipients_unique_pair`.

**Làm:**
- `models/post.py`: `Post` ORM (Design §2.1) — `latitude
  DECIMAL(11,8)` / `longitude DECIMAL(12,8)` nullable, `expires_at`
  not null.
- `models/post_recipient.py`: `PostRecipient` ORM (Design §2.2) —
  `seen_at` nullable (DL-F05-04), `UNIQUE(post_id, recipient_id)`
  tên `post_recipients_unique_pair`.
- Đăng ký trong `models/__init__.py`.
- Alembic migration `create_posts_and_post_recipients` (down_revision
  = revision mới nhất `e7d2a1f0c4b8`): tạo hai bảng + index
  (`idx_posts_user_id`, `idx_posts_expires_at`,
  `idx_post_recipients_post`, `idx_post_recipients_recipient`).

**Verify:** 7 test migration pass.

**Refs:** Design §2.1, §2.2; FR-5, FR-6; AC-F05-4;
DL-F05-01, DL-F05-03, DL-F05-04; F11 Design §2.3

---

## 3. `schemas/post.py` — request/response + validate

_Phụ thuộc Task 1. Độc lập với Task 2._

**Test trước:** trong `test_router_posts.py` (hoặc test schema
riêng) khẳng định:
- `CreatePostRequest` chấp nhận `recipient_ids: []`.
- `latitude=91` hoặc `longitude=181` → `ValidationError`.
- `latitude/longitude` optional (vắng mặt hợp lệ).

**Làm:**
- `schemas/post.py`:
  - `PostUploadUrlRequest { content_type: str }` (hoặc reuse
    `PresignedUrlRequest`).
  - `CreatePostRequest { s3_key, cdn_url, recipient_ids: list[UUID]
    = [], latitude: float|None (ge=-90, le=90), longitude:
    float|None (ge=-180, le=180) }` (DL-F05-06).
  - `CreatePostResponse { post_id, expires_at, recipient_count,
    created_at }` — **không** có lat/lng (F11 AC-F11-3).

**Verify:** test validate schema pass (422 cho lat/lng sai khoảng).

**Refs:** Design §2.3, §3.2; DL-F05-06; F11 §3.1, AC-F11-3

---

## 4. `post_service.create_post`

_Phụ thuộc Task 2 và Task 3._

**Test trước:** `backend/tests/test_service_post.py` (SQLite +
seed users/friendships):
- `test_create_post_sets_expiry_24h` — `expires_at ≈ created_at +
  24h` (DL-F05-03).
- `test_create_post_inserts_recipients` — N bạn → N rows.
- `test_create_post_subset` — chỉ subset.
- `test_create_post_zero_recipients` — post tạo, 0 row recipients.
- `test_create_post_dedup_recipients` — id trùng → de-dup.
- `test_create_post_rejects_non_friend` — recipient không phải bạn
  → `InvalidRecipientError` (DL-F05-07).
- `test_create_post_stores_latlng` / `test_create_post_null_latlng`
  (F11 AC-F11-1, AC-F11-2).

**Làm:**
- `post_service.py`:
  - `class InvalidRecipientError(Exception)`.
  - `create_post(db, *, user_id, s3_key, cdn_url, recipient_ids,
    latitude=None, longitude=None)`:
    1. De-dup `recipient_ids`.
    2. Validate mỗi recipient là bạn của `user_id` (query
       `friendships`); sai → `InvalidRecipientError` (DL-F05-07).
    3. INSERT `Post` (`expires_at = now()+POST_EXPIRY_HOURS`).
    4. INSERT `PostRecipient` cho từng recipient.
    5. Commit; trả `(post, recipient_count)`.
  - Hằng `POST_EXPIRY_HOURS = 24`.
  - **Không** gửi push (để hook F09 — DL-F05-05).

**Verify:** 8 test service pass.

**Refs:** Design §1.1–§1.3, §2.4; FR-5, FR-6, FR-7, FR-11;
AC-F05-2, AC-F05-3, AC-F05-4; DL-F05-03, DL-F05-05, DL-F05-07

---

## 5. `routers/posts.py` — `POST /posts/upload-url` + `POST /posts`

_Phụ thuộc Task 4. Đăng ký router trong `main.py`._

**Test trước:** `backend/tests/test_router_posts.py`
(theo tiền lệ `test_router_friends.py`, mock service/storage):
- `test_upload_url_returns_presigned` (prefix `posts/`).
- `test_upload_url_invalid_content_type` → 400.
- `test_create_post_201` (đủ field response).
- `test_create_post_no_latlng_in_response` (F11 AC-F11-3).
- `test_create_post_zero_recipients_201` (`recipient_count = 0`).
- `test_create_post_bad_latlng_422`.
- `test_create_post_non_friend_422` (`INVALID_RECIPIENT`).

**Làm:**
- `routers/posts.py` (prefix `/posts`):
  - `POST /upload-url` → `storage_service.generate_upload_url(
    user_id=firebase_uid, prefix="posts", content_type)`; bắt
    `InvalidContentTypeError` → 400 (DL-F05-02).
  - `POST ""` → resolve user UUID (như `_get_user_id`); gọi
    `post_service.create_post`; bắt `InvalidRecipientError` → 422
    `INVALID_RECIPIENT`; trả 201 `CreatePostResponse`.
  - Sau commit recipients: chừa **hook F09** (comment rõ ràng,
    không gọi FCM — DL-F05-05).
- `main.py`: `app.include_router(posts_router)`.

**Verify:** 7 test router pass.

**Refs:** Design §3.1, §3.2, §5; FR-4, FR-5, FR-9;
AC-F05-4; DL-F05-02, DL-F05-05, DL-F05-07; F11 §3.1, AC-F11-3

---

## 6. `SendService` — orchestrate upload → confirm (+ retry)

_Phụ thuộc Task 1 (client). Độc lập với backend tasks._

**Test trước:** `src/__tests__/send/SendService.test.ts`
(mock `uploadBackend`, `fetch`, `LocationService`):
- `test_send_happy_path` — gọi upload-url → PUT S3 → POST /posts
  đúng thứ tự, trả `CreatePostResult` (AC-F05-2).
- `test_send_retries_upload_up_to_3` — PUT fail 2 lần rồi OK → đúng
  1 lần `POST /posts` (FR-13, AC-F05-6).
- `test_send_fails_after_3_retries` — PUT fail 3 lần → throw,
  **không** gọi `POST /posts` (AC-F05-7).
- `test_send_zero_recipients` — `recipient_ids: []` vẫn gọi
  `POST /posts` (AC-F05-4).
- `test_send_merges_location_payload` — có toạ độ → body có lat/lng;
  null → không field (F11).

**Làm:**
- `SendService.ts`:
  - `send(photo, recipientIds, { uploadBackend? })`:
    1. `POST /posts/upload-url` `{ content_type: 'image/jpeg' }`.
    2. `uploadToS3(upload_url, photo.localUri)` với retry ≤
       `MAX_UPLOAD_RETRIES = 3` (FR-13).
    3. `LocationService.getCurrentLocation()` →
       `buildLocationPayload()` (F11).
    4. `POST /posts` `{ s3_key: object_key, cdn_url, recipient_ids,
       ...latlng }` → trả `CreatePostResult`.
  - Auth header qua `AuthService.getIdToken()` (như SocialService).
  - `uploadBackend` injectable (DL-F05-08).
- `__mocks__/SendService.ts`: manual mock cho test screen.

**Verify:** 5 test pass.

**Refs:** Design §1.1, §1.4, §2.3, §4.2, §5; FR-5, FR-13;
AC-F05-2, AC-F05-6, AC-F05-7; DL-F05-08; F11 (LocationService)

---

## 7. `RecipientSelectorScreen` — chọn người nhận + gửi

_Phụ thuộc Task 6._

**Test trước:** `src/__tests__/send/RecipientSelectorScreen.test.tsx`
(mock `SocialService.getFriends`, `SendService`):
- `test_all_friends_selected_by_default` (FR-2, AC-F05-1).
- `test_toggle_deselects_recipient` (FR-3, AC-F05-3).
- `test_send_button_enabled_zero_recipients` — bỏ chọn hết → nút
  "Gửi" bật, gọi `send(photo, [])` (FR-4, AC-F05-4).
- `test_send_invokes_send_service` — nhấn "Gửi" →
  `SendService.send` được gọi với ids đã chọn.

**Làm:**
- `RecipientSelectorScreen.tsx`:
  - `useEffect`: `SocialService.getFriends()`; init state chọn
    **toàn bộ** (FR-2).
  - Toggle từng người (FR-3); nút "Gửi" **luôn enabled** (FR-4).
  - Nhấn "Gửi" → `SendService.send(photo, selectedIds)`; sau thành
    công hiển thị "Đã gửi" + không giữ ảnh để gửi lại (one-shot,
    FR-10, FR-12, AC-F05-5).

**Verify:** 4 test pass.

**Refs:** Design §1.1–§1.3, §4.2; FR-1, FR-2, FR-3, FR-4, FR-10,
FR-12; AC-F05-1, AC-F05-3, AC-F05-4, AC-F05-5

---

## 8. Integration test — end-to-end create post flow

_Phụ thuộc Task 5 (router + service + migration)._

**Test trước = nội dung task:**
`backend/tests/integration/test_post_send_flow.py` (theo tiền lệ
`tests/integration/`, seed users + friendships, mock S3/storage):
- `test_broadcast_creates_post_and_recipients` — POST /posts với N
  bạn → 1 `posts` + N `post_recipients` (AC-F05-2).
- `test_subset_creates_only_selected` (AC-F05-3).
- `test_zero_recipient_persists_post` — 0 người nhận → post tồn
  tại, 0 recipients (AC-F05-4).
- `test_latlng_persisted_not_exposed` — lat/lng lưu DB đúng 8 chữ
  số nhưng **không** xuất hiện trong response (F11 AC-F11-1,
  AC-F11-3).

**Verify:** 4 integration test pass.

**Refs:** Design §6.6, §6.7; AC-F05-2, AC-F05-3, AC-F05-4;
F11 AC-F11-1, AC-F11-3; DL-F05-01

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **Push notification "new photo"** (FR-9, phần "nhận push" của
  AC-F05-2): hiện thực + test trong **F09** tại điểm hook của
  `post_service` (DL-F05-05).
- **Logic "seen"** (`post_recipients.seen_at`): thuộc **F07**; F05
  chỉ tạo cột (DL-F05-04).
- **Đọc dữ liệu** (`GET /feed`, history, seen-by): thuộc F06/F07/F08.
- **Tích hợp native upload S3 thực** (PUT binary, progress) +
  permission location thực: task triển khai sau (DL-F05-08, F11
  DL-F11-02).
- **Hợp nhất `posts` ↔ stub `photos` của F02**: out-of-scope F05
  (DL-F05-01).
