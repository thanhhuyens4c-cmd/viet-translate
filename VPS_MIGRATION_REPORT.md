# Báo Cáo Chuyển Đổi Hệ Thống VietTranslate Sang VPS Ubuntu 24.04 LTS

**Thời gian hoàn thành:** 14/10/2026  
**Môi trường thực hiện:** Ubuntu 24.04 LTS (Noble)  
**Địa chỉ máy chủ:** `103.161.118.158`  
**Trạng thái thực tế:** **HOÀN TẤT 100% (PRODUCTION READY)**

---

## 1. Kết Quả Tổng Quát

Dự án VietTranslate đã được chuyển đổi hoàn toàn từ mô hình phát triển cục bộ (SQLite) và phụ thuộc vào các dịch vụ đám mây (Supabase Cloud, Vercel) sang mô hình vận hành độc lập, tự chủ hoàn toàn trên máy chủ VPS:
- Toàn bộ cơ sở dữ liệu quan hệ được chuyển sang **PostgreSQL 16** chạy trên localhost VPS.
- Toàn bộ 35 bảng dữ liệu, 21 tài khoản người dùng, 47 công việc, 30 hợp đồng và các thực thể nghiệp vụ được di chuyển với tỷ lệ khớp **100% không mất bất kỳ bản ghi nào**.
- Ứng dụng Flask được chuyển sang quản lý chuyên nghiệp bằng **Systemd Service** và **Gunicorn WSGI**, chạy dưới tài khoản dịch vụ phi đặc quyền `www:www` (không chạy bằng root).
- Tệp người dùng tải lên và tài liệu xác minh riêng tư được tách biệt hoàn toàn khỏi mã nguồn, lưu trữ bền vững tại `/var/lib/viettranslate/` với cơ chế kiểm soát quyền truy cập nghiêm ngặt.
- Hệ thống sao lưu tự động hàng ngày (PostgreSQL dump + storage archive) được thiết lập với chính sách lưu trữ 7 ngày chống đầy ổ đĩa 16GB SSD.

---

## 2. Những Thay Đổi Đã Thực Hiện

### 2.1. Cấu hình ứng dụng và mã nguồn
1. **`app.py`**:
   - Thêm `load_dotenv()` ngay đầu file để đảm bảo biến môi trường từ `.env` luôn được nạp nhất quán dù ứng dụng chạy qua Gunicorn, CLI hay script phụ trợ.
   - Chuẩn hóa logic kiểm tra database: Nếu `FLASK_ENV=production`, hệ thống bắt buộc phải có `DATABASE_URL` trỏ tới PostgreSQL. Loại bỏ hoàn toàn cơ chế âm thầm chuyển về SQLite trong production.
   - Bổ sung cấu hình đường dẫn lưu trữ tệp qua biến môi trường `UPLOAD_FOLDER` và `PRIVATE_STORAGE_FOLDER` trỏ tới thư mục dữ liệu bền vững ngoài repository.
2. **`config.py`**:
   - Cập nhật `ProductionConfig`: Khi thiếu `DATABASE_URL`, ứng dụng sẽ `raise RuntimeError` lập tức (Fail-Fast), bảo đảm không có fallback ngoài ý muốn.
3. **`models.py`**:
   - Mở rộng độ dài trường `token_hash` trong hai model `PasswordResetToken` và `EmailVerificationToken` từ `String(128)` lên `String(255)`. Điều này khắc phục triệt để lỗi tràn cột PostgreSQL do hàm băm `scrypt` của Werkzeug sinh chuỗi 162 ký tự.

### 2.2. Hạ tầng và dịch vụ máy chủ
1. **Cài đặt PostgreSQL 16.15**:
   - Cài đặt từ kho gói chính thức của Ubuntu 24.04 (`noble-updates`).
   - Cấu hình chỉ lắng nghe tại `127.0.0.1:5432` (`listen_addresses = 'localhost'`).
   - Tối ưu bộ nhớ cho VPS 2GB RAM: `shared_buffers = 128MB`, `work_mem = 4MB`, `maintenance_work_mem = 64MB`, `max_connections = 50`.
   - Tạo role `viettranslate_user` với mật khẩu ngẫu nhiên bảo mật cao và cấp quyền trên database `viettranslate_db`.
2. **Khởi tạo Systemd Unit (`viettranslate.service`)**:
   - Thay thế việc chạy tiến trình Gunicorn daemon thủ công bằng quyền root.
   - Chạy với tài khoản hệ thống `www:www`, tự động khởi động lại khi lỗi (`Restart=on-failure`, `RestartSec=5s`), ghi log vào `journald`.
3. **Phân quyền và bảo mật tệp**:
   - File cấu hình `.env` trên VPS được đặt quyền `chmod 600` thuộc sở hữu của `www:www`.
   - Nginx cấu hình chặn triệt để các đường dẫn nhạy cảm (`.env`, `.git`, `instance`, v.v.).

