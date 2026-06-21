# F02 — Owner Profile & Pet Profile — Design

**Version:** 1.0.0
**Date:** 2026-06-21
**Status:** Draft

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                  React Native Client                   │
│                                                        │
│  ┌─────────────────┐   ┌───────────────────────────┐  │
│  │  ProfileService │   │       PetAIService        │  │
│  │  (API calls)    │   │  (on-device inference)    │  │
│  └────────┬────────┘   └───────────────────────────┘  │
│           │                     ▲                      │
│           │                     │ image bytes          │
│  ┌────────▼────────────────────┐│                      │
│  │  usePetStore / useUserStore ││                      │
│  │  (Zustand state)            ││                      │
│  └─────────────────────────────┘│                      │
└──────────────┬──────────────────┘                      │
               │ Firebase ID Token (every request)
               ▼
┌──────────────────────────────────────────┐
│           FastAPI Backend                │
│                                          │
│  AuthMiddleware (inject firebase_uid)    │
│  ┌───────────────┐  ┌─────────────────┐  │
│  │ ProfileRouter │  │   PetsRouter    │  │
│  └───────┬───────┘  └────────┬────────┘  │
│          │                   │           │
│  ┌───────▼───────────────────▼────────┐  │
│  │  ProfileService  /  PetService     │  │
│  └───────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  StorageService (presigned URL)  │    │
│  └──────────────────┬───────────────┘    │
│                     │ boto3              │
│  ┌──────────────────▼───────────────┐    │
│  │        PostgreSQL                │    │
│  │  users | pet_profiles            │    │
│  └──────────────────────────────────┘    │
└──────────────────────┬───────────────────┘
                       │ boto3 / AWS SDK
                       ▼
          ┌────────────────────────┐
          │   AWS S3 (avatars/)    │
          │   via CloudFront CDN   │
          └────────────────────────┘
```

### Luồng chính

**Owner Profile — auto-fill khi link OAuth:**
1. `POST /auth/link` (F01) hoàn thành → Firebase ID Token chứa
   `display_name` và `photo_url` từ provider.
2. Backend `AuthService` (F01) upsert vào cột `display_name` và
   `avatar_url` trong bảng `users` nếu các cột đang `NULL`.
3. Nếu user sau đó chủ động sửa → `PATCH /profile/me` ghi đè.

**Owner Profile — thay ảnh đại diện:**
1. Client gọi `POST /profile/me/avatar/upload-url`
   → Backend trả `{ upload_url, object_key }` (presigned PUT, TTL 5 min).
2. Client PUT ảnh thẳng lên S3 qua `upload_url`.
3. Client gọi `PATCH /profile/me` với
   `{ avatar_url: "<CloudFront URL>" }` để lưu URL chính thức.

**Pet Profile — tạo mới:**
1. Client chọn ảnh → `PetAIService` chạy inference on-device
   (≤ 3 giây) → trả về `{ species, gender, confidence }`.
2. Client pre-fill form; gender chỉ fill nếu confidence ≥ 0.70.
3. Người dùng có thể sửa trước khi submit.
4. Client gọi `POST /pets/avatar/upload-url` → upload ảnh lên S3.
5. Client gọi `POST /pets` với đầy đủ fields và `avatar_url`.
6. Backend kiểm tra giới hạn 1 pet/free user trước khi insert.

**Gán ảnh feed vào Pet (pre-selection trên camera UI — F04):**
1. User mở camera (F04) → `PetSelectorChip` hiển thị tên pet
   đang active phía trên shutter button (hoặc "Không gán" nếu
   chưa chọn).
2. User tap vào chip → `PetPickerOverlay` trượt lên, liệt kê
   danh sách pet + tuỳ chọn "Tạo pet mới" + "Không gán".
3. User chọn xong → overlay đóng, chip cập nhật, `pet_id`
   được giữ trong state camera.
4. User bấm chụp → F04 gửi ảnh kèm `pet_id` (nullable) trong
   payload `POST /photos` (F05 định nghĩa).
5. Backend lưu ảnh với `photos.pet_id` được set ngay, không
   cần bước link riêng.

`PATCH /pets/{pet_id}/link-photo` vẫn tồn tại để hỗ trợ
gán thủ công từ timeline hoặc history (xem F08).
---

## 2. Data Models / Schema

### 2.1 Bảng `users` (kế thừa F01, thêm ghi chú)

Không thêm bảng `owner_profiles` riêng. Owner Profile là tập
con của bảng `users` đã có.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `firebase_uid` | VARCHAR(128) UNIQUE | |
| `is_anonymous` | BOOLEAN | |
| `display_name` | VARCHAR(100) | Nullable; auto-fill từ OAuth hoặc user sửa |
| `avatar_url` | TEXT | Nullable; CloudFront URL hoặc OAuth avatar |
| `force_link_at` | TIMESTAMPTZ | Xem F01 |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Không cần migration nếu F01 đã tạo đủ cột. Nếu cần, chỉ
thêm index cho `display_name` khi có tính năng search (ngoài
phạm vi MVP).

---

### 2.2 Bảng `pet_profiles` (mới)

```sql
CREATE TYPE pet_species AS ENUM ('dog', 'cat');
CREATE TYPE pet_gender  AS ENUM ('male', 'female', 'unknown');

