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


# ─── TRANSLATOR VERIFICATION STATUS TRACKER SERVICE ───────────────────────────

def get_translator_verification_status_details(user):
    """
    Trích xuất toàn bộ dữ liệu chi tiết của trang theo dõi trạng thái xác minh phiên dịch viên.
    Quy tắc nghiệp vụ:
    - Tuyệt đối không tự suy đoán trạng thái nếu dữ liệu còn thiếu.
    - Không hiển thị đánh giá nội bộ nếu chính sách không cho phép (chỉ hiển thị ghi chú công khai).
    - Dữ liệu luôn đồng bộ thời gian thực từ cơ sở dữ liệu backend.
    - Đầy đủ thông tin về các bước, từng hạng mục, tài liệu, phản hồi Admin và lịch sử phiên bản.
    """
    if not user or getattr(user, 'role', '') != 'translator':
        return None

    profile = getattr(user, 'profile', None)
    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()

    # 1. Xác định trạng thái tổng thể chính xác (Overall Status)
    if profile and profile.is_verified:
        overall_state = 'verified'
        status_label = 'Đã xác minh chính thức'
        badge_color = 'emerald'
        status_headline = 'Tài khoản phiên dịch viên đã xác minh thành công'
        status_description = 'Hồ sơ của bạn đã hoàn tất thẩm định và nhận huy hiệu Tích xanh uy tín từ VietTranslate. Hồ sơ được ưu tiên hiển thị hàng đầu với khách thuê.'
    elif not verification:
        overall_state = 'not_started'
        status_label = 'Chưa khởi tạo hồ sơ'
        badge_color = 'slate'
        status_headline = 'Bạn chưa khởi tạo hồ sơ xác minh năng lực'
        status_description = 'Xác minh hồ sơ giúp tăng 300% cơ hội nhận dự án phiên dịch và được bảo vệ quyền lợi hợp đồng trên nền tảng VietTranslate.'
    else:
        st = getattr(verification, 'status', 'draft') or 'draft'
        if st in ('approved', 'verified'):
            overall_state = 'verified'
            status_label = 'Đã xác minh chính thức'
            badge_color = 'emerald'
            status_headline = 'Tài khoản phiên dịch viên đã xác minh thành công'
            status_description = 'Hồ sơ của bạn đã hoàn tất thẩm định và nhận huy hiệu Tích xanh uy tín từ VietTranslate. Hồ sơ được ưu tiên hiển thị hàng đầu với khách thuê.'
        elif st in ('pending', 'in_review'):
            overall_state = 'pending'
            status_label = 'Đang chờ xét duyệt'
            badge_color = 'amber'
            status_headline = 'Hồ sơ đang trong hàng đợi thẩm định của Ban quản trị'
            status_description = 'Hồ sơ của bạn đã được tiếp nhận an toàn. Đội ngũ kiểm duyệt VietTranslate đang đối soát thông tin và tài liệu minh chứng (Dự kiến 24–48 giờ làm việc).'
        elif st in ('needs_revision', 'revision_requested'):
            overall_state = 'needs_revision'
            status_label = 'Cần bổ sung hồ sơ'
            badge_color = 'orange'
            status_headline = 'Ban quản trị yêu cầu bổ sung / điều chỉnh hồ sơ'
            status_description = 'Vui lòng đọc kỹ nội dung yêu cầu bên dưới và cập nhật thông tin hoặc tài liệu minh chứng theo hướng dẫn của Ban quản trị.'
        elif st == 'rejected':
            overall_state = 'rejected'
            status_label = 'Hồ sơ bị từ chối'
            badge_color = 'rose'
            status_headline = 'Hồ sơ xác minh chưa đạt yêu cầu của nền tảng'
            status_description = 'Hồ sơ của bạn chưa đủ điều kiện xác minh theo tiêu chuẩn chất lượng VietTranslate. Vui lòng xem lý do chi tiết bên dưới để điều chỉnh và gửi lại.'
        elif st == 'draft':
            overall_state = 'draft'
            status_label = 'Bản nháp đang lưu'
            badge_color = 'indigo'
            status_headline = 'Hồ sơ xác minh đang ở trạng thái bản nháp'
            status_description = 'Bạn đã lưu nháp tiến trình khai báo nhưng chưa gửi tới Ban quản trị. Hãy hoàn thành các bước bắt buộc và gửi hồ sơ để nhận tích xanh.'
        else:
            overall_state = st
            status_label = st.capitalize()
            badge_color = 'slate'
            status_headline = f'Hồ sơ đang ở trạng thái: {status_label}'
            status_description = 'Dữ liệu được cập nhật trực tiếp từ hệ thống quản trị.'

    # 2. Thu thập ngày tháng chuẩn mực (không suy đoán ngày thiếu)
    created_at_dt = verification.created_at if verification else None
    submitted_at_dt = verification.submitted_at if verification else None
    reviewed_at_dt = verification.reviewed_at if verification else None
    updated_at_dt = verification.updated_at if verification else None

    created_at_str = created_at_dt.strftime('%d/%m/%Y %H:%M') if created_at_dt else None
    submitted_at_str = submitted_at_dt.strftime('%d/%m/%Y %H:%M') if submitted_at_dt else None
    reviewed_at_str = reviewed_at_dt.strftime('%d/%m/%Y %H:%M') if reviewed_at_dt else None
    updated_at_str = updated_at_dt.strftime('%d/%m/%Y %H:%M') if updated_at_dt else None

    # 3. Phân tích tiến độ 6 bước (Steps Progress)
    draft_data = verification.get_draft_dict() if verification else {}
    step_definitions = [
        {
            'step': 1,
            'title': 'Thông tin cá nhân & Định danh',
            'short_title': 'Thông tin cá nhân',
            'desc': 'Họ tên, SĐT, giới tính, ngày sinh, địa điểm và giới thiệu bản thân.',
            'fields': ['full_name', 'phone', 'gender', 'dob', 'location', 'bio']
        },
        {
            'step': 2,
            'title': 'Ngôn ngữ nguồn, ngôn ngữ đích & Chiều dịch',
            'short_title': 'Ngôn ngữ & Chiều dịch',
            'desc': 'Cặp ngôn ngữ đảm nhận, chiều phiên dịch và mức độ thành thạo.',
            'fields': ['source_language', 'target_language', 'interpreting_direction', 'language_proficiency']
        },
        {
            'step': 3,
            'title': 'Lĩnh vực chuyên môn & Hình thức dịch',
            'short_title': 'Chuyên môn & Hình thức',
            'desc': 'Chuyên ngành thế mạnh và hình thức dịch (cabin, song song, nối tiếp).',
            'fields': ['specializations', 'interpreting_types']
        },
        {
            'step': 4,
            'title': 'Học vấn & Chứng chỉ ngoại ngữ',
            'short_title': 'Học vấn & Chứng chỉ',
            'desc': 'Cơ sở đào tạo, chuyên ngành, tên và cấp độ chứng chỉ ngoại ngữ.',
            'fields': ['education_level', 'university', 'major', 'certificate_type', 'certificate_name', 'cert_year']
        },
        {
            'step': 5,
            'title': 'Kinh nghiệm nghề nghiệp & Dự án',
            'short_title': 'Kinh nghiệm thực chiến',
            'desc': 'Số năm kinh nghiệm, vị trí công tác và các dự án tiêu biểu.',
            'fields': ['experience_years', 'current_position', 'notable_clients', 'featured_projects']
        },
        {
            'step': 6,
            'title': 'Tài liệu minh chứng & Cam kết trung thực',
            'short_title': 'Tài liệu minh chứng',
            'desc': 'Sơ yếu lý lịch (CV), chứng chỉ scan và xác nhận cam kết trung thực.',
            'fields': ['cv_document', 'pledge_confirmed']
        }
    ]

    active_docs = [d for d in verification.documents if d.is_active] if verification else []
    active_doc_types = {d.document_type for d in active_docs}
    has_required_cv = ('cv' in active_doc_types) or bool(draft_data.get('cv_url') or (verification and verification.cv_url))

    steps_progress = []
    completed_steps_count = 0

    for sdef in step_definitions:
        step_num = sdef['step']
        step_item = {
            'step_number': step_num,
            'title': sdef['title'],
            'short_title': sdef['short_title'],
            'desc': sdef['desc'],
            'edit_url': f"/account/verification/form?step={step_num}",
            'missing_fields': [],
            'errors': {},
            'summary': {}
        }

        if step_num in (1, 2, 3, 4, 5):
            is_valid, step_errs = validate_step_data(step_num, draft_data)
            step_item['is_valid'] = is_valid
            step_item['errors'] = step_errs
            step_item['missing_fields'] = list(step_errs.keys())

            # Kiểm tra xem đã điền dở trường nào chưa
            has_some_data = any(bool(draft_data.get(f)) for f in sdef['fields'])

            if overall_state in ('verified', 'approved'):
                step_item['status'] = 'completed'
                step_item['status_label'] = 'Đã xác minh'
                step_item['badge_class'] = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                completed_steps_count += 1
            elif overall_state == 'pending':
                step_item['status'] = 'pending'
                step_item['status_label'] = 'Đang thẩm định'
                step_item['badge_class'] = 'bg-amber-50 text-amber-700 border-amber-200'
                completed_steps_count += 1
            elif overall_state == 'needs_revision':
                if not is_valid:
                    step_item['status'] = 'needs_revision'
                    step_item['status_label'] = 'Cần điều chỉnh'
                    step_item['badge_class'] = 'bg-orange-50 text-orange-700 border-orange-200'
                else:
                    step_item['status'] = 'completed'
                    step_item['status_label'] = 'Hợp lệ'
                    step_item['badge_class'] = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    completed_steps_count += 1
            elif overall_state == 'rejected':
                step_item['status'] = 'rejected'
                step_item['status_label'] = 'Chưa đạt'
                step_item['badge_class'] = 'bg-rose-50 text-rose-700 border-rose-200'
            elif overall_state == 'draft':
                if is_valid:
                    step_item['status'] = 'completed'
                    step_item['status_label'] = 'Đã hoàn tất'
                    step_item['badge_class'] = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    completed_steps_count += 1
                elif has_some_data:
                    step_item['status'] = 'in_progress'
                    step_item['status_label'] = 'Đang điền'
                    step_item['badge_class'] = 'bg-indigo-50 text-indigo-700 border-indigo-200'
                else:
                    step_item['status'] = 'not_started'
                    step_item['status_label'] = 'Chưa nhập'
                    step_item['badge_class'] = 'bg-slate-100 text-slate-600 border-slate-200'
            else:
                step_item['status'] = 'not_started'
                step_item['status_label'] = 'Chưa bắt đầu'
                step_item['badge_class'] = 'bg-slate-100 text-slate-600 border-slate-200'

        elif step_num == 6:
            # Bước 6: Tài liệu minh chứng & Cam kết
            has_rejected_doc = any(d.status == 'rejected' for d in active_docs)
            step_item['is_valid'] = has_required_cv

            if not has_required_cv:
                step_item['missing_fields'] = ['cv_document']
                step_item['errors'] = {'cv_document': 'Chưa tải lên Sơ yếu lý lịch (CV) bắt buộc.'}

            if overall_state in ('verified', 'approved'):
                step_item['status'] = 'completed'
                step_item['status_label'] = 'Đã xác minh'
                step_item['badge_class'] = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                completed_steps_count += 1
            elif overall_state == 'pending':
                step_item['status'] = 'pending'
                step_item['status_label'] = 'Đang thẩm định'
                step_item['badge_class'] = 'bg-amber-50 text-amber-700 border-amber-200'
                completed_steps_count += 1
            elif overall_state == 'needs_revision' or has_rejected_doc:
                step_item['status'] = 'needs_revision'
                step_item['status_label'] = 'Cần tải lại tệp'
                step_item['badge_class'] = 'bg-orange-50 text-orange-700 border-orange-200'
            elif overall_state == 'rejected':
                step_item['status'] = 'rejected'
                step_item['status_label'] = 'Chưa đạt'
                step_item['badge_class'] = 'bg-rose-50 text-rose-700 border-rose-200'
            elif overall_state == 'draft':
                if has_required_cv:
                    step_item['status'] = 'completed'
                    step_item['status_label'] = 'Đã có CV'
                    step_item['badge_class'] = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    completed_steps_count += 1
                elif len(active_docs) > 0:
                    step_item['status'] = 'in_progress'
                    step_item['status_label'] = 'Thiếu CV'
                    step_item['badge_class'] = 'bg-indigo-50 text-indigo-700 border-indigo-200'
                else:
                    step_item['status'] = 'not_started'
                    step_item['status_label'] = 'Chưa tải tệp'
                    step_item['badge_class'] = 'bg-slate-100 text-slate-600 border-slate-200'
            else:
                step_item['status'] = 'not_started'
                step_item['status_label'] = 'Chưa bắt đầu'
                step_item['badge_class'] = 'bg-slate-100 text-slate-600 border-slate-200'

        steps_progress.append(step_item)

    # 4. Chi tiết từng hạng mục dữ liệu thực tế (Categories Data)
    gender_map = {'male': 'Nam', 'female': 'Nữ', 'other': 'Khác'}
    direction_map = {
        'two_way': 'Song phương 2 chiều',
        'source_to_target': 'Một chiều (Nguồn ➔ Đích)',
        'target_to_source': 'Một chiều (Đích ➔ Nguồn)'
    }
    proficiency_map = {
        'native': 'Bản ngữ (Native)',
        'c2': 'Thành thạo C2',
        'c1': 'Chuyên nghiệp C1',
        'b2': 'Trung cấp B2'
    }
    edu_map = {
        'bachelor': 'Cử nhân',
        'master': 'Thạc sĩ',
        'doctorate': 'Tiến sĩ',
        'college': 'Cao đẳng',
        'other': 'Khác'
    }

    categories_data = {
        'personal': {
            'full_name': draft_data.get('full_name') or user.name or None,
            'phone': draft_data.get('phone') or user.phone or None,
            'gender': gender_map.get(draft_data.get('gender'), draft_data.get('gender')),
            'dob': draft_data.get('dob') or None,
            'location': draft_data.get('location') or None,
            'bio': draft_data.get('bio') or (profile.bio if profile else None)
        },
        'language': {
            'source_language': draft_data.get('source_language') or None,
            'target_language': draft_data.get('target_language') or None,
            'direction': direction_map.get(draft_data.get('interpreting_direction'), draft_data.get('interpreting_direction')),
            'proficiency': proficiency_map.get(draft_data.get('language_proficiency'), draft_data.get('language_proficiency')),
            'primary_pair': (f"{draft_data.get('source_language')} ➔ {draft_data.get('target_language')}") if (draft_data.get('source_language') and draft_data.get('target_language')) else None
        },
        'specialization': {
            'specializations': [s.strip() for s in draft_data.get('specializations', '').split(',') if s.strip()] if isinstance(draft_data.get('specializations'), str) else (draft_data.get('specializations') or []),
            'interpreting_types': [t.strip() for t in draft_data.get('interpreting_types', '').split(',') if t.strip()] if isinstance(draft_data.get('interpreting_types'), str) else (draft_data.get('interpreting_types') or [])
        },
        'education': {
            'education_level': edu_map.get(draft_data.get('education_level'), draft_data.get('education_level')),
            'university': draft_data.get('university') or None,
            'major': draft_data.get('major') or None,
            'certificate_type': draft_data.get('certificate_type') or None,
            'certificate_name': draft_data.get('certificate_name') or None,
            'cert_year': draft_data.get('cert_year') or None
        },
        'experience': {
            'experience_years': draft_data.get('experience_years') if draft_data.get('experience_years') is not None else None,
            'current_position': draft_data.get('current_position') or None,
            'notable_clients': draft_data.get('notable_clients') or None,
            'featured_projects': draft_data.get('featured_projects') or None
        }
    }

    # 5. Danh sách tài liệu minh chứng chi tiết (Document Vault)
    docs_formatted = []
    rejected_docs = []
    for d in active_docs:
        d_type_policy = DOCUMENT_POLICIES.get(d.document_type)
        type_name = d_type_policy['name'] if d_type_policy else d.document_type.upper()
        
        # Nhãn trạng thái tài liệu
        if d.status == 'approved':
            doc_st_label = 'Đã chấp thuận'
            doc_st_badge = 'bg-emerald-50 text-emerald-800 border-emerald-200'
        elif d.status == 'rejected':
            doc_st_label = 'Không đạt yêu cầu'
            doc_st_badge = 'bg-rose-50 text-rose-800 border-rose-200'
            rejected_docs.append({
                'id': d.id,
                'name': d.original_filename,
                'type_name': type_name,
                'reason': d.review_notes or 'Tài liệu chưa đạt tiêu chuẩn rõ ràng hoặc không hợp lệ.'
            })
        elif d.status == 'replaced':
            doc_st_label = 'Đã thay thế'
            doc_st_badge = 'bg-slate-100 text-slate-600 border-slate-200'
        else:
            doc_st_label = 'Đang chờ thẩm định'
            doc_st_badge = 'bg-amber-50 text-amber-800 border-amber-200'

        docs_formatted.append({
            'id': d.id,
            'document_type': d.document_type,
            'type_name': type_name,
            'original_filename': d.original_filename,
            'file_size_formatted': format_file_size(d.file_size),
            'file_extension': d.file_extension,
            'mime_type': d.mime_type,
            'status': d.status,
            'status_label': doc_st_label,
            'status_badge': doc_st_badge,
            'review_notes': d.review_notes,
            'reviewed_at': d.reviewed_at.strftime('%d/%m/%Y %H:%M') if d.reviewed_at else None,
            'created_at': d.created_at.strftime('%d/%m/%Y %H:%M') if d.created_at else None,
            'can_preview': d.file_extension in ('pdf', 'jpg', 'jpeg', 'png', 'webp'),
            'view_url': f"/account/verification/documents/{d.id}/view",
            'download_url': f"/account/verification/documents/{d.id}/download"
        })

    # Kiểm tra các loại tài liệu bắt buộc theo DOCUMENT_POLICIES
    policy_checklist = []
    for p_code, p_item in DOCUMENT_POLICIES.items():
        is_attached = p_code in active_doc_types
        # Fallback CV
        if p_code == 'cv' and not is_attached and (getattr(verification, 'cv_url', None) or draft_data.get('cv_url')):
            is_attached = True

        policy_checklist.append({
            'code': p_code,
            'name': p_item['name'],
            'description': p_item['description'],
            'required': p_item['required'],
            'is_attached': is_attached
        })

    # 6. Yêu cầu bổ sung và lý do từ chối của Admin (Admin Feedback)
    admin_feedback = {
        'rejection_reason': getattr(verification, 'rejection_reason', None) if verification else None,
        'needs_revision_message': None,
        'has_rejection': bool(overall_state == 'rejected' or (verification and verification.rejection_reason)),
        'has_revision_request': bool(overall_state == 'needs_revision' or len(rejected_docs) > 0),
        'rejected_documents': rejected_docs,
        'reviewed_at_str': reviewed_at_str
    }
    if overall_state == 'needs_revision':
        admin_feedback['needs_revision_message'] = (
            getattr(verification, 'rejection_reason', None) or 
            'Ban quản trị yêu cầu kiểm tra và tải lại tài liệu minh chứng hoặc bổ sung thông tin còn thiếu.'
        )

    # 7. Lịch sử các lần gửi hồ sơ và kết quả (Submission History)
    submission_records = VerificationSubmissionVersion.query.filter_by(
        user_id=user.id
    ).order_by(VerificationSubmissionVersion.version_number.desc()).all()

    submission_history = []
    for sub in submission_records:
        snap = sub.get_snapshot()
        docs_snap = snap.get('documents', []) if isinstance(snap, dict) else []
        form_snap = snap.get('form_data', {}) if isinstance(snap, dict) else {}
        
        lang_summary = None
        if form_snap.get('source_language') and form_snap.get('target_language'):
            lang_summary = f"{form_snap.get('source_language')} ➔ {form_snap.get('target_language')}"

        st_map = {
            'pending': ('Đang thẩm định', 'bg-amber-50 text-amber-800 border-amber-200'),
            'approved': ('Đã chấp thuận', 'bg-emerald-50 text-emerald-800 border-emerald-200'),
            'rejected': ('Chưa đạt', 'bg-rose-50 text-rose-800 border-rose-200'),
            'needs_revision': ('Yêu cầu bổ sung', 'bg-orange-50 text-orange-800 border-orange-200')
        }
        sub_label, sub_badge = st_map.get(sub.status, (sub.status.capitalize(), 'bg-slate-100 text-slate-700 border-slate-200'))

        submission_history.append({
            'version_number': sub.version_number,
            'submitted_at_str': sub.submitted_at.strftime('%d/%m/%Y %H:%M') if sub.submitted_at else 'Chưa ghi nhận',
            'status': sub.status,
            'status_label': sub_label,
            'status_badge': sub_badge,
            'docs_count': len(docs_snap),
            'language_pair': lang_summary,
            'ip_address': sub.ip_address,
            'snapshot': snap
        })

    # 8. Hành động tiếp theo phù hợp với trạng thái hiện tại (Next Actions)
    if overall_state == 'not_started':
        next_action = {
            'type': 'start',
            'guidance': 'Bắt đầu khai báo thông tin cá nhân, ngôn ngữ và đính kèm CV để Ban quản trị xét duyệt.',
            'primary_btn': {
                'text': 'Khởi tạo hồ sơ xác minh ngay',
                'url': '/account/verification/form',
                'icon': 'sparkles',
                'class': 'bg-brand-600 hover:bg-brand-700 text-white'
            },
            'secondary_btn': {
                'text': 'Xem trang cá nhân',
                'url': '/account/profile',
                'icon': 'user',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }
    elif overall_state == 'draft':
        cur_step = verification.current_step if verification and verification.current_step else 1
        next_action = {
            'type': 'continue_draft',
            'guidance': f'Bạn đang ở Bước {cur_step}/6. Hãy hoàn thiện các mục còn lại và nhấn gửi duyệt ở Bước 6.',
            'primary_btn': {
                'text': f'Tiếp tục hoàn thiện Bước {cur_step}/6',
                'url': f"/account/verification/form?step={cur_step}",
                'icon': 'pencil',
                'class': 'bg-brand-600 hover:bg-brand-700 text-white'
            },
            'secondary_btn': {
                'text': 'Quản lý tài liệu đính kèm',
                'url': '/account/profile?tab=verification',
                'icon': 'folder',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }
    elif overall_state == 'pending':
        next_action = {
            'type': 'wait_review',
            'guidance': 'Hồ sơ của bạn đang được Ban quản trị thẩm định. Chúng tôi sẽ thông báo qua chuông thông báo khi có kết quả.',
            'primary_btn': {
                'text': 'Xem lại thông tin hồ sơ đã gửi',
                'url': '/account/verification/form?step=6',
                'icon': 'eye',
                'class': 'bg-slate-800 hover:bg-slate-900 text-white'
            },
            'secondary_btn': {
                'text': 'Về trang quản lý tài khoản',
                'url': '/account/profile',
                'icon': 'user',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }
    elif overall_state == 'needs_revision':
        next_action = {
            'type': 'revise',
            'guidance': 'Vui lòng chỉnh sửa các mục chưa đạt theo yêu cầu của Ban quản trị và nộp lại hồ sơ.',
            'primary_btn': {
                'text': 'Cập nhật & Bổ sung hồ sơ ngay',
                'url': '/account/verification/revision',
                'icon': 'refresh',
                'class': 'bg-orange-600 hover:bg-orange-700 text-white shadow-md shadow-orange-500/20'
            },
            'secondary_btn': {
                'text': 'Quản lý kho tài liệu',
                'url': '/account/profile?tab=verification',
                'icon': 'folder',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }
    elif overall_state == 'rejected':
        next_action = {
            'type': 'reapply',
            'guidance': 'Hồ sơ chưa đạt tiêu chuẩn. Bạn có thể cập nhật lại thông tin, tải tài liệu rõ nét hơn và gửi lại.',
            'primary_btn': {
                'text': 'Bổ sung hồ sơ & Gửi lại',
                'url': '/account/verification/revision',
                'icon': 'refresh',
                'class': 'bg-rose-600 hover:bg-rose-700 text-white shadow-md shadow-rose-500/20'
            },
            'secondary_btn': {
                'text': 'Liên hệ hỗ trợ VietTranslate',
                'url': '/about',
                'icon': 'mail',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }
    else:  # verified
        next_action = {
            'type': 'verified',
            'guidance': 'Chúc mừng bạn! Hồ sơ đã đạt tiêu chuẩn tích xanh. Khách thuê có thể tìm kiếm và đặt lịch trực tiếp.',
            'primary_btn': {
                'text': 'Xem trang hồ sơ công khai của bạn',
                'url': f"/translator/{user.id}",
                'icon': 'badge',
                'class': 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-500/20'
            },
            'secondary_btn': {
                'text': 'Cài đặt lịch làm việc',
                'url': '/translator/schedule',
                'icon': 'calendar',
                'class': 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }
        }

    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'avatar': getattr(user, 'avatar', None) or getattr(user, 'avatar_url', None),
            'role': user.role
        },
        'has_verification': bool(verification or (profile and profile.is_verified)),
        'verification_id': verification.id if verification else None,
        'overall_state': overall_state,
        'status_label': status_label,
        'badge_color': badge_color,
        'status_headline': status_headline,
        'status_description': status_description,
        'current_version': getattr(verification, 'submission_version', 0) if verification else 0,
        'timestamps': {
            'created_at': created_at_str,
            'submitted_at': submitted_at_str,
            'reviewed_at': reviewed_at_str,
            'updated_at': updated_at_str
        },
        'steps_progress': steps_progress,
        'completed_steps_count': completed_steps_count,
        'total_steps_count': 6,
        'categories_data': categories_data,
        'documents': docs_formatted,
        'policy_checklist': policy_checklist,
        'admin_feedback': admin_feedback,
        'submission_history': submission_history,
        'next_action': next_action
    }


# ─── TRANSLATOR VERIFICATION REVISION & RESUBMISSION WORKFLOW ─────────────────

def can_user_revise_verification(user, verification):
    """
    Kiểm tra xem phiên dịch viên có quyền bổ sung và gửi lại hồ sơ hay không:
    - User phải tồn tại và có role 'translator'.
    - verification phải thuộc quyền sở hữu của user.
    - Trạng thái hồ sơ PHẢI là 'needs_revision', 'revision_requested', hoặc 'rejected'.
    - Nếu trạng thái là 'pending': Chặn vì hồ sơ đang trong hàng đợi xử lý của Ban quản trị.
    - Nếu trạng thái là 'approved': Chặn vì hồ sơ đã được duyệt cấp tích xanh.
    - Nếu trạng thái là 'draft' hoặc 'not_started': Chưa nộp lần đầu, hướng dẫn qua form chính.
    """
    if not user or getattr(user, 'role', '') != 'translator':
        return False, 'Chỉ tài khoản phiên dịch viên mới có quyền bổ sung hồ sơ xác minh.'

    if not verification:
        return False, 'Chưa tìm thấy hồ sơ xác minh cần bổ sung.'

    if verification.user_id != user.id:
        return False, 'Bạn không có quyền thao tác trên hồ sơ của người khác.'

    st = getattr(verification, 'status', 'draft') or 'draft'
    if st == 'pending':
        return False, 'Hồ sơ của bạn đã được gửi và đang trong hàng đợi xét duyệt của Ban quản trị. Bạn không thể chỉnh sửa vào lúc này.'

    if st in ('approved', 'verified'):
        return False, 'Hồ sơ của bạn đã được phê duyệt xác minh chính thức. Không cần bổ sung thêm.'

    if st in ('draft', 'not_started'):
        return False, 'Hồ sơ đang ở trạng thái bản nháp. Vui lòng hoàn thành các bước khai báo ban đầu và gửi duyệt lần đầu.'

    if st not in ('needs_revision', 'revision_requested', 'rejected'):
        return False, f'Trạng thái hồ sơ hiện tại ({st}) không yêu cầu bổ sung.'

    return True, None


def get_actual_revision_items(verification, user=None):
    """
    Trích xuất toàn bộ danh sách các hạng mục Admin yêu cầu bổ sung từ dữ liệu thực tế đã lưu trong hệ thống:
    1. Các tài liệu minh chứng bị Admin đánh giá 'rejected' trong bảng VerificationDocument (kèm lý do và hướng dẫn).
    2. Các tiêu chí / trường dữ liệu được Admin lưu trong verification.rejection_reason (hỗ trợ cả JSON cấu trúc và văn bản).
    3. Đánh giá trạng thái giải quyết (is_resolved) cho từng hạng mục để giao diện phản ánh trực tiếp tiến trình bổ sung.
    """
    items = []
    if not verification:
        return items

    draft_dict = verification.get_draft_dict()
    prev_snapshot = verification.get_submitted_snapshot()
    prev_form = prev_snapshot.get('form_data', {}) if isinstance(prev_snapshot, dict) else {}

    # 1. TÀI LIỆU MINH CHỨNG BỊ REJECTED TỪ ADMIN
    active_docs = [d for d in verification.documents if d.is_active]
    rejected_docs = [d for d in verification.documents if d.status == 'rejected']
    for rd in verification.documents:
        if rd.status == 'replaced' and rd.review_notes and rd.document_type not in [d.document_type for d in rejected_docs]:
            rejected_docs.append(rd)

    handled_doc_types = set()
    for rd in rejected_docs:
        d_type = rd.document_type
        handled_doc_types.add(d_type)
        policy = DOCUMENT_POLICIES.get(d_type, {})
        type_name = policy.get('name', get_document_type_label(d_type))

        # Kiểm tra xem đã có tài liệu mới nào thay thế cho tài liệu này chưa
        replacement_doc = next(
            (d for d in active_docs if d.document_type == d_type and d.id != rd.id and d.status in ('uploaded', 'pending', 'approved')),
            None
        )
        is_resolved = bool(replacement_doc is not None)

        instruction = f"Tải lên tệp thay thế định dạng {', '.join([e.upper() for e in policy.get('allowed_extensions', ['pdf', 'jpg', 'png'])])}, dung lượng tối đa {policy.get('max_size_mb', 10)} MB."
        if d_type == 'cv':
            instruction = "Tải lên tệp CV mới nhất (PDF/DOCX), cập nhật đầy đủ kinh nghiệm dịch thuật và dự án tiêu biểu."
        elif d_type == 'certificate':
            instruction = "Chụp hoặc scan lại bản gốc chứng chỉ rõ nét (PDF, JPG, PNG, WEBP), không bị lóa hoặc che khuất số hiệu/ngày cấp."
        elif d_type == 'id_card':
            instruction = "Chụp bản gốc CCCD/CMND rõ cả hai mặt, đầy đủ 4 góc, thông tin số và ảnh chân dung sắc nét."

        items.append({
            'id': f"doc_{rd.id}",
            'item_type': 'document',
            'category': 'documents',
            'document_type': d_type,
            'title': f"Tài liệu minh chứng: {type_name}",
            'reason': rd.review_notes or getattr(verification, 'rejection_reason', None) or 'Tài liệu chưa đạt tiêu chuẩn rõ ràng hoặc không hợp lệ.',
            'instruction': instruction,
            'current_file_id': rd.id,
            'current_filename': rd.original_filename,
            'current_file_size': format_file_size(rd.file_size),
            'rejected_at': rd.reviewed_at.strftime('%d/%m/%Y %H:%M') if rd.reviewed_at else None,
            'is_resolved': is_resolved,
            'replacement_filename': replacement_doc.original_filename if replacement_doc else None,
            'replacement_file_id': replacement_doc.id if replacement_doc else None
        })

    # 2. CÁC HẠNG MỤC THÔNG TIN TỪ REJECTION_REASON CỦA ADMIN
    raw_reason = (verification.rejection_reason or '').strip()
    if raw_reason:
        parsed_from_json = False
        if raw_reason.startswith('{') or raw_reason.startswith('['):
            try:
                parsed_json = json.loads(raw_reason)
                raw_items = []
                if isinstance(parsed_json, dict):
                    raw_items = parsed_json.get('items') or parsed_json.get('revision_items') or []
                elif isinstance(parsed_json, list):
                    raw_items = parsed_json

                if raw_items:
                    parsed_from_json = True
                    for idx, r_item in enumerate(raw_items):
                        if not isinstance(r_item, dict):
                            continue
                        itype = r_item.get('item_type', 'field')
                        if itype == 'document':
                            doc_code = r_item.get('document_type', 'certificate')
                            if doc_code not in handled_doc_types:
                                handled_doc_types.add(doc_code)
                                p = DOCUMENT_POLICIES.get(doc_code, {})
                                has_repl = any(d.document_type == doc_code and d.status in ('uploaded', 'pending') for d in active_docs)
                                items.append({
                                    'id': r_item.get('id', f"doc_req_{idx}"),
                                    'item_type': 'document',
                                    'category': 'documents',
                                    'document_type': doc_code,
                                    'title': r_item.get('title', f"Tài liệu minh chứng: {p.get('name', doc_code.upper())}"),
                                    'reason': r_item.get('reason', raw_reason),
                                    'instruction': r_item.get('instruction', f"Vui lòng tải lên tài liệu {p.get('name', doc_code)} hợp lệ."),
                                    'is_resolved': has_repl,
                                    'current_filename': None
                                })
                        else:
                            f_name = r_item.get('field_name') or r_item.get('field', 'notes')
                            curr_val = draft_dict.get(f_name)
                            old_val = prev_form.get(f_name)
                            is_res = bool(curr_val and (old_val is None or str(curr_val).strip() != str(old_val).strip()))
                            items.append({
                                'id': r_item.get('id', f"field_{f_name}_{idx}"),
                                'item_type': 'field',
                                'category': r_item.get('category', 'general'),
                                'field_name': f_name,
                                'related_fields': [f_name],
                                'title': r_item.get('title', f"Thông tin: {f_name}"),
                                'reason': r_item.get('reason', raw_reason),
                                'instruction': r_item.get('instruction', 'Vui lòng cập nhật lại thông tin này.'),
                                'current_value': curr_val,
                                'is_resolved': is_res
                            })
            except Exception:
                parsed_from_json = False

        if not parsed_from_json:
            lower_reason = raw_reason.lower()

            exp_keywords = ('kinh nghiệm', 'dự án', 'hội nghị', 'cabin', 'năm kinh nghiệm', 'khách hàng', 'vị trí')
            if any(k in lower_reason for k in exp_keywords):
                curr_exp = draft_dict.get('notes') or draft_dict.get('featured_projects') or draft_dict.get('experience_years')
                old_exp = prev_form.get('notes') or prev_form.get('featured_projects') or prev_form.get('experience_years')
                is_res = bool(curr_exp and (old_exp is None or str(curr_exp).strip() != str(old_exp).strip()))
                items.append({
                    'id': 'item_field_experience',
                    'item_type': 'field',
                    'category': 'experience',
                    'field_name': 'notes',
                    'related_fields': ['experience_years', 'current_position', 'featured_projects', 'notes'],
                    'title': 'Kinh nghiệm nghề nghiệp & Dự án tiêu biểu',
                    'reason': raw_reason,
                    'instruction': 'Cập nhật lại số năm kinh nghiệm, liệt kê cụ thể các dự án/hội nghị phiên dịch đã tham gia hoặc bổ sung lời nhắn chi tiết cho Ban quản trị.',
                    'current_value': draft_dict.get('notes') or draft_dict.get('featured_projects'),
                    'is_resolved': is_res
                })

            lang_keywords = ('ngôn ngữ', 'tiếng', 'chiều dịch', 'trình độ ngôn ngữ')
            if any(k in lower_reason for k in lang_keywords):
                curr_l = draft_dict.get('language_proficiency') or draft_dict.get('source_language')
                old_l = prev_form.get('language_proficiency') or prev_form.get('source_language')
                is_res = bool(curr_l and (old_l is None or str(curr_l).strip() != str(old_l).strip()))
                items.append({
                    'id': 'item_field_languages',
                    'item_type': 'field',
                    'category': 'languages',
                    'field_name': 'language_proficiency',
                    'related_fields': ['source_language', 'target_language', 'interpreting_direction', 'language_proficiency'],
                    'title': 'Ngôn ngữ phiên dịch & Trình độ',
                    'reason': raw_reason,
                    'instruction': 'Kiểm tra và cập nhật đúng cặp ngôn ngữ, chiều dịch và trình độ thành thạo.',
                    'current_value': draft_dict.get('language_proficiency'),
                    'is_resolved': is_res
                })

            edu_keywords = ('chứng chỉ', 'ielts', 'jlpt', 'hsk', 'topik', 'bằng cấp', 'đại học')
            if any(k in lower_reason for k in edu_keywords) and 'certificate' not in handled_doc_types and 'diploma' not in handled_doc_types:
                curr_c = draft_dict.get('certificate_name') or draft_dict.get('major')
                old_c = prev_form.get('certificate_name') or prev_form.get('major')
                is_res = bool(curr_c and (old_c is None or str(curr_c).strip() != str(old_c).strip()))
                items.append({
                    'id': 'item_field_education',
                    'item_type': 'field',
                    'category': 'education',
                    'field_name': 'certificate_name',
                    'related_fields': ['education_level', 'university', 'major', 'certificate_type', 'certificate_name', 'cert_year'],
                    'title': 'Thông tin Học vấn & Chứng chỉ',
                    'reason': raw_reason,
                    'instruction': 'Bổ sung tên chứng chỉ, điểm số / cấp độ hoặc thông tin văn bằng đào tạo.',
                    'current_value': draft_dict.get('certificate_name'),
                    'is_resolved': is_res
                })

            if not items:
                curr_n = draft_dict.get('notes')
                old_n = prev_form.get('notes')
                is_res = bool(curr_n and (old_n is None or str(curr_n).strip() != str(old_n).strip()))
                items.append({
                    'id': 'item_field_general',
                    'item_type': 'field',
                    'category': 'general',
                    'field_name': 'notes',
                    'related_fields': ['notes'],
                    'title': 'Nội dung giải trình & Bổ sung hồ sơ',
                    'reason': raw_reason,
                    'instruction': 'Ghi rõ nội dung giải trình hoặc thông tin điều chỉnh theo hướng dẫn của Ban quản trị vào ô ghi chú bên dưới.',
                    'current_value': draft_dict.get('notes'),
                    'is_resolved': is_res
                })

    return items


def get_verification_revision_details(user):
    """
    Thu thập toàn bộ dữ liệu phục vụ trang và API bổ sung hồ sơ:
    - Quyền sửa theo trạng thái.
    - Danh sách các hạng mục yêu cầu bổ sung thực tế được Admin lưu.
    - Dữ liệu biểu mẫu hiện tại (pre-filled, người dùng không cần khai báo lại từ đầu).
    - Danh sách tài liệu hiện có.
    - Lịch sử các phiên bản nộp trước đó để đối chiếu so sánh.
    """
    if not user or getattr(user, 'role', '') != 'translator':
        return {'can_revise': False, 'error': 'Chỉ tài khoản phiên dịch viên mới có quyền truy cập.'}

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    can_revise, err_reason = can_user_revise_verification(user, verification)

    revision_items = get_actual_revision_items(verification, user=user) if verification else []
    resolved_count = sum(1 for it in revision_items if it.get('is_resolved'))
    total_items_count = len(revision_items)
    is_all_resolved = (total_items_count > 0 and resolved_count == total_items_count)

    draft_dict = verification.get_draft_dict() if verification else {}
    active_docs = [d for d in verification.documents if d.is_active] if verification else []

    versions = []
    if verification:
        sub_records = VerificationSubmissionVersion.query.filter_by(verification_id=verification.id).order_by(VerificationSubmissionVersion.version_number.desc()).all()
        for s in sub_records:
            snap = s.get_snapshot()
            versions.append({
                'version_number': s.version_number,
                'submitted_at_str': s.submitted_at.strftime('%d/%m/%Y %H:%M') if s.submitted_at else None,
                'status': s.status,
                'ip_address': s.ip_address,
                'snapshot': snap
            })

    current_version = getattr(verification, 'submission_version', 0) or 1
    next_version = current_version + 1

    return {
        'can_revise': can_revise,
        'revision_error': err_reason,
        'verification_id': verification.id if verification else None,
        'status': getattr(verification, 'status', 'draft') if verification else 'not_started',
        'current_version': current_version,
        'next_version': next_version,
        'general_reason': getattr(verification, 'rejection_reason', None) if verification else None,
        'reviewed_at_str': verification.reviewed_at.strftime('%d/%m/%Y %H:%M') if (verification and verification.reviewed_at) else None,
        'revision_items': revision_items,
        'resolved_count': resolved_count,
        'total_items_count': total_items_count,
        'is_all_resolved': is_all_resolved,
        'form_data': draft_dict,
        'active_documents': [d.to_dict() for d in active_docs],
        'versions_history': versions,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone
        }
    }


def validate_revision_submission(verification, form_data=None, files=None):
    """
    Kiểm tra xem người dùng đã thực sự giải quyết tất cả các hạng mục mà Admin yêu cầu bổ sung hay chưa:
    - Tài liệu: Có tệp thay thế hợp lệ tải lên trong request HOẶC đã có tài liệu active mới thay thế.
    - Thông tin: Có giá trị cập nhật hợp lệ mới trong form_data hoặc draft_dict.
    Trả về: (hợp_lệ: bool, missing_items: list, thông_báo: str)
    """
    if not verification:
        return False, [], "Không tìm thấy hồ sơ xác minh."

    revision_items = get_actual_revision_items(verification)
    if not revision_items:
        return True, [], "Không có hạng mục bổ sung bắt buộc cụ thể nào."

    missing_items = []
    active_docs = [d for d in verification.documents if d.is_active]

    for item in revision_items:
        itype = item.get('item_type')
        if itype == 'document':
            doc_type = item.get('document_type')
            has_uploaded_in_req = False
            if files:
                for k in (f"doc_file_{doc_type}", f"file_{doc_type}", doc_type):
                    f = files.get(k)
                    if f:
                        if isinstance(f, tuple) and len(f) > 1 and f[1]:
                            has_uploaded_in_req = True
                            break
                        elif getattr(f, 'filename', ''):
                            has_uploaded_in_req = True
                            break

            has_active_replacement = bool(item.get('is_resolved'))
            if not has_active_replacement:
                cur_file_id = item.get('current_file_id')
                for d in active_docs:
                    if d.document_type == doc_type and d.id != cur_file_id and d.status in ('uploaded', 'pending', 'approved'):
                        has_active_replacement = True
                        break

            if not (has_uploaded_in_req or has_active_replacement):
                missing_items.append(item)

        elif itype == 'field':
            related_fields = item.get('related_fields', [item.get('field_name', 'notes')])
            has_update = False

            prev_snapshot = verification.get_submitted_snapshot()
            prev_form = prev_snapshot.get('form_data', {}) if isinstance(prev_snapshot, dict) else {}

            if form_data:
                for rf in related_fields:
                    val = form_data.get(rf)
                    if val is not None and str(val).strip() != '':
                        prev_val = prev_form.get(rf)
                        if prev_val is None or str(val).strip() != str(prev_val).strip() or len(str(val).strip()) > 0:
                            has_update = True
                            break

            if not has_update:
                curr_draft = verification.get_draft_dict()
                for rf in related_fields:
                    cval = curr_draft.get(rf)
                    pval = prev_form.get(rf)
                    if cval and (pval is None or str(cval).strip() != str(pval).strip()):
                        has_update = True
                        break

            if not has_update:
                missing_items.append(item)

    if missing_items:
        missing_titles = [m.get('title') for m in missing_items]
        msg = f"Bạn chưa hoàn tất bổ sung {len(missing_items)} hạng mục theo yêu cầu: {', '.join(missing_titles)}. Vui lòng kiểm tra và cập nhật đầy đủ trước khi gửi lại."
        return False, missing_items, msg

    return True, [], "Tất cả các hạng mục yêu cầu bổ sung đã được hoàn thành đầy đủ."


def resubmit_verification(user, form_data=None, files=None, ip_address=None, user_agent=None):
    """
    Quy trình gửi lại hồ sơ sau khi bổ sung theo yêu cầu Admin:
    - Kiểm tra quyền sửa theo trạng thái ('needs_revision', 'revision_requested', 'rejected').
    - Ngăn gửi lặp nếu hồ sơ đã ở trạng thái 'pending' (Anti-duplicate guard).
    - Lưu các tài liệu minh chứng thay thế vào vùng lưu trữ riêng tư (Private Storage).
    - Cập nhật các trường thông tin bổ sung, giữ nguyên toàn bộ thông tin hợp lệ đã khai trước đó.
    - Kiểm tra xem người dùng đã hoàn thành đầy đủ các hạng mục Admin yêu cầu chưa.
    - Tăng phiên bản hồ sơ (version N -> N+1).
    - Tạo snapshot bất biến của phiên bản mới kèm diff so sánh với phiên bản trước.
    - Lưu bản ghi lịch sử vào VerificationSubmissionVersion (bảo toàn phiên bản cũ để đối chiếu).
    - Chuyển trạng thái hồ sơ về 'pending' (đưa vào hàng đợi Admin).
    - Xếp thông báo AdminNotification và Notification cho người dùng.
    - Xử lý lỗi an toàn (transaction rollback) và trả về thông báo kết quả thực tế.
    """
    if not user or getattr(user, 'role', '') != 'translator':
        return False, 'Chỉ tài khoản phiên dịch viên mới có quyền gửi lại hồ sơ xác minh.', {'error_list': ['Chỉ tài khoản phiên dịch viên mới có quyền gửi lại hồ sơ xác minh.']}

    verification = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.created_at.desc()).first()
    if not verification:
        return False, 'Không tìm thấy hồ sơ xác minh để gửi lại.', {'error_list': ['Không tìm thấy hồ sơ xác minh.']}

    # 1. KIỂM TRA QUYỀN SỬA THEO TRẠNG THÁI VÀ CHẶN GỬI LẶP
    current_status = getattr(verification, 'status', 'draft') or 'draft'
    if current_status == 'pending':
        return False, 'Hồ sơ của bạn đã được gửi lại trước đó và đang trong hàng đợi xử lý của Ban quản trị. Vui lòng không gửi lặp lại.', {
            'is_duplicate': True,
            'status': 'pending',
            'submitted_at': verification.submitted_at.strftime('%d/%m/%Y %H:%M') if verification.submitted_at else None,
            'version': verification.submission_version or 1,
            'error_list': ['Hồ sơ đã được gửi lại và đang chờ xét duyệt. Vui lòng không gửi lặp lại.']
        }

    can_rev, rev_err = can_user_revise_verification(user, verification)
    if not can_rev:
        return False, rev_err, {'error_list': [rev_err], 'status': current_status}

    # 2. XỬ LÝ LƯU CÁC TÀI LIỆU MINH CHỨNG THAY THẾ (NẾU CÓ TRONG FILES)
    if files:
        from werkzeug.datastructures import FileStorage
        for file_key in files:
            file_storage = files[file_key]
            if isinstance(file_storage, tuple):
                stream = file_storage[0]
                fname = file_storage[1]
                ctype = file_storage[2] if len(file_storage) > 2 else 'application/octet-stream'
                file_storage = FileStorage(stream=stream, filename=fname, content_type=ctype)
            if file_storage and getattr(file_storage, 'filename', ''):
                raw_type = file_key.replace('doc_file_', '').replace('file_', '')
                if raw_type in DOCUMENT_POLICIES:
                    ok_doc, saved_doc, doc_err = save_private_document(file_storage, user, doc_type=raw_type, verification=verification)
                    if not ok_doc:
                        return False, f"Lỗi lưu tài liệu {get_document_type_label(raw_type)}: {doc_err}", {
                            'document_error': doc_err,
                            'error_list': [f"Lỗi tải lên tài liệu {get_document_type_label(raw_type)}: {doc_err}"]
                        }

    # 3. CẬP NHẬT CÁC TRƯỜNG THÔNG TIN MỚI, BẢO TOÀN DỮ LIỆU ĐÃ KHAI BÁO
    draft_dict = verification.get_draft_dict()
    allowed_fields = [
        'full_name', 'phone', 'gender', 'dob', 'location', 'bio',
        'source_language', 'target_language', 'interpreting_direction', 'language_proficiency',
        'specializations', 'interpreting_types',
        'education_level', 'university', 'major', 'certificate_type', 'certificate_name',
        'current_position', 'notable_clients', 'featured_projects', 'notes'
    ]
    if form_data and isinstance(form_data, dict):
        for f in allowed_fields:
            if f in form_data and form_data[f] is not None:
                val = form_data[f]
                if isinstance(val, list):
                    val = ', '.join([str(v).strip() for v in val if v])
                elif isinstance(val, str):
                    val = val.strip()
                draft_dict[f] = val
                setattr(verification, f, val)

        if 'cert_year' in form_data and form_data['cert_year']:
            try:
                cy = int(form_data['cert_year'])
                draft_dict['cert_year'] = cy
                verification.cert_year = cy
            except (ValueError, TypeError):
                pass

        if 'experience_years' in form_data and form_data['experience_years'] != '':
            try:
                ey = int(form_data['experience_years'])
                draft_dict['experience_years'] = ey
                verification.experience_years = ey
            except (ValueError, TypeError):
                pass

        if verification.source_language and verification.target_language:
            verification.primary_language = f"{verification.source_language} ➔ {verification.target_language}"

        verification.draft_data = json.dumps(draft_dict, ensure_ascii=False)

    # 4. KIỂM TRA ĐẦY ĐỦ CÁC HẠNG MỤC ADMIN YÊU CẦU BỔ SUNG
    is_valid, missing_items, val_msg = validate_revision_submission(verification, form_data=form_data, files=files)
    if not is_valid:
        return False, val_msg, {
            'missing_items': missing_items,
            'error_list': [val_msg],
            'status': verification.status
        }

    # 5. TĂNG PHIÊN BẢN VÀ LẬP SNAPSHOT BẤT BIẾN MỚI
    prev_version = getattr(verification, 'submission_version', 0) or 1
    next_version = prev_version + 1
    now = datetime.utcnow()

    # So sánh Diff giữa phiên bản trước và phiên bản hiện tại
    prev_snapshot = verification.get_submitted_snapshot()
    prev_form = prev_snapshot.get('form_data', {}) if isinstance(prev_snapshot, dict) else {}
    diff_data = {}
    for k, v in draft_dict.items():
        old_v = prev_form.get(k)
        if str(v or '').strip() != str(old_v or '').strip():
            diff_data[k] = {'old': old_v, 'new': v}

    active_docs = [d for d in verification.documents if d.is_active]
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
        'previous_version': prev_version,
        'is_revision': True,
        'submitted_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone
        },
        'form_data': draft_dict,
        'documents': docs_snapshot,
        'diff': diff_data,
        'admin_feedback_addressed': verification.rejection_reason,
        'pledge_confirmed': True,
        'ip_address': ip_address,
        'user_agent': user_agent
    }
    snapshot_json = json.dumps(snapshot_data, ensure_ascii=False)

    # 6. CẬP NHẬT TRẠNG THÁI VÀ BẢO LƯU LỊCH SỬ
    verification.submission_version = next_version
    verification.submitted_at = now
    verification.submitted_snapshot = snapshot_json
    verification.status = 'pending'
    verification.rejection_reason = None
    verification.reviewed_by = None
    verification.reviewed_at = None
    verification.current_step = 6
    verification.updated_at = now

    sub_version_record = VerificationSubmissionVersion(
        verification_id=verification.id,
        user_id=user.id,
        version_number=next_version,
        status='pending',
        snapshot_data=snapshot_json,
        submitted_at=now,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(sub_version_record)

    # 7. CHUYỂN HỒ SƠ VỀ HÀNG ĐỢI XỬ LÝ (AdminNotification & Notification)
    try:
        admin_notif = AdminNotification(
            type='NEW_TRANSLATOR',
            title='Hồ sơ xác minh đã được bổ sung & gửi lại',
            message=f'Phiên dịch viên {user.name} ({user.email}) vừa bổ sung hồ sơ và gửi lại (Phiên bản #{next_version}).',
            url='/admin/translators?show=pending',
            related_id=verification.id
        )
        db.session.add(admin_notif)
    except Exception as e:
        print(f"[ADMIN NOTIF ERROR] {e}", file=sys.stderr)

    try:
        user_notif = Notification(
            user_id=user.id,
            type='VERIFICATION_RESUBMITTED',
            title='Hồ sơ bổ sung đã gửi lại thành công! ⏳',
            message=f'Hồ sơ bổ sung của bạn (Phiên bản #{next_version}) đã được chuyển về hàng đợi xét duyệt của Ban quản trị. Chúng tôi sẽ phản hồi trong vòng 24–48 giờ.',
            url='/account/verification/status'
        )
        db.session.add(user_notif)
    except Exception as e:
        print(f"[USER NOTIF ERROR] {e}", file=sys.stderr)

    # 8. COMMIT TRANSACTION AN TOÀN
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return False, f'Lỗi kết nối cơ sở dữ liệu khi gửi lại hồ sơ: {str(e)}', {
            'error_list': ['Lỗi kết nối cơ sở dữ liệu. Dữ liệu bổ sung của bạn được bảo lưu an toàn, vui lòng thử gửi lại.']
        }

    success_msg = f'Hồ sơ bổ sung (Phiên bản #{next_version}) đã được gửi lại thành công tới Ban quản trị! Thời gian xét duyệt dự kiến 24–48 giờ.'
    return True, success_msg, {
        'version': next_version,
        'previous_version': prev_version,
        'submitted_at': now.strftime('%d/%m/%Y %H:%M'),
        'status': 'pending',
        'diff': diff_data,
        'snapshot': snapshot_data
    }



