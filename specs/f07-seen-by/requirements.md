# F07 — Seen By — Requirements

## Goal

Cho phép Sender biết những ai đã xem ảnh của mình (tổng hợp theo từng ảnh),
thay thế cho hệ thống reaction trong MVP.

## Users / Actors

- **Sender:** Người gửi ảnh, muốn biết ai đã xem.
- **Recipients:** Những người nhận ảnh; trạng thái "đã xem" được ghi nhận tự
  động cho từng người.
- **System:** Backend lưu và trả về seen events.

## Functional Requirements

1. Hệ thống SHALL ghi nhận sự kiện "đã xem" cho một post ngay khi ảnh được
   render đầy đủ trên màn hình full-screen của một Recipient (immediate).
2. Hệ thống SHALL lưu seen event với: post_id, viewer_user_id, seen_at
   timestamp.
3. Hệ thống SHALL cho phép Sender xem danh sách tất cả những người đã xem ảnh
   khi nhấn vào ảnh từ lịch sử gửi.
4. Hệ thống SHALL hiển thị số lượng người đã xem (e.g. "2 người đã xem") trên
   ảnh trong lịch sử của Sender, tổng hợp trên tất cả người nhận.
5. Hệ thống SHALL cập nhật danh sách seen trong thời gian thực (hoặc khi
   Sender refresh).
6. Hệ thống SHALL không ghi duplicate seen event cho cùng một cặp (post_id,
   viewer_id).

## Non-goals

- Không có reaction (Like, Haha, Wow, ...) trong MVP.
- Không có comment hoặc quick response trong MVP.
- Không có reply by capture trong MVP.
- Không thông báo riêng cho từng lần seen (chỉ hiện số lượng tổng hợp và danh
  sách).

## Technical Constraints

- Seen event được ghi nhận qua một API call ngay khi client render ảnh ở chế
  độ full-screen (immediate, không cần ngưỡng thời gian).
- Tránh ghi duplicate seen event cho cùng một cặp (post_id, viewer_id) bằng
  unique constraint hoặc upsert.
- Seen list của một post tổng hợp seen event từ tất cả Recipients của post đó
  (xem F05).

## Acceptance Criteria

**AC-F07-1:** Ghi nhận seen ngay khi xem ảnh
```
Given User B là một trong các người nhận ảnh từ User A và mở xem full-screen
When ảnh được render đầy đủ trên màn hình
Then hệ thống ghi nhận seen event cho User B ngay lập tức
  và seen event lưu đúng post_id, viewer_user_id, seen_at
```

**AC-F07-2:** Hiển thị danh sách seen cho Sender (nhiều người)
```
Given User A đã gửi ảnh cho User B, User C, User D
  và User B, User C đã xem nhưng User D chưa xem
When User A nhấn vào ảnh đó trong lịch sử gửi
Then User A thấy danh sách "User B, User C đã xem"
  và số lượng hiển thị là "2 người đã xem"
```

**AC-F07-3:** Không duplicate seen
```
Given User B đã xem ảnh của User A
When User B mở xem lại ảnh đó lần thứ hai
Then hệ thống không tạo thêm seen event mới
  và số lượng người xem không tăng
```
