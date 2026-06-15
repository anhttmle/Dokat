# API Gateway — Requirements

**Project:** Dokat (mạng xã hội dành cho thú cưng)
**Feature:** API Gateway
**Version:** 1.0
**Date:** 2026-06-15
**Status:** Draft

---

## Goal

Xây dựng một API Gateway tập trung bằng FastAPI, đóng vai trò là single entry point
cho toàn bộ client (mobile/web) của Dokat. Gateway chịu trách nhiệm xác thực
Firebase ID Token, đổi lấy JWT nội bộ, định tuyến request đến đúng upstream
service, áp đặt rate limiting, chuẩn hoá lỗi và ghi log tập trung theo chuẩn
có thể tích hợp Loki trong tương lai.

---

## Users / Actors

| Actor | Mô tả |
|---|---|
| **Mobile/Web Client** | Ứng dụng Dokat gửi request đến Gateway |
| **Quick Auth User** | Người dùng chưa có tài khoản, xác thực qua Device ID + Firebase Anonymous Auth |
| **Authenticated User** | Người dùng đã link tài khoản Google / Facebook / Apple qua Firebase |
| **Upstream Service** | Các internal microservices nhận request đã được xử lý từ Gateway |
| **Third-party AI API** | Dịch vụ AI bên ngoài (phân tích ảnh thú cưng) được Gateway proxy đến |

---

## Functional Requirements

### FR-01 — Request Routing

- **FR-01.1** Hệ thống SHALL định tuyến request đến đúng upstream service dựa
  trên path prefix (ví dụ `/users/*` → User Service, `/pets/*` → Pet Service).
- **FR-01.2** Hệ thống SHALL hỗ trợ định tuyến đến ít nhất các upstream sau:
  - **User Service** — quản lý profile người dùng
  - **Pet Service** — quản lý thông tin thú cưng
  - **Post/Feed Service** — bài đăng, timeline
  - **Social Graph Service** — kết bạn, mời bạn
  - **Capture Service** — cấp presigned S3 URL để client upload ảnh/video
  - **Send Service** — gửi capture đến danh sách bạn bè
  - **View Service** — lấy metadata ảnh/video từ CDN
  - **Response Service** — reply bằng capture, danh sách Seen
  - **History Service** — feed nhìn lại hoạt động (mặc định 1 ngày)
  - **Onboarding Service** — Quick Auth bằng Device ID
  - **Notification Service** — push notification, gợi ý daily activity
  - **Setting Service** — liên kết Quick Auth với tài khoản mạng xã hội
  - **Third-party AI API** — proxy request đến AI provider bên ngoài
- **FR-01.3** Hệ thống SHALL forward đầy đủ HTTP method, headers cần thiết
  và request body đến upstream service.
- **FR-01.4** Hệ thống SHALL trả về HTTP 404 với error body chuẩn nếu không
  tìm thấy route phù hợp.

### FR-02 — Firebase Authentication & Internal JWT Exchange

- **FR-02.1** Hệ thống SHALL yêu cầu header `Authorization: Bearer <firebase_id_token>`
  trên tất cả các endpoint được bảo vệ.
- **FR-02.2** Hệ thống SHALL xác thực Firebase ID Token sử dụng
  Firebase Admin SDK (verify signature, expiry, audience).
- **FR-02.3** Sau khi xác thực thành công, hệ thống SHALL đổi Firebase ID Token
  lấy một Internal JWT chứa ít nhất: `uid`, `email` (nếu có), `auth_provider`,
  `issued_at`, `expires_at`.
- **FR-02.4** Hệ thống SHALL forward Internal JWT đến upstream service
  thông qua header `X-Internal-Token`.
- **FR-02.5** Hệ thống SHALL trả về HTTP 401 với error body chuẩn nếu
  Firebase ID Token không hợp lệ, hết hạn hoặc bị thu hồi.
- **FR-02.6** Hệ thống SHALL hỗ trợ Quick Auth — client xác thực bằng
  Firebase Anonymous Auth (Device ID), không bắt buộc phải có email.
- **FR-02.7** Hệ thống SHALL xác định các route public (ví dụ health check)
  không yêu cầu xác thực.

