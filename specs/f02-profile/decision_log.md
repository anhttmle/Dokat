# F02 — Owner Profile & Pet Profile — Decision Log

## DL-F02-01: Không tạo bảng `owner_profiles` riêng

**Ngày:** 2026-06-21
**Quyết định:** Owner Profile được lưu trực tiếp trong bảng
`users` (cột `display_name`, `avatar_url`) thay vì tạo bảng
riêng.
**Lý do:** Requirements không yêu cầu thêm trường nào ngoài
những gì đã có trong F01. Tách bảng là over-engineering cho
MVP.

---

## DL-F02-02: AI framework on-device chưa được chọn

**Ngày:** 2026-06-21
**Quyết định:** Design giữ `PetAIService` là interface trừu
tượng. Framework cụ thể (TFLite, CoreML, ONNX, v.v.) sẽ
được quyết định khi bắt đầu implement F02 client.
**Lý do:** Chưa có quyết định từ product/tech lead. Design
không nên bị khóa vào một framework trước khi evaluate.
**Action:** Tạo task trong F02 tasks.md để research và chọn
framework trước khi bắt đầu coding `PetAIService`.

---

## DL-F02-03: Ảnh feed gán vào pet — lưu qua `photos.pet_id`

**Ngày:** 2026-06-21
**Quyết định:** Thay vì tạo bảng quan hệ riêng
`photo_pet_links`, thêm cột nullable `pet_id` vào bảng
`photos` (F04/F05 định nghĩa). Mỗi pet có **timeline riêng**
= tập hợp tất cả ảnh có `pet_id = <pet_id>`, query theo
`taken_at DESC`.
**Lý do:** Yêu cầu mỗi ảnh chỉ thuộc tối đa 1 pet (1-to-1
optional). Một cột FK đơn giản hơn bảng liên kết trong
trường hợp này. Timeline truy vấn hiệu quả qua index trên
`(pet_id, taken_at)`.
**Ràng buộc:** Nếu trong tương lai một ảnh cần thuộc nhiều
pet (ảnh chụp nhiều thú cưng), cần migrate sang bảng
`photo_pet_links` (many-to-many).

---

## DL-F02-04: Presigned URL dùng `user_id` cho path pet avatar

**Ngày:** 2026-06-21
**Quyết định:** Path S3 cho pet avatar tạm thời là
`avatars/pets/{user_id}/{timestamp}.jpg` vì `pet_id` chưa
tồn tại lúc upload.
**Lý do:** Client upload ảnh trước, sau đó mới gọi `POST
/pets` để tạo pet. Không có `pet_id` tại thời điểm lấy
presigned URL.

---

## DL-F02-06: Pet assignment là pre-selection trước khi chụp, không phải post-capture sheet

**Ngày:** 2026-06-21
**Quyết định:** Thay vì hiển thị `PhotoAssignmentSheet` sau
khi chụp ảnh, user chọn pet ngay trên camera UI qua
`PetSelectorChip` + `PetPickerOverlay` trước khi bấm chụp.
`pet_id` được gửi kèm payload trong `POST /photos` (F05).
**Lý do:** Bước hỏi post-capture làm gián đoạn flow gửi ảnh,
tệ hơn trải nghiệm so với pre-selection. Pattern này nhất
quán với cách Locket chọn recipient trước khi chụp.
**Ảnh hưởng đến AC-F02-6:** AC gốc mô tả "hiển thị gợi ý
sau khi AI hoàn tất" — được reinterpret thành gợi ý xuất
hiện trên camera UI (trước capture), không phải sau.
`PATCH /pets/{id}/link-photo` vẫn giữ để hỗ trợ gán thủ
công từ timeline/history.


**Ngày:** 2026-06-21
**Quyết định:** Khi `PATCH /pets/{id}/link-photo` gặp ảnh đã
có `pet_id` ≠ NULL, trả về 409 thay vì ghi đè.
**Lý do:** Ghi đè im lặng dễ gây mất dữ liệu. Client cần
hỏi xác nhận user trước khi "chuyển" ảnh từ pet cũ sang
pet mới. Việc ghi đè sẽ được implement trong một endpoint
riêng hoặc thêm param `force=true` trong tương lai nếu cần.

---

## DL-F02-07: SQLAlchemy Enum dùng `native_enum=False`

**Ngày:** 2026-06-21
**Quyết định:** `PetSpecies` và `PetGender` trong model
`pet_profiles` khai báo Enum với `native_enum=False` (lưu
dưới dạng VARCHAR + CHECK constraint) thay vì native ENUM
của PostgreSQL.
**Lý do:** Test suite dùng SQLite in-memory (pattern từ F01)
để chạy nhanh, không cần PostgreSQL. SQLite không hỗ trợ
native ENUM nên `native_enum=False` giúp model portable
giữa SQLite (test) và PostgreSQL (production) mà không cần
lớp mock riêng.
**Phát sinh trong:** Task 1.1 (scaffold backend F02).

