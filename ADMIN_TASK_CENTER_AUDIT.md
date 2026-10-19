# ADMIN_TASK_CENTER_AUDIT.md — Báo Cáo Rà Soát Hiện Trạng & Phương Án Xây Dựng Trung Tâm Tác Vụ Admin

**Dự án:** VietTranslate  
**Ngày thực hiện:** 20/10/2026  
**Mục tiêu:** Rà soát toàn bộ luồng quản trị (Job, Translator, Hirer, Report, Dispute), phân tích lỗ hổng phê duyệt và thiết kế Trung tâm Tác vụ Admin thống nhất kèm cơ chế Duyệt nhanh an toàn và Tối ưu Mobile.

---

## I. Hiện Trạng Hệ Thống Quản Trị (Admin Architecture)

### 1. Cấu trúc Điều hướng & Sidebar (`templates/admin_base.html`)
- Hệ thống quản trị hiện phân chia thành 3 phân khu:
  1. **Dashboard** (`/admin`)
  2. **Duyệt & Kiểm duyệt**:
     - *Hồ sơ PDV* (`/admin/translators` - `view_translators`)
     - *Người đăng* (`/admin/hirers` - `view_hirers`)
     - *Jobs* (`/admin/jobs` - `view_jobs`)
     - *Report* (`/admin/reports` - `view_reports`)
     - *Khiếu nại đơn thuê* (`/admin/disputes`)
  3. **Quản lý & Hệ thống**: Users, Proposal, Contract, Schedule, Payment, Review, Notifications, Admins, Audit logs.
- **Điểm khuyết thiếu:**
  - Chưa hề có mục **"Tác vụ"** (`/admin/tasks`) thống nhất. Admin khi đăng nhập phải bấm qua từng trang độc lập để biết trang nào đang có việc chờ xử lý.
  - Trên màn hình di động (< 768px), sidebar được chuyển thành off-canvas drawer (`transform: translateX(-100%)`).

### 2. Luồng Kiểm Duyệt Công Việc Hiện Tại (`admin_jobs` & `admin_job_review`)
- **Danh sách công việc (`templates/admin_jobs.html`)**:
  - Đã có các tab lọc theo trạng thái: *Tất cả, Chờ duyệt, Nghiêm trọng, Cần xem xét, Đã duyệt, Bị từ chối, Bị gắn cờ, Đã lưu trữ*.
  - Đã có checklist sàng lọc nhanh 8 mục.
  - **Vấn đề 1:** Chưa có trường tìm kiếm theo từ khóa (tiêu đề, tên khách thuê, mã Job `#ID`) hoặc khoảng ngày nộp.
  - **Vấn đề 2 (Hiệu năng):** Trong `app.py:10619`, route đang thực hiện `all_jobs = Job.query.order_by(Job.created_at.desc()).all()`, sau đó duyệt qua toàn bộ database bằng vòng lặp Python để chạy `evaluate_job_39_criteria(job)` rồi mới lọc bằng Python. Khi số lượng công việc lớn, thao tác này sẽ gây nghẽn CPU và độ trễ nghiêm trọng.
  - **Vấn đề 3 (Lỗ hổng duyệt nhanh):** Đang tồn tại route `POST /admin/jobs/<job_id>/approve` (dòng 10890) trực tiếp gán `job.status = 'open'` và `job.moderation_status = 'approved'` mà **hoàn toàn bỏ qua**:
    * Không kiểm tra xem Job có vi phạm nghiêm trọng (C1, C2, C3, C6, C9, C10) hay không.
    * Không kiểm tra người đăng tuyển đã xác minh danh tính hay chưa.
    * Không ghi nhận `moderation_checklist_data`, `moderated_at`, `moderated_by`.
    * Không thông báo cho người đăng tuyển.
  - **Vấn đề 4 (Lỗ hổng duyệt chi tiết):** Trong route `admin_moderate_job()` (dòng 10711), nhánh `decision == 'approve'` chỉ dựa vào hộp thoại Javascript `confirm(...)` ở phía client (`templates/admin_job_review.html:429`). Backend không hề có câu lệnh chặn `if eval_res['total_critical'] > 0: raise/flash error`, dẫn tới việc request POST trực tiếp có thể ép duyệt job vi phạm nghiêm trọng.

