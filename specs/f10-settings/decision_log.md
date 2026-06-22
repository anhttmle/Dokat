# F10 — Settings — Decision Log

---

## DL-F10-01 — Liên kết dùng lại `POST /auth/link` (F01); F10 chỉ thêm unlink

**Date:** 2026-06-22
**Context:** FR-1/FR-2 yêu cầu hiển thị trạng thái và liên kết
provider. F01 đã có `POST /auth/link` (link provider) và
`POST /auth/session` trả `providers`.
**Decision:** F10 **không** tạo endpoint link mới. Client liên kết
bằng `AuthService.linkWithProvider` + `POST /auth/link` (F01) và đọc
trạng thái từ session. F10 **chỉ** thêm endpoint *hủy* liên kết
`DELETE /users/providers/{provider}`.
**Consequence:** Giảm trùng lặp (DRY); test link thuộc F01, F10 chỉ
test unlink + render trạng thái.

---

## DL-F10-02 — Unlink: guard provider cuối; Firebase unlink ở client

**Date:** 2026-06-22
**Context:** FR-3 yêu cầu chỉ cho hủy liên kết khi còn ≥1 provider
khác (tránh khóa tài khoản). Technical Constraint: unlink qua
Firebase Auth API.
**Decision:** Backend `account_service.unlink_provider` đếm số
`user_providers` của user; nếu provider là duy nhất → raise
`LastProviderError` → **422 `LAST_PROVIDER`**, không xoá. Nếu hợp lệ
→ xoá row `user_providers`. Thao tác unlink phía Firebase do
**client** gọi (`AuthService`); backend chỉ đồng bộ DB.
**Consequence:** Không khóa tài khoản; AC-F10-2 phủ ở service +
router + UI. Firebase native không unit-test.

---

## DL-F10-03 — Block: yêu cầu bạn bè, xoá friendship, silent

**Date:** 2026-06-22
**Context:** FR-4 chỉ cho block người trong danh sách bạn bè; khi
block thì friendship bị xoá và hai bên không gửi ảnh được. FR-5 yêu
cầu block **silent**.
**Decision:** `block_service.block_user` kiểm tra friendship tồn tại
(else `NotFriendsError` → 422 `NOT_FRIENDS`), rồi gọi
`friend_service.delete_friendship` + upsert `blocked_users`
(idempotent). **Không** gọi `NotificationService` ở luồng block.
**Consequence:** Vì recipient của F05 phải là bạn bè, xoá friendship
tự động chặn gửi ảnh hai chiều. Block lặp lại an toàn (UNIQUE pair +
idempotent service).

---

## DL-F10-04 — Loại trừ block hai chiều bằng cách điền hook F06

**Date:** 2026-06-22
**Context:** FR-8 yêu cầu ẩn ảnh người bị block khỏi feed. F06 đã
chừa hook `feed_service._blocked_sender_ids` trả `set()` rỗng
(DL-F06-03).
**Decision:** F10 thêm `block_service.get_blocked_user_ids(db,
user_id)` trả tập **hai chiều**: người mà user đã chặn ∪ người đã
chặn user. Sửa thân `_blocked_sender_ids` để gọi helper này. **Không**
đổi cấu trúc query feed.
**Consequence:** A block B → ảnh B ẩn khỏi feed A và ảnh A ẩn khỏi
feed B. Thay đổi tối thiểu, đúng điểm tích hợp F06 đã thiết kế.

---

## DL-F10-05 — Unblock không khôi phục friendship; idempotent

**Date:** 2026-06-22
**Context:** Sau khi block đã xoá friendship (DL-F10-03), unblock cần
hành vi rõ ràng.
**Decision:** `unblock_user` chỉ xoá row `blocked_users` (no-op nếu
không có → idempotent, 204). **Không** tự kết bạn lại; hai người
phải dùng QR (F03) để thành bạn bè lại.
**Consequence:** Tránh khôi phục quan hệ ngoài ý muốn; nhất quán mô
hình "kết bạn chủ động" của F03.

---

## DL-F10-06 — Report reasons enum cố định; report không tự xử lý

**Date:** 2026-06-22
**Context:** FR-6 liệt kê danh sách lý do cố định (spam, nội dung
không phù hợp, quấy rối, khác); FR-7 yêu cầu lưu cho Admin. AC-F10-5
nói report **không** ẩn người dùng tự động.
**Decision:** `report_reason` là enum `{spam, inappropriate,
harassment, other}`. `report_service.report_user` validate enum
(else `InvalidReasonError` → 422 `INVALID_REASON`) và lưu
`reports`. Report **không** tạo block / ẩn người dùng.
**Consequence:** Moderation xử lý thủ công sau; client chỉ hiển thị
xác nhận. Cho phép report nhiều lần (không UNIQUE).

