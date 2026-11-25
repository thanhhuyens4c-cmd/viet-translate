"""Dịch vụ Ví cá nhân.

Mọi thao tác thay đổi số dư đều đi qua module này để:
- Khóa dòng ví (SELECT ... FOR UPDATE) tránh trừ tiền 2 lần khi request đồng thời.
- Luôn ghi một WalletTransaction kèm số dư sau giao dịch (sổ cái).

Các hàm KHÔNG commit — caller chịu trách nhiệm commit/rollback.
"""
from models import db, Wallet, WalletTransaction, WALLET_TX_TYPES

PLATFORM_FEE_RATE = 0.10
MIN_DEPOSIT = 10_000
MAX_DEPOSIT = 100_000_000
MIN_WITHDRAW = 50_000


class WalletError(Exception):
    """Lỗi nghiệp vụ ví (số dư không đủ, số tiền không hợp lệ...)."""


def platform_fee(amount):
    return int(amount * PLATFORM_FEE_RATE)


def get_or_create_wallet(user_id, lock=False):
    query = Wallet.query.filter_by(user_id=user_id)
    if lock:
        query = query.with_for_update()
    wallet = query.first()
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=0, pending_balance=0)
        db.session.add(wallet)
        db.session.flush()
    return wallet


def parse_amount(raw):
    """Chuyển chuỗi người dùng nhập ('1.000.000', '1,000,000', '1000000') thành int."""
    if raw is None:
        raise WalletError('Vui lòng nhập số tiền.')
    cleaned = str(raw).replace('.', '').replace(',', '').replace(' ', '').strip()
    if not cleaned.isdigit():
        raise WalletError('Số tiền không hợp lệ.')
    amount = int(cleaned)
    if amount <= 0:
        raise WalletError('Số tiền phải lớn hơn 0.')
    return amount


def _record(wallet, tx_type, amount, description, status='completed', contract_id=None, **extra):
    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=tx_type,
        amount=amount,
        balance_after=wallet.balance,
        status=status,
        description=description,
        contract_id=contract_id,
        **extra,
    )
    db.session.add(tx)
    return tx


def deposit(user_id, amount, method='bank_transfer'):
    if amount < MIN_DEPOSIT:
        raise WalletError(f'Số tiền nạp tối thiểu là {MIN_DEPOSIT:,} VND.')
    if amount > MAX_DEPOSIT:
        raise WalletError(f'Số tiền nạp tối đa mỗi lần là {MAX_DEPOSIT:,} VND.')
    wallet = get_or_create_wallet(user_id, lock=True)
    wallet.balance += amount
    method_label = {'bank_transfer': 'chuyển khoản', 'card': 'thẻ', 'momo': 'MoMo'}.get(method, method)
    return _record(wallet, WALLET_TX_TYPES['DEPOSIT'], amount, f'Nạp tiền qua {method_label}')


def request_withdraw(user_id, amount, bank_name, bank_account, bank_holder):
    bank_name = (bank_name or '').strip()
    bank_account = (bank_account or '').strip()
    bank_holder = (bank_holder or '').strip()
    if not bank_name or not bank_account or not bank_holder:
        raise WalletError('Vui lòng nhập đầy đủ thông tin ngân hàng.')
    if not bank_account.replace(' ', '').isdigit() or not (6 <= len(bank_account.replace(' ', '')) <= 20):
        raise WalletError('Số tài khoản ngân hàng không hợp lệ.')
    if amount < MIN_WITHDRAW:
        raise WalletError(f'Số tiền rút tối thiểu là {MIN_WITHDRAW:,} VND.')
    wallet = get_or_create_wallet(user_id, lock=True)
    if wallet.balance < amount:
        raise WalletError('Số dư ví không đủ để rút.')
    wallet.balance -= amount
    wallet.pending_balance += amount
    return _record(
        wallet, WALLET_TX_TYPES['WITHDRAW'], -amount,
        f'Rút tiền về {bank_name}', status='pending',
        bank_name=bank_name[:100], bank_account=bank_account[:50], bank_holder=bank_holder[:100].upper(),
    )


def approve_withdraw(tx, note=None):
    if tx.type != WALLET_TX_TYPES['WITHDRAW'] or tx.status != 'pending':
        raise WalletError('Yêu cầu rút tiền không ở trạng thái chờ duyệt.')
    wallet = Wallet.query.filter_by(id=tx.wallet_id).with_for_update().first()
    wallet.pending_balance -= abs(tx.amount)
    tx.status = 'completed'
    tx.admin_note = (note or '')[:255] or None
    return tx


def reject_withdraw(tx, note=None):
    if tx.type != WALLET_TX_TYPES['WITHDRAW'] or tx.status != 'pending':
        raise WalletError('Yêu cầu rút tiền không ở trạng thái chờ duyệt.')
    wallet = Wallet.query.filter_by(id=tx.wallet_id).with_for_update().first()
    amount = abs(tx.amount)
    wallet.pending_balance -= amount
    wallet.balance += amount
    tx.status = 'rejected'
    tx.admin_note = (note or '')[:255] or None
    return _record(wallet, WALLET_TX_TYPES['REFUND'], amount,
                   f'Hoàn lại yêu cầu rút tiền #{tx.id} bị từ chối')


def pay_contract(user_id, contract):
    """Khách thuê trả tiền hợp đồng từ ví (tiền chuyển vào escrow của nền tảng)."""
    amount = int(contract.agreed_price)
    wallet = get_or_create_wallet(user_id, lock=True)
    if wallet.balance < amount:
        raise WalletError('Số dư ví không đủ. Vui lòng nạp thêm tiền.')
    wallet.balance -= amount
    return _record(wallet, WALLET_TX_TYPES['PAYMENT'], -amount,
                   f'Thanh toán hợp đồng #{contract.id} (giữ trong Escrow)', contract_id=contract.id)


def release_to_translator(contract):
    """Giải ngân escrow cho phiên dịch viên khi nghiệm thu (đã trừ phí nền tảng). Idempotent."""
    existing = WalletTransaction.query.filter_by(
        contract_id=contract.id, type=WALLET_TX_TYPES['EARNING']).first()
    if existing:
        return existing
    net = int(contract.agreed_price) - platform_fee(contract.agreed_price)
    wallet = get_or_create_wallet(contract.translator_id, lock=True)
    wallet.balance += net
    return _record(wallet, WALLET_TX_TYPES['EARNING'], net,
                   f'Thu nhập hợp đồng #{contract.id} (đã trừ phí {int(PLATFORM_FEE_RATE * 100)}%)',
                   contract_id=contract.id)


def refund_contract(contract, amount=None):
    """Hoàn tiền hợp đồng về ví khách thuê. Idempotent theo contract."""
    existing = WalletTransaction.query.filter_by(
        contract_id=contract.id, type=WALLET_TX_TYPES['REFUND']).first()
    if existing:
        return existing
    amount = int(amount if amount is not None else contract.agreed_price)
    wallet = get_or_create_wallet(contract.hirer_id, lock=True)
    wallet.balance += amount
    return _record(wallet, WALLET_TX_TYPES['REFUND'], amount,
                   f'Hoàn tiền hợp đồng #{contract.id}', contract_id=contract.id)
