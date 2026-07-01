# AGENT.md — Hướng dẫn cho AI Agent

Tài liệu này là điểm khởi đầu cho mọi AI agent làm việc trong workspace
này. Đọc kỹ trước khi thực hiện bất kỳ thay đổi nào.

---

## 1. Tổng quan dự án

**Dokat** là mạng xã hội dành riêng cho chủ thú cưng (chó/mèo), cho phép
gửi ảnh thú cưng đến bạn bè theo thời gian thực — tương tự Locket, nhưng
chỉ tập trung vào pet content (không có ảnh người). MVP nhắm thị trường
Việt Nam.

- **Platform:** Flutter (iOS + Android)
- **Backend:** FastAPI (Python) + PostgreSQL + JWT Auth (default) hoặc
  Firebase Auth (optional) + MinIO (default) hoặc S3 + CloudFront
  (optional)
- **Tài liệu nguồn:** [`specs/PRD.md`](specs/PRD.md) là source of truth cho
  yêu cầu sản phẩm.
- **Migration spec:** [`specs/flutter-migration/`](specs/flutter-migration/)
  cho quyết định kiến trúc Flutter.

---

## 2. Cấu trúc monorepo

```
.
├── client/           # Flutter mobile app (Dart) — platform mới
├── client-rn/        # React Native cũ (TypeScript) — reference only
├── backend/          # FastAPI Python backend
├── specs/            # Spec-Driven Development docs (PRD + F01–F11 + flutter-migration)
├── demo/             # Expo web demo (standalone, không phụ thuộc client/)
├── .cursor/rules/    # Coding rules (SDD + Karpathy guidelines)
└── .github/workflows/ # CI
```

### Client Flutter (`client/`)

```
client/
├── pubspec.yaml      # Flutter dependencies
├── lib/
│   ├── main.dart     # Entry point (Firebase.initializeApp + runApp)
│   ├── app.dart      # DokatApp widget (ProviderScope + go_router)
│   ├── core/         # api_client.dart, constants.dart, firebase_options.dart
│   ├── features/     # F01–F11, mỗi feature có data/domain/presentation/
│   └── shared/       # Shared widgets + utils
├── test/             # Flutter tests (mirror lib/)
├── web/              # Flutter web shell (index.html, manifest)
├── Dockerfile        # Multi-stage: flutter build web → nginx
├── Makefile          # run-web, build-web, docker-build
├── android/          # Android native shell
│   └── app/
│       └── google-services.json  (gitignore'd — tự đặt)
└── ios/              # iOS native shell
    └── Runner/
        └── GoogleService-Info.plist  (gitignore'd — tự đặt)
```

### Client RN (legacy, `client-rn/`)

```
client-rn/
├── App.tsx         # Root component RN cũ (reference only)
├── src/            # Services, screens, stores, tests gốc
└── package.json
```

### Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py        # FastAPI entry + router registration
│   ├── core/          # config, firebase, redis
│   ├── middleware/    # FirebaseAuthMiddleware
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # API routes theo feature (auth, profile, pets, friends)
│   ├── schemas/       # Pydantic schemas
│   └── services/      # Business logic (giữ logic ra khỏi routers)
├── alembic/           # DB migrations
└── tests/             # pytest (unit + integration + migrations)
```

---

## 3. Tech stack

| Layer    | Công nghệ |
|----------|-----------|
| Client   | Flutter 3.22+, Dart 3.4+, Riverpod 2, go_router 14, Dio 5 |
| Auth     | **JWT mode** (default, standalone): `POST /auth/token` với `device_id`; hoặc Firebase Auth khi `AUTH_MODE=firebase` |
| Backend  | FastAPI, Uvicorn, SQLAlchemy (async), Alembic, Pydantic Settings |
| Database | PostgreSQL (asyncpg) |
| Cache    | Redis (QR OTP, TTL 5 phút) |
| Storage  | **MinIO** (default, standalone) hoặc AWS S3 + CloudFront CDN khi `STORAGE_BACKEND=s3` |
| Push     | Firebase Cloud Messaging (FCM) — graceful no-op khi Firebase không cấu hình |
| AI       | On-device model (tflite_flutter) — client-side, không gọi server |
| Test     | flutter_test + mockito (client); pytest, httpx, moto, fakeredis (backend) |

---

## 4. Quy trình phát triển (SDD — bắt buộc)

Dự án theo **Spec-Driven Development**. Luôn tuân thủ
[`.cursor/rules/sdd.mdc`](.cursor/rules/sdd.mdc):

1. **Đọc spec trước khi viết code.** Spec nằm ở
   `specs/<feature>/` (`requirements.md`, `design.md`, `tasks.md`).
   Nếu chưa có spec, DỪNG lại và yêu cầu user tạo spec trước.
2. **Chỉ implement đúng task được giao** — một task tại một thời điểm.
3. **TDD:** viết test TRƯỚC khi implementation.
4. **Chỉ làm những gì spec nêu rõ.** Không thêm tính năng "nice to have",
   không over-engineer, không thêm security layer nếu spec không yêu cầu.
5. **Decision log:** mọi quyết định thiết kế ngoài spec phải ghi vào
   `specs/<feature>/decision_log.md`.
6. Khi phân vân, làm ÍT hơn chứ không nhiều hơn.

---

## 5. Cách chạy & test

### Backend ([`backend/Makefile`](backend/Makefile))

```bash
cd backend
make install          # tạo .venv + cài requirements.txt
make run              # uvicorn app.main:app --reload --port 8000
make migrate          # alembic upgrade head
make test             # pytest (bỏ qua tests/integration)
make test-integration # chạy tests/integration/
make lint             # ruff check + black --check
```

### Client Flutter (`client/`)

```bash
# Chạy tests
cd client && flutter test

# Chạy Android (cần Android Studio + emulator)
cd client && flutter run

# Chạy iOS (cần Xcode từ App Store)
cd client && flutter run -d ios

# Lint & analyze
cd client && flutter analyze

# Build APK debug
cd client && flutter build apk --debug
```

### Setup Firebase cho Flutter (lần đầu)

```bash
# Cài FlutterFire CLI
dart pub global activate flutterfire_cli

