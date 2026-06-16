# API Gateway — Tasks

**Project:** Dokat  
**Feature:** API Gateway  
**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** Ready  

**Requirements:** [requirements.md](./requirements.md)  
**Design:** [design.md](./design.md)  
**Decisions:** [decision_log.md](./decision_log.md)

---

## Cách dùng

1. Làm **tuần tự theo số task** — task sau phụ thuộc task trước trừ khi ghi rõ
   có thể song song.
2. Mỗi task: **viết test trước (TDD)** → implement tối thiểu để test pass →
   chạy `pytest` + `ruff`.
3. Đánh dấu `[x]` khi task hoàn thành và test liên quan pass.
4. **Không** implement ngoài scope task đang làm.
5. Một agent/session chỉ xử lý **một task** mỗi lần (theo SDD rules).

---

## Task overview

| Task | Tên | Phụ thuộc | AC / FR chính |
|---|---|---|---|
| T-01 | Project scaffold & config | — | Technical Constraints |
| T-02 | Error schema & exception handlers | T-01 | FR-05.1, FR-05.5 |
| T-03 | Trace ID middleware | T-01, T-02 | FR-04.2, AC-09 |
| T-04 | Route registry & matcher | T-01, T-02 | FR-01.1, FR-01.4 |
| T-05 | Firebase auth & Internal JWT | T-01, T-02 | FR-02.1–02.7, AC-02, AC-06 |
| T-06 | HTTP proxy forwarder | T-04, T-05 | FR-01.3, FR-05.3–05.4, AC-01, AC-05 |
| T-07 | Access logging middleware | T-03, T-06 | FR-04.1, FR-04.3–04.5, AC-08 |
| T-08 | Rate limiting (Redis) | T-03, T-05 | FR-03.1–03.6, AC-03, AC-04, AC-10 |
| T-09 | Upstream error normalization | T-06, T-02 | FR-05.2 |
| T-10 | Health check endpoint | T-04, T-08 | FR-06.1–06.2, AC-07 |
| T-11 | AI route proxy (API Key only) | T-06, T-05 | FR-01.2, D-07 |
| T-12 | Docker Compose & CI | T-01 → T-11 | Technical Constraints |

---

## T-01 — Project scaffold & config

**Status:** `[x]` — Completed 2026-06-16

### Mục tiêu

Khởi tạo project `api-gateway/` với cấu trúc thư mục, dependencies, config
từ env, và FastAPI app skeleton.

### Phạm vi

