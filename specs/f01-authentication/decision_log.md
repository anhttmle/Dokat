# F01 — Authentication — Decision Log

## DL-001: pyproject.toml làm file config duy nhất cho tooling

**Date:** 2026-06-18
**Context:** Task 1.1 yêu cầu cấu hình pytest, black, ruff, mypy.
**Decision:** Dùng `pyproject.toml` thay vì các file riêng lẻ
(`setup.cfg`, `.flake8`, `mypy.ini`) để giữ config tập trung.
**Consequence:** Tất cả tooling đọc config từ một nơi duy nhất.

---

## DL-002: ruff thay cho flake8 + isort

**Date:** 2026-06-18
**Context:** Task 1.1 liệt kê `black, ruff, mypy`.
**Decision:** Dùng `ruff` cho cả linting lẫn import sorting
(thay flake8 + isort), `black` chỉ dùng cho formatting.
**Consequence:** `make lint` chạy `ruff check` + `black --check`.

---

## DL-004: Client project sống tại root ME/ với src/ là source root

**Date:** 2026-06-18
**Context:** Task 1.2 yêu cầu tạo cấu trúc `src/` nhưng không chỉ định
folder nào chứa client project. Workspace có `backend/` riêng và `src/`
rỗng ở root.
**Decision:** Client React Native project đặt tại root `/ME/` với source
code trong `src/`. File config (`package.json`, `jest.config.js`, `tsconfig.json`,
`babel.config.js`) đặt ở root cùng cấp `backend/`.
**Consequence:** `npx jest` chạy từ root; import paths trong test dùng
relative paths từ `src/`.

---

## DL-005: Manual mock AsyncStorage thay vì dùng package built-in mock

**Date:** 2026-06-18
**Context:** `@react-native-async-storage/async-storage` cung cấp mock sẵn
tại `…/jest/async-storage-mock`, nhưng cần package được install trước.
**Decision:** Tạo manual mock tại `__mocks__/@react-native-async-storage/async-storage.js`
với in-memory `storage` object; map qua `moduleNameMapper` trong `jest.config.js`.
**Consequence:** Mock rõ ràng, tự kiểm soát behavior; không phụ thuộc vào
implementation nội bộ của package.

---

## DL-006: Unit tests dùng SQLite in-memory thay vì chạy Alembic trên PostgreSQL

**Date:** 2026-06-19
**Context:** Task 2.1 yêu cầu unit tests `test_users_table_exists` và
`test_firebase_uid_unique_constraint` cho migration bảng `users`.
Chạy `alembic upgrade head` trong unit tests đòi hỏi PostgreSQL đang chạy
(vì migration dùng `gen_random_uuid()` và `TIMESTAMPTZ` — PostgreSQL-specific).
**Decision:** Unit tests dùng `Base.metadata.create_all()` với SQLite
in-memory (`sqlite:///:memory:`) để kiểm tra schema contract (table tồn
tại, UNIQUE constraint hoạt động) mà không cần PostgreSQL.
Migration Alembic vẫn dùng PostgreSQL-specific DDL cho production.
**Consequence:** Unit tests chạy không cần Docker/PostgreSQL. Integration
tests (chạy `alembic upgrade head` trên real PostgreSQL) là việc riêng
của CI pipeline.

---

## DL-007: Migration tạo thủ công (không dùng --autogenerate)

**Date:** 2026-06-19
**Context:** Task 2.1 chỉ yêu cầu migration cho bảng `users`. Model
`UserProvider` đã tồn tại trong `app/models/user.py`, nên `--autogenerate`
sẽ kéo cả bảng `user_providers` vào cùng migration.
**Decision:** Dùng `alembic revision -m "create_users_table"` (không có
`--autogenerate`) rồi viết `upgrade()`/`downgrade()` thủ công chỉ cho
bảng `users`. Bảng `user_providers` sẽ là migration riêng biệt ở task sau.
**Consequence:** Mỗi migration file scope rõ ràng; dễ rollback độc lập.

---

## DL-008: PRAGMA foreign_keys=ON trong SQLite test cho user_providers

**Date:** 2026-06-19
**Context:** Task 2.2 yêu cầu `test_user_providers_fk` — insert
`user_providers` với `user_id` không tồn tại → phải raise error.
SQLite mặc định **không** enforce FK constraint; cần bật tường minh.
**Decision:** Dùng `event.listens_for(engine, "connect")` để chạy
`PRAGMA foreign_keys=ON` trên mỗi connection mới trong fixture
`db_engine` của file test `test_user_providers_migration.py`.
**Consequence:** FK enforcement hoạt động đúng trong SQLite in-memory
test mà không ảnh hưởng các test khác (mỗi fixture dùng engine riêng).

