from models import db, HirerProfile, Review, Contract, Job

CLIENT_TYPES = ('individual', 'business', 'agency', 'organization')
HIRER_INDUSTRIES = (
    'healthcare', 'legal', 'manufacturing', 'tourism', 'it', 'trade',
    'education', 'finance', 'construction', 'media', 'government', 'other',
)
WORK_MODES = ('onsite', 'online', 'both')
HIRING_FREQUENCIES = ('one_time', 'occasional', 'regular')
SERVICE_TYPE_OPTIONS = ('Dịch thuật', 'Phiên dịch', 'Hội họp', 'Kinh doanh', 'Du lịch', 'Sự kiện', 'Khác')
LOCATION_SUGGESTIONS = ('Hà Nội', 'TP. Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ', 'Online / Toàn quốc')


def _choice(value, allowed):
    value = (value or '').strip()
    return value if value in allowed else None


def _int_or_none(value):
    try:
        n = int(str(value).replace(',', '').replace('.', '').strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def apply_hirer_profile_form(profile, form, language_names):
    """Ghi dữ liệu form hồ sơ khách vào `profile` (không commit). Giá trị ngoài danh sách cho phép bị bỏ."""
    profile.title = form.get('title', '').strip()[:100]
    profile.company = form.get('company', '').strip()[:200]
    profile.location = form.get('location', '').strip()[:100]
    profile.client_type = _choice(form.get('client_type'), CLIENT_TYPES)
    profile.industry = _choice(form.get('industry'), HIRER_INDUSTRIES)
    website = form.get('website', '').strip()[:200]
    # chỉ nhận http(s) để tránh javascript: trong href
    profile.website = website if website.lower().startswith(('http://', 'https://')) else None
    profile.about = form.get('about', '').strip()[:2000] or None
    profile.default_source_lang = _choice(form.get('default_source_lang'), language_names)
    profile.default_target_lang = _choice(form.get('default_target_lang'), language_names)
    services = [s for s in form.getlist('preferred_service_types') if s in SERVICE_TYPE_OPTIONS]
    profile.preferred_service_types = ','.join(services)
    profile.work_mode = _choice(form.get('work_mode'), WORK_MODES)
    profile.hiring_frequency = _choice(form.get('hiring_frequency'), HIRING_FREQUENCIES)
    low = _int_or_none(form.get('typical_budget_min'))
    high = _int_or_none(form.get('typical_budget_max'))
    if low and high and high < low:
        low, high = high, low
    profile.typical_budget_min, profile.typical_budget_max = low, high
    profile.needs_nda = 'needs_nda' in form
    profile.needs_certified = 'needs_certified' in form
    profile.special_requirements = form.get('special_requirements', '').strip()[:1000] or None
    profile.tax_code = form.get('tax_code', '').strip()[:20] or None
    return profile


def get_or_create_hirer_profile(user_id):
    """Trả về HirerProfile của user, tạo mới (chưa commit) nếu chưa có."""
    profile = HirerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = HirerProfile(user_id=user_id)
        db.session.add(profile)
    return profile


def recalculate_hirer_rating(hirer_id):
    """Tính lại rating/total_reviews của khách từ các Review chưa bị ẩn.

    Không commit: caller chịu trách nhiệm commit.
    """
    visible = [
        r.rating for r in Review.query.filter_by(reviewee_id=hirer_id, is_hidden=False).all()
        if r.rating
    ]
    profile = get_or_create_hirer_profile(hirer_id)
    profile.total_reviews = len(visible)
    profile.rating = round(sum(visible) / len(visible), 1) if visible else 0.0
    return profile


def get_hirer_stats(hirer_id):
    """Số liệu hoạt động công khai của khách (dùng cho trang hồ sơ)."""
    total_jobs = Job.query.filter_by(hirer_id=hirer_id).count()
    contracts = Contract.query.filter_by(hirer_id=hirer_id).all()
    completed = sum(1 for c in contracts if c.status == 'completed')
    cancelled = sum(1 for c in contracts if c.status in ('cancelled', 'canceled'))
    finished = completed + cancelled
    return {
        'total_jobs': total_jobs,
        'completed_contracts': completed,
        'cancelled_contracts': cancelled,
        'completion_rate': round(completed * 100 / finished) if finished else None,
    }