CREATE TABLE pet_profiles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    species     pet_species NOT NULL,
    gender      pet_gender  NOT NULL DEFAULT 'unknown',
    birthdate   DATE,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pet_profiles_user_id ON pet_profiles(user_id);
```

- `user_id`: 1 user có thể có nhiều pet, nhưng backend giới
  hạn 1 pet/free user ở tầng service.
- `gender = 'unknown'` là giá trị mặc định khi AI không đủ
  tự tin (confidence < 70%) và người dùng không chọn.
- `birthdate`: tùy chọn, không bắt buộc.
- `avatar_url`: CloudFront URL; `NULL` nếu không upload ảnh.

---

### 2.3 Pet Photo Timeline (phụ thuộc F04/F05)

Mỗi Pet Profile có một **timeline ảnh riêng** — bộ sưu tập
tất cả ảnh đã được gán vào pet đó (qua F04 capture hoặc
thêm thủ công).

Bảng `photos` sẽ được định nghĩa đầy đủ trong F04/F05.
F02 yêu cầu bảng đó có cột:

```sql
-- Thêm vào bảng `photos` (F04/F05 định nghĩa):
pet_id UUID REFERENCES pet_profiles(id) ON DELETE SET NULL
```

**Index cần thêm vào `photos` để query timeline hiệu quả:**
```sql
CREATE INDEX idx_photos_pet_timeline
    ON photos(pet_id, taken_at DESC NULLS LAST)
    WHERE pet_id IS NOT NULL;
