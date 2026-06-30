# F12 — Standalone Infrastructure — Requirements

## Goal

Hệ thống Dokat SHALL chạy hoàn toàn standalone (không cần Firebase,
AWS S3, hoặc CloudFront CDN) bằng JWT tự cấp và MinIO, đồng thời vẫn
hỗ trợ Firebase/S3/CDN khi được cấu hình (backward compatible).

## Users / Actors

- **Developer / DevOps:** triển khai hệ thống trên VPS hoặc local mà
  không cần tài khoản Google/AWS.
- **App User (Guest):** đăng nhập bằng `device_id`, nhận JWT, dùng app
  bình thường.
- **App User (Linked):** tiếp tục dùng Firebase Auth nếu backend được
  cấu hình `AUTH_MODE=firebase`.

## Functional Requirements

1. Hệ thống SHALL khởi động và serve API đầy đủ khi `AUTH_MODE=jwt` mà
   không có `FIREBASE_CREDENTIALS_JSON`.
2. Hệ thống SHALL expose endpoint `POST /auth/token` nhận `device_id`
   và trả `access_token` (JWT), `user_id`, `is_anonymous=true`.
3. Backend SHALL issue JWT với `sub=device_id`, ký bằng `JWT_SECRET_KEY`,
   có hạn `JWT_EXPIRE_DAYS` ngày.
4. `AuthMiddleware` SHALL verify JWT khi `AUTH_MODE=jwt` và inject
   `request.state.firebase_uid = sub` (giữ tên field để toàn bộ router
   không cần thay đổi).
5. `AuthMiddleware` SHALL tiếp tục verify Firebase ID Token khi
   `AUTH_MODE=firebase` (hành vi hiện tại không thay đổi).
6. Hệ thống SHALL upload/serve file qua MinIO khi
   `STORAGE_BACKEND=minio`, dùng `MINIO_ENDPOINT_URL` làm endpoint.
7. `build_cdn_url()` SHALL trả URL dạng
   `{MINIO_ENDPOINT_URL}/{S3_BUCKET}/{object_key}` khi
   `STORAGE_BACKEND=minio`.
8. FCM push notification SHALL bị skip silently (log warning) khi
   Firebase không được khởi tạo; không raise exception.
9. Flutter client SHALL authenticate bằng JWT lưu trong
   `flutter_secure_storage` khi Firebase user là null.
10. Flutter `NotificationService.registerToken()` SHALL skip FCM
    registration nếu gặp exception (Firebase không available).

## Non-goals

- Không tích hợp OAuth (Google/Apple/Facebook) trong JWT mode — MVP.
- Không implement full self-hosted push notification server.
- Không thay đổi DB schema (column `firebase_uid` giữ nguyên, dùng cho
  cả JWT mode với value là `device_id`).
- Không thêm refresh token mechanism trong MVP.
- Không migrate dữ liệu production hiện tại.

## Technical Constraints

- boto3 tương thích với MinIO qua `endpoint_url` — không cần thêm SDK.
- `firebase_uid` column (String 128) đủ chứa `device_id` UUID.
- JWT library: `PyJWT` (nhẹ, không có transitive dep phức tạp).
- Flutter secure storage: `flutter_secure_storage` (đã có sẵn trong
  nhiều app Flutter).
- Backward compatible: khi `AUTH_MODE=firebase`, hành vi không đổi gì.

## Acceptance Criteria

**AC-F12-1:** Khởi động standalone
Given `.env` có `AUTH_MODE=jwt`, `JWT_SECRET_KEY=test`, và không có
  `FIREBASE_CREDENTIALS_JSON`
When `uvicorn app.main:app` được chạy
Then server khởi động thành công, `/health` trả `{"status": "ok"}`
  và không có Firebase-related exception trong log.

**AC-F12-2:** JWT issue
Given server đang chạy ở `AUTH_MODE=jwt`
When client gọi `POST /auth/token` với body `{"device_id": "abc-123"}`
Then response 200 với `access_token` (JWT string), `user_id` (UUID),
  `is_anonymous: true`.

**AC-F12-3:** JWT auth middleware
Given server ở `AUTH_MODE=jwt` và client có `access_token` hợp lệ
When client gọi `GET /profile/me` với header
  `Authorization: Bearer <access_token>`
Then middleware verify JWT thành công, `request.state.firebase_uid`
  được set bằng `device_id`, router trả profile bình thường.

**AC-F12-4:** MinIO presigned URL
Given `STORAGE_BACKEND=minio`, `MINIO_ENDPOINT_URL=http://localhost:9000`
When client gọi `POST /posts/upload-url`
Then `upload_url` bắt đầu bằng `http://localhost:9000`,
  `cdn_url` bắt đầu bằng `http://localhost:9000`.

**AC-F12-5:** FCM graceful skip
Given Firebase không được khởi tạo (không có credentials)
When backend gọi `notification_service.send_new_photo()`
Then không có exception raise; log warning xuất hiện; request
  gốc hoàn thành bình thường.

**AC-F12-6:** Flutter JWT fallback
Given Flutter app không có Firebase session (Firebase không cấu hình)
  và `flutter_secure_storage` có key `jwt_token`
When bất kỳ API request nào được gửi
Then header `Authorization: Bearer <jwt_token>` được đính kèm.
