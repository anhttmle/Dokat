# F11 — Location & Time Metadata (Store Only) — Tasks

**Refs:** `requirements.md`, `design.md`, `decision_log.md`
**Stack:** React Native (TypeScript) — client-only trong phạm vi F11
(DL-F11-01).
**Convention:** viết test TRƯỚC implementation trong mỗi task.

> Bảng `posts` + endpoint `POST /posts` thuộc **F05** (DL-F11-01).
> F11 chỉ triển khai client `LocationService` + payload builder, và
> đặc tả cột `posts.latitude/longitude` cho F05 (Design §2.3, §3).

---

## 1. Bootstrap F11 structure + test runner

_Tiên quyết cho mọi task còn lại. Không có dependency ngoài._

**Làm:**
- Tạo các file skeleton (export rỗng / `throw new Error('TODO')`):
  ```
  src/
    services/
      location/
        LocationService.ts
        _geolocationBackend.ts
        locationPayload.ts
    __tests__/location/
      LocationService.test.ts
      locationPayload.test.ts
  ```
- Định nghĩa interface dùng chung: `LocationMetadata`,
  `LocationPayload` (Design §2.1, §2.2).

**Verify:** `npx jest --listTests` liệt kê đúng 2 file test mới.
`npx tsc --noEmit` không báo lỗi type.

**Refs:** Design §4.1

---

## 2. `_geolocationBackend` + `LocationService.getCurrentLocation`

_Phụ thuộc Task 1._

**Test trước:**
```typescript
// __tests__/location/LocationService.test.ts
jest.mock('../../services/location/_geolocationBackend');

it('returns coords when permission granted', async () => {
  (requestPermission as jest.Mock).mockResolvedValue('granted');
  (getCurrentPosition as jest.Mock).mockResolvedValue({
    latitude: 10.776215, longitude: 106.695058,
  });
  const result = await LocationService.getCurrentLocation();
  expect(result).toEqual({
    latitude: 10.776215, longitude: 106.695058,
  });
});

it('returns null and skips read when permission denied', async () => {
  (requestPermission as jest.Mock).mockResolvedValue('denied');
  const result = await LocationService.getCurrentLocation();
  expect(result).toBeNull();
  expect(getCurrentPosition).not.toHaveBeenCalled();
});

it('returns null on position error (fail-safe)', async () => {
  (requestPermission as jest.Mock).mockResolvedValue('granted');
  (getCurrentPosition as jest.Mock).mockRejectedValue(
    new Error('gps timeout'),
  );
  const result = await LocationService.getCurrentLocation();
  expect(result).toBeNull();
});

it('reads position only once', async () => {
  (requestPermission as jest.Mock).mockResolvedValue('granted');
  (getCurrentPosition as jest.Mock).mockResolvedValue({
    latitude: 1, longitude: 2,
  });
  await LocationService.getCurrentLocation();
  expect(getCurrentPosition).toHaveBeenCalledTimes(1);
});
```

**Làm:**
- `_geolocationBackend.ts`: export named `requestPermission()` +
  `getCurrentPosition()`; stub (native lib thay sau — DL-F11-02).
- `LocationService.ts`: `getCurrentLocation()`:
  1. `requestPermission()`; nếu != `'granted'` → return `null`
     (KHÔNG đọc toạ độ — FR-3).
  2. `getCurrentPosition()` → trả `{ latitude, longitude }`.
  3. Bọc try/catch: lỗi đọc toạ độ → return `null` (fail-safe §5).

**Verify:** 4 test pass.

**Refs:** Design §1.1, §1.2, §2.1, §4.1, §5; FR-1, FR-2, FR-3;
AC-F11-1, AC-F11-2; DL-F11-02

---

## 3. `buildLocationPayload` — map metadata → POST body fields

_Phụ thuộc Task 1. Độc lập với Task 2._

**Test trước:**
```typescript
// __tests__/location/locationPayload.test.ts
it('includes coords when location present', () => {
  const payload = buildLocationPayload({
    latitude: 10.776215, longitude: 106.695058,
  });
  expect(payload).toEqual({
    latitude: 10.776215, longitude: 106.695058,
  });
});

it('returns empty object when location is null', () => {
  expect(buildLocationPayload(null)).toEqual({});
});

it('preserves full coordinate precision', () => {
  const payload = buildLocationPayload({
    latitude: 10.12345678, longitude: 106.87654321,
  });
  expect(payload.latitude).toBe(10.12345678);
  expect(payload.longitude).toBe(106.87654321);
});
```

**Làm:**
- `locationPayload.ts`: `buildLocationPayload(loc)`:
  `LocationMetadata | null` → `{ latitude, longitude }` khi có toạ
  độ, hoặc `{}` khi `null` (không thêm field — AC-F11-2). Không làm
  tròn giá trị (Technical Constraint).

**Verify:** 3 test pass.

**Refs:** Design §1.1, §1.2, §2.2, §4.1, §3.1; FR-3, FR-4;
AC-F11-1, AC-F11-2

---

## 4. Đặc tả contract backend cho F05 (cột posts + non-expose)

_Phụ thuộc Task 3. Không sinh code backend trong F11 (DL-F11-01)._

**Làm:**
- Xác nhận `design.md` §2.3 + §3 đã đặc tả đầy đủ cho F05:
  - Bảng `posts` thêm `latitude DECIMAL(11, 8)` /
    `longitude DECIMAL(12, 8)` nullable (migration tạo bảng `posts`
    của F05 phải bao gồm).
  - `POST /posts` nhận `latitude`/`longitude` optional, validate
    [-90, 90] / [-180, 180] (Pydantic) → 422 nếu sai khoảng.
  - **Không** expose lat/lng trong bất kỳ response model nào
    (feed/history/seen) — AC-F11-3.
- Ghi rõ trong `decision_log.md` (DL-F11-01) rằng các test sau thuộc
  integration suite của F05:
  - post lưu lat/lng đúng độ chính xác 8 chữ số khi có quyền
    (AC-F11-1).
  - post lưu `NULL` khi không có quyền (AC-F11-2).
  - response feed/history/seen không chứa lat/lng (AC-F11-3).

**Verify:** `design.md` §2.3/§3 và `decision_log.md` DL-F11-01 phản
ánh đúng contract; không có file backend nào được tạo trong F11.

**Refs:** Design §0, §2.3, §3, §6.3; FR-4, FR-5; AC-F11-1, AC-F11-2,
AC-F11-3; DL-F11-01

---

## Ghi chú phạm vi (không nằm trong các task trên)

- **Persist DB + validate server** (`posts.latitude/longitude`, 422,
  non-expose): hiện thực + test trong **F05** (DL-F11-01).
- **Tích hợp native geolocation** (lib thực + permission dialog):
  task triển khai sau, ngoài phạm vi spec F11 (DL-F11-02).
- **Lấy toạ độ tại thời điểm chụp tuyệt đối**: MVP lấy ở bước gửi của
  F05; chuyển vào `CameraScreen` nếu cần độ chính xác cao hơn về sau
  (DL-F11-03).