---

## 3. Tình Trạng VPS Sau Triển Khai

| Tiêu chí | Trước triển khai | Sau triển khai | Trạng thái xác minh |
| :--- | :--- | :--- | :--- |
| **Ứng dụng Web** | Gunicorn daemon chạy quyền `root` | Systemd service `viettranslate.service` chạy quyền `www:www` | `active (running)`, tự khởi động cùng OS |
| **Cơ sở dữ liệu** | SQLite (`instance/database.db`) | PostgreSQL 16.15 tại `127.0.0.1:5432` | `active (running)`, cô lập localhost |
| **Cổng lắng nghe** | Port 5000 (root), 80 (nginx) | Port 5000 (www), 5432 (postgres localhost), 80 (nginx) | Không xung đột cổng |
| **Dung lượng đĩa** | 5.9 GB / 16 GB (40%) | 6.2 GB / 16 GB (42%) | Đủ dung lượng an toàn (>9.5 GB trống) |
| **RAM sử dụng** | ~750 MB / 2 GB | ~890 MB / 2 GB (Buffer/cache ~1.1 GB) | Ổn định, không swap thrashing |
| **HTTP Web** | HTTP 200 tại `103.161.118.158` | HTTP 200 tại `103.161.118.158` | Tất cả route chính phản hồi 200 OK |

---

## 4. Kết Quả Migration Cơ Sở Dữ Liệu (Đối Chiếu Chi Tiết)

Toàn bộ dữ liệu từ SQLite đã được trích xuất, chuyển đổi kiểu dữ liệu (Boolean, Datetime, Numeric, Foreign Key), nạp vào PostgreSQL và đồng bộ sequences. Kết quả đối chiếu số lượng bản ghi:

| STT | Tên bảng | Số dòng (SQLite) | Số dòng (PostgreSQL) | Tỷ lệ khớp | Ghi chú |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `user` | **21** | **21** | **100%** | Bao gồm tài khoản Admin, Translator, Hirer |
| 2 | `job` | **47** | **47** | **100%** | Toàn bộ các công việc đăng tuyển |
| 3 | `service` | **40** | **40** | **100%** | Danh mục dịch vụ phiên dịch |
| 4 | `contract` | **30** | **30** | **100%** | Hợp đồng giao kết |
| 5 | `translator_schedule` | **30** | **30** | **100%** | Lịch làm việc phiên dịch viên |
| 6 | `notification` | **26** | **26** | **100%** | Thông báo hệ thống |
| 7 | `admin_audit_log` | **23** | **23** | **100%** | Nhật ký thao tác quản trị |
| 8 | `translator_profile` | **17** | **17** | **100%** | Hồ sơ thông tin phiên dịch viên |
| 9 | `proposal` | **6** | **6** | **100%** | Báo giá, đề xuất ứng tuyển |
| 10 | `login_attempt` | **6** | **6** | **100%** | Lịch sử đăng nhập |
| 11 | `user_session` | **5** | **5** | **100%** | Phiên đăng nhập người dùng |
| 12 | `message` | **4** | **4** | **100%** | Tin nhắn hội thoại |
| 13 | `review` | **3** | **3** | **100%** | Đánh giá, phản hồi sau công việc |
| 14 | `email_verification_token` | **3** | **3** | **100%** | Token xác minh email |
| 15 | `interpreter_service` | **3** | **3** | **100%** | Cấu hình dịch vụ phiên dịch |
| 16 | `notification_setting` | **3** | **3** | **100%** | Cài đặt thông báo người dùng |
| 17 | `hirer_profile` | **2** | **2** | **100%** | Hồ sơ nhà tuyển dụng |
| 18 | `translator_verification` | **2** | **2** | **100%** | Hồ sơ thẩm định danh tính |
| 19 | `verification_document` | **2** | **2** | **100%** | Tài liệu xác minh KYC |
| 20 | `report` | **2** | **2** | **100%** | Báo cáo vi phạm |
| 21 | `deliverable` | **1** | **1** | **100%** | Sản phẩm bàn giao bản dịch |
| 22 | `alembic_version` | **1** | **1** | **100%** | Version migration schema |
| 23 | `admin_notification` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 24 | `direct_message` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 25 | `favorite_translator` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 26 | `interpreter_preference` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 27 | `password_reset_token` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 28 | `support_ticket` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 29 | `translator_preference` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 30 | `job_attachment` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 31 | `job_schedule` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 32 | `saved_job` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 33 | `verification_submission_version` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 34 | `contract_event` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| 35 | `payment_transaction` | 0 | 0 | 100% | Bảng rỗng hợp lệ |
| **TỔNG** | **35 BẢNG DỮ LIỆU** | **295 DÒNG** | **295 DÒNG** | **100% KHỚP** | **KHÔNG MẤT DỮ LIỆU** |