---

## DL-F02-09: Migration tests và ORM test đặt chung một file

**Ngày:** 2026-06-21
**Quyết định:** Test migration schema (3 tests spec 2.1) và test ORM
model (1 test spec 2.2) được đặt chung trong
`tests/migrations/test_pet_profiles_migration.py`, dùng chung fixture
`db_engine` / `db_session` / `seed_user`.
**Lý do:** Cả hai nhóm test dùng SQLite in-memory với
`Base.metadata.create_all()`. Tách thành 2 file nhân đôi fixture
setup mà không mang lại lợi ích phân tách rõ ràng. Nhất quán với
convention `tests/migrations/` từ F01.
**Spec đề xuất:** `tests/test_migration.py` — không follow vì khác
convention hiện tại của repo.
**Phát sinh trong:** Task 2.1 + 2.2.

---

## DL-F02-10: autofill_from_oauth được gọi từ auth router, không từ auth_service

**Ngày:** 2026-06-21
**Quyết định:** `autofill_from_oauth` (định nghĩa trong `profile_service.py`)
được gọi trực tiếp từ `routers/auth.py` ngay sau khi `link_provider` trả về,
thay vì được gọi bên trong `auth_service.link_provider`.
**Lý do:** `link_provider` trong `auth_service.py` không nhận `display_name`
hay `picture_url` từ token — chúng chỉ có sẵn trong `token_claims` ở tầng
router. Truyền thêm 2 tham số tùy chọn vào `link_provider` làm thay đổi
signature của F01 không cần thiết. Gọi từ router tách biệt trách nhiệm rõ
hơn: auth_service lo về link provider, profile_service lo về auto-fill profile.
**Ảnh hưởng:** Trong trường hợp merge (user B), `autofill_from_oauth` nhận
`firebase_uid` của guest (đã bị xóa sau merge) → query trả None → hàm
return early an toàn. User B không bị auto-fill (họ đã có tài khoản).
**Phát sinh trong:** Task 3.2.

---

## DL-F02-11: Presigned URL dùng SigV4 thay vì SigV2 mặc định

**Ngày:** 2026-06-21
**Quyết định:** `boto3.client("s3", ...)` được tạo với
`config=Config(signature_version="s3v4")` để presigned URL
chứa tham số `X-Amz-Signature` (SigV4) thay vì `Signature`
(SigV2 mặc định của moto).
**Lý do:** Spec (Design §3.3) mô tả URL trả về có
`X-Amz-Signature`; SigV4 là tiêu chuẩn AWS hiện tại và
bắt buộc với một số region. Test 4.1 kiểm tra chuỗi này
trực tiếp.
**Phát sinh trong:** Task 4.2.

---

## DL-F02-12: Router presigned URL tests dùng moto inline

**Ngày:** 2026-06-21
**Quyết định:** `test_presigned_url_owner_avatar` trong
`test_router_profile.py` được cập nhật để wrap boto3 call
trong `mock_aws()` context và tạo bucket "pawsnap" trước
khi gọi endpoint.
**Lý do:** Task 4.2 wiring router thực sự gọi `boto3`,
nên test cần moto để không gọi AWS thật. Test này đã
FAIL trước (500 NotImplementedError) — việc thêm moto
là điều kiện cần để test pass sau khi implement.
**Phát sinh trong:** Task 4.2.

---

## DL-F02-13: birthdate validation ở tầng schema (Pydantic), không ở service

**Ngày:** 2026-06-21
**Quyết định:** Validation "birthdate không trong tương lai" được thực hiện
bằng `@field_validator` trong `CreatePetRequest` (Pydantic), không phải trong
`pet_service.create_pet`.
**Lý do:** FastAPI tự động trả về 422 khi Pydantic validator thất bại —
không cần thêm try/except trong service hay router. Giữ service tập trung vào
business logic (limit check, DB write), schema tập trung vào input validation.
**Phát sinh trong:** Task 5.2.

---

## DL-F02-14: Minimal Photo model stub tạo trong F02 để test timeline

**Ngày:** 2026-06-21
**Quyết định:** Tạo `app/models/photo.py` chứa model `Photo` tối thiểu
(các cột: `id`, `user_id`, `pet_id`, `cdn_url`, `taken_at`,
`created_at`) để phục vụ các test F02 (timeline và link-photo)
trước khi F04/F05 định nghĩa bảng `photos` đầy đủ.
**Lý do:** `link_photo` và `get_pet_photos` cần query bảng `photos`
thực tế trong DB. Không thể mock toàn bộ lớp ORM vì test dùng SQLite
in-memory với `Base.metadata.create_all()`. Tạo stub model là cách
duy nhất để test chạy được mà không cần F04/F05 hoàn thành.
**Ràng buộc:** Khi F04/F05 định nghĩa `photos` đầy đủ, model này phải
được merge/replace. Không thêm cột F04/F05 vào stub này.
**Phát sinh trong:** Task 6.2 (Timeline & Link-photo implementation).

