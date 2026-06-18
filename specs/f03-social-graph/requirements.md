# F03 — Social Graph — Kết Bạn qua QR — Requirements

## Goal

Cho phép người dùng kết bạn với nhau thông qua QR code dạng OTP — scan là kết
bạn ngay, không cần xác nhận. Giới hạn tối đa 20 bạn bè (hard limit).

## Users / Actors

- **Initiator:** Người dùng hiển thị QR code của mình.
- **Scanner:** Người dùng dùng camera scan QR code của người khác.
- **System:** Backend xử lý tạo cạnh (edge) trong social graph.

## Functional Requirements

1. Hệ thống SHALL tạo một QR code OTP duy nhất cho mỗi người dùng khi họ mở
   màn hình "Thêm bạn".
2. Hệ thống SHALL gắn thời hạn hiệu lực cho QR OTP tối đa là 5 phút; sau đó
   QR tự động hết hạn.
3. Hệ thống SHALL hiển thị countdown timer trên màn hình "Thêm bạn" và tự
   động generate, hiển thị QR mới khi timer về 0 (auto-refresh).
4. Hệ thống SHALL tạo liên kết bạn bè (friendship edge) hai chiều ngay lập tức
   khi Scanner quét QR hợp lệ — không yêu cầu Initiator xác nhận.
5. Hệ thống SHALL từ chối tạo friendship nếu một trong hai người dùng đã đạt
   giới hạn 20 bạn bè và hiển thị thông báo lỗi rõ ràng.
6. Hệ thống SHALL từ chối nếu hai người dùng đã là bạn bè, tránh tạo duplicate
   edge.
7. Hệ thống SHALL từ chối nếu người dùng cố kết bạn với chính mình.
8. Hệ thống SHALL lưu friendship graph trong PostgreSQL với timestamp tạo.
9. Hệ thống SHALL cho phép người dùng xem danh sách bạn bè hiện tại.
10. Hệ thống SHALL hiển thị confirmation dialog trước khi xóa bạn bè.
11. Hệ thống SHALL cho phép người dùng xóa bạn bè sau khi xác nhận; khi xóa
    thì edge bị remove hai chiều.

## Non-goals

- Không có tính năng sync danh bạ điện thoại trong MVP.
- Không có hệ thống "chờ chấp nhận" (friend request pending).
- Không có tính năng tìm kiếm bạn bè theo tên/username.
- Không có group trong MVP.

## Technical Constraints

- QR OTP được tạo server-side, lưu tạm trong Redis hoặc PostgreSQL với TTL
  5 phút.
- QR code chứa một deep link dẫn về app.
- Mỗi QR OTP chỉ được sử dụng một lần (single-use).
- Auto-refresh QR phía client gọi lại endpoint tạo OTP khi countdown về 0.

## Acceptance Criteria

**AC-F03-1:** Tạo QR thành công
```
Given người dùng mở màn hình "Thêm bạn"
When màn hình load xong
Then một QR code được hiển thị trong vòng 2 giây
  và QR code có thể scan được bằng camera
  và một countdown timer hiển thị thời gian còn lại
```

**AC-F03-2:** Kết bạn ngay khi scan
```
Given User A hiển thị QR code (chưa hết hạn)
When User B scan QR code của User A
Then User A và User B trở thành bạn bè ngay lập tức
  và cả hai thấy nhau trong danh sách bạn bè
  mà không cần bất kỳ bước xác nhận nào
```

**AC-F03-3:** QR auto-refresh khi hết hạn
```
Given User A đang ở màn hình "Thêm bạn" và countdown về 0
When QR cũ hết hạn
Then hệ thống tự động tạo và hiển thị QR code mới
  và countdown timer được reset về 5 phút
```

**AC-F03-4:** Scan QR đã hết hạn
```
Given User A tạo QR code và 5 phút đã trôi qua (QR chưa được refresh)
When User B scan QR code đó
Then hệ thống trả về lỗi "QR đã hết hạn"
  và không tạo friendship
```

**AC-F03-5:** Hard limit 20 bạn bè
```
Given User A đang có đúng 20 bạn bè
When User B scan QR của User A
Then hệ thống hiển thị thông báo "User A đã đạt giới hạn bạn bè"
  và không tạo friendship
```

**AC-F03-6:** QR single-use
```
Given User B đã dùng QR code của User A để kết bạn thành công
When User C dùng cùng QR code đó để scan
Then hệ thống trả về lỗi "QR đã được sử dụng"
  và không tạo friendship mới
```

**AC-F03-7:** Từ chối kết bạn với chính mình
```
Given User A mở camera và scan chính QR code của mình
When hệ thống xử lý
Then hệ thống từ chối tạo friendship
  và hiển thị thông báo lỗi phù hợp
```

**AC-F03-8:** Từ chối duplicate friendship
```
Given User A và User B đã là bạn bè
When User B scan QR mới của User A
Then hệ thống không tạo edge trùng lặp
  và hiển thị thông báo đã là bạn bè
```

**AC-F03-9:** Xóa bạn có xác nhận
```
Given User A và User B là bạn bè
When User A nhấn xóa bạn và xác nhận trong confirmation dialog
Then friendship edge bị remove hai chiều
  và cả hai không còn thấy nhau trong danh sách bạn bè
```

**AC-F03-10:** Hủy xóa bạn trong dialog
```
Given User A nhấn xóa bạn với User B
When User A nhấn "Hủy" trong confirmation dialog
Then friendship vẫn được giữ nguyên
  và User B vẫn còn trong danh sách bạn bè của User A
```
