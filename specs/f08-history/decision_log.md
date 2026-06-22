# F08 — History / Timeline — Decision Log

---

## DL-F08-01 — F08 là tính năng đọc-only; chỉ thêm 2 endpoint `/history/*`

**Date:** 2026-06-22
**Context:** Requirements F08 mô tả xem lại ảnh đã gửi/nhận trong
24h. Dữ liệu (`posts`, `post_recipients`) đã do F05 tạo; cờ seen do
F07 ghi.
**Decision:** F08 **không** INSERT/UPDATE/DELETE bất kỳ bảng nào;
chỉ thêm hai endpoint đọc `GET /history/sent` và
`GET /history/received` cùng các thành phần client. Việc ghi seen
(khi mở ảnh "đã nhận") uỷ cho `SeenService.markSeen` của F07.
**Consequence:** Cả hai endpoint idempotent — refresh an toàn vô
hạn. Test chỉ cần seed dữ liệu F05/F07 rồi assert kết quả đọc.

---

## DL-F08-02 — F08 không thêm migration (tái dùng bảng F05/F02)

**Date:** 2026-06-22
**Context:** History đọc `posts`, `post_recipients`, `users`,
`pet_profiles` — tất cả đã tồn tại.
**Decision:** F08 **không** tạo bảng/cột/migration mới; chỉ
`SELECT`. Không có test migration cho F08.
**Consequence:** Giảm bề mặt thay đổi (surgical). Mọi thay đổi
schema liên quan ảnh thuộc F05/F02/F07.

---

## DL-F08-03 — Filter 24h bằng `expires_at > now()`, không xoá post

**Date:** 2026-06-22
**Context:** Requirements Technical Constraint đề xuất
`created_at >= NOW() - INTERVAL '24 hours'`. F05 đã đặt
`posts.expires_at = created_at + 24h` (DL-F05-03) và F06 lọc 24h
bằng `expires_at > now()` (DL-F06-04).
**Decision:** F08 lọc `expires_at > now()` thay vì so sánh
`created_at`. Vì `expires_at = created_at + 24h` nên hai điều kiện
**tương đương** về kết quả, nhưng cách này tái dùng index
`idx_posts_expires_at` và nhất quán với F05/F06.
**Consequence:** Khi đổi thời lượng (premium) chỉ cần sửa
`POST_EXPIRY_HOURS` ở F05; F08 không tự tính lại mốc 24h.

---

## DL-F08-04 — Tái dùng cursor pagination của `feed_service` (DRY)

**Date:** 2026-06-22
**Context:** Technical Constraint yêu cầu cursor-based pagination.
`feed_service` (F06) đã hiện thực cursor `(created_at, post_id)`
opaque base64 + `InvalidCursorError` + `FEED_PAGE_SIZE`/
`FEED_MAX_PAGE_SIZE` (DL-F06-08).
**Decision:** `history_service` **import lại**
`_encode_cursor`, `_decode_cursor`, `InvalidCursorError`,
`FEED_PAGE_SIZE`, `FEED_MAX_PAGE_SIZE` từ `feed_service` thay vì
viết lại; không định nghĩa hằng/cursor riêng cho F08.
**Consequence:** Cùng định dạng cursor giữa feed và history; sửa
một chỗ áp dụng cả hai. Cursor hỏng → 400 `INVALID_CURSOR` nhất
quán. Nếu `feed_service` đổi cấu trúc cursor, F08 hưởng lợi tự
động (rủi ro coupling chấp nhận được vì cùng domain post).

---

## DL-F08-05 — Sent history mang `recipient_count` + `seen_count`; danh sách chi tiết lấy on-demand

**Date:** 2026-06-22
**Context:** FR-3 cần phân biệt rõ ảnh đã gửi; FR-5 cần xem seen
list khi mở full-screen (qua F07). Danh sách người xem đầy đủ đã có
endpoint `GET /posts/{id}/seen-by` của F07.
**Decision:** Item "đã gửi" chỉ mang hai số tổng hợp
`recipient_count` (= `COUNT(post_recipients)`) và `seen_count`
(= `COUNT(seen_at IS NOT NULL)`) để hiển thị nhanh ở danh sách.
**Danh sách chi tiết** người đã xem được lấy **on-demand** qua
`SeenService.getSeenBy(postId)` khi mở full-screen (không nhồi vào
payload danh sách).
**Consequence:** Payload `GET /history/sent` gọn; tránh N+1 và
trùng lặp dữ liệu seen-by. Phù hợp ranh giới F07 (DL-F07-06).

---

## DL-F08-06 — `GET /history/received` tái dùng block hook của feed

