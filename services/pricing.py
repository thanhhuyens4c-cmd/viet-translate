"""Cách tính giá và phí chung cho mọi dịch vụ (dịch tài liệu và phiên dịch).

Một công thức duy nhất: giá hợp đồng = đơn giá x số lượng + phụ phí.
Số lượng là số trang, giờ hoặc ngày tùy `pricing_unit`. Phí nền tảng chỉ phụ
thuộc vào giá hợp đồng, không phụ thuộc loại dịch vụ.

Module này thuần tính toán (không đụng database) để dễ kiểm thử.
Mức phí theo điều khoản VietTranslate (dự thảo).
"""

PRICING_UNITS = ('page', 'hour', 'day', 'flat')

UNIT_LABELS = {
    'page': 'trang',
    'hour': 'giờ',
    'day': 'ngày',
    'flat': 'trọn gói',
}

# Phí dịch vụ khách trả: 2% giá hợp đồng, tối thiểu 10.000đ mỗi hợp đồng.
CLIENT_FEE_PERCENT = 2
CLIENT_FEE_MIN = 10_000

# Hoa hồng trừ vào phiên dịch viên: 10%, còn 5% cho phần doanh thu với cùng
# một khách vượt 10 triệu. Tối thiểu 20.000đ mỗi hợp đồng.
COMMISSION_PERCENT = 10
COMMISSION_PERCENT_LOYAL = 5
LOYAL_THRESHOLD = 10_000_000
COMMISSION_MIN = 20_000

WITHDRAW_MIN = 100_000


def default_unit(category_group):
    """Đơn vị mặc định khi công việc không ghi rõ: dịch viết tính theo trang, còn lại theo giờ."""
    return 'page' if category_group == 'translation' else 'hour'


def normalize_unit(unit, category_group=None):
    unit = (unit or '').strip().lower()
    return unit if unit in PRICING_UNITS else default_unit(category_group)


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
    """Hoa hồng trên số tiền phiên dịch viên thực nhận (mục 3): 10%, phần vượt 10 triệu còn 5%.

    Tối thiểu 20.000đ tính một lần cho cả hợp đồng, nhưng không vượt quá chính số tiền đó.
    Số tiền 0 thì không có hoa hồng.
    """
    amount = max(int(amount or 0), 0)
    prior_revenue = max(int(prior_revenue or 0), 0)
    if amount == 0:
        return 0
    base_part = max(0, min(amount, LOYAL_THRESHOLD - prior_revenue))
    loyal_part = amount - base_part
    commission = _percent(base_part, COMMISSION_PERCENT) + _percent(loyal_part, COMMISSION_PERCENT_LOYAL)
    return min(max(commission, COMMISSION_MIN), amount)


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

    client_fee = max(_percent(price, CLIENT_FEE_PERCENT), CLIENT_FEE_MIN)

    commission = compute_commission(price, prior_revenue)

    return {
        'client_fee': client_fee,
        'commission': commission,
        'translator_net': price - commission,
        'client_total': price + client_fee,
        'platform_revenue': client_fee + commission,
    }
