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

## DL-003: pytest-asyncio mode = auto

**Date:** 2026-06-18
**Context:** Backend dùng async FastAPI; test cần async fixtures.
**Decision:** Đặt `asyncio_mode = "auto"` trong `pyproject.toml`
để tránh phải thêm `@pytest.mark.asyncio` ở mỗi test.
**Consequence:** Tất cả async test functions chạy tự động.
