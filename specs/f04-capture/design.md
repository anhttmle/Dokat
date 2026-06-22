# F04 — Capture Ảnh + AI Validation — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F04 vs F05)

F04 là tính năng **hoàn toàn client-side**: mở camera, chụp ảnh
720p, chạy AI validation on-device, và nén ảnh JPEG quality 80.
F04 KHÔNG có backend endpoint và KHÔNG ghi DB.

- `requirements.md` F04 không liệt kê API nào; mọi FR/AC đều
  thực thi on-device (FR-3, FR-4: "không validate phía server").
- Việc upload S3 (presigned URL), tạo `posts` record và
  `post_recipients` thuộc **F05 — Gửi Ảnh** (xem PRD §F05
  Technical Constraints: "Upload ảnh dùng presigned S3 URL").

**Đầu ra của F04** là một artifact `CapturedPhoto` (xem §2.1):
ảnh đã nén + `s3_key` đã tính sẵn theo path
`posts/{user_id}/{timestamp}_{uuid}.jpg`. F05 nhận artifact này
và thực hiện upload + gửi.

> Xem `decision_log.md` → **DL-F04-01** cho quyết định ranh giới
> F04/F05.

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    React Native Client                     │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                   CameraScreen                        │ │
│  │  state: idle → capturing → validating →               │ │
│  │         (blocked | ready)                             │ │
│  │  - back camera preview + shutter                      │ │
│  │  - block overlay + "Chụp lại"                         │ │
│  └───────────────────────┬──────────────────────────────┘ │
│                          │ localUri (raw 720p)            │
│  ┌───────────────────────▼──────────────────────────────┐ │
│  │                  CaptureService                       │ │
│  │  orchestrate: validate → (block?) → compress → build  │ │
│  └───────┬───────────────────────────────┬──────────────┘ │
│          │                               │                │
│  ┌───────▼────────────┐      ┌───────────▼──────────────┐ │
│  │ PetValidationService│      │     ImageCompressor      │ │
│  │ (human detection,   │      │  JPEG q80, resize        │ │
│  │  block decision)    │      │  1280×720                │ │
│  └───────┬────────────┘      └──────────────────────────┘ │
│          │ runs                                            │
│  ┌───────▼─────────────────┐                              │
│  │ _validationModelStub    │  (on-device model runner;    │
│  │ → { human_confidence }  │   TFLite/CoreML thay sau)    │
│  └─────────────────────────┘                              │
│                                                            │
│          CapturedPhoto ──────────────► (handoff → F05)     │
└────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng chính — Chụp ảnh hợp lệ

1. User mở `CameraScreen`; app request camera permission, hiển
   thị preview **camera sau** (FR-1).
2. User nhấn shutter → camera capture ảnh ở **720p
   (1280×720px)** (FR-2). State chuyển `capturing → validating`.
3. `CaptureService.process(localUri, userId)` gọi
   `PetValidationService.validate(localUri)` **trước khi hiển
   thị preview** (FR-3).
4. `human_confidence < HUMAN_BLOCK_THRESHOLD` → ảnh hợp lệ
   (FR-5, FR-8).
5. `ImageCompressor.compress(localUri)` nén JPEG quality 80,
   resize/giữ 1280×720 (FR-9).
6. `CaptureService` tính `s3_key` =
   `posts/{userId}/{timestamp}_{uuid}.jpg` và trả
   `CapturedPhoto` (§2.1). State `validating → ready`.
7. `CameraScreen` chuyển sang flow gửi ảnh của F05, truyền
   `CapturedPhoto` (handoff).

### 1.2 Luồng — Block ảnh có người (high confidence)

1. Bước 1–3 như trên.
2. `human_confidence >= HUMAN_BLOCK_THRESHOLD` →
   `PetValidationService` trả `{ allowed: false }` (FR-4).
3. `CaptureService` **dừng ngay** — KHÔNG nén, KHÔNG tạo
   `CapturedPhoto`, KHÔNG có bất kỳ I/O mạng nào (AC-F04-2).
4. State `validating → blocked`. `CameraScreen` hiển thị overlay
   lỗi "Ảnh không hợp lệ — chỉ được chụp thú cưng" (FR-6).
5. User nhấn "Chụp lại" → state `blocked → idle`, camera mở lại
   (FR-7, AC-F04-5).

### 1.3 Luồng — AI low confidence (ưu tiên UX)

- Khi model không chắc chắn (`human_confidence` nằm dưới
  ngưỡng block), `PetValidationService` trả `allowed: true`.
- Flow tiếp tục như §1.1 (nén + handoff). Đây là lựa chọn ưu
  tiên trải nghiệm người dùng (FR-5, AC-F04-3).

---

## 2. Data Models / Schema

