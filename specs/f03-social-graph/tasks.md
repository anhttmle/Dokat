# F03 — Social Graph — Kết Bạn qua QR — Tasks

**Refs:** `requirements.md`, `design.md`
**Stack:** FastAPI (Python) + React Native (TypeScript)
**Convention:** viết test TRƯỚC implementation trong mỗi task.

---

## 1. Bootstrap F03 structure + test runner

_Tiên quyết cho tất cả task còn lại. Không có dependency ngoài._

### 1.1 Scaffold backend F03 modules

**Làm:**
- Tạo các file skeleton (pass/empty body) trong backend:
  ```
  app/
    models/friendship.py
    schemas/friend.py
    routers/friends.py
    services/otp_service.py
    services/friend_service.py
    services/notification_service.py
    core/redis.py
  tests/
    test_service_otp.py
    test_service_friend.py
    test_router_friends.py
  ```
- Đăng ký `friends` router vào `app/main.py` với prefix
  `/friends`.
- Thêm dependencies mới vào `requirements.txt`:
  `redis[hiredis]`, `fakeredis`, `firebase-admin`.

**Verify:** `make test` collect đúng 3 file test mới, 0 lỗi
import.

**Refs:** Design §4.1

---

### 1.2 Scaffold client F03 modules

**Làm:**
- Tạo các file skeleton trong React Native project:
  ```
  src/
    screens/
      AddFriendScreen.tsx
      QRScannerScreen.tsx
      FriendListScreen.tsx
    components/
      RemoveFriendDialog.tsx
    services/
      SocialService.ts
    stores/
      useFriendStore.ts
    __tests__/social/
      SocialService.test.ts
      useFriendStore.test.ts
      AddFriendScreen.test.tsx
      QRScannerScreen.test.tsx
      FriendListScreen.test.tsx
      RemoveFriendDialog.test.tsx
  ```
- Mock `SocialService` trong `__mocks__/`.

**Verify:** `npx jest --listTests` liệt kê đúng 6 file test
mới. `npx tsc --noEmit` không báo lỗi type.

**Refs:** Design §4.2

---

## 2. Migration: bảng `friendships` + cột `fcm_token`

_Độc lập. Cần chạy trước mọi integration test backend._

### 2.1 Alembic migration

**Test trước:**
```python
# tests/migrations/test_friendships_migration.py
def test_friendships_table_exists(db_engine):
    inspector = inspect(db_engine)
    assert "friendships" in inspector.get_table_names()

def test_friendships_columns(db_engine):
    cols = {c["name"] for c in
            inspect(db_engine).get_columns("friendships")}
    assert cols >= {"id", "user_id_a", "user_id_b", "created_at"}

def test_friendships_fk_to_users(db_engine):
    fks = inspect(db_engine).get_foreign_keys("friendships")
    referred = {fk["referred_table"] for fk in fks}
    assert referred == {"users"}

def test_friendships_unique_constraint_exists(db_engine):
    uqs = inspect(db_engine).get_unique_constraints("friendships")
    names = {uq["name"] for uq in uqs}
    assert "friendships_unique_pair" in names

def test_users_table_has_fcm_token(db_engine):
    cols = {c["name"] for c in
            inspect(db_engine).get_columns("users")}
    assert "fcm_token" in cols
```

**Làm:**
- Tạo Alembic revision:
  - `ALTER TABLE users ADD COLUMN fcm_token TEXT`.
  - `CREATE TABLE friendships` với CHECK constraint
    `user_id_a < user_id_b` và UNIQUE `(user_id_a, user_id_b)`.
  - `CREATE INDEX idx_friendships_a ON friendships(user_id_a)`.
  - `CREATE INDEX idx_friendships_b ON friendships(user_id_b)`.
- Thêm SQLAlchemy model `Friendship` vào
  `app/models/friendship.py`.

**Verify:** `make migrate` thành công. 5 test migration pass.

**Refs:** Design §2.1, §2.2; FR-8

---

## 3. Redis client + OTPService

_Phụ thuộc Task 1. Độc lập với DB._

### 3.1 Redis client singleton

**Test trước:**
```python
# tests/test_service_otp.py
import fakeredis.aioredis as fakeredis

@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()
```

**Làm:**
- `app/core/redis.py`: hàm `get_redis_client()` trả
  `redis.asyncio.Redis` từ `settings.REDIS_URL`.
