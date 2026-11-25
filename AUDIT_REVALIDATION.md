# BÁO CÁO TÁI XÁC MINH KIỂM TOÁN (AUDIT REVALIDATION REPORT)
**Dự án:** VietTranslate  
**Thời điểm thực hiện:** 15/10/2026  
**Môi trường xác minh:** Local Workspace & VPS Ubuntu 24.04 LTS (`103.161.118.158`)  
**Cơ sở dữ liệu:** PostgreSQL 16 (`viettranslate_db`)  

---

## 1. BẢNG TỔNG HỢP PHÂN LOẠI PHÁT HIỆN

| ID | Phát hiện | Phân loại | Mức độ | Vị trí Code / Schema | Tác động nghiệp vụ |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **SEC-01** | Lộ Traceback, truy vấn và exception trên trang lỗi 500 | `CONFIRMED`<br>`REPRODUCED` | **P0** | `app.py:1216-1220` (`handle_500`) | Rò rỉ thông tin hạ tầng, đường dẫn file và cấu trúc cơ sở dữ liệu khi có exception. |
| **SEC-02** | Khởi động ứng dụng tự động chạy schema repair và nạp dữ liệu mẫu (Seed Data) | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P0** | `app.py:1109-1206` (`_init_db`, `seed_data.py`) | Khi kết nối DB mới, production có thể tự tạo tài khoản mẫu (`admin@vt.com / admin123`), gây rủi ro an ninh nghiêm trọng. |
| **SEC-03** | `SECRET_KEY` dự phòng dùng giá trị mặc định không an toàn | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P0** | `config.py:9` (`Config.SECRET_KEY`) | Nếu thiếu biến môi trường, production âm thầm dùng key dev làm suy yếu cookie session và CSRF token. |
| **SEC-04** | 4 Màn hình Admin thiếu `_csrf_token` dẫn đến lỗi 403 Forbidden | `CONFIRMED`<br>`REPRODUCED` | **P0** | `templates/admin_reviews.html:78`<br>`templates/admin_payments.html:81`<br>`templates/admin_notifications.html:71,76`<br>`templates/admin_reports.html:86,91,96` | Admin không thể ẩn/khôi phục đánh giá, không thể refund, không thể đánh dấu đã đọc thông báo, không thể xử lý báo cáo. |
| **FLOW-01**| Trùng lặp hai khai báo route POST `/api/proposals/<id>/reject` | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P0** | `app.py:8311` (`api_hirer_reject_proposal`)<br>`app.py:9231` (`api_reject_proposal`) | Xung đột định tuyến Flask; route 8311 shadow route 9231; bỏ qua guard bảo mật và logic `services.proposals`. |
| **STOR-01**| Đường dẫn lưu trữ phân tán, tệp đính kèm hardcode `instance/` | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P1** | `app.py:7190` (`CHAT_IMAGE_FOLDER`)<br>`app.py:7475` (`JOB_FILES_FOLDER`)<br>`app.py:7484` (`DELIVERABLE_FOLDER`) | Tệp bàn giao, file đính kèm tuyển dụng và ảnh chat nằm trong thư mục git repo, dễ bị mất khi deploy/git clean. |
| **PAY-01** | Phương thức nhận tiền (Payout Methods) lưu trong tệp JSON nội bộ | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P1** | `services/payout_methods.py:41-43` (`instance/interpreter_payout_methods.json`) | Không đồng bộ giữa các worker Gunicorn, không được backup bởi PostgreSQL `pg_dump`, rủi ro mất mát dữ liệu tài chính. |
| **ARCH-01**| Bảng giá `InterpreterService` không đồng nhất với luồng hiển thị và đặt dịch vụ `Service` | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P1** | `models.py:548` (`Service`) vs `models.py:1965` (`InterpreterService`)<br>`templates/translator_profile.html:598`<br>`app.py:7397` (`book_service`) | Phiên dịch viên cấu hình biểu phí mới tại Profile tab Services nhưng khách xem hồ sơ công khai không thấy và không đặt được. |
| **DATA-01**| 46 Job và 30 Contract mồ côi (tham chiếu User ID 2..74 đã bị xóa trước đó) | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P1** | PostgreSQL `job`, `contract`, `proposal`<br>`templates/admin_contracts.html:67-75` | Màn hình Admin Contracts hiển thị khoảng trống trắng và tạo link rỗng `href="/admin/users?search="`. |
| **NOTIF-01**| Sử dụng sai `notification_type='JOB_MATCH'` cho kiểm duyệt hồ sơ người đăng tuyển | `CONFIRMED`<br>`RUNTIME_VERIFIED` | **P1** | `app.py:10410, 10434, 10458` (`admin_hirer_review_action`) | Chuông thông báo hiển thị sai danh mục "Việc làm phù hợp" thay vì "Xác minh tài khoản". |

