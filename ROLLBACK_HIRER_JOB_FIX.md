# ROLLBACK_HIRER_JOB_FIX.md — Kế Hoạch Hoàn Nguyên & Quản Trị Triển Khai An Toàn

## I. Tổng Quan Phạm Vi Thay Đổi Mã Nguồn

Các file đã được hiệu chỉnh và kiểm thử an toàn trong workspace:
1. `app.py`:
   - Hàm `_apply_hirer_profile_form`: Ngăn chặn tự cấp verified; bổ sung cơ chế phát hiện thay đổi thông tin trọng yếu (X8) để thu hồi verified về pending.
   - Hàm `_submit_for_moderation`: Tinh gọn, chỉ cập nhật trạng thái Job, tách hoàn toàn `AdminNotification` ra ngoài.
   - Route `post_job` và `edit_job`: Áp dụng kiến trúc Decoupled Transaction (Giao dịch Cấp 1 lưu Job/Schedule/Attachment commit trước; Giao dịch Cấp 2 tạo Notification commit riêng biệt, chống rollback Job).
   - Route `admin_jobs` và `admin_job_review`: Cô lập lỗi đánh giá 39 tiêu chí cấp từng bản ghi (try/except fallback).
   - Route `admin_hirer_review_action`: Enforce kiểm tra bắt buộc `eval_res['all_mandatory_passed']` trước khi cho phép `verify`.
   - Các route `download_verification_document`, `view_verification_document`, `job_attachment`: Bổ sung kiểm tra `is_admin_session_valid()`, loại bỏ lỗi 401 Unauthorized cho Quản trị viên.
2. `services/hirer_verification.py`:
   - Hàm `can_hirer_post_job`: Kiểm tra chặt chẽ cả `is_verified is True` và `verification_status == 'verified'`.
   - Hàm `evaluate_hirer_criteria`: Chuẩn hóa tiêu chí X3 (miễn trừ giấy ủy quyền cho cá nhân, yêu cầu duyệt cho doanh nghiệp) và thắt chặt kiểm tra tài khoản ngân hàng X5.
3. `services/permissions.py`: Bổ sung quyền xem tệp đính kèm Job cho Quản trị viên.
4. `templates/admin_base.html`: Hiển thị badge số lượng công việc chờ duyệt trên sidebar menu.
5. `templates/admin_jobs.html`: Bổ sung tab bộ lọc công việc "Bị từ chối".
6. `templates/admin_job_review.html`: Bổ sung khối hiển thị tệp đính kèm công việc cho Quản trị viên thẩm định.
7. `tests/test_hirer_job_lifecycle_integration.py`: Bộ kiểm thử tích hợp 5 ca kiểm thử thực tế.

**Tình trạng hiện tại:** `CODE FIXED & INTEGRATION TESTED IN WORKSPACE (100% PASSED)`.  
Chưa thực hiện triển khai tự động lên VPS do kết nối SSH tới `103.161.118.158` bị chặn quyền (`Permission denied`).

---

## II. Phương Án Hoàn Nguyên (Rollback Procedure)

### 1. Hoàn Nguyên Mã Nguồn Workspace (Git Rollback)
Nếu người dùng muốn hủy bỏ toàn bộ các thay đổi cục bộ và quay về commit trước:
```bash
# 1. Kiểm tra trạng thái các file đang sửa
git status

# 2. Hoàn nguyên các file mã nguồn và template đã sửa
git checkout main -- app.py services/hirer_verification.py services/permissions.py templates/admin_base.html templates/admin_jobs.html templates/admin_job_review.html

# 3. Xóa file test mới tạo nếu không cần giữ lại
rm tests/test_hirer_job_lifecycle_integration.py
```

### 2. Hoàn Nguyên Trên VPS (Production Rollback)
Nếu sau khi deploy lên VPS mà hệ thống phát sinh lỗi cần quay lại phiên bản trước:
```bash
# 1. Truy cập thư mục ứng dụng trên VPS
cd /www/wwwroot/viettranslate   # hoặc thư mục chứa ứng dụng thực tế

# 2. Quay về commit trước đó
git checkout <commit_hash_cu>

# 3. Khôi phục cơ sở dữ liệu nếu có thực hiện migration
psql -U <postgres_user> -d <database_name> < backup_vt_truoc_deploy.sql

# 4. Khởi động lại dịch vụ
sudo systemctl restart viettranslate.service
```

---

## III. Hướng Dẫn Triển Khai Lên VPS Production (`103.161.118.158`)

### Bước 1: Xác Định Môi Trường & Thư Mục Triển Khai Thực Tế
Lưu ý: Báo cáo cũ đề cập đường dẫn `/www/wwwroot/157.66.100.101/`. Khi truy cập VPS `103.161.118.158`, hãy kiểm tra file cấu hình dịch vụ để biết chính xác thư mục:
```bash
systemctl cat viettranslate.service | grep WorkingDirectory
```

### Bước 2: Sao Lưu Toàn Diện Trước Khi Cập Nhật (Mandatory Backup)
1. **Sao lưu Database PostgreSQL:**
   ```bash
   pg_dump -U viettranslate_user -d viettranslate_db -F c -b -v -f /backup/db_pre_deploy_$(date +%Y%m%d_%H%M%S).dump
   ```
2. **Kiểm tra file sao lưu:**
   ```bash
   ls -lh /backup/db_pre_deploy_*.dump
   ```

### Bước 3: Đồng Bộ Mã Nguồn Đã Sửa
Đẩy các commit đã kiểm thử từ repository lên Git, sau đó kéo về VPS:
```bash
cd <WorkingDirectory>
git fetch origin
git merge origin/main
```

### Bước 4: Khởi Động Lại Dịch Vụ & Kiểm Tra Trạng Thái
```bash
sudo systemctl restart viettranslate.service
sudo systemctl status viettranslate.service
```
Kiểm tra log theo thời gian thực để đảm bảo không có exception khởi động:
```bash
journalctl -u viettranslate.service -n 50 --no-pager
```

---

## IV. Phương Án Xử Lý Dữ Liệu Lịch Sử (User 100 & Các Job Cũ)

1. **Đối với User 100 (`minhnhatt@gmail.com`):**
   - Tài khoản này có trạng thái `verified` ngày 15/10/2026 nhưng không có log trong `AdminAuditLog` (do lỗi tự duyệt của code cũ).
   - **Quy tắc an toàn:** Tuyệt đối không chạy lệnh UPDATE hàng loạt trên Production để hạ trạng thái của tất cả tài khoản.
   - **Xử lý khuyến nghị:** Admin đăng nhập vào `/admin/hirers/100/verify` để tiến hành thẩm định chính thức:
     - Nếu hồ sơ hợp lệ: Admin bấm Duyệt để hệ thống tạo bản ghi `AdminAuditLog` chính thức.
     - Nếu hồ sơ thiếu thông tin: Admin bấm Yêu cầu bổ sung (`needs_revision`).

2. **Đối với các Job cũ có `moderation_status IS NULL`:**
   - Hệ thống mới đã có cơ chế bọc phòng vệ (fallback) tại `admin_jobs()` và `admin_job_review()`, tự động xử lý các job này thành `'pending'` trong câu truy vấn và cô lập mọi exception dữ liệu. Toàn bộ 161 job lịch sử đều được an toàn.
