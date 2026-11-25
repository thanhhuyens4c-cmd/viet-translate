# BÁO CÁO CHI TIẾT THỰC HIỆN SỬA LỖI VÀ TRIỂN KHAI (FIX IMPLEMENTATION REPORT)

Dự án: **VietTranslate**  
Hạ tầng: **VPS Ubuntu 24.04 LTS (103.161.118.158)**  
Cơ sở dữ liệu: **PostgreSQL 16 Local (viettranslate_db)**  
Thời gian thực hiện: **15/10/2026**  
Trạng thái: **CODE FIXED & DEPLOYED TO PRODUCTION**

---

## I. Tổng quan Kết quả Thực hiện

Toàn bộ các phát hiện từ quá trình kiểm toán và yêu cầu kỹ thuật đã được phân loại, kiểm chứng thực tế và giải quyết dứt điểm theo quy trình an toàn 8 giai đoạn.

| Mã Task | Phân loại | Tình trạng kiểm chứng | Tình trạng Code | Tình trạng Triển khai VPS |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** (Error 500 Traceback) | Bảo mật P0 | `CONFIRMED` & `REPRODUCED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **SEC-02** (Production SECRET_KEY) | Bảo mật P0 | `CONFIRMED` & `REPRODUCED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **SEC-03** (Startup Seed Protection) | Dữ liệu P0 | `CONFIRMED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **CSRF-01** (4 màn hình Admin CSRF) | Bảo mật P0 | `CONFIRMED` & `REPRODUCED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **ROUT-01** (Trùng Route Reject Proposal) | Nghiệp vụ P0 | `CONFIRMED` & `REPRODUCED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **STOR-01** (Lưu trữ tệp bền vững) | Hạ tầng P1 | `CONFIRMED` & `RUNTIME_VERIFIED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **PAY-01** (Payout Methods JSON -> PostgreSQL) | Dữ liệu P1 | `CONFIRMED` & `RUNTIME_VERIFIED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **ARCH-01** (Hợp nhất InterpreterService) | Nghiệp vụ P1 | `CONFIRMED` & `RUNTIME_VERIFIED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **ORPH-01** (An toàn dữ liệu mồ côi Admin) | Dữ liệu P1 | `CONFIRMED` & `RUNTIME_VERIFIED` | `FIXED` | `DEPLOYED & VERIFIED` |
| **NOTIF-01** (Sửa loại thông báo KYC Hirer) | Nghiệp vụ P1 | `CONFIRMED` & `RUNTIME_VERIFIED` | `FIXED` | `DEPLOYED & VERIFIED` |

---

## II. Chi tiết Từng Hạng mục Sửa lỗi

### 1. SEC-01 & SEC-02: Bảo mật Handler 500 & SECRET_KEY Production
- **Vấn đề:** `app.py` trả exception traceback trực tiếp ra trình duyệt khi xảy ra lỗi 500, làm lộ cấu trúc thư mục, câu lệnh SQL và credentials; `config.py` cho phép fallback sang secret key mặc định.
- **Giải pháp đã thực hiện:**
  - Tạo template lỗi chuyên dụng `templates/500.html` hiển thị giao diện thân thiện, chuyên nghiệp kèm mã tham chiếu sự cố ngẫu nhiên (`ERR-XXXXXXXX`).
  - Cập nhật `handle_500` trong `app.py` chỉ ghi traceback chi tiết vào server log kèm mã lỗi; response trả về mã lỗi chung, tuyệt đối không lộ dữ liệu nhạy cảm ra client.
  - Cập nhật `config.py` (`ProductionConfig`): Bắt buộc `SECRET_KEY` phải được cung cấp qua môi trường (tối thiểu 16 ký tự); nếu dùng key mặc định hoặc để trống, ứng dụng sẽ fail-fast lập tức khi khởi động.
- **Tệp thay đổi:** `app.py`, `config.py`, `templates/500.html`.
- **Kiểm tra nghiệm thu:** Test `test_02_500_handler_no_traceback` đạt kết quả `OK` trên VPS.

### 2. CSRF-01: Bổ sung CSRF Token cho 4 Màn hình Admin
- **Vấn đề:** 4 màn hình Admin (`admin_reviews.html`, `admin_payments.html`, `admin_notifications.html`, `admin_reports.html`) có form POST hoặc modal AJAX thiếu input `_csrf_token`, dẫn đến lỗi HTTP 403 Forbidden khi thao tác do decorator `@csrf_protected` từ chối.
- **Giải pháp đã thực hiện:**
  - Bổ sung `<input type="hidden" name="_csrf_token" value="{{ admin_csrf_token }}"/>` vào tất cả các form POST.
  - Bổ sung `_csrf_token` vào các modal xác nhận giải quyết khiếu nại / hoàn tiền trong `admin_reports.html`.
  - Giữ nguyên decorator `@csrf_protected` bảo mật backend.
