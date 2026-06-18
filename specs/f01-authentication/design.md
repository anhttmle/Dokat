# F01 — Authentication & Guest Mode — Design

**Version:** 1.0.0
**Date:** 2026-06-18
**Status:** Draft

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────┐
│          React Native Client             │
│                                          │
│  ┌────────────┐    ┌──────────────────┐  │
│  │ AuthService│    │LocalStorageService│  │
│  └─────┬──────┘    └──────────────────┘  │
│        │ Firebase Auth SDK               │
└────────┼─────────────────────────────────┘
         │ Firebase ID Token (in every request)
         ▼
┌──────────────────────────────────────────┐
│          Firebase Auth (Google)          │
│  - Anonymous Auth                        │
│  - OAuth: Apple / Google / Facebook      │
└──────────────────────────────────────────┘
         │ Verify via Admin SDK
         ▼
┌──────────────────────────────────────────┐
│           FastAPI Backend                │
│                                          │
│  AuthMiddleware (verify every request)   │
│  ┌──────────────┐  ┌────────────────┐    │
│  │  AuthRouter  │  │  UserService   │    │
│  └──────────────┘  └────────────────┘    │
│                                          │
│           PostgreSQL                     │
│  ┌──────────────┐  ┌────────────────┐    │
│  │    users     │  │ user_providers │    │
│  └──────────────┘  └────────────────┘    │
└──────────────────────────────────────────┘
```

### Luồng chính

**Guest Mode (lần đầu mở app):**
1. Client gọi `Firebase.signInAnonymously()` → nhận `firebase_uid` + Firebase ID Token.
2. Client lưu `firebase_uid` vào local storage (AsyncStorage).
3. Client gọi `POST /auth/session` với Firebase ID Token.
4. Backend verify token → tạo bản ghi `users` nếu chưa tồn tại → trả về user profile + flag `force_link_required`.
5. Client điều hướng vào Feed.

**OAuth Linking:**
1. Client gọi Firebase SDK để link provider (Apple/Google/Facebook) vào anonymous credential hiện tại.
2. Firebase giữ nguyên `firebase_uid`, cập nhật danh sách provider.
3. Client lấy Firebase ID Token mới → gọi `POST /auth/link`.
4. Backend cập nhật bảng `user_providers`, giữ nguyên `user.id`.

**Restore session (mở lại app):**
1. Client đọc `firebase_uid` từ local storage.
2. Firebase SDK tự refresh ID Token (nếu còn credential).
3. Client gọi `POST /auth/session` → backend confirm session còn hợp lệ.

---

## 2. Data Models / Schema

### 2.1 Bảng `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid    VARCHAR(128) UNIQUE NOT NULL,
    is_anonymous    BOOLEAN NOT NULL DEFAULT TRUE,
    display_name    VARCHAR(100),
    avatar_url      TEXT,
    force_link_at   TIMESTAMPTZ,        -- set = created_at + 7 days
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_firebase_uid ON users(firebase_uid);
```

- `firebase_uid`: primary key của Firebase, dùng để tra cứu nhanh.
- `is_anonymous`: `TRUE` nếu chưa liên kết bất kỳ OAuth provider nào.
- `force_link_at`: thời điểm bắt buộc liên kết; bằng `created_at + 7 days` và không đổi sau khi set.
- Bản ghi được tạo ngay khi Guest mở app lần đầu (không chờ link OAuth).

### 2.2 Bảng `user_providers`

```sql
CREATE TYPE oauth_provider AS ENUM ('apple', 'google', 'facebook');

CREATE TABLE user_providers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      oauth_provider NOT NULL,
    provider_uid  VARCHAR(256) NOT NULL,
    linked_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (provider, provider_uid)
);

CREATE INDEX idx_user_providers_user_id ON user_providers(user_id);
CREATE INDEX idx_user_providers_lookup
    ON user_providers(provider, provider_uid);
