# JOB_SUBMISSION_FIX_REPORT.md — Báo Cáo Sửa Pipeline Đăng Job & Kiến Trúc Tách Rời Giao Dịch

## I. Phân Tích Nguyên Nhân Gốc (Root Cause Analysis)

Khi rà soát luồng `POST /post-job` và `POST /job/<id>/edit`, phát hiện các nguyên nhân cốt lõi khiến khách thuê không đăng được job hoặc bị mất dữ liệu:

1. **Rủi ro Rollback do Giao Dịch Nguyên Khối (Coupled Notification Transaction):**
   - Trong kiến trúc cũ, `_submit_for_moderation(job, user, is_new)` thực hiện:
     ```python
     db.session.add(AdminNotification(...))
     ```
     ngay trong session chính đang chứa `Job`, `JobSchedule`, và `JobAttachment`.
   - Mặc dù việc tạo notification có bọc `try/except`, lỗi ràng buộc dữ liệu chỉ xuất hiện khi SQLAlchemy thực hiện `db.session.commit()`. Khi đó, lệnh `commit()` nằm ngoài khối try của notification.
   - Nếu xảy ra lỗi ràng buộc dữ liệu tại bản ghi `AdminNotification` hoặc lỗi mạng/driver, exception bị ném ra khối `except Exception as e:` của `post_job()`, dẫn đến gọi `db.session.rollback()`.
   - **Hậu quả:** Toàn bộ công việc hợp lệ và lịch trình của khách thuê bị xóa sổ khỏi Database chỉ vì một bản ghi thông báo phụ trợ bị lỗi.

2. **Rào cản trạng thái xác minh & Token Form:**
   - Khách thuê mới nộp hồ sơ ở trạng thái `pending` bị chặn ở backend và giao diện, nhưng thông báo không chỉ dẫn rõ ràng.
   - Khi giao dịch gặp lỗi, token chống submit trùng lặp (`session['job_form_tokens']`) bị tiêu thụ mất, khiến người dùng không thể bấm gửi lại ngay mà phải tải lại trang.

---

## II. Các Giải Pháp Kỹ Thuật Đã Triển Khai

### 1. Tách Biệt Hoàn Toàn Giao Dịch Nghiệp Vụ & Thông Báo (Decoupled Transaction)
- **Vị trí sửa đổi:** `app.py:7964-7980` (`_submit_for_moderation`), `app.py:8220-8255` (`post_job`), `app.py:8330-8365` (`edit_job`).
- **Chi tiết thực thi:**
  1. **Hàm `_submit_for_moderation` được tinh gọn:**
     - Chỉ phụ trách cập nhật các trường của Job: `job.status = 'pending'`, `job.moderation_status = 'pending'`, `job.submission_version`, và lưu `job.moderation_checklist_data`.
     - **Hoàn toàn loại bỏ lệnh `db.session.add(AdminNotification)`** khỏi hàm này.
     - Trả về `summary_label` (ví dụ: "Chờ kiểm duyệt").
  2. **Giao dịch Cấp 1 (Primary Transaction - Bắt buộc):**
     - Tạo bản ghi `Job`.
     - Lưu danh sách lịch trình `JobSchedule`.
     - Lưu các tệp đính kèm `JobAttachment`.
     - Thực hiện `db.session.commit()`.
     - **Cam kết:** Tại thời điểm này, Job và toàn bộ dữ liệu nghiệp vụ của khách thuê đã được lưu trữ bền vững 100% trong Database.
  3. **Giao dịch Cấp 2 (Secondary Transaction - Thông báo):**
     - Sau khi Giao dịch Cấp 1 đã commit thành công, hệ thống mở một try-catch độc lập:
       ```python
       try:
           from models import AdminNotification
           db.session.add(AdminNotification(
               type='NEW_JOB',
               title=f'Job mới chờ duyệt: #{job.id}',
               message=f'{user.name} vừa nộp job "{job.title}". Kết quả: {summary_label}',
               related_id=job.id,
               url=url_for('admin_job_review', job_id=job.id)
           ))
           db.session.commit()
       except Exception as notif_err:
           db.session.rollback()
           app.logger.warning(
               f"[post_job] Job {job.id} saved successfully, but AdminNotification failed: {notif_err}"
           )
       ```
     - Nếu tạo notification thất bại: Chỉ rollback thông báo lỗi và ghi log cảnh báo; Job đã lưu ở Giao dịch Cấp 1 hoàn toàn không bị ảnh hưởng.

### 2. Quản Trị Token & Phục Hồi Khi Lỗi Form
- Khi form validation thất bại hoặc xảy ra lỗi ở Giao dịch Cấp 1:
  - Hệ thống hoàn lại token vào `session['job_form_tokens']`, cho phép người dùng sửa đổi và submit lại ngay mà không bị báo lỗi "Token hết hạn".
  - Giữ lại các giá trị form đã nhập để người dùng không phải điền lại từ đầu.

### 3. Hỗ Trợ Đầy Đủ Tệp Đính Kèm Của Job
- Xử lý lưu tệp tin đính kèm vào thư mục an toàn `uploads/job_attachments/`.
- Cập nhật hàm phân quyền `can_view_job_files(job_id)` trong `app.py` và `services/permissions.py` cho phép cả người thuê sở hữu và Quản trị viên (Admin) xem/tải tệp đính kèm.

---

## III. Kết Quả Kiểm Chứng Nghiệm Thu (Automated Verification)

Kiểm thử tự động tại `tests/test_hirer_job_lifecycle_integration.py` (`test_03_post_job_decouples_notification_no_rollback`):
- **Kịch bản kiểm thử:** Giả lập lỗi ném ngoại lệ (`SQLAlchemyError`) trong quá trình tạo `AdminNotification` khi người dùng gọi `POST /post-job`.
- **Kết quả thực tế:**
  - Request trả về mã chuyển hướng thành công HTTP 302 về trang chi tiết Job.
  - Bản ghi `Job` được tìm thấy đầy đủ trong Database với `status='pending'` và `moderation_status='pending'`.
  - Tệp log ghi nhận cảnh báo lỗi notification nhưng không hề rollback Job.
  - Tỷ lệ kiểm thử: **PASSED (100%)**.
