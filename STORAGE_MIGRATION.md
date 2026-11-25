# BÁO CÁO CHUẨN HÓA VÀ LƯU TRỮ TỆP BỀN VỮNG (STORAGE MIGRATION)

## 1. Mục tiêu và Lý do Chuyển đổi
Trước khi thực hiện chuẩn hóa, ứng dụng `VietTranslate` phân tán các thư mục upload và tệp đính kèm ở nhiều vị trí trong mã nguồn (đặc biệt là thư mục `instance/`), kèm theo fallback tự động sang `/tmp`:
- Khi ứng dụng khởi động lại hoặc khi deploy code mới qua `git clean` / `rsync`, các tệp đính kèm người dùng tải lên có nguy cơ bị ghi đè hoặc thất lạc.
- Việc fallback ngầm sang `/tmp` khiến người dùng tưởng upload thành công nhưng thực tế tệp sẽ biến mất sau khi máy chủ reboot hoặc dọn dẹp bộ nhớ tạm.

**Giải pháp:**
- Chuyển toàn bộ các tệp upload công khai và tệp nhạy cảm/riêng tư ra thư mục lưu trữ chuyên dụng ngoài mã nguồn: `/var/lib/viettranslate/`.
- Cấu hình tập trung thông qua biến môi trường trong file `.env`.
- Chặn triệt để cơ chế fallback `/tmp` khi `FLASK_ENV == 'production'` (fail-fast báo lỗi hệ thống cấu hình thay vì âm thầm lưu tạm).

---

## 2. Bảng Đối chiếu Đường dẫn Lưu trữ

| Hạng mục lưu trữ | Đường dẫn cũ (Legacy) | Đường dẫn mới chuẩn hóa (VPS) | Biến môi trường (.env) | Phân quyền Linux (chmod/chown) | Tính chất bảo mật |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ảnh đại diện & Upload chung** | `static/uploads/` | `/var/lib/viettranslate/uploads/` | `UPLOAD_FOLDER` | `www:www` (0755) | Công khai có kiểm soát (Nginx/Flask) |
| **Xác minh KYC & Giấy tờ** | `instance/storage/private_verifications` | `/var/lib/viettranslate/private_storage/private_verifications` | `PRIVATE_STORAGE_FOLDER` | `www:www` (0700) | **Private strictly** - Phải qua auth backend |
| **Hình ảnh Chat** | `instance/chat_images` | `/var/lib/viettranslate/private_storage/chat_images` | `CHAT_IMAGE_FOLDER` | `www:www` (0700) | **Private strictly** - Phải là người trong hội thoại |
| **Tệp đính kèm công việc** | `instance/job_files` | `/var/lib/viettranslate/private_storage/job_files` | `JOB_FILES_FOLDER` | `www:www` (0700) | **Private strictly** - Người đăng tuyển & Ứng viên |
| **Tệp bàn giao kết quả** | `instance/deliverables` | `/var/lib/viettranslate/private_storage/deliverables` | `DELIVERABLE_FOLDER` | `www:www` (0700) | **Private strictly** - Các bên trong Hợp đồng |

---

## 3. Cấu hình Môi trường Production (`.env` trên VPS)

Tệp `/www/wwwroot/157.66.100.101/.env` đã được cấu hình bổ sung đầy đủ:
```ini
UPLOAD_FOLDER=/var/lib/viettranslate/uploads
PRIVATE_STORAGE_FOLDER=/var/lib/viettranslate/private_storage/private_verifications
CHAT_IMAGE_FOLDER=/var/lib/viettranslate/private_storage/chat_images
JOB_FILES_FOLDER=/var/lib/viettranslate/private_storage/job_files
DELIVERABLE_FOLDER=/var/lib/viettranslate/private_storage/deliverables
```

---

## 4. Đối chiếu Dữ liệu Thực tế (Reconciliation)

Kiểm tra tại thời điểm thực hiện (15/10/2026):
1. **Thư mục cũ trong `instance/` trên VPS:**
   - `instance/chat_images`: 0 tệp.
   - `instance/deliverables`: 0 tệp.
   - `instance/job_files`: 0 tệp.
   - `instance/storage/private_verifications`: 0 tệp.
2. **Thư mục đích `/var/lib/viettranslate/`:**
   - Toàn bộ cây thư mục đã được khởi tạo bởi user `www:www`.
   - Phân quyền thư mục cha: `0750` cho `/var/lib/viettranslate`, `0700` cho toàn bộ nhánh con `private_storage/`.
   - Không có tệp tin mồ côi bị sót lại trong quá trình cutover.

---

## 5. Cơ chế Kiểm soát Truy cập & Bảo mật File

1. **Path Traversal Protection:** Tất cả các tên file được tạo ra bằng uuid / token hash hex hoặc `secure_filename()` trước khi lưu vào đĩa cứng.
2. **Backend Authentication:**
   - Endpoint `/chat-image/<path>` kiểm tra người yêu cầu phải là người gửi hoặc người nhận trong phòng chat.
   - Endpoint `/job/file/<id>` kiểm tra người tải phải là chủ Job hoặc phiên dịch viên đã nộp proposal.
   - Endpoint `/contract/deliverable/<id>` kiểm tra người tải phải là hirer hoặc interpreter của hợp đồng đó.
3. **Fail-Safe Startup:** Khi chạy ở chế độ production, nếu hệ thống không tạo hoặc không ghi được vào các thư mục cấu hình, ứng dụng sẽ `raise RuntimeError` lập tức kèm thông điệp cảnh báo, ngăn ngừa việc ghi dữ liệu vào `/tmp`.
