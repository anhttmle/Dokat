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

## DL-003: pytest-asyncio mode = auto

**Date:** 2026-06-18
**Context:** Backend dùng async FastAPI; test cần async fixtures.
**Decision:** Đặt `asyncio_mode = "auto"` trong `pyproject.toml`
để tránh phải thêm `@pytest.mark.asyncio` ở mỗi test.
**Consequence:** Tất cả async test functions chạy tự động.
