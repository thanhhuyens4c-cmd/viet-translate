# Hướng Dẫn Rollback & Phục Hồi Dịch Vụ VietTranslate

Tài liệu này cung cấp quy trình từng bước để phục hồi hệ thống về trạng thái ban đầu hoặc khôi phục dữ liệu từ bản sao lưu trong trường hợp xảy ra sự cố nghiêm trọng.

---

## 1. Vị Trí Các Bản Sao Lưu An Toàn Trên VPS

Mọi bản sao lưu đều được đặt tại thư mục bảo mật `/var/backups/viettranslate/` (chỉ user `root` có quyền đọc `chmod 700`):

| Bản sao lưu | Vị trí thư mục | Thành phần bao gồm |
| :--- | :--- | :--- |
| **Bản chụp trước chuyển đổi (Pre-migration)** | `/var/backups/viettranslate/pre_migration_20261014_232353/` | - `database_20261014_232353.db` (SQLite gốc)<br>- `env_20261014_232353.bak` (Cấu hình cũ)<br>- `uploads_20261014_232353.tar.gz` (Tệp upload ban đầu)<br>- File cấu hình Nginx gốc |
| **Bản sao lưu tự động hàng ngày** | `/var/backups/viettranslate/backup_YYYYMMDD_HHMMSS/` | - `postgres_db_*.sql.gz` (Dump PostgreSQL nén gzip)<br>- `storage_*.tar.gz` (Tệp kho lưu trữ nén gzip)<br>- `env_*.bak` (Biến môi trường)<br>- Unit file `viettranslate.service` |

---

## 2. Kịch Bản 1: Rollback Khẩn Cấp Về Trạng Thái SQLite Ban Đầu

Nếu hệ thống PostgreSQL trên VPS gặp sự cố nghiêm trọng cần đưa website về trạng thái chạy bằng SQLite ban đầu:

### Bước 1: Tạm dừng Systemd Service
```bash
sudo systemctl stop viettranslate.service
```

### Bước 2: Khôi phục file cơ sở dữ liệu SQLite và cấu hình `.env`
```bash
# Khôi phục file database SQLite gốc
cp -p /var/backups/viettranslate/pre_migration_20261014_232353/database_20261014_232353.db /www/wwwroot/157.66.100.101/instance/database.db
chown www:www /www/wwwroot/157.66.100.101/instance/database.db

# Khôi phục file cấu hình cũ (hoặc đổi FLASK_ENV=development và bỏ DATABASE_URL)
cp -p /var/backups/viettranslate/pre_migration_20261014_232353/env_20261014_232353.bak /www/wwwroot/157.66.100.101/.env
chown www:www /www/wwwroot/157.66.100.101/.env
chmod 600 /www/wwwroot/157.66.100.101/.env
```

### Bước 3: Khởi động lại dịch vụ
```bash
sudo systemctl start viettranslate.service
sudo systemctl status viettranslate.service --no-pager
```

### Bước 4: Xác minh hoạt động
```bash
curl -I -s http://127.0.0.1:5000 | head -5
curl -I -s http://103.161.118.158/ | head -5
```

---

## 3. Kịch Bản 2: Phục Hồi Cơ Sở Dữ Liệu PostgreSQL Từ Bản Backup

Nếu dữ liệu PostgreSQL bị sửa nhầm hoặc lỗi logic và cần restore về bản sao lưu gần nhất:

### Bước 1: Xác định bản backup cần phục hồi
```bash
ls -lt /var/backups/viettranslate/backup_*/postgres_db_*.sql.gz | head -3
```
*Giả sử bản backup chọn là:* `/var/backups/viettranslate/backup_20261014_233624/postgres_db_20261014_233624.sql.gz`

### Bước 2: Tạm dừng dịch vụ ứng dụng
```bash
sudo systemctl stop viettranslate.service
```

### Bước 3: Xóa và tái tạo database trống
```bash
sudo -u postgres psql << EOF
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'viettranslate_db' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS viettranslate_db;
CREATE DATABASE viettranslate_db OWNER viettranslate_user;
GRANT ALL PRIVILEGES ON DATABASE viettranslate_db TO viettranslate_user;
EOF
```

### Bước 4: Nạp lại dữ liệu từ tệp nén
```bash
gunzip -c /var/backups/viettranslate/backup_20261014_233624/postgres_db_20261014_233624.sql.gz | sudo -u postgres psql -d viettranslate_db
```

### Bước 5: Cấp lại quyền cho schema public nếu cần
```bash
sudo -u postgres psql -d viettranslate_db << EOF
GRANT ALL ON SCHEMA public TO viettranslate_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO viettranslate_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO viettranslate_user;
EOF
```

### Bước 6: Khởi động lại dịch vụ và kiểm tra
```bash
sudo systemctl start viettranslate.service
sudo systemctl status viettranslate.service --no-pager
curl -I -s http://103.161.118.158/ | head -5
```

---

## 4. Kịch Bản 3: Phục Hồi Kho Lưu Trữ Tệp (Uploads & Private Storage)

Nếu các tệp tải lên bị mất hoặc hỏng:

```bash
# Xóa thư mục cũ và giải nén từ bản backup
tar -xzf /var/backups/viettranslate/backup_20261014_233624/storage_20261014_233624.tar.gz -C /var/lib/viettranslate/

# Phân quyền lại cho user www
chown -R www:www /var/lib/viettranslate
chmod 750 /var/lib/viettranslate
chmod -R 700 /var/lib/viettranslate/private_storage
chmod -R 755 /var/lib/viettranslate/uploads
```

---

## 5. Kịch Bản 4: Rollback Bản Phát Hành 15/10/2026 (Audit & Bug Fixes)

Nếu cần quay lại phiên bản code hoặc database ngay trước đợt cập nhật 15/10/2026:

### Bước 1: Dừng dịch vụ Gunicorn
```bash
sudo systemctl stop viettranslate.service
```

### Bước 2: Khôi phục Codebase
```bash
# Xóa các file code hiện tại (giữ lại venv và static nặng)
cd /www/wwwroot/157.66.100.101
tar -xzf /var/backups/viettranslate/app_pre_deploy_20261015.tar.gz -C /www/wwwroot/157.66.100.101/
chown -R www:www /www/wwwroot/157.66.100.101
```

### Bước 3: Khôi phục Database Snapshot
```bash
sudo -u postgres pg_restore --clean --if-exists -d viettranslate_db /var/backups/viettranslate/db_pre_deploy_.dump
```

### Bước 4: Khởi động lại dịch vụ và kiểm tra
```bash
sudo systemctl start viettranslate.service
sudo systemctl status viettranslate.service --no-pager
```

---

## 5. Danh Sách Kiểm Tra Sau Khi Rollback

- [ ] `viettranslate.service` có trạng thái `active (running)`.
- [ ] Không có lỗi nghiêm trọng trong log: `journalctl -u viettranslate.service -n 30 --no-pager`.
- [ ] Trang chủ phản hồi HTTP 200: `curl -I http://103.161.118.158/`.
- [ ] Đăng nhập tài khoản Admin hoặc người dùng hoạt động bình thường.
- [ ] Các tệp đính kèm và ảnh đại diện tải lên bình thường.