```

**Query timeline của một pet:**
```sql
SELECT id, cdn_url, taken_at, created_at
FROM   photos
WHERE  pet_id = :pet_id
ORDER  BY taken_at DESC NULLS LAST, created_at DESC;
```

**Quan hệ:** Một ảnh thuộc tối đa 1 pet (nullable FK).
Một pet có thể có nhiều ảnh không giới hạn.

**Nguồn ảnh vào timeline:**
- Pre-selected trên camera UI (F04): `pet_id` được gửi kèm
  payload chụp, backend lưu trực tiếp — không cần bước
  thêm sau chụp.
- Gán thủ công sau qua `PATCH /pets/{id}/link-photo` (từ
  timeline view hoặc history F08).

**Avatar vs. timeline:**
- `pet_profiles.avatar_url` — ảnh đại diện hiển thị trên
  Profile; được chọn khi tạo, có thể thay sau.
- Timeline — toàn bộ ảnh feed được tag vào pet, sắp xếp
  theo thời gian; **không nhất thiết** phải trùng với avatar.

---

## 3. API Contracts

Token xác thực: `Authorization: Bearer <Firebase ID Token>`
ở **tất cả** endpoint. `AuthMiddleware` inject `firebase_uid`
vào request context.

---

### 3.1 `GET /profile/me`

Lấy Owner Profile của user hiện tại.

**Response 200:**
```json
{
  "user_id": "uuid-...",
  "display_name": "Nguyen Van A",
  "avatar_url": "https://cdn.pawsnap.app/avatars/users/uuid-.../abc.jpg",
  "is_anonymous": false,
  "providers": ["google"]
}
```

**Response 401:** Token không hợp lệ.

---

### 3.2 `PATCH /profile/me`

Cập nhật các trường Owner Profile có thể sửa.

**Request body:**
```json
{
  "display_name": "Nguyen Van B",
  "avatar_url": "https://cdn.pawsnap.app/avatars/users/uuid-.../new.jpg"
}
```

- Tất cả trường đều tùy chọn (partial update).
- `avatar_url` phải là CloudFront URL hoặc `null`.

**Response 200:** Trả về object giống `GET /profile/me`.

**Response 422:** Validation lỗi (display_name quá dài, v.v.).

---

### 3.3 `POST /profile/me/avatar/upload-url`

Tạo presigned PUT URL để upload ảnh đại diện của Owner
lên S3.

**Request body:**
```json
{ "content_type": "image/jpeg" }
```

`content_type` phải là một trong:
`image/jpeg`, `image/png`, `image/webp`.

**Response 200:**
```json
{
  "upload_url": "https://s3.amazonaws.com/pawsnap/avatars/users/uuid-.../ts.jpg?X-Amz-...",
  "object_key": "avatars/users/uuid-.../1719000000.jpg",
  "cdn_url": "https://cdn.pawsnap.app/avatars/users/uuid-.../1719000000.jpg",
  "expires_in": 300
}
```

Client dùng `upload_url` để PUT, sau đó dùng `cdn_url` để
gọi `PATCH /profile/me`.

**Response 400:** `content_type` không hợp lệ.

---

### 3.4 `GET /pets`

Liệt kê tất cả Pet Profiles của user hiện tại.

**Response 200:**
```json
{
  "pets": [
    {
      "id": "uuid-...",
      "name": "Mochi",
      "species": "dog",
      "gender": "male",
      "birthdate": "2022-03-15",
      "avatar_url": "https://cdn.pawsnap.app/avatars/pets/uuid-.../mochi.jpg",
      "created_at": "2026-06-21T09:00:00Z"
    }
  ]
}
```

---

### 3.5 `POST /pets`

Tạo Pet Profile mới.

**Request body:**
```json
{
  "name": "Mochi",
  "species": "dog",
  "gender": "male",
  "birthdate": "2022-03-15",
  "avatar_url": "https://cdn.pawsnap.app/avatars/pets/uuid-.../mochi.jpg"
}
```

| Field | Bắt buộc | Ràng buộc |
|---|---|---|
| `name` | Có | 1–100 ký tự |
| `species` | Có | `dog` hoặc `cat` |
| `gender` | Không | `male`, `female`, `unknown` (default) |
| `birthdate` | Không | Không trong tương lai |
| `avatar_url` | Không | CloudFront URL |

**Response 201:**
```json
{
  "id": "uuid-...",
  "name": "Mochi",
  "species": "dog",
  "gender": "male",
  "birthdate": "2022-03-15",
  "avatar_url": "https://cdn.pawsnap.app/...",
  "created_at": "2026-06-21T09:00:00Z"
}
```

**Response 403:**
```json
{
  "error": "PET_LIMIT_REACHED",
  "message": "Free users can only have 1 pet profile."
}
```

**Response 422:** Validation lỗi.

---

### 3.6 `GET /pets/{pet_id}`

Lấy chi tiết một Pet Profile.

**Response 200:** Object giống một phần tử trong `GET /pets`.
**Response 404:** Pet không tồn tại hoặc không thuộc user.

---

### 3.7 `PATCH /pets/{pet_id}`

Cập nhật Pet Profile (partial update).

**Request body:** Các trường tùy chọn — `name`, `species`,
`gender`, `birthdate`, `avatar_url`.

**Response 200:** Object pet đã cập nhật.
**Response 404:** Pet không tồn tại hoặc không thuộc user.
**Response 422:** Validation lỗi.

---

### 3.8 `POST /pets/avatar/upload-url`

Tạo presigned PUT URL để upload avatar cho Pet.

**Request body:**
```json
{ "content_type": "image/jpeg" }
```

**Response 200:**
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "object_key": "avatars/pets/uuid-user/uuid-tmp/1719000000.jpg",
  "cdn_url": "https://cdn.pawsnap.app/avatars/pets/...",
  "expires_in": 300
}
```

