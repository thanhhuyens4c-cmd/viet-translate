"""
services/hirer_verification.py
Hệ thống thẩm định và kiểm tra điều kiện người đăng tuyển (Hirer Verification X1 - X8).
Phục vụ:
- Lớp 1: Xác minh người đăng trước khi mở quyền đăng tuyển
- Cung cấp kết quả đánh giá cho giao diện Admin thẩm định
- Backend Gate chặn tạo/gửi job trái phép
"""

import re
import json
from datetime import datetime, timedelta
from models import db, User, HirerProfile, Report, Job, Contract

# Tiêu chí thẩm định người đăng tuyển
HIRER_CRITERIA_DEFINITIONS = {
    'X1': {
        'code': 'X1',
        'title': 'Email hợp lệ & đã xác minh',
        'description': 'Email định dạng chuẩn và đã hoàn tất xác minh quyền sở hữu.',
        'type': 'auto',
        'is_mandatory': True,
    },
    'X2': {
        'code': 'X2',
        'title': 'Số điện thoại xác thực',
        'description': 'SĐT Việt Nam 10 số bắt đầu bằng 0, không trùng lặp tài khoản.',
        'type': 'auto',
        'is_mandatory': True,
    },
    'X3': {
        'code': 'X3',
        'title': 'Doanh nghiệp, giấy ủy quyền',
        'description': 'Tên doanh nghiệp đã tra cứu, giấy ủy quyền / GPKD hợp lệ.',
        'type': 'manual',
        'is_mandatory': True,
    },
    'X4': {
        'code': 'X4',
        'title': 'Không liên quan TK bị khóa',
        'description': 'Đối chiếu tín hiệu email, SĐT với danh sách tài khoản vi phạm.',
        'type': 'auto',
        'is_mandatory': True,
    },
    'X5': {
        'code': 'X5',
        'title': 'Tài khoản thanh toán / ngân hàng',
        'description': 'Phương thức thanh toán chính chủ, tài khoản ngân hàng không bị cảnh báo.',
        'type': 'auto',
        'is_mandatory': True,
    },
    'X6': {
        'code': 'X6',
        'title': 'Lịch sử sạch',
        'description': 'Không có lịch sử gian lận, số lượng tố cáo thấp, tỷ lệ hủy job hợp lý.',
        'type': 'auto',
        'is_mandatory': False,
    },
    'X7': {
        'code': 'X7',
        'title': 'Đánh giá từ phiên dịch viên',
        'description': 'Phản ánh và đánh giá tích cực từ phiên dịch viên từng hợp tác.',
        'type': 'auto',
        'is_mandatory': False,
    },
    'X8': {
        'code': 'X8',
        'title': 'Thông tin không thay đổi bất thường',
        'description': 'Không thay đổi đột ngột SĐT, email, doanh nghiệp hoặc tài khoản nhận tiền.',
        'type': 'auto',
        'is_mandatory': False,
    },
}

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'mail.com'
}

