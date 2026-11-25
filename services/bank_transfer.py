"""Nhận tiền thật bằng chuyển khoản VietQR, đối soát qua webhook của SePay.

Luồng: mỗi hợp đồng có một nội dung chuyển khoản riêng (VT + mã hợp đồng). Khách quét QR,
ngân hàng báo về SePay, SePay gọi webhook của sàn. Sàn khớp nội dung và số tiền rồi mới
ghim tiền (hợp đồng sang `in_progress`). Khớp sai số tiền thì KHÔNG ghim, chỉ ghi lại để admin xử lý.

Cấu hình bằng biến môi trường (xem .env.example):
    PAYMENT_MODE      sandbox (mặc định, nút thanh toán giả) hoặc live (chỉ nhận tiền thật)
    BANK_CODE         mã hoặc tên ngân hàng theo VietQR, ví dụ MBBank, Vietcombank
    BANK_ACCOUNT      số tài khoản nhận tiền (tài khoản công ty, đã gắn với SePay)
    BANK_ACCOUNT_NAME tên chủ tài khoản, chỉ để hiển thị
    SEPAY_API_KEY     khóa tự đặt khi tạo webhook trên SePay, dùng để xác thực lời gọi
"""
import hmac
import os
import re
from urllib.parse import quote

from models import db, Contract, PaymentTransaction
from services import payments, lifecycle

CODE_PREFIX = 'VT'
_CODE_RE = re.compile(rf'{CODE_PREFIX}(\d+)', re.IGNORECASE)


def mode():
    return 'live' if os.environ.get('PAYMENT_MODE', 'sandbox').strip().lower() == 'live' else 'sandbox'


def is_live():
    return mode() == 'live'


def bank_config():
    return {
        'bank': os.environ.get('BANK_CODE', '').strip(),
        'account': os.environ.get('BANK_ACCOUNT', '').strip(),
        'name': os.environ.get('BANK_ACCOUNT_NAME', '').strip(),
    }


def live_ready():
    cfg = bank_config()
    return bool(cfg['bank'] and cfg['account'] and os.environ.get('SEPAY_API_KEY'))


def transfer_code(contract_id):
    """Nội dung chuyển khoản duy nhất của hợp đồng. Không dấu cách, không ký tự đặc biệt để ngân hàng giữ nguyên."""
    return f'{CODE_PREFIX}{int(contract_id)}'


def extract_contract_id(text):
    match = _CODE_RE.search(text or '')
    return int(match.group(1)) if match else None


def qr_url(contract):
    """Ảnh VietQR đã điền sẵn số tài khoản, số tiền và nội dung."""
    cfg = bank_config()
    amount = payments.amount_to_pay(contract)
    return (f"https://qr.sepay.vn/img?acc={quote(cfg['account'])}&bank={quote(cfg['bank'])}"
            f"&amount={amount}&des={quote(transfer_code(contract.id))}")


def verify_api_key(header_value):
    """Webhook gửi 'Authorization: Apikey <khóa>'. So sánh thời gian không đổi."""
    expected = os.environ.get('SEPAY_API_KEY', '')
    if not expected or not header_value:
        return False
    token = header_value.strip()
    if token.lower().startswith('apikey '):
        token = token[7:].strip()
    return hmac.compare_digest(token, expected)


def fund_contract(contract, payer_id, method, ref=None):
    """Khách đã trả: sàn ghim tiền và hợp đồng bắt đầu. Dùng chung cho sandbox và chuyển khoản thật."""
    from services.scheduling import confirm_slot
    from services.booking import contract_has_no_time_slot
    if not (True if contract_has_no_time_slot(contract) else confirm_slot(contract.id)):
        raise payments.PaymentError('Không giữ được lịch của phiên dịch viên (có thể đã hết hạn giữ chỗ).')
    contract.status = 'in_progress'
    deposit = payments.record_deposit(contract, payer_id, method=method)
    if ref:
        deposit.transaction_ref = ref
    lifecycle.mark_paid(contract)
    from models import ContractEvent
    db.session.add(ContractEvent(contract_id=contract.id, actor_id=payer_id, event_type='paid'))
    return deposit


def process_webhook(payload):
    """Xử lý một giao dịch tiền vào từ SePay. Không tự commit. Trả về (kết_quả, ghi_chú).

    Kết quả: funded | duplicate | ignored | mismatch | unknown_contract | cannot_fund.
    Lặp lại cùng một giao dịch (SePay gọi lại khi lỗi) luôn an toàn.
    """
    if str(payload.get('transferType', 'in')).lower() != 'in':
        return 'ignored', 'Không phải tiền vào'

    ref = str(payload.get('id') or payload.get('referenceCode') or '').strip()
    if not ref:
        return 'ignored', 'Thiếu mã giao dịch'
    ref = f'sepay:{ref}'
    if PaymentTransaction.query.filter_by(transaction_ref=ref).first() is not None:
        return 'duplicate', ref

    try:
        amount = int(payload.get('transferAmount') or 0)
    except (TypeError, ValueError):
        return 'ignored', 'Số tiền không hợp lệ'
    text = ' '.join(str(payload.get(k) or '') for k in ('code', 'content', 'description'))
    contract_id = extract_contract_id(text)
    if contract_id is None:
        return 'ignored', 'Nội dung không có mã hợp đồng'

    contract = Contract.query.with_for_update().filter_by(id=contract_id).first()
    if contract is None:
        return 'unknown_contract', f'Không có hợp đồng {contract_id}'

    due = payments.amount_to_pay(contract)
    if contract.status != 'escrow_pending':
        _flag(contract, ref, amount, 'Hợp đồng không còn chờ thanh toán, cần hoàn lại cho khách')
        return 'cannot_fund', 'Hợp đồng không ở trạng thái chờ thanh toán'
    if amount != due:
        _flag(contract, ref, amount, f'Chuyển {amount}đ nhưng cần đúng {due}đ')
        return 'mismatch', f'Cần {due}đ, nhận {amount}đ'

    try:
        fund_contract(contract, contract.hirer_id, 'bank_transfer', ref)
    except payments.PaymentError as e:
        _flag(contract, ref, amount, str(e))
        return 'cannot_fund', str(e)
    return 'funded', ref


def _flag(contract, ref, amount, note):
    """Ghi lại khoản tiền không tự xử lý được để admin đối soát và hoàn tiền thủ công."""
    db.session.add(PaymentTransaction(
        contract_id=contract.id, user_id=contract.hirer_id, kind='unmatched', amount=amount,
        status='failed', payment_method='bank_transfer', transaction_ref=ref))
    try:
        from models import AdminNotification
        db.session.add(AdminNotification(
            type='PAYMENT_ISSUE', title=f'Chuyển khoản cần xử lý, hợp đồng #{contract.id}',
            message=f'{note}. Mã giao dịch {ref}.', related_id=contract.id))
    except Exception:
        pass