- Tạo cấu trúc thư mục theo [design.md](./design.md#component-breakdown)
- `pyproject.toml`: FastAPI, uvicorn, pydantic-settings, httpx, PyJWT,
  firebase-admin, redis, structlog, dev deps (pytest, pytest-asyncio, fakeredis,
  respx, freezegun, ruff)
- `app/config.py`: load toàn bộ env vars trong design (routes, limits, secrets)
- `app/main.py`: FastAPI app factory, lifespan stub (Redis/Firebase init placeholder)
- `.env.example` với tất cả biến env
- `.gitignore`: `.env`, Firebase credentials, `__pycache__`, `.pytest_cache`

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_config.py` | Config load từ env; default values đúng (rate limits, timeout) |
| `tests/unit/test_config.py` | Missing required env (`JWT_SECRET_KEY`, `REDIS_URL`) → validation error |

### Done when

- [x] `pytest tests/unit/test_config.py` pass — 15/15
- [x] `ruff check` + `ruff format --check` pass
- [x] `uvicorn app.main:app` khởi động được (health chưa cần hoạt động)

---

## T-02 — Error schema & exception handlers

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-01

### Mục tiêu

Chuẩn hoá error response JSON và global exception handlers.

### Phạm vi

- `app/errors/codes.py`: enum error codes (`UNAUTHORIZED`, `ROUTE_NOT_FOUND`,
  `RATE_LIMIT_EXCEEDED`, `UPSTREAM_TIMEOUT`, `UPSTREAM_UNAVAILABLE`,
  `INTERNAL_ERROR`, `UPSTREAM_ERROR`)
- `app/errors/handlers.py`: helper `error_response(code, message, trace_id, status)`
- Đăng ký FastAPI exception handlers → format FR-05.1
- Uncaught exception → 500 `INTERNAL_ERROR`, stack trace **chỉ** trong log

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_error_handlers.py` | Response body đúng schema `{ error: { code, message, trace_id } }` |
| `tests/unit/test_error_handlers.py` | 500 response **không** chứa stack trace |
| `tests/integration/test_error_handlers.py` | Route test throw exception → 500 format chuẩn |

### Done when

- [x] Tests pass — 24/24
- [x] Mọi gateway-generated error tuân schema FR-05.1

**Covers:** FR-05.1, FR-05.5

---

## T-03 — Trace ID middleware

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-01, T-02

### Mục tiêu

Sinh hoặc giữ `trace_id`, gắn vào request context.

### Phạm vi

- `app/middleware/trace.py`
- Client gửi `X-Trace-ID` UUID v4 hợp lệ → giữ nguyên (D-10)
- Thiếu hoặc invalid → sinh UUID v4 mới
- Lưu `trace_id` vào `request.state` để middleware/handler khác dùng

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_trace.py` | UUID validation helper |
| `tests/integration/test_tracing.py` | Không có header → sinh UUID v4 mới |
| `tests/integration/test_tracing.py` | Header UUID hợp lệ → giữ nguyên |
| `tests/integration/test_tracing.py` | Header invalid → sinh mới |
| `tests/integration/test_tracing.py` | Error response chứa cùng `trace_id` |

### Done when

- [x] Tests pass — 17/17

**Covers:** FR-04.2, AC-09 (phần sinh/giữ trace_id)

---

## T-04 — Route registry & matcher

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-01, T-02

### Mục tiêu

Đăng ký 14 path prefix → upstream config; longest prefix match; 404 nếu không khớp.

### Phạm vi

- `app/routing/registry.py`: route table từ config (prefix, upstream URL, route_id,
  per-route limit, critical flag, is_ai flag)
- `app/routing/matcher.py`: longest prefix match
- Catch-all proxy route handler stub (chưa forward thật)
- Unknown path → 404 `ROUTE_NOT_FOUND`

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_route_matcher.py` | `/pets/123` → pet-service |
| `tests/unit/test_route_matcher.py` | `/feed/timeline` → post-service (alias) |
| `tests/unit/test_route_matcher.py` | `/unknown` → None |
| `tests/unit/test_route_matcher.py` | Longest prefix: `/capture/upload` → capture |
| `tests/integration/test_routing.py` | `GET /unknown` → 404 error format chuẩn |

### Done when

- [x] Tests pass — 26/26
- [x] Đủ 14 prefix theo design + bảng critical/non-critical (D-03)

**Covers:** FR-01.1, FR-01.2, FR-01.4

---

## T-05 — Firebase auth & Internal JWT

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-01, T-02

### Mục tiêu

Verify Firebase ID Token; sinh Internal JWT HS256; skip auth cho public routes.

### Phạm vi

- `app/auth/firebase.py`: `verify_id_token` qua Firebase Admin SDK
- `app/auth/jwt_issuer.py`: HS256 JWT với claims `uid`, `email`, `auth_provider`,
  `iat`, `exp`, `iss`, `sub`; expiry ≤ 15 phút
- Auth dependency/middleware: yêu cầu `Authorization: Bearer <token>` trên
  protected routes
- Public routes: `GET /health` (và `/ready` nếu implement)
- Anonymous token: `auth_provider=anonymous`, email null (FR-02.6)
- Invalid/expired/revoked/missing token → 401, **không** forward upstream

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_jwt_issuer.py` | JWT payload đủ claims; exp ≤ 15 phút |
| `tests/unit/test_jwt_issuer.py` | Anonymous → `auth_provider=anonymous`, email null |
| `tests/integration/test_auth.py` | Expired token → 401 `UNAUTHORIZED`, không gọi upstream |
| `tests/integration/test_auth.py` | Missing Authorization → 401 |
| `tests/integration/test_auth.py` | `GET /health` không cần token |
| `tests/integration/test_quick_auth.py` | Anonymous token `/onboarding/*` → JWT `auth_provider=anonymous` |

Fixtures trong `tests/conftest.py`: mock `auth.verify_id_token`.

### Done when

- [x] Tests pass
- [x] Firebase Admin init qua `FIREBASE_CREDENTIALS_PATH`

**Covers:** FR-02.1–02.7, AC-02, AC-06

---

## T-06 — HTTP proxy forwarder

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-04, T-05

### Mục tiêu

Forward request đến upstream: method, body, headers; đo upstream latency.

### Phạm vi

- `app/proxy/client.py`: httpx `AsyncClient` pool (lifespan)
- `app/proxy/headers.py`: strip `Authorization`, hop-by-hop headers; thêm
  `X-Internal-Token`, `X-Trace-ID`
- `app/proxy/forwarder.py`: build URL, forward, measure `upstream_latency_ms`
- Timeout → 502 `UPSTREAM_TIMEOUT`
- Connection refused → 503 `UPSTREAM_UNAVAILABLE`
- 2xx/3xx → passthrough status + body
- Wire catch-all route → forwarder

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_headers.py` | Strip Authorization, hop-by-hop; add X-Internal-Token, X-Trace-ID |
| `tests/integration/test_routing.py` | **AC-01:** `GET /pets/123` + valid token → upstream nhận `X-Internal-Token`, client nhận status gốc |
| `tests/integration/test_upstream_errors.py` | **AC-05:** upstream timeout → 502, no stack in body |
| `tests/integration/test_upstream_errors.py` | Connection refused → 503 |

Fixtures: `respx` mock upstream.

### Done when

- [x] AC-01, AC-05 tests pass
- [x] `upstream_latency_ms` available cho logging (T-07)

**Covers:** FR-01.3, FR-02.4, FR-05.3–05.4, AC-01, AC-05

---

## T-07 — Access logging middleware

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-03, T-06

### Mục tiêu

Ghi JSON access log ra stdout cho mỗi request.

### Phạm vi

- `app/middleware/logging.py`
- Log fields: `trace_id`, `timestamp`, `method`, `path`, `status_code`,
  `latency_ms`, `upstream_latency_ms`, `user_id`, `client_ip`, `upstream`, `route_id`
- `client_ip` = `request.client.host` (D-08)
- Level ERROR + stack trace cho 5xx / uncaught exception
- **Không** log Authorization, Firebase token, Internal JWT payload

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_logging.py` | Log output JSON đúng schema |
| `tests/unit/test_logging.py` | **AC-08:** log không chứa Authorization / token values |
| `tests/integration/test_routing.py` | **AC-01:** log entry có trace_id, user_id, path, status_code, latency_ms |
| `tests/integration/test_tracing.py` | trace_id xuất hiện trong log entry |

Dùng `caplog` hoặc mock stdout handler.

### Done when

- [x] AC-01 (log fields), AC-08, AC-09 (log) tests pass

**Covers:** FR-04.1, FR-04.3–04.5, AC-08

---

## T-08 — Rate limiting (Redis)

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-03, T-05

### Mục tiêu

Rate limit qua Redis: per-user, per-IP (public), per-route, global.

### Phạm vi

- `app/middleware/rate_limit.py` (hoặc `app/rate_limit/`)
- Redis sliding window counter (design)
- Limits: user 200/min, IP 30/min, global 10_000/min, capture 20/min/user
- Vượt limit → 429 `RATE_LIMIT_EXCEEDED` + header `Retry-After` (≥ 1s)
- Public route (`/health`): chỉ IP limit
- Protected route: user + route (nếu có) + global
- Check **trước** proxy; auth chạy trước rate limit user-based

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_rate_limit.py` | Retry-After calculation |
| `tests/integration/test_rate_limit_user.py` | **AC-03:** 201 requests → 429 + Retry-After |
| `tests/integration/test_rate_limit_ip.py` | **AC-04:** 31 public requests → 429 |
| `tests/integration/test_rate_limit_route.py` | **AC-10:** capture limit riêng; `/pets` vẫn ok |

Dùng `fakeredis` async.

### Done when

- [x] AC-03, AC-04, AC-10 tests pass

**Covers:** FR-03.1–03.6, AC-03, AC-04, AC-10

---

## T-09 — Upstream error normalization

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-06, T-02

### Mục tiêu

Normalize upstream 4xx/5xx JSON errors; thêm `trace_id`.

### Phạm vi

- `app/errors/normalizer.py`
- Upstream `{ "error": { "code", "message" } }` → thêm `trace_id`, giữ status
- Sai schema / non-JSON → wrap `UPSTREAM_ERROR` + generic message
- 2xx/3xx không đụng

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/unit/test_error_normalizer.py` | Valid upstream error → thêm trace_id |
| `tests/unit/test_error_normalizer.py` | Invalid JSON → wrap UPSTREAM_ERROR |
| `tests/unit/test_error_normalizer.py` | FastAPI-style body → wrap (nếu gặp) |
| `tests/integration/test_upstream_errors.py` | Upstream 404 JSON → status giữ nguyên, body có trace_id |

### Done when

- [x] Tests pass

**Covers:** FR-05.2, D-06

---

## T-10 — Health check endpoint

**Status:** `[x]` — Completed 2026-06-16  
**Phụ thuộc:** T-04, T-08

### Mục tiêu

`GET /health` public, probe upstream song song, 200/503 theo critical upstream.

### Phạm vi

- `app/health/checker.py`: parallel `GET {upstream}/health`, timeout 5s
- Response schema theo design
- Critical down (User, Pet, Onboarding) → HTTP 503
- Non-critical down → vẫn 200, optional `status: "degraded"`
- Subject to IP rate limit (FR-03.2)

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/integration/test_health.py` | **AC-07:** all critical up → 200 + upstream statuses |
| `tests/integration/test_health.py` | User service down → 503 |
| `tests/integration/test_health.py` | Non-critical down → 200 (degraded) |
| `tests/integration/test_health.py` | No Authorization required |

Mock upstream health endpoints với respx.

### Done when

- [x] AC-07 tests pass

**Covers:** FR-06.1–06.2, AC-07, D-03, D-09

---

## T-11 — AI route proxy (API Key only)

**Status:** `[ ]`  
**Phụ thuộc:** T-06, T-05

### Mục tiêu

Route `/ai/*`: yêu cầu Firebase auth từ client; forward chỉ `AI_API_KEY`.

### Phạm vi

- Trong `forwarder` / `headers`: nếu `is_ai` route → strip Firebase token +
  `X-Internal-Token`; set `Authorization: Bearer <AI_API_KEY>`
- Vẫn forward `X-Trace-ID`
- Rate limit theo user (không có route limit riêng trừ khi config sau)

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/integration/test_ai_proxy.py` | Valid Firebase token + `POST /ai/analyze` → upstream nhận AI API Key |
| `tests/integration/test_ai_proxy.py` | Upstream **không** nhận X-Internal-Token |
| `tests/integration/test_ai_proxy.py` | Missing Firebase token → 401 |

### Done when

- [ ] Tests pass

**Covers:** FR-01.2 (Third-party AI), D-07

---

## T-12 — Docker Compose & CI

**Status:** `[ ]`  
**Phụ thuộc:** T-01 → T-11

### Mục tiêu

Containerize gateway; docker-compose local; CI pipeline.

### Phạm vi

- `Dockerfile`: Python 3.11 slim, multi-stage nếu cần
- `docker-compose.yml`: `api-gateway` + `redis` (D-01 — không PostgreSQL)
- Healthcheck container gateway
- `.github/workflows/ci.yml`:
  - ruff check + format
  - pytest `--cov=app --cov-fail-under=80`
  - docker build smoke
- README ngắn: setup, env, chạy local, chạy test

### Test (viết trước)

| File | Mô tả |
|---|---|
| `tests/smoke/test_docker_build.sh` hoặc CI step | `docker build` thành công |
| Manual / optional | `docker compose up` → `GET /health` → 200 |

### Done when

- [ ] `docker compose up` chạy gateway + redis
- [ ] CI workflow green với full test suite
- [ ] Coverage ≥ 80%

**Covers:** Technical Constraints, design Test Strategy / CI

---

## Acceptance Criteria checklist

Map cuối cùng — tất cả phải pass trước khi coi feature done:

| AC | Task(s) | Test file |
|---|---|---|
| AC-01 | T-06, T-07 | `tests/integration/test_routing.py` |
| AC-02 | T-05 | `tests/integration/test_auth.py` |
| AC-03 | T-08 | `tests/integration/test_rate_limit_user.py` |
| AC-04 | T-08 | `tests/integration/test_rate_limit_ip.py` |
| AC-05 | T-06, T-07 | `tests/integration/test_upstream_errors.py` |
| AC-06 | T-05, T-06 | `tests/integration/test_quick_auth.py` |
| AC-07 | T-10 | `tests/integration/test_health.py` |
| AC-08 | T-07 | `tests/unit/test_logging.py` |
| AC-09 | T-03, T-06, T-07 | `tests/integration/test_tracing.py` |
| AC-10 | T-08 | `tests/integration/test_rate_limit_route.py` |

---

## Out of scope (nhắc lại)

Không tạo task cho các mục trong requirements **Non-Goals**:

- Admin UI, WAF, gRPC, WebSocket, response caching, load balancing logic,
  billing, analytics dashboard
- `/ready` endpoint (optional — chỉ làm nếu có thời gian sau T-12)
- `TRUST_PROXY` / X-Forwarded-For (D-08 future)

---

## Gợi ý prompt cho từng session implement

```
Implement task T-0X from specs/api-gateway/tasks.md.
Follow SDD: read requirements.md + design.md + decision_log.md.
TDD: write tests first, then minimal implementation.
Only scope of T-0X — do not start other tasks.
```