**Ghi chú:** `object_key` dùng `uuid-user` vì `pet_id` chưa
tồn tại tại thời điểm upload. Client truyền `cdn_url` vào
`POST /pets` sau khi tạo.

---

### 3.9 `PATCH /pets/{pet_id}/link-photo`

Gán một ảnh feed (từ F04/F05) vào Pet Profile.

**Request body:**
```json
{ "photo_id": "uuid-photo-..." }
```

**Response 200:**
```json
{
  "pet_id": "uuid-...",
  "photo_id": "uuid-photo-...",
  "linked_at": "2026-06-21T09:30:00Z"
}
```

**Response 404:** `pet_id` không thuộc user, hoặc `photo_id`
không tồn tại / không thuộc user.

**Response 409:** Ảnh đã gán vào pet khác trước đó (ảnh chỉ
thuộc tối đa 1 pet).

---

### 3.10 `GET /pets/{pet_id}/photos`

Lấy timeline ảnh của một Pet Profile, phân trang theo
cursor.

**Query params:**

| Param | Mặc định | Mô tả |
|---|---|---|
| `limit` | 20 | Số ảnh tối đa trả về; max 50 |
| `before` | — | `taken_at` cursor (ISO 8601); lấy ảnh cũ hơn |

**Response 200:**
```json
{
  "pet_id": "uuid-...",
  "photos": [
    {
      "photo_id": "uuid-photo-...",
      "cdn_url": "https://cdn.pawsnap.app/photos/...",
      "taken_at": "2026-06-20T08:00:00Z"
    }
  ],
  "next_cursor": "2026-06-10T08:00:00Z",
  "has_more": true
}
```

- `next_cursor`: giá trị `taken_at` của ảnh cuối cùng trong
  page; truyền vào `before` để lấy page tiếp theo.
- `has_more`: `false` khi đã hết ảnh.
- Chỉ trả ảnh của pet thuộc user hiện tại.

**Response 404:** `pet_id` không tồn tại hoặc không thuộc
user.

---

## 4. Component Breakdown

### 4.1 Client (React Native)

| Component | Trách nhiệm |
|---|---|
| `ProfileService` | API calls: `GET/PATCH /profile/me`, presigned URL, CRUD pets, `GET /pets/{id}/photos`, link-photo |
| `PetAIService` | Chạy on-device inference: nhận ảnh → trả `{ species, gender, confidence }` |
| `StorageUploader` | PUT ảnh lên S3 presigned URL, retry 3 lần khi lỗi mạng |
| `ProfileScreen` | Hiển thị Owner Profile + danh sách Pet Profiles |
| `EditOwnerProfileSheet` | Bottom sheet: sửa `display_name`, thay ảnh đại diện |
| `CreatePetProfileSheet` | Multi-step: chọn ảnh → AI fill → form điền → submit |
| `EditPetProfileSheet` | Sửa thông tin pet đã có |
| `PetTimelineScreen` | Hiển thị timeline ảnh của 1 pet; infinite scroll qua cursor pagination |
| `PetSelectorChip` | Chip nhỏ phía trên shutter button (F04 camera UI); hiển thị pet đang chọn |
| `PetPickerOverlay` | Bottom sheet trượt lên khi tap chip; liệt kê pet + "Tạo pet mới" + "Không gán" |
| `usePetStore` | Zustand: `{ pets[], activePetId, loading }` |
| `useProfileStore` | Zustand: `{ ownerProfile, loading }` |

