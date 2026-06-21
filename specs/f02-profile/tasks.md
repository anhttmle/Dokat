# F02 — Owner Profile & Pet Profile — Tasks

**Refs:** `requirements.md`, `design.md`
**Stack:** FastAPI (Python) + React Native (TypeScript)
**Convention:** viết test TRƯỚC implementation trong mỗi task.

---

## 1. Bootstrap F02 structure + test runner

_Tiên quyết cho tất cả task còn lại. Không có dependency ngoài._

### 1.1 Scaffold backend F02 modules

**Làm:**
- Tạo các file skeleton (pass/empty) trong backend:
  ```
  app/
    models/pet_profile.py
    routers/profile.py
    routers/pets.py
    schemas/profile.py
    schemas/pet.py
    services/profile_service.py
    services/pet_service.py
    services/storage_service.py
  tests/
    test_router_profile.py
    test_router_pets.py
    test_service_pet.py
    test_service_storage.py
  ```
- Đăng ký `profile` và `pets` router vào `app/main.py`.
- Thêm dependencies mới vào `requirements.txt`: `boto3`,
  `moto[s3]` (cho test S3 mock).

**Verify:** `make test` chạy thành công — collect đúng các
file test mới, 0 lỗi import.

**Refs:** Design §4.2

---

### 1.2 Scaffold client F02 modules

**Làm:**
- Tạo các file skeleton trong React Native project:
  ```
  src/
    services/
      ProfileService.ts
    services/ai/
      PetAIService.ts
    stores/
      usePetStore.ts
      useProfileStore.ts
    screens/profile/
      ProfileScreen.tsx
      PetTimelineScreen.tsx
    components/profile/
      EditOwnerProfileSheet.tsx
      CreatePetProfileSheet.tsx
      EditPetProfileSheet.tsx
    components/camera/
      PetSelectorChip.tsx
      PetPickerOverlay.tsx
    __tests__/profile/
      ProfileService.test.ts
      PetAIService.test.ts
      usePetStore.test.ts
      CreatePetProfileSheet.test.tsx
      PetSelectorChip.test.tsx
  ```
- Mock `ProfileService` và `PetAIService` trong
  `jest.config.js` / `__mocks__/`.

**Verify:** `npx jest --listTests` liệt kê đúng các file
test mới. `npx tsc --noEmit` không báo lỗi type.

**Refs:** Design §4.1

---

## 2. Migration: bảng `pet_profiles`

_Độc lập. Cần chạy trước mọi integration test backend._

### 2.1 Alembic migration

**Test trước:**
```python
# tests/test_migration.py
def test_pet_profiles_table_exists(db_engine):
    inspector = inspect(db_engine)
    assert "pet_profiles" in inspector.get_table_names()

def test_pet_profiles_columns(db_engine):
    cols = {c["name"] for c in
            inspect(db_engine).get_columns("pet_profiles")}
    assert cols >= {
        "id", "user_id", "name", "species",
        "gender", "birthdate", "avatar_url",
        "created_at", "updated_at",
    }

def test_pet_profiles_fk_to_users(db_engine):
    fks = inspect(db_engine).get_foreign_keys("pet_profiles")
    assert any(fk["referred_table"] == "users" for fk in fks)
```

**Làm:**
- Tạo Alembic revision tạo `pet_species` enum,
  `pet_gender` enum và bảng `pet_profiles`.
- Thêm `CREATE INDEX idx_pet_profiles_user_id`.

**Verify:** `make migrate` chạy thành công. 3 test trên pass.

**Refs:** Design §2.2; FR-3

---

### 2.2 SQLAlchemy ORM model

**Test trước:**
```python
def test_orm_create_pet_profile(db_session, seed_user):
    pet = PetProfile(
        user_id=seed_user.id,
        name="Mochi",
        species="dog",
    )
    db_session.add(pet)
    db_session.commit()
    assert pet.id is not None
    assert pet.gender == "unknown"   # default
    assert pet.avatar_url is None
```

**Làm:**
- Implement `app/models/pet_profile.py`: class `PetProfile`
  kế thừa `Base`, map đầy đủ cột từ schema 2.1.
- Export model trong `app/models/__init__.py`.

