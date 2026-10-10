import os
import sys
import time
import secrets
import re
import json
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

