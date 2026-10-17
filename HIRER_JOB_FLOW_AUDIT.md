# HIRER_JOB_FLOW_AUDIT.md — Báo Cáo Audit Luồng Xác Minh Người Thuê & Kiểm Duyệt Job

## I. Tổng Quan & Mục Tiêu Audit
Tài liệu này ghi lại kết quả audit chi tiết, truy vết mã nguồn và kiểm chứng thực tế giữa hai quy trình nghiệp vụ:
1. **Xác minh người đăng tuyển (Hirer Verification)**
2. **Kiểm duyệt nội dung công việc (Job Moderation)**

Báo cáo tuân thủ nguyên tắc không suy đoán, đối chiếu trực tiếp giữa mã nguồn workspace và cơ sở dữ liệu VPS Production (Ubuntu 24.04 LTS, PostgreSQL Supabase / local VPS).

---

## II. Truy Vết Luồng Nghiệp Vụ Hiện Tại

### 1. Luồng Xác Minh Người Thuê (Hirer Verification)
- **UI / Giao diện:** Người dùng truy cập `/account/profile?tab=hirer_verify` (hoặc `hirer_profile`).
- **Xử lý Request:** Form POST gửi tới `/account/profile` với `action=hirer_profile`.
- **Backend Service:** Gọi `_apply_hirer_profile_form(user, profile, request.form, request.files)`.
- **Lỗ hổng phát hiện (CONFIRMED):**
  - Tại `app.py:844-850`, hàm tự động thực hiện:
    ```python
    if profile.verification_status not in ('rejected', 'revoked', 'suspended'):
        profile.is_verified = True
        profile.verification_status = 'verified'
        if not profile.verified_at:
            profile.verified_at = datetime.utcnow()
    ```
  - **Hậu quả:** Người dùng chỉ cần điền đủ các trường bắt buộc thì tài khoản **ngay lập tức được cấp trạng thái `verified`** mà không cần sự thẩm định hay phê duyệt của Admin.
  - Tại `app.py:3380-3395`, nhánh `else` tạo `AdminNotification(type='HIRER_VERIFICATION')` bị bỏ qua hoàn toàn do `profile.is_verified` đã bị gán thành `True`. Do đó Admin không hề nhận được thông báo có hồ sơ chờ duyệt.
  - Tại `app.py:10571`, hàng chờ `admin_hirers()` lọc `pending` dựa trên điều kiện tài khoản chưa verified, khiến người thuê tự xác minh biến mất khỏi tab "Chờ xác minh".

### 2. Luồng Kiểm Soát Quyền Đăng Job (Hirer Gate)
- **Hàm kiểm tra:** `can_hirer_post_job(user)` trong `services/hirer_verification.py`.
- **Lỗ hổng phát hiện (CONFIRMED):**
  - Logic cũ: `is_verified = bool(profile.is_verified or profile.verification_status == 'verified')`.
  - Nếu tài khoản có `profile.is_verified == True` nhưng trạng thái là `revoked` hoặc `rejected`, điều kiện `or` vẫn coi là hợp lệ.
  - Khi hồ sơ ở trạng thái `pending` hoặc `needs_revision`, thông báo trả về chung chung: *"Tài khoản của bạn chưa hoàn thành xác minh người đăng tuyển..."*, không giải thích rõ hồ sơ đang chờ Admin phê duyệt hay cần sửa đổi gì.

### 3. Luồng Đăng Yêu Cầu (POST /post-job)
- **Endpoint:** `POST /post-job` (app.py:7875-7942).
- **Quy trình:**
  1. Kiểm tra session, đăng nhập, role `'hirer'`.
  2. Kiểm tra `can_hirer_post_job(user)`. Nếu không đủ điều kiện -> redirect sang trang hồ sơ kèm thông báo flash.
  3. Kiểm tra form token chống double submit (`session['job_form_tokens']`).
  4. Kiểm tra CSRF qua `_csrf_ok()`.
  5. Validation dữ liệu form (`validate_job_form`) và file đính kèm (`validate_job_files`).
  6. Persistence: Tạo `Job`, flush lấy `job.id`, lưu `JobSchedule`, gọi `_submit_for_moderation`, lưu file đính kèm `JobAttachment`, commit transaction.
- **Rủi ro phát hiện (CONFIRMED):**
  - Trong `_submit_for_moderation(job, user, is_new)`: hàm gọi `evaluate_job_39_criteria(job)`. Trước đây nếu hàm đánh giá tiêu chí hoặc tạo `AdminNotification` phát sinh ngoại lệ, exception sẽ nhảy ra ngoài try-catch của `post_job()`, dẫn đến `db.session.rollback()` toàn bộ dữ liệu Job và trả về lỗi 500 kèm thông báo mơ hồ *"Không thể lưu yêu cầu. Vui lòng thử lại"*.