---

## DL-009: oauth_provider ENUM — dùng create_type=False trong op.create_table

**Date:** 2026-06-19
**Context:** Migration `user_providers` cần tạo PostgreSQL ENUM
`oauth_provider` trước khi tạo bảng. Nếu dùng `sa.Enum(...)`
trực tiếp trong `op.create_table()` mà không quản lý lifecycle
của ENUM, Alembic sẽ tự động tạo/xóa ENUM cùng bảng — nhưng
không xử lý đúng `checkfirst` khi chạy lại migration.
**Decision:** Khai báo `postgresql.ENUM(..., create_type=False)` làm
biến module-level; gọi `_OAUTH_PROVIDER.create(op.get_bind(), checkfirst=True)`
trong `upgrade()` và `_OAUTH_PROVIDER.drop(..., checkfirst=True)`
trong `downgrade()` để kiểm soát lifecycle ENUM tường minh.
**Consequence:** Migration idempotent — không lỗi nếu ENUM đã tồn tại.

---

## DL-010: FirebaseAuthMiddleware là class-based ASGI middleware, tách biệt với verify_firebase_token dependency

**Date:** 2026-06-20
**Context:** Task 3.1 yêu cầu viết tests cho `FirebaseAuthMiddleware` (tên
trong design §4.2). File `app/middleware/auth.py` hiện có `verify_firebase_token`
là FastAPI dependency function, không phải class middleware.
Design §3.3 nói "inject `firebase_uid` vào request context" — điều này chỉ
tự nhiên với class-based middleware (đặt vào `request.state`), không phải
dependency function (trả về qua DI).
**Decision:** `FirebaseAuthMiddleware` được viết test như một Starlette
`BaseHTTPMiddleware` class, inject `firebase_uid` vào `request.state.firebase_uid`,
trả về JSON response trực tiếp (không qua `HTTPException`) với format
`{"error": "...", "message": "..."}` theo design §5.2.
`verify_firebase_token` dependency hiện tại là implementation khác, sẽ được
đánh giá khi implement task 3.2+.
**Consequence:** Tests dùng `app.add_middleware(FirebaseAuthMiddleware)` trên
test app; error response body là `{"error": "...", "message": "..."}` (không
có wrapper `"detail"`).

---

## DL-011: ImportError là RED state hợp lệ cho TDD test của FirebaseAuthMiddleware

**Date:** 2026-06-20
**Context:** Task 3.1 yêu cầu "5 tests FAIL". `FirebaseAuthMiddleware` class
chưa tồn tại → pytest collection fail với ImportError thay vì 5 test failures
riêng biệt.
**Decision:** ImportError tại collection time được chấp nhận là trạng thái RED
trong TDD cycle. Khi `FirebaseAuthMiddleware` được implement, tests sẽ collect
và từng test sẽ pass/fail độc lập.
**Consequence:** Không cần tạo stub class chỉ để biến collection error thành
5 individual failures.

---

## DL-012: FirebaseAuthMiddleware implement là class, không phải FastAPI dependency

**Date:** 2026-06-20
**Context:** Task 3.2 nói "implement as FastAPI dependency (`Depends`)" nhưng
tests từ task 3.1 (đã viết và được chấp nhận) dùng
`app.add_middleware(FirebaseAuthMiddleware)` và kiểm tra
`request.state.firebase_uid` — cả hai yếu tố này chỉ hoạt động với
class-based Starlette middleware, không phải FastAPI dependency function.
**Decision:** `FirebaseAuthMiddleware` được implement là
`BaseHTTPMiddleware` subclass. `verify_firebase_token` dependency giữ nguyên
(chưa xóa) để không làm hỏng các import tiềm năng khác.
**Consequence:** Tests từ task 3.1 pass 5/5. Nếu sau này cần dùng dependency
pattern thuần (không ASGI middleware), cần viết tests mới tương ứng.

---

## DL-013: firebase_credentials_path thay bằng firebase_credentials_json trong Settings