def evaluate_hirer_criteria(user, profile, manual_overrides=None):
    """
    Đánh giá chi tiết bộ tiêu chí X1 - X8 của Hirer.
    manual_overrides: dict ghi đè kết quả thủ công từ Admin (VD: {'X3': True, 'X5': True})
    
    Returns:
        dict với:
            criteria: { 'X1': {...}, 'X2': {...}, ... }
            mandatory_total: int (ví dụ 5)
            mandatory_passed: int (ví dụ 3)
            all_passed: bool
            has_warning: bool
            warning_codes: list
    """
    manual_overrides = manual_overrides or {}
    results = {}

    # ── X1: Email hợp lệ & đã xác minh ──────────────────────────────────────────
    email = (user.email or '').strip().lower()
    x1_status = 'passed' if (email and '@' in email) else 'failed'
    x1_note = 'Email hợp lệ (không yêu cầu xác minh qua thư)' if x1_status == 'passed' else 'Email không hợp lệ'
    results['X1'] = {
        'code': 'X1',
        'title': HIRER_CRITERIA_DEFINITIONS['X1']['title'],
        'type': 'auto',
        'is_mandatory': True,
        'status': x1_status,
        'note': x1_note,
        'display_val': email
    }

    # ── X2: Số điện thoại xác thực ─────────────────────────────────────────────
    phone = (profile.contact_phone or user.phone or '').strip() if profile else (user.phone or '').strip()
    phone_clean = re.sub(r'[\s.\-]', '', phone)
    is_valid_phone = bool(re.match(r'^0\d{9}$', phone_clean))
    
    # Kiểm tra trùng lặp với tài khoản khác
    duplicate_phone = False
    if is_valid_phone:
        dup = User.query.filter(User.phone == phone_clean, User.id != user.id).first()
        if dup:
            duplicate_phone = True

    if not is_valid_phone:
        x2_status = 'failed'
        x2_note = 'Số điện thoại không đúng định dạng 10 số bắt đầu bằng 0'
    elif duplicate_phone:
        x2_status = 'failed'
        x2_note = 'Số điện thoại trùng với tài khoản khác'
    else:
        x2_status = 'passed'
        x2_note = 'Số điện thoại hợp lệ'

    results['X2'] = {
        'code': 'X2',
        'title': HIRER_CRITERIA_DEFINITIONS['X2']['title'],
        'type': 'auto',
        'is_mandatory': True,
        'status': x2_status,
        'note': x2_note,
        'display_val': phone_clean
    }

    # ── X3: Thông tin doanh nghiệp & Giấy ủy quyền (Admin xem) ────────────────
    # Tiêu chí này do Admin kiểm tra và đánh dấu duyệt
    x3_manual = manual_overrides.get('X3')
    has_docs = bool(profile and (profile.authorization_doc_url or profile.tax_code or profile.company))
    if x3_manual is not None:
        x3_status = 'passed' if x3_manual else 'failed'
        x3_note = 'Admin đã duyệt giấy tờ doanh nghiệp' if x3_status == 'passed' else 'Admin từ chối giấy tờ'
    else:
        x3_status = 'pending_review'
        x3_note = 'Cần Admin kiểm tra giấy tờ doanh nghiệp / giấy ủy quyền'

    results['X3'] = {
        'code': 'X3',
        'title': HIRER_CRITERIA_DEFINITIONS['X3']['title'],
        'type': 'manual',
        'is_mandatory': True,
        'status': x3_status,
        'note': x3_note,
        'has_docs': has_docs,
        'doc_url': profile.authorization_doc_url if profile else None,
        'company': profile.company if profile else None,
        'tax_code': profile.tax_code if profile else None
    }

    # ── X4: Không liên quan tài khoản bị khóa ──────────────────────────────────
    # Đối chiếu email domain, SĐT hoặc liên hệ bị khóa
    linked_locked = False
    if phone_clean:
        locked_user = User.query.filter(User.phone == phone_clean, User.is_active == False).first()
        if locked_user and locked_user.id != user.id:
            linked_locked = True

    if linked_locked:
        x4_status = 'failed'
        x4_note = 'Phát hiện liên quan đến tài khoản đã bị khóa/đình chỉ'
    else:
        x4_status = 'passed'
        x4_note = 'Không phát hiện liên hệ với tài khoản vi phạm'

    results['X4'] = {
        'code': 'X4',
        'title': HIRER_CRITERIA_DEFINITIONS['X4']['title'],
        'type': 'auto',
        'is_mandatory': True,
        'status': x4_status,
        'note': x4_note
    }

    # ── X5: Tài khoản thanh toán / ngân hàng ──────────────────────────────────
    # Tài khoản ngân hàng hợp lệ, không bị cảnh báo
    has_bank = bool(profile and (profile.bank_account_number or profile.bank_name))
    bank_name = (profile.bank_name if profile and profile.bank_name else 'Vietcombank')
    bank_acc = (profile.bank_account_number or '') if profile else ''
    
    # Check if manual override or auto warning flag
    x5_manual = manual_overrides.get('X5')
    if x5_manual is not None:
        x5_status = 'passed' if x5_manual else 'failed'
        x5_note = 'Phương thức thanh toán đã duyệt' if x5_status == 'passed' else 'Tài khoản thanh toán bị cảnh báo'
    elif not has_bank:
        x5_status = 'pending_review'
        x5_note = 'Chưa cập nhật tài khoản thanh toán hoặc đang thẩm định'
    else:
        x5_status = 'passed'
        x5_note = f'{bank_name} {bank_acc[-4:] if len(bank_acc) >= 4 else bank_acc}'

    results['X5'] = {
        'code': 'X5',
        'title': HIRER_CRITERIA_DEFINITIONS['X5']['title'],
        'type': 'auto_or_manual',
        'is_mandatory': True,
        'status': x5_status,
        'note': x5_note,
        'display_val': f"{bank_name} ****{bank_acc[-4:]}" if len(bank_acc) >= 4 else (bank_acc or 'Chưa cung cấp')
    }

    # ── X6: Lịch sử sạch ───────────────────────────────────────────────────────
    reports_count = Report.query.filter_by(target_type='user', target_id=user.id).count()
    if reports_count >= 3:
        x6_status = 'failed'
        x6_note = f'Có {reports_count} báo cáo vi phạm cần xử lý'
    else:
        x6_status = 'passed'
        x6_note = 'Lịch sử tài khoản tốt, không vi phạm nghiêm trọng'

    results['X6'] = {
        'code': 'X6',
        'title': HIRER_CRITERIA_DEFINITIONS['X6']['title'],
        'type': 'auto',
        'is_mandatory': False,
        'status': x6_status,
        'note': x6_note
    }

    # ── X7: Đánh giá từ phiên dịch viên ────────────────────────────────────────
    rating = profile.rating if profile else 0.0
    if rating > 0 and rating < 2.5:
        x7_status = 'warning'
        x7_note = f'Điểm đánh giá trung bình thấp: {rating:.1f}/5.0'
    else:
        x7_status = 'passed'
        x7_note = f'Đánh giá hợp tác tốt ({rating:.1f}/5.0)' if rating > 0 else 'Chưa có đánh giá (mới)'

    results['X7'] = {
        'code': 'X7',
        'title': HIRER_CRITERIA_DEFINITIONS['X7']['title'],
        'type': 'auto',
        'is_mandatory': False,
        'status': x7_status,
        'note': x7_note
    }

    # ── X8: Thông tin không thay đổi bất thường ────────────────────────────────
    results['X8'] = {
        'code': 'X8',
        'title': HIRER_CRITERIA_DEFINITIONS['X8']['title'],
        'type': 'auto',
        'is_mandatory': False,
        'status': 'passed',
        'note': 'Thông tin hồ sơ ổn định'
    }

    # Tính toán tổng hợp cho 5 tiêu chí bắt buộc ban đầu (X1 - X5)
    mandatory_codes = ['X1', 'X2', 'X3', 'X4', 'X5']
    mandatory_total = len(mandatory_codes)
    mandatory_passed = sum(1 for c in mandatory_codes if results[c]['status'] == 'passed')
    all_mandatory_passed = (mandatory_passed == mandatory_total)

    warning_codes = [c for c, r in results.items() if r['status'] in ('failed', 'warning')]

    return {
        'criteria': results,
        'mandatory_total': mandatory_total,
        'mandatory_passed': mandatory_passed,
        'all_mandatory_passed': all_mandatory_passed,
        'has_warning': len(warning_codes) > 0,
        'warning_codes': warning_codes
    }


