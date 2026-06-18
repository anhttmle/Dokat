# F11 — Location & Time Metadata (Store Only) — Requirements

## Goal

Gắn metadata vị trí (lat/lng) và thời gian vào mỗi ảnh được chụp để phục vụ
tính năng landmark/map trong phiên bản tương lai. MVP chỉ lưu, không hiển thị.

## Users / Actors

- **User:** Người chụp ảnh; app yêu cầu quyền location.
- **System:** Backend lưu metadata vào PostgreSQL.

## Functional Requirements

1. Hệ thống SHALL yêu cầu quyền truy cập vị trí khi người dùng sử dụng tính
   năng chụp ảnh lần đầu.
2. Hệ thống SHALL ghi lại latitude, longitude và timestamp của thiết bị tại
   thời điểm chụp ảnh, nếu người dùng đã cấp quyền.
3. Hệ thống SHALL cho phép chụp và gửi ảnh bình thường nếu người dùng từ chối
   quyền location (metadata vị trí để trống).
4. Hệ thống SHALL lưu location metadata vào bảng post trong PostgreSQL.
5. Hệ thống SHALL không hiển thị bất kỳ thông tin vị trí nào trên UI trong
   MVP.

## Non-goals

- Không hiển thị map, landmark hay địa điểm trong MVP.
- Không có tính năng "Offline with friend" dựa trên location proximity.
- Không chia sẻ vị trí với người dùng khác trong MVP.

## Technical Constraints

- Location được lấy một lần ngay tại thời điểm chụp (không tracking liên tục).
- Dữ liệu location chỉ dùng nội bộ, không expose qua API cho client.
- Latitude/Longitude lưu ở độ chính xác 8 chữ số thập phân (ví dụ
  `DECIMAL(11, 8)` cho lat và `DECIMAL(12, 8)` cho lng) để giữ độ chính xác
  GPS tối đa.

## Acceptance Criteria

**AC-F11-1:** Lưu metadata khi có quyền
```
Given User đã cấp quyền location cho app
When User chụp và gửi ảnh thành công
Then record post trong PostgreSQL có latitude và longitude hợp lệ
  với độ chính xác 8 chữ số thập phân
  và timestamp chụp đúng với thời điểm thực tế
```

**AC-F11-2:** Gửi ảnh bình thường khi không có quyền location
```
Given User từ chối quyền location
When User chụp và gửi ảnh
Then ảnh vẫn được gửi thành công
  và record post trong PostgreSQL có latitude = NULL, longitude = NULL
```

**AC-F11-3:** Không hiển thị location trên UI
```
Given ảnh được gửi kèm metadata vị trí
When Recipient xem ảnh trong feed hoặc History
Then không có bất kỳ thông tin vị trí nào hiển thị trên UI
```