### FR-03 — Rate Limiting

- **FR-03.1** Hệ thống SHALL giới hạn **200 request/phút** cho mỗi
  authenticated user (dựa trên Firebase UID).
- **FR-03.2** Hệ thống SHALL giới hạn **30 request/phút** cho mỗi
  IP address trên các endpoint public (chưa xác thực).
- **FR-03.3** Hệ thống SHALL hỗ trợ cấu hình rate limit riêng theo route
  (ví dụ: Capture/Upload endpoint có limit thấp hơn feed endpoint).
- **FR-03.4** Hệ thống SHALL áp đặt một global rate limit để bảo vệ toàn
  hệ thống khỏi traffic đột biến (giá trị cụ thể được cấu hình qua env).
- **FR-03.5** Hệ thống SHALL trả về HTTP 429 kèm header `Retry-After`
  (số giây) khi vượt quá rate limit.
- **FR-03.6** Hệ thống SHALL sử dụng sliding window hoặc token bucket
  algorithm cho rate limiting.

### FR-04 — Centralized Logging & Request Tracing

- **FR-04.1** Hệ thống SHALL ghi log cho mỗi request với các trường:
  `trace_id`, `timestamp`, `method`, `path`, `status_code`,
  `latency_ms`, `upstream_latency_ms`, `user_id` (nếu có), `client_ip`.
- **FR-04.2** Hệ thống SHALL sinh một `trace_id` (UUID v4) duy nhất cho
  mỗi request và forward qua header `X-Trace-ID` đến upstream service.
- **FR-04.3** Hệ thống SHALL ghi log lỗi đầy đủ bao gồm error message và
  stack trace ở log level ERROR.
- **FR-04.4** Hệ thống SHALL ghi log ra **stdout** theo định dạng JSON
  (tương thích với Loki label indexing).
- **FR-04.5** Hệ thống SHALL KHÔNG ghi thông tin nhạy cảm vào log
  (Authorization header, Firebase ID Token, Internal JWT payload).

### FR-05 — Error Response Normalization

- **FR-05.1** Hệ thống SHALL chuẩn hoá mọi error response về JSON format:
  ```json
  {
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests. Retry after 30 seconds.",
      "trace_id": "uuid-v4"
    }
  }
  ```
- **FR-05.2** Hệ thống SHALL ánh xạ lỗi từ upstream service sang HTTP
  status code phù hợp và trả về error body theo format trên.
- **FR-05.3** Hệ thống SHALL trả về HTTP 502 khi upstream service không
  phản hồi trong timeout quy định.
- **FR-05.4** Hệ thống SHALL trả về HTTP 503 khi upstream service
  không thể kết nối (connection refused).
- **FR-05.5** Hệ thống SHALL KHÔNG expose stack trace hoặc thông tin
  nội bộ trong error response trả về client.

### FR-06 — Health Check

- **FR-06.1** Hệ thống SHALL expose endpoint `GET /health` (không yêu cầu
  auth) trả về trạng thái của gateway và các upstream service.
- **FR-06.2** Endpoint health check SHALL trả về HTTP 200 nếu gateway
  hoạt động bình thường, HTTP 503 nếu có upstream critical bị down.

---

## Non-Goals

- **Không có** Admin UI / Dashboard để quản lý route và config.
- **Không có** Web Application Firewall (WAF) — không kiểm tra payload
  SQL injection, XSS.
- **Không hỗ trợ** gRPC — chỉ HTTP/REST.
- **Không hỗ trợ** WebSocket.
- **Không có** Response caching tại gateway.
- **Không có** Load balancing giữa nhiều instance của cùng một upstream service
  (giao cho Docker Compose / Kubernetes xử lý).
- **Không tính phí** theo usage (billing).
- **Không có** advanced analytics dashboard.

---

## Technical Constraints