**Verify:** Test trên pass. `mypy app/models/pet_profile.py`
không báo lỗi.

**Refs:** Design §2.2

---

## 3. Owner Profile API

_Phụ thuộc: Task 1, 2 (users table từ F01 đã tồn tại)._

### 3.1 Viết tests Owner Profile

**Làm:** Trong `tests/test_router_profile.py`, viết đủ 5 test:

```python
test_get_owner_profile_returns_display_name()
# GET /profile/me → 200, trả display_name và avatar_url từ users

test_get_owner_profile_anonymous_user()
# GET /profile/me với anonymous user → 200, display_name = None

test_patch_display_name_updates_db()
# PATCH /profile/me {display_name: "New"} → 200, DB cập nhật

test_patch_owner_profile_partial_update()
# Chỉ gửi display_name → avatar_url trong DB không đổi

test_oauth_autofill_sets_display_name_when_null()
# Simulate POST /auth/link flow: user.display_name=NULL
# → sau link, display_name = value từ Firebase token
```

**Verify:** `pytest tests/test_router_profile.py` → 5 tests
FAILED (chưa có implementation — expected).

**Refs:** AC-F02-1, AC-F02-2; Design §3.1, §3.2

---

### 3.2 Implement Owner Profile API

**Làm:**
- `app/schemas/profile.py`: `OwnerProfileResponse`,
  `PatchOwnerProfileRequest`.
- `app/services/profile_service.py`:
  - `get_owner_profile(firebase_uid)` → đọc từ `users`.
  - `update_owner_profile(firebase_uid, data)` → partial
    update `users`.
  - `autofill_from_oauth(firebase_uid, display_name,
    avatar_url)` → update chỉ khi cột đang NULL.
- `app/routers/profile.py`:
  - `GET /profile/me` gọi `get_owner_profile`.
  - `PATCH /profile/me` gọi `update_owner_profile`.
- Gọi `autofill_from_oauth` từ `auth_service.py` (F01) sau
  khi link OAuth thành công.

**Verify:** 5 tests từ 3.1 chuyển sang PASSED.

**Refs:** FR-1, FR-2, FR-11; AC-F02-1, AC-F02-2; Design §3.1,
§3.2

---

## 4. Storage Service — Presigned URL

_Độc lập. Dùng chung cho owner avatar (Task 3) và pet avatar
(Task 5)._

### 4.1 Viết tests Storage Service

**Làm:** Dùng `moto` mock S3. Trong
`tests/test_service_storage.py`, viết 4 test:

```python
test_generate_owner_avatar_upload_url_returns_presigned_url()
# POST /profile/me/avatar/upload-url {content_type: jpeg}
# → 200, upload_url chứa "X-Amz-Signature",
#   cdn_url chứa CDN_BASE_URL, expires_in=300

test_generate_pet_avatar_upload_url_uses_user_id_in_key()
# POST /pets/avatar/upload-url → object_key chứa user_id

test_invalid_content_type_returns_400()
# content_type="video/mp4" → 400 INVALID_CONTENT_TYPE

test_cdn_url_built_from_object_key()
# object_key="avatars/users/uid/ts.jpg"
# → cdn_url = CDN_BASE_URL + "/avatars/users/uid/ts.jpg"
```

**Verify:** 4 tests FAILED (expected).

**Refs:** Design §3.3, §3.8; DL-F02-04

---

### 4.2 Implement Storage Service

**Làm:**
- `app/services/storage_service.py`:
  - `ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png",
    "image/webp"}`.
  - `generate_upload_url(user_id, prefix, content_type)`
    → boto3 presigned PUT URL (TTL 300s).
  - `build_cdn_url(object_key)` → ghép `CDN_BASE_URL`.
- Thêm config: `S3_BUCKET`, `CDN_BASE_URL`, `AWS_REGION`
  vào `app/core/config.py`.
- Wiring `POST /profile/me/avatar/upload-url` và
  `POST /pets/avatar/upload-url` trong routers.

**Verify:** 4 tests từ 4.1 chuyển sang PASSED.

**Refs:** Design §3.3, §3.8; Technical Constraints

---

## 5. Pet CRUD API

_Phụ thuộc: Task 2 (ORM model), Task 1 (routers registered)._