- Thêm `REDIS_URL` vào `app/core/config.py`.
- Test fixture dùng `fakeredis` — không cần Redis thật.

**Verify:** `from app.core.redis import get_redis_client`
import thành công trong môi trường test.

**Refs:** Design §2.3

---

### 3.2 OTPService: generate & consume

**Test trước:**
```python
# tests/test_service_otp.py
async def test_generate_returns_valid_token(redis_client):
    svc = OTPService(redis_client)
    result = await svc.generate(initiator_id="user-a")
    assert UUID(result.token)          # valid UUID v4
    ttl = await redis_client.ttl(f"qr_otp:{result.token}")
    assert 298 <= ttl <= 300

async def test_consume_valid_otp(redis_client):
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id="user-a")
    payload = await svc.consume(gen.token)
    assert payload.initiator_id == "user-a"

async def test_consume_marks_used(redis_client):
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id="user-a")
    await svc.consume(gen.token)
    with pytest.raises(OTPUsedError):
        await svc.consume(gen.token)

async def test_consume_expired_otp(redis_client):
    svc = OTPService(redis_client)
    with pytest.raises(OTPExpiredError):
        await svc.consume("non-existent-token")

async def test_consume_race_condition(redis_client):
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id="user-a")
    results = await asyncio.gather(
        svc.consume(gen.token),
        svc.consume(gen.token),
        return_exceptions=True,
    )
    ok = sum(1 for r in results if not isinstance(r, Exception))
    assert ok == 1
```

**Làm:**
- `app/services/otp_service.py`:
  - `OTPService.generate(initiator_id)` → lưu Redis key
    `qr_otp:{uuid4}` TTL 300s, trả `GenerateQRResponse`.
  - `OTPService.consume(token)` → thực thi Lua script atomic
    (xem Design §2.3); ném `OTPExpiredError` hoặc
    `OTPUsedError`.
- Định nghĩa custom exceptions trong cùng file.

**Verify:** 5 test trên pass với `fakeredis`.

**Refs:** Design §2.3, §3.1; FR-1, FR-2; AC-F03-4, AC-F03-6

---

## 4. Backend: `POST /friends/qr/generate`

_Phụ thuộc Task 3._

**Test trước:**
```python
# tests/test_router_friends.py
def test_generate_qr_success(client, mock_otp_service):
    mock_otp_service.generate.return_value = GenerateQRResponse(
        token="abc", deep_link="https://...", expires_at=...
    )
    resp = client.post("/friends/qr/generate",
                       headers=auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert "deep_link" in body
    assert "expires_at" in body

def test_generate_qr_unauthenticated(client):
    resp = client.post("/friends/qr/generate")
    assert resp.status_code == 401
```

**Làm:**
- `app/routers/friends.py`:
  - `POST /friends/qr/generate` gọi `OTPService.generate()`
    và trả `GenerateQRResponse`.
- Pydantic schemas `GenerateQRResponse` trong
  `app/schemas/friend.py`.

**Verify:** 2 router test pass.

**Refs:** Design §3.1; FR-1, FR-2; AC-F03-1

---

## 5. FriendService — tạo friendship + `POST /friends/qr/scan`

_Phụ thuộc Task 2 (migration) và Task 3 (OTPService)._

### 5.1 FriendService unit tests + implementation

**Test trước:**
```python
# tests/test_service_friend.py
async def test_create_friendship_success(db_session, user_a, user_b):
    svc = FriendService(db_session)
    friendship = await svc.create(
        initiator_id=user_a.id, scanner_id=user_b.id
    )
    assert friendship.id is not None
    a, b = min(user_a.id, user_b.id), max(user_a.id, user_b.id)
    assert friendship.user_id_a == a
    assert friendship.user_id_b == b

async def test_create_self_friend(db_session, user_a):
    with pytest.raises(SelfFriendError):
        await FriendService(db_session).create(user_a.id, user_a.id)

async def test_create_already_friends(db_session, user_a, user_b):
    svc = FriendService(db_session)
    await svc.create(user_a.id, user_b.id)
    with pytest.raises(AlreadyFriendsError):
        await svc.create(user_a.id, user_b.id)

async def test_create_initiator_at_limit(db_session, user_a,
                                         twenty_friends_of_a):
    user_c = make_user()
    with pytest.raises(FriendLimitError) as exc:
        await FriendService(db_session).create(user_a.id, user_c.id)
    assert exc.value.side == "initiator"

async def test_create_scanner_at_limit(db_session, user_a,
                                        user_b_with_20_friends):
    with pytest.raises(FriendLimitError) as exc:
        await FriendService(db_session).create(user_a.id,
                                               user_b_with_20_friends.id)
    assert exc.value.side == "scanner"
```

