# HIRER_VERIFICATION_FIX_REPORT.md — Báo Cáo Sửa Vòng Đời & Kiểm Duyệt Người Thuê

## I. Mục Tiêu & Nguyên Tắc Sửa Đổi
1. **Loại bỏ triệt để cơ chế tự xác minh:** Người dùng điền đầy đủ form chỉ đưa hồ sơ vào trạng thái `pending` với `is_verified = False`.
2. **Tuân thủ tiêu chí X8:** Khi tài khoản đã `verified` thay đổi bất kỳ trường thông tin định danh hoặc tài chính trọng yếu nào, quyền xác minh lập tức bị thu hồi, đưa hồ sơ về `pending` chờ Admin thẩm định lại.
3. **Chuẩn hóa bộ tiêu chí thẩm định (Checklist Accuracy):**
   - Phân biệt rõ loại hình tài khoản trong tiêu chí X3: Tài khoản cá nhân (`individual`) được miễn trừ giấy ủy quyền doanh nghiệp; tài khoản doanh nghiệp (`business`) bắt buộc có giấy ủy quyền/quyết định bổ nhiệm do Admin thẩm định.
   - Thắt chặt tiêu chí X5: Bắt buộc tên ngân hàng hợp lệ và số tài khoản có ít nhất 6 chữ số, không chấp nhận chuỗi ký tự rỗng hoặc vô nghĩa.
4. **Bảo vệ cổng phê duyệt Admin (Review Gate Enforcement):**
   - Admin chỉ có thể phê duyệt (`action == 'verify'`) khi toàn bộ tiêu chí bắt buộc đã đạt (`eval_res['all_mandatory_passed'] is True`).
   - Loại bỏ hoàn toàn các giá trị mặc định cho `action` trong request.
5. **Đảm bảo quyền truy cập tài liệu minh chứng cho Quản trị viên:**
   - Cho phép Quản trị viên xem trực tuyến và tải về các tài liệu đính kèm phục vụ thẩm định (`download_verification_document`, `view_verification_document`) mà không bị lỗi 401 Unauthorized.

---

## II. Chi Tiết Các Thay Đổi Mã Nguồn

### 1. Xử Lý Form Hồ Sơ & Thu Hồi Trạng Thái Khi Đổi Thông Tin Trọng Yếu (X8)
- **Vị trí:** `app.py:751-875` trong `_apply_hirer_profile_form()`.
- **Cơ chế:**
  - Thu thập giá trị cũ của các trường trọng yếu trước khi gán dữ liệu mới:
    - Số điện thoại liên hệ: `contact_phone`
    - Thông tin ngân hàng: `bank_name`, `bank_account_number`
    - Thông tin doanh nghiệp: `company`, `tax_code`, `rep_name`, `company_email`
    - Họ và tên người dùng: `user.full_name`
  - Nếu `profile.verification_status == 'verified'`:
    ```python
    if is_verified_before and any_critical_changed:
        profile.verification_status = 'pending'
        profile.is_verified = False
        app.logger.info(
            f"Hirer profile {profile.user_id} critical fields changed, "
            f"reset verification_status to pending and is_verified to False."
        )
    ```
  - Nếu hồ sơ đang ở trạng thái `unverified`, rỗng, hoặc `needs_revision`: chuyển sang `pending` và giữ `is_verified = False`.
  - Giữ nguyên trạng thái nếu hồ sơ đang bị `rejected`, `revoked`, hoặc `suspended`.

### 2. Chuẩn Hóa Tiêu Chí Đánh Giá Trong `services/hirer_verification.py`
- **Tiêu chí X3 (Giấy ủy quyền đại diện tổ chức):**
  - Tài khoản cá nhân (`account_type == 'individual'`): Tự động `status = 'passed'`, `note = 'Tài khoản cá nhân: Miễn trừ giấy ủy quyền doanh nghiệp'`.
  - Tài khoản doanh nghiệp (`business`): Yêu cầu Admin thẩm định và tích chọn `chk_X3`.
- **Tiêu chí X5 (Phương thức thanh toán chính chủ):**
  - Kiểm tra có `bank_name` và `bank_account_number`.
  - Kiểm tra độ dài chữ số: `len(digits) >= 6`. Nếu không đạt, đánh dấu `status = 'failed'`.
- **Quy tắc bắt buộc:**
  - Nhóm tiêu chí bắt buộc gồm: X1, X2, X3, X4, X5.
  - Cờ `all_mandatory_passed = all(c['status'] == 'passed' for c in mandatory_crit)`.

### 3. Cổng Phê Duyệt Của Admin (`app.py:10935-10970`)
- **Vị trí:** Route `admin_hirer_review_action()`.
- **Thay đổi:**
  - Bắt buộc `action` trong danh sách `('verify', 'needs_revision', 'reject', 'revoke')`. Request thiếu action bị từ chối ngay lập tức.
  - Khi `action == 'verify'`:
    ```python
    if not eval_res.get('all_mandatory_passed'):
        flash('Không thể phê duyệt: Hồ sơ chưa đạt đầy đủ các tiêu chí bắt buộc (X1-X5).', 'danger')
        return redirect(url_for('admin_hirer_review', user_id=user_id))
    ```
  - Đảm bảo Admin không thể vô tình hay cố ý duyệt một hồ sơ có tiêu chí bắt buộc không đạt.

### 4. Khắc Phục Lỗi Nuốt Exception Thông Báo & Lỗi Quyền Tài Liệu
- **Vị trí:** `app.py:3390-3415`
  - Thay thế khối `except Exception: pass` bằng `app.logger.warning(..., exc_info=True)`. Lỗi ghi thông báo được ghi log tường minh, không làm gián đoạn luồng người dùng nhưng không bị nuốt im lặng.
- **Vị trí:** `app.py:4436-4510`
  - Cho phép Admin truy cập tài liệu qua `is_admin_session_valid()`:
    ```python
    admin_valid = is_admin_session_valid()
    if not user and not admin_valid:
        abort(401)
    ```

---

## III. Kết Quả Kiểm Thử Nghiệm Thu (Automated Test Results)

Bộ kiểm thử tại `tests/test_hirer_verification_flow.py` và `tests/test_hirer_job_lifecycle_integration.py` đã chạy và đạt 100%:
1. `test_01_profile_completion_does_not_auto_verify`: Người dùng điền đầy đủ form -> chuyển `pending`, `is_verified=False`, không tự cấp quyền đăng job.
2. `test_01_verified_hirer_changes_critical_fields_revokes_verified`: Tài khoản đã verified khi đổi `contact_phone` hoặc số tài khoản ngân hàng lập tức bị thu hồi về `pending` và `is_verified=False`.
3. `test_02_admin_review_enforces_mandatory_passed_gate`: Admin gửi `action=verify` cho hồ sơ thiếu tiêu chí bắt buộc bị chặn lại với thông báo lỗi rõ ràng.
4. `test_05_admin_can_download_and_view_verification_document`: Admin có session hợp lệ có thể xem và tải tài liệu xác minh phục vụ thẩm định (HTTP 200).
5. `test_can_hirer_post_job_enforces_strict_admin_verification`: Chặn triệt để mọi trạng thái không hợp lệ tại backend.
