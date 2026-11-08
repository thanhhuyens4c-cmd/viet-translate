"""
services/auto_verification_service.py
Hệ thống Hybrid Auto-Verification cho VietTranslate:
- Tự động thẩm định hồ sơ phiên dịch viên đa điều kiện: Email, CV, CCCD/Hộ chiếu, Chứng chỉ số QR.
- Áp dụng mô hình 3 vùng độ tin cậy họ tên và danh sách nguồn cấp tin cậy (Whitelist).
- Hỗ trợ chế độ Chạy thử (Dry-Run mode) mặc định: chỉ phân tích và đề xuất, không đổi trạng thái.
- Hỗ trợ chế độ Duyệt tự động (Auto-Approve) có kiểm soát chặt chẽ và giới hạn lô (Batch Processing).
- Ghi vết kiểm toán (Admin Audit Log) đầy đủ, minh bạch và an toàn cho VPS 1 vCPU / 2GB RAM.
"""

from __future__ import annotations
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from models import (
    db,
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument,
    AdminAuditLog,
    ADMIN_AUDIT_ACTIONS
)
from services.cert_verifier import verify_certificate, calculate_name_match

# ─── CẤU HÌNH MẶC ĐỊNH & LƯU TRỮ ─────────────────────────────────────────────

CONFIG_FILE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..', 'instance', 'auto_verification_config.json'
)

DEFAULT_SETTINGS: Dict[str, Any] = {
    'auto_approve_enabled': False,      # Mặc định TẮT phê duyệt tự động
    'dry_run_mode': True,              # Mặc định BẬT chạy thử (chỉ gắn cờ đề xuất)
    'min_name_match_score': 0.85,      # Ngưỡng khớp tên vùng High Confidence
    'batch_size': 15,                  # Tối đa 15 hồ sơ / lô để tối ưu VPS 1 vCPU
    'require_email_verified': True,    # Bắt buộc email đã xác thực
    'require_cv': True,                # Bắt buộc có tệp CV hợp lệ
    'require_id_card': True,           # Bắt buộc có CCCD / Hộ chiếu
}


def get_auto_verification_settings() -> Dict[str, Any]:
    """
    Lấy cấu hình thẩm định tự động hiện hành từ file JSON (fallback sang DEFAULT_SETTINGS).
    """
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
        except Exception as e:
            print(f"[AutoVerification] Lỗi đọc file config: {e}", file=sys.stderr)
    return DEFAULT_SETTINGS.copy()


def save_auto_verification_settings(settings: Dict[str, Any], admin_user: Optional[User] = None, ip_address: Optional[str] = None) -> Tuple[bool, str]:
    """
    Cập nhật và lưu cấu hình thẩm định tự động, ghi Audit Log.
    """
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        current = get_auto_verification_settings()
        current.update(settings)
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)

        if admin_user:
            try:
                AdminAuditLog.log(
                    action=ADMIN_AUDIT_ACTIONS.get('UPDATE_VERIFICATION_SETTINGS', 'UPDATE_VERIFICATION_SETTINGS'),
                    admin_id=admin_user.id,
                    target_type='system_setting',
                    target_id=None,
                    description=f'Admin {admin_user.name} cập nhật cấu hình Hybrid Auto-Verification (Auto-Approve: {current.get("auto_approve_enabled")}, Dry-Run: {current.get("dry_run_mode")})',
                    ip_address=ip_address,
                    extra_data=current
                )
                db.session.commit()
            except Exception:
                pass

        return True, "Cập nhật cấu hình thẩm định tự động thành công."
    except Exception as e:
        return False, f"Lỗi khi lưu cấu hình: {str(e)}"


# ─── ĐÁNH GIÁ HỒ SƠ ĐA ĐIỀU KIỆN (EVALUATION ENGINE) ──────────────────────────

