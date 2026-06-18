# Prompt tạo design.md
Đọc file specs/<feature>/requirements.md.

Nhiệm vụ:
1. Tạo `specs/<feature>/requirements.md` với các phần:
   - Architecture overview
   - Data models / Schema
   - API contracts (endpoints, request/response)
   - Component breakdown
   - Error handling strategy
   - Test strategy
2. Đặt câu hỏi nếu có gì không rõ trong requirements trước khi viết
3. KHÔNG viết code

# Prompt tạo tasks.md
Đọc `specs/<feature>/requirements.md` và `specs/<feature>/design.md `.

Tạo `specs/<feature>tasks.md` với format:
- Đánh số 1, 1.1, 1.2, 2, 2.1... (tối đa 2 cấp)
- Mỗi task phải: executable by agent, testable, independent nếu có thể
- Task đầu tiên LUÔN là: bootstrap project structure + test runner
- Mỗi task viết unit test TRƯỚC implementation
- Mỗi task reference đến requirement/acceptance criteria tương ứng
- Không quá 10 tasks chính cho 1 feature nhỏ

# Prompt thực thi từng task
Đọc các file sau làm context:
- specs/<feature>/requirements.md
- specs/<feature>/design.md
- specs/<feature>/decision_log.md

Thực hiện task sau (CHỈ task này):
---
<Task>
---

Quy tắc:
- Viết test trước, sau đó implementation
- Không implement task khác dù thấy cần thiết
- Nếu phát sinh quyết định thiết kế, thêm vào decision_log.md
- Sau khi xong, tóm tắt: đã làm gì, test cover gì