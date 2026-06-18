# F01 — Authentication & Guest Mode — Tasks

**Refs:** `requirements.md`, `design.md`
**Stack:** FastAPI (Python) + React Native (TypeScript)
**Convention:** viết test TRƯỚC implementation trong mỗi task.

---

## 1. Bootstrap project structure + test runner

_Tiên quyết cho tất cả task còn lại. Không có dependency ngoài._

### 1.1 Scaffold backend

**Làm:**
- Tạo cấu trúc thư mục:
  ```
  backend/
    app/
      core/          # firebase.py, config.py
      middleware/    # auth.py
      models/        # user.py
      routers/       # auth.py
      schemas/       # auth.py
      services/      # auth_service.py, user_service.py
    tests/
      conftest.py
    Makefile
    pyproject.toml   # pytest, black, ruff, mypy config
    requirements.txt
  ```
- Thêm dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`,
  `firebase-admin`, `asyncpg`, `pytest`, `pytest-asyncio`, `httpx`.
- `Makefile` có target: `make test`, `make lint`, `make run`.
- `conftest.py` có fixture mock `firebase_admin.auth.verify_id_token`
  (tránh gọi Firebase thật trong unit test).

**Verify:** `make test` chạy thành công với 0 test (collection không lỗi).

**Refs:** Technical Constraints (FR-10)

---

### 1.2 Scaffold client auth module

**Làm:**
- Tạo cấu trúc thư mục trong React Native project:
  ```
  src/
    services/
      AuthService.ts
      LocalStorageService.ts
    stores/
      useAuthStore.ts
    screens/auth/
      ForceLinkScreen.tsx
    components/auth/
      LinkAccountSheet.tsx
      AuthGuard.tsx
    __tests__/auth/
      AuthService.test.ts
      LocalStorageService.test.ts
      AuthGuard.test.tsx
  ```
- Cài `@react-native-firebase/auth`, `@react-native-async-storage/async-storage`,
  `zustand`, `jest`, `@testing-library/react-native`.
- `jest.config.js` mock `@react-native-firebase/auth` và `AsyncStorage`.

**Verify:** `npx jest --listTests` liệt kê đúng các file test.

**Refs:** Design §4.1

---

## 2. Database schema & migrations

_Độc lập với task 3–9 ở mức code, nhưng cần chạy trước integration test._

### 2.1 Migration: bảng `users`

**Làm:**
- Tạo Alembic migration tạo bảng `users` theo đúng schema trong design §2.1:
  `id`, `firebase_uid` (UNIQUE), `is_anonymous`, `display_name`,
  `avatar_url`, `force_link_at`, `created_at`, `updated_at`.
- Index `idx_users_firebase_uid`.

**Test (unit):**
- `test_users_table_exists`: sau khi apply migration,
  `SELECT 1 FROM users LIMIT 1` không lỗi.
- `test_firebase_uid_unique_constraint`: insert 2 rows cùng `firebase_uid`
  → raise `IntegrityError`.

**Refs:** Design §2.1; FR-1, FR-2

---

### 2.2 Migration: bảng `user_providers`

**Làm:**
- Tạo Alembic migration tạo ENUM `oauth_provider` và bảng `user_providers`
  theo schema trong design §2.2.
- UNIQUE constraint `(provider, provider_uid)`.
- Index `idx_user_providers_user_id`, `idx_user_providers_lookup`.

**Test (unit):**
- `test_user_providers_fk`: insert `user_providers` với `user_id` không tồn tại
  → raise `ForeignKeyViolation`.
- `test_provider_uid_unique_per_provider`: insert 2 rows cùng
  `(provider, provider_uid)` → raise `IntegrityError`.
- `test_multi_provider_same_user`: user có thể có cả `apple` lẫn `google`
  → insert thành công.

**Refs:** Design §2.2; FR-11

---

## 3. Firebase auth middleware

_Độc lập. Có thể phát triển song song với task 4–5._

### 3.1 Tests cho `FirebaseAuthMiddleware`

**Làm (chỉ viết test, chưa implement):**
Trong `tests/test_middleware_auth.py`:
- `test_valid_token_injects_firebase_uid`: request có token hợp lệ
  → `request.state.firebase_uid` được set đúng.
- `test_missing_token_returns_401`: không có header `Authorization`
  → HTTP 401, error code `AUTH_TOKEN_MISSING`.
- `test_expired_token_returns_401`: `verify_id_token` raise
  `ExpiredIdTokenError` → HTTP 401, error code `AUTH_TOKEN_EXPIRED`.
- `test_revoked_token_returns_401`: `verify_id_token` raise
  `RevokedIdTokenError` → HTTP 401, error code `AUTH_TOKEN_REVOKED`.
- `test_firebase_sdk_error_returns_503`: `verify_id_token` raise
  generic exception → HTTP 503.

**Verify:** `pytest tests/test_middleware_auth.py` → 5 tests FAIL
(đúng — chưa có implementation).

**Refs:** FR-10; Design §3.3; Design §5.1

---

### 3.2 Implement `FirebaseAuthMiddleware`

**Làm:**
- `app/core/firebase.py`: khởi tạo Firebase Admin SDK singleton
  (đọc credentials từ env `FIREBASE_CREDENTIALS_JSON`).
- `app/middleware/auth.py`: implement `FirebaseAuthMiddleware`
  as FastAPI dependency (`Depends`), xử lý đủ 4 nhánh lỗi từ task 3.1.
- Không log token hay PII trong bất kỳ nhánh nào.

**Verify:** `pytest tests/test_middleware_auth.py` → 5 tests PASS.

**Refs:** FR-10; Technical Constraints; Design §3.3, §5.2

---

## 4. `POST /auth/session` — upsert guest user

### 4.1 Tests cho session endpoint

**Làm (chỉ viết test):**
Trong `tests/test_router_auth_session.py`:
- `test_new_guest_creates_user_record`: token mới (anonymous) →
  tạo bản ghi `users` với `is_anonymous=True`, trả về `user_id`,
  `force_link_required=False`.
- `test_existing_user_no_duplicate`: gọi `POST /auth/session` 2 lần với
  cùng `firebase_uid` → chỉ có 1 bản ghi trong DB.
- `test_force_link_false_before_7_days`: `force_link_at` là ngày mai
  → `force_link_required=False`.
- `test_force_link_true_at_7_days`: `force_link_at` = now (đúng 7 ngày)
  → `force_link_required=True`.
- `test_providers_list_empty_for_guest`: guest user → `providers=[]`.
- `test_providers_list_populated_for_linked_user`: user có 1 row
  trong `user_providers` → `providers=["google"]`.

**Refs:** FR-1, FR-2, FR-6, FR-9; AC-F01-1, AC-F01-4, AC-F01-6

---

### 4.2 Implement session endpoint

**Làm:**
- `app/services/user_service.py`:
  `get_or_create_user(firebase_uid) -> User`.
- `app/services/auth_service.py`:
  `build_session_response(user) -> SessionResponse`
  (tính `force_link_required = now() >= force_link_at and is_anonymous`).
- `app/routers/auth.py`: `POST /auth/session` dùng
  `FirebaseAuthMiddleware`, gọi service, trả response theo schema.
- `app/schemas/auth.py`: `SessionResponse` Pydantic model.

**Verify:** `pytest tests/test_router_auth_session.py` → 6 tests PASS.

**Refs:** FR-1, FR-2, FR-6, FR-9; AC-F01-1, AC-F01-4, AC-F01-6

---

## 5. `POST /auth/link` — link OAuth provider + merge

### 5.1 Tests cho link endpoint

**Làm (chỉ viết test):**
Trong `tests/test_router_auth_link.py`:
- `test_link_single_provider`: token có provider `google` →
  tạo row `user_providers`, `is_anonymous=False`, `providers=["google"]`.
- `test_link_multiple_providers`: link `apple` rồi link `google` trên
  cùng user → `providers=["apple", "google"]`, không duplicate.
- `test_link_idempotent`: gọi link 2 lần cùng provider → không tạo
  duplicate, vẫn trả 200.
- `test_link_merge_existing_account`: `(provider, provider_uid)` đã tồn
  tại ở `user_providers` của user khác (user B) → response `merged=True`,
  `user_id` = user B's id, dữ liệu guest được gộp sang user B.
- `test_link_token_without_provider_returns_422`: token anonymous
  (không có provider info) → HTTP 422, `AUTH_PROVIDER_NOT_FOUND`.

**Refs:** FR-7, FR-8, FR-11; AC-F01-5, AC-F01-8

---

### 5.2 Implement link endpoint

**Làm:**
- `app/services/auth_service.py`:
  `link_provider(firebase_uid, provider, provider_uid) -> LinkResponse`.
  - Nếu `(provider, provider_uid)` chưa tồn tại → insert `user_providers`.
  - Nếu đã tồn tại ở user B → merge: reassign foreign keys
    (friends, photos) từ guest sang user B, xóa guest record.
  - Cập nhật `users.is_anonymous = False`.
- `app/routers/auth.py`: thêm `POST /auth/link`.
- `app/schemas/auth.py`: `LinkResponse` model.

**Verify:** `pytest tests/test_router_auth_link.py` → 5 tests PASS.

**Refs:** FR-7, FR-8, FR-11; AC-F01-5, AC-F01-8

---

## 6. Client: AuthService + LocalStorageService + useAuthStore

### 6.1 Tests cho client auth core

**Làm (chỉ viết test — Jest + mock Firebase):**
Trong `src/__tests__/auth/AuthService.test.ts`:
- `test_sign_in_anonymous_saves_uid_to_storage`: gọi `AuthService.init()`
  → Firebase `signInAnonymously` được gọi, `firebase_uid` được lưu vào
  AsyncStorage.
- `test_restore_session_reads_from_storage`: AsyncStorage có `firebase_uid`
  sẵn → `AuthService.init()` KHÔNG gọi `signInAnonymously` lại.
- `test_get_id_token_returns_current_token`: mock Firebase `getIdToken()`
  → `AuthService.getIdToken()` trả về đúng token.

Trong `src/__tests__/auth/LocalStorageService.test.ts`:
- `test_save_and_read_firebase_uid`: save → read → cùng giá trị.
- `test_clear_removes_uid`: clear → read → `null`.

**Refs:** FR-1, FR-2, FR-3; AC-F01-1, AC-F01-6, AC-F01-7

---

### 6.2 Implement AuthService + LocalStorageService + useAuthStore

**Làm:**
- `AuthService.ts`: `init()`, `signInAnonymous()`, `linkWithProvider(provider)`,
  `getIdToken()`, `currentUser`.
  - `init()`: đọc storage → nếu có uid và Firebase còn credential → restore;
    nếu không → `signInAnonymously()`.
  - Sau `signInAnonymously()`: gọi `POST /auth/session`, cập nhật store.
- `LocalStorageService.ts`: `saveUid()`, `getUid()`, `clearUid()`.
- `useAuthStore.ts`: Zustand store, fields: `user`, `isAnonymous`,
  `forceLinkRequired`, `providers`.

**Verify:** `npx jest src/__tests__/auth/` → 8 tests PASS.

**Refs:** FR-1, FR-2, FR-3, FR-7, FR-9; AC-F01-1, AC-F01-6, AC-F01-7, AC-F01-8

---

## 7. Client: AuthGuard + LinkAccountSheet

_Chặn hành động cần auth và hiển thị bottom sheet._

### 7.1 Tests cho AuthGuard

**Làm (chỉ viết test — Jest + @testing-library/react-native):**
Trong `src/__tests__/auth/AuthGuard.test.tsx`:
- `test_requireLinked_shows_sheet_when_anonymous`: `isAnonymous=true`,
  gọi `AuthGuard.requireLinked()` → `LinkAccountSheet` xuất hiện, action
  callback KHÔNG được gọi.
- `test_requireLinked_proceeds_when_linked`: `isAnonymous=false` →
  action callback ĐƯỢC gọi ngay, không hiển thị sheet.
- `test_sheet_calls_linkWithProvider_on_tap`: tap nút "Google" trên sheet
  → `AuthService.linkWithProvider("google")` được gọi.
- `test_sheet_dismisses_after_link_success`: link thành công → sheet đóng,
  action callback được gọi.

**Refs:** FR-5; AC-F01-2, AC-F01-3

---

### 7.2 Implement AuthGuard + LinkAccountSheet

**Làm:**
- `AuthGuard.tsx`: hook `useRequireLinked()` — trả về hàm `requireLinked(action)`:
  nếu `isAnonymous=true` → set state để hiển thị `LinkAccountSheet`,
  lưu `action` pending; nếu không → gọi `action()` trực tiếp.
- `LinkAccountSheet.tsx`: bottom sheet với 3 nút (Apple / Google / Facebook).
  Mỗi nút gọi `AuthService.linkWithProvider(provider)`.
  Sau link thành công → đóng sheet, gọi pending action.
  Không thể dismiss bằng cách kéo xuống nếu đang trong flow force-link.

**Verify:** `npx jest src/__tests__/auth/AuthGuard.test.tsx` → 4 tests PASS.

**Refs:** FR-5, FR-7; AC-F01-2, AC-F01-3

---

## 8. Client: ForceLinkScreen

_Full-screen không dismissible, hiển thị khi `force_link_required = true`._

### 8.1 Tests cho ForceLinkScreen

**Làm (chỉ viết test):**
Trong `src/__tests__/auth/ForceLinkScreen.test.tsx`:
- `test_renders_when_force_link_required`: `forceLinkRequired=true` →
  `ForceLinkScreen` được render, không thể navigate back.
- `test_not_rendered_when_not_required`: `forceLinkRequired=false` →
  screen không xuất hiện.
- `test_back_button_disabled`: back gesture / hardware back →
  không navigate ra khỏi screen.
- `test_link_success_navigates_to_feed`: link OAuth thành công →
  store cập nhật `forceLinkRequired=false` → navigate về Feed.

**Refs:** FR-6; AC-F01-4

---

### 8.2 Implement ForceLinkScreen

**Làm:**
- `ForceLinkScreen.tsx`: full-screen component với 3 nút provider,
  cùng logic gọi `AuthService.linkWithProvider()` như `LinkAccountSheet`.
- Dùng `useNavigation` để disable back (overwrite `beforeRemove` event).
- `AuthGuard.tsx`: wrap navigation stack với logic check
  `forceLinkRequired` từ store → render `ForceLinkScreen` thay vì app content.

**Verify:** `npx jest src/__tests__/auth/ForceLinkScreen.test.tsx`
→ 4 tests PASS.

**Refs:** FR-6; AC-F01-4

---

## 9. Integration test: full auth flow (backend)

_Chạy với Firebase Emulator + PostgreSQL test DB. Phụ thuộc task 2–5._

**Làm:**
Trong `tests/integration/test_auth_flow.py`:
- `test_full_guest_session_flow`: tạo anonymous token từ emulator →
  `POST /auth/session` → verify DB có 1 row `users`, `is_anonymous=True`.
- `test_full_link_flow`: anonymous session → `POST /auth/link` (Google) →
  verify `user_providers` có 1 row, `users.is_anonymous=False`.
- `test_data_preserved_after_link` _(AC-F01-5)_: tạo guest user, seed
  5 friends + 3 photos (dùng fixture) → link Google →
  verify friends và photos vẫn thuộc đúng `user_id`.
- `test_reinstall_guest_creates_new_uid` _(AC-F01-7)_: token mới (giả lập
  cài lại) → `POST /auth/session` → DB có row mới, row cũ vẫn tồn tại độc lập.
- `test_reinstall_linked_restores_account` _(AC-F01-8)_: user đã link
  Google → token mới cùng Google UID → `POST /auth/session` →
  trả về đúng `user_id` gốc.

**Makefile target:** `make test-integration` (chạy riêng để không block CI unit test).

**Verify:** `make test-integration` → 5 tests PASS.

**Refs:** FR-8; AC-F01-5, AC-F01-7, AC-F01-8

---

## Dependency map

```
1.1 → 3, 4, 5, 9
1.2 → 6, 7, 8
2.1 → 4, 5, 9
2.2 → 5, 9
3.1 → 3.2
3.2 → 4.2, 5.2
4.1 → 4.2
4.2 → 9
5.1 → 5.2
5.2 → 9
6.1 → 6.2
6.2 → 7.2, 8.2
7.1 → 7.2
8.1 → 8.2
```

Tasks 1.1 và 1.2 có thể chạy song song.
Tasks 2.1, 2.2, 3.1 có thể chạy song song sau khi 1.1 xong.
