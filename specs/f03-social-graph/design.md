# F03 — Social Graph — Kết Bạn qua QR — Design

**Version:** 1.0.0
**Date:** 2026-06-21
**Status:** Draft

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     React Native Client                      │
│                                                              │
│  ┌─────────────────────┐   ┌───────────────────────────────┐ │
│  │  AddFriendScreen    │   │     FriendListScreen          │ │
│  │  (QR + Countdown)   │   │  (list + remove dialog)       │ │
│  └─────────┬───────────┘   └───────────────┬───────────────┘ │
│            │                               │                 │
│  ┌─────────▼───────────────────────────────▼───────────────┐ │
│  │              useFriendStore (Zustand)                   │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                 │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │              SocialService (API calls)                  │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │ Firebase ID Token (mọi request)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  AuthMiddleware (inject firebase_uid → user_id)             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   FriendRouter                       │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │   OTPService          │   FriendService               │   │
│  │   (Redis CRUD)        │   (PostgreSQL CRUD)           │   │
│  └──────────────┬────────┴───────────────┬──────────────┘   │
│                 │                         │                  │
│  ┌──────────────▼──────┐  ┌──────────────▼──────────────┐   │
│  │  NotificationService │  │  PostgreSQL                 │   │
│  │  (Firebase FCM)      │  │  users | friendships        │   │
│  └──────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────-┘
                           │
          ┌────────────────┴──────────────────┐
          │                                   │
          ▼                                   ▼
┌──────────────────────┐         ┌────────────────────────┐
│   Redis              │         │   Firebase FCM         │
│   qr_otp:{token}     │         │   (push notification)  │
│   TTL 300 s          │         └────────────────────────┘
└──────────────────────┘
```

### 1.1 Luồng chính — Tạo QR (Initiator)

1. Initiator mở màn hình "Thêm bạn".
2. `AddFriendScreen` mount → gọi `POST /friends/qr/generate`.
3. Backend (`OTPService`) tạo token ngẫu nhiên (UUID v4), lưu
   vào Redis `qr_otp:{token}` với payload JSON và TTL 300 s.
4. Backend trả về `{ token, deep_link, expires_at }`.
5. Client render QR từ `deep_link` và bắt đầu countdown từ
   `expires_at`.
6. Khi countdown về 0, client tự gọi lại
   `POST /friends/qr/generate` để lấy QR mới (auto-refresh).

### 1.2 Luồng chính — Scan QR (Scanner)

1. Scanner mở camera trong app, scan QR của Initiator.
2. Camera đọc được `deep_link`
   (`https://<domain>/add-friend?token=<TOKEN>`).
3. App extract `token` từ URL và gọi `POST /friends/qr/scan`
   với `{ token }`.
4. Backend (`OTPService`) thực thi Lua script atomic trên Redis:
   - Key không tồn tại → `QR_EXPIRED`.
   - Key tồn tại, `used: true` → `QR_USED`.
   - Key tồn tại, `used: false` → mark `used: true`, tiếp tục.
5. `FriendService` validate:
   - Scanner không phải Initiator (self-friend check).
   - Chưa là bạn bè (duplicate check).
   - Cả hai chưa vượt giới hạn 20 bạn.
6. Nếu hợp lệ → insert row vào `friendships`.
7. `NotificationService` gửi FCM push tới Initiator
   ("User B đã kết bạn với bạn").
8. Backend trả `201 Created` cho Scanner.

### 1.3 Luồng chính — Xóa bạn

1. User A nhấn "Xóa bạn" trên `FriendListScreen`.
2. Client hiển thị `RemoveFriendDialog` confirmation.
3. Người dùng xác nhận → gọi
   `DELETE /friends/{friend_user_id}`.
4. Backend xóa row trong `friendships` (cả hai chiều xử lý
   bằng canonical ordering).
5. Client cập nhật `useFriendStore`, loại bỏ bạn khỏi danh
   sách.

---

## 2. Data Models / Schema

### 2.1 Bảng `users` (kế thừa F01/F02, thêm cột)

