import re
import json

app_file = 'app.py'
with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# flash(..., ...)
# we will just replace known exact string literals.

replacements = {
    "'Vui lòng đăng nhập để tiếp tục.'": "_t('flash.login_required')",
    "'Bạn không có quyền truy cập trang này.'": "_t('flash.unauthorized')",
    "'Tài khoản đã bị khoá.'": "_t('flash.account_locked')",
    "'Đăng nhập thành công!'": "_t('flash.login_success')",
    "'Mật khẩu không đúng.'": "_t('flash.invalid_password')",
    "'Tài khoản không tồn tại hoặc email không đúng.'": "_t('flash.account_not_found')",
    "'Hệ thống đang quá tải hoặc cơ sở dữ liệu bị khoá. Vui lòng thử lại sau.'": "_t('flash.system_overload')",
    "'Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau.'": "_t('flash.db_error')",
    "'Vai trò không hợp lệ.'": "_t('flash.invalid_role')",
    "'Email không hợp lệ. Vui lòng nhập đúng định dạng.'": "_t('flash.invalid_email')",
    "'Đăng ký thành công! Vui lòng đăng nhập.'": "_t('flash.register_success')",
    "'Tài khoản với email này đã tồn tại. Vui lòng đăng nhập.'": "_t('flash.email_exists')",
    "'Đã đăng xuất.'": "_t('flash.logout_success')",
    "'Không tìm thấy tài khoản.'": "_t('flash.account_not_found')",
    "'MongoDB chưa được cấu hình.'": "_t('flash.mongo_error')",
    "'Đã cập nhật thông tin cơ bản!'": "_t('flash.profile_updated')",
    "'Mật khẩu hiện tại không đúng.'": "_t('flash.old_password_incorrect')",
    "'Mật khẩu mới không khớp.'": "_t('flash.new_password_mismatch')",
    "'Mật khẩu mới phải ít nhất 6 ký tự.'": "_t('flash.password_too_short')",
    "'Đã đổi mật khẩu thành công!'": "_t('flash.password_changed')",
    "'Đã cập nhật hồ sơ phiên dịch viên!'": "_t('flash.translator_profile_updated')",
    "'Đã lưu tùy chọn phiên dịch!'": "_t('flash.preferences_saved')",
    "'Đã cập nhật hồ sơ khách thuê!'": "_t('flash.hirer_profile_updated')",
    "'Phiên dịch viên này hiện không hoạt động.'": "_t('flash.translator_inactive')",
    "'Bạn không thể tự thuê chính mình.'": "_t('flash.cannot_hire_self')",
    "'Đặt dịch vụ thành công! Vui lòng thanh toán Escrow để bắt đầu.'": "_t('flash.service_booked')",
    "'Đã xảy ra lỗi hệ thống, vui lòng thử lại sau.'": "_t('flash.system_error')",
    "'Chỉ Khách hàng mới có thể đăng công việc.'": "_t('flash.hirer_only_post')",
    "'Đã đăng yêu cầu thành công!'": "_t('flash.job_posted')",
    "'Vui lòng đăng nhập để gửi đề xuất.'": "_t('flash.login_required')",
    "'Chỉ Phiên dịch viên mới có thể ứng tuyển.'": "_t('flash.translator_only_apply')",
    "'Công việc đã đóng, không thể ứng tuyển.'": "_t('flash.job_closed')",
    "'Bạn không thể ứng tuyển công việc của chính mình.'": "_t('flash.cannot_apply_own_job')",
    "'Bạn đã gửi đề xuất cho công việc này rồi.'": "_t('flash.already_applied')",
    "'Không được để trống Giá đề xuất và Thời gian hoàn thành.'": "_t('flash.missing_proposal_fields')",
    "'Gửi đề xuất thành công!'": "_t('flash.proposal_sent')",
    "'Đã gửi tin nhắn!'": "_t('flash.message_sent')",
}

for vi, repl in replacements.items():
    content = content.replace(vi, repl)

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

