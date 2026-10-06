"""
admin_auth.py — Hệ thống xác thực và bảo mật Admin cho VietTranslate.

Nguyên tắc:
- Tách biệt hoàn toàn Admin session khỏi User session.
- Mọi kiểm tra quyền đều phải ở server-side, không bao giờ tin client.
- Không lưu password, session secret, hay thông tin nhạy cảm vào Audit Log.
- Default-deny: nếu nghi ngờ → từ chối.
"""

import os
import secrets
import hashlib
from functools import wraps
from datetime import datetime, timedelta

from flask import (
    session, request, redirect, url_for,
    flash, abort, g
)
from sqlalchemy.exc import SQLAlchemyError

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

# Key phân biệt Admin session với User session
ADMIN_SESSION_KEY = 'admin_id'
ADMIN_SESSION_ROLE = 'admin_role'
ADMIN_SESSION_CSRF = 'admin_csrf_token'
ADMIN_SESSION_CREATED = 'admin_session_created'
ADMIN_SESSION_LAST_SEEN = 'admin_session_last_seen'

# Session Admin hết hạn sau 2 giờ không hoạt động
ADMIN_SESSION_TIMEOUT_SECONDS = 2 * 60 * 60  # 2 hours

# Cho phép tối đa N phút bất hoạt
ADMIN_IDLE_TIMEOUT_SECONDS = 30 * 60  # 30 phút

# Roles hợp lệ
ADMIN_ROLES = ('super_admin', 'moderator', 'support', 'finance')

# Mapping quyền theo role
ROLE_PERMISSIONS = {
    'super_admin': {'*'},  # Toàn quyền
    'moderator': {
        'view_dashboard', 'view_users', 'view_translators', 'verify_translator',
        'reject_translator', 'view_jobs', 'approve_job', 'reject_job',
        'flag_job', 'unflag_job', 'view_reports', 'resolve_report',
        'reject_report', 'view_reviews', 'hide_review', 'restore_review',
        'view_proposals', 'view_contracts', 'view_schedules', 'view_audit_logs',
        'view_notifications',
    },
    'finance': {
        'view_dashboard', 'view_payments', 'refund_payment', 'view_contracts',
        'view_proposals', 'view_notifications',
    },
    'support': {
        'view_dashboard', 'view_users', 'view_translators', 'view_jobs',
        'view_reports', 'view_reviews', 'view_contracts', 'view_notifications',
        'lock_user', 'unlock_user', 'view_proposals', 'view_schedules', 'resolve_report', 'reject_report', 'view_audit_logs',
    }
}


# ─── IP HELPER ────────────────────────────────────────────────────────────────

def get_client_ip():
    """Lấy IP thực của client, xem xét X-Forwarded-For."""
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        # Lấy IP đầu tiên trong chain (IP thực của client)
        return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'


# ─── CSRF PROTECTION ──────────────────────────────────────────────────────────

def generate_csrf_token():
    """Tạo CSRF token mới và lưu vào Admin session."""
    token = secrets.token_hex(32)
    session[ADMIN_SESSION_CSRF] = token
    return token


def get_csrf_token():
    """Lấy CSRF token hiện tại, tạo mới nếu chưa có."""
    if ADMIN_SESSION_CSRF not in session:
        return generate_csrf_token()
    return session[ADMIN_SESSION_CSRF]


def validate_csrf_token(token):
    """
    So sánh CSRF token an toàn (constant-time comparison).
    Trả về True nếu hợp lệ.
    """
    stored = session.get(ADMIN_SESSION_CSRF)
    if not stored or not token:
        return False
    return secrets.compare_digest(str(stored), str(token))