Thêm cột `fcm_token` để gửi push notification:

```sql
ALTER TABLE users
    ADD COLUMN fcm_token TEXT;
```

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `firebase_uid` | VARCHAR(128) UNIQUE | |
| `display_name` | VARCHAR(100) | Nullable |
| `avatar_url` | TEXT | Nullable |
| `fcm_token` | TEXT | Nullable; cập nhật mỗi lần app mở |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### 2.2 Bảng `friendships` (mới)

```sql
CREATE TABLE friendships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id_a   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_id_b   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT friendships_canonical_order
        CHECK (user_id_a < user_id_b),
    CONSTRAINT friendships_unique_pair
        UNIQUE (user_id_a, user_id_b)
);

CREATE INDEX idx_friendships_a ON friendships(user_id_a);
CREATE INDEX idx_friendships_b ON friendships(user_id_b);
```

**Canonical ordering:** Mỗi cặp bạn bè chỉ có đúng 1 row.
`user_id_a` luôn nhỏ hơn `user_id_b` (so sánh UUID string).
Trước khi insert/lookup, backend luôn sort:
`(min(uid1, uid2), max(uid1, uid2))`.

**Query danh sách bạn của user X:**

```sql
SELECT
    CASE
        WHEN user_id_a = :uid THEN user_id_b
        ELSE user_id_a
    END AS friend_id,
    created_at
FROM friendships
WHERE user_id_a = :uid OR user_id_b = :uid
ORDER BY created_at DESC;
```

**Query đếm bạn (kiểm tra giới hạn 20):**

```sql
SELECT COUNT(*) FROM friendships
WHERE user_id_a = :uid OR user_id_b = :uid;
```

### 2.3 Redis — OTP Entry

**Key:** `qr_otp:{token}` (token là UUID v4)

**Value (JSON):**

```json
{
  "initiator_id": "<user UUID>",
  "created_at": "2026-06-21T04:00:00Z",
  "used": false
}
```

**TTL:** 300 giây (5 phút), set khi tạo.

**Lua script — atomic consume:**

```lua
local raw = redis.call('GET', KEYS[1])
if not raw then return {nil, 'expired'} end
local data = cjson.decode(raw)
if data.used then return {nil, 'used'} end
data.used = true
local ttl = redis.call('TTL', KEYS[1])
if ttl > 0 then
    redis.call('SET', KEYS[1], cjson.encode(data), 'EX', ttl)
end
return {raw, 'ok'}
```

Script đảm bảo check-and-mark là atomic, tránh race condition
khi hai Scanner cùng dùng một OTP.

---

## 3. API Contracts

Tất cả endpoint yêu cầu header:
```
Authorization: Bearer <Firebase ID Token>
```

`AuthMiddleware` inject `current_user: User` (lấy từ DB qua
`firebase_uid`).

---

### 3.1 `POST /friends/qr/generate`

Tạo QR OTP mới cho người dùng hiện tại.

**Request:** Không có body.

**Response 200 OK:**

```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "deep_link": "https://petapp.example.com/add-friend?token=550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-06-21T04:05:00Z"
}
```

**Ghi chú:**
- Endpoint tạo OTP mới mỗi lần gọi (không check OTP cũ còn
  hạn). OTP cũ tự expire theo TTL Redis.
- Client dùng `expires_at` để render countdown timer.
- QR được render từ `deep_link` hoàn toàn phía client
  (không cần server render ảnh).

**Response lỗi:**

| HTTP | Error code | Mô tả |
|---|---|---|
| 401 | `UNAUTHORIZED` | Thiếu hoặc sai token |
| 500 | `INTERNAL_ERROR` | Redis unavailable |

---

### 3.2 `POST /friends/qr/scan`

Scanner gọi sau khi mở deep link và extract token.

**Request body:**

