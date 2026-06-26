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
| Mobile client | React Native 0.76 + TypeScript 5.5 |
| State management | Zustand 5 |
| Navigation | React Navigation 7 |
| Auth | Firebase Auth (Anonymous + OAuth Google/Apple/Facebook) |
| Backend | FastAPI (Python) + Uvicorn |
| Database | PostgreSQL (SQLAlchemy async + asyncpg) |
| Migrations | Alembic |
| Cache | Redis (QR OTP) |
| Storage | AWS S3 + CloudFront CDN |
| Push notifications | Firebase Cloud Messaging (FCM) + APScheduler |
| AI validation | On-device (TFLite / CoreML) — không gọi server |
| Test (backend) | pytest + httpx + moto + fakeredis |
| Test (client) | Jest 29 + @testing-library/react-native |

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

- Python 3.11+ (dự án dùng 3.14 locally)
- Node.js 20+ và npm
- PostgreSQL 14+
- Redis 7+
- Firebase project (để lấy credentials)

### Bước 1 — Clone và cài đặt

```bash
git clone <repo-url>
cd ME

# Backend
cd backend
make install        # tạo .venv + pip install -r requirements.txt
cd ..

# Client
npm install
```

### Bước 2 — Cấu hình biến môi trường backend

Tạo file `backend/.env` (copy mẫu dưới đây):

```dotenv
# Firebase Admin SDK — bắt buộc cho production
# Lấy từ Firebase Console > Project Settings > Service Accounts
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/me_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3 (dùng moto mock khi test, cần real values khi chạy thực)
S3_BUCKET=pawsnap
CDN_BASE_URL=https://cdn.pawsnap.app
AWS_REGION=us-east-1

# Deep link base URL
DEEP_LINK_BASE=https://petapp.example.com

# Debug mode
DEBUG=false
```

> **Lưu ý:** Không có file `.env.example` trong repo — hãy tạo file `.env`
> từ bảng trên và nhờ team trưởng cung cấp giá trị thực.

### Bước 3 — Tạo database và chạy migrations

