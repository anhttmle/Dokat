# F05 — Gửi Ảnh (Multi-Recipient / Broadcast) — Decision Log

---

## DL-F05-01 — Tên bảng là `posts` (không phải stub `photos` của F02)

**Date:** 2026-06-22
**Context:** DL-F04-01 ghi chú rằng stub `photos`
(`backend/app/models/photo.py`) "sẽ được mở rộng trong F05".
Nhưng F11 Design §2.3 + PRD §F05 (Technical Constraints, AC) đã
cam kết một bảng tên **`posts`** với hai cột `latitude/longitude`
và bảng liên kết `post_recipients`. Hai spec dùng hai tên khác
nhau.
**Decision:** Dùng tên **`posts`** + `post_recipients` cho F05,
khớp với contract đã chốt của F11 (predecessor trực tiếp trong thứ
tự thực thi F04 → F11 → F05) và PRD. Ghi chú "mở rộng photos" của
F04 là forward-looking, không ràng buộc; F11 đã superseded bằng
contract `posts` cụ thể.
**Consequence:** Stub `photos` của F02 (timeline gán pet) **giữ
nguyên**, không bị F05 sửa (surgical — KISS/YAGNI). Hai bảng cùng
mô tả "ảnh" sẽ tồn tại song song trong MVP: `photos` cho pet
timeline (F02), `posts` cho luồng gửi (F05+). Việc hợp nhất
(`posts.pet_id` hoặc migrate timeline sang `posts`) **out-of-scope
F05**, ghi nhận để feature sau cân nhắc.

---

## DL-F05-02 — S3 object key do server cấp (không tin key client)

**Date:** 2026-06-22
**Context:** F04 đã tính sẵn `CapturedPhoto.s3Key`
(`posts/{userId}/{ts}_{uuid}.jpg`). F05 cần presigned PUT URL.
Có thể (a) ký đúng key client gửi lên, hoặc (b) server tự sinh key.
**Decision:** Dùng (b): `POST /posts/upload-url` reuse
`storage_service.generate_upload_url(user_id, prefix="posts",
content_type)` — server sinh key `posts/{user_id}/{timestamp}.ext`
từ `firebase_uid` đã xác thực. `CapturedPhoto.s3Key` của F04 chỉ
mang tính tham khảo; key chính thức là key server cấp.
**Consequence:** Client không thể chỉ định/ghi đè key của user
khác (an toàn hơn). Định dạng key hơi khác F04 (không có `_uuid`),
nhưng vẫn nằm dưới prefix `posts/{user_id}/` như Technical
Constraint. `POST /posts` nhận lại `object_key` này làm `s3_key`.

---

## DL-F05-03 — `expires_at = now() + 24h` cho mọi user trong MVP

**Date:** 2026-06-22
**Context:** PRD/Requirements nói "ảnh của free user được đánh dấu
`expires_at = now() + 24h`". MVP chưa có tier premium.
**Decision:** Mọi post đặt `expires_at = created_at + 24h` qua hằng
`POST_EXPIRY_HOURS = 24`. Record **không bị xoá**, chỉ dùng để ẩn
khỏi feed/history sau 24h (filter ở F06/F08).
**Consequence:** Khi có premium tier, thay đổi `POST_EXPIRY_HOURS`
hoặc thêm logic theo gói; chỉ cần sửa một chỗ trong
`post_service`.

---

## DL-F05-04 — `post_recipients.seen_at` tạo ở F05, logic seen thuộc F07

**Date:** 2026-06-22
**Context:** "Seen by" là F07. Cột lưu thời điểm xem thuộc về bảng
`post_recipients`. Tạo cột ở F07 sẽ cần thêm một migration ALTER.
**Decision:** F05 tạo sẵn cột `seen_at TIMESTAMPTZ NULL` ngay trong
migration `post_recipients` (chỗ ở tự nhiên của nó), nhưng **không**
implement bất kỳ logic seen nào. F07 sẽ thêm endpoint
`POST /posts/{id}/seen` để upsert `seen_at`.
**Consequence:** Tránh một migration ALTER thừa ở F07. F05 chỉ test
sự tồn tại của cột (migration test); hành vi seen test ở F07.