---

## 2. CHI TIẾT TỪNG PHÁT HIỆN VÀ PHƯƠNG ÁN XÁC MINH / KHẮC PHỤC

### SEC-01: Lộ Traceback trên trang lỗi 500
* **Hiện trạng xác minh (`CONFIRMED`):** Tại `app.py` dòng 1216-1220:
  ```python
  @app.errorhandler(500)
  def handle_500(e):
      import traceback
      tb = traceback.format_exc()
      return f"<pre>500 Error:\n{e}\n\nTraceback:\n{tb}</pre>", 500
  ```
* **Rủi ro:** Khi xảy ra lỗi máy chủ, toàn bộ stack trace chứa đường dẫn thư mục `/www/wwwroot/...`, cấu trúc truy vấn SQL và chi tiết biến nội bộ bị phơi bày trực tiếp ra trình duyệt.
* **Cách sửa:**
  - Kiểm tra `FLASK_ENV`. Nếu `production`, render trang thông báo lỗi 500 thân thiện (hoặc JSON nếu request AJAX/API), kèm `request_id` để tra cứu log.
  - Ghi toàn bộ traceback vào server log (`logger.error`) với mã định danh lỗi, không in thông tin nhạy cảm.
* **Cách xác minh sau sửa:** Gọi route thử nghiệm sinh exception; kiểm tra HTTP response không chứa chữ "Traceback" hay đường dẫn file; kiểm tra log server có mã lỗi tương ứng.

---

### SEC-02: Khởi động ứng dụng tự động chạy schema repair và nạp dữ liệu mẫu
* **Hiện trạng xác minh (`CONFIRMED`):** Tại `app.py` dòng 1109-1206:
  - `_init_db()` chạy `db.create_all()` và chuỗi truy vấn `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
  - Dòng 1184 kiểm tra `if user_count == 0:` và tự động gọi `seed_data()` tạo hàng loạt tài khoản mẫu (bao gồm tài khoản quản trị `admin@vt.com` mật khẩu `admin123`).
* **Rủi ro:** Production có thể bị nạp tài khoản demo ngoài ý muốn nếu kết nối cơ sở dữ liệu mới; các Gunicorn workers khởi động đồng thời chạy ALTER TABLE có thể gây lock bảng.
* **Cách sửa:**
  - Tách hoàn toàn seed data ra khỏi startup; chỉ cho phép gọi qua lệnh CLI chủ động (`python seed_data.py`).
  - Bổ sung điều kiện chặn tuyệt đối: `if os.getenv('FLASK_ENV') == 'production': return` trước mọi lệnh seed.
  - Chuyển toàn bộ các lệnh ALTER TABLE sang các tệp migration SQL/Python có phiên bản rõ ràng.
* **Cách xác minh sau sửa:** Khởi động lại service `viettranslate.service` với database trống; xác minh app không tự nạp demo data.

---

### SEC-03: `SECRET_KEY` dự phòng dùng giá trị mặc định
* **Hiện trạng xác minh (`CONFIRMED`):** Tại `config.py` dòng 9: `SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')`. Lớp `ProductionConfig` không kiểm tra giá trị của key này.
* **Rủi ro:** Nếu file cấu hình thiếu `SECRET_KEY`, hệ thống sẽ sử dụng key mặc định công khai trên GitHub, cho phép kẻ tấn công giả mạo session cookie của bất kỳ người dùng nào.
* **Cách sửa:** Trong `ProductionConfig`, nếu `SECRET_KEY` bị thiếu hoặc bằng chuỗi placeholder `'dev-secret-key-change-in-production'`, ứng dụng lập tức `raise RuntimeError` (Fail-fast).
* **Cách xác minh sau sửa:** Chạy test với `FLASK_ENV=production` và không truyền `SECRET_KEY`; xác minh ứng dụng từ chối khởi động an toàn.

---

