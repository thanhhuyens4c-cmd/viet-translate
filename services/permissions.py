from flask import abort

def can_access_contract(user_id, contract):
    from admin_auth import is_admin_session_valid
    admin_ok, _ = is_admin_session_valid()
    if admin_ok:
        return True
    if not user_id or not contract:
        return False
    return user_id in {
        contract.hirer_id,
        contract.translator_id
    }

def require_contract_access(user_id, contract):
    if not can_access_contract(user_id, contract):
        abort(403)

def can_view_profile(profile, current_user):
    """
    Xác định người dùng hiện tại có được phép xem profile này không.
    - Profile đã xác minh: Ai cũng được xem.
    - Profile chưa xác minh: Chỉ Chủ sở hữu và Admin hợp lệ mới được xem.
    """
    if profile.is_verified:
        return True
        
    # Chưa xác minh
    if current_user and current_user.id == profile.user_id:
        return True
        
    from admin_auth import is_admin_session_valid
    admin_ok, _ = is_admin_session_valid()
    if admin_ok:
        return True
        
    return False

def can_view_job(job, current_user):
    """
    Xác định người dùng hiện tại có được phép xem công việc này không.
    - Job open, approved, chưa đóng & không bị cờ: Ai cũng được xem.
    - Khách đăng tuyển, Admin hợp lệ, hoặc Phiên dịch viên đã nộp báo giá/có hợp đồng: Được xem.
    - Job pending, flagged, rejected, etc.: Chỉ Chủ sở hữu và Admin hợp lệ mới được xem.
    """
    is_moderated = getattr(job, 'moderation_status', 'approved') == 'approved'
    is_closed = (getattr(job, 'status', '') == 'closed') or (getattr(job, 'closed_at', None) is not None)
    
    if getattr(job, 'status', '') == 'open' and not getattr(job, 'is_flagged', False) and is_moderated and not is_closed:
        return True
        
    # Không thỏa mãn điều kiện công khai
    if current_user and getattr(current_user, 'id', None) == getattr(job, 'hirer_id', None):
        return True

    from admin_auth import is_admin_session_valid
    admin_ok, _ = is_admin_session_valid()
    if admin_ok:
        return True

    # Phiên dịch viên đã ứng tuyển hoặc có hợp đồng vẫn được xem job đã đóng/chốt
    if current_user and getattr(current_user, 'role', '') == 'translator' and getattr(current_user, 'id', None):
        try:
            from models import Proposal, Contract
            has_record = (
                Proposal.query.filter_by(job_id=job.id, translator_id=current_user.id).first() is not None or
                Contract.query.filter_by(job_id=job.id, translator_id=current_user.id).first() is not None
            )
            if has_record:
                return True
        except Exception:
            pass
        
    return False

