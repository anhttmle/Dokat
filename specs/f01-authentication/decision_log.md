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

## DL-003: pytest-asyncio mode = auto

**Date:** 2026-06-18
**Context:** Backend dùng async FastAPI; test cần async fixtures.
**Decision:** Đặt `asyncio_mode = "auto"` trong `pyproject.toml`
để tránh phải thêm `@pytest.mark.asyncio` ở mỗi test.
**Consequence:** Tất cả async test functions chạy tự động.
