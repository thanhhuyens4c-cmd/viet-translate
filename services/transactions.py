"""Truy vấn lịch sử giao dịch của khách thuê (hirer).

Chỉ ĐỌC dữ liệu từ DB. Trạng thái luôn lấy từ bản ghi backend
(PaymentTransaction / Contract); không nhận trạng thái từ frontend và
không ghi/đổi trạng thái ở đây.

Hệ thống hiện CHƯA có cổng thanh toán nên mọi bản ghi PaymentTransaction
phải do backend/nhà cung cấp tạo sau này. Hợp đồng không có bản ghi
thanh toán sẽ được hiển thị trung thực ('unrecorded' / 'awaiting_payment'),
không suy diễn thành "Thành công".
"""
from datetime import datetime

from flask import abort

from models import Contract, PaymentTransaction

PER_PAGE = 10

# Trạng thái hiển thị (thứ tự dùng cho bộ lọc)
STATUSES = ['awaiting_payment', 'processing', 'success', 'failed', 'refunded',
            'cancelled', 'unrecorded']

# PaymentTransaction.status -> trạng thái hiển thị
_PAYMENT_STATUS_MAP = {
    'pending': 'awaiting_payment',
    'escrow_pending': 'processing',   # chưa có bằng chứng giữ/giải ngân thật
    'completed': 'success',
    'failed': 'failed',
    'refunded': 'refunded',
}


def display_status(contract, payment):
    """Trạng thái hiển thị, suy ra hoàn toàn từ bản ghi backend."""
    if payment is not None:
        return _PAYMENT_STATUS_MAP.get(payment.status, 'processing')
    if contract.status == 'escrow_pending':
        return 'awaiting_payment'
    if contract.status == 'cancelled':
        return 'cancelled'
    # in_progress/completed nhưng không có bản ghi thanh toán nào
    return 'unrecorded'


def latest_payment(contract):
    payments = sorted(contract.payments, key=lambda p: (p.created_at or datetime.min, p.id))
    return payments[-1] if payments else None


def project_title(contract):
    if contract.job:
        return contract.job.title
    if contract.service:
        return contract.service.name
    if getattr(contract, 'interpreter_service', None):
        isvc = contract.interpreter_service
        spec = f" - {isvc.specialization}" if isvc.specialization else ""
        return f"Phiên dịch {isvc.source_lang} → {isvc.target_lang} ({isvc.interpreting_type}){spec}"
    return f'Hợp đồng #{contract.id}'


def _build_row(contract):
    payment = latest_payment(contract)
    return {
        'contract': contract,
        'payment': payment,
        'status': display_status(contract, payment),
        'title': project_title(contract),
        'order_code': f'HD{contract.id:06d}',
        'tx_code': (payment.transaction_ref or f'GD{payment.id:06d}') if payment else None,
        'date': (payment.created_at if payment else contract.created_at),
        'amount': payment.amount if payment else contract.agreed_price,
        'method': payment.payment_method if payment else None,
    }


def _matches(row, q):
    q = q.lower()
    hay = [row['order_code'], row['tx_code'], row['title'], str(row['contract'].id),
           row['payment'].transaction_ref if row['payment'] else None]
    return any(h and q in str(h).lower() for h in hay)


def list_hirer_transactions(hirer_id, q='', status='', page=1, per_page=PER_PAGE):
    """Trả về (rows, total, page, pages). Chỉ lấy hợp đồng của chính hirer_id."""
    contracts = (Contract.query.filter_by(hirer_id=hirer_id)
                 .order_by(Contract.created_at.desc(), Contract.id.desc()).all())
    rows = [_build_row(c) for c in contracts]
    if status in STATUSES:
        rows = [r for r in rows if r['status'] == status]
    q = (q or '').strip()
    if q:
        rows = [r for r in rows if _matches(r, q)]
    rows.sort(key=lambda r: r['date'], reverse=True)

    total = len(rows)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    start = (page - 1) * per_page
    return rows[start:start + per_page], total, page, pages


def get_hirer_transaction(hirer_id, contract_id):
    """Chi tiết 1 giao dịch kèm kiểm tra quyền: chỉ hirer của hợp đồng được xem."""
    contract = Contract.query.get_or_404(contract_id)
    if contract.hirer_id != hirer_id:
        abort(403)
    row = _build_row(contract)
    payments = sorted(contract.payments, key=lambda p: (p.created_at or datetime.min, p.id), reverse=True)
    return row, payments
