# F07 — Seen By — Decision Log

---

## DL-F07-01 — Seen lưu trên `post_recipients.seen_at`, không tạo bảng riêng

**Date:** 2026-06-22
**Context:** Requirements F07 cần ghi "seen event" theo cặp
(post_id, viewer_id) và đảm bảo không trùng (FR-2, FR-6). F05 đã
tạo cột `post_recipients.seen_at` (nullable) làm "chỗ ở tự nhiên"
của seen (DL-F05-04) và ràng buộc `UNIQUE (post_id, recipient_id)`
(`post_recipients_unique_pair`, F05 Design §2.2).
**Decision:** Không tạo bảng "seen events" riêng. Đánh dấu seen =
`UPDATE post_recipients.seen_at` trên dòng (post, recipient) đã có.
Vì mỗi cặp đã là một dòng duy nhất, không thể phát sinh duplicate.
**Consequence:** Không thêm migration (DL-F07-07). "Không duplicate"
(AC-F07-3) được bảo đảm bởi cấu trúc dữ liệu sẵn có thay vì logic
chống trùng bổ sung.

---

## DL-F07-02 — `POST /posts/{id}/seen` idempotent, first-seen wins

**Date:** 2026-06-22
**Context:** AC-F07-3 yêu cầu mở lại ảnh không tạo seen event mới và
không tăng số người xem. FR-1 yêu cầu ghi seen **ngay** khi render.
**Decision:** `mark_seen` chỉ đặt `seen_at = now()` khi `seen_at`
đang NULL; nếu đã có giá trị thì giữ nguyên (mốc lần xem đầu tiên).
Endpoint trả 200 với `seen_at` (cũ hoặc mới) trong cả hai trường
hợp ⇒ idempotent.
**Consequence:** Client (F06/F08) có thể gọi `markSeen` mỗi lần mở
full-screen mà không lo nhân bản; `seen_count` ổn định (AC-F07-3).
Giữ được "thời điểm xem đầu tiên" cho hiển thị danh sách.

---

## DL-F07-03 — Chỉ recipient của post mới ghi được seen

**Date:** 2026-06-22
**Context:** Seen chỉ có nghĩa cho người thực sự nhận ảnh; cần chặn
người ngoài ghi seen cho post không liên quan.
**Decision:** `mark_seen` yêu cầu tồn tại dòng
`post_recipients(post_id, viewer_id)`; nếu không → `NotRecipientError`
→ router trả **403 `NOT_RECIPIENT`**. Post không tồn tại →
`PostNotFoundError` → **404 `POST_NOT_FOUND`**.
**Consequence:** Không thể "seen" hộ hoặc seen post của người khác.
Nhất quán với mô hình recipient của F05 (chỉ recipient mới thấy ảnh
ở feed — F06).

---

## DL-F07-04 — `GET /posts/{id}/seen-by` chỉ Sender xem được

**Date:** 2026-06-22
**Context:** FR-3 nêu rõ Sender xem danh sách người đã xem "ảnh của
mình". Danh sách người xem là thông tin riêng tư của chủ post.
**Decision:** `get_seen_by` yêu cầu `post.user_id == viewer_id`;
nếu không → `NotSenderError` → router trả **403 `FORBIDDEN`**. Post
thiếu → **404 `POST_NOT_FOUND`**.
**Consequence:** Recipient không thể xem ai khác đã xem cùng một
ảnh. Phù hợp với mô hình broadcast một-chiều (Sender → recipients)
của F05.

---

## DL-F07-05 — F07 điền hook `FeedService.markSeen` qua `SeenService`

**Date:** 2026-06-22
**Context:** F06 để lại `FeedService.markSeen(postId)` dạng no-op
làm điểm tích hợp cho F07 (DL-F06-02). F07 cần phát network call
seen mà không phá vỡ contract/optimistic UI của F06.
**Decision:** Tạo `SeenService` (client) với `markSeen`/`getSeenBy`.
`FeedService.markSeen` được sửa để **delegate** sang
`SeenService.markSeen(postId)`, giữ nguyên signature ⇒ `FeedScreen`
(F06) không cần đổi.
**Consequence:** Logic seen client tập trung ở `SeenService`; F06
test optimistic UI vẫn xanh; F07 chỉ verify việc delegate +
`SeenService` gọi đúng endpoint.

---

## DL-F07-06 — `SeenByList` + `SeenService.getSeenBy` thuộc F07; gắn vào History thuộc F08

