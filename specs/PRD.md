# Product Requirements Document (PRD)

## PawSnap — MVP

**Version:** 1.0.0-draft
**Date:** 2026-06-18
**Author:** Product Team
**Status:** Draft

---

## Tổng quan sản phẩm

Dokat là mạng xã hội dành riêng cho chủ thú cưng (chó/mèo), cho phép gửi
ảnh chụp thú cưng đến bạn bè theo thời gian thực — tương tự Locket, nhưng tập
trung hoàn toàn vào pet content. Nội dung chỉ gồm ảnh chó/mèo, không có ảnh
người.

**Platform:** React Native (iOS + Android)
**Backend:** FastAPI (Python) + PostgreSQL + Firebase Auth + S3 + CloudFront
**Thị trường MVP:** Việt Nam

---

## Danh sách Feature MVP

| ID   | Feature                              | Độ ưu tiên |
|------|--------------------------------------|------------|
| F01  | Authentication & Guest Mode          | P0         |
| F02  | Owner Profile & Pet Profile          | P0         |
| F03  | Social Graph — Kết bạn qua QR        | P0         |
| F04  | Capture Ảnh + AI Validation          | P0         |
| F05  | Gửi Ảnh (Multi-Recipient)            | P0         |
| F06  | Feed & App View                      | P0         |
| F07  | Seen By                              | P1         |
| F08  | History / Timeline (1 ngày)          | P1         |
| F09  | Notification System                  | P1         |
| F10  | Settings (Liên kết tài khoản, Logout,| P1         |
|      | Block/Report)                        |            |
| F11  | Location & Time Metadata (Store Only)| P2         |

---

## F01 — Authentication & Guest Mode

### Goal

Cho phép người dùng bắt đầu sử dụng app ngay lập tức dưới dạng Guest (ẩn
danh), sau đó nâng cấp lên tài khoản đầy đủ bằng cách liên kết Apple / Google
/ Facebook khi cần thiết.

### Users / Actors

- **Guest User:** Người dùng chưa liên kết tài khoản mạng xã hội, được định
  danh bằng anonymous ID.
- **Linked User:** Người dùng đã liên kết ít nhất một tài khoản mạng xã hội.
- **System:** Backend FastAPI + Firebase Auth.

### Functional Requirements

1. Hệ thống SHALL tự động tạo một anonymous ID duy nhất cho người dùng ngay
   khi mở app lần đầu, không yêu cầu bất kỳ thông tin đầu vào nào.
2. Hệ thống SHALL lưu anonymous ID vào local storage để khôi phục session khi
   mở lại app.
3. Hệ thống SHALL cho phép Guest User dùng toàn bộ tính năng xem feed và xem
   ảnh nhận được.
4. Hệ thống SHALL hiển thị màn hình prompt liên kết tài khoản (Apple / Google
   / Facebook) khi Guest User thực hiện một trong các hành động: gửi ảnh, thêm
   bạn bè.
5. Hệ thống SHALL bắt buộc liên kết tài khoản nếu tài khoản Guest đã tồn tại
   quá 7 ngày mà chưa liên kết.
6. Hệ thống SHALL sử dụng Firebase Auth để xử lý OAuth flow với
   Apple / Google / Facebook trực tiếp từ client.
7. Hệ thống SHALL liên kết anonymous ID với tài khoản OAuth sau khi người dùng
   xác thực thành công, không làm mất dữ liệu đã có.
8. Hệ thống SHALL issue một JWT (hoặc Firebase ID Token) để xác thực các
   request đến FastAPI backend.
9. Hệ thống SHALL cho phép người dùng liên kết thêm hoặc thay đổi tài khoản
   mạng xã hội trong phần Settings.

### Non-goals

- Không hỗ trợ đăng nhập bằng email/password hay số điện thoại trong MVP.
- Không hỗ trợ xóa tài khoản trong MVP.
- Không có Group Auth (auth theo nhóm/tổ chức).

### Technical Constraints

- Firebase Anonymous Auth phải được bật trong Firebase project.
- OAuth redirect scheme phải được đăng ký đúng trong Apple Developer Console và
  Google Cloud Console.
- JWT/Firebase ID Token phải được verify ở mỗi request FastAPI.

### Acceptance Criteria

**AC-F01-1:** Guest Mode khởi tạo
```
Given người dùng mở app lần đầu tiên
When app hoàn tất khởi động
Then hệ thống tạo anonymous ID và người dùng thấy màn hình Onboarding
  mà không cần nhập bất kỳ thông tin nào
```

**AC-F01-2:** Prompt liên kết khi gửi ảnh
```
Given người dùng là Guest User (chưa liên kết)
When người dùng nhấn nút "Gửi ảnh"
Then hệ thống hiển thị bottom sheet yêu cầu liên kết tài khoản
  và không thực hiện hành động gửi cho đến khi liên kết thành công
```

**AC-F01-3:** Bắt buộc liên kết sau 7 ngày
```
Given người dùng là Guest User đã tạo tài khoản từ đúng 7 ngày trước
When người dùng mở app
Then hệ thống hiển thị màn hình full-screen bắt buộc liên kết tài khoản
  và không cho phép dismiss màn hình này
```

