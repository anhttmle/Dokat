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
