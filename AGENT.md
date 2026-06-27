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
- **Backend:** FastAPI (Python) + PostgreSQL + Firebase Auth + S3 +
  CloudFront
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
| Auth     | Firebase Auth (Anonymous + OAuth Apple/Google/Facebook) via FlutterFire |
| Backend  | FastAPI, Uvicorn, SQLAlchemy (async), Alembic, Pydantic Settings |
| Database | PostgreSQL (asyncpg) |
| Cache    | Redis (QR OTP, TTL 5 phút) |
| Storage  | AWS S3 + CloudFront CDN |
| Push     | Firebase Cloud Messaging (FCM) + APNs (firebase_messaging) |
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
| F01 | Authentication & Guest Mode      | P0 | Implemented (Flutter + backend) |
| F02 | Owner Profile & Pet Profile      | P0 | Implemented (Flutter + backend) |
| F03 | Social Graph — Kết bạn qua QR    | P0 | Implemented (Flutter + backend) |
| F04 | Capture Ảnh + AI Validation      | P0 | Implemented (Flutter) |
| F05 | Gửi Ảnh (Multi-Recipient)        | P0 | Implemented (Flutter) |
| F06 | Feed & App View                  | P0 | Implemented (Flutter) |
| F07 | Seen By                          | P1 | Implemented (Flutter) |
| F08 | History / Timeline (1 ngày)      | P1 | Implemented (Flutter) |
| F09 | Notification System              | P1 | Implemented (Flutter) |
| F10 | Settings                         | P1 | Implemented (Flutter) |
| F11 | Location & Time Metadata         | P2 | Implemented (Flutter) |

---

## 7. Quyết định kiến trúc cần biết

- **Auth flow:** Firebase Anonymous Auth khởi tạo guest ngay khi mở app,
  sau đó link OAuth provider mà không mất dữ liệu. Backend verify Firebase
  ID Token ở mỗi request qua `FirebaseAuthMiddleware`.
- **Kết bạn qua QR:** QR OTP server-side, lưu Redis với TTL 5 phút,
  single-use, instant mutual friendship; hard limit 20 bạn.
- **Backend async:** SQLAlchemy async + asyncpg. Business logic đặt trong
  `app/services/`, routers chỉ điều phối.
- **AI validation:** chạy hoàn toàn on-device, không gọi API server.
- **Media retention:** ảnh free user ẩn sau 24h (record vẫn lưu).

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

---

## 8. Coding standards

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