### 3. Lỗi Giao Diện Mobile Trên Trang Xét Duyệt Chi Tiết (`admin_job_review.html`)
- Tại dòng 325 của `templates/admin_job_review.html`:
  ```html
  <div style="position: fixed; bottom: 0; left: var(--sidebar-w); right: 0; ...">
  ```
- Biến `--sidebar-w` có giá trị `256px`. Khi mở trên điện thoại (<= 768px), sidebar của Admin đã bị ẩn ra ngoài mép trái màn hình, nhưng thanh nút cố định bên dưới vẫn bị ép `left: 256px`.
- **Hậu quả:** Toàn bộ thanh hành động chứa nút *Yêu cầu chỉnh sửa, Duyệt, Từ chối* bị đẩy văng sang bên phải màn hình, làm mất nút hoặc gây tràn ngang trầm trọng trên mobile.

---

## II. Bản Đồ Các Luồng Tác Vụ Cần Xử Lý Trong Hệ Thống

| Loại tác vụ | Nguồn dữ liệu (Model) | Điều kiện "Chờ xử lý" (Pending) | Quyền Admin yêu cầu | Route xem chi tiết | Hành động khả dụng |
|---|---|---|---|---|---|
| **Duyệt Job** | `Job` (`models.Job`) | `moderation_status == 'pending'` hoặc (`status == 'pending'` và chưa bị gắn cờ) | `view_jobs`, `approve_job`, `reject_job` | `/admin/jobs/<id>/review` | **Duyệt nhanh (có điều kiện)**, Xem xét chi tiết, Gắn cờ, Lưu trữ |
| **Xác minh PDV** | `TranslatorVerification` / `TranslatorProfile` | `TranslatorVerification.status == 'pending'` hoặc `TranslatorProfile.is_verified == False` | `view_translators`, `verify_translator` | `/admin/verifications/<id>` | Xem hồ sơ & minh chứng, Xác minh, Yêu cầu bổ sung, Từ chối |
| **Xác minh Người đăng** | `HirerProfile` / `User` | `HirerProfile.verification_status == 'pending'` | `view_hirers`, `verify_hirer` | `/admin/hirers/<id>/verify` | Xem hồ sơ doanh nghiệp / CCCD, Xác minh, Yêu cầu sửa, Từ chối |
| **Báo cáo vi phạm** | `Report` (`models.Report`) | `Report.status == 'new'` hoặc `investigating` | `view_reports`, `resolve_report` | `/admin/reports` | Điều tra, Giải quyết, Từ chối |
| **Khiếu nại đơn thuê** | `Dispute` (`models.Dispute`) | `Dispute.status in ('open', 'mediating', 'escalated')` | Quyền quản trị tranh chấp | `/admin/disputes/<id>` | Mở phiên hòa giải, Đóng băng/Xử lý Escrow, Kết luận |

---

## III. Các Nguyên Tắc & Quy Chuẩn Thiết Kế

### 1. Nguyên Tắc Duyệt Nhanh An Toàn (Safe Quick Approval)
Nút "Duyệt nhanh" chỉ được phép kích hoạt khi thỏa mãn đồng thời 100% các điều kiện sau:
1. **Trạng thái hợp lệ:** Job đang ở trạng thái `pending`, không bị `archived`, không bị `rejected`, và không bị `flagged`.
2. **Độ an toàn nội dung:** Đánh giá 39 tiêu chí có `total_critical == 0` (không vi phạm thông tin liên hệ ngoài C1, thanh toán ngoài C2, cọc phí C3, địa điểm nguy hiểm C6, bóc lột C9, trái pháp luật C10).
3. **Độ tin cậy người đăng:** Người đăng tuyển (`HirerProfile`) đã hoàn thành xác minh danh tính (`is_verified == True` hoặc `verification_status == 'verified'`).
4. **Quyền hạn Admin:** Quản trị viên đang đăng nhập có quyền `approve_job`.
5. **Đồng bộ dữ liệu:** Ghi nhận đầy đủ audit log, thời gian `moderated_at`, ID người duyệt `moderated_by`, bản snapshot tiêu chí `moderation_checklist_data`, gửi thông báo cho khách thuê và trigger gửi thông báo cho PDV phù hợp.
6. **Loại trừ duyệt nhanh:** Nếu Job có vi phạm nghiêm trọng hoặc người đăng chưa xác minh: **Ẩn / Vô hiệu hóa nút Duyệt nhanh**, hiển thị nhãn cảnh báo lý do (ví dụ: *"Có vi phạm nghiêm trọng — Cần xét duyệt chi tiết"*, *"Khách chưa xác minh"*) và chỉ dẫn sang nút *"Xét duyệt chi tiết →"*.

