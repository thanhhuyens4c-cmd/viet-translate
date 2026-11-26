"""Dòng tiền của hợp đồng: khách nạp, sàn giữ, giải ngân cho phiên dịch viên, rút tiền.

Mọi dòng tiền nằm trong một bảng `PaymentTransaction`, phân biệt bằng `kind`,
dùng chung cho dịch tài liệu và phiên dịch. Hàm ở đây KHÔNG tự commit;
route gọi chịu trách nhiệm commit hoặc rollback.
"""
from sqlalchemy import func

from models import db, Contract, PaymentTransaction, User
from services import pricing, refunds


class PaymentError(Exception):
    pass


TOPUP_MIN = 10_000
TOPUP_MAX = 50_000_000

# Phương thức nạp tiền vào ví. Tiền thật chỉ đi qua một đường duy nhất: chuyển khoản vào tài khoản
# công ty bằng mã VietQR, SePay đối soát qua webhook. App ngân hàng và các ví điện tử (MoMo, ZaloPay,
# VNPAY) đều quét được VietQR nên dùng chung đường này; chỉ khác hướng dẫn hiển thị.
# Thẻ quốc tế cần cổng thanh toán riêng nên chưa mở (available=False).
TOPUP_METHODS = {
    'bank':    {'label': 'Chuyển khoản ngân hàng', 'hint': 'Quét VietQR bằng app ngân hàng bất kỳ', 'available': True},
    'momo':    {'label': 'Ví MoMo', 'hint': 'Mở MoMo › Quét mã › Chuyển đến ngân hàng', 'available': True},
    'zalopay': {'label': 'ZaloPay', 'hint': 'Mở ZaloPay › Quét mã QR', 'available': True},
    'vnpay':   {'label': 'VNPAY QR', 'hint': 'Quét bằng app ngân hàng có VNPAY', 'available': True},
    'card':    {'label': 'Thẻ Visa / Mastercard', 'hint': 'Sắp ra mắt', 'available': False},
}


def normalize_topup_method(key):
    """Trả về mã phương thức hợp lệ đang mở; mặc định chuyển khoản ngân hàng."""
    key = (key or '').strip().lower()
    if key not in TOPUP_METHODS:
        return 'bank'
    if not TOPUP_METHODS[key]['available']:
        raise PaymentError(f"Phương thức {TOPUP_METHODS[key]['label']} chưa hỗ trợ. Vui lòng chọn phương thức khác.")
    return key


def method_label(payment_method):
    """Nhãn hiển thị cho cột payment_method (vd. 'sandbox:momo', 'bank_transfer', 'wallet')."""
    raw = payment_method or ''
    sandbox = raw.startswith('sandbox')
    key = raw.split(':', 1)[1] if ':' in raw else raw
    labels = {'bank_transfer': 'Chuyển khoản ngân hàng', 'wallet': 'Số dư ví', 'sandbox': 'Thử nghiệm',
              'original': 'Phương thức gốc'}
    label = TOPUP_METHODS[key]['label'] if key in TOPUP_METHODS else labels.get(key, key)
    return f'{label} (thử nghiệm)' if sandbox and key != 'sandbox' else label


def parse_amount(raw):
    """Đổi số tiền người dùng nhập ('1.000.000', '1,000,000', '1000000') thành int dương."""
    cleaned = str(raw if raw is not None else '').replace('.', '').replace(',', '').replace(' ', '').strip()
    if not cleaned.isdigit() or int(cleaned) <= 0:
        raise PaymentError('Số tiền không hợp lệ.')
    return int(cleaned)


def lock_wallet(user_id):
    """Khóa dòng user trong giao dịch hiện tại để hai yêu cầu cùng lúc không tiêu trùng một số dư.

    Số dư ví được tính từ sổ giao dịch nên không có dòng ví riêng để khóa; dòng user đóng vai khóa.
    SQLite không hỗ trợ FOR UPDATE và tự tuần tự hóa ghi, nên lệnh này không ảnh hưởng ở đó.
    """
    db.session.query(User.id).filter(User.id == user_id).with_for_update().first()


def prior_revenue(hirer_id, translator_id, exclude_contract_id=None):
    """Doanh thu đã hoàn thành giữa đúng cặp khách và phiên dịch viên (để xét mức hoa hồng 5%)."""
    query = db.session.query(func.coalesce(func.sum(Contract.agreed_price), 0)).filter(
        Contract.hirer_id == hirer_id,
        Contract.translator_id == translator_id,
        Contract.status == 'completed',
    )
    if exclude_contract_id is not None:
        query = query.filter(Contract.id != exclude_contract_id)
    return int(query.scalar() or 0)