**Làm:**
- `app/services/friend_service.py`:
  - `FriendService.create(initiator_id, scanner_id)`:
    1. Raise `SelfFriendError` nếu `initiator_id == scanner_id`.
    2. Tính canonical pair `(a, b) = (min, max)`.
    3. Đếm bạn của cả hai; raise `FriendLimitError(side)` nếu
       ai đó >= 20.
    4. Insert `friendships`; raise `AlreadyFriendsError` nếu
       unique constraint violation.
- Định nghĩa `SelfFriendError`, `AlreadyFriendsError`,
  `FriendLimitError` trong cùng file.

**Verify:** 5 unit test pass.

**Refs:** Design §2.2, §5.1; FR-4, FR-5, FR-6, FR-7, FR-8;
AC-F03-2, AC-F03-5, AC-F03-7, AC-F03-8

---

### 5.2 Router `POST /friends/qr/scan`

**Test trước:**
```python
# tests/test_router_friends.py
def test_scan_qr_success(client, mock_otp_svc, mock_friend_svc,
                          mock_notification_svc):
    # mocks trả về hợp lệ
    resp = client.post("/friends/qr/scan",
                       json={"token": "valid-token"},
                       headers=auth_header())
    assert resp.status_code == 201
    assert "friendship_id" in resp.json()
    assert "friend" in resp.json()

def test_scan_qr_expired(client, mock_otp_svc):
    mock_otp_svc.consume.side_effect = OTPExpiredError()
    resp = client.post("/friends/qr/scan",
                       json={"token": "expired"},
                       headers=auth_header())
    assert resp.status_code == 410
    assert resp.json()["error_code"] == "QR_EXPIRED"

def test_scan_qr_used(client, mock_otp_svc):
    mock_otp_svc.consume.side_effect = OTPUsedError()
    resp = client.post("/friends/qr/scan",
                       json={"token": "used"},
                       headers=auth_header())
    assert resp.status_code == 410
    assert resp.json()["error_code"] == "QR_USED"

def test_scan_qr_self(client, mock_otp_svc, mock_friend_svc):
    mock_friend_svc.create.side_effect = SelfFriendError()
    resp = client.post("/friends/qr/scan",
                       json={"token": "self"},
                       headers=auth_header())
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "SELF_FRIEND"

def test_scan_qr_already_friends(client, mock_otp_svc,
                                  mock_friend_svc):
    mock_friend_svc.create.side_effect = AlreadyFriendsError()
    resp = client.post("/friends/qr/scan",
                       json={"token": "dup"},
                       headers=auth_header())
    assert resp.status_code == 409

def test_scan_qr_limit_initiator(client, mock_otp_svc,
                                  mock_friend_svc):
    mock_friend_svc.create.side_effect = FriendLimitError("initiator")
    resp = client.post("/friends/qr/scan",
                       json={"token": "x"},
                       headers=auth_header())
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "FRIEND_LIMIT_INITIATOR"

def test_scan_qr_limit_scanner(client, mock_otp_svc,
                                mock_friend_svc):
    mock_friend_svc.create.side_effect = FriendLimitError("scanner")
    resp = client.post("/friends/qr/scan",
                       json={"token": "x"},
                       headers=auth_header())
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "FRIEND_LIMIT_SCANNER"
```

**Làm:**
- `app/routers/friends.py`:
  - `POST /friends/qr/scan`:
    1. `OTPService.consume(token)` → lấy `initiator_id`.
    2. `FriendService.create(initiator_id, scanner_id)`.
    3. `NotificationService.send_new_friend(initiator_id,
       scanner_display_name)` (best-effort, không await lỗi).
    4. Trả `ScanQRResponse` 201.
  - Exception handler map đúng exception → HTTP code +
    `error_code`.
- Pydantic schemas `ScanQRRequest`, `ScanQRResponse`.

**Verify:** 7 router test pass.