### SEC-04: Bốn màn hình Admin thiếu `_csrf_token`
* **Hiện trạng xác minh (`CONFIRMED`):**
  1. `templates/admin_reviews.html:78`: Form toggle ẩn/hiện đánh giá không có trường `_csrf_token`.
  2. `templates/admin_payments.html:81`: Form hoàn tiền `admin_refund_payment` không có `_csrf_token`.
  3. `templates/admin_notifications.html:71,76`: Cả form đọc một thông báo và đọc tất cả đều thiếu `_csrf_token`.
  4. `templates/admin_reports.html:86,91,96`: Nút điều tra và 2 modal xác nhận giải quyết/từ chối báo cáo thiếu `_csrf_token`.
* **Rủi ro:** Mọi thao tác này bị middleware `@csrf_protected` từ chối với lỗi **403 Forbidden** và ghi log `CSRF_VIOLATION`. Admin hoàn toàn bị liệt thao tác trên giao diện.
* **Cách sửa:**
  - Bổ sung `<input type="hidden" name="_csrf_token" value="{{ admin_csrf_token }}">` vào tất cả các form HTML POST.
  - Bổ sung header `X-CSRF-Token: {{ admin_csrf_token }}` cho mọi hàm `fetch()` AJAX trong modal.
* **Cách xác minh sau sửa:** Tái hiện gửi thiếu token -> 403; gửi token sai -> 403; gửi token đúng qua form và qua AJAX -> 200/302 thành công.

---

### FLOW-01: Trùng lặp 2 route POST `/api/proposals/<id>/reject`
* **Hiện trạng xác minh (`RUNTIME_VERIFIED`):**
  - Dòng 8311: `def api_hirer_reject_proposal(proposal_id)`: Nhận JSON, không kiểm tra CSRF.
  - Dòng 9231: `def api_reject_proposal(proposal_id)`: Kiểm tra `_proposal_api_guard()` (CSRF), gọi `services.proposals.reject_proposal_for_hirer`.
  - Kiểm tra `url_map` trên VPS cho thấy cả hai hàm cùng lắng nghe POST trên cùng một URL; hàm 8311 đè hàm 9231.
* **Cách sửa:** Hợp nhất thành 1 route chuẩn duy nhất:
  - Kiểm tra đăng nhập và quyền khách thuê sở hữu Job.
  - Hỗ trợ cả nhận JSON payload `{reason: ...}` và FormData `{note: ...}`.
  - Kiểm tra CSRF hợp lệ.
  - Cập nhật trạng thái proposal sang `rejected`, ghi `client_note`, gửi thông báo cho phiên dịch viên.
  - Trả về JSON contract thống nhất `{ok: True, message: ...}`.
* **Cách xác minh sau sửa:** Gửi request từ `job_detail.html` với đầy đủ quyền; kiểm tra proposal chuyển thành `rejected` và không có xung đột endpoint.

---

### STOR-01: Chuẩn hóa đường dẫn lưu trữ file trên VPS
* **Hiện trạng xác minh (`CONFIRMED`):**
  - `AVATAR_UPLOAD_FOLDER` và `PRIVATE_STORAGE_FOLDER` đã trỏ vào `/var/lib/viettranslate/`.
  - Nhưng dòng 7190, 7475, 7484 trong `app.py` lại hardcode `CHAT_IMAGE_FOLDER`, `JOB_FILES_FOLDER`, `DELIVERABLE_FOLDER` vào thư mục git `instance/`.
* **Cách sửa:**
  - Cập nhật `app.py` để lấy các thư mục này từ biến môi trường `os.getenv()`, với fallback mặc định an toàn.
  - Cập nhật file `.env` trên VPS để trỏ:
    * `JOB_FILES_FOLDER=/var/lib/viettranslate/private_storage/job_files`
    * `DELIVERABLE_FOLDER=/var/lib/viettranslate/private_storage/deliverables`
    * `CHAT_IMAGE_FOLDER=/var/lib/viettranslate/private_storage/chat_images`
  - Đảm bảo quyền sở hữu thư mục thuộc về user dịch vụ `www:www` (mode 750).
* **Cách xác minh sau sửa:** Tải file thử nghiệm; kiểm tra file được lưu đúng tại `/var/lib/viettranslate/` và tải về bình thường qua route bảo mật.

---

