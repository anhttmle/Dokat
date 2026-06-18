# F08 — History / Timeline (1 ngày) — Requirements

## Goal

Cho phép người dùng cuộn ngược lại timeline ảnh đã gửi/nhận trong vòng 24 giờ
qua, như một lịch sử hoạt động ngắn hạn.

## Users / Actors

- **User:** Người xem lại ảnh đã gửi hoặc nhận trong ngày.

## Functional Requirements

1. Hệ thống SHALL cung cấp màn hình History riêng biệt, có thể truy cập từ
   bottom navigation.
2. Hệ thống SHALL hiển thị tất cả ảnh đã gửi và nhận trong 24 giờ qua, theo
   thứ tự thời gian từ mới đến cũ.
3. Hệ thống SHALL phân tách rõ hai section: "Đã gửi" và "Đã nhận".
4. Hệ thống SHALL giới hạn history chỉ trong khoảng 24 giờ tính từ thời điểm
   hiện tại — ảnh cũ hơn không hiển thị.
5. Hệ thống SHALL cho phép người dùng nhấn vào từng ảnh để xem full-screen,
   bao gồm thông tin người gửi/nhận và seen list (xem F07).
6. Hệ thống SHALL hiển thị empty state nếu không có ảnh nào trong 24h qua.

## Non-goals

- Không hỗ trợ xem lịch sử quá 24 giờ đối với free user trong MVP.
- Không có tính năng download hay chia sẻ ảnh ra ngoài app.
- Không có "On this day" memory notification trong MVP.

## Technical Constraints

- API query lịch sử dùng filter `created_at >= NOW() - INTERVAL '24 hours'`.
- Phân trang cursor-based để tránh load toàn bộ 24h cùng lúc.

## Acceptance Criteria

**AC-F08-1:** Hiển thị lịch sử đúng 24h
```
Given User A đã gửi ảnh lúc 10:00 hôm nay và lúc 11:00 hôm qua
When User A mở màn hình History lúc 12:00 hôm nay
Then chỉ ảnh 10:00 hôm nay xuất hiện trong lịch sử
  và ảnh 11:00 hôm qua không hiển thị
```

**AC-F08-2:** Phân section rõ ràng
```
Given User đã gửi 2 ảnh và nhận 3 ảnh trong 24h qua
When User mở màn hình History
Then section "Đã gửi" hiển thị đúng 2 ảnh
  và section "Đã nhận" hiển thị đúng 3 ảnh
```

**AC-F08-3:** Xem ảnh full-screen từ History
```
Given User mở màn hình History
When User nhấn vào một ảnh bất kỳ
Then ảnh mở ra full-screen kèm thông tin người gửi/nhận và seen list
```

**AC-F08-4:** Empty state khi không có ảnh
```
Given User không gửi hay nhận ảnh nào trong 24h qua
When User mở màn hình History
Then hệ thống hiển thị empty state
```