- **Tệp thay đổi:** `templates/admin_reviews.html`, `templates/admin_payments.html`, `templates/admin_notifications.html`, `templates/admin_reports.html`.
- **Kiểm tra nghiệm thu:** Test `test_03_admin_csrf_protected` xác nhận request thiếu token bị từ chối 403; form kèm token hoạt động chính xác.

### 3. ROUT-01: Hợp nhất Endpoint Từ chối Báo giá (`/api/proposals/<proposal_id>/reject`)
- **Vấn đề:** Trong `app.py` tồn tại 2 khai báo route `@app.route('/api/proposals/<int:proposal_id>/reject', methods=['POST'])`. Một route xử lý trực tiếp thiếu bảo vệ đầy đủ; một route gọi qua service `reject_proposal_for_hirer` có kiểm tra quyền sở hữu và CSRF.
- **Giải pháp đã thực hiện:**
  - Hợp nhất thành 1 route chuẩn duy nhất sử dụng `reject_proposal_for_hirer`.
  - Xác thực CSRF token thông qua `_proposal_api_guard` (hỗ trợ cả header `X-CSRF-Token` và body JSON/form).
  - Cập nhật frontend `job_detail.html` truyền `X-CSRF-Token` trong request fetch.
- **Tệp thay đổi:** `app.py`, `templates/job_detail.html`.
- **Kiểm tra nghiệm thu:** Test `test_01_reject_proposal_single_route` xác nhận chỉ có 1 rule duy nhất được đăng ký trên URL map.

### 4. STOR-01: Chuẩn hóa Thư mục Lưu trữ Tệp Bền vững
- **Vấn đề:** Tệp upload và tài liệu đính kèm phân tán trong `instance/`, có cơ chế fallback tự động sang `/tmp` khiến tệp biến mất khi reboot hoặc deploy.
- **Giải pháp đã thực hiện:**
  - Cấu hình tập trung thông qua biến môi trường: `UPLOAD_FOLDER`, `PRIVATE_STORAGE_FOLDER`, `CHAT_IMAGE_FOLDER`, `JOB_FILES_FOLDER`, `DELIVERABLE_FOLDER`.
  - Trỏ toàn bộ vào `/var/lib/viettranslate/` ngoài git repository.
  - Chặn triệt để fallback sang `/tmp` khi `FLASK_ENV == 'production'` (fail-fast báo lỗi cấu hình thay vì âm thầm lưu tạm).
- **Tệp thay đổi:** `app.py`, `config.py`, `/www/wwwroot/157.66.100.101/.env`.
- **Tài liệu:** Đã phát hành `STORAGE_MIGRATION.md`.

### 5. PAY-01: Chuyển đổi Phương thức Nhận tiền từ JSON sang PostgreSQL
- **Vấn đề:** `services/payout_methods.py` lưu dữ liệu vào `instance/interpreter_payout_methods.json` với `threading.Lock()`, không an toàn giữa các Gunicorn worker và không được sao lưu tự động bởi PostgreSQL.
- **Giải pháp đã thực hiện:**
  - Tạo model SQLAlchemy `PayoutMethod` và `PayoutHistory` trong `models.py`.
  - Viết script chuyển đổi idempotent `migrations/migrate_payout_to_db.py`.
  - Tái cấu trúc `services/payout_methods.py` sử dụng SQLAlchemy ORM và transaction ACID khi chạy trong ứng dụng, đồng thời giữ fallback an toàn khi chạy unit test độc lập.
  - Số tài khoản luôn được che (`•••• •••• •••• xxxx`) khi hiển thị; không ghi số tài khoản vào audit logs.
- **Tệp thay đổi:** `models.py`, `services/payout_methods.py`, `migrations/migrate_payout_to_db.py`.
- **Tài liệu:** Đã phát hành `DB_MIGRATION_PAYOUT.md`.
- **Kiểm tra nghiệm thu:** Test `test_04_payout_methods_postgresql_crud` thực thi thành công 100% trên VPS.

