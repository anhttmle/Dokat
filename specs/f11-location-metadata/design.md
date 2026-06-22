# F11 — Location & Time Metadata (Store Only) — Design

**Version:** 1.0.0
**Date:** 2026-06-22
**Status:** Draft

---

## 0. Scope & Boundary (F11 vs F05)

F11 gắn metadata vị trí (lat/lng) + thời gian vào ảnh chụp, chỉ
**lưu**, không hiển thị (FR-5, Non-goal). Phạm vi F11 chia làm hai
phần rõ ràng:

1. **Phần triển khai được ngay trong F11 (client-only):**
   `LocationService` — xin quyền location và lấy toạ độ **một lần**
   tại thời điểm chụp/gửi; trả `null` khi người dùng từ chối quyền.
2. **Phần hợp đồng (contract) cho F05:** bảng `posts` có thêm hai cột
   `latitude DECIMAL(11, 8)` / `longitude DECIMAL(12, 8)` nullable, và
   endpoint `POST /posts` nhận thêm hai field optional `latitude` /
   `longitude`. Backend lưu nguyên giá trị, **không** expose lại qua
   bất kỳ response nào.

Theo **DL-F04-01**, bảng `posts` và endpoint `POST /posts` thuộc phạm
vi **F05 — Gửi Ảnh** (chưa tồn tại tại thời điểm F11 chạy: thứ tự
thực thi là F04 → F11 → F05). Vì vậy F11 **không** tạo migration
độc lập đụng vào bảng `posts` chưa có. Thay vào đó F11 **đặc tả** cột
+ field POST body như một hợp đồng để migration tạo bảng `posts` của
F05 hiện thực hoá.

> Xem `decision_log.md` → **DL-F11-01** (ranh giới F11/F05) và
> **DL-F11-03** (thời điểm lấy toạ độ).

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    React Native Client                     │
│                                                            │
│  (F04) CameraScreen ──capture──► CapturedPhoto             │
│                                       │                    │
│  (F05) Send flow  ◄───────────────────┘                    │
│        │                                                   │
│        │ lúc gửi: lấy toạ độ một lần                       │
│        ▼                                                   │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                  LocationService                      │ │
│  │  getCurrentLocation():                                │ │
│  │    requestPermission → granted?                       │ │
│  │      ├─ yes → read coords → { latitude, longitude }   │ │
│  │      └─ no  → null  (FR-3)                             │ │
│  └───────────────────────┬──────────────────────────────┘ │
│                          │ runs                            │
│  ┌───────────────────────▼──────────────────────────────┐ │
│  │ _geolocationBackend (injectable)                     │ │
│  │  requestPermission() / getCurrentPosition()          │ │
│  │  native lib thay sau (DL-F11-02)                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  buildLocationPayload(loc) → { latitude?, longitude? }     │
│        │ merge vào POST /posts body (do F05 gọi)           │
└────────┼───────────────────────────────────────────────────┘
         │ HTTPS POST /posts { ..., latitude?, longitude? }
         ▼