### 2. Nguyên Tắc Bộ Lọc & Tối Ưu Truy Vấn
- **Không quét toàn bộ bảng Job khi không cần thiết:**
  - Với các tab lọc theo database (chờ duyệt, đã duyệt, từ chối, gắn cờ, lưu trữ): Thực hiện lọc trực tiếp bằng SQL query `Job.query.filter(...)`.
  - Phân trang chuẩn chỉ (mặc định 20 bản ghi/trang) và chỉ chạy `evaluate_job_39_criteria` cho các bản ghi trên trang hiện tại.
  - Vẫn bảo toàn khả năng nhận diện các Job có vi phạm nghiêm trọng bằng cách ưu tiên quét các job pending.
- **Hỗ trợ tìm kiếm kết hợp đa điều kiện:**
  - Từ khóa `q` (tìm theo ID, tiêu đề, tên/email người gửi).
  - Loại tác vụ `type` (`all`, `job`, `translator`, `hirer`, `report`, `dispute`).
  - Trạng thái `status` (`pending`, `critical`, `needs_revision`, `all`).
  - Mức độ ưu tiên `priority` (`critical`, `warning`, `normal`).
  - Khoảng thời gian `time_range` (`today`, `7d`, `30d`, `all`).

### 3. Nguyên Tắc Tối Ưu Cho Điện Thoại (Mobile First)
- **Desktop (>= 768px):** Bảng dữ liệu quản trị rộng rãi, hiển thị đầy đủ các cột và nút thao tác nhanh.
- **Mobile (< 768px):** Chuyển đổi thành dạng thẻ Card (`admin-task-card`):
  - Phân tách rõ mã tác vụ, icon loại tác vụ, người gửi, mức độ ưu tiên và thời gian gửi.
  - Nút bấm to rõ, chiều cao tối thiểu **44px**, dễ chạm bằng ngón tay cái.
  - Sửa dứt điểm lỗi lệch thanh hành động cố định trên `admin_job_review.html` (`left: 0 !important`).
  - Bộ lọc hỗ trợ mở rộng/thu gọn (Collapsible Drawer) tránh choán màn hình.

---

## IV. Kế Hoạch Triển Khai Chi Tiết

- **Task 1: Xây dựng Module Nghiệp vụ Duyệt An Toàn (`services/admin_job_service.py`)**
  Hợp nhất logic duyệt an toàn dùng chung cho cả Duyệt nhanh và Duyệt chi tiết.
- **Task 2: Xây dựng Route & Controller Trung Tâm Tác Vụ (`/admin/tasks`)**
  Tạo endpoint tổng hợp các hàng chờ có bộ lọc đa năng, đếm chỉ số thực tế từ DB.
- **Task 3: Thiết Kế Giao Diện Trung Tâm Tác Vụ (`templates/admin_tasks.html`)**
  Gồm 4 thẻ chỉ số KPI thực tế, thanh bộ lọc thống nhất, danh sách dạng Table trên Desktop và dạng Cards trên Mobile.
- **Task 4: Nâng Cấp Danh Sách Quản Trị Job (`templates/admin_jobs.html`)**
  Bổ sung ô tìm kiếm, nút Duyệt nhanh có kiểm tra điều kiện an toàn, chuyển đổi responsive card trên mobile.
- **Task 5: Khắc Phục Lỗi Layout Mobile Trên `templates/admin_job_review.html`**
  Khắc phục CSS `left: var(--sidebar-w)` trên mobile <= 768px.
- **Task 6: Cập Nhật Sidebar & Dashboard Admin (`templates/admin_base.html` & `templates/admin_dashboard.html`)**
  Bổ sung liên kết Tác vụ và Badge tổng việc cần làm.
- **Task 7: Viết Bộ Kiểm Thử Tự Động & Báo Cáo Nghiệm Thu**
  Viết test case kiểm tra parity, permission, duyệt an toàn và chống bypass.