def ensure_pricing_snapshot(contract):
    """Chốt số lượng, đơn giá và phí vào hợp đồng. Chạy lại không đổi gì nếu đã chốt."""
    if contract.commission is not None and contract.client_fee is not None:
        if contract.refund_policy is None:
            # Hợp đồng chốt phí trước khi có chính sách hủy: bổ sung theo loại công việc.
            job = contract.job
            contract.refund_policy = refunds.policy_for(
                job.display_category_group if job is not None else None,
                contract.pricing_unit, contract.quantity)
        return contract

    job = contract.job
    if job is not None:
        unit = pricing.normalize_unit(job.pricing_unit, job.category_group)
        quantity = pricing.normalize_quantity(job.quantity)
    else:
        # Đặt dịch vụ có sẵn (gói dịch vụ) thì tính trọn gói.
        unit, quantity = 'flat', 1

    fees = pricing.compute_fees(
        contract.agreed_price,
        prior_revenue(contract.hirer_id, contract.translator_id, exclude_contract_id=contract.id),
    )
    contract.pricing_unit = unit
    contract.quantity = quantity
    contract.refund_policy = refunds.policy_for(
        job.display_category_group if job is not None else None, unit, quantity)
    contract.unit_price = contract.agreed_price // quantity
    contract.client_fee = fees['client_fee']
    contract.commission = fees['commission']
    contract.translator_net = fees['translator_net']
    return contract


def amount_to_pay(contract):
    """Số tiền khách phải trả: giá hợp đồng cộng phí dịch vụ."""
    ensure_pricing_snapshot(contract)
    return contract.agreed_price + contract.client_fee


def record_deposit(contract, payer_id, method='sandbox'):
    """Khách thanh toán: sàn nhận và giữ tiền. Mỗi hợp đồng chỉ có một khoản nạp."""
    existing = PaymentTransaction.query.filter_by(contract_id=contract.id, kind='deposit').first()
    if existing is not None:
        return existing
    deposit = PaymentTransaction(
        contract_id=contract.id,
        user_id=payer_id,
        kind='deposit',
        amount=amount_to_pay(contract),
        status='escrow_pending',
        payment_method=method,
    )
    db.session.add(deposit)
    return deposit


def release_funds(contract):
    """Khách nghiệm thu: chuyển phần của phiên dịch viên, sàn giữ phí và hoa hồng.

    Tổng release + platform_fee luôn bằng đúng số tiền khách đã nạp.
    """
    deposit = PaymentTransaction.query.filter_by(contract_id=contract.id, kind='deposit').first()
    if deposit is None:
        # Hợp đồng cũ thanh toán trước khi có sổ giao dịch: dựng lại khoản nạp để số liệu khớp.
        deposit = record_deposit(contract, contract.hirer_id, method='legacy')
    if deposit.status != 'escrow_pending':
        raise PaymentError('Khoản tiền này không còn được giữ, không thể giải ngân.')

    ensure_pricing_snapshot(contract)
    deposit.status = 'completed'
    db.session.add(PaymentTransaction(
        contract_id=contract.id, user_id=contract.hirer_id, payee_id=contract.translator_id,
        kind='release', amount=contract.translator_net, status='completed',
        payment_method='wallet',
    ))
    db.session.add(PaymentTransaction(
        contract_id=contract.id, user_id=contract.hirer_id, payee_id=None,
        kind='platform_fee', amount=contract.client_fee + contract.commission,
        status='completed', payment_method='platform',
    ))


def wallet_balance(user_id):
    """Số dư có thể rút: tiền đã giải ngân và tiền hoàn vào ví, trừ tiền đã rút hoặc đang chờ rút.

    Voucher bồi thường và tiền hoàn về phương thức gốc không nằm trong số dư.
    """
    def total(*filters):
        return int(db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0))
                   .filter(PaymentTransaction.payee_id == user_id, *filters).scalar() or 0)

    earned = total(PaymentTransaction.kind == 'release', PaymentTransaction.status == 'completed')
    refunded = total(PaymentTransaction.kind == 'refund', PaymentTransaction.status == 'completed',
                     PaymentTransaction.payment_method == 'wallet')
    topped_up = total(PaymentTransaction.kind == 'topup', PaymentTransaction.status == 'completed')
    spent = total(PaymentTransaction.kind == 'wallet_payment', PaymentTransaction.status == 'completed')
    # Yêu cầu rút bị từ chối (status rejected) không bị trừ, tức tiền tự quay lại ví.
    withdrawn = total(PaymentTransaction.kind == 'withdraw',
                      PaymentTransaction.status.in_(['pending', 'completed']))
    return earned + refunded + topped_up - spent - withdrawn


def wallet_summary(user_id):
    """Tổng tiền vào / ra của ví theo từng nhóm, để hiện thống kê trên trang Ví."""
    rows = (db.session.query(PaymentTransaction.kind, func.coalesce(func.sum(PaymentTransaction.amount), 0))
            .filter(PaymentTransaction.payee_id == user_id, PaymentTransaction.status == 'completed')
            .group_by(PaymentTransaction.kind).all())
    by_kind = {k: int(v or 0) for k, v in rows}
    refunded_to_wallet = int(db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(
        PaymentTransaction.payee_id == user_id, PaymentTransaction.kind == 'refund',
        PaymentTransaction.status == 'completed', PaymentTransaction.payment_method == 'wallet').scalar() or 0)
    return {
        'topped_up': by_kind.get('topup', 0),
        'earned': by_kind.get('release', 0) + refunded_to_wallet,
        'spent': by_kind.get('wallet_payment', 0),
        'withdrawn': by_kind.get('withdraw', 0),
        'pending_withdraw': pending_withdrawal_total(user_id),
    }