```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response 201 Created:**

```json
{
  "friendship_id": "7f3e9b10-...",
  "friend": {
    "user_id": "<initiator UUID>",
    "display_name": "Nguyễn Văn A",
    "avatar_url": "https://cdn.example.com/avatars/abc.jpg"
  },
  "created_at": "2026-06-21T04:02:30Z"
}
```

**Response lỗi:**

| HTTP | Error code | Mô tả |
|---|---|---|
| 401 | `UNAUTHORIZED` | Thiếu hoặc sai token |
| 409 | `ALREADY_FRIENDS` | Hai người đã là bạn bè |
| 410 | `QR_EXPIRED` | OTP không tồn tại trong Redis (hết hạn) |
| 410 | `QR_USED` | OTP đã được dùng trước đó |
| 422 | `SELF_FRIEND` | Scanner scan QR của chính mình |
| 422 | `FRIEND_LIMIT_INITIATOR` | Initiator đã đủ 20 bạn |
| 422 | `FRIEND_LIMIT_SCANNER` | Scanner đã đủ 20 bạn |
| 500 | `INTERNAL_ERROR` | Redis/DB unavailable |

**Xử lý bất đồng bộ FCM:** Notification gửi FCM sau khi
insert `friendships` thành công. Nếu FCM thất bại → log
warning, không rollback friendship (best-effort delivery).

---

### 3.3 `GET /friends`

Lấy danh sách bạn bè của người dùng hiện tại.

**Request:** Không có body/query param.

**Response 200 OK:**

```json
{
  "friends": [
    {
      "user_id": "abc123",
      "display_name": "Trần Thị B",
      "avatar_url": "https://cdn.example.com/avatars/b.jpg",
      "friendship_created_at": "2026-06-20T10:00:00Z"
    }
  ],
  "total": 1
}
```

**Ghi chú:**
- Sắp xếp theo `friendship_created_at DESC` (bạn mới nhất
  lên đầu).
- `avatar_url` có thể `null` nếu người dùng chưa upload ảnh.

**Response lỗi:**

| HTTP | Error code | Mô tả |
|---|---|---|
| 401 | `UNAUTHORIZED` | Thiếu hoặc sai token |

---

### 3.4 `DELETE /friends/{friend_user_id}`

Xóa friendship với một người dùng cụ thể.

**Path param:** `friend_user_id` — UUID của người bạn muốn
xóa.

**Request:** Không có body.

**Response 204 No Content.**

**Ghi chú:**
- Backend tính canonical pair `(min, max)` rồi DELETE.
- Nếu không tìm thấy row → vẫn trả `204` (idempotent).
- Confirmation dialog xử lý hoàn toàn phía client; backend
  không có bước confirm.

**Response lỗi:**

| HTTP | Error code | Mô tả |
|---|---|---|
| 401 | `UNAUTHORIZED` | Thiếu hoặc sai token |
| 404 | `USER_NOT_FOUND` | `friend_user_id` không tồn tại |

---

### 3.5 `PUT /profile/me/fcm-token`

Đăng ký / cập nhật FCM device token. Được gọi khi app khởi
động hoặc FCM token được refresh.

**Request body:**

```json
{
  "fcm_token": "cXV4eW..."
}
```

**Response 204 No Content.**

**Response lỗi:**

| HTTP | Error code | Mô tả |
|---|---|---|
| 401 | `UNAUTHORIZED` | Thiếu hoặc sai token |
| 422 | `VALIDATION_ERROR` | `fcm_token` rỗng |

---

## 4. Component Breakdown

### 4.1 Backend

```
backend/
├── app/
│   ├── models/
│   │   └── friendship.py      # SQLAlchemy model Friendship
│   ├── schemas/
│   │   └── friend.py          # Pydantic schemas
│   │       # GenerateQRResponse, ScanQRRequest, ScanQRResponse,
│   │       # FriendItem, FriendListResponse, FCMTokenRequest
│   ├── routers/
│   │   └── friends.py         # FriendRouter (4 endpoints)
│   ├── services/
│   │   ├── otp_service.py     # OTPService: generate, consume (Lua)
│   │   ├── friend_service.py  # FriendService: create, list, delete
│   │   └── notification_service.py  # FCM push (best-effort)
│   └── core/
│       └── redis.py           # Redis client singleton (aioredis)
├── alembic/versions/
│   └── xxxx_create_friendships_and_fcm_token.py
└── tests/
    ├── test_router_friends.py
    ├── test_service_otp.py
    └── test_service_friend.py