### 5.1 Viết tests Pet CRUD

**Làm:** Trong `tests/test_router_pets.py` và
`tests/test_service_pet.py`, viết 8 test:

```python
test_create_pet_success_returns_201()
# POST /pets {name, species=dog} → 201, id không null

test_create_pet_defaults_gender_unknown()
# POST /pets không có gender → gender="unknown" trong response

test_create_pet_rejects_future_birthdate()
# POST /pets {birthdate: tomorrow} → 422

test_create_pet_limit_reached_returns_403()
# User đã có 1 pet → POST /pets → 403 PET_LIMIT_REACHED
# (AC-F02-5)

test_get_pets_returns_list()
# Seed 1 pet → GET /pets → pets có đúng 1 phần tử

test_get_pets_empty_list()
# User chưa có pet → GET /pets → { pets: [] }

test_get_pet_not_owned_returns_404()
# GET /pets/{id_của_user_khác} → 404 PET_NOT_FOUND

test_patch_pet_partial_update()
# PATCH /pets/{id} {name: "NewName"} → name đổi,
# species/gender không đổi
```

**Verify:** 8 tests FAILED (expected).

**Refs:** FR-3, FR-4, FR-5; AC-F02-5; Design §3.4 – §3.7

---

### 5.2 Implement Pet CRUD

**Làm:**
- `app/schemas/pet.py`: `CreatePetRequest`,
  `PatchPetRequest`, `PetResponse`.
- `app/services/pet_service.py`:
  - `FREE_USER_PET_LIMIT = 1` constant.
  - `assert_can_create_pet(user_id, db)`: count + raise
    `PetLimitReachedException` nếu vượt limit.
  - `create_pet(user_id, data, db)`.
  - `list_pets(user_id, db)`.
  - `get_pet(pet_id, user_id, db)`: raise
    `PetNotFoundException` nếu không tìm thấy / không thuộc
    user.
  - `update_pet(pet_id, user_id, data, db)`.
- `app/routers/pets.py`: wiring 4 endpoints (GET, POST,
  GET/{id}, PATCH/{id}).
- Map exceptions → HTTP response trong router.

**Verify:** 8 tests từ 5.1 chuyển sang PASSED.

**Refs:** FR-3, FR-4, FR-5, FR-9, FR-11; Design §3.4 – §3.7

---

## 6. Pet Photo Timeline API

_Phụ thuộc: Task 5 (pet_service), bảng `photos` (F04/F05 cần
tồn tại — dùng mock/fixture trong test)._

### 6.1 Viết tests Timeline & Link-photo

**Làm:** Trong `tests/test_router_pets.py`, viết 7 test:

```python
test_get_pet_photos_empty()
# GET /pets/{id}/photos → { photos: [], has_more: false }

test_get_pet_photos_ordered_by_taken_at_desc()
# 3 ảnh với taken_at khác nhau → thứ tự mới → cũ

test_get_pet_photos_pagination_returns_next_cursor()
# 25 ảnh, limit=20 → has_more=true, next_cursor đúng

test_get_pet_photos_before_cursor_filters_correctly()
# Truyền before=<timestamp> → chỉ ảnh cũ hơn timestamp

test_get_pet_photos_not_owned_returns_404()
# GET /pets/{id_khác}/photos → 404

test_link_photo_success()
# PATCH /pets/{id}/link-photo {photo_id} → 200,
# photos.pet_id = pet_id trong DB

test_link_photo_already_linked_returns_409()
# Ảnh đã có pet_id ≠ NULL → 409 PHOTO_ALREADY_LINKED
```

**Verify:** 7 tests FAILED (expected).

**Refs:** FR-10; Design §2.3, §3.9, §3.10; DL-F02-03,
DL-F02-05

---

### 6.2 Implement Timeline & Link-photo

**Làm:**
- `app/schemas/pet.py`: thêm `PetPhotosResponse`,
  `LinkPhotoRequest`.
- `app/services/pet_service.py`:
  - `get_pet_photos(pet_id, user_id, db, limit, before)`
    → query `photos WHERE pet_id=X AND taken_at < before`
    ORDER BY taken_at DESC, build cursor response.
  - `link_photo_to_pet(pet_id, photo_id, user_id, db)`
    → check ownership, check `photos.pet_id IS NULL`,
    UPDATE.
