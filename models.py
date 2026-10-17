from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class LanguageItem(dict):
    def __init__(self, name, flag, cert, code, short_name=None):
        short = short_name or name.replace('Tiếng ', '')
        code_lower = code.lower()
        flag_svg = f"/static/flags/{code_lower}.svg"
        flag_alt = f"Quốc kỳ {short}"
        super().__init__(
            name=name,
            flag=flag,
            cert=cert,
            code=code,
            short_name=short,
            code_lower=code_lower,
            flag_svg=flag_svg,
            flag_alt=flag_alt,
        )
        self.__dict__ = self

    def __iter__(self):
        return iter((self['name'], self['flag'], self['cert']))


LANGUAGES = [
    LanguageItem('Tiếng Anh', '🇬🇧', 'IELTS / TOEIC / VSTEP', 'GB'),
    LanguageItem('Tiếng Nhật', '🇯🇵', 'JLPT N2 trở lên', 'JP'),
    LanguageItem('Tiếng Hàn', '🇰🇷', 'TOPIK 4 trở lên', 'KR'),
    LanguageItem('Tiếng Trung', '🇨🇳', 'HSK 5 trở lên', 'CN'),
    LanguageItem('Tiếng Pháp', '🇫🇷', 'DELF B2 trở lên', 'FR'),
    LanguageItem('Tiếng Đức', '🇩🇪', 'TestDaF / Goethe B2', 'DE'),
    LanguageItem('Tiếng Nga', '🇷🇺', 'ТРКИ B2 trở lên', 'RU'),
    LanguageItem('Tiếng Thái', '🇹🇭', 'Kiểm tra trực tiếp', 'TH'),
    LanguageItem('Tiếng Bồ Đào Nha', '🇵🇹', 'CELPE-Bras', 'PT'),
    LanguageItem('Tiếng Tây Ban Nha', '🇪🇸', 'DELE B2 trở lên', 'ES'),
]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)  # 'hirer', 'translator', 'admin'
    admin_role = db.Column(db.String(50), nullable=True) # 'super_admin', 'moderator', 'finance'
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_demo = db.Column(db.Boolean, default=False, index=True)
    email_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True) # Thời điểm xác minh thành công (dùng tính mốc 7 ngày đầu)
    avatar = db.Column(db.String(255), nullable=True)
    # Phân hệ Tài khoản Phiên dịch viên (Mục V)
    bio = db.Column(db.Text, nullable=True)
    date_of_birth = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    is_public_profile = db.Column(db.Boolean, default=True)
    phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship('TranslatorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    hirer_profile = db.relationship('HirerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    jobs_posted = db.relationship('Job', foreign_keys='Job.hirer_id', backref='hirer', lazy=True, cascade='all, delete-orphan')
    proposals = db.relationship('Proposal', backref='translator', lazy=True, cascade='all, delete-orphan')
    direct_messages_sent = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    preference = db.relationship('TranslatorPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(Notification.created_at)')

    # Phân hệ Tài khoản & Tiêu chí chuyên sâu (Mục V)
    interpreter_services = db.relationship('InterpreterService', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(InterpreterService.id)')
    interpreter_preference = db.relationship('InterpreterPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    notification_setting = db.relationship('NotificationSetting', backref='user', uselist=False, cascade='all, delete-orphan')
    user_sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(UserSession.last_active)')
    support_tickets = db.relationship('SupportTicket', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(SupportTicket.created_at)')

    @property
    def avatar_url(self):
        if self.avatar:
            avatar_val = str(self.avatar).strip()
            if (avatar_val.startswith('http://') or 
                avatar_val.startswith('https://') or 
                avatar_val.startswith('/') or 
                avatar_val.startswith('data:')):
                return avatar_val
            return f'/static/uploads/avatars/{avatar_val}'

        email_map = {
            'trans_kr@test.com': '/static/avatars/avatar_dung.jpg',
            'trans_ru@test.com': '/static/avatars/avatar_ha.jpg',
            'trans_jp@test.com': '/static/avatars/avatar_bich.jpg',
            'trans_en@test.com': '/static/avatars/avatar_cuong.jpg',
            'trans_cn@test.com': '/static/avatars/avatar_duc.jpg',
            'trans_fr@test.com': '/static/avatars/avatar_huong.jpg',
            'trans_de@test.com': '/static/avatars/avatar_khoa.jpg',
            'trans_th@test.com': '/static/avatars/avatar_nam.jpg',
            'trans_pt@test.com': '/static/avatars/avatar_huy.jpg',
            'trans_es@test.com': '/static/avatars/avatar_lananh.jpg',
        }
        name_map = {
            'phạm thị dung': '/static/avatars/avatar_dung.jpg',
            'đặng thị thanh hà': '/static/avatars/avatar_ha.jpg',
            'trần thị bích': '/static/avatars/avatar_bich.jpg',
            'lê văn cường': '/static/avatars/avatar_cuong.jpg',
            'hoàng minh đức': '/static/avatars/avatar_duc.jpg',
            'nguyễn thị mai hương': '/static/avatars/avatar_huong.jpg',
            'vũ đình khoa': '/static/avatars/avatar_khoa.jpg',
            'lý hoàng nam': '/static/avatars/avatar_nam.jpg',
            'bùi quang huy': '/static/avatars/avatar_huy.jpg',
            'ngô thị lan anh': '/static/avatars/avatar_lananh.jpg',
        }
        if self.email and self.email.lower() in email_map:
            return email_map[self.email.lower()]
        if self.name and self.name.strip().lower() in name_map:
            return name_map[self.name.strip().lower()]
        return None

    @property
    def latest_verification(self):
        """Trả về yêu cầu xác minh mới nhất của người dùng (nếu có)."""
        try:
            if hasattr(self, 'verifications') and self.verifications:
                return self.verifications[0]
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            return None
        return None

    @property
    def is_verified(self):
        """Kiểm tra tài khoản đã xác minh định danh chưa."""
        if self.role == 'translator':
            return bool(self.profile and self.profile.is_verified)
        elif self.role == 'hirer':
            return bool(self.hirer_profile and self.hirer_profile.is_verified)
        return False

    @property
    def is_phone_verified(self):
        """Kiểm tra số điện thoại đã xác thực chưa."""
        return bool(getattr(self, 'phone_verified', False) or (self.is_verified and self.phone))

    @property
    def is_authenticated(self):
        """Khả năng tương thích kiểm tra đăng nhập."""
        return True

    @property
    def is_anonymous(self):
        """Khả năng tương thích kiểm tra người dùng vô danh."""
        return False

    @property
    def subscription_tier(self):
        """Tên mã gói dịch vụ hiện tại (Mục 5.5). Mặc định là 'standard' (Gói Tiêu Chuẩn)."""
        return 'standard'

    @property
    def subscription_info(self):
        """Thông tin chi tiết về gói dịch vụ & quyền lợi đang sử dụng (Mục 5.5)."""
        tier = self.subscription_tier
        if tier == 'pro':
            return {
                'tier': 'pro',
                'name': 'Gói Phiên Dịch Viên Chuyên Nghiệp (Pro)',
                'short_name': 'Gói Pro',
                'badge_color': 'indigo',
                'duration': '30 ngày',
                'expires_at_display': 'Còn 30 ngày',
                'is_pro': True,
                'search_priority': 'Ưu tiên hiển thị Top 1 kết quả tìm kiếm',
                'notification_speed': 'Tức thì (Real-time)',
                'glossary_access': 'Mở khóa không giới hạn'
            }
        return {
            'tier': 'standard',
            'name': 'Gói Tiêu Chuẩn (Free)',
            'short_name': 'Gói Tiêu Chuẩn',
            'badge_color': 'slate',
            'duration': 'Vô thời hạn',
            'expires_at_display': 'Vô thời hạn',
            'is_pro': False,
            'search_priority': 'Tiêu chuẩn (Thứ hạng thông thường)',
            'notification_speed': 'Thông thường (Web & Email)',
            'glossary_access': 'Chỉ dành cho gói Pro'
        }


class TranslatorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    bio = db.Column(db.Text)
    languages = db.Column(db.String(300))
    badges = db.Column(db.String(200))
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    total_jobs = db.Column(db.Integer, default=0)
    response_time = db.Column(db.String(50), default='2 giờ')
    is_verified = db.Column(db.Boolean, default=False)
    certificates = db.Column(db.Text)

    # Cấu hình công khai & quyền riêng tư hồ sơ
    is_public = db.Column(db.Boolean, default=True)
    is_cv_public = db.Column(db.Boolean, default=False)

    # Cặp ngôn ngữ & Chiều phiên dịch
    source_language = db.Column(db.String(100), nullable=True)
    target_language = db.Column(db.String(100), nullable=True)
    interpreting_direction = db.Column(db.String(50), nullable=True)
    language_proficiency = db.Column(db.String(50), nullable=True)

    # Lĩnh vực chuyên môn & Hình thức làm việc
    specializations = db.Column(db.Text, nullable=True)
    interpreting_types = db.Column(db.Text, nullable=True)
    work_modes = db.Column(db.String(255), nullable=True)

    # Học vấn & Chứng chỉ công khai
    education_level = db.Column(db.String(100), nullable=True)
    university = db.Column(db.String(255), nullable=True)
    major = db.Column(db.String(255), nullable=True)
    cert_name = db.Column(db.String(255), nullable=True)
    cert_year = db.Column(db.Integer, nullable=True)

    # Kinh nghiệm nghề nghiệp
    experience_years = db.Column(db.Integer, default=0)
    current_position = db.Column(db.String(255), nullable=True)
    notable_clients = db.Column(db.Text, nullable=True)
    featured_projects = db.Column(db.Text, nullable=True)

    # Dữ liệu demo & Định giá / Khả dụng bổ sung
    is_demo = db.Column(db.Boolean, default=False, index=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    daily_rate = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), default='VND')
    employment_preference = db.Column(db.String(100), nullable=True)
    availability_status = db.Column(db.String(100), default='Sẵn sàng nhận việc')
    service_areas = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), default='Việt Nam')
    native_language = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    services = db.relationship('Service', backref='profile', lazy=True)

    @property
    def display_hourly_rate(self):
        """Định dạng mức giá theo giờ hiển thị."""
        if self.hourly_rate:
            curr = self.currency or 'VND'
            if curr == 'USD':
                return f"${int(self.hourly_rate)}/giờ"
            return f"{int(self.hourly_rate):,}".replace(',', '.') + " VND/giờ"
        return None

    @property
    def display_daily_rate(self):
        """Định dạng mức giá theo ngày hiển thị."""
        if self.daily_rate:
            curr = self.currency or 'VND'
            if curr == 'USD':
                return f"${int(self.daily_rate)}/ngày"
            return f"{int(self.daily_rate):,}".replace(',', '.') + " VND/ngày"
        return None

    @property
    def display_rate_summary(self):
        """Tóm tắt mức giá theo giờ / ngày."""
        parts = []
        if self.display_hourly_rate:
            parts.append(self.display_hourly_rate)
        if self.display_daily_rate:
            parts.append(self.display_daily_rate)
        return " · ".join(parts) if parts else "Thỏa thuận theo dự án"

    @property
    def display_country(self):
        """Quốc gia làm việc."""
        return self.country or 'Việt Nam'

    @property
    def display_location(self):
        """Địa điểm công tác chính."""
        if self.user and self.user.city:
            return self.user.city
        return self.service_areas or 'Hà Nội'

    @property
    def display_native_language(self):
        """Ngôn ngữ mẹ đẻ."""
        if self.native_language:
            return self.native_language
        return self.display_source_language

    @property
    def avatar_url(self):
        try:
            return self.user.avatar_url if self.user else None
        except Exception:
            return None

    @property
    def latest_verification(self):
        """Trả về yêu cầu xác minh mới nhất của phiên dịch viên."""
        try:
            return self.user.latest_verification if self.user else None
        except Exception:
            return None

    @property
    def display_source_language(self):
        """Ngôn ngữ nguồn chính (ưu tiên trường riêng, fallback xác minh hoặc languages)."""
        if self.source_language and self.source_language.strip():
            return self.source_language.strip()
        if self.latest_verification and self.latest_verification.source_language:
            return self.latest_verification.source_language.strip()
        if self.languages:
            parts = [l.strip() for l in self.languages.split(',') if l.strip()]
            if parts:
                return parts[0]
        return 'Tiếng Việt'

    @property
    def display_target_language(self):
        """Ngôn ngữ đích chính (ưu tiên trường riêng, fallback xác minh hoặc languages)."""
        if self.target_language and self.target_language.strip():
            return self.target_language.strip()
        if self.latest_verification and self.latest_verification.target_language:
            return self.latest_verification.target_language.strip()
        if self.languages:
            parts = [l.strip() for l in self.languages.split(',') if l.strip()]
            if len(parts) > 1:
                return parts[1]
            elif len(parts) == 1 and parts[0] != 'Tiếng Anh':
                return 'Tiếng Anh'
        return 'Tiếng Anh'

    @property
    def display_interpreting_direction(self):
        """Chiều phiên dịch."""
        if self.interpreting_direction and self.interpreting_direction.strip():
            return self.interpreting_direction.strip()
        if self.latest_verification and self.latest_verification.interpreting_direction:
            return self.latest_verification.interpreting_direction.strip()
        return 'Hai chiều (Song phương)'

    @property
    def display_language_proficiency(self):
        """Mức độ thành thạo ngôn ngữ."""
        if self.language_proficiency and self.language_proficiency.strip():
            return self.language_proficiency.strip()
        if self.latest_verification and self.latest_verification.language_proficiency:
            return self.latest_verification.language_proficiency.strip()
        return 'Chuyên nghiệp (C2/C1)'

    @property
    def display_specializations(self):
        """Danh sách lĩnh vực chuyên môn dạng list."""
        val = self.specializations
        if not val and self.latest_verification and self.latest_verification.specializations:
            val = self.latest_verification.specializations
        if not val and self.badges:
            val = self.badges
        if val:
            if isinstance(val, list):
                return val
            return [s.strip() for s in val.split(',') if s.strip()]
        return ['Thương mại & Hợp đồng', 'Hội nghị & Sự kiện']

    @property
    def display_interpreting_types(self):
        """Danh sách hình thức phiên dịch dạng list."""
        val = self.interpreting_types
        if not val and self.latest_verification and self.latest_verification.interpreting_types:
            val = self.latest_verification.interpreting_types
        if val:
            if isinstance(val, list):
                return val
            return [s.strip() for s in val.split(',') if s.strip()]
        return ['Phiên dịch nối tiếp (Consecutive)', 'Phiên dịch tháp tùng (Escort)']

    @property
    def display_work_modes(self):
        """Danh sách phương thức làm việc (trực tiếp / từ xa...)."""
        val = self.work_modes
        if val:
            if isinstance(val, list):
                return val
            return [s.strip() for s in val.split(',') if s.strip()]
        return ['Trực tiếp tại địa điểm (On-site)', 'Trực tuyến / Từ xa (Online)']

    @property
    def display_experience_years(self):
        """Số năm kinh nghiệm làm nghề thực tế."""
        if self.experience_years is not None and self.experience_years > 0:
            return self.experience_years
        if self.latest_verification and self.latest_verification.experience_years:
            return self.latest_verification.experience_years
        return 3

    @property
    def display_current_position(self):
        """Chức danh chuyên môn hiện tại."""
        if self.current_position and self.current_position.strip():
            return self.current_position.strip()
        if self.latest_verification and self.latest_verification.current_position:
            return self.latest_verification.current_position.strip()
        return self.title or 'Phiên dịch viên chuyên nghiệp'

    @property
    def display_education_level(self):
        """Trình độ học vấn."""
        if self.education_level and self.education_level.strip():
            return self.education_level.strip()
        if self.latest_verification and self.latest_verification.education_level:
            return self.latest_verification.education_level.strip()
        return 'Cử nhân'

    @property
    def display_university(self):
        """Trường đại học đào tạo."""
        if self.university and self.university.strip():
            return self.university.strip()
        if self.latest_verification and self.latest_verification.university:
            return self.latest_verification.university.strip()
        return None

    @property
    def display_major(self):
        """Chuyên ngành đào tạo."""
        if self.major and self.major.strip():
            return self.major.strip()
        if self.latest_verification and self.latest_verification.major:
            return self.latest_verification.major.strip()
        return None

    @property
    def display_cert_name(self):
        """Tên chứng chỉ ngoại ngữ."""
        if self.cert_name and self.cert_name.strip():
            return self.cert_name.strip()
        if self.latest_verification and self.latest_verification.certificate_name:
            return self.latest_verification.certificate_name.strip()
        return None

    @property
    def display_cert_year(self):
        """Năm cấp chứng chỉ."""
        if self.cert_year:
            return self.cert_year
        if self.latest_verification and self.latest_verification.cert_year:
            return self.latest_verification.cert_year
        return None

    @property
    def display_notable_clients(self):
        """Danh sách đối tác / khách hàng tiêu biểu."""
        val = self.notable_clients
        if not val and self.latest_verification and self.latest_verification.notable_clients:
            val = self.latest_verification.notable_clients
        return val

    @property
    def display_featured_projects(self):
        """Danh sách dự án hoặc sự kiện tiêu biểu."""
        val = self.featured_projects
        if not val and self.latest_verification and self.latest_verification.featured_projects:
            val = self.latest_verification.featured_projects
        return val

    @property
    def active_cv_document(self):
        """
        Trả về tệp CV đang hoạt động của phiên dịch viên (bất kể cờ is_cv_public bật hay tắt).
        Dùng cho chính chủ, Quản trị viên hoặc Người thuê có ứng viên nộp hồ sơ.
        """
        try:
            doc = VerificationDocument.query.filter_by(
                user_id=self.user_id,
                document_type='cv',
                is_active=True
            ).order_by(VerificationDocument.created_at.desc()).first()
            if doc:
                return doc
        except Exception:
            pass

        if self.latest_verification and hasattr(self.latest_verification, 'documents'):
            for doc in self.latest_verification.documents:
                if doc.document_type == 'cv' and getattr(doc, 'is_active', True):
                    return doc

        if self.user and hasattr(self.user, 'verifications') and self.user.verifications:
            for v in self.user.verifications:
                if hasattr(v, 'documents'):
                    for doc in v.documents:
                        if doc.document_type == 'cv' and getattr(doc, 'is_active', True):
                            return doc
        return None

    @property
    def public_cv_document(self):
        """
        Trả về đối tượng tài liệu CV hợp lệ khi người dùng CHỦ ĐỘNG chọn công khai (is_cv_public=True).
        Chỉ tìm tài liệu loại 'cv', không bao giờ lấy tài liệu id_card hay các loại riêng tư.
        """
        if not self.is_cv_public:
            return None
        return self.active_cv_document

    @property
    def has_public_cv(self):
        """Kiểm tra xem hồ sơ có CV được công khai và khả dụng hay không."""
        return self.public_cv_document is not None

    def is_eligible_for_public(self):
        """
        Kiểm tra xem hồ sơ có đáp ứng đủ điều kiện tối thiểu để xuất hiện công khai:
        - Có thông tin tài khoản người dùng và tên hiển thị.
        - Đã có thông tin chức danh, ngôn ngữ hoặc giới thiệu (không phải hồ sơ trống).
        """
        if not self.user:
            return False, 'Không tìm thấy thông tin tài khoản liên kết.'
        if not self.user.name or not self.user.name.strip():
            return False, 'Chưa thiết lập tên hiển thị.'
        if not self.title and not self.languages and not self.bio:
            return False, 'Hồ sơ chưa có thông tin chức danh, ngôn ngữ hoặc lời giới thiệu.'
        return True, None

    def can_view_public(self, viewer=None, is_admin_session=False):
        """
        Kiểm tra quyền xem hồ sơ của một đối tượng người xem (viewer):
        Trả về tuple: (can_view, is_preview, reason)
        - can_view: True nếu được phép xem toàn bộ hồ sơ (dù là public hay preview).
        - is_preview: True nếu đang xem ở chế độ Xem trước (Preview Mode).
        - reason: Lý do hồ sơ không công khai (nếu có).
        """
        is_owner = bool(viewer and self.user_id == getattr(viewer, 'id', None))
        is_admin = bool((viewer and getattr(viewer, 'is_admin', False)) or is_admin_session)

        # 1. Tài khoản bị vô hiệu hóa hoặc giới hạn
        if self.user and not getattr(self.user, 'is_active', True):
            if is_admin:
                return True, True, 'Tài khoản người dùng đang bị giới hạn hoặc vô hiệu hóa bởi Quản trị viên.'
            return False, False, 'Tài khoản phiên dịch viên này hiện đang bị tạm khóa hoặc giới hạn quyền bởi hệ thống.'

        # 2. Điều kiện tối thiểu để công khai
        is_eligible, ineligibility_reason = self.is_eligible_for_public()
        if not is_eligible:
            if is_owner or is_admin:
                return True, True, f'Hồ sơ chưa đủ điều kiện công khai: {ineligibility_reason}'
            return False, False, 'Hồ sơ đang trong quá trình hoàn thiện thông tin và chưa được kích hoạt công khai.'

        # 3. Chế độ riêng tư (is_public == False)
        is_pub = getattr(self, 'is_public', True)
        if is_pub is False:
            if is_owner or is_admin:
                return True, True, 'Hồ sơ đang ở chế độ Riêng tư (Ẩn trên danh bạ và tìm kiếm).'
            return False, False, 'Phiên dịch viên hiện chưa công khai hồ sơ nghề nghiệp này.'

        # 4. Hồ sơ công khai bình thường
        return True, False, None


class TranslatorPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    languages = db.Column(db.Text, default='')
    language_pairs = db.Column(db.Text, default='')
    service_types = db.Column(db.Text, default='')
    # Phục vụ ghép cặp với hồ sơ khách (xem services/matching.py)
    specialties = db.Column(db.Text, default='')    # CSV nhãn HIRING_FIELDS
    city = db.Column(db.String(100))
    work_mode = db.Column(db.String(20))            # onsite / online / both
    offers_certified = db.Column(db.Boolean, default=False)
    notify_new_jobs = db.Column(db.Boolean, default=True)
    notify_messages = db.Column(db.Boolean, default=True)
    notify_contracts = db.Column(db.Boolean, default=True)
    notify_reviews = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HirerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    title = db.Column(db.String(100))
    company = db.Column(db.String(200))
    location = db.Column(db.String(100))
    rating = db.Column(db.Float, default=0.0)

    # ── Hồ sơ mở rộng: 'business' (Doanh nghiệp / Tổ chức) hoặc 'individual' (Cá nhân)
    account_type = db.Column(db.String(20), default='individual')
    # Doanh nghiệp: `company` = tên công ty, `title` = chức vụ người đại diện
    tax_code = db.Column(db.String(13))
    industry = db.Column(db.Text)  # nhiều lĩnh vực, cách nhau bởi ", "
    company_size = db.Column(db.String(20))
    address = db.Column(db.String(300))
    company_email = db.Column(db.String(150))
    website = db.Column(db.String(300))
    hotline = db.Column(db.String(30))
    rep_name = db.Column(db.String(100))
    about = db.Column(db.Text)
    # Cá nhân
    hiring_field = db.Column(db.Text)       # nhiều lĩnh vực, cách nhau bởi ", "
    hiring_languages = db.Column(db.Text)   # ngôn ngữ thường cần
    hiring_services = db.Column(db.Text)    # hình thức dịch thường thuê
    # Dùng chung
    contact_phone = db.Column(db.String(30))
    logo = db.Column(db.Text)  # logo công ty / ảnh đại diện, lưu dạng data URI (đã giới hạn dung lượng)

    # Đánh giá nhận được từ phiên dịch viên và nhu cầu thuê (phục vụ gợi ý phiên dịch viên)
    total_reviews = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default='unverified', index=True) # unverified, pending, needs_revision, verified, rejected, revoked, suspended
    verified_at = db.Column(db.DateTime, nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account_number = db.Column(db.String(50), nullable=True)
    authorization_doc_url = db.Column(db.String(500), nullable=True)
    verification_checklist_data = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    work_mode = db.Column(db.String(20))            # onsite / online / both
    hiring_frequency = db.Column(db.String(20))     # one_time / occasional / regular
    typical_budget_min = db.Column(db.Integer)
    typical_budget_max = db.Column(db.Integer)
    needs_nda = db.Column(db.Boolean, default=False)
    needs_certified = db.Column(db.Boolean, default=False)
    special_requirements = db.Column(db.Text)


    @property
    def is_business(self):
        return self.account_type == 'business'

    @property
    def avatar_url(self):
        """Ảnh đại diện hoặc logo của hồ sơ người thuê."""
        try:
            if self.logo:
                logo_val = str(self.logo).strip()
                if logo_val:
                    if logo_val.startswith('http://') or logo_val.startswith('https://') or logo_val.startswith('/') or logo_val.startswith('data:'):
                        return logo_val
                    return f"/static/uploads/logos/{logo_val}"
            return self.user.avatar_url if self.user else None
        except Exception:
            return None


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('translator_profile.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    languages = db.Column(db.String(100))
    category = db.Column(db.String(100))
    basic_price = db.Column(db.Integer, nullable=False)
    standard_price = db.Column(db.Integer)
    premium_price = db.Column(db.Integer)
    basic_delivery = db.Column(db.String(50), default='3 ngày')
    standard_delivery = db.Column(db.String(50), default='2 ngày')
    premium_delivery = db.Column(db.String(50), default='1 ngày')


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hirer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    category_group = db.Column(db.String(50))
    service_type = db.Column(db.String(100))
    source_lang = db.Column(db.String(50))
    target_lang = db.Column(db.String(50))
    budget_type = db.Column(db.String(20))
    budget_min = db.Column(db.Integer)
    budget_max = db.Column(db.Integer)
    event_date = db.Column(db.String(100))
    event_time_start = db.Column(db.String(10))
    event_time_end = db.Column(db.String(10))
    event_location = db.Column(db.String(200))
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default='open', index=True)
    is_flagged = db.Column(db.Boolean, default=False)
    moderation_status = db.Column(db.String(20), default='pending', index=True) # pending, approved, needs_revision, rejected, flagged, archived
    moderation_checklist_data = db.Column(db.Text, nullable=True)
    moderation_notes = db.Column(db.Text, nullable=True)
    moderated_at = db.Column(db.DateTime, nullable=True)
    moderated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    submission_version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Quản lý yêu cầu (Task 02)
    specialty = db.Column(db.String(100))          # lĩnh vực chuyên môn
    word_count = db.Column(db.Integer)             # số từ / khối lượng
    extra_requirements = db.Column(db.Text)        # yêu cầu bổ sung
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

    attachments = db.relationship('JobAttachment', backref='job', lazy=True, cascade='all, delete-orphan')
    moderator = db.relationship('User', foreign_keys=[moderated_by], backref='moderated_jobs', lazy=True)
    proposals = db.relationship('Proposal', backref='job', lazy=True, cascade='all, delete-orphan')
    contract = db.relationship('Contract', backref='job', uselist=False, cascade='all, delete-orphan')
    schedules = db.relationship('JobSchedule', backref='job', lazy=True, cascade='all, delete-orphan', order_by='JobSchedule.scheduled_date')


    @property
    def display_category_group(self):
        if self.category_group:
            return self.category_group
        if self.category in ['Dịch viết']:
            return 'translation'
        return 'interpretation_other'

    @property
    def display_service_type(self):
        if self.service_type:
            return self.service_type
        mapping = {
            'Dịch viết': 'document_translation',
            'Hội nghị': 'conference',
            'Tháp tùng': 'escort',
            'Đàm phán': 'meeting',
            'Pháp lý': 'other_interpretation'
        }
        return mapping.get(self.category, 'other_interpretation')

    def display_category_text(self, lang='vi'):
        from translations import t as t_lookup
        group_key = 'translation' if self.display_category_group == 'translation' else 'interpretation_other'
        group_text = t_lookup(f'job_category.{group_key}', lang)
        known_types = (
            'document_translation', 'website_translation', 'subtitle', 'proofreading',
            'localization', 'other_translation', 'conference', 'meeting', 'business',
            'travel', 'escort', 'event', 'other_interpretation'
        )
        if self.display_service_type in known_types:
            type_text = t_lookup(f'job_category.{self.display_service_type}', lang)
        else:
            type_text = self.category or t_lookup('job_category.other', lang)
        return f"{group_text} - {type_text}"

    @property
    def applicant_count(self):
        return Proposal.query.filter_by(job_id=self.id).count()


class JobAttachment(db.Model):
    """Tệp tham khảo của yêu cầu. Lưu ngoài thư mục static, chỉ tải qua route có kiểm quyền."""
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FavoriteTranslator(db.Model):
    """Phiên dịch viên được khách thuê lưu (theo tài khoản, lưu bền vững)."""
    __table_args__ = (db.UniqueConstraint('hirer_id', 'translator_id', name='uq_favorite_hirer_translator'),)
    id = db.Column(db.Integer, primary_key=True)
    hirer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# ─── JOB SCHEDULE MODEL (TASK 1 / TASK 2) ────────────────────────────────────

class JobSchedule(db.Model):
    """
    Lưu lịch làm việc chi tiết cho từng ngày của một Job.
    Mỗi ngày = một bản ghi, với giờ bắt đầu/kết thúc riêng.

    Backward compatibility:
    - Nếu Job có JobSchedule entries → dùng JobSchedule.
    - Nếu không có → fallback về legacy fields (event_date, event_time_start, event_time_end).
    """
    __tablename__ = 'job_schedule'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer,
        db.ForeignKey('job.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    scheduled_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)   # "HH:MM"
    end_time = db.Column(db.String(10), nullable=False)     # "HH:MM"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Serialize sang dict để dùng trong API / template."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'scheduled_date': self.scheduled_date.strftime('%Y-%m-%d') if self.scheduled_date else None,
            'scheduled_date_display': self.scheduled_date.strftime('%d/%m/%Y') if self.scheduled_date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }


# ─── SCHEDULE HELPERS (TASK 1) ────────────────────────────────────────────────

def get_job_schedule_entries(job):
    """
    Trả về danh sách schedule entries cho một Job.

    Ưu tiên:
    1. JobSchedule entries (multi-day với giờ riêng)
    2. Fallback: legacy fields (event_date, event_time_start, event_time_end)

    Returns:
        list[dict] với keys: scheduled_date (date), start_time (str), end_time (str),
                              scheduled_date_display (str)
        Trả về list rỗng nếu không có dữ liệu hợp lệ.
    """
    # Ưu tiên JobSchedule entries
    if job.schedules:
        return [s.to_dict() for s in sorted(job.schedules, key=lambda s: s.scheduled_date)]

    # Fallback: legacy fields
    event_date = getattr(job, 'event_date', None)
    event_time_start = getattr(job, 'event_time_start', None)
    event_time_end = getattr(job, 'event_time_end', None)

    if not event_date:
        return []

    # Parse date range ("2024-11-30 to 2024-12-02" hoặc single date)
    try:
        from services.schedule import parse_date_range
        dates = parse_date_range(event_date)
    except Exception:
        return []

    if not dates:
        return []

    entries = []
    for d in dates:
        entries.append({
            'id': None,
            'job_id': job.id,
            'scheduled_date': d.strftime('%Y-%m-%d'),
            'scheduled_date_display': d.strftime('%d/%m/%Y'),
            'start_time': event_time_start or '',
            'end_time': event_time_end or '',
            'is_legacy': True,
        })
    return entries


def validate_schedule_entries(entries):
    """
    Validate danh sách schedule entries từ form hoặc API.

    Args:
        entries: list[dict] với keys: scheduled_date (str), start_time (str), end_time (str)

    Returns:
        (is_valid: bool, errors: list[dict])
        errors: list[{'index': int, 'field': str, 'message': str}]

    Raises không có exception — luôn trả về tuple.
    """
    from datetime import datetime, date as date_type

    if not entries:
        return False, [{'index': 0, 'field': 'entries', 'message': 'Phải có ít nhất một ngày làm việc.'}]

    errors = []
    seen_dates = set()
    DATE_FMTS = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    TIME_FMTS = ['%H:%M', '%H:%M:%S']

    def _parse_date(val):
        for fmt in DATE_FMTS:
            try:
                return datetime.strptime(str(val).strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_time(val):
        for fmt in TIME_FMTS:
            try:
                return datetime.strptime(str(val).strip(), fmt).time()
            except ValueError:
                continue
        return None

    for i, entry in enumerate(entries):
        raw_date = (entry.get('scheduled_date') or '').strip()
        raw_start = (entry.get('start_time') or '').strip()
        raw_end = (entry.get('end_time') or '').strip()

        # Validate date
        parsed_date = _parse_date(raw_date) if raw_date else None
        if not raw_date:
            errors.append({'index': i, 'field': 'scheduled_date', 'message': f'Ngày {i+1} chưa được chọn.'})
        elif parsed_date is None:
            errors.append({'index': i, 'field': 'scheduled_date', 'message': f'Ngày {i+1} không hợp lệ.'})
        elif parsed_date < datetime.utcnow().date():
            errors.append({'index': i, 'field': 'scheduled_date', 'message': f'Ngày {i+1} không được nằm trong quá khứ.'})
        elif raw_date in seen_dates or (parsed_date and parsed_date.strftime('%Y-%m-%d') in seen_dates):
            errors.append({'index': i, 'field': 'scheduled_date', 'message': f'Ngày {i+1} đã bị trùng với một ngày khác.'})
        else:
            if parsed_date:
                seen_dates.add(parsed_date.strftime('%Y-%m-%d'))

        # Validate start_time
        parsed_start = _parse_time(raw_start) if raw_start else None
        if not raw_start:
            errors.append({'index': i, 'field': 'start_time', 'message': f'Ngày {i+1} chưa có giờ bắt đầu.'})
        elif parsed_start is None:
            errors.append({'index': i, 'field': 'start_time', 'message': f'Giờ bắt đầu ngày {i+1} không hợp lệ.'})

        # Validate end_time
        parsed_end = _parse_time(raw_end) if raw_end else None
        if not raw_end:
            errors.append({'index': i, 'field': 'end_time', 'message': f'Ngày {i+1} chưa có giờ kết thúc.'})
        elif parsed_end is None:
            errors.append({'index': i, 'field': 'end_time', 'message': f'Giờ kết thúc ngày {i+1} không hợp lệ.'})

        # Validate start < end
        if parsed_start and parsed_end and parsed_end <= parsed_start:
            errors.append({'index': i, 'field': 'end_time', 'message': f'Ngày {i+1}: Giờ kết thúc phải sau giờ bắt đầu.'})

    is_valid = len(errors) == 0
    return is_valid, errors


class Proposal(db.Model):
    __table_args__ = (
        db.UniqueConstraint('job_id', 'translator_id', name='uq_proposal_job_translator'),
    )
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cover_letter = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    time_estimate = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, not_selected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    client_note = db.Column(db.Text, nullable=True)
    withdrawn_reason = db.Column(db.String(255), nullable=True)
    # Quản lý báo giá (Task 04)
    scope = db.Column(db.Text)              # phạm vi công việc
    delivery_terms = db.Column(db.Text)     # điều kiện bàn giao
    revision_terms = db.Column(db.Text)     # điều kiện chỉnh sửa
    valid_until = db.Column(db.Date)        # báo giá có hiệu lực đến
    responded_at = db.Column(db.DateTime)   # lúc khách phản hồi
    response_note = db.Column(db.Text)      # ghi chú khi từ chối

    @property
    def effective_status(self):
        """Trả về 1 trong 8 mã trạng thái chuẩn nghiệp vụ:
        - pending: Chờ phản hồi
        - reviewing: Đang xem xét
        - needs_response: Cần phản hồi
        - selected: Được chọn / Chờ xác nhận
        - accepted: Đã nhận
        - rejected: Không được chọn
        - withdrawn: Đã rút đơn
        - job_closed: Tin đã đóng
        """
        raw = (self.status or 'pending').lower().strip()
        if raw == 'withdrawn':
            return 'withdrawn'
        if raw == 'accepted':
            return 'accepted'
        if raw == 'rejected':
            return 'rejected'
        if raw == 'selected':
            return 'selected'
        if raw == 'needs_response':
            return 'needs_response'
        if raw == 'reviewing':
            return 'reviewing'

        # Nếu đang pending nhưng tin đã đóng / hết hạn / đã chốt ứng viên khác
        if self.job:
            from datetime import date
            if self.job.status == 'closed':
                return 'job_closed'
            if self.job.status == 'contracted' and raw != 'accepted':
                return 'job_closed'
            if self.job.deadline and self.job.deadline < date.today():
                return 'job_closed'
        return 'pending'

    @property
    def status_info(self):
        meta = {
            'pending': {
                'code': 'pending',
                'label': 'Chờ phản hồi',
                'badge_class': 'bg-amber-50 text-amber-700 border-amber-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
                'desc': 'Đơn đã gửi và đang chờ bên tuyển dụng phản hồi.',
                'can_withdraw': True,
                'can_update': True,
                'can_confirm': False,
            },
            'reviewing': {
                'code': 'reviewing',
                'label': 'Đang xem xét',
                'badge_class': 'bg-blue-50 text-blue-700 border-blue-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>',
                'desc': 'Bên tuyển dụng đang đánh giá hồ sơ và đề xuất của bạn.',
                'can_withdraw': True,
                'can_update': True,
                'can_confirm': False,
            },
            'needs_response': {
                'code': 'needs_response',
                'label': 'Cần phản hồi',
                'badge_class': 'bg-purple-50 text-purple-700 border-purple-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>',
                'desc': 'Bên tuyển dụng có câu hỏi hoặc yêu cầu bổ sung thông tin cho đề xuất.',
                'can_withdraw': True,
                'can_update': True,
                'can_confirm': False,
            },
            'selected': {
                'code': 'selected',
                'label': 'Được chọn / Chờ xác nhận',
                'badge_class': 'bg-emerald-50 text-emerald-800 border-emerald-300 ring-2 ring-emerald-400/20 font-extrabold',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
                'desc': 'Chúc mừng! Bạn đã được chọn. Vui lòng xác nhận nhận việc để hoàn tất tạo hợp đồng.',
                'can_withdraw': True,
                'can_update': False,
                'can_confirm': True,
            },
            'accepted': {
                'code': 'accepted',
                'label': 'Đã nhận',
                'badge_class': 'bg-teal-50 text-teal-800 border-teal-200/80 font-bold',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-teal-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
                'desc': 'Đã hoàn tất xác nhận nhận việc. Công việc đang trong giai đoạn thực hiện.',
                'can_withdraw': False,
                'can_update': False,
                'can_confirm': False,
            },
            'rejected': {
                'code': 'rejected',
                'label': 'Không được chọn',
                'badge_class': 'bg-rose-50 text-rose-700 border-rose-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
                'desc': 'Đơn ứng tuyển chưa phù hợp với yêu cầu lần này của bên tuyển dụng.',
                'can_withdraw': False,
                'can_update': False,
                'can_confirm': False,
            },
            'withdrawn': {
                'code': 'withdrawn',
                'label': 'Đã rút đơn',
                'badge_class': 'bg-slate-100 text-slate-600 border-slate-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>',
                'desc': 'Bạn đã chủ động rút đơn ứng tuyển.',
                'can_withdraw': False,
                'can_update': False,
                'can_confirm': False,
            },
            'job_closed': {
                'code': 'job_closed',
                'label': 'Tin đã đóng',
                'badge_class': 'bg-slate-100 text-slate-500 border-slate-200/80',
                'icon_svg': '<svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>',
                'desc': 'Tin tuyển dụng này đã đóng hoặc đã hết hạn nhận hồ sơ.',
                'can_withdraw': False,
                'can_update': False,
                'can_confirm': False,
            }
        }
        return meta.get(self.effective_status, meta['pending'])

    @property
    def timeline(self):
        """Lịch sử thay đổi trạng thái và các mốc thời gian của đơn."""
        events = []
        events.append({
            'title': 'Đã nộp đơn ứng tuyển',
            'time': self.created_at,
            'desc': f'Mức thù lao đề xuất: {self.price:,.0f}đ · Thời gian: {self.time_estimate or "Thỏa thuận"}',
            'type': 'submit'
        })
        updated = getattr(self, 'updated_at', None)
        if updated and (updated - self.created_at).total_seconds() > 60:
            events.append({
                'title': 'Cập nhật đề xuất',
                'time': updated,
                'desc': 'Đã cập nhật lại nội dung đề xuất hoặc bổ sung thông tin.',
                'type': 'update'
            })
        eff = self.effective_status
        if eff == 'reviewing':
            events.append({
                'title': 'Đang được xem xét',
                'time': updated or self.created_at,
                'desc': 'Bên tuyển dụng đã tiếp nhận và đang đánh giá hồ sơ.',
                'type': 'reviewing'
            })
        elif eff == 'needs_response':
            events.append({
                'title': 'Yêu cầu phản hồi',
                'time': updated or self.created_at,
                'desc': getattr(self, 'client_note', None) or 'Bên tuyển dụng cần bạn bổ sung thêm thông tin.',
                'type': 'needs_response'
            })
        elif eff == 'selected':
            events.append({
                'title': 'Được lựa chọn',
                'time': updated or self.created_at,
                'desc': 'Bên tuyển dụng đã chọn bạn cho công việc này. Vui lòng xác nhận nhận việc.',
                'type': 'selected'
            })
        elif eff == 'accepted':
            events.append({
                'title': 'Đã xác nhận nhận việc',
                'time': updated or self.created_at,
                'desc': 'Hợp đồng làm việc đã được tạo thành công.',
                'type': 'accepted'
            })
        elif eff == 'rejected':
            events.append({
                'title': 'Không được chọn',
                'time': updated or self.created_at,
                'desc': getattr(self, 'client_note', None) or 'Bên tuyển dụng đã lựa chọn ứng viên khác.',
                'type': 'rejected'
            })
        elif eff == 'withdrawn':
            events.append({
                'title': 'Đã rút đơn',
                'time': updated or self.created_at,
                'desc': getattr(self, 'withdrawn_reason', None) or 'Bạn đã chủ động rút đơn ứng tuyển.',
                'type': 'withdrawn'
            })
        elif eff == 'job_closed':
            events.append({
                'title': 'Tin tuyển dụng đã đóng',
                'time': updated or self.created_at,
                'desc': 'Công việc đã hết hạn hoặc không còn nhận đề xuất.',
                'type': 'closed'
            })
        return events


class SavedJob(db.Model):
    __tablename__ = 'saved_job'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'job_id', name='uq_saved_job_user_job'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('saved_jobs', lazy=True, cascade='all, delete-orphan'))
    job = db.relationship('Job', backref=db.backref('saved_by_users', lazy=True, cascade='all, delete-orphan'))


class Contract(db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            'job_id',
            name='uq_contract_job'
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    interpreter_service_id = db.Column(db.Integer, db.ForeignKey('interpreter_service.id'), nullable=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=True)
    hirer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    agreed_price = db.Column(db.Integer, nullable=False)
    scheduled_date = db.Column(db.String(100))
    scheduled_time_start = db.Column(db.String(10))
    scheduled_time_end = db.Column(db.String(10))
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='escrow_pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hirer = db.relationship('User', foreign_keys=[hirer_id], backref='contracts_as_hirer')
    translator = db.relationship('User', foreign_keys=[translator_id], backref='contracts_as_translator')
    messages = db.relationship('Message', backref='contract', lazy=True, cascade='all, delete-orphan')
    deliverables = db.relationship('Deliverable', backref='contract', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='contract', lazy=True, cascade='all, delete-orphan')
    service = db.relationship('Service', backref='contracts')
    interpreter_service = db.relationship('InterpreterService', backref='contracts')

    @property
    def event_sort_date(self):
        """Trả về ngày của ca làm (dùng để sắp xếp và so sánh thời gian)."""
        from datetime import date
        try:
            if self.schedule and self.schedule.scheduled_date:
                return self.schedule.scheduled_date
            if self.scheduled_date:
                from services.schedule import _parse_date
                d = _parse_date(self.scheduled_date)
                if d:
                    return d
        except Exception:
            pass
        return self.created_at.date() if self.created_at else date.min

    @property
    def shift_status_info(self):
        """
        Đối chiếu trạng thái ca làm theo 6 trạng thái chuẩn nghiệp vụ VietTranslate:
        - escrow_pending: Chờ xác nhận / Ký quỹ
        - upcoming: Đã xác nhận / Sắp tới
        - in_progress: Đang diễn ra
        - delivered: Chờ xác nhận hoàn thành
        - completed: Đã hoàn thành
        - cancelled: Đã hủy
        """
        from datetime import date
        today = date.today()

        if self.status == 'cancelled':
            return {
                'code': 'cancelled',
                'label': 'Đã hủy',
                'badge_class': 'bg-rose-50 text-rose-700 border-rose-200',
                'dot_class': 'bg-rose-500',
                'desc': 'Ca làm đã bị hủy theo thỏa thuận hoặc quá hạn xác nhận.',
                'can_report_issue': False,
                'can_deliver': False,
                'can_review': False,
                'can_view_meeting': False,
                'can_checkin': False,
            }

        if self.status == 'awaiting_translator':
            return {
                'code': 'awaiting_translator',
                'label': 'Chờ PDV xác nhận',
                'badge_class': 'bg-amber-50 text-amber-800 border-amber-200/80',
                'dot_class': 'bg-amber-500',
                'desc': 'Khách hàng đã gửi yêu cầu đặt lịch, đang chờ phiên dịch viên xác nhận.',
                'can_report_issue': False,
                'can_deliver': False,
                'can_review': False,
                'can_view_meeting': False,
                'can_checkin': False,
            }

        if self.status in ['completed', 'reviewed']:
            return {
                'code': 'completed',
                'label': 'Đã hoàn thành',
                'badge_class': 'bg-emerald-50 text-emerald-700 border-emerald-200',
                'dot_class': 'bg-emerald-500',
                'desc': 'Ca làm đã hoàn tất và được bên tuyển dụng nghiệm thu thành công.',
                'can_report_issue': False,
                'can_deliver': False,
                'can_review': True,
                'can_view_meeting': True,
                'can_checkin': False,
            }

        if self.status == 'delivered':
            return {
                'code': 'delivered',
                'label': 'Chờ xác nhận hoàn thành',
                'badge_class': 'bg-purple-50 text-purple-700 border-purple-200',
                'dot_class': 'bg-purple-500',
                'desc': 'Bạn đã báo kết thúc ca / nộp biên bản, đang chờ bên tuyển dụng nghiệm thu.',
                'can_report_issue': True,
                'can_deliver': False,
                'can_review': False,
                'can_view_meeting': True,
                'can_checkin': False,
            }

        if self.status == 'escrow_pending':
            return {
                'code': 'escrow_pending',
                'label': 'Chờ xác nhận / Ký quỹ',
                'badge_class': 'bg-amber-50 text-amber-700 border-amber-200',
                'dot_class': 'bg-amber-500',
                'desc': 'Đã chốt nhận việc, đang chờ bên tuyển dụng hoàn tất ký quỹ Escrow.',
                'can_report_issue': False,
                'can_deliver': False,
                'can_review': False,
                'can_view_meeting': False,
                'can_checkin': False,
            }

        # Trạng thái in_progress hoặc escrow_paid
        parsed_d = self.event_sort_date
        if parsed_d and parsed_d != date.min:
            if parsed_d > today:
                return {
                    'code': 'upcoming',
                    'label': 'Đã xác nhận / Sắp tới',
                    'badge_class': 'bg-sky-50 text-sky-700 border-sky-200',
                    'dot_class': 'bg-sky-500',
                    'desc': 'Ca làm đã được chốt và ký quỹ an toàn, đang trong giai đoạn chuẩn bị.',
                    'can_report_issue': True,
                    'can_deliver': False,
                    'can_review': False,
                    'can_view_meeting': True,
                    'can_checkin': False,
                }
            elif parsed_d == today:
                return {
                    'code': 'in_progress',
                    'label': 'Đang diễn ra',
                    'badge_class': 'bg-emerald-50 text-emerald-800 border-emerald-300 ring-1 ring-emerald-400/40',
                    'dot_class': 'bg-emerald-500 animate-pulse',
                    'desc': 'Ca làm diễn ra hôm nay. Vui lòng check-in và chuẩn bị thực hiện theo lịch.',
                    'can_report_issue': True,
                    'can_deliver': True,
                    'can_review': False,
                    'can_view_meeting': True,
                    'can_checkin': True,
                }
            else:
                return {
                    'code': 'in_progress',
                    'label': 'Đang diễn ra',
                    'badge_class': 'bg-amber-50 text-amber-800 border-amber-300',
                    'dot_class': 'bg-amber-500',
                    'desc': 'Đã qua ngày ca làm, vui lòng báo kết thúc hoặc nộp biên bản nghiệm thu.',
                    'can_report_issue': True,
                    'can_deliver': True,
                    'can_review': False,
                    'can_view_meeting': True,
                    'can_checkin': False,
                }

        return {
            'code': 'upcoming',
            'label': 'Đã xác nhận / Sắp tới',
            'badge_class': 'bg-sky-50 text-sky-700 border-sky-200',
            'dot_class': 'bg-sky-500',
            'desc': 'Hợp đồng ca làm việc đã kích hoạt thành công.',
            'can_report_issue': True,
            'can_deliver': True,
            'can_review': False,
            'can_view_meeting': True,
            'can_checkin': False,
        }

    @property
    def platform_fee(self):
        """Phí dịch vụ bảo đảm nền tảng Escrow (10%)."""
        return int(self.agreed_price * 0.10) if self.agreed_price else 0

    @property
    def translator_net_amount(self):
        """Số tiền thù lao thực nhận của phiên dịch viên sau khi trừ phí nền tảng (90%)."""
        return (self.agreed_price - self.platform_fee) if self.agreed_price else 0

    @property
    def acceptance_status_info(self):
        """
        Trạng thái nghiệm thu công việc:
        - accepted: Đã nghiệm thu (status in ['completed', 'reviewed'])
        - pending: Chờ nghiệm thu (status == 'delivered')
        - in_progress: Chưa tới bước nghiệm thu
        - cancelled: Đã hủy
        """
        if self.status in ['completed', 'reviewed']:
            return {
                'code': 'accepted',
                'label': 'Đã nghiệm thu',
                'badge_class': 'bg-emerald-50 text-emerald-700 border-emerald-200',
                'dot_class': 'bg-emerald-500',
                'desc': 'Bên thuê đã kiểm tra và phê duyệt kết quả công việc thành công.'
            }
        elif self.status == 'delivered':
            return {
                'code': 'pending',
                'label': 'Chờ nghiệm thu',
                'badge_class': 'bg-purple-50 text-purple-700 border-purple-200',
                'dot_class': 'bg-purple-500 animate-pulse',
                'desc': 'Bạn đã báo hoàn thành ca, đang chờ bên tuyển dụng xác nhận nghiệm thu.'
            }
        elif self.status == 'cancelled':
            return {
                'code': 'cancelled',
                'label': 'Đã hủy',
                'badge_class': 'bg-rose-50 text-rose-700 border-rose-200',
                'dot_class': 'bg-rose-500',
                'desc': 'Ca làm đã bị hủy theo thỏa thuận hoặc quá hạn.'
            }
        else:
            return {
                'code': 'in_progress',
                'label': 'Chưa nghiệm thu',
                'badge_class': 'bg-slate-100 text-slate-600 border-slate-200',
                'dot_class': 'bg-slate-400',
                'desc': 'Công việc đang trong quá trình thực hiện.'
            }

    @property
    def payment_status_info(self):
        """
        Trạng thái thanh toán theo nguồn dữ liệu Escrow thực tế:
        - paid: Đã giải ngân Escrow (status in ['completed', 'reviewed'])
        - escrow_held: Đang tạm giữ Escrow (status in ['in_progress', 'delivered'])
        - escrow_pending: Chờ khách ký quỹ (status == 'escrow_pending')
        - refunded: Đã hoàn trả / Hủy (status == 'cancelled')
        """
        if self.status in ['completed', 'reviewed']:
            return {
                'code': 'paid',
                'label': 'Đã giải ngân Escrow',
                'badge_class': 'bg-emerald-50 text-emerald-700 border-emerald-200',
                'is_paid': True,
                'desc': 'Tiền đã được giải ngân thành công sau khi nghiệm thu.'
            }
        elif self.status in ['in_progress', 'delivered']:
            return {
                'code': 'escrow_held',
                'label': 'Đang tạm giữ Escrow',
                'badge_class': 'bg-amber-50 text-amber-700 border-amber-200',
                'is_paid': False,
                'desc': 'Thù lao đang được bảo đảm tạm giữ trong tài khoản Escrow an toàn.'
            }
        elif self.status == 'escrow_pending':
            return {
                'code': 'escrow_pending',
                'label': 'Chưa ký quỹ',
                'badge_class': 'bg-slate-100 text-slate-600 border-slate-200',
                'is_paid': False,
                'desc': 'Bên thuê chưa hoàn tất bước ký quỹ thù lao.'
            }
        elif self.status == 'cancelled':
            return {
                'code': 'refunded',
                'label': 'Đã hoàn tiền / Hủy',
                'badge_class': 'bg-rose-50 text-rose-700 border-rose-200',
                'is_paid': False,
                'desc': 'Giao dịch đã được hủy hoặc hoàn trả.'
            }
        return {
            'code': 'unknown',
            'label': 'Đang xử lý',
            'badge_class': 'bg-slate-100 text-slate-600 border-slate-200',
            'is_paid': False,
            'desc': 'Trạng thái giao dịch đang được cập nhật.'
        }

    @property
    def client_review(self):
        """Nhận xét và đánh giá sao từ khách hàng tuyển dụng cho hợp đồng này."""
        for r in self.reviews:
            if r.reviewer_id == self.hirer_id:
                return r
        return None



class ContractEvent(db.Model):
    """Lịch sử xử lý của dự án (nghiệm thu, yêu cầu chỉnh sửa, bàn giao...)."""
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    event_type = db.Column(db.String(40), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', foreign_keys=[actor_id])
    contract = db.relationship('Contract', backref=db.backref('events', lazy=True, cascade='all, delete-orphan'))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship(
        'User',
        foreign_keys=[sender_id],
        backref='contract_messages_sent'
    )


class DirectMessage(db.Model):
    """Tin nhắn trực tiếp không gắn với contract - dùng khi chat hỏi thăm"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='direct_messages_received')


class Deliverable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __table_args__ = (
        db.UniqueConstraint('contract_id', 'reviewer_id', name='uq_review_contract_reviewer'),
    )
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviews_given')
    reviewee = db.relationship('User', foreign_keys=[reviewee_id], backref='reviews_received')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False, index=True)
    related_job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    related_contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True)
    related_review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=True)
    related_proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# Notification types constants
NOTIFICATION_TYPES = {
    'JOB_MATCH': 'JOB_MATCH',
    'JOB_INVITATION': 'JOB_INVITATION',
    'JOB_APPLICATION': 'JOB_APPLICATION',
    'APPLICATION_COUNT': 'APPLICATION_COUNT',
    'PROPOSAL_ACCEPTED': 'PROPOSAL_ACCEPTED',
    'PROPOSAL_REJECTED': 'PROPOSAL_REJECTED',
    'NEW_MESSAGE': 'NEW_MESSAGE',
    'CONTRACT_CREATED': 'CONTRACT_CREATED',
    'PAYMENT': 'PAYMENT',
    'CONTRACT_COMPLETED': 'CONTRACT_COMPLETED',
    'NEW_REVIEW': 'NEW_REVIEW',
    'VERIFICATION_SUBMITTED': 'VERIFICATION_SUBMITTED',
    'VERIFICATION_RESUBMITTED': 'VERIFICATION_RESUBMITTED',
    'VERIFICATION_NEEDS_REVISION': 'VERIFICATION_NEEDS_REVISION',
    'VERIFICATION_APPROVED': 'VERIFICATION_APPROVED',
    'VERIFICATION_REJECTED': 'VERIFICATION_REJECTED',
    'VERIFICATION_POLICY_UPDATE_REQUIRED': 'VERIFICATION_POLICY_UPDATE_REQUIRED'
}

VERIFICATION_NOTIFICATION_TYPES = (
    'VERIFICATION_SUBMITTED',
    'VERIFICATION_RESUBMITTED',
    'VERIFICATION_NEEDS_REVISION',
    'VERIFICATION_APPROVED',
    'VERIFICATION_REJECTED',
    'VERIFICATION_POLICY_UPDATE_REQUIRED'
)


SCHEDULE_STATUS = ('reserved', 'active', 'completed', 'cancelled')


class TranslatorSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)

    scheduled_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    buffer_before_minutes = db.Column(db.Integer, default=0)
    buffer_after_minutes = db.Column(db.Integer, default=30)

    # reserved | active | completed | cancelled
    status = db.Column(db.String(20), default='reserved', index=True)

    # shift | busy
    schedule_type = db.Column(db.String(20), default='shift', index=True)
    note = db.Column(db.String(255), nullable=True)
    is_all_day = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    translator = db.relationship('User', backref=db.backref('schedules', lazy=True))
    contract = db.relationship('Contract')


# ─── REPORT MODEL (TASK 11) ────────────────────────────────────────────────────

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Target can be: 'user', 'job', 'review', 'message', 'contract'
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    evidence_url = db.Column(db.String(500))
    
    # Status: 'new', 'investigating', 'resolved', 'rejected'
    status = db.Column(db.String(20), default='new', index=True)
    
    # Optional relation context
    related_job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    related_contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reports_submitted')
    related_job = db.relationship('Job', foreign_keys=[related_job_id])
    related_contract = db.relationship('Contract', foreign_keys=[related_contract_id])

# ─── DISPUTE MODEL (KHIẾU NẠI ĐƠN THUÊ) ────────────────────────────────────────

class Dispute(db.Model):
    """Khiếu nại của khách về một hợp đồng khi tiền còn được giữ (chưa giải ngân).

    pending_review  -> chờ admin xác nhận
    rejected        -> admin bác bỏ
    awaiting_response -> admin chuyển bước tiếp theo, PDV có 24h kháng đơn
    under_review    -> đã có thông tin 2 chiều, admin xem xét
    resolved        -> admin đã kết luận (xem resolution)
    """
    STATUSES = ('pending_review', 'rejected', 'awaiting_response', 'under_review', 'resolved')
    CATEGORIES = {'late': 'Trễ hạn', 'quality': 'Chất lượng', 'no_contact': 'Mất liên lạc'}
    RESOLUTIONS = {'keep_100': 'Giữ nguyên thanh toán 100%',
                   'refund_50': 'Giảm 50% tiền thanh toán',
                   'cancel_payment': 'Hủy thanh toán (hoàn tiền cho khách)'}

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False, index=True)
    hirer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending_review', nullable=False, index=True)

    admin_note = db.Column(db.Text)  # lý do bác bỏ / ghi chú khi chuyển bước
    forwarded_at = db.Column(db.DateTime)
    response_deadline = db.Column(db.DateTime)
    translator_response = db.Column(db.Text)
    translator_responded_at = db.Column(db.DateTime)

    resolution = db.Column(db.String(20))
    resolution_note = db.Column(db.Text)
    original_amount = db.Column(db.Integer)
    final_amount = db.Column(db.Integer)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship('Contract', backref=db.backref('disputes', lazy=True))
    hirer = db.relationship('User', foreign_keys=[hirer_id])
    translator = db.relationship('User', foreign_keys=[translator_id])
    evidence = db.relationship('DisputeEvidence', backref='dispute', lazy=True,
                               cascade='all, delete-orphan', order_by='DisputeEvidence.id')


class DisputeEvidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey('dispute.id'), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # 'hirer' | 'translator'
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── PAYMENT MODEL (TASK 13) ───────────────────────────────────────────────────

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Người thực hiện thanh toán
    amount = db.Column(db.Integer, nullable=False)
    
    # pending | completed | failed | refunded | escrow_pending
    status = db.Column(db.String(20), default='pending', index=True)
    payment_method = db.Column(db.String(50))
    transaction_ref = db.Column(db.String(100)) # Mã GD từ cổng thanh toán (nếu có)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship('Contract', backref=db.backref('payments', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id])

# ─── ADMIN NOTIFICATION MODEL (TASK 14) ────────────────────────────────────────

class AdminNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) # 'NEW_REPORT', 'NEW_JOB', 'NEW_TRANSLATOR', 'PAYMENT_ISSUE'
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False, index=True)
    
    # Optional context
    related_id = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# ─── ADMIN SECURITY MODELS ───────────────────────────────────────────────────

class LoginAttempt(db.Model):
    """
    Ghi lại mỗi lần thử đăng nhập Admin.
    Dùng để throttle brute-force: khóa tạm thời sau MAX_ATTEMPTS lần thất bại.
    """
    __tablename__ = 'login_attempt'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Số lần thất bại liên tiếp tối đa trước khi khóa
    MAX_ATTEMPTS = 5
    # Thời gian khóa (phút)
    LOCKOUT_MINUTES = 15

    @classmethod
    def count_recent_failures(cls, email, window_minutes=None):
        """Đếm số lần thất bại gần đây trong cửa sổ thời gian."""
        from datetime import timedelta
        if window_minutes is None:
            window_minutes = cls.LOCKOUT_MINUTES
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        return cls.query.filter(
            cls.email == email.lower(),
            cls.success == False,
            cls.created_at >= cutoff
        ).count()

    @classmethod
    def is_locked_out(cls, email):
        """Kiểm tra email có đang bị khóa tạm thời không."""
        return cls.count_recent_failures(email) >= cls.MAX_ATTEMPTS

    @classmethod
    def record(cls, email, ip_address=None, success=False):
        """Tạo bản ghi login attempt mới."""
        attempt = cls(
            email=email.lower().strip() if email else '',
            ip_address=ip_address,
            success=success,
        )
        db.session.add(attempt)
        # Không commit ở đây — caller chịu trách nhiệm commit
        return attempt


# Hằng số Audit Log actions
ADMIN_AUDIT_ACTIONS = {
    'LOGIN_SUCCESS': 'LOGIN_SUCCESS',
    'LOGIN_FAILED': 'LOGIN_FAILED',
    'LOGOUT': 'LOGOUT',
    'ACCOUNT_LOCKED': 'ACCOUNT_LOCKED',
    'VERIFY_TRANSLATOR': 'VERIFY_TRANSLATOR',
    'REJECT_TRANSLATOR': 'REJECT_TRANSLATOR',
    'REQUEST_POLICY_UPDATE': 'REQUEST_POLICY_UPDATE',
    'VERIFY_HIRER': 'VERIFY_HIRER',
    'REJECT_HIRER': 'REJECT_HIRER',
    'REQUEST_HIRER_REVISION': 'REQUEST_HIRER_REVISION',
    'REVOKE_HIRER': 'REVOKE_HIRER',
    'APPROVE_JOB': 'APPROVE_JOB',
    'REJECT_JOB': 'REJECT_JOB',
    'REQUEST_JOB_REVISION': 'REQUEST_JOB_REVISION',
    'FLAG_JOB': 'FLAG_JOB',
    'UNFLAG_JOB': 'UNFLAG_JOB',
    'ARCHIVE_JOB': 'ARCHIVE_JOB',
    'DELETE_JOB': 'DELETE_JOB',
    'UPDATE_JOB_TITLE': 'UPDATE_JOB_TITLE',
    'LOCK_USER': 'LOCK_USER',
    'UNLOCK_USER': 'UNLOCK_USER',
    'BAN_USER': 'BAN_USER',
    'HIDE_REVIEW': 'HIDE_REVIEW',
    'RESTORE_REVIEW': 'RESTORE_REVIEW',
    'RESOLVE_REPORT': 'RESOLVE_REPORT',
    'REJECT_REPORT': 'REJECT_REPORT',
    'CANCEL_BOOKING': 'CANCEL_BOOKING',
    'PAYMENT_ACTION': 'PAYMENT_ACTION',
    'CHANGE_PERMISSION': 'CHANGE_PERMISSION',
    'CREATE_ADMIN': 'CREATE_ADMIN',
    'RESET_MFA': 'RESET_MFA',
    'ADMIN_REAUTH': 'ADMIN_REAUTH',
    'ADMIN_ACCESS_BLOCKED': 'ADMIN_ACCESS_BLOCKED',
    'ADMIN_ACCESS_RESTORED': 'ADMIN_ACCESS_RESTORED',
    'ADMIN_PRIVILEGES_REVOKED': 'ADMIN_PRIVILEGES_REVOKED',
    'ADMIN_PASSWORD_RESET': 'ADMIN_PASSWORD_RESET',
    'PROMOTE_TO_ADMIN': 'PROMOTE_TO_ADMIN',
}


class AdminAuditLog(db.Model):
    """
    Ghi lại mọi hành động của Admin.
    - Không bao giờ xóa bảng này.
    - Không lưu password hoặc session token.
    - Admin không thể tự xóa audit log của mình.
    """
    __tablename__ = 'admin_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    # admin_id có thể None nếu login failed (chưa xác định được admin)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True)   # 'user', 'job', 'translator', ...
    target_id = db.Column(db.Integer, nullable=True)         # ID của đối tượng bị tác động
    description = db.Column(db.Text, nullable=True)          # Mô tả ngắn gọn
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    # metadata JSON: lý do từ chối, note, thông tin thêm
    extra_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    admin = db.relationship('User', foreign_keys=[admin_id], backref=db.backref('audit_logs', lazy=True))

    def get_extra_data(self):
        """Parse extra_data JSON, trả về dict."""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except (ValueError, TypeError):
            return {}

    @classmethod
    def log(cls, action, admin_id=None, target_type=None, target_id=None,
            description=None, ip_address=None, user_agent=None, extra_data=None):
        """
        Tạo một bản ghi audit log mới.
        Không commit — caller phải tự commit sau khi hoàn thành tất cả thao tác.
        """
        entry = cls(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=json.dumps(extra_data) if extra_data else None,
        )
        db.session.add(entry)
        return entry


# ─── TRANSLATOR VERIFICATION MODEL ────────────────────────────────────────────

class TranslatorVerification(db.Model):
    """
    Hồ sơ xác minh năng lực và danh tính của phiên dịch viên.
    Lưu trữ tài liệu CV, bằng cấp/chứng chỉ, kinh nghiệm và trạng thái xét duyệt của Admin.
    """
    __tablename__ = 'translator_verification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Tài liệu đính kèm
    cv_filename = db.Column(db.String(255), nullable=True)
    cv_url = db.Column(db.String(500), nullable=True)
    certificate_filename = db.Column(db.String(255), nullable=True)
    certificate_url = db.Column(db.String(500), nullable=True)
    id_card_filename = db.Column(db.String(255), nullable=True)
    id_card_url = db.Column(db.String(500), nullable=True)

    # Thông tin chuyên môn
    certificate_type = db.Column(db.String(100), nullable=True)  # IELTS, JLPT, HSK, TOPIK, Bằng ĐH, ...
    certificate_name = db.Column(db.String(255), nullable=True)  # Điểm / Chi tiết (VD: IELTS 8.0, JLPT N1)
    primary_language = db.Column(db.String(100), nullable=True)  # Ngôn ngữ thế mạnh
    experience_years = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)                    # Lời nhắn / mô tả kinh nghiệm gửi Admin

    # Tiến trình biểu mẫu nhiều bước & Dữ liệu nháp
    current_step = db.Column(db.Integer, default=1)
    draft_data = db.Column(db.Text, nullable=True)

    # Bước 1: Thông tin cá nhân
    full_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # Bước 2: Ngôn ngữ & Chiều phiên dịch
    source_language = db.Column(db.String(100), nullable=True)
    target_language = db.Column(db.String(100), nullable=True)
    interpreting_direction = db.Column(db.String(50), nullable=True)
    language_proficiency = db.Column(db.String(50), nullable=True)

    # Bước 3: Lĩnh vực chuyên môn & Hình thức phiên dịch
    specializations = db.Column(db.Text, nullable=True)
    interpreting_types = db.Column(db.Text, nullable=True)

    # Bước 4: Học vấn & Chứng chỉ
    education_level = db.Column(db.String(100), nullable=True)
    university = db.Column(db.String(255), nullable=True)
    major = db.Column(db.String(255), nullable=True)
    cert_year = db.Column(db.Integer, nullable=True)

    # Bước 5: Kinh nghiệm nghề nghiệp
    current_position = db.Column(db.String(255), nullable=True)
    notable_clients = db.Column(db.Text, nullable=True)
    featured_projects = db.Column(db.Text, nullable=True)

    # Trạng thái xét duyệt: 'draft', 'pending', 'approved', 'rejected'
    status = db.Column(db.String(20), default='draft', index=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Xét duyệt bởi Admin
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Tiến trình nộp hồ sơ, phiên bản & Snapshot bất biến
    submitted_at = db.Column(db.DateTime, nullable=True, index=True)
    submission_version = db.Column(db.Integer, default=0)
    submitted_snapshot = db.Column(db.Text, nullable=True)
    checklist_data = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('verifications', lazy=True, cascade='all, delete-orphan', order_by='desc(TranslatorVerification.created_at)'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref=db.backref('reviewed_verifications', lazy=True))

    def get_submitted_snapshot(self):
        """Trả về dữ liệu snapshot của lần nộp hồ sơ gần nhất."""
        if self.submitted_snapshot:
            try:
                return json.loads(self.submitted_snapshot)
            except Exception:
                return {}
        return {}

    def get_draft_dict(self):
        """Trả về dictionary chứa dữ liệu nháp của tất cả các bước."""
        data = {}
        if self.draft_data:
            try:
                data = json.loads(self.draft_data)
            except Exception:
                data = {}
        
        field_names = [
            'full_name', 'phone', 'gender', 'dob', 'location', 'bio',
            'source_language', 'target_language', 'interpreting_direction', 'language_proficiency',
            'specializations', 'interpreting_types',
            'education_level', 'university', 'major', 'certificate_type', 'certificate_name', 'cert_year',
            'experience_years', 'current_position', 'notable_clients', 'featured_projects', 'notes'
        ]
        for f in field_names:
            if f not in data or data[f] is None or data[f] == '':
                val = getattr(self, f, None)
                if val is not None:
                    data[f] = val

        if 'current_step' not in data:
            data['current_step'] = self.current_step or 1

        return data


# ─── VERIFICATION DOCUMENT MODEL (PRIVATE STORAGE) ────────────────────────────

class VerificationDocument(db.Model):
    """
    Tài liệu minh chứng cho hồ sơ xác minh phiên dịch viên.
    Lưu trữ riêng tư (Private Storage), hỗ trợ siêu dữ liệu (metadata),
    kiểm tra quyền truy cập nghiêm ngặt và theo dõi trạng thái thẩm định.
    """
    __tablename__ = 'verification_document'

    id = db.Column(db.Integer, primary_key=True)
    verification_id = db.Column(db.Integer, db.ForeignKey('translator_verification.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Loại tài liệu chính sách: 'cv', 'certificate', 'id_card', 'diploma', 'recommendation'
    document_type = db.Column(db.String(50), nullable=False, index=True)

    # Tên tệp gốc & tên tệp an toàn trong private storage
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # Nhà cung cấp lưu trữ ('local_private' hoặc 'supabase_private')
    storage_provider = db.Column(db.String(50), default='local_private')
    storage_path = db.Column(db.String(500), nullable=False)

    # Metadata tệp
    file_size = db.Column(db.Integer, nullable=False, default=0)  # bytes
    mime_type = db.Column(db.String(100), nullable=False)
    file_extension = db.Column(db.String(20), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True)

    # Trạng thái thẩm định: 'uploaded', 'approved', 'rejected', 'replaced'
    status = db.Column(db.String(30), default='uploaded', index=True)
    review_notes = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Đánh dấu tệp hiện thời
    is_active = db.Column(db.Boolean, default=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    verification = db.relationship('TranslatorVerification', backref=db.backref('documents', lazy=True, cascade='all, delete-orphan', order_by='desc(VerificationDocument.created_at)'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('uploaded_verification_documents', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref=db.backref('reviewed_verification_documents', lazy=True))

    def to_dict(self):
        """Chuyển đổi thành dictionary cho JSON response."""
        return {
            'id': self.id,
            'verification_id': self.verification_id,
            'document_type': self.document_type,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'file_extension': self.file_extension,
            'status': self.status,
            'review_notes': self.review_notes,
            'reviewed_at': self.reviewed_at.strftime('%d/%m/%Y %H:%M') if self.reviewed_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'can_preview': self.file_extension in ('pdf', 'jpg', 'jpeg', 'png', 'webp')
        }


# ─── VERIFICATION SUBMISSION VERSION MODEL ────────────────────────────────────

class VerificationSubmissionVersion(db.Model):
    """
    Lưu giữ các phiên bản hồ sơ đã nộp của phiên dịch viên phục vụ đối soát và audit.
    Bảo toàn snapshot bất biến tại từng thời điểm nộp hồ sơ.
    """
    __tablename__ = 'verification_submission_version'

    id = db.Column(db.Integer, primary_key=True)
    verification_id = db.Column(db.Integer, db.ForeignKey('translator_verification.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='pending')
    snapshot_data = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    verification = db.relationship('TranslatorVerification', backref=db.backref('submission_versions', lazy=True, cascade='all, delete-orphan', order_by='desc(VerificationSubmissionVersion.submitted_at)'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('verification_submissions', lazy=True))

    def get_snapshot(self):
        """Trả về dữ liệu snapshot dạng dictionary."""
        try:
            return json.loads(self.snapshot_data)
        except Exception:
            return {}

class PasswordResetToken(db.Model):
    """
    Token dùng để xác minh yêu cầu cấp lại mật khẩu.
    Chỉ lưu mã băm của token.
    """
    __tablename__ = 'password_reset_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('reset_tokens', lazy=True, cascade='all, delete-orphan'))

    def is_valid(self):
        return not self.is_used and self.expires_at > datetime.utcnow()

class EmailVerificationToken(db.Model):
    """
    Token dùng để xác minh email.
    Chỉ lưu mã băm của token.
    """
    __tablename__ = 'email_verification_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('email_verification_tokens', lazy=True, cascade='all, delete-orphan'))

    def is_valid(self):
        return not self.is_used and self.expires_at > datetime.utcnow()


# ─── PHÂN HỆ TÀI KHOẢN PHIÊN DỊCH VIÊN (MỤC V) ───────────────────────────────

class InterpreterService(db.Model):
    """
    Năng lực & Bảng giá của phiên dịch viên (Mục 5.2).
    Lưu trữ cấu hình cặp ngôn ngữ, hình thức phiên dịch, chuyên môn và mức thù lao.
    """
    __tablename__ = 'interpreter_service'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Cặp ngôn ngữ & Hình thức phiên dịch
    source_lang = db.Column(db.String(100), nullable=False)
    target_lang = db.Column(db.String(100), nullable=False)
    interpreting_type = db.Column(db.String(100), nullable=False)  # cabin, nối tiếp, tháp tùng, online
    specialization = db.Column(db.String(255), nullable=True)     # kinh doanh, kỹ thuật, y tế, pháp lý

    # Bảng giá
    hourly_rate = db.Column(db.Float, nullable=True)               # Giá theo giờ (VND)
    session_rate = db.Column(db.Float, nullable=True)              # Giá theo buổi/ca (VND)
    currency = db.Column(db.String(10), default='VND')

    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def formatted_hourly_rate(self):
        """Định dạng mức thù lao theo giờ chuẩn VNĐ (Ví dụ: 1.500.000 VNĐ)."""
        if self.hourly_rate is not None and self.hourly_rate > 0:
            return f"{int(round(self.hourly_rate)):,}".replace(',', '.') + ' VNĐ'
        return None

    @property
    def formatted_session_rate(self):
        """Định dạng mức thù lao theo ca/buổi chuẩn VNĐ (Ví dụ: 5.000.000 VNĐ)."""
        if self.session_rate is not None and self.session_rate > 0:
            return f"{int(round(self.session_rate)):,}".replace(',', '.') + ' VNĐ'
        return None

    @property
    def display_rate_summary(self):
        """Tóm tắt mức thù lao theo giờ và theo ca."""
        parts = []
        if self.formatted_hourly_rate:
            parts.append(f"{self.formatted_hourly_rate}/giờ")
        if self.formatted_session_rate:
            parts.append(f"{self.formatted_session_rate}/buổi")
        return " · ".join(parts) if parts else "Thỏa thuận"

    @property
    def display_interpreting_type(self):
        """Tên hiển thị chuẩn của hình thức phiên dịch."""
        type_map = {
            'cabin': 'Dịch Cabin (Đồng thời)',
            'nối tiếp': 'Dịch nối tiếp (Consecutive)',
            'noi_tiep': 'Dịch nối tiếp (Consecutive)',
            'tháp tùng': 'Dịch tháp tùng (Escort)',
            'thap_tung': 'Dịch tháp tùng (Escort)',
            'online': 'Dịch từ xa (Online / Remote)',
            'từ xa': 'Dịch từ xa (Online / Remote)',
        }
        raw = (self.interpreting_type or '').strip().lower()
        for k, v in type_map.items():
            if k in raw:
                return v
        return self.interpreting_type or 'Chung'

    @property
    def interpreting_type_badge_class(self):
        """Màu badge phù hợp với hình thức phiên dịch."""
        raw = (self.interpreting_type or '').strip().lower()
        if 'cabin' in raw:
            return 'bg-purple-50 text-purple-700 border-purple-200'
        elif 'nối tiếp' in raw or 'noi_tiep' in raw:
            return 'bg-blue-50 text-blue-700 border-blue-200'
        elif 'tháp tùng' in raw or 'thap_tung' in raw:
            return 'bg-amber-50 text-amber-700 border-amber-200'
        elif 'online' in raw or 'từ xa' in raw:
            return 'bg-emerald-50 text-emerald-700 border-emerald-200'
        return 'bg-slate-50 text-slate-700 border-slate-200'

    def is_kyc_verified(self):
        """
        Kiểm tra cặp ngôn ngữ và chuyên ngành của dịch vụ này
        đã được Ban quản trị DUYỆT trong hệ thống KYC hay chưa.
        NẾU ngôn ngữ/chuyên ngành ĐÃ ĐƯỢC DUYỆT ở hệ thống KYC: True -> 'Đã xác minh năng lực ✓'
        NẾU là dịch vụ tự khai thêm: False -> 'Chưa xác minh'
        """
        user = self.user
        if not user:
            return False

        # 1. Tìm hồ sơ xác minh đã duyệt (status == 'approved')
        approved_verif = None
        if hasattr(user, 'verifications') and user.verifications:
            for v in user.verifications:
                if getattr(v, 'status', None) == 'approved':
                    approved_verif = v
                    break

        user_is_verified = bool(
            approved_verif or
            getattr(user, 'is_verified', False) or
            (user.profile and getattr(user.profile, 'is_verified', False))
        )
        if not user_is_verified:
            return False

        def clean_lang(l):
            if not l:
                return ''
            s = l.strip().lower()
            lang_map = {
                'tiếng việt': 'vi', 'việt': 'vi', 'vietnamese': 'vi', 'vn': 'vi', 'vi': 'vi',
                'tiếng anh': 'en', 'anh': 'en', 'english': 'en', 'en': 'en',
                'tiếng nhật': 'ja', 'tiếng nhật bản': 'ja', 'nhật': 'ja', 'nhật bản': 'ja', 'japanese': 'ja', 'jp': 'ja', 'ja': 'ja',
                'tiếng hàn': 'ko', 'tiếng hàn quốc': 'ko', 'hàn': 'ko', 'hàn quốc': 'ko', 'korean': 'ko', 'kr': 'ko', 'ko': 'ko',
                'tiếng trung': 'zh', 'tiếng trung quốc': 'zh', 'trung': 'zh', 'trung quốc': 'zh', 'chinese': 'zh', 'cn': 'zh', 'zh': 'zh',
                'tiếng pháp': 'fr', 'pháp': 'fr', 'french': 'fr', 'fr': 'fr',
                'tiếng đức': 'de', 'đức': 'de', 'german': 'de', 'de': 'de',
                'tiếng nga': 'ru', 'nga': 'ru', 'russian': 'ru', 'ru': 'ru',
                'tiếng tây ban nha': 'es', 'tây ban nha': 'es', 'spanish': 'es', 'es': 'es',
                'tiếng bồ đào nha': 'pt', 'bồ đào nha': 'pt', 'portuguese': 'pt', 'pt': 'pt',
                'tiếng thái': 'th', 'thái': 'th', 'thái lan': 'th', 'thai': 'th', 'th': 'th',
            }
            return lang_map.get(s, s)

        approved_langs = set()
        if approved_verif:
            if approved_verif.source_language:
                approved_langs.add(clean_lang(approved_verif.source_language))
            if approved_verif.target_language:
                approved_langs.add(clean_lang(approved_verif.target_language))
            if approved_verif.primary_language:
                approved_langs.add(clean_lang(approved_verif.primary_language))
        if user.profile:
            if user.profile.source_language:
                approved_langs.add(clean_lang(user.profile.source_language))
            if user.profile.target_language:
                approved_langs.add(clean_lang(user.profile.target_language))
            if user.profile.languages:
                for l in user.profile.languages.split(','):
                    approved_langs.add(clean_lang(l))

        src_clean = clean_lang(self.source_lang)
        tgt_clean = clean_lang(self.target_lang)

        lang_matched = False
        if approved_langs:
            if src_clean in approved_langs and tgt_clean in approved_langs:
                lang_matched = True
            elif (src_clean in ('vi', '') and tgt_clean in approved_langs) or (tgt_clean in ('vi', '') and src_clean in approved_langs):
                lang_matched = True
        else:
            lang_matched = True

        # Thu thập lĩnh vực chuyên môn đã được duyệt
        approved_specs = set()
        def extract_specs(raw):
            if not raw:
                return
            if isinstance(raw, str):
                import json
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        for x in parsed:
                            approved_specs.add(str(x).strip().lower())
                        return
                except Exception:
                    pass
                for part in raw.replace(';', ',').split(','):
                    if part.strip():
                        approved_specs.add(part.strip().lower())
            elif isinstance(raw, list):
                for x in raw:
                    approved_specs.add(str(x).strip().lower())

        if approved_verif and approved_verif.specializations:
            extract_specs(approved_verif.specializations)
        if user.profile and user.profile.specializations:
            extract_specs(user.profile.specializations)

        svc_spec = (self.specialization or '').strip().lower()
        spec_matched = False
        if not svc_spec or not approved_specs:
            spec_matched = True
        else:
            for app_sp in approved_specs:
                if app_sp in svc_spec or svc_spec in app_sp:
                    spec_matched = True
                    break
                words_app = set(app_sp.replace('&', ' ').replace('-', ' ').split())
                words_svc = set(svc_spec.replace('&', ' ').replace('-', ' ').split())
                if words_app & words_svc:
                    spec_matched = True
                    break

        return bool(lang_matched and spec_matched)

    def to_dict(self):
        """Chuyển đổi thành Dictionary phục vụ JSON API."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'interpreting_type': self.interpreting_type,
            'display_interpreting_type': self.display_interpreting_type,
            'interpreting_type_badge_class': self.interpreting_type_badge_class,
            'specialization': self.specialization or '',
            'hourly_rate': self.hourly_rate,
            'formatted_hourly_rate': self.formatted_hourly_rate,
            'session_rate': self.session_rate,
            'formatted_session_rate': self.formatted_session_rate,
            'display_rate_summary': self.display_rate_summary,
            'currency': self.currency or 'VND',
            'is_active': self.is_active,
            'is_kyc_verified': self.is_kyc_verified(),
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None
        }


class InterpreterPreference(db.Model):
    """
    Tiêu chí nhận việc của phiên dịch viên (Mục 5.4).
    Lưu trữ các ràng buộc bộ lọc: ngôn ngữ, chuyên môn, phương thức làm việc và khoảng giá mong muốn.
    """
    __tablename__ = 'interpreter_preference'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)

    languages = db.Column(db.Text, nullable=True)            # JSON string hoặc chuỗi phân tách các ngôn ngữ
    specializations = db.Column(db.Text, nullable=True)      # JSON string hoặc chuỗi phân tách các chuyên môn
    work_mode = db.Column(db.String(50), default='both')     # online, offline, both
    min_rate = db.Column(db.Float, nullable=True)            # Mức giá tối thiểu mong muốn
    max_rate = db.Column(db.Float, nullable=True)            # Mức giá tối đa mong muốn
    allow_outside_rate = db.Column(db.Boolean, default=False)# Chấp nhận việc ngoài khoảng giá
    available_hours = db.Column(db.Text, nullable=True)      # Khung giờ làm việc sẵn sàng (JSON/Text)
    locations = db.Column(db.Text, nullable=True)            # Khu vực nhận việc trực tiếp (JSON/Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_languages_list(self):
        if not self.languages:
            return []
        try:
            val = json.loads(self.languages)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [l.strip() for l in self.languages.split(',') if l.strip()]

    def set_languages_list(self, items):
        if isinstance(items, list):
            self.languages = json.dumps(items, ensure_ascii=False)
        else:
            self.languages = str(items or '')

    def get_specializations_list(self):
        if not self.specializations:
            return []
        try:
            val = json.loads(self.specializations)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [s.strip() for s in self.specializations.split(',') if s.strip()]

    def set_specializations_list(self, items):
        if isinstance(items, list):
            self.specializations = json.dumps(items, ensure_ascii=False)
        else:
            self.specializations = str(items or '')

    def get_locations_list(self):
        if not self.locations:
            return []
        try:
            val = json.loads(self.locations)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [loc.strip() for loc in self.locations.split(',') if loc.strip()]

    def set_locations_list(self, items):
        if isinstance(items, list):
            self.locations = json.dumps(items, ensure_ascii=False)
        else:
            self.locations = str(items or '')

    def get_available_hours_list(self):
        if not self.available_hours:
            return []
        try:
            val = json.loads(self.available_hours)
            if isinstance(val, list):
                return val
        except Exception:
            pass
        return [h.strip() for h in self.available_hours.split(',') if h.strip()]

    def set_available_hours_list(self, items):
        if isinstance(items, list):
            self.available_hours = json.dumps(items, ensure_ascii=False)
        else:
            self.available_hours = str(items or '')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'languages': self.get_languages_list(),
            'specializations': self.get_specializations_list(),
            'work_mode': self.work_mode or 'both',
            'min_rate': self.min_rate,
            'max_rate': self.max_rate,
            'allow_outside_rate': bool(self.allow_outside_rate),
            'available_hours': self.get_available_hours_list(),
            'locations': self.get_locations_list(),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class NotificationSetting(db.Model):
    """
    Cài đặt nhận thông báo của người dùng (Mục 5.6.1).
    Phục vụ cấu hình tùy chọn thông báo (Notification Preferences) với 4 nhóm:
    1. Nhóm Công việc: Job mới phù hợp, Trạng thái đơn ứng tuyển, Khách đã xem hồ sơ
    2. Nhóm Lịch trình: Nhắc lịch ca dịch sắp tới (kèm các mốc 60p, 30p, 15p)
    3. Nhóm Thu nhập: Cập nhật thù lao và giải ngân
    4. Nhóm Bảo mật & Hệ thống: Cảnh báo đăng nhập lạ và bảo mật (Luôn bật và khóa)
    """
    __tablename__ = 'notification_setting'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)

    # 1. Nhóm Công việc
    notify_job_match = db.Column(db.Boolean, default=True)           # Công việc mới phù hợp tiêu chí
    notify_application_update = db.Column(db.Boolean, default=True)  # Trạng thái đơn ứng tuyển / hợp đồng
    notify_profile_view = db.Column(db.Boolean, default=True)        # Khách đã xem hồ sơ

    # 2. Nhóm Lịch trình
    notify_schedule_reminder = db.Column(db.Boolean, default=True)   # Nhắc lịch ca dịch sắp tới
    reminder_time_60m = db.Column(db.Boolean, default=True)          # Mốc nhắc: Trước 60 phút
    reminder_time_30m = db.Column(db.Boolean, default=True)          # Mốc nhắc: Trước 30 phút
    reminder_time_15m = db.Column(db.Boolean, default=False)         # Mốc nhắc: Trước 15 phút

    # 3. Nhóm Thu nhập
    notify_income_update = db.Column(db.Boolean, default=True)       # Cập nhật thù lao và giải ngân

    # 4. Nhóm Bảo mật & Hệ thống (Luôn BẬT và KHÓA)
    notify_security_alert = db.Column(db.Boolean, default=True)      # Cảnh báo đăng nhập lạ và bảo mật

    # Tiếp thị & Nền tảng
    notify_marketing = db.Column(db.Boolean, default=False)          # Tin khuyến mại, sự kiện nền tảng

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Alias properties cho tính tương thích và tiện dụng
    @property
    def reminder_60m(self):
        return bool(self.reminder_time_60m) if self.reminder_time_60m is not None else True

    @reminder_60m.setter
    def reminder_60m(self, val):
        self.reminder_time_60m = bool(val)

    @property
    def reminder_30m(self):
        return bool(self.reminder_time_30m) if self.reminder_time_30m is not None else True

    @reminder_30m.setter
    def reminder_30m(self, val):
        self.reminder_time_30m = bool(val)

    @property
    def reminder_15m(self):
        return bool(self.reminder_time_15m) if self.reminder_time_15m is not None else False

    @reminder_15m.setter
    def reminder_15m(self, val):
        self.reminder_time_15m = bool(val)

    @property
    def notify_payout(self):
        return bool(self.notify_income_update) if self.notify_income_update is not None else True

    @notify_payout.setter
    def notify_payout(self, val):
        self.notify_income_update = bool(val)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notify_job_match': True if self.notify_job_match is None else bool(self.notify_job_match),
            'notify_application_update': True if self.notify_application_update is None else bool(self.notify_application_update),
            'notify_profile_view': True if self.notify_profile_view is None else bool(self.notify_profile_view),
            'notify_schedule_reminder': True if self.notify_schedule_reminder is None else bool(self.notify_schedule_reminder),
            'reminder_time_60m': True if self.reminder_time_60m is None else bool(self.reminder_time_60m),
            'reminder_time_30m': True if self.reminder_time_30m is None else bool(self.reminder_time_30m),
            'reminder_time_15m': False if self.reminder_time_15m is None else bool(self.reminder_time_15m),
            'reminder_60m': True if self.reminder_time_60m is None else bool(self.reminder_time_60m),
            'reminder_30m': True if self.reminder_time_30m is None else bool(self.reminder_time_30m),
            'reminder_15m': False if self.reminder_time_15m is None else bool(self.reminder_time_15m),
            'notify_income_update': True if self.notify_income_update is None else bool(self.notify_income_update),
            'notify_security_alert': True,  # Luôn BẬT và KHÓA
            'notify_marketing': bool(self.notify_marketing),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class UserSession(db.Model):
    """
    Quản lý phiên đăng nhập và bảo mật thiết bị (Mục 5.6.2).
    """
    __tablename__ = 'user_session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    session_id = db.Column(db.String(255), nullable=True, index=True) # Token phiên
    device_name = db.Column(db.String(255), nullable=True)            # Trình duyệt / Thiết bị
    ip_address = db.Column(db.String(50), nullable=True)              # Địa chỉ IP
    last_active = db.Column(db.DateTime, default=datetime.utcnow)    # Lần hoạt động cuối
    is_current = db.Column(db.Boolean, default=False)                 # Đánh dấu phiên hiện tại
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def format_last_active(self):
        """Định dạng thời gian hoạt động gần nhất thân thiện tiếng Việt."""
        if not self.last_active:
            return "Chưa xác định"
        now = datetime.utcnow()
        diff = now - self.last_active
        seconds = int(diff.total_seconds())
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return "Vừa xong"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} phút trước"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} giờ trước"
        days = hours // 24
        if days < 7:
            return f"{days} ngày trước"
        return self.last_active.strftime("%H:%M %d/%m/%Y")

    def get_device_type(self):
        """Xác định loại thiết bị: desktop, mobile, tablet."""
        name = (self.device_name or "").lower()
        if any(x in name for x in ['iphone', 'android', 'mobile', 'phone']):
            return 'mobile'
        if any(x in name for x in ['ipad', 'tablet']):
            return 'tablet'
        return 'desktop'

    def to_dict(self, current_session_token=None):
        """Chuyển đổi UserSession thành dict đầy đủ thuộc tính."""
        is_cur = bool(current_session_token and self.session_id == current_session_token) or (not current_session_token and bool(self.is_current))
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'device_name': self.device_name or 'Trình duyệt Web',
            'ip_address': self.ip_address or '127.0.0.1',
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'last_active_formatted': self.format_last_active(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_current': is_cur,
            'device_type': self.get_device_type()
        }


