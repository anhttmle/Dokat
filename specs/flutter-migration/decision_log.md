# Flutter Migration — Decision Log

## DL-001: Riverpod thay vì BLoC hoặc Provider

**Quyết định:** Dùng `flutter_riverpod ^2` (AsyncNotifier pattern).

**Lý do:** Riverpod compile-safe, không cần BuildContext để đọc state, dễ
test hơn BLoC. Code structure tương đồng với Zustand (store-like notifiers).
Codebase scale của Dokat không đủ lớn để BLoC worth it.

---

## DL-002: go_router thay vì Navigator 2.0 raw

**Quyết định:** Dùng `go_router ^14`.

**Lý do:** Declarative, hỗ trợ deep link, ShellRoute cho bottom nav, cú
pháp route gần với React Navigation. Không cần viết thêm boilerplate.

---

## DL-003: Dio thay vì http package

**Quyết định:** Dùng `dio ^5`.

**Lý do:** Dio có interceptor built-in để inject Bearer token, retry, và
logging — thay thế trực tiếp cho fetch wrapper trong RN services. `http`
package cần viết thêm wrapper.

---

## DL-004: tflite_flutter cho on-device AI

**Quyết định:** Dùng `tflite_flutter ^0.10`.

**Lý do:** Thay thế trực tiếp TFLite/CoreML bridge RN. Cùng model file
`.tflite`, không cần đổi model.

---

## DL-005: mobile_scanner thay vì qr_code_scanner

**Quyết định:** Dùng `mobile_scanner ^6`.

**Lý do:** `qr_code_scanner` không còn maintain. `mobile_scanner` là fork
được maintain tốt, hỗ trợ iOS 14+ và Android minSdk 21+.

---

## DL-006: flutter_secure_storage cho token nhạy cảm

**Quyết định:** Dùng `flutter_secure_storage` cho lưu thông tin nhạy cảm,
`shared_preferences` cho data không nhạy cảm.

**Lý do:** Firebase ID Token tự manage bởi Firebase SDK. `shared_preferences`
đủ cho non-sensitive config. Không cần secure storage cho anonymous session
vì Firebase tự persist.

---

## DL-007: Không dùng freezed/json_serializable

**Quyết định:** Viết domain models thủ công với `fromJson`/`toJson`.

**Lý do:** YAGNI — codebase MVP không đủ phức tạp để cần code generation.
Giảm build setup complexity. Có thể migrate sau nếu cần.

---

## DL-008: Giữ client-rn/ làm reference

**Quyết định:** Không xóa `client-rn/`, chỉ gitignore `node_modules/`.

**Lý do:** RN codebase là reference quan trọng cho business logic và test
cases đã viết.
