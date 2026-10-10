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

    services = db.relationship('Service', backref='profile', lazy=True)

    @property
    def avatar_url(self):
        return self.user.avatar_url if self.user else None


class TranslatorPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    languages = db.Column(db.Text, default='')
    language_pairs = db.Column(db.Text, default='')
    service_types = db.Column(db.Text, default='')
    specialties = db.Column(db.Text, default='')    # CSV khóa ngành, cùng danh sách HIRER_INDUSTRIES
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
    total_reviews = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)

    # Thông tin phục vụ gợi ý phiên dịch viên phù hợp
    client_type = db.Column(db.String(30))          # individual / business / agency / organization
    industry = db.Column(db.String(60))             # xem HIRER_INDUSTRIES
    website = db.Column(db.String(200))
    about = db.Column(db.Text)
    default_source_lang = db.Column(db.String(50))
    default_target_lang = db.Column(db.String(50))
    preferred_service_types = db.Column(db.Text)    # CSV, cùng nhãn với TranslatorPreference.service_types
    work_mode = db.Column(db.String(20))            # onsite / online / both
    hiring_frequency = db.Column(db.String(20))     # one_time / occasional / regular
    typical_budget_min = db.Column(db.Integer)
    typical_budget_max = db.Column(db.Integer)
    needs_nda = db.Column(db.Boolean, default=False)
    needs_certified = db.Column(db.Boolean, default=False)
    special_requirements = db.Column(db.Text)
    tax_code = db.Column(db.String(20))             # riêng tư, chỉ admin dùng để xác minh


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
    'NEW_REVIEW': 'NEW_REVIEW'
}


SCHEDULE_STATUS = ('reserved', 'active', 'completed', 'cancelled')


class TranslatorSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    translator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True, unique=True)
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
    contract = db.relationship('Contract', backref=db.backref('schedule', uselist=False))


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
