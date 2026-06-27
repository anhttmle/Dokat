---
name: verify-api-contract
description: >-
  Rà soát contract mismatch giữa Flutter service và FastAPI backend schema
  trong dự án Dokat. Dùng khi user nói "verify contract", "check API mismatch",
  "kiểm tra client-BE", "tích hợp client backend", hoặc trước khi chạy thật
  sau khi implement một feature mới.
---

# Verify API Contract — Client ↔ Backend

## Context nhanh

Backend là **source of truth**. Flutter services nằm ở
`client/lib/features/*/data/`. Backend schemas nằm ở
`backend/app/schemas/`. Xem bảng đầy đủ ở `AGENT.md §7`.

## Workflow

### Bước 1: Xác định phạm vi

Feature nào cần verify? (F01–F11)  
Lấy danh sách endpoints từ `backend/app/routers/<feature>.py`.

### Bước 2: Đọc song song

| Đọc | File |
|-----|------|
| Backend schema | `backend/app/schemas/<feature>.py` |
| Backend router | `backend/app/routers/<feature>.py` |
| Flutter service | `client/lib/features/<feature>/data/<name>_service.dart` |

### Bước 3: Checklist 6 điểm (hay nhầm nhất)

Kiểm tra từng điểm bên dưới:

**1. Response wrapping**
Backend thường wrap list trong object — không trả list thẳng:
```
GET /pets            → { pets: [...] }       ✓ / response.data trực tiếp ✗
GET /friends         → { friends: [...] }
GET /users/block     → { blocked: [...] }
GET /feed            → { items: [...] }
GET /posts/{id}/seen-by → { viewers: [...] }
GET /pets/{id}/photos   → { photos: [...] }
```

**2. Field names trong request body**
```
POST /friends/qr/scan  → token (không phải otp)
POST /posts            → s3_key + cdn_url (không phải image_url)
POST /posts            → latitude, longitude flat (không phải location nested)
POST /users/block      → user_id (không phải target_user_id)
POST /users/report     → user_id (không phải target_user_id)
PATCH /pets/{id}/link-photo → photo_id UUID (không phải photo_url)
```

**3. Upload URL response**
`POST /posts/upload-url` trả 3 field:
```
{ upload_url, object_key, cdn_url, expires_in }
```
Client phải lấy `object_key` (= s3_key) và `cdn_url` — không chỉ `upload_url`.

**4. Feed image key**
`GET /feed` → `cdn_url` (không phải `image_url`), `seen: bool` (không phải `seen_by_me`).

**5. Method return type**
- `CaptureService.uploadImage()` → `void` (CDN URL lấy từ presigned response)
- `LocationService.getCurrentPayload()` → `LocationPayload?` (không phải `Map?`)

**6. Dio response type generic**
Nếu backend trả object thì dùng `get<Map<String, dynamic>>`, không phải `get<List<dynamic>>`.

### Bước 4: Báo cáo

Liệt kê:
```
Feature | Service method | Gap | Cần sửa
```

Với mỗi gap: file cần sửa + dòng thay đổi cụ thể.

### Bước 5: Ghi decision log

Với mỗi gap đã sửa, thêm entry vào `specs/<feature>/decision_log.md`
theo format DL-FXX-N (xem `sdd-task-execute` skill).

## Tham chiếu nhanh

- Field names đúng: `AGENT.md §7` — bảng "Field name dễ nhầm"
- Response shapes: `AGENT.md §7` — bảng "Response shape quan trọng"
- Upload flow F05: `AGENT.md §7` — "Luồng upload ảnh"
- Decision logs đã có: `specs/f*/decision_log.md` (DL-F02-20, DL-F03-14, DL-F05-11, DL-F06-11, DL-F07-11, DL-F10-13)
