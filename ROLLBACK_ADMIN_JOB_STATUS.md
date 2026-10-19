# PHƯƠNG ÁN KHÔI PHỤC VÀ ROLLBACK (ROLLBACK_ADMIN_JOB_STATUS.md)
**Dự án:** VietTranslate  
**Ngày lập:** 20/10/2026  
**Mục đích:** Hướng dẫn chi tiết từng bước khôi phục mã nguồn và cơ sở dữ liệu về trạng thái trước khi áp dụng các thay đổi chuẩn hóa trạng thái Job.

---

## I. NGUYÊN TẮC AN TOÀN TRƯỚC KHI ROLLBACK
1. Không tác động đến các bản ghi giao dịch (Hợp đồng, Báo giá, Đánh giá, Lịch sử kiểm toán).
2. Kiểm tra log hệ thống trước khi quyết định rollback để xác định chính xác nguyên nhân lỗi.
3. Luôn sao lưu dữ liệu hiện hành trước khi thực hiện bất kỳ thao tác rollback nào.

---

## II. ROLLBACK MÃ NGUỒN (CODE ROLLBACK)

### 1. Danh sách các file mã nguồn đã sửa đổi:
- `services/admin_job_service.py`
- `services/admin_task_service.py`
- `services/permissions.py`
- `services/proposals.py`
- `services/matching.py`
- `app.py`
- `templates/admin_jobs.html`
- `tests/test_job_status_moderation_lifecycle.py` (File test mới thêm)

### 2. Các bước rollback bằng Git (Nếu chưa commit):
Nếu các thay đổi đang ở working directory và chưa commit:
```bash
# 1. Kiểm tra trạng thái hiện tại
git status

# 2. Khôi phục các file mã nguồn về bản gốc trên nhánh main
git checkout -- services/admin_job_service.py
git checkout -- services/admin_task_service.py
git checkout -- services/permissions.py
git checkout -- services/proposals.py
git checkout -- services/matching.py
git checkout -- app.py
git checkout -- templates/admin_jobs.html

# 3. Xóa file test mới (nếu muốn trả về trạng thái ban đầu)
rm tests/test_job_status_moderation_lifecycle.py
```

### 3. Nếu đã commit trên branch riêng:
```bash
# Quay lại commit trước khi áp dụng thay đổi
git revert <COMMIT_HASH> --no-edit
```

---

## III. ROLLBACK DỮ LIỆU CƠ SỞ DỮ LIỆU (DATABASE ROLLBACK)

Nếu Quản trị viên đã thực hiện script backfill từ `ADMIN_JOB_STATUS_MIGRATION.md`:

### 1. Khôi phục từ bảng sao lưu tự động `job_status_backup_20261020`:
```sql
-- Trên PostgreSQL / SQLite
UPDATE job 
SET status = b.status 
FROM job_status_backup_20261020 b 
WHERE job.id = b.id;

-- Xác minh số lượng bản ghi đã khôi phục
SELECT COUNT(*) FROM job WHERE status = 'open' AND moderation_status = 'pending';
```

### 2. Nếu khôi phục toàn bộ database từ bản backup tgz/sql trước triển khai:
```bash
# 1. Dừng service Flask
sudo systemctl stop viettranslate.service

# 2. Khôi phục database PostgreSQL
pg_restore -U vietuser -d viettranslate_db -c /backup/viettranslate_pre_job_status_fix.dump

# 3. Khởi động lại service
sudo systemctl start viettranslate.service
```

---

## IV. BƯỚC XÁC MINH SAU KHI ROLLBACK (VERIFICATION CHECKLIST)
1. Kiểm tra trạng thái dịch vụ web:
   ```bash
   sudo systemctl status viettranslate.service
   ```
2. Chạy bộ kiểm thử regression gốc để đảm bảo hệ thống chạy bình thường:
   ```bash
   python -m unittest discover tests
   python test_hirer_job_moderation.py
   ```
3. Truy cập trang Quản trị Job `/admin/jobs` và kiểm tra giao diện đã hiển thị đúng cấu hình ban đầu.
