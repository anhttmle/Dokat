# F12 — Standalone Infrastructure — Decision Log

## DL-F12-01: Giữ nguyên column `firebase_uid`

**Quyết định:** Không rename column `firebase_uid` thành `auth_uid`.

**Lý do:** Trong JWT mode, `device_id` được lưu vào cột `firebase_uid`
(đây chỉ là string column). Tránh migration DB không cần thiết. Toàn bộ
routers đọc `request.state.firebase_uid` không cần thay đổi.

---

## DL-F12-02: JWT library — PyJWT thay vì python-jose

**Quyết định:** Dùng `PyJWT` không phải `python-jose`.

**Lý do:** `PyJWT` nhẹ hơn, maintained tốt hơn, không cần
`cryptography` transitive dep cho HS256. `python-jose` có CVE lịch sử.

---

## DL-F12-03: Middleware inject cùng field `firebase_uid`

**Quyết định:** Trong JWT mode, middleware vẫn set
`request.state.firebase_uid = jwt_sub`.

**Lý do:** Toàn bộ 10+ router và service đọc `request.state.firebase_uid`.
Thay đổi field name sẽ cần sửa tất cả các nơi. Giữ nguyên field name
là surgical change tối thiểu.

---

## DL-F12-04: MinIO — không thêm SDK riêng

**Quyết định:** Dùng boto3 với `endpoint_url=MINIO_ENDPOINT_URL`.

**Lý do:** MinIO tương thích 100% S3 API. boto3 đã có sẵn. Không cần
thêm `minio` Python package.

---

## DL-F12-05: CDN URL trong MinIO mode

**Quyết định:** `cdn_url = {MINIO_ENDPOINT_URL}/{S3_BUCKET}/{object_key}`

**Lý do:** MinIO có thể serve file trực tiếp qua HTTP. Trong dev, client
có thể truy cập MinIO URL trực tiếp. Production có thể đặt nginx trước.

---

## DL-F12-06: OAuth không có trong JWT MVP

**Quyết định:** `POST /auth/token` chỉ hỗ trợ anonymous (device_id),
không hỗ trợ OAuth trong JWT mode.

**Lý do:** YAGNI — OAuth trong JWT mode cần thêm redirect flow phức tạp.
MVP standalone chỉ cần anonymous session để test.

---

## DL-F12-07: flutter_secure_storage cho JWT

**Quyết định:** Flutter lưu JWT vào `flutter_secure_storage` với key
`jwt_token`.

**Lý do:** Keychain (iOS) / Keystore (Android) là nơi an toàn nhất cho
token. SharedPreferences/Hive không mã hoá.

---

## DL-F12-08: AuthNotifier JWT bootstrap trước Firebase

**Ngày:** 2026-07-01

**Context:** Docker compose chạy `AUTH_MODE=jwt` nhưng Flutter web vẫn
sign-in Firebase anonymous và gửi Firebase ID token → backend trả 401,
tất cả màn hình hiện DioException.

**Quyết định:**
1. `AuthNotifier._init()` gọi `signInWithDeviceId` trước; nếu thành công
   (backend JWT mode) → `AuthAuthenticated(isGuest: true)` không cần Firebase.
2. Nếu `/auth/token` trả 404 (Firebase backend) → fall through Firebase flow.
3. `api_client` interceptor ưu tiên JWT trong storage hơn Firebase token.

**Consequence:** Client tự detect backend mode, không cần `--dart-define`.