---

## DL-F05-05 — F05 không gửi push; để lại điểm tích hợp cho F09

**Date:** 2026-06-22
**Context:** FR-9 yêu cầu push tới từng recipient sau khi lưu post.
Nhưng kế hoạch tổng đặt "new-photo notification trigger" vào **F09
T3** ("trong post creation"). Implement FCM ở F05 sẽ trùng lặp F09.
**Decision:** F05 chỉ tạo `posts` + `post_recipients` và để lại
**điểm tích hợp** rõ ràng trong `post_service.create_post` (sau khi
commit recipients) cho F09 cắm `send_push_notification` vào. F05
**không** gọi FCM.
**Consequence:** AC-F05-2 (phần "recipients nhận push") được phủ
test trong integration suite của **F09**. F05 chỉ verify post +
recipients được tạo đúng. Khi 0 recipient → không có gì để push
(FR-9), nhất quán dù hook nằm ở F09.

---

## DL-F05-06 — Validate input bằng Pydantic ở `POST /posts`

**Date:** 2026-06-22
**Context:** Body `POST /posts` gồm `s3_key`, `cdn_url`,
`recipient_ids`, `latitude?`, `longitude?`. F11 §3.1 yêu cầu
validate khoảng toạ độ.
**Decision:** Dùng Pydantic schema `CreatePostRequest`:
`latitude` ∈ [-90, 90], `longitude` ∈ [-180, 180] (ge/le), hai
field optional; `recipient_ids` list UUID có thể rỗng; `s3_key`,
`cdn_url` non-empty. Sai khoảng → 422 tự động.
**Consequence:** Đồng nhất với cách validate hiện có (F02/F03).
De-dup `recipient_ids` thực hiện ở service (không phải validation)
để giữ schema thuần khai báo.

---

## DL-F05-07 — Recipients phải là bạn bè của Sender (reject 422)

**Date:** 2026-06-22
**Context:** Requirements không nêu rõ server có chặn gửi tới người
lạ hay không. Tuy nhiên gửi ảnh tới user bất kỳ (không phải bạn) là
lỗ hổng quyền riêng tư; user-rule yêu cầu validate input.
**Decision:** `post_service.create_post` kiểm tra mọi
`recipient_id` đều nằm trong danh sách bạn bè của Sender
(`friendships`). Nếu có phần tử không phải bạn → raise
`InvalidRecipientError` → router map **422 `INVALID_RECIPIENT`**.
Đây là validation tối thiểu, không phải "security layer" thừa.
**Consequence:** Client (RecipientSelectorScreen) vốn chỉ hiển thị
bạn bè nên trường hợp này hiếm; chốt chặn server ngăn lạm dụng API
trực tiếp. Nếu sau này cho phép gửi tới người không phải bạn, nới
lỏng quy tắc tại một chỗ trong service.

---

## DL-F05-08 — Upload S3 + camera/screen abstract sau interface, native tích hợp sau

**Date:** 2026-06-22
**Context:** Chưa có thư viện upload/file thực trong `package.json`;
cần test logic `SendService` (thứ tự gọi, retry) mà không phụ thuộc
native (tiền lệ DL-F03-11, DL-F04-03).
**Decision:** `SendService` nhận `uploadBackend` (hàm PUT file lên
S3) injectable/mockable; HTTP fetch tới backend cũng mock được.
`RecipientSelectorScreen` dùng component mock-friendly như tiền lệ
F03/F04. Tích hợp native (PUT binary thực, progress) thực hiện ở
task triển khai sau.
**Consequence:** Unit test chỉ kiểm tra business logic (orchestrate
upload→confirm, retry ≤ 3, merge location payload, default-select
recipients), không kiểm tra native upload thực hay hiệu năng "5
giây" (AC-F05-2).

---

## DL-F05-09 — `POST /posts` trả 404 khi firebase_uid chưa có user row