### PAY-01: Chuyển dữ liệu Payout Methods từ JSON sang PostgreSQL
* **Hiện trạng xác minh (`CONFIRMED`):** `services/payout_methods.py` sử dụng `instance/interpreter_payout_methods.json`.
* **Cách sửa:**
  - Tạo model `PayoutMethod` và `PayoutHistory` trong `models.py` với đầy đủ trường: `id` (UUID hoặc chuỗi tương thích), `user_id` (FK), `bank_code`, `account_number_encrypted`, `account_number_masked`, `account_holder_name`, `branch`, `is_default`, `created_at`, `updated_at`.
  - Viết migration script đọc file JSON (nếu có), nhập an toàn vào PostgreSQL qua transaction.
  - Tái cấu trúc các hàm trong `services/payout_methods.py` để thao tác trực tiếp với SQLAlchemy, bảo đảm ACID giữa các Gunicorn workers.
* **Cách xác minh sau sửa:** Thêm tài khoản ngân hàng mới; đổi tài khoản mặc định; xóa tài khoản; đối chiếu dữ liệu lưu trong PostgreSQL.

---

### ARCH-01: Hợp nhất luồng Bảng giá và Đặt dịch vụ
* **Hiện trạng xác minh (`RUNTIME_VERIFIED`):**
  - Model `InterpreterService` (bảng `interpreter_service`) lưu thù lao theo giờ (`hourly_rate`) và theo ca (`session_rate`).
  - Model `Service` (bảng `service`) lưu 3 gói basic/standard/premium.
  - Trang hồ sơ công khai `templates/translator_profile.html` duyệt `profile.services` (chỉ đọc `Service`), bỏ qua hoàn toàn `InterpreterService`.
* **Cách sửa:**
  - Trong `templates/translator_profile.html`: Bổ sung khối hiển thị chuyên biệt cho Bảng giá Phiên dịch viên (`profile.user.interpreter_services`), hiển thị rõ ràng ngôn ngữ nguồn, đích, hình thức (Cabin, Nối tiếp, Tháp tùng, Online) và mức thù lao VND/giờ, VND/ca.
  - Nâng cấp route `/book/<service_id>` và `services/booking.py` để hỗ trợ nhận diện cả `service_id` (gói dịch vụ cũ) lẫn `interpreter_service_id` (bảng giá mới), tạo Hợp đồng tương thích bảo toàn cả hai luồng.
* **Cách xác minh sau sửa:** Tạo dịch vụ mới tại `/account/profile?tab=services`; vào trang công khai `/translator/<id>` kiểm tra dịch vụ hiển thị chính xác; bấm Đặt dịch vụ và hoàn tất tạo hợp đồng.

---

### DATA-01: Xử lý an toàn bản ghi mồ côi (Orphans)
* **Hiện trạng xác minh (`RUNTIME_VERIFIED`):** Quét PostgreSQL trên VPS cho thấy có 46 Job và 30 Contract tham chiếu tới các User ID cũ không còn tồn tại trong bảng `user`.
* **Cách sửa:**
  - Tuyệt đối không xóa dữ liệu lịch sử hay tạo user giả.
  - Trong `templates/admin_contracts.html` (dòng 67-75) và các template liên quan: Bổ sung guard check `{% raw %}{% if c.hirer %}{{ c.hirer.name }}{% else %}<span class="text-slate-500 italic">Khách cũ (#{{ c.hirer_id }})</span>{% endif %}{% endraw %}` để ngăn chặn thẻ `<a>` rỗng và khoảng trống trắng trên giao diện.
* **Cách xác minh sau sửa:** Truy cập `/admin/contracts`; toàn bộ 30 hợp đồng lịch sử hiển thị rõ ràng tên khách hoặc nhãn định danh người dùng cũ, không gây lỗi giao diện.

---

### NOTIF-01: Sửa loại thông báo kiểm duyệt người đăng tuyển
* **Hiện trạng xác minh (`CONFIRMED`):** Tại `app.py` dòng 10410, 10434, 10458: Dùng `notification_type='JOB_MATCH'`.
* **Cách sửa:** Thay thế bằng:
  - Khi phê duyệt: `notification_type='VERIFICATION_APPROVED'`
  - Khi yêu cầu bổ sung: `notification_type='VERIFICATION_NEEDS_REVISION'`
  - Khi từ chối: `notification_type='VERIFICATION_REJECTED'`
* **Cách xác minh sau sửa:** Duyệt hồ sơ Hirer từ Admin; kiểm tra thông báo nhận được mang đúng biểu tượng và danh mục xác minh tài khoản.
