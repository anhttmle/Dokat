# API Gateway — Decision Log

Ghi các quyết định thiết kế không được nêu rõ trong requirements, đã được
product owner xác nhận ngày 2026-06-15.

---

## D-01 — Không dùng PostgreSQL

**Context:** Stack ban đầu gợi ý PostgreSQL; requirements chỉ nêu Redis cho
rate limiting.

**Decision:** Gateway **không kết nối PostgreSQL**. Stateful storage duy nhất
là Redis. Docker Compose của Gateway chỉ gồm `api-gateway` + `redis`.

**Rationale:** Gateway không có business data cần persist; tránh dependency
không cần thiết.

---

## D-02 — Path prefix routing

**Context:** Requirements liệt kê upstream services nhưng không định nghĩa URL
prefix.

**Decision:** Dùng bảng path prefix trong [design.md](./design.md#proxied-routes-path-prefix--upstream)
(`/users`, `/pets`, `/posts`, `/feed`, `/social`, `/capture`, `/send`, `/view`,
`/responses`, `/history`, `/onboarding`, `/notifications`, `/settings`, `/ai`).

**Status:** Confirmed OK.

---

## D-03 — Critical upstreams cho health check

**Context:** FR-06.2 yêu cầu HTTP 503 khi "upstream critical" down nhưng không
liệt kê.

**Decision:**

| Critical (503 nếu down) | Non-critical (báo status, không kéo 503) |
|---|---|
| User Service | Post/Feed Service |
| Pet Service | Social Graph Service |
| Onboarding Service | Capture, Send, View, Response, History, Notification, Setting, AI |

**Status:** Confirmed OK.

---

## D-04 — Internal JWT: HS256, upstream không verify

**Context:** Requirements cho phép HS256 hoặc RS256; chưa rõ upstream có verify
JWT không.

**Decision:**

- Gateway ký Internal JWT bằng **HS256** (`JWT_SECRET_KEY`).
- Upstream **không verify chữ ký** — tin tưởng mạng nội bộ, decode payload
  để lấy `uid`, `email`, `auth_provider`.
- Gateway vẫn forward `X-Internal-Token` (FR-02.4).

**Rationale:** Gateway là single auth boundary; đơn giản hoá upstream services.

---

## D-05 — Giá trị mặc định rate limit & timeout

**Context:** FR-03.4 và upstream timeout không có giá trị cụ thể.

**Decision:**

| Config | Default | Env var |
|---|---|---|
| Global rate limit | 10_000 req/min | `RATE_LIMIT_GLOBAL_PER_MIN` |
| Upstream proxy timeout | 30s | `UPSTREAM_TIMEOUT_SECONDS` |
| Capture per-route limit | 20 req/min/user | `RATE_LIMIT_CAPTURE_PER_MIN` |
| Health probe timeout | 5s | `HEALTH_PROBE_TIMEOUT_SECONDS` |

**Status:** Confirmed OK.

---

## D-06 — Upstream error format

**Context:** FR-05.2 yêu cầu normalize lỗi upstream nhưng chưa định nghĩa schema
upstream.

**Decision:** Upstream trả `{ "error": { "code", "message" } }`. Gateway giữ
status code gốc và **bổ sung `trace_id`** vào response trả client.

---

## D-07 — Third-party AI API: chỉ proxy API Key

**Context:** Route `/ai/*` proxy đến provider bên ngoài.

**Decision:**

- Client vẫn phải có Firebase token hợp lệ (rate limit theo user).
- Gateway **strip** Firebase `Authorization` và **không gửi** `X-Internal-Token`.
- Gateway set `Authorization: Bearer <AI_API_KEY>` từ env khi forward.

---

## D-08 — Client IP: direct connection

**Context:** Rate limit IP trên public endpoint (FR-03.2).

**Decision:** Hiện tại **không** đứng sau reverse proxy. `client_ip` =
`request.client.host`. Không implement `X-Forwarded-For` / `TRUST_PROXY` ở v1.

**Future:** Thêm `TRUST_PROXY` khi deploy sau load balancer.

---

## D-09 — Upstream health probe: HTTP GET

**Context:** FR-06.1 yêu cầu báo trạng thái upstream.

**Decision:** Probe bằng `GET {upstream_base_url}/health`, timeout 5s, chạy
song song cho tất cả upstream.

---

## D-10 — Trace ID propagation từ client

**Context:** AC-09 mô tả sinh trace_id khi client không gửi header.

**Decision:** Nếu client gửi `X-Trace-ID` là **UUID v4 hợp lệ** → giữ nguyên.
Nếu thiếu hoặc invalid → Gateway sinh UUID v4 mới.

---

## D-11 — Access log via stdlib logging

**Context:** T-07 yêu cầu JSON access log ra stdout (FR-04.4). Design ghi
structlog nhưng dependency chưa được dùng ở các task trước.

**Decision:** Dùng stdlib ``logging`` với message là JSON string
(``json.dumps(entry)``). Logger name ``app.middleware.logging``. Level
INFO cho status < 500, ERROR cho status >= 500. Đủ cho Loki ingestion và
``caplog`` trong tests; structlog có thể thêm sau nếu cần.

---

## D-12 — GatewayError trong middleware

**Context:** T-08 raise ``GatewayError`` từ ``RateLimitMiddleware`` cho IP
limit trên ``/health``.

**Decision:** Starlette ``BaseHTTPMiddleware`` không route exception tới
FastAPI handlers. Middleware bắt ``GatewayError`` và trả
``gateway_error_response()`` (shared helper trong ``handlers.py``). Route
handlers vẫn raise ``GatewayError`` bình thường.
