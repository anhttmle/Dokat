# F04 — Capture Ảnh + AI Validation — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** React Native (TypeScript) — client-only (DL-F04-01)
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> F04 không có backend (xem Design §0, §3). Mọi task đều thuộc
> React Native client.

---

## 1. Bootstrap F04 structure + test runner

_Tiên quyết cho tất cả task còn lại. Không có dependency ngoài._

**Làm:**
- Tạo các file skeleton (export rỗng / `throw new Error('TODO')`)
  trong client:
  ```
  src/
    screens/
      CameraScreen.tsx
    services/
      capture/
        CaptureService.ts
        PetValidationService.ts
        ImageCompressor.ts
      ai/
        _validationModelStub.ts
    __tests__/capture/
      PetValidationService.test.ts
      ImageCompressor.test.ts
      CaptureService.test.ts
      CameraScreen.test.tsx
  ```
- Định nghĩa các interface dùng chung trong file tương ứng:
  `CapturedPhoto`, `ValidationResult`, `RawValidationModelResult`
  (Design §2).

**Verify:** `npx jest --listTests` liệt kê đúng 4 file test mới.
`npx tsc --noEmit` không báo lỗi type.

**Refs:** Design §4.1

---

## 2. `_validationModelStub` + `PetValidationService`

_Phụ thuộc Task 1. Độc lập với các task khác._

**Test trước:**
```typescript
// __tests__/capture/PetValidationService.test.ts
jest.mock('../../services/ai/_validationModelStub');

it('allows image when human confidence is low', async () => {
  (runValidationModel as jest.Mock).mockResolvedValue({
    human_confidence: 0.20,
  });
  const result = await PetValidationService.validate('file://x.jpg');
  expect(result.allowed).toBe(true);
  expect(result.humanConfidence).toBe(0.20);
});

it('blocks image when human confidence is high', async () => {
  (runValidationModel as jest.Mock).mockResolvedValue({
    human_confidence: 0.95,
  });
  const result = await PetValidationService.validate('file://x.jpg');
  expect(result.allowed).toBe(false);
});

it('blocks at threshold boundary 0.70 (inclusive)', async () => {
  (runValidationModel as jest.Mock).mockResolvedValue({
    human_confidence: 0.70,
  });
  const result = await PetValidationService.validate('file://x.jpg');
  expect(result.allowed).toBe(false);
});
```

**Làm:**
- `_validationModelStub.ts`: hàm `runValidationModel(uri)` trả
  `RawValidationModelResult` hardcoded (giống `_petModelStub` của
  F02). Export named function để mock độc lập.
- `PetValidationService.ts`: `validate(localUri)` gọi
  `runValidationModel`, áp `HUMAN_BLOCK_THRESHOLD = 0.70`
  (inclusive), trả `ValidationResult`.

**Verify:** 4 test pass (gồm `test_validate_returns_confidence`).

**Refs:** Design §2.2, §2.3, §2.4, §4.1; FR-3, FR-4, FR-5;
AC-F04-2, AC-F04-3; DL-F04-02, DL-F04-03

---

## 3. `ImageCompressor`

_Phụ thuộc Task 1. Độc lập với Task 2._

**Test trước:**
```typescript
// __tests__/capture/ImageCompressor.test.ts
it('compresses with JPEG quality 0.8', async () => {
  const backend = jest.fn().mockResolvedValue({
    uri: 'file://out.jpg', width: 1280, height: 720,
  });
  const result = await ImageCompressor.compress('file://in.jpg', backend);
  expect(backend).toHaveBeenCalledWith(
    'file://in.jpg',
    expect.objectContaining({ quality: 0.8, maxWidth: 1280, maxHeight: 720 }),
  );
  expect(result.uri).toBe('file://out.jpg');
});

it('targets 720p output dimensions', async () => {
  const backend = jest.fn().mockResolvedValue({
    uri: 'file://out.jpg', width: 1280, height: 720,
  });
  const result = await ImageCompressor.compress('file://in.jpg', backend);
  expect(result.width).toBe(1280);
  expect(result.height).toBe(720);
});
```

**Làm:**
- `ImageCompressor.ts`: `compress(localUri, backend?)` nhận
  backend nén injectable (mặc định stub no-op cho tới khi tích
  hợp native lib — DL-F04-03). Cấu hình `quality: 0.8`,
  `maxWidth: 1280`, `maxHeight: 720`. Trả `{ uri, width, height }`.

**Verify:** 3 test pass (gồm `test_compress_returns_jpeg_uri`).

**Refs:** Design §4.1; FR-2, FR-9; AC-F04-6; DL-F04-03

---

## 4. `CaptureService` — orchestrate validate → compress → build

_Phụ thuộc Task 2 và Task 3._