**Refs:** Design §3.2, §5.1; FR-4, FR-5, FR-6, FR-7;
AC-F03-2, AC-F03-4, AC-F03-5, AC-F03-6, AC-F03-7, AC-F03-8

---

## 6. FriendService — danh sách bạn + `GET /friends`

_Phụ thuộc Task 2._

### 6.1 FriendService list unit tests + implementation

**Test trước:**
```python
# tests/test_service_friend.py
async def test_list_friends_empty(db_session, user_a):
    result = await FriendService(db_session).list_friends(user_a.id)
    assert result == []

async def test_list_friends_bidirectional(db_session, user_a,
                                          user_b):
    await FriendService(db_session).create(user_a.id, user_b.id)
    from_a = await FriendService(db_session).list_friends(user_a.id)
    from_b = await FriendService(db_session).list_friends(user_b.id)
    assert len(from_a) == 1
    assert from_a[0]["user_id"] == str(user_b.id)
    assert len(from_b) == 1
    assert from_b[0]["user_id"] == str(user_a.id)
```

**Làm:**
- `FriendService.list_friends(user_id)` → thực thi query
  CASE/WHERE hai chiều (Design §2.2), JOIN bảng `users` để
  lấy `display_name`, `avatar_url`. Trả danh sách dict.

**Verify:** 2 test pass.

**Refs:** Design §2.2, §3.3; FR-9; AC-F03-2

---

### 6.2 Router `GET /friends`

**Test trước:**
```python
# tests/test_router_friends.py
def test_get_friends_list(client, mock_friend_svc):
    mock_friend_svc.list_friends.return_value = [
        {"user_id": "u1", "display_name": "Bob",
         "avatar_url": None,
         "friendship_created_at": "2026-06-21T00:00:00Z"},
    ]
    resp = client.get("/friends", headers=auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["friends"][0]["user_id"] == "u1"

def test_get_friends_unauthenticated(client):
    resp = client.get("/friends")
    assert resp.status_code == 401
```

**Làm:**
- `GET /friends` gọi `FriendService.list_friends()` và trả
  `FriendListResponse`.
- Schemas `FriendItem`, `FriendListResponse`.

**Verify:** 2 test pass.

**Refs:** Design §3.3; FR-9

---

## 7. FriendService — xóa bạn + `DELETE /friends/{friend_user_id}`

_Phụ thuộc Task 2._

### 7.1 FriendService delete unit tests + implementation

**Test trước:**
```python
# tests/test_service_friend.py
async def test_delete_friendship(db_session, user_a, user_b):
    svc = FriendService(db_session)
    await svc.create(user_a.id, user_b.id)
    await svc.delete(user_a.id, user_b.id)
    friends = await svc.list_friends(user_a.id)
    assert friends == []

async def test_delete_friendship_idempotent(db_session, user_a,
                                             user_b):
    svc = FriendService(db_session)
    # Xóa khi chưa có friendship — không raise exception
    await svc.delete(user_a.id, user_b.id)
```

**Làm:**
- `FriendService.delete(user_id, friend_id)`:
  - Tính canonical pair.
  - DELETE row; không raise nếu không tìm thấy (idempotent).

**Verify:** 2 test pass.

**Refs:** Design §2.2, §3.4; FR-11; AC-F03-9

---

### 7.2 Router `DELETE /friends/{friend_user_id}`

**Test trước:**
```python
# tests/test_router_friends.py
def test_delete_friend_success(client, mock_friend_svc):
    resp = client.delete("/friends/some-uuid",
                         headers=auth_header())
    assert resp.status_code == 204

def test_delete_friend_user_not_found(client, mock_friend_svc,
                                       mock_user_svc):
    mock_user_svc.get_by_id.return_value = None
    resp = client.delete("/friends/nonexistent",
                         headers=auth_header())
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"

def test_delete_friend_unauthenticated(client):
    resp = client.delete("/friends/some-uuid")
    assert resp.status_code == 401
```

**Làm:**
- `DELETE /friends/{friend_user_id}`:
  - Validate `friend_user_id` tồn tại trong `users`; nếu không
    → `UserNotFoundError` → 404.
  - Gọi `FriendService.delete()`.
  - Trả 204 No Content.

**Verify:** 3 test pass.

**Refs:** Design §3.4; FR-11; AC-F03-9, AC-F03-10

