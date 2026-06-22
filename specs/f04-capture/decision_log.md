# F04 — Capture Ảnh + AI Validation — Decision Log

---

## DL-F04-01 — F04 là client-only; upload/post creation thuộc F05

**Date:** 2026-06-22
**Context:** Kế hoạch tổng (build F04–F11) phác thảo F04 bao gồm
"presigned S3 URL endpoint" và "photos table migration". Tuy
nhiên `specs/f04-capture/requirements.md` không liệt kê bất kỳ
API/FR nào về upload hay ghi DB; FR-3/FR-4 nêu rõ "không validate
phía server". PRD §F05 đặt phần upload bằng presigned S3 URL,
tạo `posts` và `post_recipients` vào phạm vi F05.
**Decision:** Giới hạn F04 thuần client-side: capture + AI
validation + nén JPEG q80. F04 chỉ tạo artifact `CapturedPhoto`
(ảnh đã nén + `s3_key` tính sẵn) để handoff sang F05. Không thêm
endpoint, không thêm migration trong F04.
**Consequence:** Tránh trùng lặp công việc với F05 (upload, bảng
`posts`/`post_recipients`). Bảng `photos` stub hiện tại
(`backend/app/models/photo.py`) sẽ được mở rộng trong F05, không
phải F04. Ranh giới handoff là interface `CapturedPhoto`.

---

## DL-F04-02 — Ngưỡng block người = 0.70 (inclusive)

**Date:** 2026-06-22
**Context:** FR-4 yêu cầu block khi phát hiện người "với độ tin
cậy cao"; FR-5 yêu cầu cho phép upload khi "low confidence".
Requirements không nêu con số ngưỡng cụ thể.
**Decision:** Dùng `HUMAN_BLOCK_THRESHOLD = 0.70`, so sánh
inclusive (`human_confidence >= 0.70` → block). Chọn 0.70 cho
nhất quán với `GENDER_CONFIDENCE_THRESHOLD` đã dùng ở F02
(`PetAIService`).
**Consequence:** Có thể tinh chỉnh khi tích hợp model thật và đo
false-positive/negative. Test ngưỡng biên (`== 0.70`) khẳng định
hành vi inclusive.

---

## DL-F04-03 — Camera & image compression abstract sau interface, tích hợp native sau

**Date:** 2026-06-22
**Context:** `package.json` chưa có thư viện camera (Vision
Camera / Expo Camera) hay nén ảnh (image-resizer /
expo-image-manipulator). Cần test được logic capture/validation
mà không phụ thuộc native module (tiền lệ **DL-F03-11**).
**Decision:** `ImageCompressor` và camera component được abstract
sau interface injectable/mockable. Model AI chạy qua
`_validationModelStub` (giống `_petModelStub` của F02). Tích hợp
thư viện native thực hiện ở task triển khai sau, không nằm trong
phạm vi spec F04.
**Consequence:** Unit test chỉ kiểm tra business logic (ngưỡng
block, tham số nén, state machine, format `s3_key`), không kiểm
tra native UI/permission hay hiệu năng thực (AC-F04-4 xác minh
thủ công).

---

## DL-F04-04 — Sinh UUID cho `s3Key` bằng Math.random (không thêm dependency)

**Date:** 2026-06-22
**Context:** `s3Key` cần một UUID (`posts/{userId}/{ts}_{uuid}.jpg`,
AC-F04-6). `crypto.randomUUID` không đảm bảo có mặt trong môi
trường React Native/Jest, và spec không chỉ định thư viện UUID.
**Decision:** Sinh UUID v4-style bằng helper nội bộ dựa trên
`Math.random` trong `CaptureService.ts`. Output hex+hyphen khớp
regex `[0-9a-f-]+` của test, không thêm native dependency (nhất
quán tinh thần DL-F04-03).
**Consequence:** Không dùng cho mục đích bảo mật/mã hóa; chỉ để
tạo tên file duy nhất. Có thể thay bằng `crypto.randomUUID` hoặc
thư viện uuid khi tích hợp native ở task sau.
