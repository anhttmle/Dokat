# AGENT.md — Hướng dẫn cho AI Agent

Tài liệu này là điểm khởi đầu cho mọi AI agent làm việc trong workspace
này. Đọc kỹ trước khi thực hiện bất kỳ thay đổi nào.

---

## 1. Tổng quan dự án

**Dokat** là mạng xã hội dành riêng cho chủ thú cưng (chó/mèo), cho phép
gửi ảnh thú cưng đến bạn bè theo thời gian thực — tương tự Locket, nhưng
chỉ tập trung vào pet content (không có ảnh người). MVP nhắm thị trường
Việt Nam.

- **Platform:** React Native (iOS + Android)
- **Backend:** FastAPI (Python) + PostgreSQL + Firebase Auth + S3 +
  CloudFront
- **Tài liệu nguồn:** [`specs/PRD.md`](specs/PRD.md) là source of truth cho
  yêu cầu sản phẩm.

---

## 2. Cấu trúc monorepo

```
.
├── src/              # React Native client (TypeScript)
├── backend/          # FastAPI Python backend
├── specs/            # Spec-Driven Development docs (PRD + F01–F11)
├── __mocks__/        # Jest mocks (Firebase, AsyncStorage)
├── .cursor/rules/    # Coding rules (SDD + Karpathy guidelines)
└── .github/workflows/ # CI
```

### Client (`src/`)

```
src/
├── components/   # UI components (auth, camera, profile, ...)
├── screens/      # Màn hình (AddFriend, FriendList, QRScanner, Profile, ...)
├── services/     # AuthService, ProfileService, SocialService, ai/PetAIService
├── stores/       # Zustand stores (useAuthStore, useProfileStore, ...)
└── __tests__/    # Test mirror theo domain (auth, profile, social)
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
| Client   | React Native 0.76, React 18.3, TypeScript 5.5, Zustand 5, React Navigation 7 |
| Auth     | Firebase Auth (Anonymous + OAuth Apple/Google/Facebook) |
| Backend  | FastAPI, Uvicorn, SQLAlchemy (async), Alembic, Pydantic Settings |
| Database | PostgreSQL (asyncpg) |
| Cache    | Redis (QR OTP, TTL 5 phút) |
| Storage  | AWS S3 + CloudFront CDN |
| Push     | Firebase Cloud Messaging (FCM) + APNs |
| AI       | On-device model (TFLite / CoreML) — client-side, không gọi server |
| Test     | Jest + Testing Library (client); pytest, httpx, moto, fakeredis (backend) |

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

### Client (root)

```bash
npm test           # chạy Jest
npm run test:list  # liệt kê các test files
```

---

## 6. Tiến độ feature

| ID  | Feature                          | Priority | Trạng thái |
|-----|----------------------------------|----------|------------|
| F01 | Authentication & Guest Mode      | P0 | Implemented (client + backend) |
| F02 | Owner Profile & Pet Profile      | P0 | Implemented (client + backend) |
| F03 | Social Graph — Kết bạn qua QR    | P0 | Implemented (client + backend) |
| F04 | Capture Ảnh + AI Validation      | P0 | Chỉ có requirements |
| F05 | Gửi Ảnh (Multi-Recipient)        | P0 | Chỉ có requirements |
| F06 | Feed & App View                  | P0 | Chỉ có requirements |
| F07 | Seen By                          | P1 | Chỉ có requirements |
| F08 | History / Timeline (1 ngày)      | P1 | Chỉ có requirements |
| F09 | Notification System              | P1 | Chỉ có requirements |
| F10 | Settings                         | P1 | Chỉ có requirements |
| F11 | Location & Time Metadata         | P2 | Chỉ có requirements |

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
- CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) đang trỏ tới
  thư mục `api-gateway/` — không tồn tại. Backend thực tế ở `backend/`,
  nên CI hiện không chạy cho code hiện có.

---

## 8. Coding standards

- **Python (backend):** PEP 8 / PEP 257, 4 spaces, line ≤ 79 ký tự, một
  class/function chính mỗi file. Format bằng `black` + `isort`, lint bằng
  `ruff`, type-check bằng `mypy`. Import order: stdlib → third-party →
  local. Không hardcode secrets — dùng `.env` / pydantic settings.
- **TypeScript (client):** theo style hiện có của codebase, test với Jest.
- **Nguyên tắc chung:** DRY, KISS, YAGNI, SOLID. Tránh nesting sâu
  (≤ 2–3 cấp). Đặt tên rõ ràng, docstring cho public API.
- Chi tiết đầy đủ xem [`.cursor/rules/`](.cursor/rules/).
