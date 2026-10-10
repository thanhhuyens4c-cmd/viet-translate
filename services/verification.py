import os
import sys
import time
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from models import (
    db, User, TranslatorProfile, TranslatorVerification,
    AdminNotification, Notification, ADMIN_AUDIT_ACTIONS, AdminAuditLog
)

ALLOWED_VERIFICATION_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'webp'}
MAX_VERIFICATION_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_verification_file(filename):
    """Kiểm tra phần mở rộng tệp hợp lệ cho tài liệu xác minh."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VERIFICATION_EXTENSIONS


def get_verification_upload_folder():
    """Trả về thư mục lưu trữ tài liệu xác minh cục bộ."""
    if os.environ.get('VERCEL') == '1':
        folder = '/tmp/verifications'
    else:
        folder = os.path.join('static', 'uploads', 'verifications')
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = '/tmp'
    return folder


def save_verification_file(file_storage, user_id, doc_type='doc'):
    """
    Lưu tệp tài liệu xác minh (CV, chứng chỉ, CCCD).
    Ưu tiên lưu trữ an toàn, hỗ trợ Supabase Storage nếu khả dụng hoặc local file.
    Trả về: (thành_công, tên_file, url, thông_báo_lỗi)
    """
    if not file_storage or not file_storage.filename:
        return False, None, None, 'Tệp tải lên không hợp lệ.'

    if not allowed_verification_file(file_storage.filename):
        return False, None, None, 'Định dạng tệp không được hỗ trợ. Vui lòng chọn PDF, DOC, DOCX, JPG hoặc PNG.'

    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
    except Exception:
        size = 0

    if size > MAX_VERIFICATION_FILE_SIZE:
        return False, None, None, 'Kích thước tệp vượt quá giới hạn cho phép (tối đa 10MB).'

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    clean_uid = str(user_id).replace('mongo:', 'm_')
    random_suffix = secrets.token_hex(4)
    filename = f"{doc_type}_u{clean_uid}_{int(time.time())}_{random_suffix}.{ext}"

    # Kiểm tra Supabase Storage (nếu được cấu hình bucket 'verifications')
    supabase_uploaded = False
    supabase_url = None
    try:
        from supabase_client import get_supabase_client
        sb = get_supabase_client()
        if sb:
            file_bytes = file_storage.read()
            file_storage.seek(0)
            res = sb.storage.from_('verifications').upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": file_storage.mimetype}
            )
            if res:
                supabase_url = sb.storage.from_('verifications').get_public_url(filename)
                supabase_uploaded = True
    except Exception as e:
        # Fallback về lưu local
        supabase_uploaded = False

    # Lưu bản copy cục bộ để đảm bảo phục vụ được ngay cả khi offline
    upload_folder = get_verification_upload_folder()
    local_path = os.path.join(upload_folder, filename)
    try:
        file_storage.save(local_path)
    except Exception as e:
        print(f"[VERIFICATION UPLOAD ERROR] Local save failed: {e}", file=sys.stderr)
        if not supabase_uploaded:
            return False, None, None, 'Không thể lưu tệp trên máy chủ. Vui lòng thử lại.'

    final_url = supabase_url if supabase_uploaded else f"/static/uploads/verifications/{filename}"
    return True, filename, final_url, None


def submit_verification_request(user, form_data, files):
    """
    Xử lý nộp hồ sơ xác minh từ phiên dịch viên.
    Tự động cập nhật bản ghi cũ hoặc tạo mới nếu chưa có.
    """
    if not user or user.role != 'translator':
        return False, 'Chỉ tài khoản phiên dịch viên mới có thể nộp hồ sơ xác minh.'

    profile = user.profile
    if not profile:
        profile = TranslatorProfile(user_id=user.id)
        db.session.add(profile)
        db.session.flush()

    # Lấy bản ghi xác minh hiện có hoặc tạo mới
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    is_new = False
    if not verification:
        verification = TranslatorVerification(user_id=user.id)
        db.session.add(verification)
        is_new = True

    # Xử lý tệp CV
    cv_file = files.get('cv_file')
    if cv_file and cv_file.filename:
        ok, fname, furl, err = save_verification_file(cv_file, user.id, doc_type='cv')
        if not ok:
            return False, err
        verification.cv_filename = fname
        verification.cv_url = furl
    elif is_new or not verification.cv_url:
        return False, 'Vui lòng tải lên sơ yếu lý lịch (CV) định dạng PDF hoặc Word.'

    # Xử lý tệp Chứng chỉ
    cert_file = files.get('certificate_file')
    if cert_file and cert_file.filename:
        ok, fname, furl, err = save_verification_file(cert_file, user.id, doc_type='cert')
        if not ok:
            return False, err
        verification.certificate_filename = fname
        verification.certificate_url = furl

    # Xử lý tệp CCCD / Giấy tờ tùy thân (Tùy chọn)
    id_card_file = files.get('id_card_file')
    if id_card_file and id_card_file.filename:
        ok, fname, furl, err = save_verification_file(id_card_file, user.id, doc_type='idcard')
        if not ok:
            return False, err
        verification.id_card_filename = fname
        verification.id_card_url = furl

    # Các thông tin biểu mẫu
    verification.certificate_type = form_data.get('certificate_type', '').strip()
    verification.certificate_name = form_data.get('certificate_name', '').strip()
    verification.primary_language = form_data.get('primary_language', '').strip()

    try:
        verification.experience_years = int(form_data.get('experience_years') or 0)
    except ValueError:
        verification.experience_years = 0

    verification.notes = form_data.get('notes', '').strip()
    verification.status = 'pending'
    verification.rejection_reason = None
    verification.reviewed_by = None
    verification.reviewed_at = None
    verification.updated_at = datetime.utcnow()

    # Thông báo cho Ban quản trị (Admin)
    try:
        admin_notif = AdminNotification(
            type='NEW_TRANSLATOR',
            title='Yêu cầu xác minh hồ sơ mới',
            message=f'Phiên dịch viên {user.name} ({user.email}) vừa nộp hồ sơ xác minh năng lực.',
            url='/admin/translators?show=pending',
            related_id=verification.id
        )
        db.session.add(admin_notif)
    except Exception as e:
        print(f"[VERIFICATION NOTIF ERROR] {e}", file=sys.stderr)

    db.session.commit()
    return True, 'Hồ sơ xác minh đã được gửi thành công! Ban quản trị sẽ xét duyệt trong vòng 24–48 giờ.'


def review_verification_request(verification_id, admin_user, action, reason=None, ip_address=None, user_agent=None):
    """
    Ban quản trị duyệt (approve) hoặc từ chối (reject) yêu cầu xác minh.
    Đồng bộ trạng thái TranslatorProfile.is_verified, gửi thông báo và ghi Audit Log.
    """
    verification = TranslatorVerification.query.get(verification_id)
    if not verification:
        return False, 'Không tìm thấy hồ sơ xác minh.'

    user = verification.user
    profile = user.profile if user else None
    if not profile and user:
        profile = TranslatorProfile(user_id=user.id)
        db.session.add(profile)

    now = datetime.utcnow()
    verification.reviewed_by = admin_user.id if admin_user else None
    verification.reviewed_at = now

    if action == 'approve':
        verification.status = 'approved'
        verification.rejection_reason = None
        if profile:
            profile.is_verified = True

        # Gửi thông báo cho phiên dịch viên
        try:
            notif = Notification(
                user_id=user.id,
                type='VERIFICATION_APPROVED',
                title='Hồ sơ đã được xác minh thành công! 🎉',
                message='Chúc mừng bạn! Hồ sơ phiên dịch viên của bạn đã được xác minh chính thức. Huy hiệu uy tín đã xuất hiện trên trang cá nhân.',
                url='/account/profile?tab=verification'
            )
            db.session.add(notif)
        except Exception as e:
            print(f"[NOTIF ERROR] {e}", file=sys.stderr)

        # Ghi Audit Log
        try:
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS.get('VERIFY_TRANSLATOR', 'VERIFY_TRANSLATOR'),
                admin_id=admin_user.id if admin_user else None,
                target_type='translator',
                target_id=profile.id if profile else user.id,
                description=f'Phê duyệt xác minh hồ sơ cho phiên dịch viên {user.name} ({user.email}).',
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'verification_id': verification.id, 'certificate': verification.certificate_name}
            )
        except Exception as e:
            print(f"[AUDIT LOG ERROR] {e}", file=sys.stderr)

        db.session.commit()
        return True, f'Đã phê duyệt xác minh cho {user.name}.'

    elif action == 'reject':
        rejection_reason = (reason or 'Hồ sơ chưa đạt yêu cầu xác minh. Vui lòng kiểm tra lại tài liệu đã tải lên.').strip()
        verification.status = 'rejected'
        verification.rejection_reason = rejection_reason
        if profile:
            profile.is_verified = False

        # Gửi thông báo cho phiên dịch viên kèm lý do
        try:
            notif = Notification(
                user_id=user.id,
                type='VERIFICATION_REJECTED',
                title='Hồ sơ xác minh chưa được phê duyệt',
                message=f'Hồ sơ của bạn chưa được duyệt với lý do: "{rejection_reason}". Bạn có thể cập nhật tài liệu và nộp lại.',
                url='/account/profile?tab=verification'
            )
            db.session.add(notif)
        except Exception as e:
            print(f"[NOTIF ERROR] {e}", file=sys.stderr)

        # Ghi Audit Log
        try:
            AdminAuditLog.log(
                action=ADMIN_AUDIT_ACTIONS.get('REJECT_TRANSLATOR', 'REJECT_TRANSLATOR'),
                admin_id=admin_user.id if admin_user else None,
                target_type='translator',
                target_id=profile.id if profile else user.id,
                description=f'Từ chối xác minh hồ sơ {user.name} ({user.email}). Lý do: {rejection_reason}',
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'verification_id': verification.id, 'reason': rejection_reason}
            )
        except Exception as e:
            print(f"[AUDIT LOG ERROR] {e}", file=sys.stderr)

        db.session.commit()
        return True, f'Đã từ chối xác minh hồ sơ của {user.name}.'

    return False, 'Hành động không hợp lệ.'