```

**Trách nhiệm từng service:**

| Service | Trách nhiệm |
|---|---|
| `OTPService` | Tạo token, lưu Redis, Lua consume script |
| `FriendService` | Validate rules, insert/delete friendships, đếm bạn |
| `NotificationService` | Gọi Firebase Admin SDK gửi FCM (best-effort) |

### 4.2 React Native Client

```
src/
├── screens/
│   ├── AddFriendScreen.tsx    # QR display + countdown auto-refresh
│   ├── FriendListScreen.tsx   # Danh sách bạn + remove action
│   └── QRScannerScreen.tsx    # Camera scanner, extract token
├── components/
│   └── RemoveFriendDialog.tsx # Confirmation dialog
├── services/
│   └── SocialService.ts       # API calls (generateQR, scan, list, remove)
└── stores/
    └── useFriendStore.ts      # Zustand: friends[], loading, error
```

**Trách nhiệm từng component:**

| Component | Trách nhiệm |
|---|---|
| `AddFriendScreen` | Gọi `generateQR` khi mount và khi countdown = 0; render QR image từ deep_link; hiển thị countdown |
| `QRScannerScreen` | Mở camera; decode QR URL; extract token; gọi `scan`; navigate to result |
| `FriendListScreen` | Gọi `GET /friends`; render danh sách; trigger `RemoveFriendDialog` |
| `RemoveFriendDialog` | Modal xác nhận; gọi `DELETE` khi confirm; không làm gì khi cancel |
| `SocialService` | Wrap axios/fetch; gắn Authorization header |
| `useFriendStore` | Cache danh sách bạn; optimistic update khi xóa |

**Deep link handling:**
Universal link `https://<domain>/add-friend?token=<TOKEN>`
được intercept bởi React Native linking handler.
- Nếu app đang foreground → navigate đến `QRScannerScreen`
  (hoặc xử lý inline nếu scanner đang mở).
- Nếu app ở background/closed → app mở và navigate tới màn
  hình xử lý scan.

---

## 5. Error Handling Strategy

### 5.1 Backend

**Nguyên tắc:**
- Service layer ném custom exception (`FriendshipError`,
  `OTPError`).
- Router layer catch và map sang HTTP response.
- Không expose stack trace; chỉ trả `error_code` + `message`.

**Error response format (chuẩn hóa):**

```json
{
  "error_code": "QR_EXPIRED",
  "message": "QR code đã hết hạn. Vui lòng yêu cầu người kia làm mới QR."
}
```

**Bảng mapping exception → HTTP:**

| Exception | HTTP | Error code | Message hiển thị |
|---|---|---|---|
| `OTPExpiredError` | 410 | `QR_EXPIRED` | "QR đã hết hạn" |
| `OTPUsedError` | 410 | `QR_USED` | "QR đã được sử dụng" |
| `SelfFriendError` | 422 | `SELF_FRIEND` | "Không thể kết bạn với chính mình" |
| `AlreadyFriendsError` | 409 | `ALREADY_FRIENDS` | "Hai người đã là bạn bè" |
| `FriendLimitError(side)` | 422 | `FRIEND_LIMIT_INITIATOR` / `FRIEND_LIMIT_SCANNER` | "Đã đạt giới hạn 20 bạn bè" |
| `UserNotFoundError` | 404 | `USER_NOT_FOUND` | "Người dùng không tồn tại" |

**Redis unavailable:** Nếu Redis down, `POST /friends/qr/generate`
và `POST /friends/qr/scan` trả 503.

**FCM failure:** Log warning, trả 201 bình thường (friendship
đã được tạo). Không retry trong MVP.

### 5.2 Client