┌────────────────────────────────────────────────────────────┐
│              FastAPI Backend (hiện thực ở F05)             │
│  posts.latitude  DECIMAL(11, 8) NULL  ◄── contract F11     │
│  posts.longitude DECIMAL(12, 8) NULL  ◄── contract F11     │
│  KHÔNG trả lat/lng trong bất kỳ GET response nào (AC-F11-3)│
└────────────────────────────────────────────────────────────┘
```

### 1.1 Luồng — Có quyền location (AC-F11-1)

1. User chụp ảnh (F04) và vào flow gửi (F05).
2. Send flow gọi `LocationService.getCurrentLocation()`.
3. `LocationService` gọi `requestPermission()`; người dùng đã/đang
   cấp quyền → `granted` (FR-1, FR-2).
4. `getCurrentPosition()` trả toạ độ; `LocationService` trả
   `{ latitude, longitude }` (số thực, đầy đủ độ chính xác GPS).
5. `buildLocationPayload(loc)` → `{ latitude, longitude }` được merge
   vào body `POST /posts`.
6. Backend (F05) lưu vào `posts.latitude` / `posts.longitude` ở độ
   chính xác 8 chữ số thập phân (FR-4, AC-F11-1).

### 1.2 Luồng — Từ chối quyền location (AC-F11-2)

1. Bước 1–3 như trên; người dùng **từ chối** quyền.
2. `LocationService.getCurrentLocation()` trả `null` (FR-3).
3. `buildLocationPayload(null)` → `{}` (không có field lat/lng).
4. Send flow gửi ảnh **bình thường**; backend lưu post với
   `latitude = NULL`, `longitude = NULL` (AC-F11-2).

### 1.3 Luồng — Không hiển thị location (AC-F11-3)

- Backend **không** đưa `latitude` / `longitude` vào bất kỳ schema
  response nào (feed, history, seen). Dữ liệu chỉ dùng nội bộ
  (Technical Constraint). Do đó không có UI nào nhận được toạ độ để
  hiển thị (AC-F11-3).

---

## 2. Data Models / Schema

### 2.1 Client — `LocationMetadata` (TypeScript)

```typescript
interface LocationMetadata {
  /** Vĩ độ thiết bị tại thời điểm chụp/gửi, [-90, 90]. */
  latitude: number;
  /** Kinh độ thiết bị tại thời điểm chụp/gửi, [-180, 180]. */
  longitude: number;
}
```

`getCurrentLocation()` trả `LocationMetadata | null` — `null` khi
không có quyền hoặc đọc toạ độ thất bại (FR-3).

### 2.2 Client — `LocationPayload` (phần body POST /posts)

```typescript
interface LocationPayload {
  /** Có mặt chỉ khi lấy được toạ độ; nếu không → bỏ field. */
  latitude?: number;
  longitude?: number;
}
```

### 2.3 Backend — cột bổ sung trên bảng `posts` (contract cho F05)

| Cột | Kiểu | Null | Mô tả |
|---|---|---|---|
| `latitude` | `DECIMAL(11, 8)` | YES | Vĩ độ; `NULL` khi không có quyền (AC-F11-2) |
| `longitude` | `DECIMAL(12, 8)` | YES | Kinh độ; `NULL` khi không có quyền |

- Độ chính xác 8 chữ số thập phân giữ độ chính xác GPS tối đa
  (Technical Constraint, AC-F11-1).
- Hai cột **chỉ dùng nội bộ**; tuyệt đối không đưa vào response model
  (AC-F11-3).
- Migration tạo hai cột này nằm trong migration tạo bảng `posts` của
  **F05** (DL-F11-01), không phải migration riêng của F11.

---

## 3. API Contracts

F11 **không tạo endpoint mới**. F11 chỉ **mở rộng hợp đồng** của
`POST /posts` (do F05 hiện thực).

### 3.1 `POST /posts` — phần mở rộng do F11 (request)

```jsonc
{
  // ...các field do F05 định nghĩa (s3_key, recipient_ids, ...)
  "latitude": 10.77621500,   // optional, có khi user cấp quyền
  "longitude": 106.69505800  // optional
}
```

- Hai field **optional**. Vắng mặt ⇒ lưu `NULL` (AC-F11-2).
- Validate phía server (do F05): nếu có mặt, `latitude` ∈ [-90, 90],
  `longitude` ∈ [-180, 180] (Pydantic). Giá trị ngoài khoảng → 422.

### 3.2 Response

- **Không** field location nào xuất hiện trong response của
  `POST /posts`, `GET /feed`, `GET /history/*`, hay `GET
  /posts/{id}/seen-by` (AC-F11-3, Technical Constraint).

---

## 4. Component Breakdown

### 4.1 React Native Client (phạm vi triển khai F11)

```
src/
├── services/
│   └── location/
│       ├── LocationService.ts        # xin quyền + lấy toạ độ 1 lần
│       ├── _geolocationBackend.ts    # backend native injectable
│       │                             #   (stub; native lib thay sau)
│       └── locationPayload.ts        # LocationMetadata → body fields
└── __tests__/location/
    ├── LocationService.test.ts
    └── locationPayload.test.ts
```

| Component | Trách nhiệm |
|---|---|
| `LocationService` | `getCurrentLocation()`: gọi `requestPermission()`; nếu granted → `getCurrentPosition()` → `LocationMetadata`; nếu denied/lỗi → `null` (FR-1, FR-2, FR-3) |
| `_geolocationBackend` | Abstraction quanh native geolocation (`requestPermission`, `getCurrentPosition`); stub mockable, native lib tích hợp sau (DL-F11-02) |
| `locationPayload` | `buildLocationPayload(loc)`: `LocationMetadata \| null` → `{ latitude, longitude }` hoặc `{}` để merge vào POST body |

### 4.2 Quan hệ với F04 / F05

- **Không sửa** `CaptureService` của F04 (đã seal — DL-F04-01). Toạ độ
  được lấy ở bước **gửi** của F05, không gắn vào `CapturedPhoto`
  (DL-F11-03).
- F05 là consumer: gọi `LocationService.getCurrentLocation()` rồi
  `buildLocationPayload()` khi dựng body `POST /posts`, và migration
  bảng `posts` của F05 thêm hai cột ở §2.3.

---

## 5. Error Handling Strategy

| Tình huống | Xử lý phía client |
|---|---|
| Người dùng từ chối quyền location | `getCurrentLocation()` trả `null`; gửi ảnh vẫn tiếp tục bình thường (FR-3, AC-F11-2) |
| `getCurrentPosition()` throw / timeout | Bắt lỗi trong `LocationService`; trả `null` (fail-safe: location là optional, không chặn việc gửi ảnh) |
| Toạ độ ngoài khoảng hợp lệ (server) | F05 validate bằng Pydantic → 422 (đặc tả §3.1) |

**Nguyên tắc:** location là metadata **không bắt buộc**. Mọi lỗi liên
quan location **không được** chặn luồng chụp/gửi ảnh (FR-3).

---

## 6. Test Strategy

Test F11 là client-side (Jest). Viết test TRƯỚC implementation (TDD).
Phần lưu DB + validate server được test trong integration suite của
**F05** (DL-F11-01); F11 đặc tả các case đó dưới đây để F05 phủ.

### 6.1 `LocationService.test.ts`

| Test case | Mô tả |
|---|---|
| `test_returns_coords_when_permission_granted` | Permission granted + `getCurrentPosition` trả toạ độ → `{ latitude, longitude }` đúng giá trị (FR-2, AC-F11-1) |
| `test_returns_null_when_permission_denied` | Permission denied → trả `null`, **không** gọi `getCurrentPosition` (FR-3, AC-F11-2) |
| `test_returns_null_on_position_error` | `getCurrentPosition` reject → trả `null`, không throw (fail-safe §5) |
| `test_reads_position_once` | Gọi `getCurrentPosition` đúng **một** lần — không tracking liên tục (Technical Constraint) |

### 6.2 `locationPayload.test.ts`

| Test case | Mô tả |
|---|---|
| `test_payload_includes_coords_when_present` | `LocationMetadata` → `{ latitude, longitude }` (AC-F11-1) |
| `test_payload_empty_when_null` | `null` → `{}` (không field lat/lng) (AC-F11-2) |
| `test_payload_preserves_precision` | Giá trị toạ độ giữ nguyên độ chính xác, không làm tròn (Technical Constraint) |

### 6.3 Acceptance Criteria Mapping

| AC | Test phủ |
|---|---|
| AC-F11-1 | `test_returns_coords_when_permission_granted`, `test_payload_includes_coords_when_present`; (DB persist độ chính xác 8 chữ số → integration F05) |
| AC-F11-2 | `test_returns_null_when_permission_denied`, `test_payload_empty_when_null`; (post lưu `NULL` → integration F05) |
| AC-F11-3 | Đặc tả §3.2 (không expose lat/lng); kiểm chứng ở response-schema test của F05 |

### 6.4 Ghi chú Test

- `_geolocationBackend` được mock bằng `jest.mock` để giả lập
  permission granted/denied và toạ độ (tiền lệ **DL-F04-03**).
- Test **không** kiểm tra native permission dialog hay GPS thật — chỉ
  kiểm tra business logic (permission gate, một-lần-đọc, mapping
  payload).
- Phần backend (cột `posts.latitude/longitude`, validate 422,
  không-expose) được phủ trong integration suite của **F05** vì bảng
  `posts` thuộc F05 (DL-F11-01).
