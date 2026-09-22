from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    auto_reply_enabled = db.Column(db.Boolean, default=False)
    auto_reply_message = db.Column(db.Text, nullable=True)
    auto_reply_cooldown_hours = db.Column(db.Integer, default=24)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HirerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    title = db.Column(db.String(100))
    company = db.Column(db.String(200))
    location = db.Column(db.String(100))
    rating = db.Column(db.Float, default=0.0)


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

    @property
    def display_category_text(self):
        group_text = 'Dịch thuật' if self.display_category_group == 'translation' else 'Phiên dịch & Khác'
        mapping = {
            'document_translation': "Dịch tài liệu",
            'website_translation': "Dịch website",
            'subtitle': "Dịch phụ đề",
            'proofreading': "Hiệu đính",
            'localization': "Bản địa hóa",
            'other_translation': "Dịch thuật khác",
            'conference': "Hội nghị / Cabin",
            'meeting': "Họp / Đàm phán",
            'business': "Kinh doanh / Thương mại",
            'travel': "Du lịch",
            'escort': "Tháp tùng",
            'event': "Sự kiện",
            'other_interpretation': "Dịch vụ khác"
        }
        type_text = mapping.get(self.display_service_type, self.category or 'Khác')
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
    is_auto_reply = db.Column(db.Boolean, default=False, nullable=False)
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
    is_auto_reply = db.Column(db.Boolean, default=False, nullable=False)
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

    translator = db.relationship('User', backref=db.backref('schedules', lazy=True))
    contract = db.relationship('Contract', backref=db.backref('schedule', uselist=False))