| Tình huống | Xử lý phía client |
|---|---|
| `QR_EXPIRED` / `QR_USED` | Toast "QR không hợp lệ", hướng dẫn scan QR mới |
| `ALREADY_FRIENDS` | Toast "Hai bạn đã là bạn bè rồi" |
| `SELF_FRIEND` | Toast "Đây là QR của chính bạn" |
| `FRIEND_LIMIT_*` | Toast với tên người bị giới hạn (parse error_code) |
| Network timeout | Retry tối đa 1 lần; nếu vẫn lỗi → toast chung |
| Scan thất bại toàn bộ | Không thay đổi `useFriendStore` |

---

## 6. Test Strategy

### 6.1 Backend Unit Tests

**`test_service_otp.py`** — `OTPService`:

| Test case | Mô tả |
|---|---|
| `test_generate_returns_valid_token` | Token là UUID hợp lệ, TTL được set 300s |
| `test_consume_valid_otp` | Trả initiator_id, mark used=true |
| `test_consume_expired_otp` | Key không tồn tại → `OTPExpiredError` |
| `test_consume_used_otp` | Key có used=true → `OTPUsedError` |
| `test_consume_race_condition` | Hai goroutine consume cùng lúc → chỉ một thành công |

**`test_service_friend.py`** — `FriendService`:

| Test case | Mô tả |
|---|---|
| `test_create_friendship_success` | Insert row, canonical order đúng |
| `test_create_self_friend` | → `SelfFriendError` |
| `test_create_already_friends` | → `AlreadyFriendsError` |
| `test_create_initiator_at_limit` | Initiator có 20 bạn → `FriendLimitError` |
| `test_create_scanner_at_limit` | Scanner có 20 bạn → `FriendLimitError` |
| `test_list_friends_empty` | Trả list rỗng |
| `test_list_friends_bidirectional` | Cả hai chiều query được |
| `test_delete_friendship` | Row bị xóa, idempotent khi gọi 2 lần |

### 6.2 Backend API Tests (router level)

**`test_router_friends.py`** — mock service layer:

| Test case | Mô tả |
|---|---|
| `test_generate_qr_success` | 200, response có token + deep_link + expires_at |
| `test_generate_qr_unauthenticated` | 401 |
| `test_scan_qr_success` | 201, response có friendship + friend info |
| `test_scan_qr_expired` | 410, error_code = QR_EXPIRED |
| `test_scan_qr_used` | 410, error_code = QR_USED |
| `test_scan_qr_self` | 422, error_code = SELF_FRIEND |
| `test_scan_qr_already_friends` | 409 |
| `test_scan_qr_limit_initiator` | 422, error_code = FRIEND_LIMIT_INITIATOR |
| `test_scan_qr_limit_scanner` | 422, error_code = FRIEND_LIMIT_SCANNER |
| `test_get_friends_list` | 200, trả đúng danh sách |
| `test_delete_friend_success` | 204 |
| `test_delete_friend_not_found` | 204 (idempotent) |
| `test_put_fcm_token` | 204 |

### 6.3 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F03-1 | `test_generate_qr_success` + client render QR |
| AC-F03-2 | `test_scan_qr_success` |
| AC-F03-3 | Client-side (countdown = 0 → re-call generate) |
| AC-F03-4 | `test_scan_qr_expired` |
| AC-F03-5 | `test_scan_qr_limit_initiator` |
| AC-F03-6 | `test_scan_qr_used` + `test_consume_race_condition` |
| AC-F03-7 | `test_scan_qr_self` |
| AC-F03-8 | `test_scan_qr_already_friends` |
| AC-F03-9 | `test_delete_friend_success` |
| AC-F03-10 | Client-side (dialog cancel, không gọi DELETE) |

### 6.4 Ghi chú Test

- Unit test `OTPService` dùng `fakeredis` (không cần Redis thật).
- Unit test `FriendService` dùng SQLite in-memory hoặc
  PostgreSQL test DB.
- Router test mock service layer bằng `pytest-mock`.
- Không cần integration test E2E cho MVP; AC-F03-2 được cover
  bằng unit + router test kết hợp.