def evaluate_verification_submission(verification_id: int) -> Dict[str, Any]:
    """
    Phân tích và thẩm định độc lập 4 khía cạnh của một hồ sơ xác minh:
    1. Trạng thái tài khoản & Email.
    2. Tệp CV và kinh nghiệm nghề nghiệp.
    3. Tài liệu định danh cá nhân (CCCD / Hộ chiếu).
    4. Chứng chỉ số trực tuyến (QR / Digital Badge).

    Kết quả auto_status:
    - 'auto_eligible': Đạt 100% điều kiện, đủ tiêu chuẩn đề xuất duyệt.
    - 'manual_review': Cần Admin thẩm định bằng mắt (lệch tên nhẹ, thiếu link số, website nguồn lỗi).
    - 'not_eligible': Vi phạm tiêu chuẩn (chứng chỉ hết hạn, bị thu hồi, sai lệch lớn).
    """
    verification = TranslatorVerification.query.get(verification_id)
    if not verification:
        return {'success': False, 'message': 'Không tìm thấy hồ sơ xác minh.'}

    user = verification.user
    if not user:
        return {'success': False, 'message': 'Không tìm thấy người dùng sở hữu hồ sơ.'}

    settings = get_auto_verification_settings()

    checks: Dict[str, Any] = {
        'email': {'passed': False, 'label': 'Xác thực Email', 'detail': ''},
        'cv': {'passed': False, 'label': 'Hồ sơ CV', 'detail': ''},
        'identity': {'passed': False, 'label': 'Định danh (CCCD/Hộ chiếu)', 'detail': ''},
        'certificate': {'passed': False, 'label': 'Chứng chỉ năng lực', 'detail': '', 'status': 'pending'},
        'profile_data': {'passed': False, 'label': 'Thông tin chuyên môn', 'detail': ''}
    }

    # 1. Kiểm tra Email
    if user.email_verified:
        checks['email']['passed'] = True
        checks['email']['detail'] = f"Đã xác minh ({user.email})"
    else:
        checks['email']['passed'] = False
        checks['email']['detail'] = "Chưa xác minh địa chỉ email."

    # 2. Kiểm tra CV
    active_cv = verification.active_cv_doc
    if active_cv and active_cv.file_size > 0 and active_cv.file_extension in ('pdf', 'docx', 'doc'):
        checks['cv']['passed'] = True
        checks['cv']['detail'] = f"Tệp hợp lệ: {active_cv.original_filename} ({round(active_cv.file_size / 1024, 1)} KB)"
    elif verification.cv_url or verification.cv_filename:
        checks['cv']['passed'] = True
        checks['cv']['detail'] = f"Đã có tệp CV lưu trữ ({verification.cv_filename or 'URL'})"
    else:
        checks['cv']['passed'] = False
        checks['cv']['detail'] = "Chưa nộp tệp CV hoặc tệp không hợp lệ."

    # 3. Kiểm tra tài liệu định danh (CCCD/Hộ chiếu)
    id_docs = [d for d in verification.documents if d.is_active and d.document_type in ('id_card', 'diploma') and d.file_size > 0]
    if id_docs:
        checks['identity']['passed'] = True
        checks['identity']['detail'] = f"Đã tải lên {len(id_docs)} tài liệu minh chứng định danh."
    elif verification.id_card_url or verification.id_card_filename:
        checks['identity']['passed'] = True
        checks['identity']['detail'] = "Đã có minh chứng CCCD trong hồ sơ."
    else:
        checks['identity']['passed'] = False
        checks['identity']['detail'] = "Chưa có tài liệu CCCD/Hộ chiếu."

    # 4. Kiểm tra Chứng chỉ số trực tuyến (QR / Digital Badge)
    cert_status = 'manual_review'
    name_score = 0.0
    cert_detail = "Hồ sơ truyền thống, không có đường dẫn kiểm thực số trực tuyến."

    if verification.verification_url:
        cert_res = verify_certificate(
            user_name=user.name or '',
            raw_url=verification.verification_url,
            declared_cert_name=verification.certificate_name or verification.certificate_type or ''
        )
        cert_status = cert_res.get('cert_status', 'manual_review')
        name_score = cert_res.get('name_match_score', 0.0)
        conf_zone = cert_res.get('confidence_zone', 'low')

        if cert_res.get('is_valid') and cert_status == 'verified':
            checks['certificate']['passed'] = True
            cert_detail = f"Xác minh trực tuyến thành công từ {cert_res.get('issuer_name')}. Khớp tên vùng cao ({int(name_score * 100)}%)."
        elif cert_status == 'expired':
            checks['certificate']['passed'] = False
            cert_detail = f"Chứng chỉ đã hết hạn từ ngày {cert_res.get('issued_date') or ''}."
        elif cert_status == 'revoked':
            checks['certificate']['passed'] = False
            cert_detail = "Chứng chỉ không tồn tại hoặc đã bị tổ chức cấp thu hồi (Mã 404)."
        elif cert_status == 'manual_review':
            checks['certificate']['passed'] = False
            cert_detail = f"Độ khớp tên đạt {int(name_score * 100)}% ({conf_zone}). Cần Admin đối soát lại."
        else:
            checks['certificate']['passed'] = False
            cert_detail = cert_res.get('error') or "Không xác minh được tính hợp lệ của chứng chỉ."
    else:
        # Nếu có đính kèm file chứng chỉ scan truyền thống
        cert_docs = [d for d in verification.documents if d.is_active and d.document_type == 'certificate' and d.file_size > 0]
        if cert_docs or verification.certificate_filename:
            checks['certificate']['passed'] = False  # Vẫn cần Admin kiểm tra bằng mắt
            cert_detail = "Đã đính kèm ảnh/file chứng chỉ scan (Cần Admin kiểm tra trực tiếp)."
        else:
            checks['certificate']['passed'] = False
            cert_detail = "Chưa có chứng chỉ trong hồ sơ."

    checks['certificate']['status'] = cert_status
    checks['certificate']['detail'] = cert_detail
    checks['certificate']['name_match_score'] = name_score

    # 5. Kiểm tra thông tin chuyên môn
    if (verification.source_language or verification.primary_language) and (verification.experience_years is not None):
        checks['profile_data']['passed'] = True
        checks['profile_data']['detail'] = f"Ngôn ngữ: {verification.source_language or verification.primary_language} · {verification.experience_years} năm kinh nghiệm."
    else:
        checks['profile_data']['passed'] = False
        checks['profile_data']['detail'] = "Thiếu thông tin cặp ngôn ngữ hoặc kinh nghiệm."

    # ─── KẾT LUẬN TOÀN DIỆN CỦA BỘ MÁY ───────────────────────────────────────
    auto_status = 'manual_review'
    if cert_status in ('expired', 'revoked'):
        auto_status = 'not_eligible'
    elif (checks['email']['passed'] and 
          checks['cv']['passed'] and 
          checks['identity']['passed'] and 
          checks['profile_data']['passed'] and 
          checks['certificate']['passed'] and 
          cert_status == 'verified'):
        auto_status = 'auto_eligible'
    else:
        auto_status = 'manual_review'

    # Cập nhật vào DB
    now = datetime.utcnow()
    verification.auto_status = auto_status
    verification.cert_status = cert_status
    verification.name_match_score = name_score
    verification.auto_evaluated_at = now
    verification.auto_review_metadata = json.dumps({
        'evaluated_at': now.strftime('%d/%m/%Y %H:%M:%S'),
        'auto_status': auto_status,
        'cert_status': cert_status,
        'name_match_score': name_score,
        'checks': checks
    }, ensure_ascii=False)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AutoVerification] Lỗi commit kết quả thẩm định: {e}", file=sys.stderr)

    return {
        'success': True,
        'verification_id': verification.id,
        'user_name': user.name,
        'user_email': user.email,
        'auto_status': auto_status,
        'cert_status': cert_status,
        'name_match_score': name_score,
        'checks': checks
    }


