"""Cách tính giá và phí chung cho mọi dịch vụ (dịch tài liệu và phiên dịch).

Một công thức duy nhất: giá hợp đồng = đơn giá x số lượng + phụ phí.
Số lượng là số trang, giờ, ngày hoặc buổi tùy `pricing_unit`; trọn kì và trọn gói
luôn là 1 khoản tổng. Phí nền tảng chỉ phụ
thuộc vào giá hợp đồng, không phụ thuộc loại dịch vụ.

Module này thuần tính toán (không đụng database) để dễ kiểm thử.
Mức phí theo điều khoản VietTranslate (dự thảo).
"""

PRICING_UNITS = ('page', 'hour', 'day', 'session', 'period', 'flat')

UNIT_LABELS = {
    'page': 'trang',
    'hour': 'giờ',
    'day': 'ngày',
    'session': 'buổi',
    'period': 'kì',
    'flat': 'trọn gói',
}

# Đơn vị trả một khoản tổng (không nhân số lượng): trọn gói và trọn kì.
LUMP_UNITS = ('period', 'flat')
# Đơn vị phải ghi rõ số giờ mỗi ngày / mỗi buổi để hai bên hiểu cùng một khối lượng.
UNITS_NEED_HOURS = ('day', 'session', 'period')
MAX_HOURS_PER_UNIT = 24
MAX_PERIOD_DAYS = 366

# Phí dịch vụ khách trả: đúng 2% giá hợp đồng.
CLIENT_FEE_PERCENT = 2

# Hoa hồng trừ vào phiên dịch viên: đúng 10%, còn 5% cho phần doanh thu với cùng
# một khách vượt 10 triệu.
# Không áp mức tối thiểu: trước đây phí tối thiểu 10.000đ / hoa hồng 20.000đ làm đơn nhỏ
# bị thu sai tỉ lệ (vd. hợp đồng 23.000đ mà phiên dịch viên chỉ nhận 3.000đ).
COMMISSION_PERCENT = 10
COMMISSION_PERCENT_LOYAL = 5
LOYAL_THRESHOLD = 10_000_000

WITHDRAW_MIN = 1_000  # rút tối thiểu 1.000đ mỗi lần


# Đơn vị hợp lệ theo nhóm dịch vụ: dịch tài liệu tính theo trang, phiên dịch (kể cả dịch cabin)
# tính theo giờ hoặc ngày, không bao giờ theo trang.
TRANSLATION_UNITS = ('page', 'flat')
INTERPRETATION_UNITS = ('hour', 'day', 'session', 'period', 'flat')


def default_unit(category_group):
    """Đơn vị mặc định khi công việc không ghi rõ: dịch viết tính theo trang, còn lại theo giờ."""
    return 'page' if category_group == 'translation' else 'hour'


def allowed_units(category_group):
    return TRANSLATION_UNITS if category_group == 'translation' else INTERPRETATION_UNITS


def normalize_unit(unit, category_group=None):
    """Đơn vị hợp lệ cho nhóm dịch vụ; sai nhóm (vd. phiên dịch mà chọn "trang") thì về mặc định."""
    unit = (unit or '').strip().lower()
    if unit not in PRICING_UNITS:
        return default_unit(category_group)
    if category_group is not None and unit not in allowed_units(category_group):
        return default_unit(category_group)
    return unit


def is_lump(unit):
    return unit in LUMP_UNITS


def describe_volume(unit, quantity=1, hours_per_unit=None, period_days=None):
    """Mô tả khối lượng dễ đọc, vd. "4 buổi × 3 giờ/buổi (tổng 12 giờ)", "Trọn kì 20 ngày × 4 giờ/ngày"."""
    q = normalize_quantity(quantity)
    h = int(hours_per_unit) if hours_per_unit else None
    if unit == 'page':
        return f'{q} trang'
    if unit == 'hour':
        return f'{q} giờ'
    if unit in ('day', 'session'):
        label = UNIT_LABELS[unit]
        text = f'{q} {label}'
        if h:
            text += f' × {h} giờ/{label}'
            if q > 1:
                text += f' (tổng {q * h} giờ)'
        return text
    if unit == 'period':
        days = int(period_days) if period_days else None
        text = 'Trọn kì'
        if days:
            text += f' {days} ngày'
            if h:
                text += f' × {h} giờ/ngày (tổng {days * h} giờ)'
        elif h:
            text += f', {h} giờ/ngày'
        return text
    return 'Trọn gói'


def normalize_quantity(quantity):
    """Số lượng luôn là số nguyên dương; thiếu hoặc sai thì coi là 1."""
    try:
        value = int(quantity)
    except (TypeError, ValueError):
        return 1
    return value if value > 0 else 1


def _percent(amount, percent):
    """Làm tròn nửa lên, chỉ dùng số nguyên để không lệch từng đồng."""
    return (amount * percent + 50) // 100


def compute_quote(unit_price, quantity, surcharge=0):
    """Giá hợp đồng = đơn giá x số lượng + phụ phí."""
    unit_price = max(int(unit_price or 0), 0)
    surcharge = max(int(surcharge or 0), 0)
    return unit_price * normalize_quantity(quantity) + surcharge


def compute_commission(amount, prior_revenue=0):
    """Hoa hồng trên số tiền phiên dịch viên thực nhận (mục 3): 10%, phần vượt 10 triệu còn 5%."""
    amount = max(int(amount or 0), 0)
    prior_revenue = max(int(prior_revenue or 0), 0)
    if amount == 0:
        return 0
    base_part = max(0, min(amount, LOYAL_THRESHOLD - prior_revenue))
    loyal_part = amount - base_part
    return _percent(base_part, COMMISSION_PERCENT) + _percent(loyal_part, COMMISSION_PERCENT_LOYAL)


def compute_fees(price, prior_revenue=0):
    """Tính phí cho một hợp đồng.

    price: giá hợp đồng (chưa gồm phí dịch vụ).
    prior_revenue: doanh thu đã hoàn thành trước đó giữa đúng cặp khách và
        phiên dịch viên này. Phần giá vượt LOYAL_THRESHOLD tính hoa hồng 5%.

    Trả về dict: client_fee, commission, translator_net, client_total, sàn thu.
    """
    price = max(int(price or 0), 0)
    prior_revenue = max(int(prior_revenue or 0), 0)

    if price == 0:
        return {'client_fee': 0, 'commission': 0, 'translator_net': 0,
                'client_total': 0, 'platform_revenue': 0}

    client_fee = _percent(price, CLIENT_FEE_PERCENT)

    commission = compute_commission(price, prior_revenue)

    return {
        'client_fee': client_fee,
        'commission': commission,
        'translator_net': price - commission,
        'client_total': price + client_fee,
        'platform_revenue': client_fee + commission,
    }
