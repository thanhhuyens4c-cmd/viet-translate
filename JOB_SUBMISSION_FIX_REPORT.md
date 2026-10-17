# JOB_SUBMISSION_FIX_REPORT.md — Báo Cáo Sửa Luồng Tạo & Lưu Job

## I. Phân Tích Nguyên Nhân Gốc (Root Cause Analysis)

Khi truy vết luồng `POST /post-job`, phát hiện hai nhóm nguyên nhân khiến khách thuê không đăng được job hoặc gặp lỗi không mong muốn:

1. **Rào cản trạng thái xác minh & thông báo không rõ ràng:**
   - Người thuê chưa hoàn thành hồ sơ (như các tài khoản User 94, 96, 97 trên production) hoặc hồ sơ mới nộp đang ở trạng thái `pending` thì nút submit bị khóa ở frontend (`btn-submit` có cờ `disabled`), và backend trả về thông báo lỗi chung chung. Người dùng không phân biệt được là hệ thống lỗi hay tài khoản đang chờ Admin duyệt.
2. **Nguy cơ Exception trong giao dịch lưu Job (Transaction Rollback):**
   - Trong pipeline lưu job:
     ```python
     job = Job(hirer_id=user.id, **data)
     db.session.add(job)
     db.session.flush()
     _save_job_schedule(job, entries)
     _submit_for_moderation(job, user, is_new=True)
     save_job_files(job, validated)
     db.session.commit()
     ```
   - Hàm `_submit_for_moderation` gọi `evaluate_job_39_criteria(job)` và `AdminNotification`. Nếu hàm tiêu chí gặp trường dữ liệu bất thường hoặc quá trình tạo `AdminNotification` gặp lỗi (ví dụ cảnh báo URL scheme khi chạy ngoài request context chuẩn), exception chưa được bắt phòng vệ sẽ nhảy ra ngoài, khiến `post_job()` rollback toàn bộ transaction và trả về lỗi HTTP 500: *"Không thể lưu yêu cầu. Vui lòng thử lại"*.

---

## II. Các Biện Pháp Khắc Phục Đã Triển Khai

### 1. Bọc Phòng Vệ Cho `_submit_for_moderation(job, user, is_new)`
- **Vị trí:** `app.py:7674-7705`
- **Mã nguồn sau khi sửa:**
  ```python
  def _submit_for_moderation(job, user, is_new):
      """Đưa job vào hàng chờ duyệt (giống quy trình đăng job của hệ thống)."""
      import json
      from services.job_moderation import evaluate_job_39_criteria
      job.status = 'pending'
      job.moderation_status = 'pending'
      job.submission_version = 1 if is_new else (job.submission_version or 1) + 1
      summary_label = 'Chờ kiểm duyệt'
      try:
          result = evaluate_job_39_criteria(job)
          job.moderation_checklist_data = json.dumps(result)
          summary_label = result.get('summary_label', 'Chờ kiểm duyệt')
      except Exception as e:
          app.logger.warning(f"Error evaluating 39 criteria for job {job.id}: {e}")
          job.moderation_checklist_data = json.dumps({'summary_label': 'Chờ kiểm duyệt', 'error': str(e)})

      try:
          from models import AdminNotification
          db.session.add(AdminNotification(
              type='NEW_JOB',
              title=(f'Job mới chờ duyệt: #{job.id}' if is_new else f'Job cập nhật chờ duyệt lại: #{job.id}'),
              message=f'{user.name} vừa {"nộp" if is_new else "cập nhật"} job "{job.title}". Kết quả: {summary_label}',
              related_id=job.id, url=url_for('admin_job_review', job_id=job.id)))
      except Exception as e:
          app.logger.warning(f"Failed to create AdminNotification for job {job.id}: {e}")
  ```
- **Lợi ích:** Đảm bảo `job.status = 'pending'` và `job.moderation_status = 'pending'` **luôn luôn được thiết lập và lưu trữ thành công vào Database**. Lỗi thứ cấp từ thông báo hoặc bộ lọc phân tích tuyệt đối không thể làm mất dữ liệu Job hợp lệ của khách hàng.

### 2. Tăng Cường Tính Bền Vững & Ghi Log Lỗi trong `post_job`
- **Vị trí:** `app.py:7941-7965`
- **Thay đổi:**
  - `data.pop('_entries', [])`: Sử dụng fallback an toàn, loại bỏ nguy cơ `KeyError`.
  - Thay thế `print()` sơ sài bằng `app.logger.error(..., exc_info=True)` ghi lại đầy đủ stacktrace phục vụ chẩn đoán trên server.
  - Khi giao dịch thất bại, khôi phục lại `job_form_tokens` trong session để người dùng có thể gửi lại form mà không bị báo lỗi "token hết hạn".

### 3. Đồng Bộ Trải Nghiệm & Hướng Dẫn Người Thuê
- Khi tài khoản chưa đủ điều kiện (ví dụ `pending`), hàm `can_hirer_post_job` trả về lý do cụ thể và điều hướng khách thuê về đúng tab xem tiến độ xét duyệt (`/account/profile?tab=hirer_verify`), không gây hiểu lầm rằng hệ thống gặp trục trặc kỹ thuật.

---

## III. Kết Quả Kiểm Chứng (Verification Results)
- Chạy kiểm thử tự động `test_06_job_creation_enters_moderation_queue` trong `tests/test_hirer_verification_flow.py`:
  - Bản ghi Job được lưu thành công vào cơ sở dữ liệu.
  - Cả hai cột `status` và `moderation_status` đều mang giá trị `'pending'`.
  - Cột `submission_version` được khởi tạo là `1`.
  - Dữ liệu `moderation_checklist_data` chứa kết quả đánh giá 39 tiêu chí.
  - Job ngay lập tức xuất hiện trong câu truy vấn danh sách chờ duyệt của Admin.
