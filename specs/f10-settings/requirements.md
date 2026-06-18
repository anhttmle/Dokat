# F10 — Settings (Liên kết tài khoản, Block/Report, Logout) — Requirements

## Goal

Cung cấp các tùy chọn cài đặt tài khoản cần thiết cho MVP: liên kết/hủy liên
kết mạng xã hội, chặn/báo cáo người dùng vi phạm, và đăng xuất.

## Users / Actors

- **User:** Thực hiện các thao tác cài đặt.
- **Admin/Moderation Team:** Nhận report từ người dùng để xử lý.
- **System:** Xử lý liên kết OAuth, quản lý block list.

## Functional Requirements

**Liên kết tài khoản:**

1. Hệ thống SHALL hiển thị trạng thái liên kết của từng provider
   (Apple / Google / Facebook) trong Settings.
2. Hệ thống SHALL cho phép người dùng liên kết một provider chưa được liên kết.
3. Hệ thống SHALL cho phép người dùng hủy liên kết một provider, với điều kiện
   tài khoản còn ít nhất một provider khác được liên kết (tránh khóa tài
   khoản).

**Block/Report:**

4. Hệ thống SHALL chỉ cho phép người dùng block một người trong danh sách bạn
   bè hiện tại; khi block thì friendship bị xóa và hai bên không thể gửi ảnh
   cho nhau.
5. Hệ thống SHALL thực hiện block ở chế độ silent — người bị block không nhận
   được bất kỳ thông báo nào về việc bị block.
6. Hệ thống SHALL cho phép người dùng report một người dùng khác với lý do
   (danh sách lý do cố định: spam, nội dung không phù hợp, quấy rối, khác).
7. Hệ thống SHALL lưu report vào database để Admin/Moderation Team xử lý.
8. Hệ thống SHALL ẩn người dùng bị block khỏi danh sách bạn bè và feed.

**Logout:**

9. Hệ thống SHALL cho phép người dùng đăng xuất; khi đăng xuất thì xóa local
   session và device token.
10. Hệ thống SHALL sau khi đăng xuất điều hướng người dùng về màn hình
    Onboarding.

## Non-goals

- Không có Privacy settings nâng cao (ai thấy profile, ai gửi được ảnh)
  trong MVP.
- Không có tính năng Hide post/user trong MVP.
- Không có tính năng xóa tài khoản trong MVP.
- Không có tính năng Cache cleaning trong MVP.
- Không cho phép block người không nằm trong danh sách bạn bè.
- Không thông báo cho người bị block (silent block).

## Technical Constraints

- OAuth unlink thực hiện qua Firebase Auth API.
- Block list lưu trong PostgreSQL; mọi feed/friend query phải exclude users
  trong block list.
- Report record lưu với: reporter_id, reported_user_id, reason, created_at.
- Block chỉ áp dụng cho cặp user đang là bạn bè (validation phía backend).

## Acceptance Criteria

**AC-F10-1:** Liên kết Google thành công
```
Given User chưa liên kết Google trong Settings
When User nhấn "Liên kết Google" và hoàn thành OAuth flow
Then Settings hiển thị Google là "Đã liên kết"
  và User có thể dùng tài khoản Google để đăng nhập lần sau
```

**AC-F10-2:** Không cho hủy liên kết provider duy nhất
```
Given User chỉ có duy nhất Apple được liên kết
When User cố hủy liên kết Apple
Then hệ thống hiển thị thông báo lỗi
  và không thực hiện hủy liên kết
```

**AC-F10-3:** Block user (silent)
```
Given User A và User B là bạn bè
When User A block User B
Then User B biến mất khỏi danh sách bạn bè của User A
  và User A biến mất khỏi danh sách bạn bè của User B
  và không ai trong hai người có thể gửi ảnh cho người kia
  và User B không nhận được bất kỳ thông báo nào về việc bị block
```

**AC-F10-4:** Chỉ block được bạn bè
```
Given User A và User X không phải là bạn bè
When User A cố block User X
Then hệ thống không cho phép thực hiện block
```

**AC-F10-5:** Report user
```
Given User A muốn report User B
When User A gửi report với lý do "Spam"
Then hệ thống lưu report thành công
  và hiển thị xác nhận "Cảm ơn bạn đã báo cáo"
  và User B vẫn hiển thị bình thường (không bị ẩn tự động)
```

**AC-F10-6:** Logout
```
Given User đang đăng nhập
When User nhấn "Đăng xuất" và xác nhận
Then session bị xóa trên thiết bị
  và device token bị xóa
  và User được redirect về màn hình Onboarding
  và User không còn nhận push notification
```