**AC-F01-4:** Liên kết tài khoản không mất dữ liệu
```
Given người dùng là Guest User có 5 bạn bè và 3 ảnh đã gửi
When người dùng liên kết tài khoản Google thành công
Then toàn bộ bạn bè và ảnh vẫn còn nguyên sau khi liên kết
```

**AC-F01-5:** Khôi phục session
```
Given người dùng đã đăng nhập và tắt app
When người dùng mở lại app
Then hệ thống tự động khôi phục session mà không yêu cầu đăng nhập lại
```

---

## F02 — Owner Profile & Pet Profile

### Goal

Cho phép người dùng thiết lập thông tin cá nhân và tạo hồ sơ thú cưng (có hỗ
trợ AI nhận diện loài và giới tính từ ảnh), tạo nền tảng cho trải nghiệm cá
nhân hóa.

### Users / Actors

- **User:** Người dùng đã qua bước tạo anonymous ID.
- **AI Service:** Model nhận diện hình ảnh (client-side) để auto-fill thông
  tin thú cưng.

### Functional Requirements

1. Hệ thống SHALL yêu cầu người dùng điền Owner Profile (Tên, Giới tính,
   Ngày sinh) trong flow Onboarding trước khi sử dụng các tính năng khác.
2. Hệ thống SHALL cho phép người dùng tạo ít nhất một Pet Profile với các
   trường: Tên, Giới tính, Loại (chó/mèo), Ngày sinh.
3. Hệ thống SHALL cho phép người dùng upload ảnh thú cưng khi tạo Pet Profile.
4. Hệ thống SHALL chạy AI model nhận diện trên client để auto-fill các trường
   Loại (chó/mèo) và Giới tính từ ảnh được upload.
5. Hệ thống SHALL cho phép người dùng chỉnh sửa lại các thông tin do AI
   auto-fill trước khi lưu.
6. Hệ thống SHALL cho phép người dùng có nhiều hơn một Pet Profile.
7. Hệ thống SHALL cho phép người dùng chỉnh sửa Owner Profile và Pet Profile
   bất kỳ lúc nào từ màn hình Profile.

### Non-goals

- Không có tính năng AI generate avatar/artwork cho thú cưng trong MVP.
- Không hỗ trợ loại thú cưng ngoài chó/mèo.
- Không có tính năng chia sẻ công khai Pet Profile ra ngoài danh sách bạn bè.

### Technical Constraints

- AI model nhận diện chạy hoàn toàn on-device (không gọi API server) để tránh
  latency và chi phí.
- Ảnh avatar Pet lưu lên S3, phục vụ qua CloudFront CDN.
- Dữ liệu profile lưu trong PostgreSQL.

### Acceptance Criteria

**AC-F02-1:** Owner Profile bắt buộc
```
Given người dùng vừa tạo anonymous ID
When người dùng chưa hoàn thành Owner Profile
Then hệ thống chặn truy cập vào các màn hình chính
  và redirect về màn hình điền Owner Profile
```

**AC-F02-2:** AI auto-fill Pet Profile
```
Given người dùng upload ảnh một con chó lên Pet Profile
When AI model hoàn tất nhận diện (≤ 3 giây)
Then trường "Loại" được tự động điền là "Chó"
  và trường "Giới tính" được điền nếu model có độ tin cậy ≥ 70%
```

**AC-F02-3:** Chỉnh sửa thông tin AI auto-fill
```
Given AI đã auto-fill Loại = "Mèo" nhưng thực tế là "Chó"
When người dùng chỉnh sửa lại trường Loại
Then hệ thống chấp nhận giá trị người dùng nhập
  và lưu đúng "Chó" vào database
```

**AC-F02-4:** Nhiều Pet Profile
```
Given người dùng đã có 1 Pet Profile
When người dùng nhấn "Thêm thú cưng" và hoàn thành form
Then hệ thống lưu Pet Profile thứ 2
  và cả hai hiển thị trong màn hình Profile của người dùng
```

---

## F03 — Social Graph — Kết Bạn qua QR

### Goal

Cho phép người dùng kết bạn với nhau thông qua QR code dạng OTP — scan là kết
bạn ngay, không cần xác nhận. Giới hạn tối đa 20 bạn bè (hard limit).

### Users / Actors

- **Initiator:** Người dùng hiển thị QR code của mình.
- **Scanner:** Người dùng dùng camera scan QR code của người khác.
- **System:** Backend xử lý tạo cạnh (edge) trong social graph.

### Functional Requirements

1. Hệ thống SHALL tạo một QR code OTP duy nhất cho mỗi người dùng khi họ mở
   màn hình "Thêm bạn".
2. Hệ thống SHALL gắn thời hạn hiệu lực cho QR OTP tối đa là 5 phút; sau đó
   QR tự động hết hạn.
3. Hệ thống SHALL tạo liên kết bạn bè (friendship edge) hai chiều ngay lập tức
   khi Scanner quét QR hợp lệ — không yêu cầu Initiator xác nhận.
4. Hệ thống SHALL từ chối tạo friendship nếu một trong hai người dùng đã đạt
   giới hạn 20 bạn bè và hiển thị thông báo lỗi rõ ràng.
5. Hệ thống SHALL từ chối nếu hai người dùng đã là bạn bè, tránh tạo duplicate
   edge.
