# Hướng Dẫn Triển Khai VietTranslate Trên VPS Ubuntu 24.04 LTS

Tài liệu này mô tả chi tiết kiến trúc, cấu hình dịch vụ, thiết lập bảo mật và quy trình vận hành hệ thống VietTranslate hoạt động hoàn toàn cục bộ trên máy chủ VPS Ubuntu 24.04 LTS, không còn phụ thuộc runtime vào Supabase Cloud hay Vercel.

---

## 1. Tổng Quan Kiến Trúc Triển Khai

| Thành phần | Công nghệ / Phiên bản | Cổng / Socket | Tài khoản thực thi |
| :--- | :--- | :--- | :--- |
| **Hệ điều hành** | Ubuntu 24.04 LTS (Kernel 6.8 x86_64) | - | `root` quản trị |
| **Reverse Proxy** | Nginx (aaPanel compiled) | `80` (HTTP), `443` (HTTPS khi gắn domain) | `www:www` |
| **WSGI Server** | Gunicorn 26.2.0 (2 Sync Workers) | `127.0.0.1:5000` | `www:www` (Non-root) |
| **Backend App** | Python 3.12 (Flask 3.0.0, SQLAlchemy 2.1) | Venv tại `/www/wwwroot/157.66.100.101/venv` | `www:www` |
| **Cơ sở dữ liệu** | PostgreSQL 16.15 (Localhost) | `127.0.0.1:5432` | `viettranslate_user` |
| **Lưu trữ tệp công khai** | Thư mục cục bộ `/var/lib/viettranslate/uploads/` | - | `www:www` (755) |
| **Lưu trữ tệp riêng tư**| Thư mục cục bộ `/var/lib/viettranslate/private_storage/` | - | `www:www` (700) |
| **Dịch vụ sao lưu** | Cron job + Shell script | 02:30 hàng ngày | `root` |

---

## 2. Cấu Trúc Thư Mục Trên VPS

```text
/www/wwwroot/157.66.100.101/             <-- Thư mục mã nguồn ứng dụng (quyền www:www)
├── .env                                 <-- Biến môi trường production (chmod 600, www:www)
├── app.py                               <-- Entrypoint Flask ứng dụng
├── config.py                            <-- Cấu hình hệ thống (ProductionConfig)
├── models.py                            <-- Định nghĩa SQLAlchemy models
├── venv/                                <-- Virtual environment Python 3.12
└── static/                              <-- Tài nguyên giao diện tĩnh (CSS, JS, icons)

/var/lib/viettranslate/                  <-- Thư mục lưu trữ dữ liệu bền vững ngoài code
├── uploads/                             <-- Tệp người dùng tải lên công khai (avatar, cert)
│   ├── avatars/
│   └── certificates/
└── private_storage/                     <-- Tệp tài liệu riêng tư (KYC, hợp đồng, deliverable)
    ├── private_verifications/
    ├── deliverables/
    └── chat_images/

/var/backups/viettranslate/              <-- Thư mục chứa các bản sao lưu tự động (chmod 700)
/etc/systemd/system/viettranslate.service<-- File cấu hình systemd service cho Gunicorn
/usr/local/bin/backup_viettranslate.sh   <-- Script sao lưu tự động hàng ngày
/etc/cron.d/viettranslate_backup         <-- Cron schedule sao lưu tự động
```

---

## 3. Cấu Hình Cơ Sở Dữ Liệu (PostgreSQL 16)

### 3.1. Thiết lập lắng nghe và tối ưu tài nguyên (1 vCPU, 2GB RAM)
File cấu hình: `/etc/postgresql/16/main/postgresql.conf`
- `listen_addresses = 'localhost'`: Chỉ cho phép kết nối từ máy chủ nội bộ qua `127.0.0.1`, tuyệt đối không mở cổng 5432 ra ngoài Internet.
- `shared_buffers = 128MB`: Phù hợp với máy chủ 2GB RAM, tránh tranh chấp bộ nhớ với Gunicorn và Nginx.
- `work_mem = 4MB`: Giới hạn bộ nhớ cho mỗi câu query sorting/hash.
- `maintenance_work_mem = 64MB`: Tối ưu cho bảo trì index và vacuum.
- `max_connections = 50`: Giới hạn connection pool, kết hợp SQLAlchemy `pool_size=3`, `max_overflow=2`.