def csrf_protected(f):
    """
    Decorator: kiểm tra CSRF token cho tất cả POST/PUT/DELETE requests.
    Áp dụng cho mọi route Admin thay đổi dữ liệu.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = (
                request.form.get('_csrf_token') or
                request.headers.get('X-CSRF-Token') or
                request.headers.get('X-CSRFToken')
            )
            if not validate_csrf_token(token):
                # Ghi audit log trước khi từ chối
                try:
                    from models import AdminAuditLog, db
                    AdminAuditLog.log(
                        action='CSRF_VIOLATION',
                        admin_id=session.get(ADMIN_SESSION_KEY),
                        description='CSRF token không hợp lệ hoặc bị thiếu.',
                        ip_address=get_client_ip(),
                        user_agent=request.headers.get('User-Agent', '')[:512],
                    )
                    db.session.commit()
                except Exception:
                    pass
                abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── SESSION MANAGEMENT ───────────────────────────────────────────────────────

def create_admin_session(user):
    """
    Khởi tạo Admin session an toàn sau khi xác thực thành công.
    - Không đụng vào user session ('user_id').
    - Rotate session ID bằng cách clear và tạo lại.
    - Đặt timeout riêng cho Admin.
    """
    # Xóa toàn bộ session cũ để tránh session fixation
    session.clear()

    now_ts = datetime.utcnow().timestamp()
    session[ADMIN_SESSION_KEY] = user.id
    session[ADMIN_SESSION_ROLE] = getattr(user, 'admin_role', None) or 'super_admin'
    session[ADMIN_SESSION_CREATED] = now_ts
    session[ADMIN_SESSION_LAST_SEEN] = now_ts
    session[ADMIN_SESSION_CSRF] = secrets.token_hex(32)
    session.permanent = True  # Dùng PERMANENT_SESSION_LIFETIME
    session.modified = True


def destroy_admin_session():
    """Hủy Admin session hoàn toàn."""
    # Xóa sạch tất cả key liên quan đến Admin
    for key in (ADMIN_SESSION_KEY, ADMIN_SESSION_ROLE, ADMIN_SESSION_CSRF,
                ADMIN_SESSION_CREATED, ADMIN_SESSION_LAST_SEEN):
        session.pop(key, None)
    session.modified = True


def is_admin_session_valid():
    """
    Kiểm tra Admin session có còn hợp lệ không:
    1. Phải có admin_id trong session.
    2. Thời gian tạo session không quá ADMIN_SESSION_TIMEOUT_SECONDS.
    3. Thời gian idle không quá ADMIN_IDLE_TIMEOUT_SECONDS.
    Trả về (is_valid: bool, reason: str).
    """
    admin_id = session.get(ADMIN_SESSION_KEY)
    if not admin_id:
        return False, 'no_session'

    now_ts = datetime.utcnow().timestamp()
    created = session.get(ADMIN_SESSION_CREATED, 0)
    last_seen = session.get(ADMIN_SESSION_LAST_SEEN, 0)

    # Kiểm tra session tuyệt đối (từ lúc tạo)
    if now_ts - created > ADMIN_SESSION_TIMEOUT_SECONDS:
        return False, 'session_expired'

    # Kiểm tra idle timeout
    if now_ts - last_seen > ADMIN_IDLE_TIMEOUT_SECONDS:
        return False, 'idle_timeout'

    return True, 'ok'


def refresh_admin_session():
    """Cập nhật last_seen timestamp để tránh idle timeout."""
    session[ADMIN_SESSION_LAST_SEEN] = datetime.utcnow().timestamp()
    session.modified = True


# ─── GET CURRENT ADMIN ────────────────────────────────────────────────────────

def get_current_admin():
    """
    Lấy User object của Admin đang đăng nhập.
    LUÔN query lại từ database — không tin session value.
    Trả về User hoặc None.
    """
    admin_id = session.get(ADMIN_SESSION_KEY)
    if not admin_id:
        return None
    try:
        from models import User
        user = User.query.get(admin_id)
        # Xác minh lại server-side: phải là admin và còn active
        if user and user.is_admin and user.is_active:
            return user
        return None
    except SQLAlchemyError as e:
        print(f'[ADMIN AUTH] DB error in get_current_admin: {e}')
        return None


# ─── DECORATORS ───────────────────────────────────────────────────────────────

def admin_login_required(f):
    """
    Decorator: yêu cầu Admin đăng nhập hợp lệ.
    - Anonymous → /admin/login
    - User thường (không is_admin) → 403
    - Session hết hạn → /admin/login với thông báo
    - Admin session hợp lệ → tiếp tục, refresh last_seen
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Kiểm tra session validity
        valid, reason = is_admin_session_valid()
        if not valid:
            destroy_admin_session()
            if reason in ('session_expired', 'idle_timeout'):
                flash('Phiên làm việc Admin đã hết hạn. Vui lòng đăng nhập lại.', 'warning')
            return redirect(url_for('admin_login'))

        # 2. Verify từ database — không tin session is_admin
        admin = get_current_admin()
        if admin is None:
            destroy_admin_session()
            flash('Không tìm thấy tài khoản Admin hoặc tài khoản đã bị vô hiệu hóa.', 'error')
            return redirect(url_for('admin_login'))

        # 3. Lưu admin vào g để dùng trong request
        g.current_admin = admin
        g.admin_role = session.get(ADMIN_SESSION_ROLE, 'moderator')
        g.csrf_token = get_csrf_token()

        # 4. Refresh idle timer
        refresh_admin_session()

        return f(*args, **kwargs)
    return decorated