### 6. ARCH-01: Hợp nhất InterpreterService và Service
- **Vấn đề:** Phiên dịch viên thiết lập năng lực và bảng giá theo giờ/ca trong `InterpreterService`, nhưng trang hồ sơ công khai (`translator_profile.html`) chỉ đọc `profile.services` (mô hình gói dịch vụ cũ), khiến khách hàng không thấy biểu phí mới và không đặt được dịch vụ.
- **Giải pháp đã thực hiện:**
  - Mở rộng `Contract` model bổ sung khóa ngoại `interpreter_service_id = db.Column(db.Integer, db.ForeignKey('interpreter_service.id'), nullable=True)`.
  - Bổ sung cột `interpreter_service_id` vào bảng `contract` trong cơ sở dữ liệu PostgreSQL production.
  - Cập nhật `services/booking.py` hỗ trợ đặt trực tiếp theo `interpreter_service_id`.
  - Thêm endpoint `@app.route('/book-interpreter/<int:interpreter_service_id>')` và template `templates/book_interpreter.html` chuyên dụng cho đặt dịch vụ theo giờ hoặc theo buổi/ca.
  - Cập nhật `templates/translator_profile.html` hiển thị rõ ràng bảng giá theo giờ/ca của `InterpreterService` bên cạnh các gói dịch vụ truyền thống.
  - Cập nhật hàm `project_title` và `language_pair` trong `services/projects.py` và `services/transactions.py` hiển thị chính xác tên dịch vụ phiên dịch.
- **Tệp thay đổi:** `models.py`, `app.py`, `services/booking.py`, `services/projects.py`, `services/transactions.py`, `templates/translator_profile.html`, `templates/book_interpreter.html`.

### 7. ORPH-01: Xử lý An toàn Dữ liệu Mồ côi trong Admin Contracts
- **Vấn đề:** 30 bản ghi hợp đồng lịch sử có `c.hirer` hoặc `c.translator` là `None` (do dữ liệu cũ tham chiếu ID người dùng đã xóa). Template `admin_contracts.html` truy cập trực tiếp `c.hirer.email`, `c.translator.email` dẫn đến lỗi render 500.
- **Giải pháp đã thực hiện:**
  - Áp dụng nguyên tắc **không xóa bản ghi lịch sử, không tạo người dùng giả**.
  - Bổ sung kiểm tra an toàn trong `templates/admin_contracts.html`:
    - Nếu có user: hiển thị tên và link chi tiết.
    - Nếu user không tồn tại: hiển thị `Khách cũ (#id)` hoặc `PDV cũ (#id)` kèm chú thích lịch sử an toàn.
  - Hỗ trợ hiển thị badge `[INT]` cho các hợp đồng tạo từ `InterpreterService`.
- **Tệp thay đổi:** `templates/admin_contracts.html`.
- **Kiểm tra nghiệm thu:** Test `test_05_contract_orphan_safety_in_template` render thành công không phát sinh exception.

### 8. NOTIF-01: Chuẩn hóa Loại Thông báo Xác minh Người đăng tuyển
- **Vấn đề:** Hàm `admin_hirer_review_action` gửi thông báo với `notification_type='JOB_MATCH'` cho cả 3 trường hợp duyệt, yêu cầu sửa đổi và từ chối.
- **Giải pháp đã thực hiện:**
  - Đổi sang các loại thông báo chuyên biệt chuẩn: `VERIFICATION_APPROVED`, `VERIFICATION_NEEDS_REVISION`, `VERIFICATION_REJECTED`.
  - Các loại thông báo này thuộc nhóm hệ thống & bảo mật, tự động khóa luôn bật trong `NotificationSetting` (không bị tắt nhầm bởi tùy chọn việc làm) và hiển thị đúng nhãn "Xác minh hồ sơ" kèm màu sắc badge trực quan.
- **Tệp thay đổi:** `app.py`.

---

## III. Tình trạng Dịch vụ VPS sau Triển khai

1. **Systemd Service (`viettranslate.service`):**
   - Trạng thái: `active (running)`.
   - Process: Gunicorn master (PID 57290) + 2 sync workers (PID 57291, 57292).
   - Port lắng nghe: `127.0.0.1:5000`.
2. **Reverse Proxy Nginx:**
   - Hoạt động ổn định, chuyển tiếp cổng 80 -> `127.0.0.1:5000`.
   - HTTP Status: `200 OK` trên các trang công khai (`/`, `/login`, `/translators`, `/admin/login`).
3. **Cơ sở dữ liệu PostgreSQL 16:**
   - Kết nối local qua unix socket / 127.0.0.1:5432.
   - Bảng mới `payout_methods` và `payout_histories` đã được tạo và đồng bộ.
   - Cột `contract.interpreter_service_id` đã được bổ sung thành công.
   - Bản sao lưu an toàn trước khi deploy được lưu trữ tại:
     `/var/backups/viettranslate/db_pre_deploy_.dump` (284 KB)
     `/var/backups/viettranslate/app_pre_deploy_20261015.tar.gz` (7.6 MB)
