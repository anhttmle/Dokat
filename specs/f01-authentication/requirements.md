# F01 — Authentication & Guest Mode — Requirements

## Goal

Cho phép người dùng bắt đầu sử dụng app ngay lập tức dưới dạng Guest (ẩn
danh) mà không cần nhập bất kỳ thông tin nào, sau đó nâng cấp lên tài khoản
đầy đủ bằng cách liên kết Apple / Google / Facebook khi thực hiện các hành
động cần định danh.

## Users / Actors

- **Guest User:** Người dùng chưa liên kết tài khoản mạng xã hội, được định
  danh bằng anonymous ID.
- **Linked User:** Người dùng đã liên kết ít nhất một tài khoản mạng xã hội.
- **System:** Backend FastAPI + Firebase Auth.

## Functional Requirements

1. Hệ thống SHALL tự động tạo một anonymous ID duy nhất cho người dùng ngay
   khi mở app lần đầu, không yêu cầu bất kỳ thông tin đầu vào nào.
2. Hệ thống SHALL lưu anonymous ID vào local storage để khôi phục session khi
   mở lại app (trong cùng một lần cài đặt).
3. Hệ thống SHALL chỉ khôi phục session sau khi app bị gỡ và cài lại nếu người
   dùng đã liên kết ít nhất một tài khoản OAuth; nếu chưa liên kết, hệ thống
   SHALL tạo một anonymous ID mới.
4. Hệ thống SHALL cho phép Guest User dùng toàn bộ tính năng xem feed và xem
   ảnh nhận được mà không cần liên kết tài khoản.
5. Hệ thống SHALL hiển thị prompt liên kết tài khoản (Apple / Google /
   Facebook) khi Guest User thực hiện một trong các hành động: gửi ảnh, thêm
   bạn bè.
6. Hệ thống SHALL bắt buộc liên kết tài khoản nếu tài khoản Guest đã tồn tại
   quá 7 ngày mà chưa liên kết.
7. Hệ thống SHALL sử dụng Firebase Auth để xử lý OAuth flow với Apple / Google
   / Facebook trực tiếp từ client.
8. Hệ thống SHALL liên kết anonymous ID với tài khoản OAuth sau khi người dùng
   xác thực thành công, không làm mất dữ liệu đã có (bạn bè, ảnh, pet profile).
9. Hệ thống SHALL issue một JWT (hoặc Firebase ID Token) để xác thực các
   request đến FastAPI backend.
10. Hệ thống SHALL verify JWT/Firebase ID Token ở mỗi request đến FastAPI
    backend.
11. Hệ thống SHALL cho phép người dùng liên kết thêm hoặc thay đổi tài khoản
    mạng xã hội trong phần Settings (xem F10).

## Non-goals

- Không hỗ trợ đăng nhập bằng email/password hay số điện thoại trong MVP.
- Không hỗ trợ xóa tài khoản trong MVP.
- Không có Group Auth (auth theo nhóm/tổ chức).
- Không khôi phục dữ liệu Guest sau khi gỡ app nếu chưa liên kết OAuth.

## Technical Constraints

- Firebase Anonymous Auth phải được bật trong Firebase project.
- OAuth redirect scheme phải được đăng ký đúng trong Apple Developer Console
  và Google Cloud Console.
- JWT/Firebase ID Token phải được verify ở mỗi request FastAPI.
- Anonymous ID lưu trong local storage; chỉ Linked User mới có khả năng khôi
  phục danh tính sau khi cài lại app (dựa trên OAuth identity từ Firebase).

## Acceptance Criteria

**AC-F01-1:** Guest Mode khởi tạo
```
Given người dùng mở app lần đầu tiên
When app hoàn tất khởi động
Then hệ thống tạo anonymous ID và đưa người dùng vào màn hình Feed
  mà không cần nhập bất kỳ thông tin nào
```

**AC-F01-2:** Prompt liên kết khi gửi ảnh
```
Given người dùng là Guest User (chưa liên kết)
When người dùng nhấn nút "Gửi ảnh"
Then hệ thống hiển thị bottom sheet yêu cầu liên kết tài khoản
  và không thực hiện hành động gửi cho đến khi liên kết thành công
```

**AC-F01-3:** Prompt liên kết khi thêm bạn
```
Given người dùng là Guest User (chưa liên kết)
When người dùng thực hiện thêm bạn bè
Then hệ thống hiển thị prompt yêu cầu liên kết tài khoản
  và không tạo friendship cho đến khi liên kết thành công
```

**AC-F01-4:** Bắt buộc liên kết sau 7 ngày
```
Given người dùng là Guest User đã tạo tài khoản từ đúng 7 ngày trước
When người dùng mở app
Then hệ thống hiển thị màn hình full-screen bắt buộc liên kết tài khoản
  và không cho phép dismiss màn hình này
```

**AC-F01-5:** Liên kết tài khoản không mất dữ liệu
```
Given người dùng là Guest User có 5 bạn bè và 3 ảnh đã gửi
When người dùng liên kết tài khoản Google thành công
Then toàn bộ bạn bè và ảnh vẫn còn nguyên sau khi liên kết
```

**AC-F01-6:** Khôi phục session trong cùng lần cài đặt
```
Given người dùng đã đăng nhập và tắt app (chưa gỡ app)
When người dùng mở lại app
Then hệ thống tự động khôi phục session mà không yêu cầu đăng nhập lại
```

**AC-F01-7:** Gỡ và cài lại app — Guest chưa liên kết
```
Given người dùng là Guest User chưa liên kết OAuth
When người dùng gỡ app và cài lại
Then hệ thống tạo một anonymous ID mới
  và không khôi phục dữ liệu Guest cũ
```

**AC-F01-8:** Gỡ và cài lại app — đã liên kết OAuth
```
Given người dùng đã liên kết tài khoản Google
When người dùng gỡ app, cài lại và đăng nhập Google
Then hệ thống khôi phục đúng tài khoản cùng toàn bộ dữ liệu trước đó
```
