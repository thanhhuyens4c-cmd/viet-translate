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
    avatar = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship('TranslatorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    hirer_profile = db.relationship('HirerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    jobs_posted = db.relationship('Job', backref='hirer', lazy=True, cascade='all, delete-orphan')
    proposals = db.relationship('Proposal', backref='translator', lazy=True, cascade='all, delete-orphan')
    direct_messages_sent = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    preference = db.relationship('TranslatorPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(Notification.created_at)')

    @property
    def avatar_url(self):
        if self.avatar:
            if self.avatar.startswith('http://') or self.avatar.startswith('https://') or self.avatar.startswith('/'):
                return self.avatar
            return f'/static/uploads/avatars/{self.avatar}'

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
        if hasattr(self, 'verifications') and self.verifications:
            return self.verifications[0]
        return None


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

    services = db.relationship('Service', backref='profile', lazy=True)

    @property
    def avatar_url(self):
        return self.user.avatar_url if self.user else None

    @property
    def latest_verification(self):
        """Trả về yêu cầu xác minh mới nhất của phiên dịch viên."""
        return self.user.latest_verification if self.user else None


class TranslatorPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    languages = db.Column(db.Text, default='')
    language_pairs = db.Column(db.Text, default='')
    service_types = db.Column(db.Text, default='')
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

    @property
    def is_business(self):
        return self.account_type == 'business'


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    'VERIFICATION_APPROVED': 'VERIFICATION_APPROVED',
    'VERIFICATION_REJECTED': 'VERIFICATION_REJECTED'
}


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
    'APPROVE_JOB': 'APPROVE_JOB',
    'REJECT_JOB': 'REJECT_JOB',
    'FLAG_JOB': 'FLAG_JOB',
    'UNFLAG_JOB': 'UNFLAG_JOB',
    'DELETE_JOB': 'DELETE_JOB',
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

