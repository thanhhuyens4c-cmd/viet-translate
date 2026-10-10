from models import db, HirerProfile, Review, Contract, Job

WORK_MODES = ('onsite', 'online', 'both')
HIRING_FREQUENCIES = ('one_time', 'occasional', 'regular')

# Ngành của doanh nghiệp (BUSINESS_INDUSTRIES) -> lĩnh vực chuyên môn của phiên dịch viên (HIRING_FIELDS)
INDUSTRY_TO_FIELDS = {
    'Sản xuất / Công nghiệp': ('Sản xuất / Kỹ thuật',),
    'Thương mại / Xuất nhập khẩu': ('Đàm phán / Thương mại', 'Xuất nhập khẩu / Logistics'),
    'Du lịch / Khách sạn / Nhà hàng': ('Du lịch',),
    'Y tế / Dược': ('Y tế',),
    'Giáo dục / Đào tạo': ('Giáo dục / Du học',),
    'Công nghệ / IT': ('Công nghệ / IT',),
    'Tài chính / Ngân hàng / Bảo hiểm': ('Tài chính / Ngân hàng',),
    'Xây dựng / Bất động sản': ('Sản xuất / Kỹ thuật',),
    'Pháp lý / Tư vấn': ('Pháp lý / Công chứng',),
    'Truyền thông / Sự kiện': ('Hội nghị / Sự kiện',),
    'Logistics / Vận tải': ('Xuất nhập khẩu / Logistics',),
    'Nông nghiệp / Thực phẩm': ('Sản xuất / Kỹ thuật',),
}


def _split(value):
    return [p.strip() for p in (value or '').split(',') if p.strip()]


def hirer_expertise_fields(profile):
    """Các lĩnh vực chuyên môn (nhãn HIRING_FIELDS) mà khách cần, từ hiring_field (cá nhân) hoặc industry (doanh nghiệp).

    industry lưu dạng "A, B" nhưng nhãn có thể chứa " / " chứ không chứa ", " nên tách theo ", " là an toàn.
    """
    if not profile:
        return set()
    if profile.account_type == 'business':
        fields = set()
        for ind in _split(profile.industry):
            fields.update(INDUSTRY_TO_FIELDS.get(ind, ()))
        return fields
    return set(_split(profile.hiring_field))


def get_or_create_hirer_profile(user_id):
    """Trả về HirerProfile của user, tạo mới (chưa commit) nếu chưa có."""
    profile = HirerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = HirerProfile(user_id=user_id)
        db.session.add(profile)
    return profile


def recalculate_hirer_rating(hirer_id):
    """Tính lại rating/total_reviews của khách từ các Review chưa bị ẩn. Caller chịu trách nhiệm commit."""
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


def _choice(value, allowed):
    value = (value or '').strip()
    return value if value in allowed else None


def _int_or_none(value):
    try:
        n = int(str(value).replace(',', '').replace('.', '').strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def apply_hirer_hiring_needs(profile, form):
    """Ghi các trường nhu cầu thuê (không bắt buộc) vào profile. Giá trị ngoài danh sách cho phép bị bỏ."""
    profile.work_mode = _choice(form.get('work_mode'), WORK_MODES)
    profile.hiring_frequency = _choice(form.get('hiring_frequency'), HIRING_FREQUENCIES)
    low = _int_or_none(form.get('typical_budget_min'))
    high = _int_or_none(form.get('typical_budget_max'))
    if low and high and high < low:
        low, high = high, low
    profile.typical_budget_min, profile.typical_budget_max = low, high
    profile.needs_nda = 'needs_nda' in form
    profile.needs_certified = 'needs_certified' in form
    profile.special_requirements = (form.get('special_requirements') or '').strip()[:1000] or None
    return profile