### 4. Luồng Hàng Chờ Kiểm Duyệt Job của Admin (Admin Job Queue)
- **Endpoint:** `GET /admin/jobs` (`admin_jobs()` tại app.py:10255).
- **Lỗ hổng & Sự bất nhất phát hiện (CONFIRMED):**
  - Điều kiện lọc pending: `is_pending = (job.moderation_status == 'pending' or job.status == 'pending') and not job.is_flagged`.
  - Trên database VPS production: Các job lịch sử (Job 46, Job 45...) có `moderation_status = NULL`.
  - Menu Admin Sidebar (`templates/admin_base.html:848`): Chỉ hiển thị badge `admin_badge_flagged_jobs`, **hoàn toàn không hiển thị badge `admin_badge_pending_jobs`**. Khi có job mới nộp, Admin nhìn vào menu không thấy số đếm thông báo chờ duyệt.
  - Tại `admin_moderate_job()` (`app.py:10322`): `decision = request.form.get('decision', 'approve')` mặc định là `'approve'`. Ngoài ra, loại thông báo gửi cho người thuê khi duyệt/từ chối job bị dùng nhầm thành `JOB_MATCH` thay vì `JOB_APPROVED`, `JOB_NEEDS_REVISION`, `JOB_REJECTED`.
  - Tại `admin_hirer_review_action()` (`app.py:10615`): `action = request.form.get('action', 'verify')` mặc định là `'verify'`, vi phạm nguyên tắc kiểm soát phân quyền.

---

## III. Bảng Tổng Hợp Trạng Thái & Bằng Chứng

| Mã lỗi / Hiện tượng | Phân loại | Vị trí mã nguồn | Bằng chứng thực tế |
| :--- | :--- | :--- | :--- |
| Tự động kích hoạt verified khi điền profile | **CONFIRMED** | `app.py:844-850` | `profile.is_verified = True` gán trực tiếp trong `_apply_hirer_profile_form()`. Kiểm tra DB VPS: User 100 (`minhnhatt@gmail.com`) có trạng thái `verified` ngày 15/10 mà không có bất kỳ dòng log nào trong `admin_audit_log`. |
| Action Admin mặc định duyệt hồ sơ | **CONFIRMED** | `app.py:10615` | `request.form.get('action', 'verify')` tự gán verify khi request thiếu trường action. |
| Decision Admin mặc định duyệt Job | **CONFIRMED** | `app.py:10322` | `request.form.get('decision', 'approve')` tự gán approve khi thiếu decision. |
| Sidebar Admin không báo số job chờ duyệt | **CONFIRMED** | `templates/admin_base.html:848` | Template chỉ hiển thị `admin_badge_flagged_jobs`, không render `admin_badge_pending_jobs`. |
| Dùng nhầm loại thông báo Job | **CONFIRMED** | `app.py:10353, 10386` | Dùng `notification_type='JOB_MATCH'` cho sự kiện kiểm duyệt Job. |
| Người thuê mới không đăng được job | **CONFIRMED** | `services/hirer_verification.py:282` | Các user chưa nộp hoặc mới nộp hồ sơ bị chặn đúng theo rule nhưng nhận thông báo chưa rõ ràng. |

---

## IV. Danh Sách Tác Vụ Cần Xử Lý
1. **Loại bỏ tự phê duyệt:** Sửa `_apply_hirer_profile_form` chỉ chuyển sang `pending`, giữ nguyên `is_verified=False`.
2. **Chuẩn hóa Backend Gate:** Sửa `can_hirer_post_job` bắt buộc cả `is_verified=True` và `verification_status='verified'`.
3. **Chống giả mạo request:** Bỏ qua mọi tham số trạng thái xác minh do client gửi lên.
4. **Bảo vệ route xét duyệt Admin:** Bắt buộc có `action` và `decision` hợp lệ, cấm dùng giá trị mặc định có tính phê duyệt; bổ sung action `revoke`.
5. **Đảm bảo tính bền vững của Job:** Bọc phòng vệ việc đánh giá tiêu chí và gửi notification để lỗi thứ cấp không rollback Job hợp lệ.
6. **Thống nhất hàng chờ Admin:** Cập nhật query `admin_jobs`, bổ sung tab "Bị từ chối", hiển thị đúng badge `admin_badge_pending_jobs` trên sidebar.
7. **Bảo vệ dữ liệu lịch sử:** Lập phương án tái xét duyệt cho User 100 mà không tự tiện mass-update database production.