6. Hệ thống SHALL từ chối nếu người dùng cố kết bạn với chính mình.
7. Hệ thống SHALL lưu friendship graph trong PostgreSQL với timestamp tạo.
8. Hệ thống SHALL cho phép người dùng xem danh sách bạn bè hiện tại.
9. Hệ thống SHALL cho phép người dùng xóa bạn bè; khi xóa thì edge bị remove
   hai chiều.

### Non-goals

- Không có tính năng sync danh bạ điện thoại trong MVP.
- Không có hệ thống "chờ chấp nhận" (friend request pending).
- Không có tính năng tìm kiếm bạn bè theo tên/username.
- Không có group trong MVP.

### Technical Constraints

- QR OTP được tạo server-side, lưu tạm trong Redis hoặc PostgreSQL với TTL
  5 phút.
- QR code chứa một deep link dẫn về app.
- Mỗi QR OTP chỉ được sử dụng một lần (single-use).

### Acceptance Criteria

**AC-F03-1:** Tạo QR thành công
```
Given người dùng mở màn hình "Thêm bạn"
When màn hình load xong
Then một QR code được hiển thị trong vòng 2 giây
  và QR code có thể scan được bằng camera
```

**AC-F03-2:** Kết bạn ngay khi scan
```
Given User A hiển thị QR code (chưa hết hạn)
When User B scan QR code của User A
Then User A và User B trở thành bạn bè ngay lập tức
  và cả hai thấy nhau trong danh sách bạn bè
  mà không cần bất kỳ bước xác nhận nào
```

**AC-F03-3:** QR hết hạn
```
Given User A tạo QR code và 5 phút đã trôi qua
When User B scan QR code đó
Then hệ thống trả về lỗi "QR đã hết hạn"
  và không tạo friendship
```

**AC-F03-4:** Hard limit 20 bạn bè
```
Given User A đang có đúng 20 bạn bè
When User B scan QR của User A
Then hệ thống hiển thị thông báo "User A đã đạt giới hạn bạn bè"
  và không tạo friendship
```

**AC-F03-5:** QR single-use
```
Given User B đã dùng QR code của User A để kết bạn thành công
When User C dùng cùng QR code đó để scan
Then hệ thống trả về lỗi "QR đã được sử dụng"
  và không tạo friendship mới
```

---

## F04 — Capture Ảnh + AI Validation

### Goal

Cho phép người dùng chụp ảnh thú cưng trực tiếp trong app ở độ phân giải
720p. AI model chạy on-device sẽ xác nhận ảnh chỉ chứa chó/mèo — nếu phát
hiện người thì block upload.

### Users / Actors

- **User:** Người dùng chụp ảnh.
- **AI Validation Engine:** Model on-device phân loại nội dung ảnh.

### Functional Requirements

1. Hệ thống SHALL mở camera in-app khi người dùng nhấn nút chụp.
2. Hệ thống SHALL chụp ảnh ở độ phân giải 720p (1280×720px).
3. Hệ thống SHALL chạy AI model on-device để phân loại nội dung ảnh ngay sau
   khi chụp, trước khi hiển thị preview.
4. Hệ thống SHALL block hoàn toàn không cho upload nếu AI phát hiện có người
   trong ảnh (human detected).