---

## 8. NotificationService + `PUT /profile/me/fcm-token`

_Phụ thuộc Task 2. Độc lập với Task 5._

### 8.1 NotificationService + FCM token endpoint

**Test trước:**
```python
# tests/test_service_friend.py
async def test_notification_sent_on_scan(client, mock_otp_svc,
                                          mock_friend_svc,
                                          mock_notification_svc):
    client.post("/friends/qr/scan", json={"token": "t"},
                headers=auth_header())
    mock_notification_svc.send_new_friend.assert_called_once()

async def test_notification_failure_does_not_rollback(
        client, mock_otp_svc, mock_friend_svc, mock_notification_svc):
    mock_notification_svc.send_new_friend.side_effect = Exception()
    resp = client.post("/friends/qr/scan", json={"token": "t"},
                       headers=auth_header())
    assert resp.status_code == 201  # friendship vẫn tạo

# tests/test_router_friends.py
def test_put_fcm_token_success(client):
    resp = client.put("/profile/me/fcm-token",
                      json={"fcm_token": "abc123"},
                      headers=auth_header())
    assert resp.status_code == 204

def test_put_fcm_token_empty(client):
    resp = client.put("/profile/me/fcm-token",
                      json={"fcm_token": ""},
                      headers=auth_header())
    assert resp.status_code == 422
```

**Làm:**
- `app/services/notification_service.py`:
  - `NotificationService.send_new_friend(initiator_id,
    scanner_name)`: đọc `users.fcm_token` của initiator; gọi
    Firebase Admin `messaging.send()`; log warning nếu lỗi,
    không raise.
- `app/routers/profile.py` (hoặc router mới):
  - `PUT /profile/me/fcm-token`: update `users.fcm_token`.
- Schema `FCMTokenRequest`.

**Verify:** 4 test pass.

**Refs:** Design §3.5, §5.1; FR-4

---

## 9. Client — SocialService + useFriendStore + AddFriendScreen

_Phụ thuộc Task 1.2. Không phụ thuộc backend thật (mock API)._

### 9.1 SocialService + useFriendStore

**Test trước:**
```typescript
// __tests__/social/SocialService.test.ts
it('generateQR calls POST /friends/qr/generate', async () => {
  mockAxios.post.mockResolvedValue({
    data: { token: 't', deep_link: 'https://...', expires_at: '...' }
  });
  const res = await SocialService.generateQR();
  expect(res.token).toBe('t');
});

it('scanQR calls POST /friends/qr/scan', async () => {
  mockAxios.post.mockResolvedValue({ data: { friendship_id: 'f1' } });
  const res = await SocialService.scanQR('token-abc');
  expect(res.friendship_id).toBe('f1');
});

// __tests__/social/useFriendStore.test.ts
it('removeFriend removes friend from list optimistically', () => {
  const { result } = renderHook(() => useFriendStore());
  act(() => result.current.setFriends([{ user_id: 'u1', ... }]));
  act(() => result.current.removeFriend('u1'));
  expect(result.current.friends).toHaveLength(0);
});
```

**Làm:**
- `SocialService.ts`: `generateQR()`, `scanQR(token)`,
  `getFriends()`, `removeFriend(friendUserId)`,
  `updateFCMToken(token)` — wrap axios với Authorization
  header.
- `useFriendStore.ts`: state `friends[]`, `loading`,
  `error`; actions `setFriends`, `addFriend`, `removeFriend`.

**Verify:** 3 test trên pass.

**Refs:** Design §4.2; FR-9

---

### 9.2 AddFriendScreen

**Test trước:**
```typescript
// __tests__/social/AddFriendScreen.test.tsx
it('calls generateQR on mount and renders QR', async () => {
  mockSocialService.generateQR.mockResolvedValue({
    token: 't', deep_link: 'https://x.com/...', expires_at: futureISO
  });
  const { findByTestId } = render(<AddFriendScreen />);
  await findByTestId('qr-image');
  expect(mockSocialService.generateQR).toHaveBeenCalledTimes(1);
});

it('calls generateQR again when countdown reaches zero', async () => {
  jest.useFakeTimers();
  // expires_at = now + 1s
  mockSocialService.generateQR.mockResolvedValue({
    token: 't', deep_link: '...', expires_at: nowPlusOneSecond
  });
  render(<AddFriendScreen />);
  act(() => jest.advanceTimersByTime(1100));
  await waitFor(() =>
    expect(mockSocialService.generateQR).toHaveBeenCalledTimes(2)
  );
});
```