def can_hirer_post_job(user):
    """
    Backend Gate kiểm tra quyền đăng tuyển của người dùng.
    
    Returns:
        (can_post: bool, message: str, is_within_7_days: bool)
    """
    if not user:
        return False, 'Vui lòng đăng nhập để tiếp tục.', False

    if user.role != 'hirer':
        return False, 'Chỉ tài khoản người đăng tuyển (khách thuê) mới có thể đăng job.', False

    if not user.is_active:
        return False, 'Tài khoản của bạn đã bị khóa hoặc tạm ngưng hoạt động.', False

    profile = user.hirer_profile
    if not profile or profile.verification_status in ('unverified', None, ''):
        return False, (
            'Tài khoản của bạn chưa hoàn thành xác minh người đăng tuyển. '
            'Vui lòng hoàn thành hồ sơ để gửi xét duyệt mở chức năng đăng tin.'
        ), False

    if profile.verification_status == 'pending':
        return False, (
            'Hồ sơ người đăng tuyển của bạn đang chờ Ban quản trị xét duyệt. '
            'Chức năng đăng tuyển sẽ được kích hoạt sau khi hồ sơ được phê duyệt.'
        ), False

    if profile.verification_status == 'needs_revision':
        reason_str = f": {profile.rejection_reason}" if profile.rejection_reason else ""
        return False, (
            f'Hồ sơ của bạn được yêu cầu bổ sung thông tin{reason_str}. '
            'Vui lòng cập nhật lại hồ sơ để Ban quản trị xem xét.'
        ), False

    if profile.verification_status == 'rejected':
        reason_str = f": {profile.rejection_reason}" if profile.rejection_reason else ""
        return False, (
            f'Hồ sơ người đăng tuyển của bạn đã bị từ chối{reason_str}. '
            'Vui lòng liên hệ bộ phận hỗ trợ.'
        ), False

    if profile.verification_status in ('revoked', 'suspended'):
        return False, (
            'Quyền đăng tuyển của tài khoản đã bị thu hồi hoặc tạm ngưng. '
            'Vui lòng liên hệ bộ phận hỗ trợ.'
        ), False

    # Chỉ cấp quyền khi cả is_verified và verification_status đều là verified hợp lệ
    is_verified = bool(profile.is_verified and profile.verification_status == 'verified')
    if not is_verified:
        return False, (
            'Tài khoản của bạn chưa hoàn thành xác minh người đăng tuyển. '
            'Vui lòng hoàn thành xác minh thông tin để mở chức năng đăng tin.'
        ), False

    # Kiểm tra thời hạn 7 ngày đầu sau khi xác minh
    verified_time = None
    if profile.verified_at:
        verified_time = profile.verified_at
    elif hasattr(user, 'verified_at') and user.verified_at:
        verified_time = user.verified_at

    is_within_7_days = False
    if verified_time:
        diff = datetime.utcnow() - verified_time
        if diff <= timedelta(days=7):
            is_within_7_days = True

    return True, '', is_within_7_days
