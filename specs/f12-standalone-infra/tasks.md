# F12 — Standalone Infrastructure — Tasks

## 1. Bootstrap

### 1.1 Xác nhận test runner + thêm PyJWT dependency

**Mục tiêu:** `make test` vẫn pass 100% sau khi thêm PyJWT vào
`requirements.txt`. 0 test mới.

**Test trước:** chạy `make test` xem baseline pass.

**Reference AC:** FR-1 (system starts without Firebase)

---

## 2. JWT Auth — Backend

### 2.1 `app/core/jwt_auth.py` — JWT issue và verify

**Mục tiêu:** Module JWT thuần với `create_token`, `verify_token`,
`JWTAuthError`.

**Test trước:** `tests/test_core_jwt_auth.py` — test create, verify,
expired token, wrong secret.

**Reference AC:** AC-F12-2, AC-F12-3

---

### 2.2 `app/middleware/auth.py` — dual-mode (JWT + Firebase)

**Mục tiêu:** `AuthMiddleware` branch theo `AUTH_MODE`; inject
`request.state.firebase_uid` trong cả hai mode.

**Test trước:** `tests/test_middleware_auth.py` — thêm test JWT mode
(mock `jwt_auth.verify_token`), giữ nguyên Firebase test.

**Reference AC:** AC-F12-1, AC-F12-3

---

### 2.3 `app/routers/auth_jwt.py` — `POST /auth/token`

**Mục tiêu:** Router mới; chỉ đăng ký khi `AUTH_MODE=jwt`; upsert user
và trả JWT.

**Test trước:** `tests/test_router_auth_jwt.py` — happy path, empty
device_id, idempotent (gọi 2 lần same device_id trả same user_id).

**Reference AC:** AC-F12-2

---

## 3. MinIO Storage — Backend

### 3.1 `app/services/storage_service.py` — MinIO endpoint support

**Mục tiêu:** `_get_s3_client()` thêm `endpoint_url` khi MinIO mode;
`build_cdn_url()` trả MinIO URL.

**Test trước:** `tests/test_service_storage.py` — thêm test MinIO mode
(mock boto3 client với `endpoint_url`).

**Reference AC:** AC-F12-4

---

### 3.2 `docker-compose.yml` + `backend/.env.example`

**Mục tiêu:** `docker compose up` khởi động PostgreSQL + Redis + MinIO
+ Backend đầy đủ. `.env.example` document tất cả vars.

**Test trước:** manual smoke test — `curl http://localhost:8000/health`
sau `docker compose up`.

**Reference AC:** AC-F12-1, AC-F12-4

---

## 4. Firebase Optional

### 4.1 `app/core/firebase.py` — graceful init

**Mục tiêu:** `get_firebase_app()` trả `None` thay vì crash khi không
có credentials. `is_firebase_available()` helper.

**Test trước:** unit test `get_firebase_app()` với env rỗng → return
`None` không raise.

**Reference AC:** AC-F12-1, AC-F12-5

---

### 4.2 `app/services/notification_service.py` + `app/main.py` — skip FCM

**Mục tiêu:** `_send_push()` check `is_firebase_available()` trước khi
gọi FCM. `main.py` init Firebase trong try/except.

**Test trước:** `tests/test_notification_service.py` — thêm test
`_send_push` khi Firebase unavailable → không raise, log warning.

**Reference AC:** AC-F12-5

---

## 5. Flutter JWT Mode

### 5.1 `client/lib/core/api_client.dart` — JWT fallback interceptor

**Mục tiêu:** Interceptor đọc `jwt_token` từ `flutter_secure_storage`
khi `FirebaseAuth.currentUser == null`.

**Test trước:** `test/core/api_client_test.dart` — mock
`FlutterSecureStorage`, verify header `Authorization: Bearer <jwt>`
khi no Firebase user.

**Reference AC:** AC-F12-6

---

### 5.2 `client/lib/features/auth/data/auth_service.dart` — JWT sign-in

**Mục tiêu:** `signInWithDeviceId(dio)` — generate/read device_id, POST
/auth/token, lưu JWT vào secure storage.

**Test trước:** `test/features/auth/auth_service_test.dart` — mock Dio,
verify JWT lưu vào storage.

**Reference AC:** AC-F12-2, AC-F12-6

---

### 5.3 `client/lib/features/notifications/data/notification_service.dart`
— graceful FCM skip

**Mục tiêu:** `registerToken()` bọc trong try/catch, không crash khi
Firebase không available.

**Test trước:** `test/features/notifications/notification_service_test.dart`
— mock `FirebaseMessaging` throw exception, verify không propagate.

**Reference AC:** AC-F12-6 (partial — FR-10)

---

## 6. Integration Smoke Test

### 6.1 Verify `docker compose up` → full standalone flow

**Mục tiêu:** Script/makefile target xác nhận:
1. `/health` trả OK
2. `POST /auth/token` trả JWT
3. Dùng JWT gọi `GET /profile/me` thành công

**Test trước:** `tests/integration/test_standalone_flow.py` — không cần
Firebase emulator; chỉ dùng JWT + MinIO mock.

**Reference AC:** AC-F12-1, AC-F12-2, AC-F12-3, AC-F12-4, AC-F12-5
