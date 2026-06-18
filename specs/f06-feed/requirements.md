# F06 — Feed & App View — Requirements

## Goal

Hiển thị ảnh thú cưng mà người dùng nhận được từ bạn bè theo thứ tự thời gian
gần nhất, trong App View (không có Home Screen Widget cho MVP).

## Users / Actors

- **User (Recipient):** Người xem feed của mình.
- **System:** Backend cung cấp danh sách post theo user.

## Functional Requirements

1. Hệ thống SHALL hiển thị màn hình Feed là màn hình chính sau khi đăng nhập.
2. Hệ thống SHALL hiển thị ảnh nhận được từ tất cả bạn bè, sắp xếp theo thời
   gian mới nhất lên đầu.
3. Hệ thống SHALL chỉ hiển thị ảnh trong vòng 24 giờ kể từ thời điểm gửi
   (đối với free user).
4. Hệ thống SHALL hiển thị thông tin đi kèm mỗi ảnh: tên người gửi, tên thú
   cưng (nếu có), thời gian gửi tương đối (e.g. "3 phút trước").
5. Hệ thống SHALL đánh dấu post là "đã xem" khi người dùng mở ảnh xem đầy đủ
   (full-screen).
6. Hệ thống SHALL phân biệt trạng thái "chưa xem" và "đã xem" bằng visual
   indicator trên feed item.
7. Hệ thống SHALL hỗ trợ pull-to-refresh để tải ảnh mới nhất.
8. Hệ thống SHALL load ảnh từ CloudFront CDN với placeholder khi đang tải.
9. Hệ thống SHALL hiển thị empty state khi feed trống (chưa có bạn hoặc chưa
   nhận ảnh nào trong 24h).
10. Hệ thống SHALL loại trừ ảnh từ những người dùng bị block khỏi feed (xem
    F10).

## Non-goals

- Không có Home Screen Widget trong MVP.
- Không có infinite scroll (feed chỉ hiển thị trong phạm vi 24h).
- Không có thuật toán ranking/recommendation — chỉ chronological order.
- Không có ads/sponsored content trong MVP.

## Technical Constraints

- Feed API endpoint trả về danh sách post có phân trang (cursor-based
  pagination).
- Ảnh được serve qua CloudFront CDN để tối ưu tốc độ tải.
- Client cache ảnh đã tải để tránh load lại khi scroll.
- Feed query phải filter `expires_at > NOW()` và exclude block list.

## Acceptance Criteria

**AC-F06-1:** Feed hiển thị ảnh mới
```
Given User A gửi ảnh cho User B lúc 14:00
When User B mở app lúc 14:01
Then ảnh của User A xuất hiện ở đầu feed của User B
  với thông tin "1 phút trước"
```

**AC-F06-2:** Ảnh hết hạn 24h ẩn khỏi feed
```
Given User A gửi ảnh cho User B lúc 14:00 hôm qua
When User B mở feed vào lúc 14:01 hôm nay (25 giờ sau)
Then ảnh đó không còn xuất hiện trên feed
```

**AC-F06-3:** Trạng thái chưa xem / đã xem
```
Given User B nhận ảnh mới chưa xem
When User B mở app
Then ảnh hiển thị với visual indicator "chưa xem" (e.g. viền nổi bật)
  và sau khi User B xem ảnh đầy đủ, indicator chuyển sang "đã xem"
```

**AC-F06-4:** Empty state
```
Given User mới chưa có bạn bè nào
When User mở màn hình Feed
Then hệ thống hiển thị màn hình empty state với hướng dẫn "Thêm bạn bè để
  xem ảnh thú cưng của họ"
```

**AC-F06-5:** Pull-to-refresh
```
Given User đang ở màn hình Feed
When User kéo xuống để refresh
Then hệ thống tải lại danh sách ảnh mới nhất
  và hiển thị các ảnh mới (nếu có) ở đầu feed
```

**AC-F06-6:** Sắp xếp theo thời gian mới nhất
```
Given User B nhận ảnh từ User A lúc 14:00 và từ User C lúc 14:05
When User B mở feed
Then ảnh của User C (14:05) hiển thị phía trên ảnh của User A (14:00)
```