---

## DL-F10-07 — Logout xoá `fcm_token`; phần native ở client

**Date:** 2026-06-22
**Context:** FR-9/FR-10 yêu cầu logout xoá local session + device
token và điều hướng về Onboarding.
**Decision:** `POST /users/logout` →
`account_service.clear_device_token` set `users.fcm_token = None`
(idempotent) để chặn push tới thiết bị đã đăng xuất. Client
`AuthService.signOut` (Firebase) + clear `LocalStorageService` +
nav Onboarding.
**Consequence:** Push không tới thiết bị cũ sau logout. Phần Firebase
signOut + storage clear là native, không unit-test sâu.

---

## DL-F10-08 — Router `settings.py` prefix `/users`; resolve caller chuẩn

**Date:** 2026-06-22
**Context:** Các endpoint đặt dưới `/users/...` (block/report/logout)
và `/users/providers/...`.
**Decision:** Tạo `routers/settings.py` với
`APIRouter(prefix="/users", tags=["settings"])`. Resolve
`firebase_uid → user UUID` bằng helper `_get_user_id` (theo tiền lệ
`routers/friends.py`/`posts.py`); chưa có row → **404
`USER_NOT_FOUND`**. Đăng ký trong `main.py`.
**Consequence:** Nhất quán pattern auth/error toàn backend; không tạo
user ngầm (YAGNI).

---

## DL-F10-09 — Thêm `GET /users/block` để hỗ trợ UI bỏ chặn

**Date:** 2026-06-22
**Context:** FR-8 yêu cầu quản lý người bị block; muốn bỏ chặn cần
biết danh sách đã chặn. Requirements không mô tả màn hình riêng.
**Decision:** Thêm endpoint tối thiểu `GET /users/block` trả danh
sách `BlockedUserItem` (JOIN `users` lấy `display_name`,
`avatar_url`). Hiển thị trong `SettingsScreen`.
**Consequence:** Cho phép bỏ chặn từ UI mà không mở rộng phạm vi
ngoài Non-goals. Chỉ caller xem danh sách block của chính mình.

---

## DL-F10-10 — Không sửa `friend_service`; ẩn bạn bè là hệ quả của xoá friendship

**Date:** 2026-06-22
**Context:** FR-8 yêu cầu ẩn người bị block khỏi danh sách bạn bè.
Block đã xoá friendship (DL-F10-03).
**Decision:** **Không** thêm filter block vào `friend_service.
list_friends`. Vì block xoá friendship, người bị block tự động vắng
mặt trong `GET /friends`.
**Consequence:** Thay đổi tối thiểu (surgical). Test integration
verify `GET /friends` không còn người bị block.

---

## DL-F10-11 — Self-block/self-report bị từ chối ở service; không CHECK ở DB

**Date:** 2026-06-22
**Context:** Cần chặn block/report chính mình. SQLite không xử lý
`CHECK` đồng nhất với PostgreSQL (tiền lệ DL-F03-01).
**Decision:** Không đặt `CHECK (blocker_id <> blocked_id)` ở DB.
Service raise `SelfBlockError`/`SelfReportError` → **422
`SELF_BLOCK`/`SELF_REPORT`**.
**Consequence:** Validation ở một chỗ (service); nhất quán cách
friendship xử lý self-friend (F03).

---

## DL-F10-12 — Test migration theo ORM metadata (không chạy Alembic trên SQLite)

**Date:** 2026-06-22
**Context:** Design §6.6 yêu cầu test migration (upgrade tạo bảng +
UNIQUE/enum, downgrade gỡ bảng). Toàn bộ migration test hiện có
(`test_posts_migration.py`, `test_friendships_migration.py`, …) dùng
`Base.metadata.create_all` trên SQLite in-memory, vì các migration thật
là PostgreSQL-specific (`gen_random_uuid()`, `postgresql.ENUM`) và không
chạy được trên SQLite.
**Decision:** `test_migration_settings.py` theo đúng tiền lệ: dùng ORM
metadata làm nguồn sự thật để kiểm `blocked_users`/`reports` tồn tại,
UNIQUE pair, FK, cột `reason`; `test_downgrade_drops_tables` dùng
`Base.metadata.drop_all` cho 2 bảng. File migration Alembic vẫn viết
theo style PG như các sibling (`b2c3d4e5f6a7_*`).
**Consequence:** Nhất quán toàn repo, không thêm phụ thuộc test; verify
schema contract §2.1/§2.2 mà không cần PostgreSQL trong unit test.
