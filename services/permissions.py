from flask import abort

def can_access_contract(user_id, contract):
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
    - Job open, approved & không bị cờ: Ai cũng được xem.
    - Job pending, flagged, rejected, etc.: Chỉ Chủ sở hữu và Admin hợp lệ mới được xem.
    """
    is_moderated = getattr(job, 'moderation_status', 'approved') == 'approved'
    if job.status == 'open' and not job.is_flagged and is_moderated:
        return True
        
    # Không thỏa mãn điều kiện công khai
    if current_user and current_user.id == job.hirer_id:
        return True
        
    from admin_auth import is_admin_session_valid
    admin_ok, _ = is_admin_session_valid()
    if admin_ok:
        return True
        
    return False