**Luồng `CreatePetProfileSheet`:**
```
Step 1: Chọn ảnh (camera / gallery)
         └─► PetAIService.infer(image)   ≤ 3s
              └─► species, gender (nếu confidence ≥ 0.70)
Step 2: Form hiển thị AI kết quả (editable)
         ├── name (text input)
         ├── species (pre-filled, editable)
         ├── gender  (pre-filled nếu confident, editable)
         └── birthdate (date picker, optional)
Step 3: Submit
         ├── StorageUploader.upload(image, presigned_url)
         └── ProfileService.createPet({ ...fields, avatar_url })
```

### 4.2 Backend (FastAPI)

| Component | Trách nhiệm |
|---|---|
| `app/routers/profile.py` | `GET/PATCH /profile/me`, `POST /profile/me/avatar/upload-url` |
| `app/routers/pets.py` | CRUD `/pets`, `POST /pets/avatar/upload-url`, `PATCH /pets/{id}/link-photo`, `GET /pets/{id}/photos` |
| `app/services/profile_service.py` | Đọc/ghi `users` (display_name, avatar_url); upsert từ OAuth |
| `app/services/pet_service.py` | Tạo/đọc/sửa pet; enforce 1-pet limit; link photo; query timeline |
| `app/services/storage_service.py` | Generate presigned PUT URL (boto3); build CloudFront URL |
| `app/models/pet_profile.py` | SQLAlchemy ORM model cho `pet_profiles` |
| `app/schemas/profile.py` | Pydantic schemas: `OwnerProfileResponse`, `PatchOwnerProfileRequest` |
| `app/schemas/pet.py` | Pydantic schemas: `PetResponse`, `CreatePetRequest`, `PatchPetRequest`, `PetPhotosResponse` |

**Giới hạn pet — logic trong `pet_service.py`:**
```
def assert_can_create_pet(user_id):
    count = db.query(PetProfile).filter_by(user_id=user_id).count()
    if count >= FREE_USER_PET_LIMIT:   # FREE_USER_PET_LIMIT = 1
        raise PetLimitReachedException()
```

---

## 5. Error Handling Strategy

### 5.1 Phân loại lỗi

| Tình huống | HTTP Status | Error Code | Hành động client |
|---|---|---|---|
| Token thiếu / sai / hết hạn | 401 | (xem F01) | Xem F01 |
| Pet không thuộc user hiện tại | 404 | `PET_NOT_FOUND` | Hiển thị thông báo, quay về |
| Vượt giới hạn 1 pet (free) | 403 | `PET_LIMIT_REACHED` | Hiển thị upsell / thông báo |
| Ảnh đã gán vào pet khác | 409 | `PHOTO_ALREADY_LINKED` | Hỏi user có muốn chuyển pet không |
| `content_type` không hợp lệ | 400 | `INVALID_CONTENT_TYPE` | Thông báo chọn lại ảnh |
| Validation thất bại | 422 | (field-level errors) | Highlight trường lỗi trên form |
| S3 / CloudFront không trả về | 503 | `STORAGE_UNAVAILABLE` | Retry sau, thông báo lỗi |

### 5.2 Format lỗi chuẩn (nhất quán với F01)

```json
{
  "error": "PET_LIMIT_REACHED",
  "message": "Free users can only have 1 pet profile."
}
```

- Production: không expose stack trace.
- Không log `avatar_url` đầy đủ hay bất kỳ PII nào.

### 5.3 Retry strategy (client)

- Upload S3 (PUT) thất bại do mạng: retry tối đa 3 lần với
  backoff 1s → 2s → 4s trước khi báo lỗi.
- `503 STORAGE_UNAVAILABLE`: thông báo lỗi, không retry tự
  động (URL đã hết hạn sau 5 phút).
- `409 PHOTO_ALREADY_LINKED`: không retry, hiển thị dialog
  xác nhận chuyển gán.

---

## 6. Test Strategy

### 6.1 Unit Tests — Backend