class SupportTicket(db.Model):
    """
    Yêu cầu hỗ trợ kỹ thuật và khiếu nại (Mục 5.7.3).
    """
    __tablename__ = 'support_ticket'

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    category = db.Column(db.String(100), nullable=False)     # Phân loại: compensation, cancellation, dispute, identity, technical, other
    title = db.Column(db.String(255), nullable=False)        # Tiêu đề
    description = db.Column(db.Text, nullable=False)         # Nội dung mô tả chi tiết
    attachment_url = db.Column(db.String(500), nullable=True)# URL tệp đính kèm (ảnh lỗi, tài liệu...)
    status = db.Column(db.String(30), default='open', index=True) # open, in_progress, resolved, closed
    admin_reply = db.Column(db.Text, nullable=True)          # Phản hồi từ Ban Quản trị / Hỗ trợ viên
    admin_reply_at = db.Column(db.DateTime, nullable=True)   # Thời gian phản hồi

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status_label(self):
        labels = {
            'open': 'Đã tiếp nhận',
            'received': 'Đã tiếp nhận',
            'in_progress': 'Đang xử lý',
            'resolved': 'Đã giải quyết',
            'closed': 'Đã đóng'
        }
        return labels.get(self.status, 'Đã tiếp nhận')

    @property
    def status_badge_class(self):
        badges = {
            'open': 'bg-blue-50 text-blue-700 border-blue-200/80',
            'received': 'bg-blue-50 text-blue-700 border-blue-200/80',
            'in_progress': 'bg-amber-50 text-amber-700 border-amber-200/80',
            'resolved': 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
            'closed': 'bg-slate-100 text-slate-700 border-slate-200/80'
        }
        return badges.get(self.status, 'bg-blue-50 text-blue-700 border-blue-200/80')

    @property
    def category_label(self):
        labels = {
            'compensation': 'Nhận thù lao & Escrow',
            'cancellation': 'Quy tắc hủy ca & Bồi thường',
            'dispute': 'Giải quyết tranh chấp & Khiếu nại',
            'identity': 'Đổi thông tin định danh & KYC',
            'technical': 'Sự cố kỹ thuật & Đăng nhập',
            'account_security': 'Bảo mật tài khoản',
            'other': 'Yêu cầu khác'
        }
        return labels.get(self.category, self.category or 'Hỗ trợ chung')

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_code': self.ticket_code,
            'user_id': self.user_id,
            'category': self.category,
            'category_label': self.category_label,
            'title': self.title,
            'description': self.description,
            'attachment_url': self.attachment_url,
            'status': self.status,
            'status_label': self.status_label,
            'status_badge_class': self.status_badge_class,
            'admin_reply': self.admin_reply,
            'admin_reply_at': self.admin_reply_at.strftime('%d/%m/%Y %H:%M') if self.admin_reply_at else None,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None,
        }


class PayoutMethod(db.Model):
    __tablename__ = 'payout_methods'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    bank_code = db.Column(db.String(20), nullable=False)
    bank_short_name = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    masked_account_number = db.Column(db.String(50), nullable=False)
    account_holder_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(120), nullable=True, default='')
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)
    status_label = db.Column(db.String(100), default='Khai báo hợp lệ · Đang hoạt động', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('payout_methods', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'bank_code': self.bank_code,
            'bank_short_name': self.bank_short_name,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'masked_account_number': self.masked_account_number,
            'account_holder_name': self.account_holder_name,
            'branch': self.branch or '',
            'is_default': self.is_default,
            'status': self.status,
            'status_label': self.status_label,
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else ''
        }


class PayoutHistory(db.Model):
    __tablename__ = 'payout_histories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    method_id = db.Column(db.String(36), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    bank = db.Column(db.String(50), nullable=True)
    masked_account = db.Column(db.String(50), nullable=True)
    summary = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('payout_histories', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'action': self.action,
            'method_id': self.method_id,
            'bank': self.bank or '',
            'masked_account': self.masked_account or '',
            'timestamp': self.created_at.isoformat() if self.created_at else '',
            'summary': self.summary or ''
        }