---

## DL-F02-15: `before` cursor normalize '+' trước khi parse ISO 8601

**Ngày:** 2026-06-21
**Quyết định:** Trong `get_pet_photos`, trước khi gọi
`datetime.fromisoformat(before)`, thay thế `" "` thành `"+"` trong
chuỗi `before`.
**Lý do:** HTTP query string decode `+` thành space (application/x-www-
form-urlencoded). ISO 8601 timezone offset dùng `+` (ví dụ
`+00:00`). Nếu client truyền `before=2026-06-20T10:00:00+00:00`, server
nhận được `2026-06-20T10:00:00 00:00` → `fromisoformat` fail với
`ValueError`. Normalize về `+` trước khi parse giải quyết vấn đề này.
**Phát sinh trong:** Task 6.2 (debug test_get_pet_photos_before_cursor).

---

## DL-F02-16: BASE_URL hardcode `http://localhost:8000` trong ProfileService

**Ngày:** 2026-06-21
**Quyết định:** `BASE_URL` trong `ProfileService.ts` được hardcode là
`http://localhost:8000` thay vì đọc từ biến môi trường.
**Lý do:** Repo chưa có cơ chế config env cho React Native client
(chưa dùng `react-native-config` hay tương đương). Hardcode đủ cho
dev/test hiện tại. Khi cần multi-env, sẽ tách thành module config riêng.
**Phát sinh trong:** Task 7.2.

---

## DL-F02-17: PetAIService tách internal model runner thành `_petModelStub`

**Ngày:** 2026-06-21
**Quyết định:** Logic inference của `PetAIService.infer` tách thành
hai layer: `_petModelStub.ts` export hàm `runModel` (raw model
output, luôn bao gồm `gender_confidence`), và `PetAIService.infer`
áp dụng threshold `>= 0.70` trước khi expose ra ngoài.
**Lý do:** Tests cần kiểm soát raw model output độc lập để test
cả hai nhánh (gender trả về vs. undefined). Nếu `infer` là blackbox
hoàn toàn (không mock được phần bên trong), không thể viết test
riêng cho từng nhánh mà không làm hỏng thiết kế public interface.
Tách thành module riêng cho phép `jest.mock('_petModelStub')` mà
không đụng đến public API của `PetAIService`.
**Ràng buộc:** `_petModelStub` là internal module; prefix `_` báo
hiệu không import trực tiếp từ ngoài package `services/ai`.
**Phát sinh trong:** Task 8.1 + 8.2.

---

## DL-F02-18: `CreatePetProfileSheet` nhận `imageUri` prop để skip Step 1

**Ngày:** 2026-06-21
**Quyết định:** Component nhận prop `imageUri?: string`. Khi được
cung cấp, component bỏ qua Step 1 (chọn ảnh) và chạy AI inference
ngay khi mount. Khi không có `imageUri`, hiển thị Step 1 để user
chọn ảnh.
**Lý do:** Repo chưa có thư viện image picker; việc mock picker
trong tests phức tạp và không thuộc phạm vi task này. Prop
`imageUri` cho phép tests và camera flow (F04) cung cấp ảnh
sẵn có mà không cần mock picker. Pattern này không ảnh hưởng
đến UX thực tế vì F04 sẽ truyền URI sau khi capture.
**Phát sinh trong:** Task 8.1 + 8.2.

---

## DL-F02-19: PetPickerOverlay thêm prop `onOpenCreatePet?` không có trong spec

**Ngày:** 2026-06-21
**Quyết định:** `PetPickerOverlay` nhận thêm prop tùy chọn
`onOpenCreatePet?: () => void` ngoài danh sách props gốc trong
spec (`visible, pets, onSelectPet, onClose`).
**Lý do:** Design §4.1 mô tả item "Tạo pet mới" cần mở
`CreatePetProfileSheet`. Nếu không có callback này, button chỉ gọi
`onClose()` mà không trigger gì — F04 sẽ không thể wire up sheet.
Prop là optional để backward-compatible; tests Task 9.1/9.2 không
test behaviour này nên không cần mock.
**Phát sinh trong:** Task 9.2.

---

## DL-F02-08: ProfileService dùng `fetch` làm HTTP transport

**Ngày:** 2026-06-21
**Quyết định:** Client `ProfileService` gọi backend qua
global `fetch` (mock được trong Jest), token lấy từ
`AuthService.getIdToken()`.
**Lý do:** Repo chưa có HTTP client dùng chung; `fetch` có
sẵn trong React Native, không thêm dependency. Test scaffold
mock `global.fetch` để định nghĩa contract trước khi
implement.
**Ghi chú phụ:** `ProfileService` và `PetAIService` được
viết theo dạng object-literal export default (nhất quán với
`AuthService` hiện có) thay vì class như mô tả trong plan —
chọn để khớp style codebase và đơn giản hóa manual mock.
**Phát sinh trong:** Task 1.2 (scaffold client F02).