- Wiring `GET /pets/{id}/photos` và
  `PATCH /pets/{id}/link-photo` trong router.

**Verify:** 7 tests từ 6.1 chuyển sang PASSED.

**Refs:** Design §3.9, §3.10; DL-F02-03, DL-F02-05, DL-F02-06

---

## 7. Owner Profile UI

_Phụ thuộc: Task 1.2 (scaffold client). Backend Task 3 cần
hoàn thành để test e2e; unit test dùng mock._

### 7.1 Viết tests Owner Profile UI

**Làm:** Trong `__tests__/profile/`, viết 4 test:

```typescript
test("ProfileService.getOwnerProfile calls GET /profile/me")
// Mock axios → verify URL và Authorization header

test("ProfileService.patchOwnerProfile calls PATCH /profile/me")
// Mock axios → verify body chỉ chứa trường được truyền
// (partial update)

test("useProfileStore sets ownerProfile after fetch")
// Call store.fetchProfile() → state.ownerProfile cập nhật

test("EditOwnerProfileSheet shows current display_name")
// Render với ownerProfile mock → text input có value đúng
```

**Verify:** `npx jest __tests__/profile/` → 4 tests FAILED.

**Refs:** FR-2, FR-11; AC-F02-1, AC-F02-2; Design §4.1

---

### 7.2 Implement Owner Profile UI

**Làm:**
- `ProfileService.ts`: `getOwnerProfile()`, `patchOwnerProfile(data)`,
  `getOwnerAvatarUploadUrl(contentType)`.
- `useProfileStore.ts`: Zustand store `{ ownerProfile,
  loading, fetchProfile, patchProfile }`.
- `ProfileScreen.tsx`: hiển thị `display_name`, `avatar_url`,
  nút "Chỉnh sửa". Nếu `display_name = null` → hiển thị
  placeholder.
- `EditOwnerProfileSheet.tsx`: text input cho `display_name`,
  image picker + `StorageUploader` cho avatar; submit gọi
  `patchProfile`.

**Verify:** 4 tests từ 7.1 chuyển sang PASSED.

**Refs:** FR-2, FR-11; AC-F02-1, AC-F02-2

---

## 8. Create/Edit Pet UI + PetAIService

_Phụ thuộc: Task 1.2, Task 7.2 (ProfileScreen mount điểm
vào CreatePetProfileSheet). AI framework là abstraction —
không phụ thuộc framework cụ thể (DL-F02-02)._

### 8.1 Viết tests PetAIService + Create Pet flow

**Làm:** Viết 5 test:

```typescript
test("PetAIService.infer returns species and confidence")
// Mock model inference → { species: "dog", confidence: 0.92,
//   gender: "male", gender_confidence: 0.85 }

test("PetAIService.infer does not fill gender when confidence < 0.70")
// gender_confidence = 0.60 → result.gender = undefined

test("CreatePetProfileSheet pre-fills species from AI result")
// Render sheet với AI mock trả species=cat → species picker
// hiển thị "Mèo"

test("CreatePetProfileSheet allows editing AI-filled species")
// User đổi species → submit gọi ProfileService.createPet
// với species do user chọn (AC-F02-4)

test("ProfileService.createPet calls POST /pets with correct body")
// Mock axios → verify payload name, species, gender,
// avatar_url
```

**Verify:** 5 tests FAILED (expected).

**Refs:** FR-3, FR-6, FR-7, FR-8, FR-9; AC-F02-3, AC-F02-4;
Design §4.1 (Luồng CreatePetProfileSheet); DL-F02-02

---

### 8.2 Implement PetAIService + Create/Edit Pet UI

**Làm:**
- `PetAIService.ts`: interface `AIInferenceResult` (species,
  confidence, gender?, gender_confidence?); implement
  `infer(imageUri)` — bên trong là stub/placeholder trả
  hardcoded result cho đến khi AI framework được chọn
  (DL-F02-02).
- `usePetStore.ts`: Zustand store `{ pets, fetchPets,
  createPet, updatePet }`.
- `ProfileService.ts`: thêm `createPet(data)`,
  `updatePet(petId, data)`, `listPets()`,
  `getPetAvatarUploadUrl(contentType)`.