| Test | Kiểm tra |
|---|---|
| `test_get_owner_profile` | `GET /profile/me` → trả đúng `display_name`, `avatar_url` từ `users` |
| `test_patch_display_name` | `PATCH /profile/me` với `display_name` mới → cập nhật DB |
| `test_patch_avatar_url` | `PATCH /profile/me` với `avatar_url` mới → cập nhật DB |
| `test_patch_owner_profile_partial` | Chỉ gửi `display_name` → `avatar_url` không thay đổi |
| `test_create_pet_success` | `POST /pets` hợp lệ → insert `pet_profiles`, trả 201 |
| `test_create_pet_limit_reached` | User đã có 1 pet → `POST /pets` → 403 `PET_LIMIT_REACHED` |
| `test_create_pet_no_gender` | Không truyền `gender` → default `unknown` |
| `test_create_pet_future_birthdate` | `birthdate` > today → 422 |
| `test_get_pets_empty` | User chưa có pet → `GET /pets` → `{ pets: [] }` |
| `test_get_pet_not_owned` | `GET /pets/{id}` của user khác → 404 |
| `test_patch_pet_partial` | Sửa `name` → các trường khác không đổi |
| `test_link_photo_success` | `PATCH /pets/{id}/link-photo` hợp lệ → UPDATE `photos.pet_id` |
| `test_link_photo_already_linked` | Ảnh đã có `pet_id` ≠ NULL → 409 `PHOTO_ALREADY_LINKED` |
| `test_get_pet_photos_empty` | Pet chưa có ảnh → `GET /pets/{id}/photos` → `{ photos: [], has_more: false }` |
| `test_get_pet_photos_ordered` | 3 ảnh gán vào pet → trả đúng thứ tự `taken_at DESC` |
| `test_get_pet_photos_pagination` | Có 25 ảnh, `limit=20` → trả 20 ảnh, `has_more=true`, `next_cursor` đúng |
| `test_get_pet_photos_before_cursor` | Truyền `before=<cursor>` → chỉ trả ảnh cũ hơn cursor |
| `test_get_pet_photos_not_owned` | `GET /pets/{id}/photos` của pet khác user → 404 |
| `test_presigned_url_owner_avatar` | `POST /profile/me/avatar/upload-url` → trả URL S3 hợp lệ |
| `test_presigned_url_invalid_type` | `content_type = "video/mp4"` → 400 `INVALID_CONTENT_TYPE` |
| `test_oauth_autofill_display_name` | `POST /auth/link` (F01) → `users.display_name` được fill từ token |

### 6.2 Integration Tests — Backend

- Dùng mocked S3 (moto) để test presigned URL flow mà
  không cần AWS thật.
- Test full create-pet flow: `POST /pets/avatar/upload-url` →
  (mock PUT) → `POST /pets` → `GET /pets` → verify DB state.

### 6.3 E2E / Acceptance Tests — map từ AC

| AC | Test scenario |
|---|---|
| AC-F02-1 | App lần đầu → không màn hình nào yêu cầu Owner/Pet Profile |
| AC-F02-2 | Link Google → `GET /profile/me` trả `display_name` + `avatar_url` từ Google |
| AC-F02-3 | Upload ảnh chó → AI fill `species=dog`; gender fill nếu confidence ≥ 0.70 |
| AC-F02-4 | AI fill `species=cat` → user sửa thành `dog` → `POST /pets` lưu `dog` |
| AC-F02-5 | Free user có 1 pet → `POST /pets` → 403 với message đúng |
| AC-F02-6 | Mở camera → `PetSelectorChip` hiển thị → tap → `PetPickerOverlay` liệt kê pets → chọn pet → chụp → ảnh có `pet_id` đúng; chọn "Không gán" → `pet_id = NULL` |
| AC-F02-7 | User không có pet → dùng feed, gửi ảnh, kết bạn không bị chặn |

### 6.4 Coverage target

- `pet_service.py` (bao gồm limit check, link-photo): ≥ 80%.
- `profile_service.py`: ≥ 80%.
- `storage_service.py`: ≥ 80% (dùng mock S3).
- `StorageUploader` (client): test retry logic với mock network.
