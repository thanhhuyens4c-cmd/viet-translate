"""
services/account_security.py
Phân hệ Quản lý Bảo mật Tài khoản (Mục 5.6.2 & 5.6.3):
1. Đổi mật khẩu an toàn:
   - Tuân thủ cơ chế Authentication hiện có (werkzeug.security check_password_hash / generate_password_hash).
   - Kiểm tra mật khẩu cũ chính xác, trả về thông báo lỗi rõ ràng nếu sai.
   - Kiểm tra mật khẩu mới: tối thiểu 8 ký tự, có ít nhất một chữ cái in hoa (A-Z), có ít nhất một chữ số (0-9).
   - Xác nhận mật khẩu mới trùng khớp và không trùng mật khẩu cũ.
2. Quản lý phiên đăng nhập (UserSession):
   - Đăng ký và theo dõi phiên đăng nhập (User Agent, IP, thời gian hoạt động).
   - Phân định phiên hiện tại (is_current) và các thiết bị khác.
   - Thu hồi/Hủy phiên đăng nhập thực sự ở backend:
     + Đăng xuất khỏi thiết bị này (hủy token hiện tại hoặc token thiết bị chỉ định).
     + Đăng xuất tất cả thiết bị khác (xóa toàn bộ token của các thiết bị khác trong DB).
"""

import re
import secrets
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, UserSession, User


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """
    Validate mật khẩu mới theo tiêu chuẩn bảo mật:
    - Tối thiểu 8 ký tự.
    - Chứa ít nhất một chữ cái in hoa (A-Z).
    - Chứa ít nhất một chữ số (0-9).
    """
    if not password or len(password) < 8:
        return False, "Mật khẩu mới phải có tối thiểu 8 ký tự."
    
    if not re.search(r'[A-Z]', password):
        return False, "Mật khẩu mới phải chứa ít nhất một chữ cái in hoa (A-Z)."
        
    if not re.search(r'\d', password):
        return False, "Mật khẩu mới phải chứa ít nhất một chữ số (0-9)."
        
    return True, ""


def hash_password(password: str) -> str:
    """Hash mật khẩu an toàn theo cơ chế hiện tại của dự án (pbkdf2:sha256 qua werkzeug)."""
    try:
        return generate_password_hash(password, method='pbkdf2:sha256')
    except TypeError:
        return generate_password_hash(password)


