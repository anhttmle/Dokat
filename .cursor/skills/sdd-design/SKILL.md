---
name: sdd-design
description: >-
  Tạo design.md cho một feature Dokat theo SDD workflow. Dùng khi user nói
  "tạo design cho F0X", "viết design.md", "thiết kế feature", hoặc bắt đầu
  một feature mới sau khi đã có requirements.md.
---

# SDD — Tạo design.md

## Bước 1: Đọc context

Đọc theo thứ tự:
1. `specs/<feature>/requirements.md` — toàn bộ, không bỏ qua
2. `AGENT.md §7` — API contract đã verified (nếu feature có client-BE)
3. Các `specs/<feature>/decision_log.md` của feature phụ thuộc (nếu có)

Nếu chưa có `requirements.md` → **DỪNG**, yêu cầu tạo trước.

## Bước 2: Làm rõ trước khi viết

Hỏi nếu requirements có điểm không rõ:
- Acceptance criteria nào mâu thuẫn nhau?
- Feature phụ thuộc feature nào chưa implement?
- Giới hạn scope (ví dụ: "MVP chỉ cần…")?

## Bước 3: Viết design.md

Tạo `specs/<feature>/design.md` với cấu trúc:

```
## 1. Architecture overview
Mô tả luồng dữ liệu end-to-end (client → backend → DB).
Sơ đồ nếu phức tạp.

## 2. Data models / Schema
Bảng DB mới hoặc cột thêm vào. Không mô tả lại bảng từ feature khác.

## 3. API contracts
Mỗi endpoint: method, path, request body, response shape, error codes.
Format: khớp với Pydantic schema pattern của backend.

## 4. Component breakdown
Backend: service functions, router handlers.
Client Flutter: service Dart, domain model, provider, screens/widgets.

## 5. Error handling strategy
Map exception → HTTP status code → client error state.

## 6. Test strategy
Backend: unit (service), router (httpx), migration.
Client: mock Dio, widget test.
```

## Quy tắc

- KHÔNG viết code trong design.md
- KHÔNG implement bất kỳ file nào
- Chỉ mô tả NHỮNG GÌ yêu cầu spec nêu, không thêm "nice to have"
- Quyết định thiết kế quan trọng → ghi vào `decision_log.md` cùng lúc