# Configure (cần Firebase project dokat-67ae7)
cd client && flutterfire configure --project=dokat-67ae7
```

### Client RN cũ (reference, `client-rn/`)

```bash
cd client-rn
npm test           # chạy Jest (reference)
```

### Demo web (Expo — không cần Xcode)

```bash
cd demo && npx expo start --web
# mở http://localhost:8081
```

---

## 6. Tiến độ feature

| ID  | Feature                          | Priority | Trạng thái |
|-----|----------------------------------|----------|------------|
| F01 | Authentication & Guest Mode      | P0 | Integrated (Flutter + backend, Firebase live) |
| F02 | Owner Profile & Pet Profile      | P0 | Integrated (Flutter + backend, Firebase live) |
| F03 | Social Graph — Kết bạn qua QR    | P0 | Integrated (Flutter + backend, Firebase live) |
| F04 | Capture Ảnh + AI Validation      | P0 | Implemented (Flutter client-only) |
| F05 | Gửi Ảnh (Multi-Recipient)        | P0 | Integrated (Flutter + backend, Firebase live) |
| F06 | Feed & App View                  | P0 | Integrated (Flutter + backend, Firebase live) |
| F07 | Seen By                          | P1 | Integrated (Flutter + backend, Firebase live) |
| F08 | History / Timeline (1 ngày)      | P1 | Implemented (Flutter — cần verify contract) |
| F09 | Notification System              | P1 | Implemented (Flutter — cần verify contract) |
| F10 | Settings                         | P1 | Integrated (Flutter + backend, Firebase live) |
| F11 | Location & Time Metadata         | P2 | Implemented (Flutter client-only, stub null) |

---

## 7. Client ↔ Backend API contract (đã verified, 2026-06-27)

> Backend là **source of truth**. Mọi field name, response shape phải khớp
> với `backend/app/schemas/`. Xem `specs/<feature>/decision_log.md` để biết
> lý do từng quyết định.

### Flutter service map

| Flutter service | File | Backend prefix |
|-----------------|------|----------------|
| `AuthService` | `features/auth/data/auth_service.dart` | `POST /auth/session`, `/auth/link` |
| `ProfileService` | `features/profile/data/profile_service.dart` | `/profile/me` |
| `PetService` | `features/profile/data/pet_service.dart` | `/pets` |
| `SocialService` | `features/social/data/social_service.dart` | `/friends` |
| `SendService` | `features/send/data/send_service.dart` | `/posts` |
| `FeedService` | `features/feed/data/feed_service.dart` | `/feed` |
| `SeenService` | `features/seen/data/seen_service.dart` | `/posts/{id}/seen` |
| `HistoryService` | `features/history/data/history_service.dart` | `/history` |
| `NotificationService` | `features/notifications/data/notification_service.dart` | `/notifications` |
| `SettingsService` | `features/settings/data/settings_service.dart` | `/users` |
| `LocationService` | `features/location/data/location_service.dart` | client-only (stub null) |

### Response shape quan trọng (hay bị nhầm)

```
GET  /pets            → { pets: [...] }           (không phải list thẳng)
GET  /friends         → { friends: [...], total }
GET  /users/block     → { blocked: [...], total }
GET  /feed            → { items: [...], next_cursor }
GET  /pets/{id}/photos→ { pet_id, photos: [{photo_id, cdn_url, taken_at}], ... }
GET  /posts/{id}/seen-by → { post_id, seen_count, viewers: [{user_id, display_name, ...}] }
POST /posts/upload-url→ { upload_url, object_key, cdn_url, expires_in }
POST /auth/session    → { user_id, is_anonymous, providers, display_name, avatar_url }
```

### Field name dễ nhầm

| Endpoint | Field đúng | Field SAI (cũ) |
|----------|-----------|----------------|
| `POST /friends/qr/generate` response | `token` | ~~`otp`~~ |
| `POST /friends/qr/scan` request | `token` | ~~`otp`~~ |
| `POST /posts` request | `s3_key`, `cdn_url` | ~~`image_url`~~ |
| `POST /posts` request | `latitude`, `longitude` (flat) | ~~`location: {lat, lng}`~~ |
| `GET /feed` response | `cdn_url`, `seen` | ~~`image_url`, `seen_by_me`~~ |
| `POST /users/block` request | `user_id` | ~~`target_user_id`~~ |
| `POST /users/report` request | `user_id` | ~~`target_user_id`~~ |
| `PATCH /pets/{id}/link-photo` request | `photo_id` (UUID) | ~~`photo_url`~~ |

### Luồng upload ảnh (F05 — quan trọng)

```
1. POST /posts/upload-url → { upload_url, object_key, cdn_url }
2. PUT <upload_url> (binary, S3 presigned) — không trả body
3. POST /posts { s3_key: object_key, cdn_url, recipient_ids, latitude?, longitude? }
```

`CaptureService.uploadImage()` chỉ thực hiện bước 2 (void). CDN URL lấy từ
bước 1, không strip-parse từ presigned URL.

### Auth header

Mọi request đính kèm Firebase ID Token:

```
Authorization: Bearer <firebase_id_token>
```

`api_client.dart` inject token tự động qua Dio interceptor. Backend verify
token qua `FirebaseAuthMiddleware` rồi inject `request.state.firebase_uid`.

---

## 8. Quyết định kiến trúc cần biết

- **Auth flow:** Firebase Anonymous Auth khởi tạo guest ngay khi mở app,
  sau đó link OAuth provider mà không mất dữ liệu. Backend verify Firebase
  ID Token ở mỗi request qua `FirebaseAuthMiddleware`.
- **Kết bạn qua QR:** QR OTP server-side, lưu Redis với TTL 5 phút,
  single-use, instant mutual friendship; hard limit 20 bạn.
- **Backend async:** SQLAlchemy async + asyncpg. Business logic đặt trong
  `app/services/`, routers chỉ điều phối.
- **AI validation:** chạy hoàn toàn on-device, không gọi API server.
- **Media retention:** ảnh free user ẩn sau 24h (record vẫn lưu).

### F12 — Standalone mode (thêm 2026-06-30)

Hệ thống hỗ trợ chạy hoàn toàn không phụ thuộc Firebase/AWS:

| Env var | Giá trị | Hành vi |
|---------|---------|---------|
| `AUTH_MODE` | `jwt` | Backend tự cấp JWT, không cần Firebase |
| `AUTH_MODE` | `firebase` (default) | Firebase Auth như cũ |
| `STORAGE_BACKEND` | `minio` | Upload qua MinIO local |
| `STORAGE_BACKEND` | `s3` (default) | AWS S3 như cũ |

**Để chạy standalone:**
```bash
# Option 1: docker compose
docker compose up   # postgres + redis + minio + backend + client (:8080)
# Đặt PUBLIC_HOST trong .env (IP LAN) trước khi truy cập từ thiết bị ngoài host.