5. Hệ thống SHALL hiển thị thông báo lỗi rõ ràng ("Ảnh không hợp lệ — chỉ
   được chụp thú cưng") khi bị block.
6. Hệ thống SHALL cho phép người dùng chụp lại nếu ảnh bị block.
7. Hệ thống SHALL cho phép upload nếu AI xác nhận ảnh hợp lệ (chứa chó/mèo
   hoặc không có người).
8. Hệ thống SHALL nén và optimize ảnh trước khi upload lên S3 để giảm dung
   lượng mà không làm giảm chất lượng đáng kể.
9. Hệ thống SHALL hoàn tất AI validation trong vòng 3 giây trên thiết bị
   tầm trung.

### Non-goals

- Không có Image Editor (filter, sticker, crop, flip, AI generate) trong MVP.
- Không hỗ trợ chụp video trong MVP.
- Không validate phía server; việc kiểm tra chỉ thực hiện on-device.
- Không hỗ trợ upload ảnh từ thư viện ảnh hệ thống (chỉ chụp trực tiếp).

### Technical Constraints

- AI model phải chạy hoàn toàn on-device (TFLite hoặc CoreML).
- Model phải nhẹ (≤ 20MB) để không làm tăng đáng kể bundle size.
- Ảnh upload lên S3 theo path có cấu trúc:
  `posts/{user_id}/{timestamp}_{uuid}.jpg`.
- Metadata ảnh (user_id, timestamp, s3_key) lưu vào PostgreSQL.

### Acceptance Criteria

**AC-F04-1:** Chụp ảnh hợp lệ
```
Given người dùng mở camera và chụp ảnh chỉ có một con mèo
When AI validation hoàn tất
Then hệ thống cho phép tiếp tục flow gửi ảnh
  và ảnh được lưu ở độ phân giải 720p
```

**AC-F04-2:** Block ảnh có người
```
Given người dùng chụp ảnh có cả người và chó
When AI validation hoàn tất
Then hệ thống hiển thị thông báo lỗi "Ảnh không hợp lệ"
  và không cho phép gửi ảnh
  và không upload bất kỳ dữ liệu nào lên server
```

**AC-F04-3:** Thời gian validation
```
Given người dùng chụp ảnh
When AI bắt đầu validation
Then kết quả validation xuất hiện trong vòng 3 giây
  trên thiết bị tầm trung (4GB RAM)
```

**AC-F04-4:** Chụp lại sau khi bị block
```
Given ảnh vừa bị block vì có người
When người dùng nhấn "Chụp lại"
Then camera mở lại và người dùng có thể chụp ảnh mới
```

---

## F05 — Gửi Ảnh (Multi-Recipient / Broadcast)

### Goal

Cho phép người dùng gửi ảnh thú cưng vừa chụp đến bạn bè theo mô hình
broadcast: mặc định gửi tới tất cả bạn bè hiện có (có thể là 0 nếu chưa có
bạn nào), hoặc chọn một subset người nhận. Mỗi lần chụp là one-shot: sau khi
gửi xong, ảnh bị discard và muốn gửi tiếp phải chụp lại.

### Users / Actors

- **Sender:** Người dùng gửi ảnh.
- **Recipients:** Không, một, hoặc nhiều người bạn nhận ảnh (0..N).
- **System:** Backend xử lý lưu post và trigger notification.

### Functional Requirements

1. Hệ thống SHALL hiển thị danh sách bạn bè để Sender chọn người nhận sau khi
   ảnh pass AI validation.
2. Hệ thống SHALL mặc định chọn sẵn toàn bộ bạn bè hiện có của Sender làm danh
   sách người nhận.
3. Hệ thống SHALL cho phép Sender bỏ chọn hoặc chọn lại để gửi tới một subset
   bất kỳ, bao gồm trường hợp 0 người nhận.
4. Hệ thống SHALL cho phép nhấn "Gửi" ngay cả khi số người nhận là 0.
5. Hệ thống SHALL upload ảnh lên S3 (một lần) và luôn tạo post record trong
   PostgreSQL khi Sender gửi, kể cả khi danh sách người nhận rỗng.
6. Hệ thống SHALL gắn post với toàn bộ danh sách người nhận đã chọn (0..N) qua
   quan hệ many-to-many.
7. Hệ thống SHALL lưu post vào History "Đã gửi" của Sender trong mọi trường
   hợp, kể cả khi không có người nhận nào (xem F08).
8. Hệ thống SHALL hiển thị ảnh trên feed của tất cả người nhận được chọn, và
   chỉ những người đó (xem F06).
9. Hệ thống SHALL gửi push notification đến từng Recipient ngay sau khi ảnh
   được lưu thành công (xem F09); khi 0 người nhận thì không gửi notification.
10. Hệ thống SHALL discard ảnh sau khi gửi thành công; nếu muốn gửi thêm,
    Sender phải chụp lại (one-shot).
11. Hệ thống SHALL lưu timestamp gửi vào metadata của post.
12. Hệ thống SHALL hiển thị trạng thái "Đã gửi" cho Sender sau khi upload
    thành công.
13. Hệ thống SHALL xử lý trường hợp mất kết nối: retry upload tối đa 3 lần
    trước khi báo lỗi cho người dùng.

### Non-goals

- Không hỗ trợ gửi nhóm (group send) trong MVP — chỉ broadcast/multi-select
  cá nhân.
- Không có tính năng unsend/thu hồi ảnh trong MVP.
- Không cho phép gửi lại cùng một ảnh sau khi đã gửi (one-shot, ảnh bị
  discard).

### Technical Constraints

- Upload ảnh dùng presigned S3 URL (client upload trực tiếp lên S3, không qua
  FastAPI backend) để giảm tải server.
- Ảnh chỉ upload lên S3 một lần cho một lần gửi, dù gửi cho nhiều người.
- Quan hệ post — recipients là many-to-many: một bảng liên kết
  `post_recipients(post_id, recipient_id, ...)`; bảng này có thể rỗng cho một
  post (trường hợp 0 người nhận).
- Sau khi upload thành công, client gọi FastAPI để tạo post record và (nếu có)
  các bản ghi post_recipients trong PostgreSQL.
- Ảnh của free user được đánh dấu `expires_at = now() + 24h` trong database
  (record vẫn giữ, chỉ ẩn khỏi feed sau 24h).

### Acceptance Criteria

**AC-F05-1:** Mặc định chọn sẵn tất cả bạn bè
```
Given Sender có 4 bạn bè và vừa chụp ảnh hợp lệ
When màn hình chọn người nhận hiển thị
Then cả 4 bạn bè được chọn sẵn theo mặc định
```

**AC-F05-2:** Gửi broadcast tới tất cả bạn bè thành công
```
Given Sender giữ nguyên mặc định chọn cả 3 bạn bè
When Sender nhấn "Gửi"
Then ảnh xuất hiện trên feed của cả 3 người nhận trong vòng 5 giây
  và cả 3 người nhận đều nhận được push notification
  và Sender thấy trạng thái "Đã gửi"
```

**AC-F05-3:** Gửi cho một subset người nhận
```
Given Sender có 4 bạn bè và bỏ chọn còn lại 2 người (User B, User C)
When Sender nhấn "Gửi"
Then ảnh chỉ xuất hiện trên feed của User B và User C
  và hai người còn lại không nhận được ảnh hay notification
```

**AC-F05-4:** Gửi khi 0 người nhận — lưu vào History của mình
```
Given Sender chưa có bạn bè nào (hoặc bỏ chọn hết người nhận)
When Sender nhấn "Gửi"
Then ảnh vẫn được upload và lưu thành công
  và ảnh xuất hiện trong History "Đã gửi" của Sender
  và không có push notification nào được gửi đi
```

**AC-F05-5:** One-shot — ảnh bị discard sau khi gửi
```
Given Sender đã gửi ảnh thành công
When Sender muốn gửi tiếp
Then ảnh đã bị discard và không còn để gửi lại
  và Sender phải chụp ảnh mới để gửi tiếp
```

**AC-F05-6:** Mất kết nối khi gửi
```
Given Sender đang upload ảnh và mất kết nối internet
When kết nối được khôi phục trong vòng 30 giây
Then hệ thống tự động retry upload
  và ảnh được gửi thành công đến tất cả người nhận đã chọn
  mà không cần Sender thao tác lại
```

**AC-F05-7:** Upload thất bại sau 3 lần retry
```
Given Sender đang upload và mất kết nối kéo dài
When hệ thống đã retry 3 lần thất bại
Then hệ thống hiển thị thông báo lỗi rõ ràng
  và ảnh chưa được lưu cũng như chưa gửi cho bất kỳ người nhận nào
```

---

## F06 — Feed & App View

### Goal

Hiển thị ảnh thú cưng mà người dùng nhận được từ bạn bè theo thứ tự thời gian
gần nhất, trong App View (không có Home Screen Widget cho MVP).

### Users / Actors

- **User (Recipient):** Người xem feed của mình.
- **System:** Backend cung cấp danh sách post theo user.

### Functional Requirements

1. Hệ thống SHALL hiển thị màn hình Feed là màn hình chính sau khi đăng nhập.
2. Hệ thống SHALL hiển thị ảnh nhận được từ tất cả bạn bè, sắp xếp theo thời
   gian mới nhất lên đầu.
3. Hệ thống SHALL chỉ hiển thị ảnh trong vòng 24 giờ kể từ thời điểm gửi
   (đối với free user).
4. Hệ thống SHALL hiển thị thông tin đi kèm mỗi ảnh: tên người gửi, tên thú
   cưng (nếu có), thời gian gửi tương đối (e.g. "3 phút trước").
5. Hệ thống SHALL đánh dấu post là "đã xem" khi người dùng mở ảnh xem đầy đủ.
6. Hệ thống SHALL phân biệt trạng thái "chưa xem" và "đã xem" bằng visual
   indicator trên feed item.
7. Hệ thống SHALL hỗ trợ pull-to-refresh để tải ảnh mới nhất.
8. Hệ thống SHALL load ảnh từ CloudFront CDN với placeholder khi đang tải.
9. Hệ thống SHALL hiển thị empty state khi feed trống (chưa có bạn hoặc chưa
   nhận ảnh nào trong 24h).

### Non-goals

- Không có Home Screen Widget trong MVP.
- Không có infinite scroll (feed chỉ hiển thị trong phạm vi 24h).
- Không có thuật toán ranking/recommendation — chỉ chronological order.
- Không có ads/sponsored content trong MVP.

### Technical Constraints

- Feed API endpoint trả về danh sách post có phân trang (cursor-based
  pagination).
- Ảnh được serve qua CloudFront CDN để tối ưu tốc độ tải.
- Client cache ảnh đã tải để tránh load lại khi scroll.

### Acceptance Criteria

**AC-F06-1:** Feed hiển thị ảnh mới
```
Given User A gửi ảnh cho User B lúc 14:00
When User B mở app lúc 14:01
Then ảnh của User A xuất hiện ở đầu feed của User B
  với thông tin "1 phút trước"
```

**AC-F06-2:** Ảnh hết hạn 24h ẩn khỏi feed
```
Given User A gửi ảnh cho User B lúc 14:00 hôm qua
When User B mở feed vào lúc 14:01 hôm nay (25 giờ sau)
Then ảnh đó không còn xuất hiện trên feed
```

**AC-F06-3:** Trạng thái chưa xem / đã xem
```
Given User B nhận ảnh mới chưa xem
When User B mở app
Then ảnh hiển thị với visual indicator "chưa xem" (e.g. viền nổi bật)
  và sau khi User B xem ảnh đầy đủ, indicator chuyển sang "đã xem"
```

**AC-F06-4:** Empty state
```
Given User mới chưa có bạn bè nào
When User mở màn hình Feed
Then hệ thống hiển thị màn hình empty state với hướng dẫn "Thêm bạn bè để
  xem ảnh thú cưng của họ"
```

---

## F07 — Seen By

### Goal

Cho phép Sender biết ai đã xem ảnh của mình, thay thế cho hệ thống reaction
trong MVP.

### Users / Actors

- **Sender:** Người gửi ảnh, muốn biết ai đã xem.
- **Recipient:** Người xem ảnh, trạng thái "đã xem" được ghi nhận tự động.
- **System:** Backend lưu và trả về seen events.

### Functional Requirements

1. Hệ thống SHALL ghi nhận sự kiện "đã xem" cho một post khi Recipient mở và
   hiển thị ảnh đó đầy đủ (full-screen view).
2. Hệ thống SHALL lưu seen event với: post_id, viewer_user_id, seen_at
   timestamp.
3. Hệ thống SHALL cho phép Sender xem danh sách những người đã xem ảnh khi
   nhấn vào ảnh từ lịch sử gửi.
4. Hệ thống SHALL hiển thị số lượng người đã xem (e.g. "2 người đã xem") trên
   ảnh trong lịch sử của Sender.
5. Hệ thống SHALL cập nhật danh sách seen trong thời gian thực (hoặc khi
   Sender refresh).

### Non-goals

- Không có reaction (Like, Haha, Wow, ...) trong MVP.
- Không có comment hoặc quick response trong MVP.
- Không có reply by capture trong MVP.
- Không thông báo riêng cho từng lần seen (chỉ hiện số lượng tổng hợp).

### Technical Constraints

- Seen event được ghi nhận qua một API call khi client render ảnh ở chế độ
  full-screen.
- Tránh ghi duplicate seen event cho cùng một cặp (post_id, viewer_id).

### Acceptance Criteria

**AC-F07-1:** Ghi nhận seen khi xem ảnh
```
Given User B nhận ảnh từ User A và mở xem full-screen
When ảnh được hiển thị đầy đủ (không bị che khuất)
Then hệ thống ghi nhận seen event cho User B
  và seen event lưu đúng post_id, viewer_user_id, seen_at
```

**AC-F07-2:** Hiển thị danh sách seen cho Sender
```
Given User A đã gửi ảnh và User B, User C đã xem
When User A nhấn vào ảnh đó trong lịch sử gửi
Then User A thấy danh sách "User B, User C đã xem"
  và số lượng hiển thị là "2 người đã xem"
```

**AC-F07-3:** Không duplicate seen
```
Given User B đã xem ảnh của User A
When User B mở xem lại ảnh đó lần thứ hai
Then hệ thống không tạo thêm seen event mới
  và số lượng người xem không tăng
```

---

## F08 — History / Timeline (1 ngày)

### Goal

Cho phép người dùng cuộn ngược lại timeline ảnh đã gửi/nhận trong vòng 24 giờ
qua, như một lịch sử hoạt động ngắn hạn.

### Users / Actors

- **User:** Người xem lại ảnh đã gửi hoặc nhận trong ngày.

### Functional Requirements

1. Hệ thống SHALL cung cấp màn hình History riêng biệt, có thể truy cập từ
   bottom navigation.
2. Hệ thống SHALL hiển thị tất cả ảnh đã gửi và nhận trong 24 giờ qua, theo
   thứ tự thời gian từ mới đến cũ.
3. Hệ thống SHALL phân tách rõ hai section: "Đã gửi" và "Đã nhận".
4. Hệ thống SHALL giới hạn history chỉ trong khoảng 24 giờ tính từ thời điểm
   hiện tại — ảnh cũ hơn không hiển thị.
5. Hệ thống SHALL cho phép người dùng nhấn vào từng ảnh để xem full-screen,
   bao gồm thông tin người gửi/nhận và seen list.
6. Hệ thống SHALL hiển thị empty state nếu không có ảnh nào trong 24h qua.

### Non-goals

- Không hỗ trợ xem lịch sử quá 24 giờ đối với free user trong MVP.
- Không có tính năng download hay chia sẻ ảnh ra ngoài app.
- Không có "On this day" memory notification trong MVP.

### Technical Constraints

- API query lịch sử dùng filter `created_at >= NOW() - INTERVAL '24 hours'`.
- Phân trang cursor-based để tránh load toàn bộ 24h cùng lúc.

### Acceptance Criteria

**AC-F08-1:** Hiển thị lịch sử đúng 24h
```
Given User A đã gửi ảnh lúc 10:00 hôm nay và lúc 11:00 hôm qua
When User A mở màn hình History lúc 12:00 hôm nay
Then chỉ ảnh 10:00 hôm nay xuất hiện trong lịch sử
  và ảnh 11:00 hôm qua không hiển thị
```

**AC-F08-2:** Phân section rõ ràng
```
Given User đã gửi 2 ảnh và nhận 3 ảnh trong 24h qua
When User mở màn hình History
Then section "Đã gửi" hiển thị đúng 2 ảnh
  và section "Đã nhận" hiển thị đúng 3 ảnh
```

**AC-F08-3:** Xem ảnh full-screen từ History
```
Given User mở màn hình History
When User nhấn vào một ảnh bất kỳ
Then ảnh mở ra full-screen kèm thông tin người gửi và seen list
```

---

## F09 — Notification System

### Goal

Thông báo cho người dùng khi nhận ảnh mới và nhắc nhở chăm sóc thú cưng theo
lịch cố định được cấu hình bởi App Owner cho từng loại thú cưng.

### Users / Actors

- **Recipient:** Nhận push notification khi có ảnh mới.
- **Pet Owner (User):** Nhận daily reminders chăm sóc thú cưng.
- **App Owner (Admin):** Cấu hình lịch reminder cho từng loại thú cưng
  (chó/mèo).
- **System:** Notification service gửi push qua FCM/APNs.

### Functional Requirements

**Notification — Ảnh mới:**
1. Hệ thống SHALL gửi push notification đến Recipient ngay sau khi một ảnh mới
   được gửi đến họ.
2. Push notification SHALL chứa: tên người gửi, tên thú cưng (nếu có), và
   thumbnail ảnh.
3. Hệ thống SHALL điều hướng người dùng đến ảnh tương ứng khi họ tap vào
   notification.

**Notification — Daily Pet Reminders:**
4. Hệ thống SHALL hỗ trợ các loại reminder: cho ăn, ngủ, tắm, chơi.
5. Hệ thống SHALL cho phép App Owner cấu hình lịch (giờ) cho từng loại
   reminder, phân theo loại thú cưng (chó/mèo) — qua admin interface hoặc
   config.
6. Hệ thống SHALL gửi reminder đến tất cả người dùng có thú cưng thuộc loại
   tương ứng vào đúng giờ đã cấu hình.
7. Hệ thống SHALL cho phép người dùng bật/tắt từng loại reminder trong
   Settings.
8. Hệ thống SHALL tôn trọng timezone của thiết bị người dùng khi gửi
   reminder.

**Chung:**
9. Hệ thống SHALL dùng Firebase Cloud Messaging (FCM) cho Android và APNs
   cho iOS.
10. Hệ thống SHALL lưu device token vào PostgreSQL khi người dùng cấp quyền
    notification.

### Non-goals

- Không có notification cho video trong MVP.
- Không có in-app notification center / notification history trong MVP.
- Người dùng không tự cài giờ reminder — lịch do App Owner quản lý.

### Technical Constraints

- FastAPI background job (Celery hoặc APScheduler) xử lý việc gửi reminder
  theo lịch.
- Device token được refresh và cập nhật mỗi khi app mở.
- Rate limit: không gửi quá 5 reminder/ngày/user để tránh spam.

### Acceptance Criteria

**AC-F09-1:** Notification ảnh mới
```
Given User B đang có app đóng (background)
When User A gửi ảnh cho User B
Then User B nhận push notification trong vòng 5 giây
  với nội dung hiển thị tên User A và thumbnail ảnh
```

**AC-F09-2:** Deep link từ notification
```
Given User B nhận push notification về ảnh mới
When User B tap vào notification
Then app mở ra và điều hướng thẳng đến ảnh đó trong feed
```

**AC-F09-3:** Daily reminder đúng giờ
```
Given App Owner đã cấu hình reminder "Cho ăn" cho Chó lúc 07:00
  và User có ít nhất một Pet Profile loại "Chó"
When đồng hồ điện thoại User đến 07:00 (theo timezone thiết bị)
Then User nhận push notification "Đến giờ cho [tên chó] ăn rồi!"
```

**AC-F09-4:** Tắt reminder
```
Given User đã bật reminder "Tắm" trong Settings
When User tắt reminder "Tắm"
Then User không còn nhận notification loại "Tắm" kể từ sau đó
```

**AC-F09-5:** Timezone đúng
```
Given User A ở Hà Nội (UTC+7) và App Owner cấu hình reminder lúc 07:00
When đồng hồ Hà Nội là 07:00
Then User A nhận reminder (không phải 07:00 UTC)
```

---

## F10 — Settings (Liên kết tài khoản, Block/Report, Logout)

### Goal

Cung cấp các tùy chọn cài đặt tài khoản cần thiết cho MVP: liên kết/hủy liên
kết mạng xã hội, chặn/báo cáo người dùng vi phạm, và đăng xuất.

### Users / Actors

- **User:** Thực hiện các thao tác cài đặt.
- **Admin/Moderation Team:** Nhận report từ người dùng để xử lý.
- **System:** Xử lý liên kết OAuth, quản lý block list.

### Functional Requirements

**Liên kết tài khoản:**
1. Hệ thống SHALL hiển thị trạng thái liên kết của từng provider
   (Apple / Google / Facebook) trong Settings.
2. Hệ thống SHALL cho phép người dùng liên kết một provider chưa được liên kết.
3. Hệ thống SHALL cho phép người dùng hủy liên kết một provider, với điều kiện
   tài khoản còn ít nhất một provider khác được liên kết (tránh khóa tài
   khoản).

**Block/Report:**
4. Hệ thống SHALL cho phép người dùng block một người bạn; khi block thì
   friendship bị xóa và hai bên không thể gửi ảnh cho nhau.
5. Hệ thống SHALL cho phép người dùng report một người dùng khác với lý do
   (danh sách lý do cố định: spam, nội dung không phù hợp, quấy rối, khác).
6. Hệ thống SHALL lưu report vào database để Admin/Moderation Team xử lý.
7. Hệ thống SHALL ẩn người dùng bị block khỏi danh sách bạn bè và feed.

**Logout:**
8. Hệ thống SHALL cho phép người dùng đăng xuất; khi đăng xuất thì xóa local
   session và device token.
9. Hệ thống SHALL sau khi đăng xuất điều hướng người dùng về màn hình
   Onboarding.

### Non-goals

- Không có Privacy settings nâng cao (ai thấy profile, ai gửi được ảnh)
  trong MVP.
- Không có tính năng Hide post/user trong MVP.
- Không có tính năng xóa tài khoản trong MVP.
- Không có tính năng Cache cleaning trong MVP.

### Technical Constraints

- OAuth unlink thực hiện qua Firebase Auth API.
- Block list lưu trong PostgreSQL; mọi feed/friend query phải exclude users
  trong block list.
- Report record lưu với: reporter_id, reported_user_id, reason, created_at.

### Acceptance Criteria

**AC-F10-1:** Liên kết Google thành công
```
Given User chưa liên kết Google trong Settings
When User nhấn "Liên kết Google" và hoàn thành OAuth flow
Then Settings hiển thị Google là "Đã liên kết"
  và User có thể dùng tài khoản Google để đăng nhập lần sau
```

**AC-F10-2:** Không cho hủy liên kết provider duy nhất
```
Given User chỉ có duy nhất Apple được liên kết
When User cố hủy liên kết Apple
Then hệ thống hiển thị thông báo lỗi
  và không thực hiện hủy liên kết
```

**AC-F10-3:** Block user
```
Given User A và User B là bạn bè
When User A block User B
Then User B biến mất khỏi danh sách bạn bè của User A
  và User A biến mất khỏi danh sách bạn bè của User B
  và không ai trong hai người có thể gửi ảnh cho người kia
```

**AC-F10-4:** Report user
```
Given User A muốn report User B
When User A gửi report với lý do "Spam"
Then hệ thống lưu report thành công
  và hiển thị xác nhận "Cảm ơn bạn đã báo cáo"
  và User B vẫn hiển thị bình thường (không bị ẩn tự động)
```

**AC-F10-5:** Logout
```
Given User đang đăng nhập
When User nhấn "Đăng xuất" và xác nhận
Then session bị xóa trên thiết bị
  và User được redirect về màn hình Onboarding
  và User không còn nhận push notification
```

---

## F11 — Location & Time Metadata (Store Only)

### Goal

Gắn metadata vị trí (lat/lng) và thời gian vào mỗi ảnh được chụp để phục vụ
tính năng landmark/map trong phiên bản tương lai. MVP chỉ lưu, không hiển thị.

### Users / Actors

- **User:** Người chụp ảnh; app yêu cầu quyền location.
- **System:** Backend lưu metadata vào PostgreSQL.

### Functional Requirements

1. Hệ thống SHALL yêu cầu quyền truy cập vị trí khi người dùng sử dụng tính
   năng chụp ảnh lần đầu.
2. Hệ thống SHALL ghi lại latitude, longitude và timestamp của thiết bị tại
   thời điểm chụp ảnh, nếu người dùng đã cấp quyền.
3. Hệ thống SHALL cho phép chụp và gửi ảnh bình thường nếu người dùng từ chối
   quyền location (metadata vị trí để trống).
4. Hệ thống SHALL lưu location metadata vào bảng post trong PostgreSQL.
5. Hệ thống SHALL không hiển thị bất kỳ thông tin vị trí nào trên UI trong
   MVP.

### Non-goals

- Không hiển thị map, landmark hay địa điểm trong MVP.
- Không có tính năng "Offline with friend" dựa trên location proximity.
- Không chia sẻ vị trí với người dùng khác trong MVP.

### Technical Constraints

- Location được lấy một lần ngay tại thời điểm chụp (không tracking liên tục).
- Dữ liệu location chỉ dùng nội bộ, không expose qua API cho client.

### Acceptance Criteria

**AC-F11-1:** Lưu metadata khi có quyền
```
Given User đã cấp quyền location cho app
When User chụp và gửi ảnh thành công
Then record post trong PostgreSQL có latitude và longitude hợp lệ
  và timestamp chụp đúng với thời điểm thực tế
```

**AC-F11-2:** Gửi ảnh bình thường khi không có quyền location
```
Given User từ chối quyền location
When User chụp và gửi ảnh
Then ảnh vẫn được gửi thành công
  và record post trong PostgreSQL có latitude = NULL, longitude = NULL
```

**AC-F11-3:** Không hiển thị location trên UI
```
Given ảnh được gửi kèm metadata vị trí
When Recipient xem ảnh trong feed hoặc History
Then không có bất kỳ thông tin vị trí nào hiển thị trên UI
```

---

## Tóm tắt các quyết định kiến trúc

| Hạng mục            | Quyết định                                          |
|---------------------|-----------------------------------------------------|
| Mobile framework    | React Native (iOS + Android)                        |
| Authentication      | Firebase Auth (Anonymous + OAuth)                  |
| Backend API         | FastAPI (Python)                                    |
| Database            | PostgreSQL                                          |
| Object Storage      | AWS S3                                              |
| CDN                 | AWS CloudFront                                      |
| Push Notification   | Firebase Cloud Messaging (FCM) + APNs               |
| AI Validation       | On-device model (TFLite / CoreML)                   |
| Media Retention     | Free user: ẩn sau 24h (data vẫn lưu vĩnh viễn)     |
| Thị trường MVP      | Việt Nam                                            |

## Ngoài phạm vi MVP

Các tính năng sau sẽ xem xét ở phiên bản sau:

- Capture video + Video editor
- Image editor (filter, sticker, AI generate)
- Home Screen Widget
- Sync danh bạ
- CRUD Group + Send to group
- Reactions (Like, Haha, Wow, ...)
- Comment / Quick response / Reply by capture
- Landmark / Map từ location metadata
- Premium subscription (media retention dài hơn)
- Blended ad / Video ad
- Privacy settings nâng cao
- Xóa tài khoản
