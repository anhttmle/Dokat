# F06 — Feed & App View — Decision Log

---

## DL-F06-01 — F06 là tính năng đọc-only; chỉ thêm `GET /feed`

**Date:** 2026-06-22
**Context:** Requirements F06 mô tả hiển thị ảnh đã nhận. Dữ liệu
(`posts`, `post_recipients`) đã do F05 tạo. Câu hỏi: F06 có cần
ghi/sửa dữ liệu nào không.
**Decision:** F06 **không** INSERT/UPDATE/DELETE bất kỳ bảng nào;
chỉ thêm một endpoint đọc `GET /feed` và các thành phần client.
Việc đánh dấu seen (ghi) được uỷ cho F07 (DL-F06-02).
**Consequence:** `GET /feed` idempotent — refresh an toàn vô hạn.
Không có rủi ro ghi sai dữ liệu trong F06; test chỉ cần seed dữ
liệu F05 rồi assert kết quả đọc.

---

## DL-F06-02 — Cờ `seen` đọc ở F06, persist (`POST /posts/{id}/seen`) thuộc F07

**Date:** 2026-06-22
**Context:** FR-5 ("đánh dấu đã xem khi mở full-screen") và FR-6
("phân biệt seen/unseen") thuộc F06. Nhưng cột
`post_recipients.seen_at` và endpoint ghi seen thuộc F07
(DL-F05-04, thứ tự F06 → F07).
**Decision:** F06 **đọc** `seen_at` để suy ra cờ `seen` cho mỗi
feed item (FR-6) và render indicator (FR-6, AC-F06-3). Khi mở
full-screen, `FeedScreen` cập nhật **optimistic** `seen=true` cục
bộ và gọi `FeedService.markSeen(postId)` — một **điểm tích hợp**
để F07 cắm network call `POST /posts/{id}/seen` vào. F06 **không**
gọi network seen.
**Consequence:** AC-F06-3 phần "persist sang DB" được phủ ở F07.
F06 test chỉ verify: đọc đúng cờ seen, render indicator, optimistic
toggle + gọi hook. Tránh implement trùng endpoint seen ở hai
feature.

---

## DL-F06-03 — Loại trừ block qua hook rỗng cho đến khi F10

**Date:** 2026-06-22
**Context:** FR-10 yêu cầu loại ảnh từ người bị block, ghi rõ "(xem
F10)". Bảng `blocked_users` chưa tồn tại ở thời điểm F06 (F10 sau
F06).
**Decision:** Feed query đã **block-aware**: lọc
`posts.user_id NOT IN _blocked_sender_ids(db, viewer_id)`. Helper
`_blocked_sender_ids` trả về `set()` (rỗng) cho đến khi F10 hiện
thực bảng + điền logic. Không tạo bảng block ở F06 (out-of-scope,
KISS/YAGNI).
**Consequence:** Khi F10 xong, chỉ cần điền thân helper — không
phải sửa cấu trúc query feed. F06 test verify hook được áp dụng
(no-op rỗng → không loại ai); test loại trừ block thực thuộc F10.

---

## DL-F06-04 — Filter 24h bằng `expires_at > now()`, không xoá post

**Date:** 2026-06-22
**Context:** FR-3 yêu cầu chỉ hiển thị ảnh trong 24h. F05 đã đặt
`posts.expires_at = created_at + 24h` (DL-F05-03) và **giữ** record.
**Decision:** Feed lọc `expires_at > now()` thay vì so sánh
`created_at + 24h` hay xoá row. Tận dụng cột + index
`idx_posts_expires_at` sẵn có (F05 Design §2.1).
**Consequence:** Nhất quán với F05/F08; khi đổi thời lượng (premium)
chỉ cần sửa `POST_EXPIRY_HOURS` ở F05. F06 không tự tính lại mốc.

---

## DL-F06-05 — `GET /feed` trả 404 khi `firebase_uid` chưa có user row

**Date:** 2026-06-22
**Context:** Resolve `firebase_uid` → viewer UUID; token hợp lệ
nhưng chưa gọi `/auth/session` thì không có user row (giống
DL-F05-09).
**Decision:** Router trả **404 `USER_NOT_FOUND`** (nhất quán pattern
`routers/posts.py` / `routers/friends.py`), không tạo user ngầm
(YAGNI).
**Consequence:** Client luôn gọi `/auth/session` trước (F01) nên
nhánh này hiếm; chốt chặn tránh 500 khi gọi API trực tiếp.

---

## DL-F06-06 — F06 không thêm migration (tái dùng bảng F05/F02)

**Date:** 2026-06-22
**Context:** Feed đọc `posts`, `post_recipients`, `users`,
`pet_profiles` — tất cả đã tồn tại.
**Decision:** F06 **không** tạo bảng/cột/migration mới; chỉ
`SELECT`. Không có test migration cho F06.
**Consequence:** Giảm bề mặt thay đổi (surgical). Mọi thay đổi
schema liên quan ảnh thuộc F05/F02/F07.

