# ADMIN_JOB_QUEUE_FIX_REPORT.md — Báo Cáo Sửa Hàng Chờ & Cơ Chế Cô Lập Lỗi Quản Trị Job

## I. Phân Tích Thực Trạng & Rủi Ro Hàng Chờ Admin

Trước khi sửa đổi, hàng chờ kiểm duyệt Job tại `/admin/jobs` và trang thẩm định chi tiết `/admin/jobs/<id>/review` tiềm ẩn các vấn đề nghiêm trọng:

1. **Rủi ro sập toàn bộ danh sách do một bản ghi lỗi (Queue-level Crash):**
   - Trong route `admin_jobs()`, hệ thống lặp qua danh sách toàn bộ các job và thực hiện:
     ```python
     eval_res = evaluate_job_39_criteria(job)
     ```
   - Đoạn code này hoàn toàn không có khối `try/except` bảo vệ cấp từng bản ghi.
   - Nếu trong cơ sở dữ liệu có bất kỳ job nào chứa dữ liệu bất thường (ví dụ: ngày giờ sai format, trường rỗng không tương thích, hoặc lỗi logic trong evaluator), toàn bộ request `GET /admin/jobs` sẽ trả về lỗi HTTP 500.
   - **Hậu quả:** Admin hoàn toàn không xem được danh sách kiểm duyệt; các job hợp lệ mới đăng bị "tắc nghẽn" và biến mất khỏi tầm mắt của Admin.

2. **Khó khăn trong việc thẩm định tệp đính kèm của Job:**
   - Tại màn hình xem xét job `templates/admin_job_review.html`, không có khối hiển thị danh sách các tệp đính kèm do khách thuê tải lên (`JobAttachment`).
   - Route tải tệp `job_attachment` chỉ cho phép người thuê sở hữu truy cập, khiến Admin bấm vào link tài liệu bị báo lỗi 403/401.

3. **Ẩn Badge số lượng chờ duyệt trên thanh Menu:**
   - Menu Sidebar Admin chỉ hiển thị badge cho job bị gắn cờ (`admin_badge_flagged_jobs`), hoàn toàn không hiển thị số lượng job đang chờ duyệt (`admin_badge_pending_jobs`).

4. **Sự không nhất quán giữa `moderation_status` và `status` trong dữ liệu lịch sử:**
   - Các job cũ trên cơ sở dữ liệu có trường hợp `moderation_status` mang giá trị `NULL`.
   - Câu truy vấn badge cũ chỉ đếm `Job.query.filter_by(moderation_status='pending').count()`, làm sót các job có `status='pending'` nhưng `moderation_status IS NULL`.

---

## II. Các Thay Đổi Mã Nguồn Đã Thực Hiện

### 1. Cơ Chế Cô Lập Lỗi Từng Bản Ghi (Per-Record Error Isolation)
- **Vị trí sửa đổi:** `app.py:10600-10675` (`admin_jobs`) và `app.py:10680-10730` (`admin_job_review`).
- **Chi tiết thực thi:**
  - Bọc lời gọi `evaluate_job_39_criteria(job)` trong khối `try/except Exception`:
    ```python
    try:
        eval_res = evaluate_job_39_criteria(job)
    except Exception as eval_err:
        app.logger.warning(f"Error evaluating criteria for job {job.id}: {eval_err}")
        eval_res = {
            'summary_label': 'Chưa đánh giá được — cần kiểm tra thủ công',
            'severity': 'review',
            'needs_manual_review': True,
            'passed_count': 0,
            'total_count': 39,
            'groups': {}
        }
    ```
  - **Tác dụng:** Dù có bản ghi bị lỗi dữ liệu, danh sách `/admin/jobs` vẫn hiển thị đầy đủ 100% các job khác. Bản ghi gặp sự cố được đánh dấu cảnh báo "Cần kiểm tra thủ công" để Admin xử lý an toàn mà không làm tê liệt hệ thống.

### 2. Bổ Sung Hiển Thị & Phân Quyền Xem Tệp Đính Kèm Của Job Cho Admin
- **Template:** Bổ sung khối hiển thị tệp đính kèm trong `templates/admin_job_review.html`:
  - Hiển thị tên file gốc (`original_filename`), định dạng, dung lượng.
  - Cung cấp nút xem trực tuyến và tải về an toàn.
- **Phân quyền Backend:** Cập nhật hàm `can_view_job_files(job_id)` trong `app.py` và `services/permissions.py`:
  ```python
  def can_view_job_files(job_id):
      if is_admin_session_valid():
          return True
      # Kiểm tra quyền hirer sở hữu...
  ```
  - Đảm bảo Admin có đầy đủ thẩm quyền kiểm tra hồ sơ, tài liệu công việc trước khi ra quyết định duyệt.

### 3. Đồng Bộ Trạng Thái & Số Đếm Badge Sidebar
- Cập nhật Context Processor (`app.py:1313-1322`):
  ```python
  badges['admin_badge_pending_jobs'] = Job.query.filter(
      db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
      db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
  ).count()
  ```
- Hiển thị badge màu vàng (warning) trên sidebar Admin khi có job chờ duyệt.

### 4. Bổ Sung Bộ Lọc "Bị từ chối" & Chuẩn Hóa Quyết Định Duyệt
- Thêm tab `<a href="?status=rejected">Bị từ chối</a>` vào `templates/admin_jobs.html`.
- Bắt buộc `decision in ('approve', 'needs_revision', 'reject')` trong route `admin_moderate_job()`. Request thiếu decision bị từ chối rõ ràng.
- Gửi đúng mã loại notification: `JOB_APPROVED`, `JOB_NEEDS_REVISION`, `JOB_REJECTED`.

---

## III. Kết Quả Kiểm Thử Nghiệm Thu (Automated Verification)

Kiểm thử tự động tại `tests/test_hirer_job_lifecycle_integration.py` (`test_04_admin_jobs_queue_isolates_evaluation_errors`):
- **Kịch bản kiểm thử:** Cố tình đưa vào database một Job có dữ liệu bất thường và mock hàm `evaluate_job_39_criteria` ném ra ngoại lệ `RuntimeError("Critical evaluation failure")`.
- **Kết quả thực tế:**
  - Route `GET /admin/jobs` vẫn phản hồi mã thành công HTTP 200.
  - Job vẫn xuất hiện trong danh sách hiển thị với nhãn cảnh báo an toàn `"Chưa đánh giá được — cần kiểm tra thủ công"`.
  - Tỷ lệ kiểm thử: **PASSED (100%)**.