```bash
# Tạo database (chạy một lần)
createdb me_dev

cd backend
make migrate        # alembic upgrade head
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

### Client — Cấu trúc `client/`

```
client/
├── App.tsx              # Root component (Firebase init + Navigation)
├── index.js             # Entry point (AppRegistry)
├── package.json
├── ios/                 # iOS native shell (Xcode project)
│   ├── Dokat/
│   │   └── GoogleService-Info.plist  (gitignore'd — tự đặt)
│   ├── Dokat.xcodeproj
│   └── Podfile
├── android/             # Android native shell
│   └── app/
│       └── google-services.json  (gitignore'd — tự đặt)
└── src/
├── components/          # UI components tái sử dụng
│   ├── auth/            # AuthPromptModal, ...
│   ├── camera/          # CameraPreview, ...
│   ├── profile/         # PetProfileCard, ...
│   └── *.tsx            # FeedItem, SeenByList, NotificationPreferenceSection,...
├── screens/             # Màn hình (AddFriend, FriendList, QRScanner, ...)
├── services/            # HTTP clients → backend API
│   ├── AuthService.ts   # Firebase Auth + getIdToken()
│   ├── SocialService.ts # /friends endpoints
│   ├── FeedService.ts   # /feed
│   ├── PostService.ts   # /posts
│   └── ...
├── stores/              # Zustand stores (useAuthStore, useProfileStore, ...)
└── __tests__/           # Jest tests (mirror theo domain)
    ├── auth/
    ├── profile/
    ├── social/
    ├── feed/
    ├── notifications/
    └── ...
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

- Follow style hiện có của codebase
- Test với Jest + @testing-library/react-native

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

### Client

```bash
# Từ thư mục client/
cd client
npm test                 # chạy toàn bộ Jest tests
npm run test:list        # liệt kê các test files
```

Test files nằm trong `client/src/__tests__/<domain>/`. Số lượng hiện tại: 42 test
suites, 170 tests.

**Mock pattern chuẩn cho service tests:**

```typescript
jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { getIdToken: jest.fn().mockResolvedValue('mock-token') },
}));

const mockFetch = jest.fn();
(globalThis as any).fetch = mockFetch;
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

### 8.2 Frontend — React Native

#### Trạng thái hiện tại ✅

React Native app shell đã được khởi tạo và cấu hình xong:

```
ME/
├── client/                        ← Toàn bộ React Native mobile app
│   ├── App.tsx                    ← Root component (Firebase init + Navigation)
│   ├── index.js                   ← Entry point (AppRegistry)
│   ├── ios/
│   │   ├── Dokat/
│   │   │   ├── GoogleService-Info.plist  ← Firebase iOS config (gitignore'd)
│   │   │   ├── AppDelegate.swift
│   │   │   └── Info.plist         ← Bundle ID: com.carbonix.dokat
│   │   ├── Dokat.xcodeproj
│   │   └── Podfile                ← Firebase pods đã được thêm
│   └── android/
│       └── app/
│           └── google-services.json  ← cần thêm thủ công (gitignore'd)
├── backend/                       ← FastAPI backend
├── specs/                         ← SDD specs (shared)
└── demo/                          ← Expo web demo
```

#### Cấu hình Firebase Native

| File | Lấy từ | Đặt tại | Trạng thái |
|---|---|---|---|
| `GoogleService-Info.plist` | Firebase Console → Project `dokat-67ae7` → iOS | `client/ios/Dokat/` | ✅ Đã có |
| `google-services.json` | Firebase Console → Project `dokat-67ae7` → Android | `client/android/app/` | ⏳ Cần thêm |

Cả hai file đều trong `.gitignore` — mỗi dev phải tự đặt sau khi clone.

#### Build iOS

**Yêu cầu:** macOS + **Xcode 15+** (tải từ App Store) + CocoaPods.

```bash
# Bước 1 — Cài CocoaPods (một lần)
brew install cocoapods

# Bước 2 — Install native pods
cd client/ios && pod install && cd ../..

# Bước 3 — Chạy trên simulator
cd client && npx react-native run-ios
# hoặc chỉ định device cụ thể:
npx react-native run-ios --simulator "iPhone 16 Pro"

# Production build — Xcode → Product → Archive
# hoặc dùng Fastlane (khuyến nghị cho CI)
```

> **Lưu ý:** `pod install` yêu cầu Xcode đầy đủ (không chỉ Command Line Tools).
> Tải Xcode từ App Store (~10GB) trước khi chạy lệnh này.

#### Build Android

Yêu cầu: Android Studio + JDK 17.

```bash
# Dev build (chạy trên emulator hoặc thiết bị thật)
cd client && npx react-native run-android

# Release APK (debug signing)
cd client/android && ./gradlew assembleRelease

# Release AAB (để upload Google Play)
cd client/android && ./gradlew bundleRelease
```

> **Release signing:** cần `client/android/app/keystore.jks` và cấu hình
> `client/android/gradle.properties`. Hỏi team trưởng để lấy keystore.

#### Cấu hình `BASE_URL` cho từng môi trường

Các service trong `client/src/services/` hiện hardcode:

```typescript
const BASE_URL = 'http://localhost:8000';
```

Trước khi build production, thay bằng URL backend thực. Cách chuẩn là dùng
biến môi trường qua `react-native-config` hoặc build flavors (Android) /
schemes (iOS):

```bash
npm install react-native-config
```

Sau đó tạo `.env.production`:

```dotenv
API_BASE_URL=https://api.dokat.app
```

Và dùng trong service:

```typescript
import Config from 'react-native-config';
const BASE_URL = Config.API_BASE_URL ?? 'http://localhost:8000';
```

#### CI/CD frontend (cần thêm vào ci.yml)

```yaml
  test-client:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd client && npm ci
      - run: cd client && npm test -- --ci --coverage
```

---

### 8.3 Tóm tắt trạng thái build hiện tại

| Thành phần | Dev local | Production build | Ghi chú |
|---|---|---|---|
| Backend API | `make run` | Gunicorn (cần thêm) | Không cần sửa code |
| Backend Docker | — | Dockerfile chưa tồn tại | Cần tạo |
| Backend CI | — | CI trỏ sai path | Cần sửa `ci.yml` |
| Backend migrations | `make migrate` | `alembic upgrade head` | Chạy trước khi restart |
| Client (React Native) | — | Chưa có app shell | Cần khởi tạo RN project |
| Client iOS | — | Xcode Archive | Cần app shell + pod install |
| Client Android | — | `./gradlew bundleRelease` | Cần app shell + keystore |
| Client CI | — | Chưa có | Cần thêm job vào `ci.yml` |

---

## 9. Các điểm cần lưu ý

| Vấn đề | Chi tiết |
|---|---|
| `README.md` trống | Dùng tài liệu này và `AGENT.md` thay thế |
| CI không hoạt động | `.github/workflows/ci.yml` trỏ tới `api-gateway/` — thư mục không tồn tại. Xem §8.1 để biết cách sửa |
| Client cần Xcode | RN app shell đã setup trong `client/`. Cần cài Xcode từ App Store → `cd client/ios && pod install` → `cd client && npx react-native run-ios` |
| `FIREBASE_CREDENTIALS_JSON` | Bắt buộc cho backend production. Để dev local, có thể dùng Application Default Credentials (`gcloud auth application-default login`) |
| Database URL format | Backend dùng `postgresql+asyncpg://` cho runtime, nhưng Alembic migrations dùng sync driver (psycopg2) — `env.py` tự chuyển đổi |
| SQLite trong tests | Unit tests dùng SQLite in-memory (không cần Postgres). Integration tests mới cần Postgres thực |
| AGENT.md có thể lỗi thời | Bảng tiến độ trong `AGENT.md` không phản ánh trạng thái thực — nhiều feature (F05–F10) đã implement backend nhưng AGENT.md vẫn ghi "Chỉ có requirements" |

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
