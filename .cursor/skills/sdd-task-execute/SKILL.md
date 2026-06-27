---
name: sdd-task-execute
description: >-
  Thực thi đúng một task SDD trong dự án Dokat. Dùng khi user nói "thực hiện
  task X.Y", "implement task", "execute task", hoặc chỉ định task cụ thể từ
  tasks.md. Tuân thủ nghiêm TDD và chỉ làm đúng task được giao.
---

# SDD — Thực thi một task

## Bước 1: Đọc context (bắt buộc)

Đọc 3 file trước khi viết bất kỳ dòng code nào:
1. `specs/<feature>/requirements.md`
2. `specs/<feature>/design.md`
3. `specs/<feature>/decision_log.md`

Đọc thêm `AGENT.md` nếu task liên quan đến client-BE integration.

## Bước 2: Xác nhận scope

Lặp lại task được giao và ranh giới của nó:
- Task này làm GÌ?
- Task này KHÔNG làm gì? (task liền sau hoặc liên quan)
- AC nào được phủ?

Nếu task không rõ → hỏi trước khi bắt đầu.

## Bước 3: TDD — viết test trước

1. Tạo file test (mirror structure)
2. Viết test cases cho AC của task — tất cả phải **FAIL** lúc này
3. Chỉ sau khi test fail rõ ràng mới bắt đầu implementation

Backend: `backend/tests/`  
Client Flutter: `client/test/features/<feature>/`

## Bước 4: Implementation

- Chỉ implement đủ để test PASS
- Không thêm logic cho task sau dù thấy cần thiết
- Giữ đúng coding standard (PEP8/`flutter analyze`)

## Bước 5: Khi phát sinh design decision

Nếu gặp quyết định không có trong spec:
1. **DỪNG** — không tự quyết định im lặng
2. Ghi vào `specs/<feature>/decision_log.md` với format:

```markdown
## DL-F0X-N — <Tên quyết định>

**Date:** YYYY-MM-DD
**Context:** Tại sao phát sinh quyết định này.
**Decision:** Đã chọn cách nào.
**Consequence:** Hệ quả, ai cần biết.
```

## Bước 6: Tóm tắt sau khi xong

Trả lời 3 câu:
- Đã làm gì?
- Test cover AC nào?
- Có decision log mới không?

## Quy tắc tuyệt đối

- CHỈ làm đúng task được chỉ định — không làm task khác dù thấy "cần thiết"
- KHÔNG xoá dead code không liên quan đến task
- KHÔNG "cải thiện" code lân cận không liên quan
- Mọi changed line phải trực tiếp từ task yêu cầu