**Date:** 2026-06-22
**Context:** FR-3/FR-4 mô tả hiển thị danh sách + số người xem "trong
lịch sử gửi". Màn hình History thuộc F08 (sau F07).
**Decision:** F07 cung cấp **component** `SeenByList` (render độc
lập từ `SeenByResult`) và `SeenService.getSeenBy`. Việc **gắn**
component vào màn hình History và áp filter 24h thuộc F08 — cùng kiểu
boundary như hook `markSeen` của F06 (DL-F06-02).
**Consequence:** F07 test component render độc lập; F08 chịu trách
nhiệm tích hợp UI. Tránh phụ thuộc ngược F07 → F08.

---

## DL-F07-07 — F07 không thêm migration (tái dùng cột F05)

**Date:** 2026-06-22
**Context:** Seen ghi/đọc trên `post_recipients.seen_at`; bảng +
ràng buộc unique pair đã có từ F05.
**Decision:** F07 **không** tạo bảng/cột/migration mới; chỉ
UPDATE/SELECT cột `seen_at` đã tồn tại. Không có test migration cho
F07 (giống DL-F06-06).
**Consequence:** Giảm bề mặt thay đổi (surgical). Mọi thay đổi schema
liên quan ảnh tập trung ở F05/F02.

---

## DL-F07-08 — `seen-by` trả `seen_count` + `viewers[]` tổng hợp toàn bộ recipients

**Date:** 2026-06-22
**Context:** FR-4 yêu cầu hiển thị số lượng người đã xem ("2 người
đã xem") tổng hợp trên tất cả người nhận.
**Decision:** `get_seen_by` SELECT các recipient của post có
`seen_at IS NOT NULL`, JOIN `users` lấy `display_name`/`avatar_url`,
sắp `seen_at DESC`; trả `viewers[]` và `seen_count = len(viewers)`.
**Consequence:** Client chỉ cần đọc một endpoint để vừa hiển thị số
lượng vừa liệt kê tên. Không cần đếm ở nơi khác (DRY).

---

## DL-F07-09 — 404 `USER_NOT_FOUND` khi `firebase_uid` chưa có user row

**Date:** 2026-06-22
**Context:** Resolve `firebase_uid` → viewer UUID; token hợp lệ
nhưng chưa gọi `/auth/session` thì không có user row (giống
DL-F06-05).
**Decision:** Router trả **404 `USER_NOT_FOUND`** (nhất quán pattern
`routers/posts.py` / `routers/feed.py`), không tạo user ngầm (YAGNI).
**Consequence:** Client luôn gọi `/auth/session` trước (F01) nên
nhánh này hiếm; chốt chặn tránh 500 khi gọi API trực tiếp.

---

## DL-F07-11 — Flutter `SeenService.getSeenBy()` parse `viewers[]` từ `SeenByResponse`

**Date:** 2026-06-27
**Context:** Khi tích hợp client với backend thật, phát hiện `SeenService.getSeenBy()`
parse response như `List<String>` (cast trực tiếp), nhưng backend `SeenByResponse`
trả `{post_id, seen_count: int, viewers: [{user_id, display_name, avatar_url, seen_at}]}`.
**Decision:** `getSeenBy()` đổi sang `get<Map<String, dynamic>>`, đọc
`response.data['viewers']`, map mỗi viewer lấy `display_name` (skip nếu null/empty),
giữ return type `List<String>` để `SeenByList` widget không cần thay đổi.
Widget hiển thị tên bằng `Chip(label: Text(name))` như cũ.
**Consequence:** `SeenByList` hiển thị đúng tên người đã xem từ backend thật.
Nếu sau này widget cần avatar hoặc `seen_at`, cần thay đổi return type
`getSeenBy()` thành `List<SeenViewer>` và cập nhật widget.

---

## DL-F07-10 — Thay test `markSeen` cũ trong `FeedService.test.ts`

**Date:** 2026-06-22
**Context:** F06 để lại test `markSeen` trong `FeedService.test.ts`
khẳng định "resolves without issuing a network call" (no-op hook).
F07 sửa `FeedService.markSeen` để **delegate** sang
`SeenService.markSeen` (DL-F07-05) ⇒ test đó không còn đúng (giờ có
network call qua `SeenService`).
**Decision:** Gỡ block test `markSeen` đã lỗi thời khỏi
`FeedService.test.ts` (đây là dọn dẹp trực tiếp do thay đổi của F07
gây ra); việc verify delegation được phủ bởi file test mới chuyên
trách `__tests__/seen/FeedServiceMarkSeen.test.ts` (Design §6.4).
Các test `getFeed` còn lại của `FeedService.test.ts` giữ nguyên và
vẫn xanh.
**Consequence:** Không trùng lặp test (DRY); contract delegation chỉ
có một nguồn sự thật. `FeedService.test.ts` và `FeedScreen.test.tsx`
(mock toàn bộ `FeedService`) vẫn xanh.
