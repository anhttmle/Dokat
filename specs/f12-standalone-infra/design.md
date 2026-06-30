# F12 — Standalone Infrastructure — Design

## 1. Architecture Overview

Hệ thống có hai mode vận hành, chọn qua env vars:

```
AUTH_MODE=jwt  (default)          AUTH_MODE=firebase
STORAGE_BACKEND=minio (default)   STORAGE_BACKEND=s3

Client ──Bearer JWT──► AuthMiddleware (JWT verify)
                           │
                           ▼ request.state.firebase_uid = device_id
                       Routers / Services (không đổi)
                           │
                   ┌───────┴────────┐
                   ▼                ▼
              PostgreSQL       MinIO (S3-compat)
              (không đổi)      endpoint_url injected
```

Client Flutter đọc JWT từ `flutter_secure_storage` khi không có Firebase
session. Khi Firebase được cấu hình, flow hiện tại giữ nguyên.

## 2. Data Models / Schema

**Không thay đổi schema DB.** Column `firebase_uid` (String 128) được
tái dùng để lưu `device_id` trong JWT mode. (DL-F12-01)

## 3. API Contracts

### POST /auth/token (mới — JWT mode only)

Endpoint này chỉ available khi `AUTH_MODE=jwt`. Trong Firebase mode,
endpoint không được đăng ký.

**Request body:**
```json
{ "device_id": "550e8400-e29b-41d4-a716-446655440000" }
```

**Response 200:**
```json
{
  "access_token": "<JWT string>",
  "user_id": "<UUID>",
  "is_anonymous": true
}
```

**Response 422:** nếu `device_id` rỗng.

**Note:** `/auth/token` nằm trong `_PUBLIC_PATHS` của middleware (không
cần token để gọi).

### Existing endpoints (không thay đổi contract)

Tất cả endpoint hiện tại giữ nguyên request/response shape. Middleware
inject `request.state.firebase_uid` với value là `device_id` (JWT mode)
hoặc Firebase UID (firebase mode).

## 4. Component Breakdown

### Backend

**`app/core/config.py`** — thêm fields:
- `auth_mode: Literal["firebase", "jwt"] = "jwt"`
- `jwt_secret_key: str = ""`
- `jwt_algorithm: str = "HS256"`
- `jwt_expire_days: int = 30`
- `storage_backend: Literal["s3", "minio"] = "minio"`
- `minio_endpoint_url: str = "http://localhost:9000"`

**`app/core/firebase.py`** — make optional:
- `get_firebase_app()` trả `firebase_admin.App | None`
- Return `None` khi không có credentials và không raise exception
- Add `is_firebase_available() -> bool` helper

**`app/core/jwt_auth.py`** (mới):
- `create_token(sub: str) -> str` — issue JWT
- `verify_token(token: str) -> str` — trả `sub` hoặc raise `JWTAuthError`
- `class JWTAuthError(Exception)` — custom exception

**`app/middleware/auth.py`** — dual-mode:
- Class renamed: `AuthMiddleware` (thay `FirebaseAuthMiddleware`)
- `dispatch()`: check `settings.auth_mode`
  - `"jwt"` → `jwt_auth.verify_token(token)` → set `firebase_uid = sub`
  - `"firebase"` → existing Firebase verify flow
- `_PUBLIC_PATHS` += `"/auth/token"`

**`app/routers/auth_jwt.py`** (mới):
- `POST /auth/token`
- Schema input: `TokenRequest(device_id: str)`
- Schema output: `TokenResponse(access_token, user_id, is_anonymous)`
- Logic: `get_or_create_user(db, device_id)` rồi `create_token(device_id)`
- Router prefix: `/auth`, chỉ đăng ký khi `AUTH_MODE=jwt`

**`app/services/storage_service.py`** — MinIO support:
- Thêm helper `_get_s3_client()` trả `boto3.client` với
  `endpoint_url=settings.minio_endpoint_url` nếu `storage_backend=minio`
- `build_cdn_url(object_key)` trả
  `{minio_endpoint_url}/{s3_bucket}/{object_key}` nếu MinIO,
  `{cdn_base_url}/{object_key}` nếu S3

**`app/services/notification_service.py`** — graceful skip:
- `_send_push()` check `is_firebase_available()` trước khi gọi
  `firebase_admin.messaging.send()`; nếu `False` → log warning, return

**`app/main.py`** — update:
- `get_firebase_app()` gọi trong `try/except`, không crash nếu không có credentials
- Import `AuthMiddleware` thay `FirebaseAuthMiddleware`
- Đăng ký `auth_jwt_router` nếu `settings.auth_mode == "jwt"`

### Flutter Client

**`client/lib/core/api_client.dart`** — JWT fallback:
- Interceptor: nếu `firebaseAuth.currentUser == null`, đọc JWT từ
  `FlutterSecureStorage` key `"jwt_token"` và đính vào header

**`client/lib/features/auth/data/auth_service.dart`** — JWT mode:
- Thêm method `signInWithDeviceId(Dio dio)`:
  - Tạo/đọc `device_id` từ `FlutterSecureStorage` key `"device_id"`
  - Nếu chưa có: generate UUID v4
  - Gọi `POST /auth/token` với `device_id`
  - Lưu `access_token` vào `FlutterSecureStorage` key `"jwt_token"`
  - Lưu `user_id` vào key `"jwt_user_id"`

**`client/lib/features/notifications/data/notification_service.dart`**:
- Wrap toàn bộ `registerToken()` trong `try/catch` Exception
- Log warning nếu FCM không available; không rethrow

### Infra

**`docker-compose.yml`** (root):
- Services: `postgres`, `redis`, `minio`, `backend`
- MinIO: image `minio/minio`, ports `9000:9000` + `9001:9001`
- Backend env: `AUTH_MODE=jwt`, `STORAGE_BACKEND=minio`,
  `MINIO_ENDPOINT_URL=http://minio:9000`

**`backend/.env.example`** — document tất cả env vars

## 5. Error Handling Strategy

| Tình huống | HTTP | Error code |
|-----------|------|-----------|
| JWT missing | 401 | `AUTH_TOKEN_MISSING` |
| JWT expired | 401 | `AUTH_TOKEN_EXPIRED` |
| JWT invalid signature | 401 | `AUTH_TOKEN_INVALID` |
| `device_id` rỗng | 422 | FastAPI validation error |
| Firebase không có khi `AUTH_MODE=firebase` | 503 | `AUTH_SERVICE_UNAVAILABLE` |
| MinIO không reach được | boto3 exception propagate tới 500 |

## 6. Test Strategy

**Backend unit tests (mới):**
- `tests/test_core_jwt_auth.py`: `create_token`, `verify_token`,
  expired token, invalid token
- `tests/test_middleware_auth.py` (update): thêm test JWT mode bên cạnh
  Firebase mode
- `tests/test_router_auth_jwt.py`: POST /auth/token happy path, empty
  device_id
- `tests/test_service_storage.py` (update): thêm test MinIO mode (với
  `moto` mock endpoint_url)

**Flutter tests (update):**
- `test/features/auth/auth_service_test.dart`: thêm `signInWithDeviceId`
- `test/core/api_client_test.dart`: thêm JWT fallback interceptor test