**Date:** 2026-06-20
**Context:** Task 3.2 yêu cầu `firebase.py` đọc credentials từ env
`FIREBASE_CREDENTIALS_JSON` (JSON string). Field cũ là
`firebase_credentials_path` (file path) không còn phù hợp với yêu cầu deploy
trên cloud không có file system.
**Decision:** Thay `firebase_credentials_path: str = ""` bằng
`firebase_credentials_json: str = ""` trong `Settings`. `firebase.py` parse
JSON string bằng `json.loads()` rồi tạo `credentials.Certificate()`.
**Consequence:** Credentials được truyền qua env var (phù hợp 12-factor app);
không cần mount file vào container.

---

## DL-014: SQLite in-memory router tests dùng StaticPool + check_same_thread=False

**Date:** 2026-06-20
**Context:** Task 4.1/4.2 — router tests dùng `TestClient(app)` với SQLite
in-memory. FastAPI chạy sync route trong worker thread qua
`anyio.to_thread.run_sync`. Hai vấn đề xuất hiện:
1. `sqlite3.ProgrammingError: SQLite objects created in a thread can only
   be used in that same thread` — connection bị block cross-thread.
2. `OperationalError: no such table: users` — mỗi SQLite in-memory connection
   có database riêng biệt; worker thread tạo connection mới thấy DB trống.
**Decision:** Dùng `StaticPool` để SQLAlchemy tái sử dụng đúng một connection
duy nhất cho toàn bộ engine; kết hợp `check_same_thread=False` để cho phép
connection đó dùng từ nhiều thread.
**Consequence:** Tất cả test fixtures dùng SQLite in-memory phải khai báo
`poolclass=StaticPool` và `connect_args={"check_same_thread": False}`.

---

## DL-015: get_db dependency định nghĩa trong router, sync session

**Date:** 2026-06-20
**Context:** Task 4.2 yêu cầu endpoint `POST /auth/session` có DB access.
Config production dùng `database_url = postgresql+asyncpg://...` (async),
nhưng các services được implement synchronous (không dùng async/await).
**Decision:** `get_db` là sync generator dependency định nghĩa trong
`app/routers/auth.py`. Engine production dùng `+asyncpg` URL stripped thành
sync PostgreSQL URL. Tests override hoàn toàn `get_db` qua
`app.dependency_overrides`, không cần thay đổi config.
**Consequence:** Khi migrate sang async (future task), cần refactor
`get_or_create_user`, `build_session_response` và `get_db` sang async pattern.

---

## DL-016: FirebaseAuthMiddleware được add vào main.py globally

**Date:** 2026-06-20
**Context:** Task 4.2 yêu cầu endpoint session "dùng FirebaseAuthMiddleware".
Middleware đã implement là ASGI class (BaseHTTPMiddleware), không phải
per-route dependency.
**Decision:** `app.add_middleware(FirebaseAuthMiddleware)` trong `main.py`,
bảo vệ toàn bộ app (kể cả `/health`). Việc exempt `/health` khỏi auth là
concern của task khác.
**Consequence:** Mọi endpoint (kể cả `/health`) đều yêu cầu Firebase token.
Tests dùng `patch("firebase_admin.auth.verify_id_token")` để bypass middleware.

---

## DL-017: token_claims injected vào request.state bởi FirebaseAuthMiddleware

**Date:** 2026-06-20
**Context:** Task 5.2 — endpoint `POST /auth/link` cần trích xuất thông
tin provider từ Firebase ID Token (``sign_in_provider``, ``identities``).
Middleware hiện chỉ inject ``firebase_uid``; router không có cách nào
đọc phần còn lại của decoded token.
**Decision:** Thêm ``request.state.token_claims = decoded`` vào
``FirebaseAuthMiddleware.dispatch()`` ngay sau khi set ``firebase_uid``.
Link endpoint đọc ``request.state.token_claims`` để lấy provider info.
**Consequence:** Tất cả endpoint downstream có thể đọc claims đầy đủ
từ ``request.state.token_claims`` mà không cần gọi lại
``verify_id_token``. Tests tiếp tục patch
``firebase_admin.auth.verify_id_token`` như cũ.

---

## DL-018: merge case không reassign friends/photos (tables chưa tồn tại)

**Date:** 2026-06-20
**Context:** Task 5.2 mô tả merge: "reassign foreign keys (friends,
photos) từ guest sang user B". Bảng friends (F03) và photos (F05) chưa
được tạo ở thời điểm task này.
**Decision:** ``link_provider()`` trong ``auth_service.py`` chỉ xóa
guest record (cascade xóa providers). Comment trong code đánh dấu vị
trí cần thêm reassignment khi F03/F05 được implement.
**Consequence:** Merge hiện tại an toàn vì guest chưa có friends/photos.
Khi F03/F05 hoàn thành, cần cập nhật ``link_provider`` để reassign.

