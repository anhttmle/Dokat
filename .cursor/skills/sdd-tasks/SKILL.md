---
name: sdd-tasks
description: >-
  Tạo tasks.md cho một feature Dokat theo SDD workflow. Dùng khi user nói
  "tạo task list cho F0X", "breakdown tasks", "viết tasks.md", hoặc sau khi
  đã có requirements.md và design.md.
---

# SDD — Tạo tasks.md

## Bước 1: Đọc context

Đọc đủ 2 file trước khi viết:
1. `specs/<feature>/requirements.md`
2. `specs/<feature>/design.md`

Nếu một trong hai chưa có → **DỪNG**, yêu cầu tạo trước.

## Bước 2: Viết tasks.md

### Format bắt buộc

```
# F0X — <Tên Feature> — Tasks

## 1. Bootstrap
### 1.1 Scaffold project structure + test runner
...

## 2. <Nhóm logic>
### 2.1 <Task cụ thể>
...
```

### Quy tắc đánh số
- Tối đa 2 cấp: `1`, `1.1`, `1.2`, `2`, `2.1`…
- Tối đa **10 task chính** (số chẵn)

### Task đầu tiên (bắt buộc)
Task 1.1 luôn là: bootstrap cấu trúc thư mục + xác nhận test runner chạy được (0 test passes).

### Mỗi task phải có
- **Mục tiêu:** một câu mô tả output
- **Test trước:** viết test TRƯỚC implementation (TDD)
- **Reference AC:** `AC-F0X-N` hoặc `FR-N` tương ứng từ requirements.md
- **Độc lập:** có thể làm mà không cần task sau hoàn thành

### Scope
- Chỉ bao gồm những gì design.md mô tả
- Không thêm task "optimize", "refactor", "nice to have"
- Tasks backend và client Flutter tách nhóm rõ ràng

## Quy tắc

- KHÔNG viết code
- KHÔNG implement bất kỳ file nào
- Sau khi tạo xong, tóm tắt số task chính và AC nào được phủ
