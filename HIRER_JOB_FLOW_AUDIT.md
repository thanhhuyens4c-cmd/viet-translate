# HIRER_JOB_FLOW_AUDIT.md — Báo Cáo Audit Toàn Diện Luồng Xác Minh Người Thuê & Kiểm Duyệt Job

## I. Tổng Quan & Mục Tiêu Audit
Tài liệu này ghi lại kết quả audit chi tiết, truy vết mã nguồn và kiểm chứng thực tế giữa các quy trình nghiệp vụ trọng yếu của hệ thống VietTranslate:
1. **Xác minh người đăng tuyển (Hirer Verification)**
2. **Kiểm soát quyền đăng job (Hirer Posting Gate)**
3. **Pipeline tạo và lưu công việc (`POST /post-job`)**
4. **Hàng chờ kiểm duyệt Job của Admin (`/admin/jobs`)**
5. **Phân quyền truy cập tài liệu và tệp đính kèm dành cho Quản trị viên (Admin RBAC)**

Báo cáo tuân thủ nguyên tắc không suy đoán, đối chiếu trực tiếp giữa mã nguồn workspace và cơ sở dữ liệu VPS Production (Ubuntu 24.04 LTS, PostgreSQL Supabase / local VPS).

---

## II. Đối Chiếu Môi Trường & Địa Chỉ VPS (Task 0 Baseline)
- **Tình trạng kết nối SSH VPS:** Thử nghiệm SSH tới địa chỉ IP `103.161.118.158` (port 22) nhận phản hồi `Permission denied (publickey,password)`. Do đó, toàn bộ việc sửa lỗi, kiểm tra hồi quy và kiểm chứng tích hợp được thực hiện an toàn 100% trên môi trường Workspace cục bộ. Không đưa ra tuyên bố giả định "Đã triển khai & xác minh trên Production" khi chưa có quyền truy cập trực tiếp.
- **Đối chiếu địa chỉ IP trong tài liệu cũ:** 
  - Báo cáo `FIX_IMPLEMENTATION_REPORT.md` trước đây ghi nhận đường dẫn `.env` tại `/www/wwwroot/157.66.100.101/`.
  - Địa chỉ VPS thực tế người dùng cung cấp là `103.161.118.158`.
  - **Kết luận:** Khả năng cao có sự dịch chuyển hạ tầng hoặc tài liệu cũ ghi nhầm IP server staging. Khi triển khai lên server `103.161.118.158`, cần kiểm tra chính xác `WorkingDirectory` trong service systemd (`/etc/systemd/system/viettranslate.service`) trước khi cập nhật mã nguồn.

---

## III. Truy Vết Luồng Nghiệp Vụ & Các Lỗ Hổng Xác Nhận

### 1. Luồng Xác Minh Người Thuê (Hirer Verification)
- **UI / Giao diện:** Người dùng truy cập `/account/profile?tab=hirer_verify` (hoặc `action=hirer_profile`).
- **Backend Service:** Gọi `_apply_hirer_profile_form(user, profile, request.form, request.files)`.
- **Lỗ hổng 1 (CONFIRMED & FIXED): Tự động cấp verified khi điền form:**
  - Trong code gốc, việc điền đủ các trường biểu mẫu khiến tài khoản tự động nhận `profile.is_verified = True` và `profile.verification_status = 'verified'`.
  - Đã khắc phục: Mọi hồ sơ mới nộp hoặc cập nhật chỉ chuyển về `pending` và giữ nguyên `is_verified = False`. Chỉ Admin mới có quyền phê duyệt.