# Now update JSON files
new_keys_vi = {
    "login_required": "Vui lòng đăng nhập để tiếp tục.",
    "unauthorized": "Bạn không có quyền truy cập trang này.",
    "account_locked": "Tài khoản đã bị khoá.",
    "login_success": "Đăng nhập thành công!",
    "invalid_password": "Mật khẩu không đúng.",
    "account_not_found": "Tài khoản không tồn tại hoặc email không đúng.",
    "system_overload": "Hệ thống đang quá tải hoặc cơ sở dữ liệu bị khoá. Vui lòng thử lại sau.",
    "db_error": "Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau.",
    "invalid_role": "Vai trò không hợp lệ.",
    "invalid_email": "Email không hợp lệ. Vui lòng nhập đúng định dạng.",
    "register_success": "Đăng ký thành công! Vui lòng đăng nhập.",
    "email_exists": "Tài khoản với email này đã tồn tại. Vui lòng đăng nhập.",
    "logout_success": "Đã đăng xuất.",
    "mongo_error": "MongoDB chưa được cấu hình.",
    "profile_updated": "Đã cập nhật thông tin cơ bản!",
    "old_password_incorrect": "Mật khẩu hiện tại không đúng.",
    "new_password_mismatch": "Mật khẩu mới không khớp.",
    "password_too_short": "Mật khẩu mới phải ít nhất 6 ký tự.",
    "password_changed": "Đã đổi mật khẩu thành công!",
    "translator_profile_updated": "Đã cập nhật hồ sơ phiên dịch viên!",
    "preferences_saved": "Đã lưu tùy chọn phiên dịch!",
    "hirer_profile_updated": "Đã cập nhật hồ sơ khách thuê!",
    "translator_inactive": "Phiên dịch viên này hiện không hoạt động.",
    "cannot_hire_self": "Bạn không thể tự thuê chính mình.",
    "service_booked": "Đặt dịch vụ thành công! Vui lòng thanh toán Escrow để bắt đầu.",
    "system_error": "Đã xảy ra lỗi hệ thống, vui lòng thử lại sau.",
    "hirer_only_post": "Chỉ Khách hàng mới có thể đăng công việc.",
    "job_posted": "Đã đăng yêu cầu thành công!",
    "translator_only_apply": "Chỉ Phiên dịch viên mới có thể ứng tuyển.",
    "job_closed": "Công việc đã đóng, không thể ứng tuyển.",
    "cannot_apply_own_job": "Bạn không thể ứng tuyển công việc của chính mình.",
    "already_applied": "Bạn đã gửi đề xuất cho công việc này rồi.",
    "missing_proposal_fields": "Không được để trống Giá đề xuất và Thời gian hoàn thành.",
    "proposal_sent": "Gửi đề xuất thành công!",
    "message_sent": "Đã gửi tin nhắn!",
}

new_keys_en = {
    "login_required": "Please log in to continue.",
    "unauthorized": "You are not authorized to access this page.",
    "account_locked": "Account is locked.",
    "login_success": "Logged in successfully!",
    "invalid_password": "Incorrect password.",
    "account_not_found": "Account not found or incorrect email.",
    "system_overload": "System is overloaded. Please try again later.",
    "db_error": "Database connection error. Please try again later.",
    "invalid_role": "Invalid role.",
    "invalid_email": "Invalid email address.",
    "register_success": "Registered successfully! Please log in.",
    "email_exists": "An account with this email already exists. Please log in.",
    "logout_success": "Logged out successfully.",
    "mongo_error": "MongoDB is not configured.",
    "profile_updated": "Profile updated successfully!",
    "old_password_incorrect": "Current password is incorrect.",
    "new_password_mismatch": "New passwords do not match.",
    "password_too_short": "New password must be at least 6 characters.",
    "password_changed": "Password changed successfully!",
    "translator_profile_updated": "Translator profile updated successfully!",
    "preferences_saved": "Preferences saved successfully!",
    "hirer_profile_updated": "Hirer profile updated successfully!",
    "translator_inactive": "This translator is currently inactive.",
    "cannot_hire_self": "You cannot hire yourself.",
    "service_booked": "Service booked successfully! Please proceed to Escrow payment.",
    "system_error": "A system error occurred, please try again later.",
    "hirer_only_post": "Only Hirers can post jobs.",
    "job_posted": "Job posted successfully!",
    "translator_only_apply": "Only Translators can apply.",
    "job_closed": "This job is closed and no longer accepting proposals.",
    "cannot_apply_own_job": "You cannot apply to your own job.",
    "already_applied": "You have already applied to this job.",
    "missing_proposal_fields": "Proposed Rate and Delivery Time are required.",
    "proposal_sent": "Proposal sent successfully!",
    "message_sent": "Message sent!",
}

with open('i18n/vi.json', 'r', encoding='utf-8') as f:
    vi_data = json.load(f)
with open('i18n/en.json', 'r', encoding='utf-8') as f:
    en_data = json.load(f)

vi_data['flash'] = new_keys_vi
en_data['flash'] = new_keys_en

with open('i18n/vi.json', 'w', encoding='utf-8') as f:
    json.dump(vi_data, f, ensure_ascii=False, indent=2)
with open('i18n/en.json', 'w', encoding='utf-8') as f:
    json.dump(en_data, f, ensure_ascii=False, indent=2)

print("Replaced app.py strings and updated i18n JSON.")
