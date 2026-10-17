# HIRER_VERIFICATION_FIX_REPORT.md — Báo Cáo Sửa Vòng Đời Xác Minh Người Thuê

## I. Mục Tiêu Sửa Đổi
1. Loại bỏ hoàn toàn cơ chế tự động kích hoạt `is_verified=True` và `verification_status='verified'` khi người dùng hoàn thành form hồ sơ.
2. Thiết lập quyền phê duyệt xác minh duy nhất thuộc về Ban quản trị (Admin) có thẩm quyền (`require_permission('verify_hirer')`).
3. Ngăn chặn triệt để nguy cơ giả mạo trạng thái xác minh qua request HTTP từ trình duyệt.
4. Đảm bảo quy trình chuyển đổi trạng thái hồ sơ nhất quán: `unverified` -> `pending` -> `verified` / `needs_revision` / `rejected` / `revoked`.

---

## II. Chi Tiết Các Thay Đổi Mã Nguồn

### 1. `app.py` — Hàm `_apply_hirer_profile_form(user, profile, form, files)`
- **Vị trí:** `app.py:844-852`
- **Mã nguồn trước khi sửa:**
  ```python
  if profile.verification_status not in ('rejected', 'revoked', 'suspended'):
      profile.is_verified = True
      profile.verification_status = 'verified'
      if not profile.verified_at:
          profile.verified_at = datetime.utcnow()
  return []
  ```
- **Mã nguồn sau khi sửa:**
  ```python
  # Cập nhật trạng thái xác minh:
  # Người dùng điền đủ thông tin hợp lệ chỉ đưa hồ sơ vào trạng thái 'pending' chờ Admin duyệt.
  # Tuyệt đối KHÔNG tự động cấp quyền 'verified'. Quyết định phê duyệt thuộc thẩm quyền Admin.
  # Nếu hồ sơ đang ở trạng thái bị từ chối/thu hồi/đình chỉ, không tự mở lại.
  # Nếu hồ sơ đã được Admin xác minh trước đó, giữ nguyên trạng thái xác minh.
  if profile.verification_status in ('unverified', None, '', 'needs_revision'):
      profile.verification_status = 'pending'
      profile.is_verified = False
  return []
  ```
- **Tác dụng:**
  - Hồ sơ mới điền đủ dữ liệu hợp lệ chuyển sang trạng thái `pending` và giữ `is_verified = False`.
  - Hồ sơ đang bị yêu cầu bổ sung (`needs_revision`) khi sửa lại cũng quay về `pending`, không tự vượt cấp.
  - Hồ sơ đã bị `rejected`, `revoked` hoặc `suspended` không bị tự ý mở lại khi gửi form.
  - Các tham số giả mạo như `is_verified` hay `verification_status` trong form client hoàn toàn bị phớt lờ.

### 2. `app.py` — Route Lưu Hồ Sơ Khách Thuê (`account_profile`)
- **Vị trí:** `app.py:3380-3408`
- **Thay đổi:**
  - Phân biệt rõ rệt 3 kịch bản:
    1. `profile.is_verified and profile.verification_status == 'verified'`: Báo cập nhật hồ sơ thành công.
    2. `profile.verification_status == 'pending'`: Báo hồ sơ đã lưu và gửi yêu cầu thẩm định tới Ban quản trị; đồng thời tạo bản ghi `AdminNotification(type='HIRER_VERIFICATION')` (kiểm tra tránh trùng lặp thông báo chưa đọc).
    3. `profile.verification_status in ('rejected', 'revoked', 'suspended')`: Cảnh báo hồ sơ không hợp lệ để tự động nộp lại.

### 3. `app.py` — Route Thẩm Định Admin (`admin_hirer_review_action`)
- **Vị trí:** `app.py:10636-10735`
- **Thay đổi:**
  - Bắt buộc kiểm tra `action in ('verify', 'needs_revision', 'reject', 'revoke')`.
  - **Loại bỏ hoàn toàn hành vi mặc định `action = request.form.get('action', 'verify')`**. Nếu request thiếu hoặc sai action, hệ thống lập tức từ chối và hiển thị flash thông báo lỗi.
  - Bổ sung nhánh xử lý `action == 'revoke'`: chuyển trạng thái về `revoked`, thu hồi cờ `is_verified=False`, ghi `AdminAuditLog(action=ADMIN_AUDIT_ACTIONS['REVOKE_HIRER'])` và gửi thông báo `VERIFICATION_REVOKED` tới khách thuê.

### 4. `app.py` — Danh Sách Quản Lý Người Thuê (`admin_hirers`)
- **Vị trí:** `app.py:10586-10620`
- **Thay đổi:**
  - Định nghĩa chính xác `is_pending = bool(p and p.verification_status == 'pending')`. Chỉ những tài khoản đã nộp hồ sơ hợp lệ và đang chờ duyệt mới xuất hiện trong bộ đếm `pending_count` và tab "Chờ xác minh".
  - Người dùng mới đăng ký chưa khai báo thông tin (`unverified`) được hiển thị đúng badge "Chưa nộp hồ sơ", không bị hiển thị nhầm là "Chờ xác minh".

### 5. `services/hirer_verification.py` — Hàm `can_hirer_post_job(user)`
- **Vị trí:** `services/hirer_verification.py:282-325`
- **Thay đổi:**
  - Bắt buộc đồng thời cả hai điều kiện: `profile.is_verified is True` VÀ `profile.verification_status == 'verified'`.
  - Thêm thông báo giải thích chi tiết theo từng trạng thái:
    - `pending`: *"Hồ sơ người đăng tuyển của bạn đang chờ Ban quản trị xét duyệt. Chức năng đăng tuyển sẽ được kích hoạt sau khi hồ sơ được phê duyệt."*
    - `needs_revision`: Kèm lý do cần chỉnh sửa cụ thể.
    - `rejected` / `revoked`: Thông báo bị từ chối/thu hồi và hướng dẫn liên hệ hỗ trợ.

---

## III. Kết Quả Kiểm Thử Nghiệm Thu (Automated Test Results)

Đã chạy thành công bộ kiểm thử tự động tại `tests/test_hirer_verification_flow.py`:
- `test_01_profile_completion_does_not_auto_verify`: **PASSED** (điền đủ form -> pending, `is_verified=False`, verified_at=None, không thể đăng job).
- `test_02_needs_revision_profile_resubmission_goes_to_pending`: **PASSED** (sửa form khi needs_revision -> pending, `is_verified=False`).
- `test_03_rejected_profile_cannot_self_verify_on_edit`: **PASSED** (hồ sơ rejected không thể tự verify khi sửa form).
- `test_04_can_hirer_post_job_enforces_strict_admin_verification`: **PASSED** (chặn unverified, pending, revoked; chỉ cho phép verified hợp lệ).
- `test_05_admin_hirer_review_requires_explicit_action`: **PASSED** (Admin request thiếu action bị từ chối, không tự động duyệt).