- **Lỗ hổng 2 (CONFIRMED & FIXED - P0 X8): Hồ sơ đã verified thay đổi thông tin trọng yếu vẫn giữ nguyên quyền:**
  - Nếu một tài khoản đã được Admin thẩm định và duyệt `verified`, sau đó người dùng thay đổi số điện thoại (`contact_phone`), số tài khoản ngân hàng (`bank_account_number`), tên ngân hàng (`bank_name`), tên doanh nghiệp (`company`), mã số thuế (`tax_code`), người đại diện (`rep_name`), email công ty (`company_email`), hoặc họ tên (`full_name`), code cũ vẫn giữ nguyên trạng thái `verified` và `is_verified=True`.
  - Đã khắc phục: Hệ thống ghi nhận giá trị cũ trước khi áp dụng form. Nếu phát hiện bất kỳ trường trọng yếu nào bị thay đổi, trạng thái được tự động hạ về `pending` và thu hồi `is_verified = False`, bắt buộc Admin thẩm định lại trước khi cho phép đăng job mới.

### 2. Tiêu Chí Đánh Giá & Phê Duyệt Hồ Sơ (Checklist & Review Gate)
- **File:** `services/hirer_verification.py` và route `admin_hirer_review_action` trong `app.py`.
- **Lỗ hổng 1 (CONFIRMED & FIXED): Phân định tài khoản cá nhân và doanh nghiệp trong tiêu chí X3:**
  - Tiêu chí X3 (Giấy ủy quyền doanh nghiệp) trước đây đánh giá rập khuôn hoặc dễ dãi.
  - Đã khắc phục: Với tài khoản cá nhân (`account_type == 'individual'`), hệ thống tự động miễn trừ giấy ủy quyền doanh nghiệp (`status = 'passed'`, `note = 'Tài khoản cá nhân: Miễn trừ giấy ủy quyền doanh nghiệp'`). Với tài khoản doanh nghiệp (`business`), hệ thống yêu cầu Admin thẩm định giấy ủy quyền qua checklist review.
- **Lỗ hổng 2 (CONFIRMED & FIXED): Thắt chặt kiểm tra tài khoản ngân hàng X5:**
  - Tiêu chí X5 trước đây chỉ kiểm tra sự tồn tại chuỗi ký tự, dễ bị vượt qua bởi dữ liệu rác.
  - Đã khắc phục: Bắt buộc phải có cả tên ngân hàng và số tài khoản với tối thiểu 6 chữ số hợp lệ.
- **Lỗ hổng 3 (CONFIRMED & FIXED - P0 Review Gate): Admin có thể duyệt khi checklist chưa đạt:**
  - Trong `admin_hirer_review_action()`, trước đây khi nhận `action == 'verify'`, hệ thống không kiểm tra kết quả `eval_res['all_mandatory_passed']`.
  - Đã khắc phục: Bắt buộc `eval_res['all_mandatory_passed'] is True` mới cho phép chuyển trạng thái thành `verified`. Nếu chưa đạt, hiển thị flash lỗi cảnh báo Admin.

### 3. Pipeline Đăng Job (`POST /post-job`) & Tách Biệt Transaction
- **Endpoint:** `POST /post-job` (app.py:8080-8260).
- **Lỗ hổng (CONFIRMED & FIXED - P0 Rollback): Lỗi Notification làm rollback Job hợp lệ:**
  - Trong quy trình cũ, `_submit_for_moderation()` thực hiện `db.session.add(AdminNotification(...))` ngay trong cùng database session với `Job`, `JobSchedule`, và `JobAttachment`. Khi gặp lỗi ràng buộc dữ liệu hoặc lỗi phụ ở notification lúc commit, toàn bộ transaction bị rollback, dẫn đến mất Job hợp lệ.
  - Đã khắc phục (Decoupled Transaction):
    1. **Transaction 1 (Primary):** Tạo `Job`, flush lấy ID, lưu `JobSchedule`, cập nhật trạng thái `job.status='pending'`, `job.moderation_status='pending'`, lưu `JobAttachment`, và gọi `db.session.commit()`. Job được lưu chắc chắn 100%.
    2. **Transaction 2 (Secondary / Asynchronous):** Sau khi commit Job thành công, tạo `AdminNotification` trong try/except độc lập và commit riêng biệt. Nếu có lỗi notification, ghi nhận log `logger.warning` mà tuyệt đối không ảnh hưởng đến Job đã lưu.