**Date:** 2026-06-22
**Context:** Received history đọc cùng tập dữ liệu với
`GET /feed`. Feed đã block-aware qua `_blocked_sender_ids` (rỗng
đến khi F10 — DL-F06-03). Requirements F08 không nêu block nhưng
ẩn ảnh từ người bị block là hành vi nhất quán cần có.
**Decision:** `get_received` áp dụng cùng helper
`feed_service._blocked_sender_ids(db, viewer_id)` (no-op rỗng đến
khi F10). `get_sent` **không** áp dụng (người dùng luôn xem được
ảnh chính mình đã gửi).
**Consequence:** Feed và received history nhất quán về loại trừ
block. Khi F10 điền helper, cả hai được lọc mà không phải sửa
query. Test received verify hook được áp dụng (no-op).

---

## DL-F08-07 — Endpoint trả 404 khi `firebase_uid` chưa có user row

**Date:** 2026-06-22
**Context:** Resolve `firebase_uid` → viewer UUID; token hợp lệ
nhưng chưa gọi `/auth/session` thì không có user row (giống
DL-F06-05).
**Decision:** Router trả **404 `USER_NOT_FOUND`** (nhất quán pattern
`routers/feed.py` / `routers/posts.py`), không tạo user ngầm
(YAGNI).
**Consequence:** Client luôn gọi `/auth/session` trước (F01) nên
nhánh này hiếm; chốt chặn tránh 500 khi gọi API trực tiếp.

---

## DL-F08-08 — Gắn `SeenByList` (F07) vào full-screen tab "Đã gửi"

**Date:** 2026-06-22
**Context:** F07 cung cấp component `SeenByList` +
`SeenService.getSeenBy`/`markSeen` và cố ý để lại việc **gắn** vào
màn hình History cho F08 (DL-F07-06). FR-5 yêu cầu full-screen kèm
thông tin người gửi/nhận + seen list.
**Decision:** Khi tap ảnh trong section **"Đã gửi"**,
`HistoryScreen` gọi `SeenService.getSeenBy(postId)` rồi render
`SeenByList`. Khi tap ảnh **"Đã nhận"**, gọi
`SeenService.markSeen(postId)` (idempotent) và hiển thị thông tin
người gửi (đã có trong item). F08 **không** tạo endpoint/seen logic
mới — chỉ tái dùng `SeenService`.
**Consequence:** Hoàn tất boundary DL-F07-06. Không trùng lặp logic
seen. F08 test chỉ verify việc gọi đúng `SeenService` ở hai luồng
mở full-screen.

---

## DL-F08-09 — `HistoryScreen` cập nhật `seen` lạc quan khi mở ảnh "Đã nhận"

**Date:** 2026-06-22
**Context:** Design §1.3 chỉ nêu khi mở ảnh "đã nhận" thì gọi
`SeenService.markSeen(postId)`, không nói rõ cờ `seen` ở danh sách
cập nhật ra sao trong khi chờ network. `FeedScreen` (F06) đã có
tiền lệ cập nhật `seen` lạc quan ngay khi mở (DL-F06-02).
**Decision:** Khi tap ảnh "Đã nhận", `HistoryScreen` cập nhật ngay
`seen=true` cho item đó trong state (lạc quan) **trước** khi
`SeenService.markSeen` hoàn tất, nhất quán với `FeedScreen`. Lỗi
mạng của `markSeen` (idempotent — DL-F07-02) không revert UI, lần
refresh kế tiếp sẽ đồng bộ lại từ server.
**Consequence:** UX nhất quán giữa Feed và History; không thêm
trạng thái loading riêng cho thao tác phụ này. Việc này không tạo
endpoint/logic seen mới (vẫn nằm trong ranh giới DL-F08-08).

---

## DL-F08-10 — Trích `_cursor_filter` nội bộ trong `history_service`

**Date:** 2026-06-22
**Context:** Cả `get_sent` và `get_received` đều cần cùng một mệnh
đề lọc `(created_at, id)` "cũ hơn cursor" theo thứ tự DESC, dựa trên
`_decode_cursor` tái dùng từ `feed_service` (DL-F08-04).
**Decision:** Gom logic dựng filter cursor thành helper nội bộ
`_cursor_filter(cursor)` trong `history_service` để hai hàm dùng
chung (DRY), thay vì lặp lại biểu thức `or_/and_` ở mỗi hàm.
`_cursor_filter` raise `InvalidCursorError` (qua `_decode_cursor`)
nên hành vi lỗi cursor không đổi.
**Consequence:** Giảm trùng lặp trong F08; vẫn giữ nguyên định dạng
cursor và lỗi `INVALID_CURSOR` chung với feed. Không ảnh hưởng API.
