# F11 — Location & Time Metadata — Decision Log

---

## DL-F11-01 — Bảng `posts` thuộc F05; F11 chỉ đặc tả cột, không tạo migration

**Date:** 2026-06-22
**Context:** Kế hoạch tổng phác thảo F11 task "Backend schema: thêm
`latitude`/`longitude` vào bảng `posts`". Tuy nhiên thứ tự thực thi là
F04 → F11 → F05, và bảng `posts` được tạo trong **F05** (DL-F04-01).
Tại thời điểm F11 chạy, bảng `posts` chưa tồn tại nên không thể có
migration thêm cột vào nó.
**Decision:** F11 **không** tạo migration độc lập. F11 đặc tả hai cột
`latitude DECIMAL(11, 8)` / `longitude DECIMAL(12, 8)` nullable + field
optional trong body `POST /posts` như một **hợp đồng** (Design §2.3,
§3). Migration tạo bảng `posts` của F05 hiện thực hoá hai cột này.
Phần triển khai code của F11 là client `LocationService` +
`buildLocationPayload`.
**Consequence:** Tránh dangling migration đụng bảng chưa tồn tại, nhất
quán DL-F04-01. Phần persist DB + validate server được test trong
integration suite của F05, không phải F11.

---

## DL-F11-02 — Geolocation native abstract sau interface, tích hợp lib sau

**Date:** 2026-06-22
**Context:** `package.json` chưa có thư viện geolocation
(`@react-native-community/geolocation`, `expo-location`...). Cần test
được logic xin quyền + lấy toạ độ mà không phụ thuộc native module
(tiền lệ **DL-F04-03**, **DL-F03-11**).
**Decision:** `LocationService` gọi qua `_geolocationBackend`
(abstraction injectable/mockable) với `requestPermission()` và
`getCurrentPosition()`. Stub no-op cho tới khi tích hợp native lib ở
task triển khai sau.
**Consequence:** Unit test chỉ phủ business logic (permission gate,
một-lần-đọc, fail-safe → `null`), không kiểm tra permission dialog hay
GPS thật.

---

## DL-F11-03 — Lấy toạ độ tại bước gửi (F05), không sửa CaptureService của F04

**Date:** 2026-06-22
**Context:** Requirement FR-2 nói lấy toạ độ "tại thời điểm chụp ảnh".
F04 (`CaptureService`) đã seal và là client-only không có location
(DL-F04-01). Sửa F04 để chèn location sẽ vi phạm ranh giới đã chốt.
**Decision:** `LocationService.getCurrentLocation()` được gọi ở bước
**gửi** của F05 (cách lúc chụp vài giây), không gắn toạ độ vào artifact
`CapturedPhoto` của F04. Toạ độ merge vào body `POST /posts` qua
`buildLocationPayload`.
**Consequence:** Không retro-sửa F04. Sai số thời gian giữa chụp và gửi
là không đáng kể cho MVP (chỉ lưu, không hiển thị). Nếu sau này cần độ
chính xác thời điểm chụp tuyệt đối, có thể chuyển việc lấy toạ độ vào
`CameraScreen` ở task sau.
