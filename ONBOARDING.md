# Tài liệu Onboarding — Dokat (ME)

Dành cho **junior fullstack developer** mới gia nhập dự án.  
Đọc tài liệu này từ đầu đến cuối trước khi chạm vào bất kỳ dòng code nào.

---

## Mục lục

1. [Giới thiệu dự án](#1-giới-thiệu-dự-án)
2. [Kiến trúc tổng quan](#2-kiến-trúc-tổng-quan)
3. [Setup môi trường](#3-setup-môi-trường)
4. [Cấu trúc codebase](#4-cấu-trúc-codebase)
5. [Luồng Authentication](#5-luồng-authentication)
6. [Quy trình phát triển (SDD)](#6-quy-trình-phát-triển-sdd)
7. [Chạy Tests](#7-chạy-tests)
8. [Build & Deploy](#8-build--deploy)
9. [Các điểm cần lưu ý](#9-các-điểm-cần-lưu-ý)
10. [Tài liệu tham khảo](#10-tài-liệu-tham-khảo)

---

## 1. Giới thiệu dự án

**Dokat** là mạng xã hội ảnh thú cưng (chó/mèo), cho phép chủ thú cưng gửi
ảnh đến bạn bè theo thời gian thực — tương tự Locket nhưng chỉ tập trung vào
pet content, không có ảnh người. MVP nhắm thị trường Việt Nam.

### Tech stack tóm gọn

| Layer | Công nghệ |
|---|---|
| Mobile client | Flutter 3.22+ (Dart 3.4+) |
| State management | Riverpod 2 (AsyncNotifier) |
| Navigation | go_router 14 |
| HTTP client | Dio 5 |
| Auth | **JWT mode** (standalone, default) hoặc Firebase Auth (`AUTH_MODE=firebase`) |
| Backend | FastAPI (Python) + Uvicorn |
| Database | PostgreSQL (SQLAlchemy async + asyncpg) |
| Migrations | Alembic |
| Cache | Redis (QR OTP, TTL 5 phút) |
| Storage | **MinIO** (standalone, default) hoặc AWS S3 + CloudFront CDN (`STORAGE_BACKEND=s3`) |
| Push notifications | Firebase Cloud Messaging (FCM) — graceful no-op khi không cấu hình |
| AI validation | On-device (tflite_flutter) — không gọi server |
| Test (backend) | pytest + httpx + moto + fakeredis |
| Test (client) | flutter_test + mockito |

---

## 2. Kiến trúc tổng quan

### Luồng request end-to-end

```mermaid
flowchart TD
    Client["React Native Client"]
    Firebase["Firebase Auth SDK"]
    Middleware["FirebaseAuthMiddleware\n(verify ID Token)"]
    Routers["FastAPI Routers"]
    Services["Services Layer\n(business logic)"]
    DB[("PostgreSQL")]
    Redis[("Redis\nQR OTP")]
    S3["AWS S3\n+ CloudFront"]
    FCM["Firebase FCM\n(push notifications)"]

    Client -->|"Bearer ID Token"| Middleware
    Client -->|"getIdToken()"| Firebase
    Firebase -->|"ID Token"| Client
    Middleware -->|"request.state.firebase_uid"| Routers
    Routers --> Services
    Services --> DB
    Services --> Redis
    Services --> S3
    Services --> FCM
```

### Monorepo layout

```
.
├── src/               # React Native client (TypeScript)
├── backend/           # FastAPI Python backend
├── specs/             # Spec-Driven Development docs (PRD + F01–F11)
├── __mocks__/         # Jest mocks (Firebase Auth, AsyncStorage)
├── .cursor/rules/     # Coding rules (SDD + Karpathy guidelines)
└── .github/workflows/ # CI (hiện cần cập nhật — xem §8)
```

### Danh sách API endpoints (10 router)

| Prefix | File | Mục đích |
|---|---|---|
| `POST /auth/session` | `routers/auth.py` | Tạo / khôi phục user session |
| `POST /auth/link` | `routers/auth.py` | Gắn OAuth provider vào account |
| `GET /PATCH /profile/me` | `routers/profile.py` | Lấy / cập nhật hồ sơ chủ |
| `POST /profile/me/avatar/upload-url` | `routers/profile.py` | Presigned URL upload avatar |
| `/pets/*` | `routers/pets.py` | CRUD pet profile + ảnh pet |
| `/friends/*` | `routers/friends.py` | QR generate/scan, danh sách bạn, FCM token |
| `POST /posts` | `routers/posts.py` | Gửi ảnh (tạo post + recipients) |
| `GET /feed` | `routers/feed.py` | Feed ảnh nhận được (24h, cursor pagination) |
| `/posts/{id}/seen*` | `routers/seen.py` | Đánh dấu đã xem, xem ai đã xem |
| `GET /history/sent|received` | `routers/history.py` | Lịch sử ảnh đã gửi / nhận |
| `/users/block|report|logout` | `routers/settings.py` | Chặn, báo cáo, đăng xuất |
| `GET|PUT /notifications/preferences` | `routers/notifications.py` | Toggle reminder |
| `GET /health` | `main.py` | Health check |

---

## 3. Setup môi trường

### Prerequisites

**Cách 1 — Docker Compose (khuyến nghị, nhanh nhất):**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 24+
- Python 3.11+ (chỉ cần cho backend dev, không cần nếu chỉ chạy Docker)
- **Flutter 3.22+** (để chạy app mobile)

**Cách 2 — Manual (cài từng service):**
- Python 3.11+, PostgreSQL 14+, Redis 7+, MinIO server
- **Flutter 3.22+** — cài theo [flutter.dev/install](https://flutter.dev/docs/get-started/install)
- Android Studio (cho Android emulator) hoặc Xcode (cho iOS)

---

### Bước 1 — Clone và cài đặt

```bash
git clone <repo-url>
cd ME

# Backend
cd backend
make install        # tạo .venv + pip install -r requirements.txt
cd ..

# Flutter client
cd client
flutter pub get
cd ..
```

---

### Bước 2 — Credentials & Secrets

> Tất cả giá trị dưới đây là **defaults cho môi trường local/dev**.
> Production phải thay `JWT_SECRET_KEY` và dùng giá trị riêng.

#### Services & Ports (Docker Compose)

| Service | URL / Port | Mục đích |
|---------|-----------|---------|
| **Flutter Web** | http://\<PUBLIC_HOST\>:8080 | Client web; API tại `/api` |
| **Backend API** | http://\<PUBLIC_HOST\>:8000 | Swagger (tùy chọn; web dùng `/api`) |
| **PostgreSQL** | localhost:5432 | Database chính |
| **Redis** | localhost:6379 | QR OTP cache |
| **MinIO API** | http://localhost:9000 | Object storage (S3-compatible) |
| **MinIO Console** | http://localhost:9001 | Web UI quản lý bucket |
| **CloudBeaver** | http://localhost:8978 | Web UI review PostgreSQL |

#### Credentials mặc định (Docker Compose)

| Service | Biến | Giá trị mặc định | Ghi chú |
|---------|------|-----------------|---------|
| **PostgreSQL** | `POSTGRES_DB` | `me_dev` | |
| | `POSTGRES_USER` | `me_user` | |
| | `POSTGRES_PASSWORD` | `me_pass` | |
| | `DATABASE_URL` | `postgresql+asyncpg://me_user:me_pass@localhost:5432/me_dev` | |
| **Redis** | `REDIS_URL` | `redis://localhost:6379/0` | No auth |
| **MinIO** | `MINIO_ROOT_USER` | `minioadmin` | |
| | `MINIO_ROOT_PASSWORD` | `minioadmin` | |
| | `MINIO_ENDPOINT_URL` | `http://localhost:9000` | Backend → MinIO (trong Docker: `http://minio:9000`) |
| | `MINIO_PUBLIC_ENDPOINT_URL` | `http://<PUBLIC_HOST>:9000` | Presigned URL cho browser (set trong `.env` gốc) |
| | `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | `minioadmin` / `minioadmin` | boto3 ký presigned URL |
| | `S3_BUCKET` | `pawsnap` | Bucket tự tạo khi compose up |
| **JWT Auth** | `JWT_SECRET_KEY` | `change-me-in-production` | **Bắt buộc thay trong prod** |
| | `JWT_EXPIRE_DAYS` | `30` | |
| **Firebase** | `FIREBASE_CREDENTIALS_JSON` | `""` (rỗng) | Không cần ở standalone mode |

#### Kết nối CloudBeaver → PostgreSQL

Lần đầu mở http://localhost:8978:
1. Hoàn thành wizard tạo admin account
2. **New Connection → PostgreSQL**
3. Điền:
   - Host: `postgres` *(tên service trong Docker network)*
   - Port: `5432`
   - Database: `me_dev`
   - Username: `me_user`
   - Password: `me_pass`

#### Cấu hình backend `.env`

```bash
cp backend/.env.example backend/.env
```

**Standalone mode (mặc định — không cần Firebase/AWS):**

```dotenv
AUTH_MODE=jwt
JWT_SECRET_KEY=change-me-to-a-long-random-string-min-32-chars
JWT_EXPIRE_DAYS=30

STORAGE_BACKEND=minio
MINIO_ENDPOINT_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
S3_BUCKET=pawsnap
AWS_REGION=us-east-1

DATABASE_URL=postgresql+asyncpg://me_user:me_pass@localhost:5432/me_dev
REDIS_URL=redis://localhost:6379/0

FIREBASE_CREDENTIALS_JSON=
```

**Production mode (Firebase + AWS S3):**

```dotenv
AUTH_MODE=firebase
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

STORAGE_BACKEND=s3
S3_BUCKET=pawsnap
CDN_BASE_URL=https://cdn.pawsnap.app
AWS_REGION=us-east-1

DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/me_prod
REDIS_URL=redis://<host>:6379/0
```

> Xem đầy đủ tất cả env vars và giải thích: [`backend/.env.example`](backend/.env.example)

---

### Bước 3 — Khởi động hệ thống

#### Option A — Docker Compose (khuyến nghị)

Tạo file `.env` ở thư mục gốc repo (copy từ `.env.example`):

```bash
cp .env.example .env
```

**Truy cập từ máy khác (điện thoại, laptop trong LAN):** đặt `PUBLIC_HOST`
bằng **IP LAN** của máy chạy Docker (không dùng `localhost`):

```dotenv
# Ví dụ máy host có IP 192.168.1.100 trên WiFi
PUBLIC_HOST=192.168.1.100
```

| Biến | Mục đích |
|------|----------|
| `PUBLIC_HOST` | Hostname/IP mà **trình duyệt bên ngoài** dùng để mở app |
| → MinIO presigned URL | `http://PUBLIC_HOST:9000/...` (upload ảnh) |
| → Flutter web API | Tự động qua `https://PUBLIC_HOST:8443/api` (nginx proxy) |

#### HTTPS — bắt buộc để camera hoạt động trên LAN

Trình duyệt chỉ cho phép `getUserMedia` (camera/microphone) trong **secure
context** (`https://` hoặc `localhost`). Cần chạy qua HTTPS khi dùng từ
điện thoại hoặc thiết bị khác trong mạng LAN.

**Lần đầu (một lần duy nhất trên máy host):**

```bash
brew install mkcert   # macOS; xem https://github.com/FiloSottile/mkcert
mkcert -install       # cài root CA vào hệ thống
make gen-certs PUBLIC_HOST=192.168.1.100   # tạo cert cho IP LAN
```

**Cài root CA lên iPhone/Android (để Safari/Chrome tin cert):**
1. Tìm file CA: `open "$(mkcert -CAROOT)"` → lấy `rootCA.pem`
2. AirDrop / email file đó sang điện thoại
3. iOS: mở file → cài Profile → Settings → General → About →
   Certificate Trust Settings → bật trust cho "mkcert …"

```bash
docker compose up -d
# Tự động: postgres + redis + minio + cloudbeaver + backend + client web
```

**URL khi `PUBLIC_HOST=192.168.1.100`:**

| Service | URL |
|---------|-----|
| App web (HTTPS — camera OK) | **https://192.168.1.100:8443** |
| App web (HTTP → redirect) | http://192.168.1.100:8080 |
| API (qua proxy) | https://192.168.1.100:8443/api |
| MinIO upload | http://192.168.1.100:9000 |
| Backend trực tiếp (Swagger) | http://192.168.1.100:8000 |

> Client web **không** hardcode `localhost:8000`. Nginx proxy `/api` → backend
> nên cùng một image hoạt động từ localhost lẫn IP LAN mà không rebuild.
>
> **Web session storage:** trên web, JWT và `device_id` được lưu vào
> `localStorage` (qua `shared_preferences`) thay vì `flutter_secure_storage`,
> vì Web Crypto API — cần thiết để mã hoá — chỉ hoạt động trên `https://`
> hoặc `localhost`. Plain HTTP qua IP LAN hoạt động bình thường với cách này.

Verify:
```bash
curl http://localhost:8000/health               # → {"status":"ok"}
curl -k https://localhost:8443/api/health       # → {"status":"ok"} (qua proxy)
curl -kI https://localhost:8443                 # → HTTP/1.1 200 OK
```

Chỉ build lại client web sau khi sửa Flutter:

```bash
docker compose up -d --build client
```

Sau khi đổi `PUBLIC_HOST`, cần gen lại cert và restart:

```bash
make gen-certs PUBLIC_HOST=<IP-mới>
docker compose up -d --force-recreate backend client
```

#### Option B — Manual

```bash
# Tạo database
createdb me_dev

# Chạy migrations
cd backend && make migrate

# Khởi động backend
make run
```

Hiện có **7 migration files** theo thứ tự:

| Revision | Nội dung |
|---|---|
| `ab39c569791b` | Tạo bảng `users` |
| `c526c80e8e72` | Tạo bảng `user_providers` |
| `3b8e1f2a6d90` | Tạo bảng `pet_profiles` |
| `e7d2a1f0c4b8` | Tạo bảng `friendships` + cột `fcm_token` |
| `f1a2b3c4d5e6` | Tạo bảng `posts` + `post_recipients` |
| `b2c3d4e5f6a7` | Tạo bảng `blocked_users` + `reports` |
| `a1b2c3d4e5f6` | Thêm `users.timezone` + `notification_preferences` |

### Bước 4 — Chạy backend

```bash
cd backend
make run            # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Kiểm tra: `curl http://localhost:8000/health` → `{"status": "ok"}`

Swagger UI tự động tại `http://localhost:8000/docs`.

---

## 4. Cấu trúc codebase

### Backend — Kiến trúc phân tầng

```
backend/
├── app/
│   ├── main.py                  # FastAPI app + đăng ký router
│   ├── core/
│   │   ├── config.py            # pydantic-settings (đọc .env)
│   │   ├── firebase.py          # khởi tạo Firebase Admin SDK
│   │   └── redis.py             # Redis client
│   ├── middleware/
│   │   └── auth.py              # FirebaseAuthMiddleware (global)
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py              # User, UserProvider
│   │   ├── pet_profile.py       # PetProfile, PetSpecies, PetGender
│   │   ├── friendship.py        # Friendship
│   │   ├── post.py              # Post
│   │   ├── post_recipient.py    # PostRecipient
│   │   ├── block.py             # BlockedUser
│   │   ├── report.py            # Report
│   │   └── notification_pref.py # NotificationPreference, ReminderType
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── routers/                 # API handlers (mỏng — chỉ điều phối)
│   └── services/                # Business logic (đặt toàn bộ logic ở đây)
├── alembic/                     # Migrations
├── config/
│   └── reminders.yaml           # Lịch reminder (F09)
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── migrations/              # Schema migration tests
    ├── integration/             # End-to-end (cần Postgres + Firebase emulator)
    └── test_*.py                # Unit / router tests (SQLite in-memory)
```

**Nguyên tắc:** router không chứa business logic. Mọi xử lý đặt trong
`services/`. Router chỉ: nhận request → gọi service → trả response / map lỗi.

### Client Flutter — Cấu trúc `client/`

```
client/
├── pubspec.yaml         # Dependencies (riverpod, dio, go_router, firebase_*, ...)
├── analysis_options.yaml
├── lib/
│   ├── main.dart        # Entry: Firebase.initializeApp + ProviderScope + runApp
│   ├── app.dart         # DokatApp (MaterialApp.router + go_router config)
│   ├── core/
│   │   ├── api_client.dart       # Dio + Bearer token interceptor
│   │   ├── constants.dart        # BASE_URL, hard limits
│   │   ├── firebase_options.dart # FlutterFire CLI generated (tự đặt)
│   │   └── providers.dart        # dioProvider, firebaseAuthProvider
│   ├── features/        # Mỗi feature có data/domain/presentation/
│   │   ├── auth/        # F01: AuthService, AuthNotifier, AuthGuard, ForceLinkScreen
│   │   ├── profile/     # F02: ProfileService, PetService, ProfileScreen
│   │   ├── social/      # F03: SocialService, FriendListScreen, QRScannerScreen
│   │   ├── capture/     # F04: CaptureService, PetValidationService, CameraScreen
│   │   ├── send/        # F05: SendService, RecipientSelectorScreen
│   │   ├── feed/        # F06: FeedService, FeedScreen, FeedItem
│   │   ├── seen/        # F07: SeenService, SeenByList
│   │   ├── history/     # F08: HistoryService, HistoryScreen
│   │   ├── notifications/ # F09: NotificationService, NotificationPreferenceSection
│   │   ├── settings/    # F10: SettingsService, SettingsScreen, AccountLinkRow
│   │   └── location/    # F11: LocationService, LocationPayload
│   └── shared/
│       ├── widgets/     # LoadingOverlay
│       └── utils/       # relativeTime()
├── test/                # Flutter tests (mirror lib/features/)
├── android/             # Android native shell
│   └── app/
│       └── google-services.json  (gitignore'd — chạy flutterfire configure)
└── ios/                 # iOS native shell
    └── Runner/
        └── GoogleService-Info.plist  (gitignore'd — chạy flutterfire configure)
```

### Client RN legacy — `client-rn/` (reference only)

```
client-rn/
├── App.tsx              # Root component RN cũ
├── src/                 # Services, screens, stores, tests gốc (TypeScript)
└── package.json
```

### Specs — Một feature, một thư mục

```
specs/
├── PRD.md                    # Source of truth: toàn bộ product requirements
├── f01-authentication/
│   ├── requirements.md       # User stories + Acceptance Criteria
│   ├── design.md             # Thiết kế kỹ thuật chi tiết
│   ├── tasks.md              # Task breakdown (TDD step-by-step)
│   └── decision_log.md       # Quyết định ngoài spec
├── f02-profile/
├── f03-social-graph/
└── ...                       # F04 → F11
```

---

## 5. Luồng Authentication

### Tổng quan

Dự án dùng **Firebase Authentication** theo mô hình:
1. Mở app → tự động đăng nhập **Anonymous** (không cần action từ user).
2. Khi user muốn link tài khoản → **link OAuth provider** (Google/Apple/Facebook)
   vào cùng anonymous account, không mất dữ liệu.
3. Mọi API call đính kèm **Firebase ID Token** (JWT) trong header.

### Sequence diagram

```mermaid
sequenceDiagram
    participant App as React Native App
    participant FBSDK as Firebase SDK
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    App->>FBSDK: signInAnonymously()
    FBSDK-->>App: UserCredential (anonymous)
    App->>FBSDK: getIdToken()
    FBSDK-->>App: ID Token (JWT)

    App->>API: POST /auth/session\nAuthorization: Bearer <token>
    API->>FBSDK: verify_id_token(token)
    FBSDK-->>API: {uid: "abc123", ...}
    API->>DB: get_or_create_user(firebase_uid)
    DB-->>API: User record
    API-->>App: {user_id, is_anonymous: true, ...}

    Note over App,API: Mọi request tiếp theo đều kèm Bearer token

    App->>FBSDK: linkWithCredential(googleCredential)
    FBSDK-->>App: Linked UserCredential
    App->>API: POST /auth/link\nAuthorization: Bearer <new-token>
    API->>DB: link_provider(firebase_uid, "google", provider_uid)
    API-->>App: {is_anonymous: false, providers: ["google"]}
```

### Token trong backend

`FirebaseAuthMiddleware` áp dụng cho **toàn bộ routes**. Khi verify thành công:

```python
request.state.firebase_uid   # "abc123" — dùng để lookup user trong DB
request.state.token_claims   # full decoded JWT payload
```

Các lỗi trả về:

| HTTP code | Error code | Nguyên nhân |
|---|---|---|
| 401 | `AUTH_TOKEN_MISSING` | Thiếu header hoặc sai format |
| 401 | `AUTH_TOKEN_EXPIRED` | Token hết hạn |
| 401 | `AUTH_TOKEN_REVOKED` | Token bị thu hồi |
| 503 | `AUTH_SERVICE_UNAVAILABLE` | Firebase SDK lỗi tạm thời |

### Mock trong tests

Tất cả test backend đều mock `firebase_admin.auth.verify_id_token` qua
fixture `mock_verify_id_token` trong `backend/tests/conftest.py`:

```python
@pytest.fixture(autouse=False)
def mock_verify_id_token():
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {
            "uid": "test-uid-anonymous",
            "firebase": {"sign_in_provider": "anonymous"},
        }
        yield mock
```

Dùng fixture này trong router tests:

```python
def test_something(client: TestClient, mock_verify_id_token: MagicMock):
    # mock đã active — gửi request bình thường
    resp = client.get("/profile/me", headers={"Authorization": "Bearer fake"})
```

---

## 6. Quy trình phát triển (SDD)

Dự án theo **Spec-Driven Development** — bắt buộc, không ngoại lệ.

### Các bước khi nhận một task

```mermaid
flowchart TD
    A["Nhận task (ví dụ: F05-T3)"]
    B["Đọc specs/f05-send-photo/requirements.md\nvà design.md"]
    C{"Spec có\nrõ ràng?"}
    D["Hỏi team trưởng\nhoặc yêu cầu cập nhật spec"]
    E["Viết test trước\n(TDD)"]
    F["Implement\n(chỉ đúng task được giao)"]
    G["Chạy tests pass?"]
    H["Fix bugs"]
    I{"Có quyết định\nngoài spec?"}
    J["Ghi vào decision_log.md"]
    K["Done — tạo PR"]

    A --> B
    B --> C
    C -->|Không| D
    C -->|Có| E
    E --> F
    F --> G
    G -->|Không| H
    H --> G
    G -->|Có| I
    I -->|Có| J
    J --> K
    I -->|Không| K
```

### Rules bắt buộc (từ `.cursor/rules/sdd.mdc`)

1. **Đọc spec trước khi code.** Nếu chưa có spec, DỪNG và yêu cầu tạo spec.
2. **Một task tại một thời điểm** — không ôm nhiều việc.
3. **TDD:** test trước, implementation sau.
4. **Không thêm gì ngoài spec** — không "nice to have", không over-engineer.
5. **Decision log:** quyết định ngoài spec → ghi `specs/<feature>/decision_log.md`.
6. Khi phân vân, làm **ÍT hơn** chứ không nhiều hơn.

### Coding standards

**Python (backend):**

- PEP 8 / PEP 257 — 4 spaces, dòng ≤ 79 ký tự
- Một class hoặc một function chính mỗi file
- Format: `black` + `isort`; lint: `ruff`
- Import order: stdlib → third-party → local (cách nhau dòng trống)
- Docstring cho mọi public class và function
- Không hardcode secrets — dùng `backend/.env` + pydantic settings

**TypeScript (client):**

- `dart format` — auto-format Dart code
- `flutter analyze` — static analysis (rules trong `analysis_options.yaml`)
- Test với `flutter_test` + `mockito`

**Nguyên tắc chung:** DRY, KISS, YAGNI, SOLID. Tránh nesting > 3 cấp.
Đặt tên mô tả rõ ý nghĩa.

---

## 7. Chạy Tests

### Backend

```bash
cd backend

# Unit tests + router tests (SQLite in-memory, nhanh ~10s)
make test

# Integration tests (cần Postgres + Firebase Auth Emulator)
make test-integration

# Lint + format check
make lint
```

**Integration tests cần thêm:**

```bash
# Khởi động Firebase emulator (terminal riêng)
firebase emulators:start --only auth

# Set env vars
export FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
export FIREBASE_PROJECT_ID=demo-test
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/me_test
```

**Pattern chuẩn cho router tests** (SQLite in-memory, không cần Postgres):

```python
@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

@pytest.fixture()
def client(db_session, mock_verify_id_token) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### Client Flutter

```bash
cd client

# Chạy toàn bộ unit + widget tests
flutter test

# Chạy với coverage report
flutter test --coverage

# Analyze (lint)
flutter analyze
```

Test files nằm trong `client/test/features/<feature>/`, mirror `lib/features/`.

**Mock pattern chuẩn cho service tests (mockito):**

```dart
@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late ProfileService service;

  setUp(() {
    mockDio = MockDio();
    service = ProfileService(dio: mockDio);
  });

  test('getProfile parses response', () async {
    when(mockDio.get<Map<String, dynamic>>('/profile/me'))
        .thenAnswer((_) async => Response(
              requestOptions: RequestOptions(path: '/profile/me'),
              data: {'user_id': 'u1', 'display_name': 'Test'},
              statusCode: 200,
            ));

    final profile = await service.getProfile();
    expect(profile.displayName, 'Test');
  });
}
```

Sau khi thêm `@GenerateMocks`, chạy code generation:

```bash
cd client && dart run build_runner build
```

---

## 8. Build & Deploy

### 8.1 Backend (FastAPI)

#### Môi trường dev (hiện tại)

```bash
cd backend
make run   # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Flag `--reload` chỉ dùng cho dev — tự động restart khi code thay đổi.
**Không dùng `--reload` trên production.**

#### Production — Uvicorn + Gunicorn

Cách chuẩn để chạy FastAPI production là dùng Gunicorn làm process manager
với Uvicorn workers:

```bash
cd backend

# Cài thêm gunicorn (chưa có trong requirements.txt)
.venv/bin/pip install gunicorn

# Chạy với 4 workers (thông thường: 2 × CPU cores + 1)
.venv/bin/gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

#### Production — Checklist trước khi deploy

```
[ ] Đặt DEBUG=false trong .env
[ ] DATABASE_URL trỏ đến PostgreSQL production
[ ] REDIS_URL trỏ đến Redis production
[ ] FIREBASE_CREDENTIALS_JSON chứa service account thật
[ ] S3_BUCKET và CDN_BASE_URL là giá trị thật
[ ] Chạy migration trước khi restart server
[ ] Không commit file .env vào git
```

#### Chạy migration trên production

Luôn chạy migration **trước** khi restart ứng dụng:

```bash
cd backend
.venv/bin/alembic upgrade head
# sau đó mới restart service
```

Kiểm tra trạng thái migration hiện tại:

```bash
.venv/bin/alembic current    # revision đang chạy
.venv/bin/alembic history    # toàn bộ lịch sử migration
```

#### Containerize với Docker (cần tạo)

Hiện tại repo **chưa có Dockerfile**. Khi cần containerize, tạo
`backend/Dockerfile` theo mẫu:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

Build và chạy:

```bash
cd backend
docker build -t dokat-backend:latest .
docker run -p 8000:8000 --env-file .env dokat-backend:latest
```

#### CI/CD backend (cần sửa)

File `.github/workflows/ci.yml` hiện trỏ sai vào `api-gateway/` — không
tồn tại. Để CI hoạt động với cấu trúc thực, cần cập nhật thành:

```yaml
on:
  push:
    paths: ["backend/**"]
  pull_request:
    paths: ["backend/**"]

defaults:
  run:
    working-directory: backend

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: make install
      - run: make lint
      - run: make test
```

---

### 8.2 Flutter Client

#### Setup Firebase (lần đầu sau clone)

Chạy FlutterFire CLI để tạo `lib/core/firebase_options.dart`:

```bash
# Cài FlutterFire CLI (một lần)
dart pub global activate flutterfire_cli

# Configure (cần Firebase project dokat-67ae7)
cd client
flutterfire configure --project=dokat-67ae7
```

Lệnh này tự tạo `android/app/google-services.json` và
`ios/Runner/GoogleService-Info.plist` — cả hai đều trong `.gitignore`.

| File | Đặt tại | Cách lấy |
|---|---|---|
| `google-services.json` | `client/android/app/` | `flutterfire configure` hoặc Firebase Console |
| `GoogleService-Info.plist` | `client/ios/Runner/` | `flutterfire configure` hoặc Firebase Console |

#### Build Android

```bash
# Dev — chạy trên emulator hoặc thiết bị
cd client && flutter run

# APK debug
cd client && flutter build apk --debug

# APK release
cd client && flutter build apk --release

# AAB (để upload Google Play)
cd client && flutter build appbundle
```

#### Build iOS

**Yêu cầu:** macOS + Xcode 15+ (App Store).

```bash
# Chạy trên iOS simulator
cd client && flutter run -d ios

# Release build (IPA)
cd client && flutter build ipa
```

#### Cấu hình `BASE_URL` cho từng môi trường

`BASE_URL` đọc từ `--dart-define` (mặc định `http://localhost:8000`):

```bash
# Dev — dùng default localhost
flutter run

# Staging
flutter run --dart-define=BASE_URL=https://api-staging.dokat.app

# Production build
flutter build apk --dart-define=BASE_URL=https://api.dokat.app
```

#### CI/CD Flutter

`.github/workflows/ci.yml` đã cập nhật với job `flutter` chạy:
1. `flutter pub get`
2. `flutter analyze`
3. `flutter test --coverage`

---

## 9. Các điểm cần lưu ý

| Vấn đề | Chi tiết |
|---|---|
| `README.md` trống | Dùng tài liệu này và `AGENT.md` thay thế |
| Flutter SDK chưa cài | Cài Flutter 3.22+ từ flutter.dev trước khi chạy bất kỳ `flutter` command nào |
| Firebase config chưa có | Chỉ cần nếu `AUTH_MODE=firebase`. Standalone mode không cần. Nếu dùng Firebase: chạy `flutterfire configure --project=dokat-67ae7` |
| iOS build cần Xcode | macOS + Xcode 15+ từ App Store. `flutter run -d ios` sẽ fail đến khi Xcode cài xong |
| `JWT_SECRET_KEY` trong prod | Phải thay giá trị `change-me-in-production` bằng string ngẫu nhiên ≥ 32 ký tự. Dùng: `openssl rand -hex 32` |
| `FIREBASE_CREDENTIALS_JSON` | Chỉ bắt buộc khi `AUTH_MODE=firebase`. Standalone mode để rỗng là ổn |
| Database URL format | Backend dùng `postgresql+asyncpg://` cho runtime, nhưng Alembic migrations dùng sync driver (psycopg2) — `env.py` tự chuyển đổi |
| MinIO bucket public | `minio-init` service tự tạo bucket `pawsnap` với policy `public` khi `docker compose up`. Nếu chạy manual cần tạo thủ công |
| CloudBeaver host trong Docker | Dùng hostname `postgres` (tên service), không phải `localhost`, khi kết nối từ CloudBeaver vào PostgreSQL |
| SQLite trong tests | Unit tests dùng SQLite in-memory (không cần Postgres). Integration tests mới cần Postgres thực |
| `client-rn/` | React Native cũ — giữ làm reference, không cần maintain. `node_modules/` bị gitignore |

---

## 10. Tài liệu tham khảo

### Tài liệu nội bộ

| Tài liệu | Mục đích |
|---|---|
| [`specs/PRD.md`](specs/PRD.md) | Product Requirements Document — source of truth |
| [`AGENT.md`](AGENT.md) | Context tổng quan cho AI agent (và member mới) |
| [`.cursor/rules/sdd.mdc`](.cursor/rules/sdd.mdc) | SDD rules bắt buộc |
| [`.cursor/rules/karpathy-guideline.mdc`](.cursor/rules/karpathy-guideline.mdc) | Coding guidelines |

### Specs theo feature

| Feature | Thư mục |
|---|---|
| F01 — Authentication & Guest Mode | [`specs/f01-authentication/`](specs/f01-authentication/) |
| F02 — Owner Profile & Pet Profile | [`specs/f02-profile/`](specs/f02-profile/) |
| F03 — Social Graph (QR) | [`specs/f03-social-graph/`](specs/f03-social-graph/) |
| F04 — Capture Ảnh + AI Validation | [`specs/f04-capture/`](specs/f04-capture/) |
| F05 — Gửi Ảnh (Multi-Recipient) | [`specs/f05-send-photo/`](specs/f05-send-photo/) |
| F06 — Feed & App View | [`specs/f06-feed/`](specs/f06-feed/) |
| F07 — Seen By | [`specs/f07-seen-by/`](specs/f07-seen-by/) |
| F08 — History / Timeline | [`specs/f08-history/`](specs/f08-history/) |
| F09 — Notification System | [`specs/f09-notifications/`](specs/f09-notifications/) |
| F10 — Settings | [`specs/f10-settings/`](specs/f10-settings/) |
| F11 — Location & Time Metadata | [`specs/f11-location-metadata/`](specs/f11-location-metadata/) |
| F12 — Standalone Infrastructure | [`specs/f12-standalone-infra/`](specs/f12-standalone-infra/) |

### Stack references

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Alembic migrations](https://alembic.sqlalchemy.org/en/latest/)
- [React Native docs](https://reactnative.dev/)
- [React Navigation](https://reactnavigation.org/)
- [Zustand](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [Firebase Admin Python SDK](https://firebase.google.com/docs/admin/setup)
- [Firebase React Native SDK](https://rnfirebase.io/)
- [APScheduler](https://apscheduler.readthedocs.io/en/stable/)