**Test trước:**
```typescript
// __tests__/capture/CaptureService.test.ts
jest.mock('../../services/capture/PetValidationService');
jest.mock('../../services/capture/ImageCompressor');

it('skips compression and returns null when blocked', async () => {
  (PetValidationService.validate as jest.Mock).mockResolvedValue({
    humanConfidence: 0.95, allowed: false,
  });
  const result = await CaptureService.process('file://raw.jpg', 'user-1');
  expect(result).toBeNull();
  expect(ImageCompressor.compress).not.toHaveBeenCalled();
});

it('builds CapturedPhoto when valid', async () => {
  (PetValidationService.validate as jest.Mock).mockResolvedValue({
    humanConfidence: 0.10, allowed: true,
  });
  (ImageCompressor.compress as jest.Mock).mockResolvedValue({
    uri: 'file://small.jpg', width: 1280, height: 720,
  });
  const result = await CaptureService.process('file://raw.jpg', 'user-1');
  expect(result?.localUri).toBe('file://small.jpg');
  expect(result?.width).toBe(1280);
  expect(result?.height).toBe(720);
});

it('builds s3Key in posts/{userId}/{ts}_{uuid}.jpg format', async () => {
  // ...mocks allowed:true + compress
  const result = await CaptureService.process('file://raw.jpg', 'user-1');
  expect(result?.s3Key).toMatch(
    /^posts\/user-1\/\d+_[0-9a-f-]+\.jpg$/,
  );
});

it('returns null and does not throw on model error', async () => {
  (PetValidationService.validate as jest.Mock).mockRejectedValue(
    new Error('model failed'),
  );
  const result = await CaptureService.process('file://raw.jpg', 'user-1');
  expect(result).toBeNull();
});
```

**Làm:**
- `CaptureService.ts`: `process(localUri, userId)`:
  1. `PetValidationService.validate(localUri)`.
  2. Nếu `!allowed` → return `null` (KHÔNG nén — AC-F04-2).
  3. `ImageCompressor.compress(localUri)`.
  4. Tính `s3Key = posts/{userId}/{timestamp}_{uuid}.jpg`.
  5. Build + trả `CapturedPhoto` (`capturedAt = ISO now`).
  - Bọc try/catch: model lỗi → return `null`, không crash.

**Verify:** 5 test pass.

**Refs:** Design §1.1, §1.2, §2.1, §4.1, §5; FR-4, FR-8, FR-9;
AC-F04-1, AC-F04-2, AC-F04-6; DL-F04-01

---

## 5. `CameraScreen` — capture, state machine, block/retake

_Phụ thuộc Task 4._

**Test trước:**
```typescript
// __tests__/capture/CameraScreen.test.tsx
jest.mock('../../services/capture/CaptureService');

it('transitions to ready and hands off on valid capture', async () => {
  (CaptureService.process as jest.Mock).mockResolvedValue({
    localUri: 'file://small.jpg', s3Key: 'posts/u/..', width: 1280,
    height: 720, capturedAt: '2026-06-22T00:00:00Z',
  });
  const onReady = jest.fn();
  const { getByTestId } = render(<CameraScreen onReady={onReady} />);
  act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));
  await waitFor(() => expect(onReady).toHaveBeenCalled());
});

it('shows block overlay when capture is rejected', async () => {
  (CaptureService.process as jest.Mock).mockResolvedValue(null);
  const { getByTestId, findByText } = render(<CameraScreen />);
  act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));
  await findByText('Ảnh không hợp lệ — chỉ được chụp thú cưng');
});

it('resets to idle when retake pressed after block', async () => {
  (CaptureService.process as jest.Mock).mockResolvedValue(null);
  const { getByTestId, findByText, queryByText } = render(<CameraScreen />);
  act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));
  await findByText('Ảnh không hợp lệ — chỉ được chụp thú cưng');
  fireEvent.press(getByTestId('retake-button'));
  expect(queryByText('Ảnh không hợp lệ — chỉ được chụp thú cưng'))
    .toBeNull();
});

it('configures back camera', () => {
  const { getByTestId } = render(<CameraScreen />);
  expect(getByTestId('camera').props.position).toBe('back');
});
```

**Làm:**
- `CameraScreen.tsx`:
  - State machine: `idle | capturing | validating | blocked |
    ready`.
  - Camera component (mock-friendly `View` với `testID="camera"`,
    `position="back"`, prop `onCapture(localUri)` — theo
    DL-F03-11/DL-F04-03).
  - `onCapture` → `CaptureService.process(uri, userId)`:
    - trả `CapturedPhoto` → state `ready`, gọi `onReady(photo)`
      (handoff sang F05).
    - trả `null` → state `blocked`, hiển thị overlay lỗi +
      `testID="retake-button"`.
  - "Chụp lại" → state về `idle`.

**Verify:** 4 test pass.

**Refs:** Design §1.1, §1.2, §1.3, §4.1, §5; FR-1, FR-2, FR-6,
FR-7; AC-F04-1, AC-F04-2, AC-F04-5

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **AC-F04-4** (validation ≤ 3 giây): phụ thuộc model thật +
  thiết bị; xác minh thủ công khi tích hợp model, không cover
  bằng unit test (Design §6.6).
- **Tích hợp native** (camera thực + thư viện nén): thực hiện ở
  task triển khai sau, ngoài phạm vi spec F04 (DL-F04-03).
- **Upload S3 + tạo post record**: thuộc F05, không phải F04
  (DL-F04-01).