# Option 2: local
AUTH_MODE=jwt JWT_SECRET_KEY=your-secret STORAGE_BACKEND=minio \
  MINIO_ENDPOINT_URL=http://localhost:9000 \
  make run
```

**JWT flow (F12):**
```
Client: POST /auth/token { device_id }
Backend: upsert user (firebase_uid=device_id), return JWT
Client: Bearer <JWT> on all requests
```

**New files (F12):**
- `backend/app/core/jwt_auth.py` — `create_token`, `verify_token`
- `backend/app/routers/auth_jwt.py` — `POST /auth/token`
- `docker-compose.yml` — full standalone stack
- `backend/.env.example` — tất cả env vars documented
- `specs/f12-standalone-infra/` — requirements, design, tasks
- `client/lib/core/session_storage.dart` — `SessionStorage` abstraction
  (web → `SharedPreferences`; mobile → `FlutterSecureStorage`)

**Storage platform split (DL-F12-09):**
`flutter_secure_storage_web` cần Web Crypto API — chỉ hoạt động trên
`https://` hoặc `localhost`. Deploy qua `http://<LAN-IP>` trả lỗi
"Null check operator on null value" ngay khi khởi app. Fix: web dùng
`_SharedPreferencesStorage`, inject qua `sessionStorageProvider` (Riverpod).

### Gap đã biết (cần lưu ý, không tự ý sửa nếu không được yêu cầu)

- `README.md` ở root hiện trống.
- CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) đã được cập
  nhật cho Flutter. Backend CI vẫn cần fix path.
- iOS build cần Xcode (macOS + App Store). `flutter run -d ios` sẽ thất bại
  cho đến khi Xcode được cài.
- `client/android/app/google-services.json` chưa có — chạy
  `flutterfire configure` hoặc lấy thủ công từ Firebase Console
  (project `dokat-67ae7`).
- `client/ios/Runner/GoogleService-Info.plist` chưa có — tương tự trên.
- Flutter SDK chưa cài — cần cài Flutter 3.22+ trước khi chạy bất kỳ
  Flutter command nào.
- `client-rn/` giữ nguyên làm reference; không cần maintain.
- **F08 (`history_service.dart`) và F09 (`notification_service.dart`) chưa
  được verify contract với backend** — cần rà soát tương tự F01–F07/F10
  trước khi chạy thật.
- **F11 (`location_service.dart`):** `getCurrentPayload()` trả `null` (stub).
  Tích hợp `geolocator` package thực sự là task riêng chưa làm.

---

## 9. Coding standards

- **Python (backend):** PEP 8 / PEP 257, 4 spaces, line ≤ 79 ký tự, một
  class/function chính mỗi file. Format bằng `black` + `isort`, lint bằng
  `ruff`, type-check bằng `mypy`. Import order: stdlib → third-party →
  local. Không hardcode secrets — dùng `.env` / pydantic settings.
- **Dart (client Flutter):** `dart format`, `flutter analyze` (lint rules
  trong `analysis_options.yaml`). snake_case files, lowerCamelCase vars,
  UpperCamelCase classes. Test với `flutter_test` + `mockito`.
- **Nguyên tắc chung:** DRY, KISS, YAGNI, SOLID. Tránh nesting sâu
  (≤ 2–3 cấp). Đặt tên rõ ràng, docstring cho public API.
- Chi tiết đầy đủ xem [`.cursor/rules/`](.cursor/rules/).