| Constraint | Chi tiết |
|---|---|
| **Language** | Python 3.11+ |
| **Framework** | FastAPI |
| **Auth SDK** | Firebase Admin Python SDK |
| **Containerization** | Docker; orchestration bằng Docker Compose (hiện tại) và Kubernetes (tương lai) |
| **Log format** | JSON structured log ra stdout (tương thích Loki) |
| **Rate limit storage** | Redis (để đảm bảo consistency khi scale ngang) |
| **Internal JWT** | HS256 hoặc RS256, expiry ngắn (≤ 15 phút) |
| **Upstream protocol** | HTTP/1.1 REST |
| **Scale target** | Hàng chục nghìn request/phút |
| **Config** | Toàn bộ cấu hình qua environment variables / `.env`, không hardcode |
| **Secret management** | Firebase service account key và JWT secret key KHÔNG được commit vào repo |

---

## Acceptance Criteria

### AC-01 — Happy path routing

```
Given client gửi GET /pets/123 kèm Firebase ID Token hợp lệ
When Gateway nhận request
Then Gateway verify token thành công
 And Gateway sinh Internal JWT chứa uid tương ứng
 And Gateway forward request đến Pet Service với header X-Internal-Token
 And Client nhận response từ Pet Service với status code gốc
 And Log entry chứa trace_id, user_id, path=/pets/123, status_code, latency_ms
```

### AC-02 — Invalid Firebase token

```
Given client gửi request kèm Firebase ID Token đã hết hạn
When Gateway verify token
Then Gateway trả về HTTP 401
 And Response body có format: {"error": {"code": "UNAUTHORIZED", "message": "...", "trace_id": "..."}}
 And Request KHÔNG được forward đến upstream service
```

### AC-03 — Rate limit per user

```
Given authenticated user gửi 201 request trong vòng 1 phút
When request thứ 201 đến Gateway
Then Gateway trả về HTTP 429
 And Response header chứa Retry-After (số giây > 0)
 And Response body có format error chuẩn với code RATE_LIMIT_EXCEEDED
```

### AC-04 — Rate limit per IP (public endpoint)

```
Given một IP address không xác thực gửi 31 request/phút đến public endpoint
When request thứ 31 đến Gateway
Then Gateway trả về HTTP 429 với Retry-After header
```

### AC-05 — Upstream timeout

```
Given upstream service không phản hồi trong thời gian timeout cấu hình
When Gateway chờ response từ upstream
Then Gateway trả về HTTP 502
 And Response body có format error chuẩn với code UPSTREAM_TIMEOUT
 And Log entry ghi error detail kèm trace_id
 And Stack trace KHÔNG xuất hiện trong response body trả về client
```

### AC-06 — Quick Auth (Anonymous)

```
Given client gửi Firebase Anonymous ID Token (Device ID login) đến /onboarding/*
When Gateway verify token
Then Gateway xác nhận token hợp lệ (dù không có email)
 And Gateway sinh Internal JWT với auth_provider=anonymous
 And Request được forward đến Onboarding Service
```

### AC-07 — Health check

```
Given tất cả upstream critical đang hoạt động
When client gọi GET /health (không có Authorization header)
Then Gateway trả về HTTP 200
 And Response body liệt kê trạng thái các upstream service
```

### AC-08 — Log does not contain secrets

```
Given một request hợp lệ được xử lý bởi Gateway
When kiểm tra log entry tương ứng
Then log entry KHÔNG chứa giá trị của Authorization header
 And log entry KHÔNG chứa nội dung Firebase ID Token
 And log entry KHÔNG chứa Internal JWT payload
```

### AC-09 — Trace ID propagation

```
Given client gửi request không có X-Trace-ID header
When Gateway xử lý request
Then Gateway sinh UUID v4 làm trace_id
 And Gateway forward header X-Trace-ID đến upstream service
 And trace_id xuất hiện trong log entry
 And trace_id xuất hiện trong error response (nếu có lỗi)
```

### AC-10 — Per-route rate limit (Capture endpoint)

```
Given Capture endpoint được cấu hình rate limit riêng (thấp hơn mặc định)
When user vượt quá giới hạn của Capture endpoint dù chưa đạt global user limit
Then Gateway trả về HTTP 429 chỉ cho Capture endpoint
 And Các endpoint khác của cùng user vẫn hoạt động bình thường
```
