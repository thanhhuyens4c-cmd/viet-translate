import os
import sys
import time
import secrets
import re
import json
import hashlib
import zipfile
import io
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from models import (
    db, User, TranslatorProfile, TranslatorVerification, VerificationDocument,
    AdminNotification, Notification, ADMIN_AUDIT_ACTIONS, AdminAuditLog,
    VerificationSubmissionVersion
)

# ─── POLICY CẤU HÌNH CÁC LOẠI TÀI LIỆU MINH CHỨNG ĐƯỢC PHÉP ───────────────────

DOCUMENT_POLICIES = {
    'cv': {
        'code': 'cv',
        'name': 'Sơ yếu lý lịch (CV / Resume)',
        'description': 'Bản tóm tắt học vấn, chứng chỉ và kinh nghiệm dự án dịch thuật.',
        'required': True,
        'allowed_extensions': {'pdf', 'doc', 'docx'},
        'allowed_mimes': {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'max_size_bytes': 10 * 1024 * 1024,  # 10MB
        'max_size_mb': 10,
        'magic_types': {'pdf', 'doc', 'docx'}
    },
    'certificate': {
        'code': 'certificate',
        'name': 'Bằng cấp / Chứng chỉ ngoại ngữ',
        'description': 'Bản scan hoặc ảnh chụp chứng chỉ (IELTS, JLPT, HSK, TOPIK, DELF, TestDaF...).',
        'required': False,
        'allowed_extensions': {'pdf', 'jpg', 'jpeg', 'png', 'webp'},
        'allowed_mimes': {
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/webp'
        },
        'max_size_bytes': 10 * 1024 * 1024,  # 10MB
        'max_size_mb': 10,
        'magic_types': {'pdf', 'jpeg', 'png', 'webp'}
    },
    'id_card': {
        'code': 'id_card',
        'name': 'Căn cước công dân / Hộ chiếu (CCCD)',
        'description': 'Tài liệu định danh cá nhân để xác minh danh tính. Được lưu trữ riêng tư tuyệt đối.',
        'required': False,
        'allowed_extensions': {'pdf', 'jpg', 'jpeg', 'png', 'webp'},
        'allowed_mimes': {
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/webp'
        },
        'max_size_bytes': 10 * 1024 * 1024,  # 10MB
        'max_size_mb': 10,
        'magic_types': {'pdf', 'jpeg', 'png', 'webp'}
    },
    'diploma': {
        'code': 'diploma',
        'name': 'Bằng tốt nghiệp Đại học / Cao đẳng',
        'description': 'Văn bằng cử nhân/thạc sĩ chuyên ngành biên phiên dịch hoặc ngoại ngữ.',
        'required': False,
        'allowed_extensions': {'pdf', 'jpg', 'jpeg', 'png', 'webp'},
        'allowed_mimes': {
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/webp'
        },
        'max_size_bytes': 10 * 1024 * 1024,  # 10MB
        'max_size_mb': 10,
        'magic_types': {'pdf', 'jpeg', 'png', 'webp'}
    },
    'recommendation': {
        'code': 'recommendation',
        'name': 'Thư giới thiệu / Hợp đồng dự án tiêu biểu',
        'description': 'Hợp đồng, thư giới thiệu hoặc xác nhận kinh nghiệm từ các đối tác, khách hàng.',
        'required': False,
        'allowed_extensions': {'pdf', 'doc', 'docx'},
        'allowed_mimes': {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'max_size_bytes': 10 * 1024 * 1024,  # 10MB
        'max_size_mb': 10,
        'magic_types': {'pdf', 'doc', 'docx'}
    }
}

ALLOWED_VERIFICATION_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'webp'}
MAX_VERIFICATION_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_document_type_label(doc_type):
    """Lấy tên hiển thị tiếng Việt của loại tài liệu."""
    policy = DOCUMENT_POLICIES.get(doc_type)
    return policy['name'] if policy else str(doc_type).upper()


def format_file_size(size_bytes):
    """Định dạng dung lượng tệp cho giao diện."""
    if not size_bytes or size_bytes <= 0:
        return '0 KB'
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def detect_file_type_from_bytes(data: bytes):
    """
    Xác định loại tệp thực tế dựa trên magic bytes (chữ ký nhị phân ở cấp máy chủ).
    Không tin tưởng vào phần mở rộng do người dùng gửi lên.
    """
    if not data or len(data) < 4:
        return None
    # 1. PDF: %PDF-
    if data.startswith(b'%PDF-'):
        return 'pdf'
    # 2. PNG: \x89PNG\r\n\x1a\n
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    # 3. JPEG: \xff\xd8\xff
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    # 4. WEBP: RIFF....WEBP
    if data[:4] == b'RIFF' and len(data) >= 12 and data[8:12] == b'WEBP':
        return 'webp'
    # 5. Legacy DOC (OLE Compound File)
    if data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        return 'doc'
    # 6. Modern DOCX (Zip container containing Word XML)
    if data.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                if '[Content_Types].xml' in names or any(n.startswith('word/') for n in names):
                    return 'docx'
        except Exception:
            return None
    return None


def get_private_verification_folder():
    """
    Trả về đường dẫn thư mục lưu trữ riêng tư (Private Storage Folder).
    Nằm hoàn toàn ngoài thư mục static công khai.
    """
    configured = None
    try:
        configured = current_app.config.get('PRIVATE_STORAGE_FOLDER')
    except RuntimeError:
        pass
    if not configured:
        configured = os.environ.get('PRIVATE_STORAGE_FOLDER')
    if not configured:
        if os.environ.get('VERCEL') == '1':
            configured = '/tmp/private_verifications'
        else:
            basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            configured = os.path.join(basedir, 'instance', 'storage', 'private_verifications')

    try:
        os.makedirs(configured, exist_ok=True)
    except OSError:
        configured = '/tmp/private_verifications'
        os.makedirs(configured, exist_ok=True)
    return configured


def allowed_verification_file(filename):
    """Kiểm tra phần mở rộng tệp hợp lệ cho tài liệu xác minh."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VERIFICATION_EXTENSIONS


def can_user_access_document(user, document):
    """
    Kiểm tra quyền truy cập (xem / tải xuống) tài liệu xác minh:
    - Quản trị viên (admin): Được phép
    - Chính chủ sở hữu tài liệu (user.id == document.user_id): Được phép
    - Người khác: Từ chối (403)
    """
    if not user:
        return False, 'Vui lòng đăng nhập để truy cập tài liệu.'
    if getattr(user, 'role', '') == 'admin':
        return True, None
    if document.user_id == user.id:
        return True, None
    return False, 'Bạn không có quyền truy cập hoặc xem tài liệu riêng tư này.'


def can_user_modify_verification_documents(user, verification):
    """
    Kiểm tra xem người dùng có quyền tải lên / thay thế / xóa tài liệu
    dựa trên trạng thái hiện tại của hồ sơ xác minh:
    - Cho phép khi hồ sơ ở trạng thái 'draft', 'rejected', 'needs_revision', 'not_started' hoặc chưa có hồ sơ.
    - Chặn khi hồ sơ ở trạng thái 'pending' (đang được thẩm định) để bảo đảm tính toàn vẹn.
    - Chặn khi hồ sơ ở trạng thái 'approved' (đã duyệt thành công).
    """
    if not user or user.role != 'translator':
        return False, 'Chỉ phiên dịch viên mới có thể quản lý tài liệu xác minh.'
    if not verification:
        return True, None
    if verification.user_id != user.id and getattr(user, 'role', '') != 'admin':
        return False, 'Bạn không thể thao tác trên hồ sơ của người khác.'

    st = getattr(verification, 'status', 'draft') or 'draft'
    if st == 'pending':
        return False, 'Hồ sơ đang trong quá trình Ban quản trị thẩm định. Bạn không thể thay đổi tài liệu vào lúc này.'
    if st == 'approved':
        return False, 'Hồ sơ đã được phê duyệt xác minh chính thức. Tài liệu không thể tự ý thay đổi.'

    return True, None


def save_private_document(file_storage, user, doc_type, verification=None):
    """
    Lưu tài liệu minh chứng vào vùng lưu trữ riêng tư (Private Storage).
    Thực hiện kiểm tra nghiêm ngặt:
    - Kiểm tra loại tài liệu theo chính sách
    - Kiểm tra trạng thái hồ sơ xác minh
    - Kiểm tra loại tệp thực tế qua chữ ký nhị phân (magic bytes)
    - Kiểm tra kích thước tệp thực tế
    - Lưu metadata vào bảng VerificationDocument
    - Đánh dấu tài liệu cũ cùng loại là 'replaced'
    - Tuyệt đối không coi việc tải lên thành công là đã xác minh
    Trả về: (thành_công: bool, document: VerificationDocument, lỗi: str)
    """
    if not user or user.role != 'translator':
        return False, None, 'Chỉ tài khoản phiên dịch viên mới có quyền tải lên tài liệu minh chứng.'

    doc_type = (doc_type or '').strip().lower()
    # Chuẩn hóa alias cũ nếu có
    if doc_type in ('cert', 'certificate_file'):
        doc_type = 'certificate'
    elif doc_type in ('idcard', 'id_card_file'):
        doc_type = 'id_card'
    elif doc_type in ('cv_file',):
        doc_type = 'cv'

    policy = DOCUMENT_POLICIES.get(doc_type)
    if not policy:
        return False, None, f"Loại tài liệu '{doc_type}' không nằm trong chính sách hỗ trợ của VietTranslate."

    # Lấy hoặc tạo hồ sơ xác minh
    if not verification:
        verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
        if not verification:
            verification = TranslatorVerification(user_id=user.id, status='draft', current_step=1)
            db.session.add(verification)
            db.session.flush()

    can_mod, mod_err = can_user_modify_verification_documents(user, verification)
    if not can_mod:
        return False, None, mod_err

    if not file_storage or not file_storage.filename:
        return False, None, 'Vui lòng chọn tệp tài liệu để tải lên.'

    raw_filename = file_storage.filename.strip()
    if '.' not in raw_filename:
        return False, None, 'Tệp tải lên thiếu phần mở rộng (extension).'

    ext = raw_filename.rsplit('.', 1)[1].lower()
    if ext not in policy['allowed_extensions']:
        allowed_str = ', '.join([e.upper() for e in sorted(policy['allowed_extensions'])])
        return False, None, f"Định dạng .{ext} không được hỗ trợ cho {policy['name']}. Vui lòng chọn tệp: {allowed_str}."

    # Đọc dữ liệu nhị phân để kiểm tra dung lượng và chữ ký magic bytes
    try:
        file_bytes = file_storage.read()
        file_storage.seek(0)
    except Exception as e:
        return False, None, f"Lỗi đọc nội dung tệp: {str(e)}"

    size = len(file_bytes)
    if size == 0:
        return False, None, 'Tệp tải lên rỗng (0 bytes). Vui lòng chọn tệp có nội dung.'

    if size > policy['max_size_bytes']:
        max_mb = policy['max_size_mb']
        curr_mb = size / (1024 * 1024)
        return False, None, f"Kích thước tệp ({curr_mb:.2f} MB) vượt quá giới hạn cho phép ({max_mb} MB)."

    # KIỂM TRA CHỮ KÝ TỆP THỰC TẾ TRÊN MÁY CHỦ (MAGIC BYTES)
    detected_type = detect_file_type_from_bytes(file_bytes)
    if not detected_type:
        return False, None, f"Nội dung tệp thực tế không phải là định dạng an toàn hợp lệ (không vượt qua kiểm tra chữ ký nhị phân)."

    # Đối chiếu detected_type với chính sách
    type_matches = False
    if detected_type in policy['magic_types']:
        type_matches = True
    elif detected_type == 'jpeg' and ('jpg' in policy['magic_types'] or 'jpeg' in policy['magic_types']):
        type_matches = True

    if not type_matches:
        return False, None, f"Nội dung tệp thực tế ({detected_type.upper()}) không khớp với loại tài liệu yêu cầu hoặc phần mở rộng .{ext}."

    # Xác định MIME type
    mime_type = mimetypes.guess_type(raw_filename)[0] or 'application/octet-stream'
    if detected_type == 'pdf':
        mime_type = 'application/pdf'
    elif detected_type in ('jpeg', 'jpg'):
        mime_type = 'image/jpeg'
    elif detected_type == 'png':
        mime_type = 'image/png'
    elif detected_type == 'webp':
        mime_type = 'image/webp'
    elif detected_type == 'docx':
        mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif detected_type == 'doc':
        mime_type = 'application/msword'

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Sinh tên tệp ngẫu nhiên bảo mật (tránh lộ danh tính hoặc số CCCD)
    unique_token = secrets.token_hex(16)
    stored_filename = f"pdoc_{doc_type}_{unique_token}.{ext}"

    # Kiểm tra Supabase Storage nếu cấu hình bucket private
    supabase_stored = False
    supabase_key_path = None
    try:
        from supabase_client import get_supabase_client
        sb = get_supabase_client()
        if sb:
            res = sb.storage.from_('verification_documents').upload(
                path=stored_filename,
                file=file_bytes,
                file_options={"content-type": mime_type}
            )
            if res:
                supabase_stored = True
                supabase_key_path = f"verification_documents/{stored_filename}"
    except Exception:
        supabase_stored = False

    # Luôn lưu vào Private Local Storage (ngoài static)
    private_folder = get_private_verification_folder()
    local_path = os.path.join(private_folder, stored_filename)
    try:
        with open(local_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"[PRIVATE STORAGE ERROR] Failed to write file: {e}", file=sys.stderr)
        if not supabase_stored:
            return False, None, 'Không thể lưu trữ tệp trên vùng an toàn máy chủ. Vui lòng thử lại.'

    # Đánh dấu các tài liệu cũ của cùng doc_type là 'replaced' và is_active=False
    existing_active = VerificationDocument.query.filter_by(
        verification_id=verification.id,
        document_type=doc_type,
        is_active=True
    ).all()
    for old_doc in existing_active:
        old_doc.is_active = False
        old_doc.status = 'replaced'
        old_doc.updated_at = datetime.utcnow()

    # Tạo bản ghi mới cho VerificationDocument
    # LƯU Ý: Trạng thái mặc định là 'uploaded' - TUYỆT ĐỐI CHƯA PHẢI LÀ 'approved' HAY 'verified'
    new_doc = VerificationDocument(
        verification_id=verification.id,
        user_id=user.id,
        document_type=doc_type,
        original_filename=raw_filename,
        stored_filename=stored_filename,
        storage_provider='supabase_private' if supabase_stored else 'local_private',
        storage_path=supabase_key_path if supabase_stored else local_path,
        file_size=size,
        mime_type=mime_type,
        file_extension=ext,
        file_hash=file_hash,
        status='uploaded',
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(new_doc)
    db.session.flush()

    # Đồng bộ tương thích ngược vào TranslatorVerification
    doc_download_url = f"/account/verification/documents/{new_doc.id}/download"
    if doc_type == 'cv':
        verification.cv_filename = raw_filename
        verification.cv_url = doc_download_url
    elif doc_type == 'certificate':
        verification.certificate_filename = raw_filename
        verification.certificate_url = doc_download_url
    elif doc_type == 'id_card':
        verification.id_card_filename = raw_filename
        verification.id_card_url = doc_download_url

    verification.updated_at = datetime.utcnow()
    db.session.commit()

    return True, new_doc, None


def save_verification_file(file_storage, user_id, doc_type='doc'):
    """
    Hàm wrapper tương thích ngược: chuyển hướng toàn bộ quá trình lưu
    sang hệ thống Private Storage an toàn.
    """
    user = User.query.get(user_id)
    if not user:
        return False, None, None, 'Không tìm thấy người dùng.'
    # Chuẩn hóa loại doc_type
    dt = 'cv' if doc_type == 'cv' else ('certificate' if doc_type in ('cert', 'certificate') else ('id_card' if doc_type in ('idcard', 'id_card') else 'cv'))
    ok, doc, err = save_private_document(file_storage, user, doc_type=dt)
    if not ok:
        return False, None, None, err
    download_url = f"/account/verification/documents/{doc.id}/download"
    return True, doc.original_filename, download_url, None


def delete_private_document(doc_id, user):
    """
    Xóa tài liệu minh chứng khi hồ sơ còn ở trạng thái nháp hoặc cần sửa.
    """
    doc = VerificationDocument.query.get(doc_id)
    if not doc:
        return False, 'Không tìm thấy tài liệu.'

    can_access, acc_err = can_user_access_document(user, doc)
    if not can_access:
        return False, acc_err

    verification = doc.verification
    can_mod, mod_err = can_user_modify_verification_documents(user, verification)
    if not can_mod:
        return False, mod_err

    doc.is_active = False
    doc.status = 'deleted'

    if doc.storage_path and os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except OSError:
            pass

    if verification:
        download_marker = f"/account/verification/documents/{doc.id}/"
        if verification.cv_url and download_marker in verification.cv_url:
            verification.cv_url = None
            verification.cv_filename = None
        if verification.certificate_url and download_marker in verification.certificate_url:
            verification.certificate_url = None
            verification.certificate_filename = None
        if verification.id_card_url and download_marker in verification.id_card_url:
            verification.id_card_url = None
            verification.id_card_filename = None

    db.session.commit()
    return True, 'Đã xóa tài liệu minh chứng thành công.'


def validate_verification_eligibility(verification, additional_data=None, require_confirmation=True):
    """
    Kiểm tra toàn diện tính hợp lệ của hồ sơ trước khi gửi xét duyệt:
    1. Kiểm tra trạng thái hồ sơ: Không cho gửi lặp lại nếu đang pending hoặc đã approved.
    2. Kiểm tra dữ liệu bắt buộc của tất cả các bước (Bước 1 đến Bước 5).
    3. Kiểm tra tài liệu cần thiết theo chính sách (CV là tài liệu bắt buộc theo chính sách).
    4. Kiểm tra sự xác nhận cam kết trung thực từ phía người dùng.
    
    Trả về: (is_eligible: bool, errors_dict: dict[str, str], error_messages: list[str])
    """
    errors_dict = {}
    error_messages = []

    if not verification:
        return False, {'verification': 'Chưa khởi tạo hồ sơ.'}, ['Không tìm thấy hồ sơ xác minh để kiểm tra.']

    # Kiểm tra trạng thái
    st = getattr(verification, 'status', 'draft') or 'draft'
    if st == 'pending':
        errors_dict['status'] = 'Hồ sơ đang trong quá trình Ban quản trị thẩm định, không thể gửi lặp lại.'
        error_messages.append('Hồ sơ của bạn đã được gửi trước đó và đang trong hàng đợi xử lý của Ban quản trị.')
        return False, errors_dict, error_messages
    elif st == 'approved':
        errors_dict['status'] = 'Hồ sơ đã được phê duyệt xác minh chính thức.'
        error_messages.append('Hồ sơ của bạn đã được phê duyệt xác minh chính thức.')
        return False, errors_dict, error_messages

    # Thu thập toàn bộ dữ liệu từ draft và additional_data
    data = verification.get_draft_dict()
    if additional_data and isinstance(additional_data, dict):
        for k, v in additional_data.items():
            if v is not None and v != '':
                data[k] = v

    # 1. Kiểm tra dữ liệu từng bước (1 -> 5)
    step_titles = {
        1: 'Thông tin cá nhân & Định danh',
        2: 'Ngôn ngữ nguồn, ngôn ngữ đích & Chiều dịch',
        3: 'Lĩnh vực chuyên môn & Hình thức dịch',
        4: 'Học vấn & Chứng chỉ ngoại ngữ',
        5: 'Kinh nghiệm nghề nghiệp & Dự án'
    }

    for step_num in range(1, 6):
        ok, step_errs = validate_step_data(step_num, data)
        if not ok:
            for f_name, f_msg in step_errs.items():
                errors_dict[f_name] = f_msg
                error_messages.append(f"Bước {step_num} ({step_titles[step_num]}): {f_msg}")

    # 2. Kiểm tra tài liệu cần thiết theo chính sách DOCUMENT_POLICIES
    active_docs = [d for d in verification.documents if getattr(d, 'is_active', False)] if verification.id else []
    active_types = {d.document_type for d in active_docs}

    for p_code, policy in DOCUMENT_POLICIES.items():
        if policy.get('required'):
            has_doc = (p_code in active_types)
            # Tương thích ngược: nếu cv_url đã có sẵn
            if p_code == 'cv' and (getattr(verification, 'cv_url', None) or data.get('cv_url')):
                has_doc = True
            
            if not has_doc:
                errors_dict[f'document_{p_code}'] = f"Thiếu tài liệu bắt buộc theo chính sách: {policy['name']}."
                error_messages.append(f"Tài liệu minh chứng: Chưa đính kèm {policy['name']} (bắt buộc theo chính sách VietTranslate).")

    # 3. Yêu cầu người dùng xác nhận thông tin trước khi gửi
    if require_confirmation:
        confirmed = False
        if additional_data:
            c_val = additional_data.get('confirmed') or additional_data.get('confirm_accuracy') or additional_data.get('pledge_confirmed')
            if c_val in (True, 'true', '1', 1, 'on', 'yes'):
                confirmed = True
        if not confirmed:
            errors_dict['confirmed'] = 'Vui lòng xác nhận cam kết tính chính xác và trung thực của hồ sơ trước khi gửi.'
            error_messages.append('Cam kết tính chính xác: Bạn cần tích chọn xác nhận cam kết thông tin và tài liệu trước khi gửi.')

    is_eligible = (len(error_messages) == 0)
    return is_eligible, errors_dict, error_messages


def submit_verification_for_review(user, form_data=None, confirmed=False, ip_address=None, user_agent=None):
    """
    Hành động gửi hồ sơ xác minh phiên dịch viên tới Ban quản trị:
    - Kiểm tra dữ liệu bắt buộc ở backend (tất cả các bước 1-5).
    - Kiểm tra tài liệu cần thiết theo chính sách (CV là bắt buộc).
    - Hiển thị danh sách lỗi chi tiết nếu hồ sơ chưa đủ điều kiện gửi.
    - Yêu cầu người dùng xác nhận cam kết trước khi gửi.
    - Ngăn chặn gửi lặp do bấm nút nhiều lần (idempotency, lock theo trạng thái).
    - Lưu snapshot phiên bản hồ sơ được gửi (versioning + bất biến).
    - Ghi thời điểm gửi (submitted_at) và trạng thái tương ứng (pending).
    - Chuyển hồ sơ sang hàng đợi Admin (AdminNotification).
    - Sau khi gửi, ngăn không cho sửa âm thầm phiên bản đã gửi.
    - Nếu thao tác thất bại, cho phép người dùng xử lý và thử lại mà không tạo hồ sơ trùng.
    
    Trả về: (thành_công: bool, thông_báo: str, metadata: dict)
    """
    if not user or user.role != 'translator':
        return False, 'Chỉ tài khoản phiên dịch viên mới có quyền gửi hồ sơ xác minh.', {'error_list': ['Chỉ tài khoản phiên dịch viên mới có quyền gửi hồ sơ xác minh.']}

    # Lấy hồ sơ xác minh hiện tại của người dùng
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    if not verification:
        return False, 'Không tìm thấy hồ sơ xác minh. Vui lòng hoàn thành biểu mẫu khai báo trước khi gửi.', {'error_list': ['Chưa tìm thấy hồ sơ xác minh.']}

    # 1. NGĂN GỬI LẶP KHI ĐÃ TRONG TRẠNG THÁI PENDING HOẶC APPROVED
    current_status = getattr(verification, 'status', 'draft') or 'draft'
    if current_status == 'pending':
        return False, 'Hồ sơ của bạn đã được gửi trước đó và đang trong hàng đợi xử lý của Ban quản trị. Vui lòng không gửi lặp lại.', {
            'is_duplicate': True,
            'status': 'pending',
            'submitted_at': verification.submitted_at.strftime('%d/%m/%Y %H:%M') if verification.submitted_at else None,
            'version': verification.submission_version or 1,
            'error_list': ['Hồ sơ đã được gửi và đang chờ xét duyệt. Vui lòng không gửi lặp lại.']
        }
    if current_status == 'approved':
        return False, 'Hồ sơ của bạn đã được phê duyệt xác minh chính thức. Không cần gửi lại.', {
            'is_already_approved': True,
            'status': 'approved',
            'error_list': ['Hồ sơ đã được phê duyệt xác minh chính thức.']
        }

    # Nếu có form_data truyền kèm: cập nhật nháp trước khi kiểm tra
    if form_data and isinstance(form_data, dict):
        draft = verification.get_draft_dict()
        field_mappings = [
            'full_name', 'phone', 'gender', 'dob', 'location', 'bio',
            'source_language', 'target_language', 'interpreting_direction', 'language_proficiency',
            'specializations', 'interpreting_types',
            'education_level', 'university', 'major', 'certificate_type', 'certificate_name',
            'current_position', 'notable_clients', 'featured_projects', 'notes'
        ]
        for f in field_mappings:
            if f in form_data and form_data[f] is not None:
                val = form_data[f]
                if isinstance(val, list):
                    val = ', '.join([str(v).strip() for v in val if v])
                elif isinstance(val, str):
                    val = val.strip()
                draft[f] = val
                setattr(verification, f, val)

        if 'cert_year' in form_data and form_data['cert_year']:
            try:
                cy = int(form_data['cert_year'])
                draft['cert_year'] = cy
                verification.cert_year = cy
            except (ValueError, TypeError):
                pass

        if 'experience_years' in form_data and form_data['experience_years'] != '':
            try:
                ey = int(form_data['experience_years'])
                draft['experience_years'] = ey
                verification.experience_years = ey
            except (ValueError, TypeError):
                pass

        if verification.source_language and verification.target_language:
            verification.primary_language = f"{verification.source_language} ➔ {verification.target_language}"

        verification.draft_data = json.dumps(draft, ensure_ascii=False)

    # 2. KIỂM TRA TÍNH HỢP LỆ VÀ ĐIỀU KIỆN GỬI HỒ SƠ
    data_for_check = {'confirmed': confirmed}
    if form_data:
        data_for_check.update(form_data)

    is_eligible, errors_dict, error_messages = validate_verification_eligibility(
        verification,
        additional_data=data_for_check,
        require_confirmation=True
    )

    if not is_eligible:
        return False, 'Hồ sơ chưa đủ điều kiện gửi xét duyệt. Vui lòng kiểm tra và hoàn thiện danh sách bên dưới.', {
            'errors': errors_dict,
            'error_list': error_messages,
            'status': verification.status
        }

    # 3. LẬP PHIÊN BẢN VÀ SNAPSHOT BẤT BIẾN
    now = datetime.utcnow()
    next_version = (getattr(verification, 'submission_version', 0) or 0) + 1

    active_docs = [d for d in verification.documents if getattr(d, 'is_active', False)]
    docs_snapshot = [
        {
            'id': d.id,
            'document_type': d.document_type,
            'type_name': get_document_type_label(d.document_type),
            'original_filename': d.original_filename,
            'stored_filename': d.stored_filename,
            'file_size': d.file_size,
            'file_size_formatted': format_file_size(d.file_size),
            'mime_type': d.mime_type,
            'file_hash': d.file_hash,
            'file_extension': d.file_extension,
            'created_at': d.created_at.strftime('%d/%m/%Y %H:%M') if d.created_at else None
        }
        for d in active_docs
    ]

    snapshot_data = {
        'version': next_version,
        'submitted_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone
        },
        'form_data': verification.get_draft_dict(),
        'documents': docs_snapshot,
        'pledge_confirmed': True,
        'ip_address': ip_address,
        'user_agent': user_agent
    }
    snapshot_json = json.dumps(snapshot_data, ensure_ascii=False)

    # 4. CẬP NHẬT TRẠNG THÁI HỒ SƠ
    verification.submission_version = next_version
    verification.submitted_at = now
    verification.submitted_snapshot = snapshot_json
    verification.status = 'pending'
    verification.rejection_reason = None
    verification.reviewed_by = None
    verification.reviewed_at = None
    verification.current_step = 6
    verification.updated_at = now

    # Lưu bản ghi lịch sử phiên bản
    submission_version_record = VerificationSubmissionVersion(
        verification_id=verification.id,
        user_id=user.id,
        version_number=next_version,
        status='pending',
        snapshot_data=snapshot_json,
        submitted_at=now,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(submission_version_record)

    # 5. CHUYỂN HỒ SƠ SANG HÀNG ĐỢI ADMIN (AdminNotification)
    try:
        admin_notif = AdminNotification(
            type='NEW_TRANSLATOR',
            title='Yêu cầu xác minh hồ sơ mới',
            message=f'Phiên dịch viên {user.name} ({user.email}) vừa nộp hồ sơ xác minh năng lực (Phiên bản #{next_version}).',
            url='/admin/translators?show=pending',
            related_id=verification.id
        )
        db.session.add(admin_notif)
    except Exception as e:
        print(f"[ADMIN NOTIF ERROR] {e}", file=sys.stderr)

    # Gửi thông báo cho phiên dịch viên
    try:
        user_notif = Notification(
            user_id=user.id,
            type='VERIFICATION_SUBMITTED',
            title='Hồ sơ xác minh đã gửi thành công! ⏳',
            message=f'Hồ sơ của bạn (Phiên bản #{next_version}) đã được chuyển tới hàng đợi xét duyệt của Ban quản trị. Chúng tôi sẽ phản hồi trong vòng 24–48 giờ.',
            url='/account/profile?tab=verification'
        )
        db.session.add(user_notif)
    except Exception as e:
        print(f"[USER NOTIF ERROR] {e}", file=sys.stderr)

    # 6. COMMIT TRANSACTION AN TOÀN
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Đảm bảo hồ sơ vẫn giữ nguyên trạng thái cũ, không bị trùng lặp bản ghi
        return False, f'Lỗi kết nối cơ sở dữ liệu khi gửi hồ sơ: {str(e)}', {
            'error_list': ['Lỗi kết nối cơ sở dữ liệu. Dữ liệu của bạn được bảo lưu an toàn, vui lòng thử gửi lại.']
        }

    success_msg = f'Hồ sơ xác minh (Phiên bản #{next_version}) đã được gửi thành công tới Ban quản trị! Thời gian xét duyệt dự kiến 24–48 giờ.'
    return True, success_msg, {
        'version': next_version,
        'submitted_at': now.strftime('%d/%m/%Y %H:%M'),
        'status': 'pending',
        'snapshot': snapshot_data
    }


def submit_verification_request(user, form_data, files):
    """
    Hàm tương thích ngược: Xử lý tệp đính kèm trực tiếp (nếu có)
    rồi chuyển tiếp tới hệ thống kiểm tra và lập phiên bản submit_verification_for_review.
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
    if not verification:
        verification = TranslatorVerification(user_id=user.id, status='draft', current_step=1)
        db.session.add(verification)
        db.session.flush()

    # Xử lý tệp CV nếu có truyền trực tiếp
    cv_file = files.get('cv_file')
    if cv_file and cv_file.filename:
        ok, doc, err = save_private_document(cv_file, user, doc_type='cv', verification=verification)
        if not ok:
            return False, err

    # Xử lý tệp Chứng chỉ nếu có
    cert_file = files.get('certificate_file')
    if cert_file and cert_file.filename:
        ok, doc, err = save_private_document(cert_file, user, doc_type='certificate', verification=verification)
        if not ok:
            return False, err

    # Xử lý tệp CCCD nếu có
    id_card_file = files.get('id_card_file')
    if id_card_file and id_card_file.filename:
        ok, doc, err = save_private_document(id_card_file, user, doc_type='id_card', verification=verification)
        if not ok:
            return False, err

    # Gọi hàm gửi chính với cờ xác nhận từ biểu mẫu
    confirmed = form_data.get('confirmed') in (True, 'true', '1', 1, 'on')
    ok, msg, meta = submit_verification_for_review(user, form_data=form_data, confirmed=confirmed)
    return ok, msg


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

        # Đồng bộ trạng thái đánh giá tài liệu minh chứng
        for doc in verification.documents:
            if doc.is_active:
                doc.status = 'approved'
                doc.reviewed_by = admin_user.id if admin_user else None
                doc.reviewed_at = now

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

        # Đồng bộ trạng thái đánh giá tài liệu minh chứng
        for doc in verification.documents:
            if doc.is_active:
                doc.status = 'rejected'
                doc.review_notes = rejection_reason
                doc.reviewed_by = admin_user.id if admin_user else None
                doc.reviewed_at = now

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


# ─── MULTI-STEP VERIFICATION DECLARATION & DRAFT SYSTEM ─────────────────────────

def get_or_create_verification_draft(user):
    """
    Lấy hoặc khởi tạo bản ghi xác minh dạng bản nháp (draft) cho phiên dịch viên.
    Nếu chưa có, tự động điền các thông tin sẵn có từ tài khoản (name, phone, email, bio).
    """
    if not user or user.role != 'translator':
        return None

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    if not verification:
        verification = TranslatorVerification(
            user_id=user.id,
            status='draft',
            current_step=1,
            full_name=user.name or '',
            phone=user.phone or '',
            bio=user.profile.bio if user.profile and user.profile.bio else ''
        )
        db.session.add(verification)
        db.session.commit()

    # Pre-populate nếu các trường còn trống
    draft_dict = verification.get_draft_dict()
    updated = False
    if not verification.full_name and user.name:
        verification.full_name = user.name
        updated = True
    if not verification.phone and user.phone:
        verification.phone = user.phone
        updated = True
    if not verification.bio and user.profile and user.profile.bio:
        verification.bio = user.profile.bio
        updated = True

    if updated:
        db.session.commit()

    return verification


def validate_step_data(step, data):
    """
    Kiểm tra tính hợp lệ của dữ liệu theo từng bước quy định.
    Trả về: (is_valid: bool, errors: dict[str, str])
    """
    errors = {}
    current_year = datetime.utcnow().year

    if step == 1:
        # 1. Thông tin cá nhân
        full_name = (data.get('full_name') or '').strip()
        if not full_name:
            errors['full_name'] = 'Vui lòng nhập họ và tên đầy đủ.'
        elif len(full_name.split()) < 2:
            errors['full_name'] = 'Họ và tên định danh phải có ít nhất 2 từ (Họ và Tên).'

        phone = (data.get('phone') or '').strip()
        phone_clean = re.sub(r'[\s\-\.]', '', phone)
        if not phone:
            errors['phone'] = 'Vui lòng nhập số điện thoại liên hệ.'
        elif not re.match(r'^(\+84|0)[3|5|7|8|9][0-9]{8}$', phone_clean) and not (phone_clean.isdigit() and 9 <= len(phone_clean) <= 12):
            errors['phone'] = 'Số điện thoại không hợp lệ (Ví dụ: 0901234567 hoặc +84901234567).'

        gender = (data.get('gender') or '').strip()
        if not gender or gender not in ('male', 'female', 'other'):
            errors['gender'] = 'Vui lòng chọn giới tính.'

        dob_str = (data.get('dob') or '').strip()
        if not dob_str:
            errors['dob'] = 'Vui lòng chọn ngày sinh.'
        else:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d')
                age = (datetime.utcnow() - dob_date).days // 365
                if age < 18:
                    errors['dob'] = 'Bạn phải từ 18 tuổi trở lên để đăng ký xác minh phiên dịch viên.'
                elif age > 80:
                    errors['dob'] = 'Năm sinh không hợp lệ.'
            except ValueError:
                errors['dob'] = 'Định dạng ngày sinh không đúng (YYYY-MM-DD).'

        location = (data.get('location') or '').strip()
        if not location:
            errors['location'] = 'Vui lòng nhập hoặc chọn tỉnh/thành phố nơi bạn cư trú.'

        bio = (data.get('bio') or '').strip()
        if not bio:
            errors['bio'] = 'Vui lòng viết đoạn tóm tắt giới thiệu bản thân.'
        elif len(bio) < 20:
            errors['bio'] = f'Giới thiệu bản thân cần ít nhất 20 ký tự (Hiện tại: {len(bio)} ký tự).'

    elif step == 2:
        # 2. Ngôn ngữ nguồn, ngôn ngữ đích và chiều phiên dịch
        source_lang = (data.get('source_language') or '').strip()
        target_lang = (data.get('target_language') or '').strip()
        direction = (data.get('interpreting_direction') or '').strip()
        proficiency = (data.get('language_proficiency') or '').strip()

        if not source_lang:
            errors['source_language'] = 'Vui lòng chọn ngôn ngữ nguồn.'
        if not target_lang:
            errors['target_language'] = 'Vui lòng chọn ngôn ngữ đích.'
        if source_lang and target_lang and source_lang.strip().lower() == target_lang.strip().lower():
            errors['target_language'] = 'Ngôn ngữ đích phải khác với ngôn ngữ nguồn.'

        valid_directions = ('two_way', 'source_to_target', 'target_to_source')
        if not direction or direction not in valid_directions:
            errors['interpreting_direction'] = 'Vui lòng chọn chiều phiên dịch hợp lệ.'

        valid_proficiencies = ('native', 'c2', 'c1', 'b2')
        if not proficiency or proficiency not in valid_proficiencies:
            errors['language_proficiency'] = 'Vui lòng chọn mức độ thành thạo ngôn ngữ.'

    elif step == 3:
        # 3. Lĩnh vực chuyên môn
        specs = data.get('specializations')
        if isinstance(specs, str):
            specs_list = [s.strip() for s in specs.split(',') if s.strip()]
        elif isinstance(specs, list):
            specs_list = [s.strip() for s in specs if s and str(s).strip()]
        else:
            specs_list = []

        if not specs_list:
            errors['specializations'] = 'Vui lòng chọn ít nhất 1 lĩnh vực chuyên môn thế mạnh.'

        types = data.get('interpreting_types')
        if isinstance(types, str):
            types_list = [t.strip() for t in types.split(',') if t.strip()]
        elif isinstance(types, list):
            types_list = [t.strip() for t in types if t and str(t).strip()]
        else:
            types_list = []

        if not types_list:
            errors['interpreting_types'] = 'Vui lòng chọn ít nhất 1 hình thức phiên dịch bạn có thể đảm nhận.'

    elif step == 4:
        # 4. Học vấn và chứng chỉ
        edu_level = (data.get('education_level') or '').strip()
        if not edu_level:
            errors['education_level'] = 'Vui lòng chọn trình độ học vấn cao nhất.'

        university = (data.get('university') or '').strip()
        if not university:
            errors['university'] = 'Vui lòng nhập tên trường hoặc cơ sở đào tạo.'
        elif len(university) < 3:
            errors['university'] = 'Tên trường đào tạo phải có ít nhất 3 ký tự.'

        major = (data.get('major') or '').strip()
        if not major:
            errors['major'] = 'Vui lòng nhập chuyên ngành đào tạo.'

        cert_type = (data.get('certificate_type') or '').strip()
        if not cert_type:
            errors['certificate_type'] = 'Vui lòng chọn loại chứng chỉ hoặc bằng cấp ngoại ngữ.'

        cert_name = (data.get('certificate_name') or '').strip()
        if not cert_name:
            errors['certificate_name'] = 'Vui lòng nhập điểm số hoặc cấp độ chứng chỉ (VD: IELTS 8.0, JLPT N1).'

        cert_year_val = data.get('cert_year')
        try:
            cert_year = int(cert_year_val)
            if cert_year < 1980 or cert_year > current_year:
                errors['cert_year'] = f'Năm cấp chứng chỉ không hợp lệ (1980 - {current_year}).'
        except (ValueError, TypeError):
            errors['cert_year'] = 'Vui lòng nhập năm cấp chứng chỉ hợp lệ.'

    elif step == 5:
        # 5. Kinh nghiệm nghề nghiệp
        exp_years_val = data.get('experience_years')
        try:
            exp_years = int(exp_years_val)
            if exp_years < 0 or exp_years > 50:
                errors['experience_years'] = 'Số năm kinh nghiệm phải từ 0 đến 50 năm.'
        except (ValueError, TypeError):
            errors['experience_years'] = 'Vui lòng nhập số năm kinh nghiệm hợp lệ (chữ số).'

        position = (data.get('current_position') or '').strip()
        if not position:
            errors['current_position'] = 'Vui lòng nhập vị trí hoặc chức danh phiên dịch hiện tại/gần nhất.'
        elif len(position) < 3:
            errors['current_position'] = 'Vị trí công tác cần ít nhất 3 ký tự.'

        projects = (data.get('featured_projects') or '').strip()
        if not projects:
            errors['featured_projects'] = 'Vui lòng mô tả các dự án, sự kiện phiên dịch tiêu biểu đã tham gia.'
        elif len(projects) < 30:
            errors['featured_projects'] = f'Mô tả dự án tiêu biểu cần ít nhất 30 ký tự để minh chứng năng lực (Hiện tại: {len(projects)} ký tự).'

    return len(errors) == 0, errors


def save_verification_draft(user, form_data, target_step=None):
    """
    Lưu nháp thông tin biểu mẫu vào bảng TranslatorVerification.
    Cập nhật các cột trường dữ liệu thực và cấu trúc draft_data (JSON).
    """
    if not user or user.role != 'translator':
        return False, None, 'Chỉ phiên dịch viên mới có thể lưu bản nháp xác minh.'

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    if verification:
        st = getattr(verification, 'status', 'draft') or 'draft'
        if st == 'pending':
            return False, None, 'Hồ sơ đang trong quá trình Ban quản trị thẩm định. Bạn không thể chỉnh sửa dữ liệu đã gửi.'
        if st == 'approved':
            return False, None, 'Hồ sơ đã được phê duyệt xác minh chính thức. Dữ liệu không thể tự ý thay đổi.'

    if not verification:
        verification = TranslatorVerification(user_id=user.id, status='draft', current_step=1)
        db.session.add(verification)

    # Đọc dữ liệu hiện tại
    draft = verification.get_draft_dict()

    # Cập nhật các trường được gửi lên
    field_mappings = [
        'full_name', 'phone', 'gender', 'dob', 'location', 'bio',
        'source_language', 'target_language', 'interpreting_direction', 'language_proficiency',
        'specializations', 'interpreting_types',
        'education_level', 'university', 'major', 'certificate_type', 'certificate_name',
        'current_position', 'notable_clients', 'featured_projects', 'notes'
    ]

    for field in field_mappings:
        if field in form_data:
            val = form_data.get(field)
            if isinstance(val, list):
                val = ', '.join([str(v).strip() for v in val if v])
            elif isinstance(val, str):
                val = val.strip()
            draft[field] = val
            setattr(verification, field, val)

    # Xử lý trường cert_year (int)
    if 'cert_year' in form_data and form_data.get('cert_year'):
        try:
            cert_year = int(form_data.get('cert_year'))
            draft['cert_year'] = cert_year
            verification.cert_year = cert_year
        except (ValueError, TypeError):
            pass

    # Xử lý trường experience_years (int)
    if 'experience_years' in form_data and form_data.get('experience_years') != '':
        try:
            exp_years = int(form_data.get('experience_years'))
            draft['experience_years'] = exp_years
            verification.experience_years = exp_years
        except (ValueError, TypeError):
            pass

    # Xử lý các cặp ngôn ngữ phụ (secondary_language_pairs) nếu có
    if 'secondary_language_pairs' in form_data:
        draft['secondary_language_pairs'] = form_data.get('secondary_language_pairs')

    # Đồng bộ cột canonical cho tìm kiếm và danh bạ
    if verification.source_language and verification.target_language:
        verification.primary_language = f"{verification.source_language} ➔ {verification.target_language}"
    elif verification.source_language:
        verification.primary_language = verification.source_language

    # Cập nhật current_step nếu được truyền
    if target_step is not None:
        try:
            s = int(target_step)
            if 1 <= s <= 6:
                verification.current_step = s
                draft['current_step'] = s
        except (ValueError, TypeError):
            pass

    # Giữ trạng thái nháp (chỉ khi hồ sơ chưa gửi duyệt chính thức)
    if verification.status in (None, 'not_started'):
        verification.status = 'draft'

    verification.draft_data = json.dumps(draft, ensure_ascii=False)
    verification.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        return True, verification, None
    except Exception as e:
        db.session.rollback()
        return False, None, f"Lỗi lưu trữ cơ sở dữ liệu: {str(e)}"

