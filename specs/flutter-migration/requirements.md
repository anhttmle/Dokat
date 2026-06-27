# Flutter Migration — Requirements

## Goal

Migrate toàn bộ client Dokat từ React Native 0.76 (TypeScript) sang Flutter
(Dart), giữ nguyên backend FastAPI và tất cả 11 features (F01–F11).

## Scope

- Thư mục `client/` mới là Flutter project.
- Thư mục `client-rn/` giữ nguyên làm reference (React Native cũ).
- Backend (`backend/`) không thay đổi.
- Tất cả spec feature F01–F11 vẫn là source of truth; migration chỉ thay đổi
  platform, không thay đổi yêu cầu nghiệp vụ.

## Functional Requirements

1. Tất cả Acceptance Criteria trong F01–F11 phải được thỏa mãn bởi Flutter
   client.
2. Flutter client phải gọi đúng tất cả API endpoints đang dùng trong RN client
   (35+ endpoints, base `http://localhost:8000` cho dev).
3. Firebase Anonymous Auth và OAuth (Apple/Google/Facebook) phải hoạt động
   như F01 quy định.
4. On-device AI validation (F04) phải chạy bằng `tflite_flutter` — không gọi
   server.
5. QR generate và scan (F03) phải hoạt động trên cả iOS và Android.
6. Push notification (F09) qua Firebase Cloud Messaging phải hoạt động trên
   cả hai platform.

## Non-goals

- Không thay đổi bất kỳ business logic nào ở backend.
- Không thêm feature mới ngoài F01–F11.
- Không implement web/desktop Flutter — chỉ iOS + Android.

## Technical Constraints

- Flutter SDK >= 3.22.0.
- Dart SDK >= 3.4.0.
- `minSdkVersion` Android: 24 (giữ nguyên).
- iOS deployment target: 14.0 (tương đương RN cũ).
- Bundle ID giữ nguyên: `com.carbonix.dokat`.
- `google-services.json` và `GoogleService-Info.plist` phải được đặt thủ
  công (gitignore'd).

## Acceptance Criteria

**AC-MIG-1:** App khởi động thành công trên Android emulator sau khi setup.

**AC-MIG-2:** Tất cả AC từ F01–F11 được thỏa mãn bởi Flutter client.

**AC-MIG-3:** `flutter test` pass với coverage >= 80% cho services và
providers.

**AC-MIG-4:** `flutter analyze` không có error.