def pending_withdrawal_total(user_id):
    return int(db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(
        PaymentTransaction.payee_id == user_id, PaymentTransaction.kind == 'withdraw',
        PaymentTransaction.status == 'pending').scalar() or 0)


def topup(user_id, amount, method='sandbox', ref=None):
    """Nạp tiền vào ví (không gắn hợp đồng). Chế độ live chỉ gọi từ webhook khi ngân hàng báo tiền vào."""
    if amount < TOPUP_MIN:
        raise PaymentError(f'Số tiền nạp tối thiểu là {TOPUP_MIN:,}đ.')
    if amount > TOPUP_MAX:
        raise PaymentError(f'Số tiền nạp tối đa mỗi lần là {TOPUP_MAX:,}đ.')
    tx = PaymentTransaction(
        contract_id=None, user_id=user_id, payee_id=user_id, kind='topup', amount=amount,
        status='completed', payment_method=method, transaction_ref=ref,
    )
    db.session.add(tx)
    return tx


def pay_from_wallet(contract, user_id):
    """Trừ số dư ví để trả hợp đồng. Caller ghim tiền tiếp bằng fund_contract(..., method='wallet')."""
    if user_id != contract.hirer_id:
        raise PaymentError('Chỉ khách hàng của hợp đồng mới thanh toán được.')
    existing = PaymentTransaction.query.filter_by(contract_id=contract.id, kind='wallet_payment').first()
    if existing is not None:
        raise PaymentError('Hợp đồng này đã được thanh toán bằng ví.')
    lock_wallet(user_id)
    due = amount_to_pay(contract)
    if wallet_balance(user_id) < due:
        raise PaymentError('Số dư ví không đủ. Vui lòng nạp thêm tiền.')
    tx = PaymentTransaction(
        contract_id=contract.id, user_id=user_id, payee_id=user_id, kind='wallet_payment',
        amount=due, status='completed', payment_method='wallet',
    )
    db.session.add(tx)
    return tx


def voucher_balance(user_id):
    return int(db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(
        PaymentTransaction.kind == 'voucher', PaymentTransaction.payee_id == user_id).scalar() or 0)


def request_withdrawal(user_id, amount, destination=None):
    """Gửi yêu cầu rút tiền về tài khoản chính chủ; admin chuyển khoản rồi đánh dấu hoàn tất.

    destination: chuỗi mô tả tài khoản nhận (ngân hàng, số tài khoản đã che, chủ tài khoản),
    lưu vào transaction_ref để admin biết chuyển về đâu.
    """
    try:
        amount = parse_amount(amount)
    except PaymentError:
        raise PaymentError('Số tiền rút không hợp lệ.')
    lock_wallet(user_id)
    if amount < pricing.WITHDRAW_MIN:
        raise PaymentError(f'Số tiền rút tối thiểu là {pricing.WITHDRAW_MIN:,}đ.')
    if amount > wallet_balance(user_id):
        raise PaymentError('Số dư không đủ để rút.')

    # Gắn giao dịch nhận tiền gần nhất làm mốc đối chiếu (nếu có); ví chỉ có tiền nạp thì để trống.
    anchor = PaymentTransaction.query.filter(
        PaymentTransaction.payee_id == user_id,
        PaymentTransaction.kind.in_(['release', 'refund']),
        PaymentTransaction.status == 'completed',
    ).order_by(PaymentTransaction.id.desc()).first()
    withdrawal = PaymentTransaction(
        contract_id=anchor.contract_id if anchor else None, user_id=user_id, payee_id=user_id,
        kind='withdraw', amount=amount, status='pending', payment_method='bank_transfer',
        transaction_ref=(destination or None) and str(destination)[:100],
    )
    db.session.add(withdrawal)
    return withdrawal


def complete_withdrawal(payment):
    """Admin đã chuyển khoản: áp dụng cho yêu cầu rút tiền và tiền hoàn về phương thức gốc đang chờ."""
    if payment.kind not in ('withdraw', 'refund') or payment.status != 'pending':
        raise PaymentError('Chỉ đánh dấu hoàn tất được khoản rút hoặc hoàn tiền đang chờ chuyển khoản.')
    payment.status = 'completed'
    return payment


def reject_withdrawal(payment, note=None):
    """Admin từ chối yêu cầu rút tiền: khoản rút thôi bị trừ nên tiền tự quay lại số dư ví."""
    if payment.kind != 'withdraw' or payment.status != 'pending':
        raise PaymentError('Chỉ từ chối được yêu cầu rút tiền đang chờ chuyển khoản.')
    payment.status = 'rejected'
    payment.note = (note or '').strip()[:255] or None
    return payment