---

## DL-F06-07 — Thời gian tương đối tính ở client; CDN/cache là native

**Date:** 2026-06-22
**Context:** FR-4 yêu cầu "thời gian gửi tương đối" (e.g. "3 phút
trước"); FR-8 yêu cầu tải ảnh CDN + placeholder + cache.
**Decision:** Backend trả `created_at` dạng **ISO 8601 tuyệt đối**;
client format thành chuỗi tương đối qua util thuần
`formatRelativeTime(iso, now)` (tiếng Việt, dễ test, không phụ
thuộc múi giờ server). Tải/cache ảnh CDN là tích hợp native, không
unit-test (tiền lệ DL-F05-08).
**Consequence:** Logic hiển thị thời gian test được độc lập; tránh
trả chuỗi i18n từ server. Cache ảnh để task triển khai native sau.

---

## DL-F06-08 — Cursor pagination mã hoá `(created_at, post_id)`

**Date:** 2026-06-22
**Context:** Technical Constraint yêu cầu cursor-based pagination dù
feed giới hạn 24h (Non-goal: infinite scroll). Cần thứ tự ổn định
khi nhiều post cùng `created_at`.
**Decision:** Sắp `created_at DESC, post_id DESC`. Cursor là chuỗi
opaque (base64 JSON `{created_at, post_id}`) của item cuối; trang
sau lọc `(created_at, post_id)` "nhỏ hơn" theo thứ tự DESC. Lấy
`limit+1` để biết còn trang (`next_cursor`) hay không. Cursor hỏng →
`InvalidCursorError` → 400 `INVALID_CURSOR`. `limit` mặc định
`FEED_PAGE_SIZE=20`, trần `FEED_MAX_PAGE_SIZE=50` (clamp).
**Consequence:** Thứ tự deterministic kể cả khi trùng timestamp.
Client có thể chỉ dùng trang đầu trong MVP; cursor sẵn sàng cho mở
rộng. Không lộ created_at/id thô qua tham số (opaque).

---

## DL-F06-09 — `seen` là giá trị suy ra, không phải cột

**Date:** 2026-06-22
**Context:** Feed cần cờ seen cho mỗi item (FR-6). `post_recipients`
có `seen_at` (nullable) cho đúng edge (post, viewer).
**Decision:** `seen = (post_recipients.seen_at IS NOT NULL)` cho
edge của viewer. Vì feed chỉ trả post mà viewer là recipient nên có
đúng một edge `(post, viewer)`; không cần thêm cột boolean.
**Consequence:** Không thay đổi schema (DL-F06-06). F07 ghi
`seen_at` → lần `getFeed` sau phản ánh đúng `seen`.

---

## DL-F06-11 — Flutter `Post` domain model dùng `cdn_url` + `seen`; bỏ `seenByCount`

**Date:** 2026-06-27
**Context:** Khi tích hợp client với backend thật (Firebase live), phát hiện
`Post.fromJson` đọc sai key JSON. Backend `FeedItemResponse` trả `cdn_url`
(không phải `image_url`), `seen: bool` (không phải `seen_by_me`), và không
có field `seen_by_count`. Flutter model trước đó dùng các key cũ từ giai
đoạn dev/mock.
**Decision:**
- `Post.fromJson`: đọc `json['cdn_url']`, `json['seen']`, bỏ `seenByCount`.
- `FeedItem` widget: đổi badge `seenByCount` thành icon seen/unseen
  (`Icons.visibility` / `Icons.visibility_outlined`) — backend feed endpoint
  không trả count (count chỉ có ở `GET /posts/{id}/seen-by` dành cho Sender).
- `Post.copyWith`: bỏ param `seenByCount`.
**Consequence:** Feed render đúng ảnh CDN. Count không hiển thị trên
feed view (đúng business logic — Recipient không cần biết bao nhiêu người
đã xem, chỉ Sender mới xem danh sách qua F07 `SeenByList`).

---

## DL-F06-10 — Chi tiết hiện thực client: fallback "ngày trước" + placeholder URI

**Date:** 2026-06-22
**Context:** Design §4.2 liệt kê 3 nhãn thời gian ("vừa xong", "N phút
trước", "N giờ trước") và yêu cầu placeholder ảnh CDN (FR-8) nhưng không
chốt giá trị cụ thể. Feed giới hạn 24h nên thực tế hiếm khi vượt giờ.
**Decision:** `formatRelativeTime` thêm nhánh fallback `"N ngày trước"`
(defensive, không đổi 3 case đã test) và `FeedItem` dùng một
`defaultSource` placeholder tĩnh
(`https://cdn.pawsnap.app/static/feed-placeholder.png`). `markSeen` là
no-op async (đúng DL-F06-02) — không phát network ở F06.
**Consequence:** Không ảnh hưởng AC/test hiện có; tải/cache ảnh CDN thật
+ full-screen viewer vẫn là task native sau (DL-F06-07). Khi F07 vào,
chỉ cần điền thân `markSeen`.