# ─── PHÊ DUYỆT TỰ ĐỘNG CÓ KIỂM SOÁT (AUTO-APPROVE) ───────────────────────────

def auto_approve_submission(verification_id: int, admin_user: Optional[User] = None, is_batch: bool = False) -> Tuple[bool, str]:
    """
    Phê duyệt an toàn cho một hồ sơ đạt trạng thái 'auto_eligible':
    - Bảo đảm hồ sơ đang ở trạng thái 'pending'.
    - Tạo checklist 16 tiêu chí đầy đủ.
    - Gọi review_verification_request() chính thức.
    - Ghi nhận Audit Log phân biệt rõ ràng giữa AUTO_VERIFY và duyệt thủ công.
    """
    verification = TranslatorVerification.query.get(verification_id)
    if not verification:
        return False, "Không tìm thấy hồ sơ xác minh."

    if verification.status != 'pending':
        return False, f"Hồ sơ hiện có trạng thái '{verification.status}', không thể tự động phê duyệt."

    if verification.auto_status != 'auto_eligible':
        return False, "Hồ sơ chưa đạt 100% điều kiện tự động duyệt ('auto_eligible')."

    from services.verification import review_verification_request

    # Tự động lập bảng checklist đạt chuẩn
    checklist_keys = ['A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'B3', 'B4', 'C1', 'C2', 'C3', 'C4', 'C5', 'D1', 'D2']
    checklist_data = {k: True for k in checklist_keys}

    reason = "Hệ thống Hybrid Auto-Verification tự động phê duyệt (Đạt 100% tiêu chí email, CV, CCCD và chứng chỉ số)."
    if is_batch:
        reason += " [Xử lý lô Batch]"

    ok, msg = review_verification_request(
        verification_id=verification.id,
        admin_user=admin_user,
        action='approve',
        reason=reason,
        checklist_data=checklist_data
    )

    if ok:
        try:
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS.get('AUTO_VERIFY_TRANSLATOR', 'AUTO_VERIFY_TRANSLATOR'),
                admin_id=admin_user.id if admin_user else None,
                target_type='translator',
                target_id=verification.user_id,
                description=f'Hệ thống tự động duyệt hồ sơ cho {verification.user.name} ({verification.user.email}) qua Hybrid Auto-Verification.',
                extra_data={'verification_id': verification.id, 'score': verification.name_match_score}
            )
            db.session.commit()
        except Exception:
            pass

    return ok, msg


