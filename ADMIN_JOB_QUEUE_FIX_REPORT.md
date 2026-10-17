# ADMIN_JOB_QUEUE_FIX_REPORT.md — Báo Cáo Sửa Hàng Chờ Kiểm Duyệt Job Của Admin

## I. Phân Tích Thực Trạng Hàng Chờ Admin

Trước khi sửa đổi, hàng chờ kiểm duyệt Job tại `/admin/jobs` gặp phải các vấn đề sau:

1. **Badge thông báo trên Sidebar Menu bị ẩn:**
   - Tại `templates/admin_base.html:848`, mục menu `Jobs` chỉ kiểm tra và hiển thị `admin_badge_flagged_jobs` (số lượng bài bị gắn cờ vi phạm).
   - Biến `admin_badge_pending_jobs` (số lượng bài đăng chờ duyệt) hoàn toàn không được đưa vào sidebar badge. Khi người thuê đăng job mới, Admin nhìn vào menu bên trái không thấy tín hiệu có bài mới chờ duyệt.
2. **Sự không nhất quán giữa `moderation_status` và `status` lịch sử:**
   - Các job cũ trên cơ sở dữ liệu có trường hợp `moderation_status` bị `NULL` (chưa chạy migration hoặc tạo từ phiên bản cũ).
   - Câu truy vấn badge chỉ đếm `Job.query.filter_by(moderation_status='pending').count()`, bỏ sót các job có `status='pending'` nhưng `moderation_status IS NULL`.
3. **Thiếu bộ lọc cho các Job bị từ chối:**
   - Tại giao diện `admin_jobs.html`, có các tab "Tất cả", "Chờ duyệt", "Nghiêm trọng", "Cần xem xét", "Đã duyệt", "Bị gắn cờ", "Đã lưu trữ" nhưng **thiếu tab "Bị từ chối"** (`rejected`). Admin không thể lọc nhanh danh sách các job đã bị từ chối phê duyệt.
4. **Hành vi phê duyệt mặc định & nhầm loại Notification:**
   - Tại route `POST /admin/jobs/<id>/moderate`: nếu request thiếu trường `decision`, code cũ tự động gán mặc định thành `'approve'`.
   - Thông báo gửi cho khách thuê khi Admin duyệt hoặc từ chối job dùng nhầm loại `JOB_MATCH` thay vì `JOB_APPROVED`, `JOB_NEEDS_REVISION`, `JOB_REJECTED`.

---

## II. Các Thay Đổi Mã Nguồn Đã Thực Hiện

### 1. Cập Nhật Context Processor Tính Badge Admin (`app.py:1313-1322`)
```python
badges['admin_badge_pending_jobs'] = Job.query.filter(
    db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
    db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
).count()
badges['admin_badge_flagged_jobs'] = Job.query.filter_by(is_flagged=True).count()
```
- Số đếm phản ánh chính xác cả các job mới lẫn dữ liệu lịch sử chưa đồng bộ, đồng thời loại trừ các job đã bị gắn cờ vi phạm.

### 2. Hiển Thị Badge Chờ Duyệt Trên Sidebar (`templates/admin_base.html:847-853`)
{% raw %}
```html
Jobs
{% if admin_badge_pending_jobs and admin_badge_pending_jobs > 0 %}
<span class="nav-badge warning">{{ admin_badge_pending_jobs }}</span>
{% elif admin_badge_flagged_jobs and admin_badge_flagged_jobs > 0 %}
<span class="nav-badge danger">{{ admin_badge_flagged_jobs }}</span>
{% endif %}
```
{% endraw %}
- Khi có job chờ duyệt, sidebar hiển thị badge màu vàng (warning) nổi bật. Nếu không có job pending nhưng có job bị flagged, hiển thị badge màu đỏ (danger).

### 3. Chuẩn Hóa Logic Bộ Lọc Trong `admin_jobs()` (`app.py:10290-10325`)
```python
is_pending = bool((job.moderation_status == 'pending' or (job.status == 'pending' and job.moderation_status not in ('approved', 'rejected', 'archived', 'flagged'))) and not job.is_flagged)
...
elif status_filter == 'rejected':
    include = bool(job.moderation_status == 'rejected')
```
- Đồng thời bổ sung tab `<a href="?status=rejected">Bị từ chối</a>` vào `templates/admin_jobs.html:79`.

### 4. Loại Bỏ Quyết Định Mặc Định Trong `admin_moderate_job()` (`app.py:10340-10445`)
- Yêu cầu bắt buộc `decision in ('approve', 'needs_revision', 'reject')`. Request thiếu hoặc sai decision bị từ chối rõ ràng kèm thông báo lỗi.
- Khi từ chối (`reject`), cập nhật cả `job.moderation_status = 'rejected'` và `job.status = 'closed'` để đóng job dứt điểm.
- Gửi đúng loại notification: `JOB_APPROVED`, `JOB_NEEDS_REVISION`, `JOB_REJECTED`.

---

## III. Kết Quả Sau Khi Sửa Đổi
1. Mọi công việc hợp lệ được gửi từ người thuê đều hiển thị đầy đủ trong hàng chờ `/admin/jobs?status=pending`.
2. Badge thông báo trên sidebar Admin hiển thị chính xác số lượng công việc đang chờ duyệt.
3. Danh sách lấy trực tiếp từ bảng `Job`, hoàn toàn độc lập với việc gửi thông báo `AdminNotification`.
4. Các thao tác xét duyệt của Admin được ghi nhận đầy đủ trong `AdminAuditLog` với đầy đủ chi tiết tiêu chí và lý do.
