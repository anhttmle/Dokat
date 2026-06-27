---
name: sdd-requirements
description: >-
  Tương tác với user để thu thập yêu cầu và viết requirements.md cho một
  feature mới trong dự án Dokat theo chuẩn SDD. Dùng khi user nói "tạo
  requirements cho feature X", "spec feature mới", "tôi muốn build tính năng
  Y", "viết requirements.md", hoặc bắt đầu bất kỳ feature mới nào chưa có
  specs.
---

# SDD — Tạo requirements.md (interactive)

## Nguyên tắc

Đây là bước ĐẦU TIÊN trong SDD — đứng trước design.md và tasks.md.  
Không tự suy diễn scope. Hỏi đủ để viết spec chính xác, không thêm không bớt.

---

## Phase 1: Thu thập thông tin (hỏi tuần tự)

### Câu hỏi 1 — Goal & Actors

Hỏi:
- Feature này giải quyết vấn đề gì cho user?
- Ai sẽ dùng tính năng này? (guest, owner, pet owner, sender, recipient…)
- Có feature nào trong F01–F11 hiện tại liên quan không?

### Câu hỏi 2 — Happy path

Hỏi user mô tả **luồng chính** bằng ngôn ngữ tự nhiên:
> "User mở app → làm gì → kết quả là gì?"

Ghi lại từng bước — đây là nguồn để derive Functional Requirements.

### Câu hỏi 3 — Edge cases & lỗi

Hỏi:
- Điều gì xảy ra nếu thiếu dữ liệu / mất kết nối / permission bị từ chối?
- Có giới hạn nào (số lượng, kích thước, thời gian)?
- Hành động nào cần xác nhận trước khi thực hiện?

### Câu hỏi 4 — Non-goals (quan trọng)

Hỏi rõ:
> "Những gì bạn KHÔNG muốn có trong MVP này?"

Gợi ý nếu user không chắc: search, filter nâng cao, notification, analytics,
share ra ngoài app, premium-only, v.v.

### Câu hỏi 5 — Technical constraints

Hỏi:
- Dùng service nào đã có? (Firebase, S3, Redis, FCM, on-device AI)
- Có ràng buộc về performance, platform (iOS only / Android only)?
- Cần backend mới hay chỉ là client-only?

---

## Phase 2: Confirm trước khi viết

Trước khi viết file, tóm tắt lại những gì đã thu thập:

```
Feature: <tên>
Goal: <1 câu>
Actors: <danh sách>
Happy path: <3–5 bước>
Edge cases: <danh sách ngắn>
Non-goals: <danh sách>
Constraints: <danh sách>
```

Hỏi: "Bạn muốn thay đổi gì trước khi tôi viết requirements.md?"

---

## Phase 3: Viết requirements.md

Tạo `specs/<feature-id>-<tên>/requirements.md` với format:

```markdown
# F<N> — <Tên Feature> — Requirements

## Goal
<1–2 câu mô tả mục tiêu và giá trị cho user>

## Users / Actors
- **<Actor 1>:** <vai trò>
- **<Actor 2>:** <vai trò>

## Functional Requirements

1. Hệ thống SHALL <hành động cụ thể, có thể test được>
2. Hệ thống SHALL ...
(đánh số liên tục, mỗi FR một hành vi độc lập)

## Non-goals
- Không có <X> trong MVP.
- Không có <Y>.

## Technical Constraints
- <Constraint cụ thể, kỹ thuật>

## Acceptance Criteria

**AC-F<N>-1:** <Tên scenario>
Given <điều kiện ban đầu>
When <hành động của actor>
Then <kết quả mong đợi cụ thể>
  và <điều kiện phụ nếu có>

**AC-F<N>-2:** ...
```

### Quy tắc viết FR

- Dùng "SHALL" cho yêu cầu bắt buộc, "SHOULD" cho khuyến nghị
- Mỗi FR mô tả **một** hành vi — không gộp nhiều hành vi vào một câu
- Có thể test được: tránh "hệ thống SHALL hoạt động tốt"

### Quy tắc viết AC

- Mỗi AC phủ đúng **một** FR hoặc một edge case
- Given/When/Then — không bỏ qua bước nào
- Cụ thể: số liệu, thông báo lỗi, giới hạn phải rõ

---

## Phase 4: Sau khi viết xong

1. Tạo thư mục `specs/<feature-id>-<tên>/` nếu chưa có
2. Tạo file `decision_log.md` trống với header:
   ```markdown
   # F<N> — <Tên> — Decision Log
   ```
3. Tóm tắt: số FR, số AC, feature nào phụ thuộc
4. Gợi ý bước tiếp theo: "Dùng skill `sdd-design` để tạo design.md"