F04 **không có schema database** (xem §0). Mục này định nghĩa
các kiểu dữ liệu client-side (TypeScript interface) là hợp đồng
nội bộ giữa các service.

### 2.1 `CapturedPhoto` — artifact handoff sang F05

```typescript
interface CapturedPhoto {
  /** Local URI của ảnh ĐÃ nén (JPEG q80, 1280×720). */
  localUri: string;
  /** S3 key đã tính: posts/{userId}/{timestamp}_{uuid}.jpg */
  s3Key: string;
  /** Chiều rộng pixel sau nén (1280). */
  width: number;
  /** Chiều cao pixel sau nén (720). */
  height: number;
  /** Thời điểm chụp, ISO 8601 (dùng cho metadata post ở F05). */
  capturedAt: string;
}
```

### 2.2 `ValidationResult` — kết quả AI validation

```typescript
interface ValidationResult {
  /** Độ tin cậy "có người" trong ảnh, [0, 1]. */
  humanConfidence: number;
  /**
   * true nếu được phép upload.
   * false ⇔ humanConfidence >= HUMAN_BLOCK_THRESHOLD (FR-4).
   * low confidence → true (FR-5, ưu tiên UX).
   */
  allowed: boolean;
}
```

### 2.3 `RawValidationModelResult` — đầu ra model runner stub

```typescript
interface RawValidationModelResult {
  /** Xác suất ảnh chứa người, [0, 1]. */
  human_confidence: number;
}
```

### 2.4 Hằng số ngưỡng

```typescript
/** Ngưỡng block khi phát hiện người (FR-4, AC-F04-2). */
const HUMAN_BLOCK_THRESHOLD = 0.70;
```

`0.70` được chọn nhất quán với ngưỡng confidence của F02
(`GENDER_CONFIDENCE_THRESHOLD`). Xem `decision_log.md`
→ **DL-F04-02**.

---

## 3. API Contracts

**Không có.** F04 không gọi backend (xem §0). Mọi xử lý
(capture, validation, compression) đều on-device. Các endpoint
upload/post creation được định nghĩa trong design của F05.

---

## 4. Component Breakdown

### 4.1 React Native Client

```
src/
├── screens/
│   └── CameraScreen.tsx              # camera sau + shutter +
│                                     #   validating/blocked UI
├── services/
│   ├── capture/
│   │   ├── CaptureService.ts         # orchestrate validate →
│   │   │                             #   compress → build artifact
│   │   ├── PetValidationService.ts   # human detection +
│   │   │                             #   block decision
│   │   └── ImageCompressor.ts        # JPEG q80, resize 1280×720
│   └── ai/
│       └── _validationModelStub.ts   # model runner stub
│                                     #   (TFLite/CoreML thay sau)
└── __tests__/capture/
    ├── PetValidationService.test.ts
    ├── ImageCompressor.test.ts
    ├── CaptureService.test.ts
    └── CameraScreen.test.tsx
```

**Trách nhiệm từng component:**

| Component | Trách nhiệm |
|---|---|
| `CameraScreen` | Request camera permission; mở camera sau; capture 720p; quản lý state machine (idle/capturing/validating/blocked/ready); hiển thị block overlay + "Chụp lại"; handoff `CapturedPhoto` sang F05 |
| `CaptureService` | `process(localUri, userId)`: gọi validate → nếu block thì throw/return blocked, nếu pass thì gọi compress + tính `s3Key` + build `CapturedPhoto` |
| `PetValidationService` | `validate(localUri)`: chạy `_validationModelStub`, áp `HUMAN_BLOCK_THRESHOLD`, trả `ValidationResult` |
| `ImageCompressor` | `compress(localUri)`: nén JPEG quality 80, resize 1280×720, trả local URI ảnh mới |
| `_validationModelStub` | Hàm `runValidationModel(uri)` trả `RawValidationModelResult` hardcoded; mock độc lập trong test |

**Ghi chú tích hợp native (deferred):**
- Camera thực (Vision Camera / Expo Camera) và thư viện nén
  (image-resizer / expo-image-manipulator) chưa có trong
  `package.json`. Theo tiền lệ **DL-F03-11**, các service này
  được abstract sau interface injectable để test bằng mock; tích
  hợp native library thực hiện ở task triển khai sau. Xem
  `decision_log.md` → **DL-F04-03**.

### 4.2 Quan hệ với code F02 đã có

- F02 đã có `src/services/ai/PetAIService.ts` (nhận diện
  species/gender) và `_petModelStub.ts`. F04 **không sửa**
  hai file này; thêm `PetValidationService` riêng cho human
  detection (trách nhiệm khác — KISS/SRP).

---

## 5. Error Handling Strategy

F04 không có lỗi mạng (client-only). Các tình huống cần xử lý:

| Tình huống | Xử lý phía client |
|---|---|
| Người dùng từ chối camera permission | Hiển thị hướng dẫn cấp quyền; không mở camera |
| AI phát hiện người (high confidence) | State `blocked`; overlay "Ảnh không hợp lệ — chỉ được chụp thú cưng"; nút "Chụp lại"; KHÔNG nén, KHÔNG handoff (FR-4, FR-6, AC-F04-2) |
| AI low confidence | `allowed: true` → tiếp tục flow (FR-5) |
| Model runner throw lỗi | Bắt lỗi trong `CaptureService`; fail-safe: coi như block + cho phép chụp lại (không để app crash); không handoff |
| Nén ảnh thất bại | Báo lỗi "Không thể xử lý ảnh"; cho phép chụp lại |

**Nguyên tắc bảo mật (AC-F04-2):** Khi bị block, tuyệt đối
không thực hiện bất kỳ I/O mạng nào và không tạo
`CapturedPhoto`. `CaptureService` đảm bảo nén chỉ chạy SAU khi
`validate()` trả `allowed: true`.

---

## 6. Test Strategy

Tất cả test là client-side (Jest + React Native Testing
Library). Viết test TRƯỚC implementation (TDD).

### 6.1 `PetValidationService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_validate_allows_low_confidence` | `human_confidence` dưới ngưỡng → `allowed: true` (FR-5, AC-F04-3) |
| `test_validate_blocks_high_confidence` | `human_confidence >= 0.70` → `allowed: false` (FR-4, AC-F04-2) |
| `test_validate_boundary_at_threshold` | `human_confidence == 0.70` → block (ngưỡng inclusive) |
| `test_validate_returns_confidence` | `ValidationResult.humanConfidence` khớp output model |

### 6.2 `ImageCompressor.test.ts`

| Test case | Mô tả |
|---|---|
| `test_compress_uses_quality_80` | Gọi compressor backend với `quality = 0.8` (FR-9, AC-F04-6) |
| `test_compress_targets_720p` | Output kích thước 1280×720 (FR-2) |
| `test_compress_returns_jpeg_uri` | Trả URI ảnh `.jpg` mới |

### 6.3 `CaptureService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_process_blocked_skips_compression` | Khi `validate` trả `allowed: false`: KHÔNG gọi `ImageCompressor`, KHÔNG trả `CapturedPhoto` (AC-F04-2) |
| `test_process_valid_builds_captured_photo` | Khi pass: gọi compress, trả `CapturedPhoto` với `localUri` đã nén (AC-F04-1) |
| `test_process_s3key_format` | `s3Key` đúng dạng `posts/{userId}/{ts}_{uuid}.jpg` (AC-F04-6) |
| `test_process_sets_dimensions_720p` | `width=1280, height=720` (FR-2, AC-F04-1) |
| `test_process_model_error_no_handoff` | Model throw → không trả `CapturedPhoto`, không crash |

### 6.4 `CameraScreen.test.tsx`

| Test case | Mô tả |
|---|---|
| `test_capture_valid_transitions_ready` | Chụp ảnh hợp lệ → state `ready`, handoff được gọi (AC-F04-1) |
| `test_capture_human_shows_block_overlay` | Bị block → hiển thị message "Ảnh không hợp lệ" (FR-6, AC-F04-2) |
| `test_retake_resets_to_idle` | Nhấn "Chụp lại" → state về `idle`, camera mở lại (FR-7, AC-F04-5) |
| `test_uses_back_camera` | Camera component cấu hình camera sau (FR-1) |

### 6.5 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F04-1 | `test_process_valid_builds_captured_photo`, `test_process_sets_dimensions_720p`, `test_capture_valid_transitions_ready` |
| AC-F04-2 | `test_validate_blocks_high_confidence`, `test_process_blocked_skips_compression`, `test_capture_human_shows_block_overlay` |
| AC-F04-3 | `test_validate_allows_low_confidence` |
| AC-F04-4 | Hiệu năng on-device — không cover bằng unit test; xác minh thủ công trên thiết bị tầm trung (xem §6.6) |
| AC-F04-5 | `test_retake_resets_to_idle` |
| AC-F04-6 | `test_compress_uses_quality_80`, `test_process_s3key_format` |

### 6.6 Ghi chú Test

- `PetValidationService` test dùng `jest.mock` cho
  `_validationModelStub` để stub `human_confidence`.
- `ImageCompressor` test mock backend nén (chưa có native lib);
  chỉ kiểm tra tham số truyền vào (quality, kích thước).
- `CameraScreen` test mock camera bằng `View` với custom prop
  (theo tiền lệ **DL-F03-11**); không test native UI/permission.
- **AC-F04-4 (validation ≤ 3s)** phụ thuộc model thực + thiết
  bị; không thể cover bằng unit test. Khi tích hợp model thật,
  đo thủ công trên thiết bị 4GB RAM.