- `CreatePetProfileSheet.tsx`: 3 bước như design §4.1;
  confidence threshold cho gender là `>= 0.70`.
- `EditPetProfileSheet.tsx`: form pre-fill từ pet hiện tại,
  partial update.

**Verify:** 5 tests từ 8.1 chuyển sang PASSED.

**Refs:** FR-3, FR-6, FR-7, FR-8, FR-9; AC-F02-3, AC-F02-4

---

## 9. Camera pet selector (PetSelectorChip + PetPickerOverlay)

_Phụ thuộc: Task 8.2 (usePetStore có danh sách pet). Tích
hợp vào camera screen của F04 — F02 chỉ cung cấp component,
không sửa F04 camera logic._

### 9.1 Viết tests PetSelectorChip + PetPickerOverlay

**Làm:** Trong `__tests__/profile/PetSelectorChip.test.tsx`,
viết 4 test:

```typescript
test("PetSelectorChip shows 'Không gán' when no pet selected")
// Render PetSelectorChip activePetId=null →
// text "Không gán" hiển thị

test("PetSelectorChip shows pet name when pet selected")
// activePetId=uuid, pets=[{id:uuid, name:"Mochi"}] →
// text "Mochi" hiển thị

test("tap PetSelectorChip opens PetPickerOverlay")
// fireEvent.press → onOpenPicker called

test("PetPickerOverlay selecting pet calls onSelectPet with pet_id")
// Render overlay với 1 pet → press pet item →
// onSelectPet called với đúng pet.id

test("PetPickerOverlay 'Không gán' option calls onSelectPet(null)")
// Press "Không gán" → onSelectPet(null)
```

**Verify:** 5 tests FAILED (expected).

**Refs:** FR-10; AC-F02-6; Design §4.1 (PetSelectorChip,
PetPickerOverlay); DL-F02-06

---

### 9.2 Implement PetSelectorChip + PetPickerOverlay

**Làm:**
- `PetSelectorChip.tsx`: props `{ activePetId, pets,
  onOpenPicker }`. Hiển thị tên pet active hoặc "Không gán".
- `PetPickerOverlay.tsx`: props `{ visible, pets,
  onSelectPet(id | null), onClose }`. Render danh sách
  pet + item "Tạo pet mới" (callback mở
  `CreatePetProfileSheet`) + item "Không gán".
- Không sửa file nào của F04 — export hai component để F04
  tự import.

**Verify:** 5 tests từ 9.1 chuyển sang PASSED.

**Refs:** FR-10; AC-F02-6; DL-F02-06

---

## 10. Pet Timeline Screen

_Phụ thuộc: Task 8.2 (usePetStore), Task 6.2 (backend
endpoint). Unit test dùng mock ProfileService._

### 10.1 Viết tests PetTimelineScreen

**Làm:** Viết 3 test:

```typescript
test("PetTimelineScreen renders pet avatar and name in header")
// Render với pet mock → avatar image + name hiển thị

test("PetTimelineScreen renders photo grid from API response")
// Mock ProfileService.getPetPhotos → 3 ảnh → 3 image item
// hiển thị trong FlatList

test("PetTimelineScreen loads next page on scroll to end")
// has_more=true → scroll to end → ProfileService.getPetPhotos
// được gọi lần 2 với before=next_cursor
```

**Verify:** 3 tests FAILED (expected).

**Refs:** Design §3.10, §4.1 (PetTimelineScreen)

---

### 10.2 Implement PetTimelineScreen

**Làm:**
- `ProfileService.ts`: thêm `getPetPhotos(petId, params?)`.
- `PetTimelineScreen.tsx`: header với avatar + tên pet;
  FlatList 2 cột; infinite scroll dùng `next_cursor` từ
  response; loading spinner khi `has_more=true` và đang
  fetch.
- Điều hướng từ `ProfileScreen` → `PetTimelineScreen` khi
  tap vào pet item.

**Verify:** 3 tests từ 10.1 chuyển sang PASSED. Chạy
`make test` — toàn bộ backend tests pass. Chạy
`npx jest` — toàn bộ client tests pass.

**Refs:** Design §3.10, §4.1; AC-F02-7