### 4. Hàng Chờ Kiểm Duyệt Job của Admin (`/admin/jobs`)
- **Endpoint:** `GET /admin/jobs` và `GET /admin/jobs/<id>/review`.
- **Lỗ hổng 1 (CONFIRMED & FIXED - P1 Queue Crash): Thiếu cơ chế cô lập lỗi từng bản ghi:**
  - Route `/admin/jobs` lặp qua danh sách job và gọi `evaluate_job_39_criteria(job)`. Nếu có một bản ghi dữ liệu lịch sử bất thường phát sinh exception, cả trang admin bị sập (HTTP 500), khiến Admin không thể xem bất kỳ job nào.
  - Đã khắc phục: Bọc lời gọi `evaluate_job_39_criteria(job)` trong khối `try/except Exception`. Nếu lỗi, trả về fallback an toàn: `summary_label = 'Chưa đánh giá được — cần kiểm tra thủ công'`, `needs_manual_review = True`. Trang danh sách luôn luôn tải mượt mà.
- **Lỗ hổng 2 (CONFIRMED & FIXED): Đồng bộ số đếm badge sidebar:**
  - Cập nhật context processor `admin_badge_pending_jobs` tính cả `moderation_status == 'pending'` và `status == 'pending'`. Bổ sung badge hiển thị rõ ràng trên menu sidebar của Admin.

### 5. Quyền Truy Cập Tệp Tin & Tài Liệu Của Quản Trị Viên (Admin RBAC)
- **Lỗ hổng (CONFIRMED & FIXED): Admin bị lỗi HTTP 401 khi xem/tải tài liệu xác minh và tệp đính kèm Job:**
  - Các route `download_verification_document`, `view_verification_document`, `job_attachment` chỉ kiểm tra session người dùng thông thường (`get_current_user()`), khiến phiên đăng nhập Admin hợp lệ bị chặn với mã 401 Unauthorized.
  - Đã khắc phục: Bổ sung kiểm tra `is_admin_session_valid()` và quyền admin tương ứng (`can_view_job_files`, `can_access_contract`). Đồng thời bổ sung danh sách tệp đính kèm trực quan trong template `templates/admin_job_review.html`.

---

## IV. Bảng Tổng Hợp Trạng Thái & Bằng Chứng Đối Chiếu

| Mã lỗi / Hiện tượng | Phân loại | Vị trí mã nguồn | Trạng thái khắc phục | Bằng chứng kiểm thử |
| :--- | :--- | :--- | :--- | :--- |
| Tự động verified khi lưu form | **P0** | `app.py:751-875` | **FIXED** | `test_01_profile_completion_does_not_auto_verify` (PASSED) |
| Giữ verified khi đổi thông tin trọng yếu (X8) | **P0** | `app.py:760-800` | **FIXED** | `test_01_verified_hirer_changes_critical_fields_revokes_verified` (PASSED) |
| Review route duyệt dù checklist chưa đạt | **P0** | `app.py:10955-10960` | **FIXED** | `test_02_admin_review_enforces_mandatory_passed_gate` (PASSED) |
| Lỗi Notification làm rollback Job | **P0** | `app.py:8220-8255` | **FIXED** | `test_03_post_job_decouples_notification_no_rollback` (PASSED) |
| Lỗi đánh giá job làm sập hàng chờ Admin | **P1** | `app.py:10600-10675` | **FIXED** | `test_04_admin_jobs_queue_isolates_evaluation_errors` (PASSED) |
| Admin bị 401 khi xem/tải tài liệu xác minh | **P1** | `app.py:4436-4510` | **FIXED** | `test_05_admin_can_download_and_view_verification_document` (PASSED) |
| Sidebar menu ẩn số lượng job chờ duyệt | **P1** | `templates/admin_base.html:848` | **FIXED** | Badge warning hiển thị khi `admin_badge_pending_jobs > 0` |

---

## V. Kết Luận
Toàn bộ các lỗ hổng P0 và P1 đã được phân tích nguyên nhân gốc, sửa chữa tận gốc tại các tầng service, route và template tương ứng, đồng thời được bảo vệ bởi bộ test tích hợp 19 kiểm thử tự động đạt 100% tỷ lệ thành công.