def change_user_password(user, old_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
    """
    Xử lý đổi mật khẩu cho người dùng:
    - Kiểm tra mật khẩu cũ qua đúng Auth provider hiện tại (check_password_hash).
    - Validate mật khẩu mới và xác nhận mật khẩu.
    - Cập nhật password_hash và lưu cơ sở dữ liệu.
    """
    if not user:
        return False, "Không tìm thấy thông tin tài khoản người dùng."

    if not old_password:
        return False, "Vui lòng nhập mật khẩu hiện tại."

    if not new_password:
        return False, "Vui lòng nhập mật khẩu mới."

    if not confirm_password:
        return False, "Vui lòng xác nhận lại mật khẩu mới."

    # 1. Kiểm tra mật khẩu cũ qua đúng Auth provider hiện tại
    if not check_password_hash(user.password_hash, old_password):
        return False, "Mật khẩu hiện tại không chính xác. Vui lòng kiểm tra lại."

    # 2. Kiểm tra xác nhận mật khẩu
    if new_password != confirm_password:
        return False, "Xác nhận mật khẩu mới không trùng khớp."

    # 3. Kiểm tra không trùng mật khẩu cũ
    if check_password_hash(user.password_hash, new_password):
        return False, "Mật khẩu mới không được trùng với mật khẩu hiện tại."

    # 4. Kiểm tra độ phức tạp của mật khẩu mới
    is_valid, err_msg = validate_password_complexity(new_password)
    if not is_valid:
        return False, err_msg

    # 5. Cập nhật password_hash bằng đúng provider
    try:
        user.password_hash = hash_password(new_password)
        db.session.commit()

        # Tạo thông báo bảo mật gửi cho người dùng
        try:
            from models import Notification
            notif = Notification(
                user_id=user.id,
                type='SECURITY_ALERT',
                title='Mật khẩu tài khoản đã được thay đổi',
                message='Mật khẩu tài khoản VietTranslate của bạn vừa được cập nhật thành công. Nếu bạn không thực hiện hành động này, vui lòng liên hệ Ban quản trị ngay.',
                url='/account/profile?tab=security'
            )
            db.session.add(notif)
            db.session.commit()
        except Exception:
            pass

        return True, "Đổi mật khẩu thành công! Mật khẩu mới đã được cập nhật an toàn."
    except Exception as e:
        db.session.rollback()
        return False, f"Lỗi hệ thống khi cập nhật mật khẩu: {str(e)}"


def parse_device_name(req) -> str:
    """
    Phân tích User-Agent để xác định tên thiết bị và trình duyệt thân thiện.
    Ví dụ: 'Chrome trên macOS', 'Safari trên iPhone', 'Edge trên Windows'.
    """
    if not req:
        return "Trình duyệt Web"

    ua_str = ""
    if hasattr(req, 'headers') and req.headers:
        ua_str = req.headers.get('User-Agent', '')
    elif isinstance(req, str):
        ua_str = req

    if not ua_str:
        return "Trình duyệt Web"

    ua_lower = ua_str.lower()

    # 1. Xác định Hệ điều hành / Nền tảng
    os_name = "Thiết bị không xác định"
    if "iphone" in ua_lower:
        os_name = "iPhone"
    elif "ipad" in ua_lower:
        os_name = "iPad"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "linux" in ua_lower:
        os_name = "Linux"

    # 2. Xác định Trình duyệt
    browser_name = "Trình duyệt"
    if "edg/" in ua_lower or "edge/" in ua_lower:
        browser_name = "Edge"
    elif "chrome/" in ua_lower and "edg/" not in ua_lower and "opr/" not in ua_lower:
        browser_name = "Chrome"
    elif "safari/" in ua_lower and "chrome/" not in ua_lower:
        browser_name = "Safari"
    elif "firefox/" in ua_lower:
        browser_name = "Firefox"
    elif "opr/" in ua_lower or "opera/" in ua_lower:
        browser_name = "Opera"

    return f"{browser_name} trên {os_name}"


def get_client_ip(req) -> str:
    """Lấy địa chỉ IP chính xác của client, hỗ trợ proxy headers (X-Forwarded-For)."""
    if not req:
        return "127.0.0.1"

    if hasattr(req, 'headers') and req.headers:
        forwarded = req.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()

    if hasattr(req, 'remote_addr') and req.remote_addr:
        return req.remote_addr

    return "127.0.0.1"


def register_user_session(user, req, session_token: str = None) -> UserSession:
    """
    Đăng ký hoặc cập nhật phiên đăng nhập (UserSession) trong cơ sở dữ liệu.
    Lưu token phiên vào Flask session['session_token'].
    """
    from flask import session as flask_session

    if not user:
        return None

    token = session_token or flask_session.get('session_token') or secrets.token_urlsafe(32)
    flask_session['session_token'] = token

    device_name = parse_device_name(req)
    ip_addr = get_client_ip(req)

    try:
        user_sess = UserSession.query.filter_by(user_id=user.id, session_id=token).first()
        now = datetime.utcnow()

        if user_sess:
            user_sess.device_name = device_name
            user_sess.ip_address = ip_addr
            user_sess.last_active = now
            user_sess.is_current = True
        else:
            # Hủy cờ is_current của các phiên khác trong DB đối với user này nếu có
            UserSession.query.filter_by(user_id=user.id).update({'is_current': False})
            user_sess = UserSession(
                user_id=user.id,
                session_id=token,
                device_name=device_name,
                ip_address=ip_addr,
                last_active=now,
                is_current=True,
                created_at=now
            )
            db.session.add(user_sess)

        db.session.commit()
        return user_sess
    except Exception:
        db.session.rollback()
        return None


def get_active_sessions(user, current_session_token: str = None) -> list[dict]:
    """
    Lấy danh sách phiên đăng nhập của người dùng từ bảng UserSession,
    kèm định dạng thời gian và cờ đánh dấu phiên hiện tại.
    """
    if not user:
        return []

    try:
        sessions = UserSession.query.filter_by(user_id=user.id).order_by(UserSession.last_active.desc()).all()
    except Exception:
        db.session.rollback()
        return []

    results = []

    for s in sessions:
        is_cur = bool(current_session_token and s.session_id == current_session_token) or (not current_session_token and s.is_current)
        results.append(s.to_dict(current_session_token=current_session_token))

    return results


def revoke_user_session(user_id: int, target_identifier, current_token: str = None) -> tuple[bool, str, bool]:
    """
    Thu hồi một phiên làm việc cụ thể ở backend (xóa bản ghi khỏi UserSession).
    - target_identifier: Có thể là UserSession.id (int) hoặc session_id (str token).
    - Trả về: (success: bool, message: str, is_current_session: bool)
    """
    sess = None
    target_str = str(target_identifier).strip() if target_identifier is not None else ""

    if target_str.isdigit():
        sess = UserSession.query.filter_by(user_id=user_id, id=int(target_str)).first()

    if not sess and target_str:
        sess = UserSession.query.filter_by(user_id=user_id, session_id=target_str).first()

    if not sess:
        return False, "Phiên đăng nhập không tồn tại hoặc đã bị thu hồi trước đó.", False

    is_current = bool(current_token and sess.session_id == current_token) or sess.is_current

    try:
        db.session.delete(sess)
        db.session.commit()
        return True, "Đã thu hồi phiên đăng nhập thành công.", is_current
    except Exception as e:
        db.session.rollback()
        return False, f"Lỗi hệ thống khi thu hồi phiên: {str(e)}", is_current


def revoke_all_other_sessions(user_id: int, current_token: str = None) -> tuple[bool, str, int]:
    """
    Thu hồi và đăng xuất tất cả các thiết bị khác ở backend.
    Giữ lại duy nhất phiên hiện tại (trùng current_token).
    - Trả về: (success: bool, message: str, revoked_count: int)
    """
    try:
        query = UserSession.query.filter(UserSession.user_id == user_id)
        if current_token:
            query = query.filter(UserSession.session_id != current_token)
        else:
            # Nếu không có token phiên hiện tại, giữ lại phiên có thời gian last_active mới nhất
            latest = UserSession.query.filter_by(user_id=user_id).order_by(UserSession.last_active.desc()).first()
            if latest:
                query = query.filter(UserSession.id != latest.id)

        other_sessions = query.all()
        count = len(other_sessions)

        for s in other_sessions:
            db.session.delete(s)

        db.session.commit()
        return True, f"Đã thu hồi thành công {count} phiên đăng nhập trên các thiết bị khác.", count
    except Exception as e:
        db.session.rollback()
        return False, f"Lỗi hệ thống khi thu hồi các phiên: {str(e)}", 0
