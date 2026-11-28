"""Chính sách hủy và hoàn tiền (điều khoản mục 5, 6, 7), phần thuần tính toán.

Không đụng database để dễ kiểm thử. Việc ghi sổ tiền nằm ở `services/lifecycle.py`.
Thời gian của lịch phiên dịch là giờ Việt Nam (UTC+7); phần còn lại của app dùng UTC.
"""
from datetime import datetime, timedelta

VN_OFFSET = timedelta(hours=7)

POLICIES = ('document', 'event', 'conference')

# Dịch tài liệu: phiên dịch viên được coi là đã bắt đầu sau 12 giờ kể từ khi khách thanh toán.
AUTO_START_HOURS = 12
# Khách không thanh toán trong 24 giờ thì hợp đồng tự hủy.
UNPAID_CANCEL_HOURS = 24
# Phiên dịch viên trễ hạn quá 24 giờ thì khách được hủy ngay.
LATE_GRACE_HOURS = 24
FREE_REVISIONS = 2
EVIDENCE_HOURS = 48
# Hủy khi phiên dịch viên đang làm mà hai bên không nộp bằng chứng: hoàn 50%.
DEFAULT_WORKING_REFUND_PERCENT = 50

# Tự giải ngân: dịch tài liệu 5 ngày (7 ngày nếu trên 20 trang), sự kiện 48 giờ sau khi kết thúc.
AUTO_RELEASE_DAYS = 5
AUTO_RELEASE_DAYS_LONG = 7
LONG_DOCUMENT_PAGES = 20
AUTO_RELEASE_EVENT_HOURS = 48
REMINDER_HOURS = 24

# Vi phạm của phiên dịch viên.
VIOLATION_LOCK_POINTS = 3
VIOLATION_LOCK_MONTHS = 12
FIRST_OFFENSE_MONTHS = 6
NO_SHOW_COMPENSATION_PERCENT = 10


def policy_for(category_group, pricing_unit, quantity):
    """Chốt loại chính sách hủy lúc tạo hợp đồng: tài liệu, sự kiện, hay hội nghị nhiều ngày."""
    if category_group == 'translation':
        return 'document'
    # Nhiều ngày (tính theo ngày) hoặc trọn kì nhiều ngày: áp chính sách hội nghị.
    if pricing_unit in ('day', 'period') and (quantity or 1) > 1:
        return 'conference'
    return 'event'


def event_refund_percent(policy, hours_until_start):
    """Phần trăm giá hợp đồng khách được hoàn khi hủy sự kiện, theo thời gian còn lại tới giờ bắt đầu."""
    if policy == 'conference':
        if hours_until_start >= 14 * 24:
            return 100
        if hours_until_start >= 7 * 24:
            return 50
        return 0
    if hours_until_start >= 7 * 24:
        return 100
    if hours_until_start >= 48:
        return 50
    return 0


def auto_release_deadline(policy, quantity, *, delivered_at=None, event_end=None):
    """Hạn tự giải ngân. Tài liệu tính từ lúc nộp bài, sự kiện tính từ lúc sự kiện kết thúc."""
    if policy == 'document':
        if delivered_at is None:
            return None
        days = AUTO_RELEASE_DAYS_LONG if (quantity or 0) > LONG_DOCUMENT_PAGES else AUTO_RELEASE_DAYS
        return delivered_at + timedelta(days=days)
    if event_end is None:
        return None
    return event_end + timedelta(hours=AUTO_RELEASE_EVENT_HOURS)


def _parse_date(value):
    if hasattr(value, 'year') and hasattr(value, 'month'):
        return value
    text = (value or '').strip()[:10]
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_time(value):
    text = (value or '').strip()[:5]
    try:
        return datetime.strptime(text, '%H:%M').time()
    except ValueError:
        return None


def to_utc(date_value, time_value):
    """Ngày giờ ghi trong hợp đồng (giờ Việt Nam) đổi sang UTC. Không đọc được thì trả None."""
    d = _parse_date(date_value)
    t = _parse_time(time_value)
    if d is None or t is None:
        return None
    return datetime.combine(d, t) - VN_OFFSET


def hours_between(later, earlier):
    return (later - earlier).total_seconds() / 3600.0