---



**Date:** 2026-06-18
**Context:** Backend dùng async FastAPI; test cần async fixtures.
**Decision:** Đặt `asyncio_mode = "auto"` trong `pyproject.toml`
để tránh phải thêm `@pytest.mark.asyncio` ở mỗi test.
**Consequence:** Tất cả async test functions chạy tự động.

---

## DL-019: AuthService.init() không gọi POST /auth/session

**Date:** 2026-06-20
**Context:** Task 6.2 mô tả "Sau `signInAnonymously()`: gọi `POST /auth/session`,
cập nhật store." Nhưng 3 test được liệt kê ở task 6.1 không có test nào
kiểm tra lời gọi API hay cập nhật store.
**Decision:** `AuthService.init()` chỉ implement những gì tests cover:
đọc storage → restore hoặc signInAnonymously → lưu uid. Lời gọi
`POST /auth/session` và cập nhật store sẽ được thêm khi có test tương ứng.
**Consequence:** YAGNI — không build trước feature chưa có test. Khi task
tiếp theo yêu cầu API call trong init(), cần thêm test + implementation.

---

## DL-020: Tests thêm vào file hiện có thay vì tạo file mới

**Date:** 2026-06-20
**Context:** Task 6.1 yêu cầu 5 tests mới nhưng cả hai file
`AuthService.test.ts` và `LocalStorageService.test.ts` đã tồn tại với
tests khác đang PASS.
**Decision:** Append tests vào cuối các file hiện có thay vì tạo file mới.
Mỗi nhóm tests mới được đặt trong `describe` block riêng để tách biệt
setup (beforeEach reset storage, reset mocks) với các tests cũ.
**Consequence:** Không phá vỡ 17 tests đang pass; tests mới có isolation
rõ ràng qua beforeEach riêng của mỗi describe block.

---

## DL-021: useRequireLinked là named export từ AuthGuard.tsx

**Date:** 2026-06-20
**Context:** Task 7.2 yêu cầu `AuthGuard.tsx` chứa hook `useRequireLinked()`.
Có thể đặt hook này trong file riêng (`useRequireLinked.ts`) hoặc
cùng file với `AuthGuard` component.
**Decision:** `useRequireLinked` là `named export` từ `AuthGuard.tsx`, giữ
cùng file vì hook và component chia sẻ mục đích (auth gating). Default
export vẫn là `AuthGuard` component.
**Consequence:** Import trong test: `import AuthGuard, { useRequireLinked }
from '../../components/auth/AuthGuard'`. Nếu hook phức tạp hơn sau này,
có thể tách ra file riêng mà không cần thay đổi consumer imports.

---

## DL-022: LinkAccountSheet trả null khi visible=false thay vì dựa vào Modal

**Date:** 2026-06-20
**Context:** React Native `Modal` với `visible={false}` vẫn render children
trong môi trường test (jest preset mock Modal thành plain View). Nếu chỉ
dùng `visible` prop của Modal, `queryByTestId('link-account-sheet')` sẽ
tìm thấy element kể cả khi sheet đáng lẽ phải ẩn → test assertions sai.
**Decision:** `LinkAccountSheet` returns `null` sớm khi `visible=false`.
Modal giữ nguyên cho production (animation, native layer), nhưng conditional
return đảm bảo test có thể assert `queryByTestId` trả `null` đúng.
**Consequence:** Test assertions cho "sheet is not visible" hoạt động
chính xác. Production behavior không thay đổi (Modal chỉ thấy khi visible=true).

---

## DL-023: AuthService.linkWithProvider dùng OAuthProvider stub

**Date:** 2026-06-20
**Context:** Task 7.2 yêu cầu `AuthService.linkWithProvider(provider)`.
OAuth flow thực (Google Sign-In, Apple Auth) cần native SDK modules và
không thể test trong Jest environment.
**Decision:** Implementation dùng `auth.OAuthProvider` từ Firebase mock
với type cast `as any`. Trong unit tests, toàn bộ `AuthService` được mock
(`jest.mock('../../services/AuthService')`), nên implementation không ảnh
hưởng kết quả tests. Khi integrate native OAuth (task khác), method này
sẽ được cập nhật với flow thực.
**Consequence:** `linkWithProvider` có signature đúng và testable; native
OAuth integration là concern của task sau.
