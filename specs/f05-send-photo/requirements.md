# F05 — Gửi Ảnh (Multi-Recipient / Broadcast) — Requirements

## Goal

Cho phép người dùng gửi ảnh thú cưng vừa chụp đến bạn bè theo mô hình
broadcast: mặc định gửi tới tất cả bạn bè hiện có (có thể là 0 nếu chưa có
bạn nào), hoặc chọn một subset người nhận. Mỗi lần chụp là one-shot: sau khi
gửi xong, ảnh bị discard và muốn gửi tiếp phải chụp lại.

## Users / Actors

- **Sender:** Người dùng gửi ảnh.
- **Recipients:** Không, một, hoặc nhiều người bạn nhận ảnh (0..N).
- **System:** Backend xử lý lưu post và trigger notification.

## Functional Requirements

1. Hệ thống SHALL hiển thị danh sách bạn bè để Sender chọn người nhận sau khi
   ảnh pass AI validation.
2. Hệ thống SHALL mặc định chọn sẵn toàn bộ bạn bè hiện có của Sender làm danh
   sách người nhận.
3. Hệ thống SHALL cho phép Sender bỏ chọn hoặc chọn lại để gửi tới một subset
   bất kỳ, bao gồm trường hợp 0 người nhận.
4. Hệ thống SHALL cho phép nhấn "Gửi" ngay cả khi số người nhận là 0.
5. Hệ thống SHALL upload ảnh lên S3 (một lần) và luôn tạo post record trong
   PostgreSQL khi Sender gửi, kể cả khi danh sách người nhận rỗng.
6. Hệ thống SHALL gắn post với toàn bộ danh sách người nhận đã chọn (0..N) qua
   quan hệ many-to-many.
7. Hệ thống SHALL lưu post vào History "Đã gửi" của Sender trong mọi trường
   hợp, kể cả khi không có người nhận nào (xem F08).
8. Hệ thống SHALL hiển thị ảnh trên feed của tất cả người nhận được chọn, và
   chỉ những người đó (xem F06).
9. Hệ thống SHALL gửi push notification đến từng Recipient ngay sau khi ảnh
   được lưu thành công (xem F09); khi 0 người nhận thì không gửi notification.
10. Hệ thống SHALL discard ảnh sau khi gửi thành công; nếu muốn gửi thêm,
    Sender phải chụp lại (one-shot).
11. Hệ thống SHALL lưu timestamp gửi vào metadata của post.
12. Hệ thống SHALL hiển thị trạng thái "Đã gửi" cho Sender sau khi upload
    thành công.
13. Hệ thống SHALL xử lý trường hợp mất kết nối: retry upload tối đa 3 lần
    trước khi báo lỗi cho người dùng.

## Non-goals

- Không hỗ trợ gửi nhóm (group send) trong MVP — chỉ broadcast/multi-select
  cá nhân.
- Không có tính năng unsend/thu hồi ảnh trong MVP.
- Không cho phép gửi lại cùng một ảnh sau khi đã gửi (one-shot, ảnh bị
  discard).

## Technical Constraints

- Upload ảnh dùng presigned S3 URL (client upload trực tiếp lên S3, không qua
  FastAPI backend) để giảm tải server.
- Ảnh chỉ upload lên S3 một lần cho một lần gửi, dù gửi cho nhiều người.
- Quan hệ post — recipients là many-to-many: một bảng liên kết
  `post_recipients(post_id, recipient_id, ...)`; bảng này có thể rỗng cho một
  post (trường hợp 0 người nhận).
- Sau khi upload thành công, client gọi FastAPI để tạo post record và (nếu có)
  các bản ghi post_recipients trong PostgreSQL.
- Ảnh của free user được đánh dấu `expires_at = now() + 24h` trong database
  (record vẫn giữ, chỉ ẩn khỏi feed sau 24h).

## Acceptance Criteria

**AC-F05-1:** Mặc định chọn sẵn tất cả bạn bè
```
Given Sender có 4 bạn bè và vừa chụp ảnh hợp lệ
When màn hình chọn người nhận hiển thị
Then cả 4 bạn bè được chọn sẵn theo mặc định
```

**AC-F05-2:** Gửi broadcast tới tất cả bạn bè thành công
```
Given Sender giữ nguyên mặc định chọn cả 3 bạn bè
When Sender nhấn "Gửi"
Then ảnh xuất hiện trên feed của cả 3 người nhận trong vòng 5 giây
  và cả 3 người nhận đều nhận được push notification
  và Sender thấy trạng thái "Đã gửi"
```

**AC-F05-3:** Gửi cho một subset người nhận
```
Given Sender có 4 bạn bè và bỏ chọn còn lại 2 người (User B, User C)
When Sender nhấn "Gửi"
Then ảnh chỉ xuất hiện trên feed của User B và User C
  và hai người còn lại không nhận được ảnh hay notification
```

**AC-F05-4:** Gửi khi 0 người nhận — lưu vào History của mình
```
Given Sender chưa có bạn bè nào (hoặc bỏ chọn hết người nhận)
When Sender nhấn "Gửi"
Then ảnh vẫn được upload và lưu thành công
  và ảnh xuất hiện trong History "Đã gửi" của Sender
  và không có push notification nào được gửi đi
```

**AC-F05-5:** One-shot — ảnh bị discard sau khi gửi
```
Given Sender đã gửi ảnh thành công
When Sender muốn gửi tiếp
Then ảnh đã bị discard và không còn để gửi lại
  và Sender phải chụp ảnh mới để gửi tiếp
```

**AC-F05-6:** Mất kết nối khi gửi
```
Given Sender đang upload ảnh và mất kết nối internet
When kết nối được khôi phục trong vòng 30 giây
Then hệ thống tự động retry upload
  và ảnh được gửi thành công đến tất cả người nhận đã chọn
  mà không cần Sender thao tác lại
```

**AC-F05-7:** Upload thất bại sau 3 lần retry
```
Given Sender đang upload và mất kết nối kéo dài
When hệ thống đã retry 3 lần thất bại
Then hệ thống hiển thị thông báo lỗi rõ ràng
  và ảnh chưa được lưu cũng như chưa gửi cho bất kỳ người nhận nào
```
