# F02 — Owner Profile & Pet Profile — Requirements

## Goal

Cho phép người dùng quản lý hình ảnh thú cưng thông qua Pet Profile (tùy
chọn, có hỗ trợ AI nhận diện loài và giới tính từ ảnh). Owner Profile được
tự động lấy từ tài khoản OAuth khi liên kết, không yêu cầu người dùng nhập
thủ công.

## Users / Actors

- **User:** Người dùng đã có anonymous ID (Guest hoặc Linked).
- **AI Service:** Model nhận diện hình ảnh (client-side) để auto-fill thông
  tin thú cưng và gợi ý gán ảnh vào Pet Profile.

## Functional Requirements

1. Hệ thống SHALL KHÔNG yêu cầu người dùng nhập bất kỳ trường Owner Profile
   nào trong flow Onboarding; Guest User được vào thẳng màn hình Feed.
2. Hệ thống SHALL tự động lấy thông tin Owner Profile (tên, ảnh đại diện nếu
   có) từ tài khoản Apple / Google / Facebook khi người dùng liên kết OAuth.
3. Hệ thống SHALL cho phép người dùng tạo Pet Profile với các trường: Tên,
   Giới tính, Loại (chó/mèo), Ngày sinh.
4. Hệ thống SHALL giới hạn tối đa 1 Pet Profile cho mỗi free user trong MVP.
5. Hệ thống SHALL coi việc tạo Pet Profile là tùy chọn ở mọi thời điểm; người
   dùng không bao giờ bị bắt buộc phải tạo Pet Profile để sử dụng app.
6. Hệ thống SHALL cho phép người dùng upload/chụp ảnh thú cưng khi tạo Pet
   Profile.
7. Hệ thống SHALL chạy AI model nhận diện trên client để auto-fill các trường
   Loại (chó/mèo) và Giới tính từ ảnh được cung cấp.
8. Hệ thống SHALL auto-fill trường Giới tính chỉ khi model có độ tin cậy
   ≥ 70%.
9. Hệ thống SHALL cho phép người dùng chỉnh sửa lại các thông tin do AI
   auto-fill trước khi lưu.
10. Khi người dùng chụp một bức ảnh (xem F04), hệ thống SHALL gợi ý một trong
    ba lựa chọn: gán ảnh vào Pet Profile đã có, tạo Pet Profile mới, hoặc bỏ
    qua.
11. Hệ thống SHALL cho phép người dùng chỉnh sửa Owner Profile và Pet Profile
    bất kỳ lúc nào từ màn hình Profile.

## Non-goals

- Không có tính năng AI generate avatar/artwork cho thú cưng trong MVP.
- Không hỗ trợ loại thú cưng ngoài chó/mèo.
- Không có tính năng chia sẻ công khai Pet Profile ra ngoài danh sách bạn bè.
- Không bắt buộc Owner Profile hay Pet Profile tại bất kỳ thời điểm nào.
- Không hỗ trợ nhiều hơn 1 Pet Profile cho free user (premium ngoài phạm vi
  MVP).

## Technical Constraints

- AI model nhận diện chạy hoàn toàn on-device (không gọi API server) để tránh
  latency và chi phí.
- Ảnh avatar Pet lưu lên S3, phục vụ qua CloudFront CDN.
- Dữ liệu profile lưu trong PostgreSQL.
- Giới hạn 1 Pet Profile/free user được enforce ở backend (validation khi
  tạo).

## Acceptance Criteria

**AC-F02-1:** Guest vào thẳng Feed, không Onboarding profile
```
Given người dùng vừa tạo anonymous ID lần đầu
When app hoàn tất khởi động
Then người dùng vào thẳng màn hình Feed
  và không có màn hình nào yêu cầu điền Owner Profile hay Pet Profile
```

**AC-F02-2:** Owner Profile auto-fill từ OAuth
```
Given Guest User chưa có Owner Profile
When người dùng liên kết tài khoản Google thành công
Then hệ thống tự động điền tên và ảnh đại diện từ tài khoản Google
  vào Owner Profile
```

**AC-F02-3:** AI auto-fill Pet Profile
```
Given người dùng cung cấp ảnh một con chó khi tạo Pet Profile
When AI model hoàn tất nhận diện (≤ 3 giây)
Then trường "Loại" được tự động điền là "Chó"
  và trường "Giới tính" được điền nếu model có độ tin cậy ≥ 70%
```

**AC-F02-4:** Chỉnh sửa thông tin AI auto-fill
```
Given AI đã auto-fill Loại = "Mèo" nhưng thực tế là "Chó"
When người dùng chỉnh sửa lại trường Loại
Then hệ thống chấp nhận giá trị người dùng nhập
  và lưu đúng "Chó" vào database
```

**AC-F02-5:** Giới hạn 1 Pet Profile cho free user
```
Given free user đã có đúng 1 Pet Profile
When người dùng cố tạo Pet Profile thứ 2
Then hệ thống từ chối và hiển thị thông báo giới hạn
  và không lưu Pet Profile mới
```

**AC-F02-6:** Gợi ý gán ảnh khi chụp
```
Given người dùng chụp một bức ảnh hợp lệ
When AI hoàn tất nhận diện
Then hệ thống hiển thị gợi ý gán ảnh vào Pet Profile có sẵn,
  tạo Pet Profile mới, hoặc bỏ qua
  và người dùng có thể chọn bỏ qua mà vẫn tiếp tục flow gửi ảnh
```

**AC-F02-7:** Pet Profile luôn tùy chọn
```
Given người dùng chưa có Pet Profile nào
When người dùng dùng các tính năng feed, gửi ảnh, kết bạn
Then hệ thống không chặn hay bắt buộc tạo Pet Profile tại bất kỳ bước nào
```