**Date:** 2026-06-22
**Context:** Design §3.2 chỉ liệt kê 201, 422 (lat/lng), 422
`INVALID_RECIPIENT`. Nhưng `_get_user_id` cần resolve `firebase_uid`
→ user UUID; nếu token hợp lệ nhưng chưa từng gọi `POST /auth/session`
thì không có user row.
**Decision:** Router trả **404 `USER_NOT_FOUND`** trong trường hợp
này (nhất quán với pattern `routers/friends.py`), thay vì để
`uuid.UUID(None)` ném 500. Không thêm logic tạo user ngầm (YAGNI).
**Consequence:** Client luôn gọi `/auth/session` trước (F01), nên
nhánh này hiếm; chốt chặn tránh 500 khi gọi API trực tiếp.

---

## DL-F05-11 — Flutter `SendService`: `getUploadUrl` trả record; `sendPost` dùng `s3_key`+`cdn_url`; `CaptureService.uploadImage` trả `void`

**Date:** 2026-06-27
**Context:** Khi tích hợp client với backend thật, phát hiện 3 mismatch trong
luồng gửi ảnh:
1. `getUploadUrl()` chỉ lấy `upload_url`, bỏ mất `object_key` (s3_key) và
   `cdn_url` mà backend `PresignedUrlResponse` trả kèm.
2. `sendPost()` gửi `image_url` thay vì `s3_key`+`cdn_url`, và gửi nested
   `location: {latitude, longitude}` thay vì flat `latitude`/`longitude` như
   `CreatePostRequest` yêu cầu.
3. `CaptureService.uploadImage()` trả `String` bằng cách strip query param
   của presigned URL — cách này sai vì CDN URL và S3 base URL là khác nhau.
**Decision:**
- `getUploadUrl()` trả Dart named record `({String uploadUrl, String s3Key, String cdnUrl})`.
- `sendPost()` đổi signature: nhận `s3Key`, `cdnUrl`, `double? latitude`,
  `double? longitude` thay vì `imageUrl` và nested `locationPayload`.
- `CaptureService.uploadImage()` trả `void` — CDN URL lấy từ response của
  `getUploadUrl`, không cần derive từ presigned URL.
- `LocationService.getCurrentPayload()` trả `LocationPayload?` (typed) thay vì
  `Map<String, dynamic>?` để call site truy cập `.latitude`/`.longitude` an toàn.
- `RecipientSelectorScreen` cập nhật để destructure record và truyền đúng fields.
**Consequence:** Luồng upload hoàn chỉnh và chính xác: server cấp key → upload
PUT S3 → confirm với s3_key + cdn_url. Không còn derive CDN URL sai từ presigned URL.

---

## DL-F05-10 — `created_at`/`expires_at` tính ở Python trong service

**Date:** 2026-06-22
**Context:** `expires_at` phải xấp xỉ `created_at + 24h`
(DL-F05-03). Nếu `created_at` dùng `server_default now()` còn
`expires_at` tính ở Python thì hai mốc lệch nhau (clock khác nguồn).
**Decision:** `create_post` lấy một `now =
datetime.now(timezone.utc)` duy nhất, set cả `created_at` và
`expires_at = now + 24h` từ mốc đó, đảm bảo quan hệ chính xác và
deterministic cho test.
**Consequence:** Cột `created_at` vẫn giữ `server_default now()`
trong schema (cho INSERT trực tiếp ngoài service), nhưng đường đi qua
service luôn nhất quán.

---

## DL-F05-12 — `pet_id` trong sendPost chưa có backend support

**Ngày:** 2026-06-30

**Context:** `SendService.sendPost` và UI `recipient_selector_screen.dart`
truyền `pet_id` lên `POST /posts`, nhưng backend `CreatePostRequest` không
có field này → Pydantic bỏ qua silently → tính năng tag pet không hoạt
động.

**Decision:** Giữ nguyên `pet_id` param ở client vì đây là planned feature
(user chọn pet trước khi gửi post). Không xóa để tránh mất UI flow.

**Action cần làm:** Khi implement pet-tagging, thêm
`pet_id: uuid.UUID | None = None` vào `CreatePostRequest` backend và lưu
vào bảng `posts`.
