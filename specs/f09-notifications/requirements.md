# F09 — Notification System — Requirements

## Goal

Thông báo cho người dùng khi nhận ảnh mới và nhắc nhở chăm sóc thú cưng theo
lịch cố định được cấu hình bởi App Owner cho từng loại thú cưng.

## Users / Actors

- **Recipient:** Nhận push notification khi có ảnh mới.
- **Pet Owner (User):** Nhận daily reminders chăm sóc thú cưng.
- **App Owner (Admin):** Cấu hình lịch reminder cho từng loại thú cưng
  (chó/mèo) thông qua config file.
- **System:** Notification service gửi push qua FCM/APNs.

## Functional Requirements

**Notification — Ảnh mới:**

1. Hệ thống SHALL gửi push notification đến Recipient ngay sau khi một ảnh mới
   được gửi đến họ.
2. Push notification SHALL chứa: tên người gửi, tên thú cưng (nếu có), và
   thumbnail ảnh.
3. Hệ thống SHALL điều hướng người dùng đến ảnh tương ứng khi họ tap vào
   notification.

**Notification — Daily Pet Reminders:**

4. Hệ thống SHALL hỗ trợ các loại reminder: cho ăn, ngủ, tắm, chơi.
5. Hệ thống SHALL cho phép App Owner cấu hình lịch (giờ) cho từng loại
   reminder, phân theo loại thú cưng (chó/mèo) qua một config file (YAML/JSON)
   deploy cùng backend.
6. Hệ thống SHALL gửi reminder đến tất cả người dùng có thú cưng thuộc loại
   tương ứng vào đúng giờ đã cấu hình.
7. Hệ thống SHALL cho phép người dùng bật/tắt từng loại reminder trong
   Settings; mặc định tất cả reminder được bật (opt-out model).
8. Hệ thống SHALL tôn trọng timezone của thiết bị người dùng khi gửi reminder.

**Chung:**

9. Hệ thống SHALL dùng Firebase Cloud Messaging (FCM) cho Android và APNs cho
   iOS.
10. Hệ thống SHALL lưu device token vào PostgreSQL khi người dùng cấp quyền
    notification.
11. Hệ thống SHALL KHÔNG áp dụng giới hạn số lượng notification mỗi ngày trong
    MVP.

## Non-goals

- Không có notification cho video trong MVP.
- Không có in-app notification center / notification history trong MVP.
- Người dùng không tự cài giờ reminder — lịch do App Owner quản lý.
- Không có rate limit số lượng notification/ngày trong MVP.

## Technical Constraints

- FastAPI background job (Celery hoặc APScheduler) xử lý việc gửi reminder
  theo lịch.
- Lịch reminder được khai báo trong config file (YAML/JSON) deploy cùng
  backend; thay đổi lịch yêu cầu redeploy.
- Device token được refresh và cập nhật mỗi khi app mở.
- Mặc định trạng thái bật/tắt reminder của user mới là tất cả "bật".

## Acceptance Criteria

**AC-F09-1:** Notification ảnh mới
```
Given User B đang có app đóng (background)
When User A gửi ảnh cho User B
Then User B nhận push notification trong vòng 5 giây
  với nội dung hiển thị tên User A và thumbnail ảnh
```

**AC-F09-2:** Deep link từ notification
```
Given User B nhận push notification về ảnh mới
When User B tap vào notification
Then app mở ra và điều hướng thẳng đến ảnh đó trong feed
```

**AC-F09-3:** Daily reminder đúng giờ
```
Given App Owner đã cấu hình reminder "Cho ăn" cho Chó lúc 07:00 trong config
  và User có ít nhất một Pet Profile loại "Chó"
When đồng hồ điện thoại User đến 07:00 (theo timezone thiết bị)
Then User nhận push notification "Đến giờ cho [tên chó] ăn rồi!"
```

**AC-F09-4:** Reminder mặc định bật
```
Given User vừa cài app và cấp quyền notification
When App Owner cấu hình một reminder cho loại pet của User
Then User nhận reminder đó mà không cần bật thủ công (opt-out model)
```

**AC-F09-5:** Tắt reminder
```
Given User đã bật reminder "Tắm" trong Settings (mặc định)
When User tắt reminder "Tắm"
Then User không còn nhận notification loại "Tắm" kể từ sau đó
```

**AC-F09-6:** Timezone đúng
```
Given User A ở Hà Nội (UTC+7) và App Owner cấu hình reminder lúc 07:00
When đồng hồ Hà Nội là 07:00
Then User A nhận reminder (không phải 07:00 UTC)
```