### 3.2. Tài khoản và phân quyền
- **Database**: `viettranslate_db`
- **User runtime**: `viettranslate_user` (quyền `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`).
- Chỉ cấp quyền `ALL` trên database `viettranslate_db` và schema `public`.

---

## 4. Quản Lý Dịch Vụ Ứng Dụng (Systemd Service)

Dịch vụ được định nghĩa tại `/etc/systemd/system/viettranslate.service`:

```ini
[Unit]
Description=VietTranslate Web Application Service (Gunicorn)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/157.66.100.101
EnvironmentFile=/www/wwwroot/157.66.100.101/.env
ExecStart=/www/wwwroot/157.66.100.101/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 --timeout 60 --access-logfile - --error-logfile - app:app
Restart=on-failure
RestartSec=5s
TimeoutStartSec=30
StandardOutput=journal
StandardError=journal
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Các lệnh quản lý dịch vụ:
```bash
# Kiểm tra trạng thái dịch vụ
sudo systemctl status viettranslate.service --no-pager

# Khởi động / Dừng / Khởi động lại dịch vụ
sudo systemctl start viettranslate.service
sudo systemctl stop viettranslate.service
sudo systemctl restart viettranslate.service

# Xem log thời gian thực qua journalctl
sudo journalctl -u viettranslate.service -f

# Xem 50 dòng log gần nhất
sudo journalctl -u viettranslate.service -n 50 --no-pager
```

---

## 5. Cấu Hình Nginx Reverse Proxy & Bảo Mật

File vhost: `/www/server/nginx/conf/vhost/157.66.100.101.conf`
File reverse proxy: `/www/server/panel/vhost/nginx/proxy/157.66.100.101/*.conf`

- **Upstream**: `proxy_pass http://127.0.0.1:5000;`
- **Proxy headers**: `Host $host`, `X-Real-IP $remote_addr`, `X-Forwarded-For $proxy_add_x_forwarded_for`, `Upgrade $http_upgrade`, `Connection $connection_upgrade`.
- **Cấu hình SSL / HTTPS (Port 443)**:
  - Chứng chỉ SSL tự ký hiện tại: `/etc/ssl/certs/viettranslate_selfsigned.crt`
  - Khóa riêng tư SSL: `/etc/ssl/private/viettranslate_selfsigned.key`
  - Giao thức: `TLSv1.2 TLSv1.3`
  - Hỗ trợ đồng thời cả HTTP cổng 80 và HTTPS cổng 443.
- **Kích hoạt Let's Encrypt khi có tên miền riêng**:
  Hệ thống đã chuẩn bị sẵn script tự động:
  ```bash
  sudo /usr/local/bin/enable_letsencrypt.sh yourdomain.com
  ```
  Script sẽ tự kiểm tra DNS, xin cấp chứng chỉ qua Certbot webroot, cập nhật Nginx và reload tự động.
- **Chặn truy cập trực tiếp các tệp nhạy cảm**:
  ```nginx
  location ~ ^/(\.user.ini|\.htaccess|\.git|\.env|\.svn|\.project|LICENSE|README.md|instance) {
      return 404;
  }
  ```
- **Kiểm tra cú pháp Nginx và reload**:
  ```bash
  nginx -t
  nginx -s reload
  ```

---

## 6. Chính Sách Sao Lưu Tự Động (Backup & Retention)

- **Script sao lưu**: `/usr/local/bin/backup_viettranslate.sh`
- **Lịch chạy**: `30 2 * * *` (02:30 sáng hàng ngày qua `/etc/cron.d/viettranslate_backup`).
- **Nội dung sao lưu**:
  1. Dump toàn bộ PostgreSQL: `pg_dump` nén gzip (`postgres_db_*.sql.gz`).
  2. Nén toàn bộ tệp lưu trữ: `/var/lib/viettranslate/` (`storage_*.tar.gz`).
  3. Sao lưu cấu hình môi trường: `.env` và unit file systemd.
- **Kiểm tra an toàn**:
  - Kiểm tra dung lượng ổ đĩa trống tối thiểu 1GB trước khi thực hiện.
  - Tự động xóa các bản sao lưu cũ hơn 7 ngày để chống đầy ổ cứng 16GB SSD.
  - Phân quyền nghiêm ngặt `chmod 700` cho thư mục backup và `chmod 600` cho file nén.
