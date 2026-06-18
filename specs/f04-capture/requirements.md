# F04 — Capture Ảnh + AI Validation — Requirements

## Goal

Cho phép người dùng chụp ảnh thú cưng trực tiếp trong app ở độ phân giải
720p bằng camera sau. AI model chạy on-device sẽ xác nhận ảnh chỉ chứa
chó/mèo — nếu phát hiện rõ người thì block upload.

## Users / Actors

- **User:** Người dùng chụp ảnh.
- **AI Validation Engine:** Model on-device phân loại nội dung ảnh.

## Functional Requirements

1. Hệ thống SHALL mở camera in-app sử dụng camera sau (back camera) khi người
   dùng nhấn nút chụp.
2. Hệ thống SHALL chụp ảnh ở độ phân giải 720p (1280×720px).
3. Hệ thống SHALL chạy AI model on-device để phân loại nội dung ảnh ngay sau
   khi chụp, trước khi hiển thị preview.
4. Hệ thống SHALL block hoàn toàn không cho upload nếu AI phát hiện rõ có
   người trong ảnh (human detected với độ tin cậy cao).
5. Hệ thống SHALL cho phép upload khi AI không chắc chắn (low confidence) về
   việc có người hay không, ưu tiên trải nghiệm người dùng.
6. Hệ thống SHALL hiển thị thông báo lỗi rõ ràng ("Ảnh không hợp lệ — chỉ
   được chụp thú cưng") khi bị block.
7. Hệ thống SHALL cho phép người dùng chụp lại nếu ảnh bị block.
8. Hệ thống SHALL cho phép upload nếu AI xác nhận ảnh hợp lệ (chứa chó/mèo
   hoặc không có người).
9. Hệ thống SHALL nén ảnh ở chất lượng JPEG quality 80% trước khi upload lên
   S3 để giảm dung lượng mà không làm giảm chất lượng đáng kể.
10. Hệ thống SHALL hoàn tất AI validation trong vòng 3 giây trên thiết bị
    tầm trung.

## Non-goals

- Không có Image Editor (filter, sticker, crop, flip, AI generate) trong MVP.
- Không hỗ trợ chụp video trong MVP.
- Không validate phía server; việc kiểm tra chỉ thực hiện on-device.
- Không hỗ trợ upload ảnh từ thư viện ảnh hệ thống (chỉ chụp trực tiếp).
- Không hỗ trợ camera trước (front/selfie), flash, hay zoom trong MVP.

## Technical Constraints

- AI model phải chạy hoàn toàn on-device (TFLite hoặc CoreML).
- Model phải nhẹ (≤ 20MB) để không làm tăng đáng kể bundle size.
- Ảnh upload lên S3 theo path có cấu trúc:
  `posts/{user_id}/{timestamp}_{uuid}.jpg`.
- Metadata ảnh (user_id, timestamp, s3_key) lưu vào PostgreSQL.
- Nén ảnh JPEG quality = 80 trước khi upload.

## Acceptance Criteria

**AC-F04-1:** Chụp ảnh hợp lệ
```
Given người dùng mở camera (camera sau) và chụp ảnh chỉ có một con mèo
When AI validation hoàn tất
Then hệ thống cho phép tiếp tục flow gửi ảnh
  và ảnh được lưu ở độ phân giải 720p
```

**AC-F04-2:** Block ảnh có người (high confidence)
```
Given người dùng chụp ảnh có rõ ràng cả người và chó
When AI validation hoàn tất với độ tin cậy cao "có người"
Then hệ thống hiển thị thông báo lỗi "Ảnh không hợp lệ"
  và không cho phép gửi ảnh
  và không upload bất kỳ dữ liệu nào lên server
```

**AC-F04-3:** Cho phép upload khi AI low confidence
```
Given người dùng chụp ảnh mà AI không chắc chắn có người hay không
When AI validation hoàn tất với độ tin cậy thấp
Then hệ thống cho phép tiếp tục flow gửi ảnh (ưu tiên UX)
```

**AC-F04-4:** Thời gian validation
```
Given người dùng chụp ảnh
When AI bắt đầu validation
Then kết quả validation xuất hiện trong vòng 3 giây
  trên thiết bị tầm trung (4GB RAM)
```

**AC-F04-5:** Chụp lại sau khi bị block
```
Given ảnh vừa bị block vì có người
When người dùng nhấn "Chụp lại"
Then camera mở lại và người dùng có thể chụp ảnh mới
```

**AC-F04-6:** Nén ảnh trước upload
```
Given ảnh đã pass AI validation
When hệ thống chuẩn bị upload lên S3
Then ảnh được nén ở JPEG quality 80%
  và được lưu theo path posts/{user_id}/{timestamp}_{uuid}.jpg
```