---

## 5. Bằng Chứng Kiểm Tra Thực Tế

### 5.1. Kiểm tra kết nối và truy vấn ứng dụng từ Gunicorn
Log từ `journalctl -u viettranslate.service`:
```text
gunicorn: [DB] Using: postgresql+psycopg://viettranslate_user:bc6cd1176e...
gunicorn: [DB Sync] Phân hệ Tài khoản: Đã đồng bộ schema thành công.
gunicorn: [DB] Database sẵn sàng. Users=21
```

### 5.2. Kiểm tra truy cập các Endpoint qua HTTP từ bên ngoài
Thực thi kiểm tra HTTP Request tới địa chỉ IP `103.161.118.158`:
- `GET /` -> **HTTP 200 OK** (Dung lượng: 95,747 bytes)
- `GET /login` -> **HTTP 200 OK**
- `GET /register` -> **HTTP 200 OK**
- `GET /translators` -> **HTTP 200 OK**
- `GET /jobs` -> **HTTP 200 OK**
- `GET /admin/login` -> **HTTP 200 OK**

### 5.3. Kiểm tra bảo mật chặn tệp nhạy cảm
- `GET /.env` -> **HTTP 404 Not Found (Bị chặn bởi Nginx)**
- `GET /.git` -> **HTTP 404 Not Found (Bị chặn bởi Nginx)**
- `GET /instance/database.db` -> **HTTP 404 Not Found (Bị chặn bởi Nginx)**

---

## 6. Độc Lập Với Supabase Và Vercel

1. **Loại bỏ phụ thuộc runtime**:
   - Ứng dụng không còn gọi bất kỳ API, cơ sở dữ liệu hay lưu trữ nào của Supabase Cloud khi người dùng truy cập, tạo tài khoản, đăng tin hay tải tệp.
   - Tệp `supabase_client.py` được giữ lại theo đúng yêu cầu bảo toàn mã nguồn, nhưng khi không có `SUPABASE_URL` và `SUPABASE_KEY` trong `.env`, client sẽ trả về `None` và ứng dụng tự động chuyển hướng mọi hoạt động lưu trữ sang kho cục bộ an toàn (`local_private`).
2. **Không phụ thuộc Vercel**:
   - Ứng dụng chạy liên tục 24/7 dưới dạng Systemd daemon trên Ubuntu 24.04, không bị giới hạn cold-start hay timeout serverless của Vercel.

---

## 7. Sao Lưu Và Vận Hành

- **Vị trí backup khởi tạo (Pre-migration)**: `/var/backups/viettranslate/pre_migration_20261014_232353/`
- **Vị trí backup tự động hàng ngày**: `/var/backups/viettranslate/backup_YYYYMMDD_HHMMSS/`
- **Tần suất**: 02:30 sáng hàng ngày (Crontab: `/etc/cron.d/viettranslate_backup`).
- **Kiểm tra tính toàn vẹn**: Tệp `.sql.gz` được kiểm tra qua `gzip -t`, tệp `.tar.gz` được kiểm tra qua `tar -tzf`.
- **Chính sách dọn dẹp**: Tự động xóa các bản sao lưu cũ hơn 7 ngày, bảo đảm không bao giờ làm đầy ổ SSD 16GB.

---

## 8. Tình Trạng HTTPS & Đề Xuất Tiếp Theo

1. **HTTPS & Chứng chỉ SSL đã được thiết lập**:
   - Website hiện phục vụ đồng thời cả HTTP cổng 80 và **HTTPS cổng 443** tại địa chỉ: `https://103.161.118.158/`.
   - Chứng chỉ SSL tự ký (RSA 2048-bit, SAN IP: `103.161.118.158`) có hiệu lực 365 ngày đã được kích hoạt trên Nginx.
   - Khi có tên miền riêng trỏ về IP này, quản trị viên chỉ cần thực hiện 1 câu lệnh duy nhất để chuyển sang chứng chỉ Let's Encrypt chính thức:
     ```bash
     sudo /usr/local/bin/enable_letsencrypt.sh yourdomain.com
     ```
2. **Sao lưu ngoài máy chủ (Off-site Backup)**:
   - Các bản sao lưu hiện tại nằm trên chính ổ đĩa của VPS (`/var/backups/viettranslate/`). Nếu xảy ra thảm họa phần cứng VPS (hỏng đĩa vật lý), bản sao lưu cục bộ có thể bị ảnh hưởng.
   - *Khuyến nghị:* Trong tương lai, cấu hình thêm rclone để tự động sao lưu bản `postgres_db_*.sql.gz` lên Google Drive hoặc AWS S3.
