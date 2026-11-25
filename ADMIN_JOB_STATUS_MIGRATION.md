# HƯỚNG DẪN MIGRATION & BACKFILL DỮ LIỆU JOB (ADMIN_JOB_STATUS_MIGRATION.md)
**Dự án:** VietTranslate  
**Ngày lập:** 20/10/2026  
**Trạng thái:** SẴN SÀNG (CHẾ ĐỘ AN TOÀN — HỖ TRỢ DRY-RUN & ROLLBACK)  

---

## I. MỤC TIÊU VÀ PHẠM VI ÁP DỤNG
Dữ liệu kiểm toán trên môi trường cho thấy một số bản ghi công việc được tạo trước khi hệ thống chuẩn hóa kiểm duyệt (hoặc tạo từ các kịch bản kiểm thử / seed ban đầu) có sự bất nhất giữa hai trường:
- `Job.status = 'open'` nhưng `Job.moderation_status = 'pending'`.

**Nguyên tắc an toàn:**
1. Các bản sửa đổi backend trong code hiện tại đã tự động cô lập an toàn các bản ghi này:
   - Chúng **không** xuất hiện trên danh sách việc làm công khai (`/jobs`).
   - Chúng **không** lọt vào API việc làm đề xuất (`/api/jobs/recommended`).
   - Chúng hiển thị đúng badge **"Chờ duyệt"** (thay vì nhãn nhầm "Đã duyệt").
2. Migration/backfill này là **tùy chọn (optional)** dành cho Quản trị viên muốn đồng bộ triệt để trường `status = 'pending'` cho các bản ghi đang chờ duyệt trong DB mà chưa từng có quyết định phê duyệt.
3. **Tuyệt đối không** cập nhật các job đã đóng (`closed`, `cancelled`), đã lưu trữ (`archived`), hoặc đã chốt hợp đồng (`contracted`, `completed`).

---

## II. KỊCH BẢN BACKFILL PYTHON (HỖ TRỢ DRY-RUN)

Kịch bản script Python có thể chạy trực tiếp trong thư mục dự án:

```python
# scripts/backfill_job_statuses.py
import sys
from datetime import datetime
from app import app, db
from models import Job

def run_backfill(dry_run=True):
    with app.app_context():
        print(f"=== CHẠY KIỂM ĐỊNH & ĐỒNG BỘ TRẠNG THÁI JOB (DRY_RUN={dry_run}) ===")
        
        # Nhóm 1: Job status='open' nhưng moderation_status='pending', chưa đóng và chưa bị cờ
        candidates = Job.query.filter(
            Job.status == 'open',
            Job.moderation_status == 'pending',
            Job.closed_at.is_(None),
            db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
        ).all()
        
        print(f"Phát hiện {len(candidates)} jobs có status='open' nhưng moderation_status='pending'.")
        for j in candidates:
            print(f"  - Job #{j.id}: '{j.title[:40]}' (Tạo ngày: {j.created_at}) -> Cần chuyển status='pending'")
            
        if not dry_run:
            for j in candidates:
                j.status = 'pending'
            db.session.commit()
            print(f"-> ĐÃ CẬP NHẬT THÀNH CÔNG {len(candidates)} BẢN GHI SANG status='pending'.")
        else:
            print("-> CHẾ ĐỘ DRY-RUN: Không có dữ liệu nào bị thay đổi trong database.")

if __name__ == '__main__':
    dry_run_mode = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run_mode = False
    run_backfill(dry_run=dry_run_mode)
```

### Cách thực thi an toàn trên máy chủ:
```bash
# 1. Chạy thử nghiệm xem trước danh sách bản ghi (Dry-run):
python -c "from scripts.backfill_job_statuses import run_backfill; run_backfill(dry_run=True)"

# 2. Sau khi xác nhận số lượng, thực thi chính thức:
python -c "from scripts.backfill_job_statuses import run_backfill; run_backfill(dry_run=False)"
```

---

## III. LỆNH SQL THỦ CÔNG TRÊN POSTGRESQL / SQLITE

### 1. Kiểm tra số lượng trước khi update:
```sql
SELECT id, title, status, moderation_status, created_at 
FROM job 
WHERE status = 'open' 
  AND moderation_status = 'pending' 
  AND closed_at IS NULL 
  AND (is_flagged = FALSE OR is_flagged IS NULL);
```

### 2. Thực thi cập nhật:
```sql
-- Tạo bảng sao lưu trước khi cập nhật
CREATE TABLE job_status_backup_20261020 AS 
SELECT id, status, moderation_status, closed_at 
FROM job 
WHERE status = 'open' AND moderation_status = 'pending';

-- Cập nhật đồng bộ
UPDATE job 
SET status = 'pending' 
WHERE status = 'open' 
  AND moderation_status = 'pending' 
  AND closed_at IS NULL 
  AND (is_flagged = FALSE OR is_flagged IS NULL);
```

### 3. Đối chiếu số lượng sau khi cập nhật:
```sql
SELECT status, moderation_status, COUNT(*) 
FROM job 
GROUP BY status, moderation_status;
```
Số lượng bản ghi `status = 'open' AND moderation_status = 'pending'` phải bằng 0.

---

## IV. PHƯƠNG ÁN ROLLBACK DỮ LIỆU
Nếu cần khôi phục lại trạng thái cũ từ bảng backup:
```sql
UPDATE job 
SET status = b.status 
FROM job_status_backup_20261020 b 
WHERE job.id = b.id;

-- Xóa bảng backup sau khi hoàn tất
DROP TABLE job_status_backup_20261020;
```