def require_permission(permission):
    """
    Decorator: kiểm tra Admin có quyền cụ thể không.
    Phải dùng sau @admin_login_required.

    Ví dụ:
        @admin_login_required
        @require_permission('verify_translator')
        def admin_verify_translator(profile_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = getattr(g, 'admin_role', None)
            if not _has_permission(role, permission):
                # Ghi audit log cho unauthorized access attempt
                try:
                    from models import AdminAuditLog, db
                    AdminAuditLog.log(
                        action='UNAUTHORIZED_ACCESS',
                        admin_id=session.get(ADMIN_SESSION_KEY),
                        description=f'Cố truy cập [{permission}] nhưng không có quyền. Role: {role}.',
                        ip_address=get_client_ip(),
                        user_agent=request.headers.get('User-Agent', '')[:512],
                    )
                    db.session.commit()
                except Exception:
                    pass
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def _has_permission(role, permission):
    """Kiểm tra role có quyền permission không."""
    if not role:
        return False
    perms = ROLE_PERMISSIONS.get(role, set())
    return '*' in perms or permission in perms


# ─── AUDIT LOG HELPER ─────────────────────────────────────────────────────────

def audit_log(action, target_type=None, target_id=None, description=None, extra_data=None):
    """
    Ghi Audit Log cho hành động Admin hiện tại.
    Tự động lấy admin_id, ip, user_agent từ request context.

    Cách dùng:
        audit_log('FLAG_JOB', target_type='job', target_id=job.id,
                  description=f'Gắn cờ vi phạm job "{job.title}"')
        db.session.commit()
    """
    try:
        from models import AdminAuditLog
        admin_id = session.get(ADMIN_SESSION_KEY)
        return AdminAuditLog.log(
            action=action,
            admin_id=admin_id,
            target_type=target_type,
            target_id=target_id,
            description=description,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:512],
            extra_data=extra_data,
        )
    except Exception as e:
        print(f'[AUDIT LOG ERROR] {e}')
        return None


# ─── CONTEXT PROCESSOR ────────────────────────────────────────────────────────

def inject_admin_globals():
    """
    Context processor cho tất cả Admin templates.
    Inject: current_admin, admin_role, csrf_token, admin_session_info.
    """
    current_admin = getattr(g, 'current_admin', None)
    admin_role = getattr(g, 'admin_role', None)
    csrf_token = getattr(g, 'csrf_token', get_csrf_token())
    return dict(
        current_admin=current_admin,
        admin_role=admin_role,
        admin_csrf_token=csrf_token,
        has_permission=lambda perm: _has_permission(admin_role, perm),
    )