```

- Một user có thể liên kết nhiều provider (Apple + Google + Facebook).
- `UNIQUE (provider, provider_uid)` ngăn cùng một tài khoản OAuth gắn vào hai user khác nhau.

---

## 3. API Contracts

Token xác thực: `Authorization: Bearer <Firebase ID Token>` ở **tất cả** endpoint.

### 3.1 `POST /auth/session`

Được gọi mỗi khi app khởi động (guest hoặc đã linked). Backend tự tạo user nếu chưa tồn tại.

**Request:**
```
POST /auth/session
Authorization: Bearer <Firebase ID Token>
```
_(Không có body — mọi thông tin cần thiết nằm trong token.)_

**Response 200:**
```json
{
  "user_id": "uuid-...",
  "firebase_uid": "firebaseUID123",
  "is_anonymous": true,
  "force_link_required": false,
  "force_link_at": "2026-06-25T00:00:00Z",
  "providers": []
}
```

| Field | Mô tả |
|---|---|
| `force_link_required` | `true` nếu `now() >= force_link_at` và `is_anonymous = true` |
| `force_link_at` | Client dùng để đếm ngược hoặc kiểm tra offline |
| `providers` | Danh sách provider đã liên kết: `["google"]`, `[]`, v.v. |

**Response 401:** Token không hợp lệ hoặc đã hết hạn.

---

### 3.2 `POST /auth/link`

Được gọi sau khi client link OAuth provider thành công trên Firebase.

**Request:**
```
POST /auth/link
Authorization: Bearer <Firebase ID Token (sau khi link)>
```
_(Không có body — Firebase ID Token đã chứa thông tin provider mới.)_

**Response 200:**
```json
{
  "user_id": "uuid-...",
  "is_anonymous": false,
  "providers": ["google"]
}
```

**Response 200 (merge case):** Khi provider đã từng liên kết với một user cũ (đã xóa app), backend merge dữ liệu và trả về account được giữ lại.

```json
{
  "user_id": "uuid-existing",
  "is_anonymous": false,
  "providers": ["google"],
  "merged": true
}
```

**Response 401:** Token không hợp lệ.
**Response 422:** Token không chứa thông tin provider sau khi link.

---

### 3.3 Auth Middleware (áp dụng toàn bộ router)

Không phải endpoint riêng — là FastAPI dependency được inject vào tất cả router.

**Logic:**
1. Đọc header `Authorization: Bearer <token>`.
2. Gọi `firebase_admin.auth.verify_id_token(token)`.
3. Nếu hợp lệ → inject `firebase_uid` vào request context.
4. Nếu không hợp lệ → raise `HTTPException(401)`.

---

## 4. Component Breakdown

### 4.1 Client (React Native)

| Component | Trách nhiệm |
|---|---|
| `AuthService` | Wrap Firebase Auth SDK; gọi `signInAnonymously`, `linkWithProvider`, `currentUser`, `getIdToken` |
| `LocalStorageService` | Đọc/ghi `firebase_uid` và `force_link_at` vào AsyncStorage |
| `AuthGuard` | HOC/hook; kiểm tra `force_link_required` khi app resume, chặn màn hình nếu cần force-link |
| `LinkAccountSheet` | Bottom sheet hiển thị 3 nút (Apple / Google / Facebook) khi trigger hành động cần auth |
| `ForceLink Screen` | Full-screen, không dismissible; hiển thị khi `force_link_required = true` |
| `useAuthStore` | Zustand store giữ trạng thái: `{ user, isAnonymous, forceLinkRequired }` |

**Trigger prompt liên kết:**
- Gửi ảnh (F05): gọi `AuthGuard.requireLinked()` trước khi mở camera.
- Thêm bạn (F03): gọi `AuthGuard.requireLinked()` trước khi gửi friend request.

### 4.2 Backend (FastAPI)

| Component | Trách nhiệm |
|---|---|
| `app/middleware/auth.py` | `FirebaseAuthMiddleware`: verify token mọi request, inject `firebase_uid` |
| `app/routers/auth.py` | Định nghĩa `POST /auth/session` và `POST /auth/link` |
| `app/services/auth_service.py` | Business logic: upsert user, tính `force_link_required`, xử lý merge |
| `app/services/user_service.py` | CRUD cho bảng `users` và `user_providers` |
| `app/models/user.py` | SQLAlchemy ORM models |
| `app/schemas/auth.py` | Pydantic request/response schemas |
| `app/core/firebase.py` | Khởi tạo Firebase Admin SDK singleton |

---

## 5. Error Handling Strategy

### 5.1 Phân loại lỗi

| Tình huống | HTTP Status | Error Code | Hành động client |
|---|---|---|---|
| Token thiếu / sai format | 401 | `AUTH_TOKEN_MISSING` | Gọi lại `getIdToken()`, retry |
| Token hết hạn | 401 | `AUTH_TOKEN_EXPIRED` | Firebase tự refresh, retry |
| Token bị revoke | 401 | `AUTH_TOKEN_REVOKED` | Đăng xuất, xóa local storage |
| Provider đã linked ở user khác | 200 | — | Merge tự động, trả về account merged |
| Provider không có trong token | 422 | `AUTH_PROVIDER_NOT_FOUND` | Thông báo lỗi cho user |
| Firebase Admin SDK lỗi | 503 | `AUTH_SERVICE_UNAVAILABLE` | Hiển thị lỗi hệ thống, retry sau |

### 5.2 Không expose stack trace

- Production: chỉ trả `{ "error": "<error_code>", "message": "<user-friendly message>" }`.
- Log chi tiết vào structured logger (không log token hay PII).

### 5.3 Retry strategy (client)

- 401 `EXPIRED` → Firebase SDK tự refresh → retry 1 lần.
- 503 → retry với exponential backoff (1s, 2s, 4s), tối đa 3 lần.
- Các lỗi khác → không retry, hiển thị thông báo.

---

## 6. Test Strategy

### 6.1 Unit Tests (Backend)

| Test | Kiểm tra |
|---|---|
| `test_upsert_new_guest_user` | `POST /auth/session` với token mới → tạo bản ghi `users`, `is_anonymous=True` |
| `test_restore_existing_session` | `POST /auth/session` với `firebase_uid` đã tồn tại → không tạo bản ghi mới |
| `test_force_link_flag_before_7_days` | User tạo 6 ngày trước → `force_link_required = False` |
| `test_force_link_flag_at_7_days` | User tạo đúng 7 ngày trước → `force_link_required = True` |
| `test_link_new_provider` | `POST /auth/link` → cập nhật `user_providers`, `is_anonymous = False` |
| `test_link_multi_provider` | Link Apple rồi link Google → `providers = ["apple", "google"]` |
| `test_link_merge_existing_account` | Provider đã tồn tại ở user B → merge, response có `merged = True` |
| `test_invalid_token_returns_401` | Token sai → `401 AUTH_TOKEN_MISSING` |
| `test_expired_token_returns_401` | Token expired → `401 AUTH_TOKEN_EXPIRED` |

### 6.2 Integration Tests (Backend)

- Dùng `firebase_admin` với Firebase Emulator trong CI.
- Test full flow: tạo anonymous token → `POST /auth/session` → `POST /auth/link` → verify DB state.

### 6.3 E2E / Acceptance Tests (Client + Backend)

Map trực tiếp từ AC trong requirements:

| AC | Test scenario |
|---|---|
| AC-F01-1 | App lần đầu → `signInAnonymously` thành công → vào Feed |
| AC-F01-2 | Guest nhấn "Gửi ảnh" → bottom sheet xuất hiện → không submit |
| AC-F01-3 | Guest nhấn "Thêm bạn" → prompt xuất hiện → không tạo friendship |
| AC-F01-4 | User tạo 7 ngày → `force_link_required = true` → full-screen, không dismiss được |
| AC-F01-5 | Guest có 5 bạn + 3 ảnh → link Google → data còn nguyên |
| AC-F01-6 | Background app rồi foreground → session tự khôi phục |
| AC-F01-7 | Guest chưa link → xóa cài lại → `firebase_uid` mới, không khôi phục dữ liệu |
| AC-F01-8 | Đã link Google → xóa cài lại → link lại Google → đúng account + data |

### 6.4 Coverage target

- Backend business logic (`auth_service.py`, `user_service.py`): ≥ 80%.
- Middleware `FirebaseAuthMiddleware`: 100% (các nhánh valid/invalid/expired/revoked).
