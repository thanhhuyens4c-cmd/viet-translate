# ROLLBACK_HIRER_JOB_FIX.md — Kế Hoạch Hoàn Nguyên & Quản Trị Rủi Ro

## I. Tổng Quan Phạm Vi Thay Đổi

Các file đã được chỉnh sửa trong workspace:
1. `app.py`: Logic xác minh hồ sơ, pipeline đăng job, hàng chờ admin hirers và admin jobs.
2. `services/hirer_verification.py`: Backend gate `can_hirer_post_job`.
3. `templates/admin_base.html`: Badge pending jobs trên menu sidebar.
4. `templates/admin_jobs.html`: Thêm tab bộ lọc job bị từ chối.
5. `templates/admin_hirers.html`: Phân biệt badge trạng thái người thuê.
6. `templates/account_profile.html`: Điều kiện hiển thị tích xanh hồ sơ khách thuê.
7. `tests/test_hirer_verification_flow.py`: Bộ kiểm thử tự động mới.

**Tình trạng triển khai hiện tại:** `CODE FIXED IN WORKSPACE, NOT DEPLOYED TO PRODUCTION`.
Chưa thực hiện bất kỳ lệnh thay đổi cấu trúc database hoặc deploy đè lên VPS.

---

## II. Phương Án Hoàn Nguyên (Rollback Procedure)

### 1. Hoàn Nguyên Mã Nguồn Workspace (Git Rollback)
Nếu cần đưa mã nguồn workspace về trạng thái commit gốc ban đầu (`cbcd98c`):
```bash
# Kiểm tra lại các file đã sửa
git status

# Hoàn nguyên các file mã nguồn (chỉ thực hiện khi có yêu cầu hoàn nguyên)
git checkout main -- app.py services/hirer_verification.py templates/admin_base.html templates/admin_jobs.html templates/admin_hirers.html templates/account_profile.html

# Xóa file test mới tạo nếu không muốn giữ lại
rm tests/test_hirer_verification_flow.py
```

### 2. Kế Hoạch Triển Khai Sản Phẩm An Toàn (Safe Deploy Plan)
Khi người dùng quyết định triển khai lên VPS:
1. **Bước 1: Sao lưu (Backup):**
   - Backup cơ sở dữ liệu PostgreSQL production:
     `pg_dump -U <user> -d <dbname> > backup_vt_hirer_job_$(date +%Y%m%d_%H%M%S).sql`
   - Kiểm tra dung lượng và tính toàn vẹn của tệp backup trước khi tiếp tục.
2. **Bước 2: Đồng bộ mã nguồn:**
   - Kéo code đã được nghiệm thu vào thư mục `/www/wwwroot/157.66.100.101` trên VPS.
3. **Bước 3: Khởi động lại dịch vụ an toàn:**
   - `sudo systemctl restart viettranslate.service`
   - `sudo systemctl status viettranslate.service` (kiểm tra status `active (running)`).
4. **Bước 4: Kiểm tra khói (Smoke Test) trên VPS:**
   - Đăng nhập tài khoản Admin, kiểm tra `/admin/jobs` và `/admin/hirers`.
   - Kiểm tra log ứng dụng: `journalctl -u viettranslate.service -n 50 --no-pager`.

### 3. Phương Án Xử Lý Dữ Liệu Lịch Sử (User 100)
- **Hiện trạng:** User 100 (`minhnhatt@gmail.com`) là tài khoản người thuê duy nhất trên VPS bị tự động kích hoạt `verified` vào ngày 15/10/2026 mà không có bản ghi trong `admin_audit_log`.
- **Khuyến nghị an toàn:**
  - **KHÔNG** chạy lệnh SQL bulk update chuyển tất cả tài khoản `verified` về `pending` (vì sẽ ảnh hưởng đến các tài khoản đã được Admin phê duyệt hợp lệ như User 95).
  - Admin vào trực tiếp màn hình `/admin/hirers/100/verify` trên giao diện quản trị để thực hiện thẩm định chính thức:
    - Nếu thông tin của User 100 hợp lệ -> Admin nhấn **Xác minh** để hệ thống ghi nhận `AdminAuditLog`.
    - Nếu thiếu thông tin -> Admin nhấn **Yêu cầu bổ sung** hoặc **Từ chối**.
  - Phương án này đảm bảo không gây gián đoạn bất ngờ và tuân thủ đúng quy trình nghiệp vụ.