**Làm:**
- `AddFriendScreen.tsx`:
  - Gọi `SocialService.generateQR()` khi mount.
  - Render QR image từ `deep_link` (dùng thư viện
    `react-native-qrcode-svg`).
  - Countdown timer tính từ `expires_at`; khi về 0 → gọi lại
    `generateQR()` tự động (auto-refresh).
  - Hiển thị loading spinner khi đang tải QR mới.

**Verify:** 2 test pass.

**Refs:** Design §4.2; FR-1, FR-2, FR-3; AC-F03-1, AC-F03-3

---

## 10. Client — QRScannerScreen + FriendListScreen + RemoveFriendDialog

_Phụ thuộc Task 9.1 (SocialService + useFriendStore)._

### 10.1 QRScannerScreen

**Test trước:**
```typescript
// __tests__/social/QRScannerScreen.test.tsx
it('extracts token from deep link and calls scanQR', async () => {
  mockSocialService.scanQR.mockResolvedValue({
    friendship_id: 'f1', friend: { display_name: 'Bob', ... }
  });
  const { getByTestId } = render(<QRScannerScreen />);
  act(() => getByTestId('qr-scanner')
      .props.onRead('https://petapp.example.com/add-friend?token=abc'));
  await waitFor(() =>
    expect(mockSocialService.scanQR).toHaveBeenCalledWith('abc')
  );
});

it('shows toast on QR_EXPIRED error', async () => {
  mockSocialService.scanQR.mockRejectedValue(
    { response: { data: { error_code: 'QR_EXPIRED' } } }
  );
  // verify toast shown
});
```

**Làm:**
- `QRScannerScreen.tsx`:
  - Mở camera (Expo Camera / Vision Camera).
  - Khi scan được URL → extract `token` query param.
  - Gọi `SocialService.scanQR(token)` → navigate kết quả.
  - Xử lý lỗi: map `error_code` → toast message (Design §5.2).

**Verify:** 2 test pass.

**Refs:** Design §4.2; FR-4; AC-F03-2, AC-F03-4, AC-F03-6,
AC-F03-7, AC-F03-8

---

### 10.2 FriendListScreen + RemoveFriendDialog

**Test trước:**
```typescript
// __tests__/social/FriendListScreen.test.tsx
it('fetches and renders friend list on mount', async () => {
  mockSocialService.getFriends.mockResolvedValue({
    friends: [{ user_id: 'u1', display_name: 'Alice', ... }],
    total: 1
  });
  const { findByText } = render(<FriendListScreen />);
  await findByText('Alice');
});

// __tests__/social/RemoveFriendDialog.test.tsx
it('calls removeFriend on confirm', async () => {
  const onConfirm = jest.fn();
  const { getByText } = render(
    <RemoveFriendDialog friendName="Alice" onConfirm={onConfirm}
                        onCancel={jest.fn()} visible />
  );
  fireEvent.press(getByText('Xóa'));
  expect(onConfirm).toHaveBeenCalled();
});

it('does NOT call removeFriend on cancel', () => {
  const onConfirm = jest.fn();
  const onCancel = jest.fn();
  const { getByText } = render(
    <RemoveFriendDialog friendName="Alice" onConfirm={onConfirm}
                        onCancel={onCancel} visible />
  );
  fireEvent.press(getByText('Hủy'));
  expect(onConfirm).not.toHaveBeenCalled();
  expect(onCancel).toHaveBeenCalled();
});
```

**Làm:**
- `FriendListScreen.tsx`:
  - Gọi `SocialService.getFriends()` khi mount; render danh
    sách.
  - Nút "Xóa bạn" → hiển thị `RemoveFriendDialog`.
  - Sau confirm → `SocialService.removeFriend()` + optimistic
    update `useFriendStore.removeFriend()`.
- `RemoveFriendDialog.tsx`:
  - Modal với `friendName`, callback `onConfirm`, `onCancel`.
  - Không gọi API trực tiếp — chỉ trigger callback.

**Verify:** 3 test pass.

**Refs:** Design §4.2; FR-9, FR-10, FR-11;
AC-F03-9, AC-F03-10