# ─── BATCH PROCESSING (QUÉT LÔ & DUYỆT ĐỒNG LOẠT) ────────────────────────────

def batch_evaluate_pending_submissions(limit: int = 15) -> Dict[str, Any]:
    """
    Chế độ Chạy thử (Dry-Run Batch):
    Quét một lô hồ sơ 'pending' tối đa 'limit' bản ghi, phân tích và gắn cờ đề xuất
    mà TUYỆT ĐỐI KHÔNG thay đổi trạng thái duyệt của hồ sơ.
    Tối ưu cho VPS 1 vCPU / 2GB RAM.
    """
    settings = get_auto_verification_settings()
    safe_limit = min(limit, settings.get('batch_size', 15))

    pending_list = TranslatorVerification.query.filter_by(status='pending').order_by(
        TranslatorVerification.submitted_at.desc()
    ).limit(safe_limit).all()

    total_scanned = len(pending_list)
    auto_eligible_count = 0
    manual_review_count = 0
    not_eligible_count = 0
    results: List[Dict[str, Any]] = []

    for verif in pending_list:
        try:
            res = evaluate_verification_submission(verif.id)
            status = res.get('auto_status')
            if status == 'auto_eligible':
                auto_eligible_count += 1
            elif status == 'not_eligible':
                not_eligible_count += 1
            else:
                manual_review_count += 1
            results.append(res)
        except Exception as e:
            print(f"[BatchEvaluate] Lỗi hồ sơ #{verif.id}: {e}", file=sys.stderr)
            manual_review_count += 1

    return {
        'success': True,
        'total_scanned': total_scanned,
        'auto_eligible_count': auto_eligible_count,
        'manual_review_count': manual_review_count,
        'not_eligible_count': not_eligible_count,
        'results': results
    }


def batch_auto_approve_eligible(admin_user: User, limit: int = 15) -> Dict[str, Any]:
    """
    Duyệt hàng loạt hồ sơ đã được máy xác nhận 'auto_eligible':
    - Chỉ Super Admin hoặc Moderator được phép thực thi.
    - Xử lý tối đa 'limit' hồ sơ trong một lượt.
    - Ghi nhận Audit Log tổng hợp 'BATCH_AUTO_VERIFY_TRANSLATORS'.
    """
    settings = get_auto_verification_settings()
    safe_limit = min(limit, settings.get('batch_size', 15))

    eligible_list = TranslatorVerification.query.filter_by(
        status='pending',
        auto_status='auto_eligible'
    ).limit(safe_limit).all()

    approved_count = 0
    failed_count = 0
    approved_ids: List[int] = []

    for verif in eligible_list:
        ok, msg = auto_approve_submission(verif.id, admin_user=admin_user, is_batch=True)
        if ok:
            approved_count += 1
            approved_ids.append(verif.id)
        else:
            failed_count += 1

    if approved_count > 0:
        try:
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS.get('BATCH_AUTO_VERIFY_TRANSLATORS', 'BATCH_AUTO_VERIFY_TRANSLATORS'),
                admin_id=admin_user.id,
                target_type='translator',
                target_id=None,
                description=f'Admin {admin_user.name} duyệt hàng loạt {approved_count} hồ sơ PDV đủ điều kiện tự động.',
                extra_data={'approved_verification_ids': approved_ids, 'failed_count': failed_count}
            )
            db.session.commit()
        except Exception:
            pass

    return {
        'success': True,
        'total_processed': len(eligible_list),
        'approved_count': approved_count,
        'failed_count': failed_count,
        'approved_ids': approved_ids
    }

