"""Vòng đời tiền của hợp đồng: bắt đầu, nộp bài, sửa bài, hủy, hoàn tiền, tranh chấp, tự giải ngân.

Dùng chung cho dịch tài liệu và phiên dịch; chỉ khác chính sách (`contract.refund_policy`).
Các hàm ở đây KHÔNG tự commit: route hoặc cron gọi chịu trách nhiệm commit hoặc rollback.
Mọi dòng tiền đi qua `PaymentTransaction`; mỗi lần tách tiền luôn có
hoàn + giải ngân + phí sàn = đúng số khách đã nạp.
"""
from datetime import datetime, timedelta

from models import (db, Contract, PaymentTransaction, TranslatorProfile,
                    TranslatorSchedule, TranslatorViolation, User)
from services import payments, pricing, refunds


class LifecycleError(Exception):
    pass


# Hợp đồng đang được sàn giữ tiền: đang làm, hoặc khách đã yêu cầu sửa bài.
FUNDED_STATUSES = ('in_progress', 'revision_requested')


def _has_active_dispute(contract):
    """Hợp đồng có khiếu nại đang xử lý (hệ thống khiếu nại trong disputes.py) thì tiền bị đóng băng."""
    from disputes import active_dispute
    return active_dispute(contract.id) is not None


def _require_not_frozen(contract):
    if _has_active_dispute(contract):
        raise LifecycleError('Hợp đồng đang có khiếu nại chưa giải quyết, tiền đang bị đóng băng.')


# ─── Mốc thời gian ────────────────────────────────────────────────────────────

def _now(now):
    return now or datetime.utcnow()


def event_start(contract):
    return refunds.to_utc(contract.scheduled_date, contract.scheduled_time_start)


def event_end(contract):
    return refunds.to_utc(contract.scheduled_date, contract.scheduled_time_end)


def has_started(contract, now=None):
    """Đã bắt đầu làm khi bấm "Bắt đầu", hoặc 12 giờ sau khi khách thanh toán, mốc nào đến trước."""
    if contract.started_at is not None:
        return True
    if contract.paid_at is None:
        return False
    return _now(now) >= contract.paid_at + timedelta(hours=refunds.AUTO_START_HOURS)


def is_funded(contract):
    """Sàn đang giữ tiền của hợp đồng này (đã nạp, chưa giải ngân hay hoàn)."""
    return contract.status in FUNDED_STATUSES and PaymentTransaction.query.filter_by(
        contract_id=contract.id, kind='deposit', status='escrow_pending').first() is not None


# ─── Thanh toán, bắt đầu, nộp bài, sửa bài ────────────────────────────────────

def mark_paid(contract, now=None):
    """Khách đã thanh toán: ghi mốc giữ tiền và, với sự kiện, hạn tự giải ngân."""
    now = _now(now)
    payments.ensure_pricing_snapshot(contract)
    contract.paid_at = now
    if contract.refund_policy != 'document':
        contract.auto_release_at = refunds.auto_release_deadline(
            contract.refund_policy, contract.quantity, event_end=event_end(contract))


def start_work(contract, user_id, now=None):
    if user_id != contract.translator_id:
        raise LifecycleError('Chỉ phiên dịch viên của hợp đồng mới bấm được "Bắt đầu".')
    if contract.status not in FUNDED_STATUSES:
        raise LifecycleError('Phiên dịch viên chỉ bắt đầu khi hợp đồng ở trạng thái đang giữ tiền.')
    if contract.started_at is None:
        contract.started_at = _now(now)


def register_delivery(contract, now=None):
    """Phiên dịch viên nộp bài (dịch tài liệu). Hạn tự giải ngân tính lại từ đầu sau mỗi lần nộp."""
    now = _now(now)
    if contract.started_at is None:
        contract.started_at = now
    contract.delivered_at = now
    if contract.refund_policy == 'document':
        contract.auto_release_at = refunds.auto_release_deadline(
            'document', contract.quantity, delivered_at=now)
        contract.release_reminded_at = None


def note_revision_requested(contract):
    """Ghi nhận một lần yêu cầu sửa bài (gọi từ services/projects.py). Mỗi đơn có 2 lần sửa miễn phí, chỉ dịch tài liệu."""
    if contract.refund_policy is None:
        payments.ensure_pricing_snapshot(contract)
    if contract.refund_policy != 'document':
        raise LifecycleError('Phiên dịch tại sự kiện không áp dụng sửa bài miễn phí.')
    if (contract.revisions_used or 0) >= refunds.FREE_REVISIONS:
        raise LifecycleError('Đã hết 2 lần sửa miễn phí. Nếu bài vẫn chưa đạt, bạn có thể gửi khiếu nại.')
    contract.revisions_used = (contract.revisions_used or 0) + 1
    contract.delivered_at = None
    contract.auto_release_at = None


# ─── Giải ngân ────────────────────────────────────────────────────────────────

def complete_contract(contract):
    """Nghiệm thu (khách bấm hoặc tự giải ngân): trừ hoa hồng, chuyển phần còn lại cho phiên dịch viên."""
    payments.release_funds(contract)
    contract.status = 'completed'
    contract.auto_release_at = None
    if contract.job:
        contract.job.status = 'completed'
    profile = TranslatorProfile.query.filter_by(user_id=contract.translator_id).first()
    if profile:
        profile.total_jobs = (profile.total_jobs or 0) + 1


# ─── Chia tiền khi hủy hoặc tranh chấp ────────────────────────────────────────

def settle(contract, refund_percent, *, refund_fee, refund_to='wallet', waive_commission=False,
           cancelled_by=None, reason=None, final_status='cancelled'):
    """Chia số tiền sàn đang giữ giữa khách, phiên dịch viên và sàn.

    refund_percent: phần trăm GIÁ HỢP ĐỒNG hoàn cho khách (0-100).
    refund_fee: có hoàn cả phí dịch vụ 2% hay không.
    refund_to: 'wallet' (vào ví ngay) hoặc 'original' (về phương thức gốc, admin chuyển khoản rồi đánh dấu).
    Hoa hồng chỉ tính trên phần phiên dịch viên thực nhận.
    """
    deposit = PaymentTransaction.query.filter_by(contract_id=contract.id, kind='deposit').first()
    if deposit is None or deposit.status != 'escrow_pending':
        raise LifecycleError('Khoản tiền này không còn được giữ, không thể hoàn hay chia.')
    if refund_to not in ('wallet', 'original'):
        raise LifecycleError('Nơi nhận tiền hoàn không hợp lệ.')
    if deposit.payment_method == 'wallet':
        # Khách đã trả bằng số dư ví: "phương thức gốc" chính là ví, hoàn ngay không cần chuyển khoản.
        refund_to = 'wallet'

    payments.ensure_pricing_snapshot(contract)
    refund_percent = min(max(int(refund_percent), 0), 100)
    price = contract.agreed_price
    refund_price = price * refund_percent // 100
    translator_part = price - refund_price

    commission = 0
    if translator_part > 0 and not waive_commission:
        commission = pricing.compute_commission(
            translator_part,
            payments.prior_revenue(contract.hirer_id, contract.translator_id, exclude_contract_id=contract.id))
    translator_net = translator_part - commission
    fee_back = contract.client_fee if refund_fee else 0
    refund_total = refund_price + fee_back
    platform_fee = (contract.client_fee - fee_back) + commission

    if refund_total + translator_net + platform_fee != deposit.amount:
        raise LifecycleError('Tách tiền không khớp số đã nạp.')

    deposit.status = 'refunded' if translator_net == 0 and platform_fee == 0 else 'completed'
    if refund_total > 0:
        db.session.add(PaymentTransaction(
            contract_id=contract.id, user_id=contract.hirer_id, payee_id=contract.hirer_id,
            kind='refund', amount=refund_total,
            status='completed' if refund_to == 'wallet' else 'pending', payment_method=refund_to))
    if translator_net > 0:
        db.session.add(PaymentTransaction(
            contract_id=contract.id, user_id=contract.hirer_id, payee_id=contract.translator_id,
            kind='release', amount=translator_net, status='completed', payment_method='wallet'))
    if platform_fee > 0:
        db.session.add(PaymentTransaction(
            contract_id=contract.id, user_id=contract.hirer_id, payee_id=None,
            kind='platform_fee', amount=platform_fee, status='completed', payment_method='platform'))

    contract.status = final_status
    contract.auto_release_at = None
    if final_status == 'cancelled':
        contract.cancelled_by = cancelled_by
        contract.cancel_reason = (reason or '')[:255]
        _cancel_schedule(contract)
    if translator_net > 0 and final_status == 'completed':
        profile = TranslatorProfile.query.filter_by(user_id=contract.translator_id).first()
        if profile:
            profile.total_jobs = (profile.total_jobs or 0) + 1
    return {'refund': refund_total, 'translator_net': translator_net,
            'commission': commission, 'platform_fee': platform_fee}


def _cancel_schedule(contract):
    schedule = TranslatorSchedule.query.filter_by(contract_id=contract.id).first()
    if schedule and schedule.status in ('reserved', 'active'):
        schedule.status = 'cancelled'


def _close_job(contract, reopen):
    job = contract.job
    if job is not None and job.status in ('open', 'in_progress', 'hired', 'assigned', 'closed', 'filled'):
        job.status = 'open' if reopen else 'cancelled'


# ─── Khách hủy ────────────────────────────────────────────────────────────────

def hirer_cancel_percent(contract, now=None):
    """Phần trăm giá hợp đồng khách được hoàn khi tự hủy, hoặc None nếu cần sàn phân xử.

    Trả về (phần_trăm, lý_do).
    """
    now = _now(now)
    if contract.refund_policy == 'document':
        if not has_started(contract, now):
            return 100, 'Hủy trước khi phiên dịch viên bắt đầu làm'
        return None, 'Hủy khi phiên dịch viên đang làm, cần sàn phân xử'

    start = event_start(contract)
    if start is None:
        return None, 'Hợp đồng không có giờ bắt đầu rõ ràng, cần sàn phân xử'
    hours = refunds.hours_between(start, now)
    return refunds.event_refund_percent(contract.refund_policy, hours), 'Hủy lịch phiên dịch trước giờ bắt đầu'


def cancel_by_hirer(contract, user_id, *, now=None, refund_to='wallet', disaster=False):
    """Khách hủy hợp đồng. Trả về ('cancelled', kết_quả) hoặc ('dispute', Dispute) khi cần sàn phân xử."""
    now = _now(now)
    if user_id != contract.hirer_id:
        raise LifecycleError('Chỉ khách hàng của hợp đồng mới hủy được.')

    if contract.status == 'escrow_pending':
        contract.status = 'cancelled'
        contract.cancelled_by = 'hirer'
        contract.cancel_reason = 'Khách hủy trước khi thanh toán'
        _cancel_schedule(contract)
        _close_job(contract, reopen=True)
        return 'cancelled', {'refund': 0}
    if contract.status not in FUNDED_STATUSES:
        raise LifecycleError('Hợp đồng ở trạng thái này không hủy được.')
    _require_not_frozen(contract)

    if disaster:
        # Thiên tai, dịch bệnh, lệnh nhà nước: hoàn 100%, sàn miễn hoa hồng. Chỉ admin xác nhận được.
        raise LifecycleError('Hủy do bất khả kháng cần nhân viên sàn xác nhận, vui lòng gửi khiếu nại.')

    percent, reason = hirer_cancel_percent(contract, now)
    if percent is None:
        # Cần sàn phân xử: khách gửi khiếu nại, tiền được giữ cho tới khi có kết luận.
        return 'dispute', None

    result = settle(contract, percent, refund_fee=percent > 0, refund_to=refund_to,
                    cancelled_by='hirer', reason=reason)
    _close_job(contract, reopen=False)
    return 'cancelled', result


def hirer_cancel_percent_applied(contract):
    """Phần trăm giá đã hoàn cho khách ở lần hủy vừa ghi sổ (để hiện thông báo)."""
    refund = PaymentTransaction.query.filter_by(contract_id=contract.id, kind='refund').first()
    if refund is None or not contract.agreed_price:
        return 0
    return min(100, round(100 * (refund.amount - (contract.client_fee or 0)) / contract.agreed_price))         if refund.amount > (contract.client_fee or 0) else 0


def cancel_for_late_delivery(contract, user_id, *, now=None):
    """Phiên dịch viên trễ hạn quá 24 giờ: khách hủy ngay, hoàn 100% kể cả phí, về phương thức gốc."""
    now = _now(now)
    if user_id != contract.hirer_id:
        raise LifecycleError('Chỉ khách hàng của hợp đồng mới hủy được.')
    if contract.status not in FUNDED_STATUSES or contract.delivered_at is not None:
        raise LifecycleError('Chỉ hủy vì trễ hạn được khi phiên dịch viên chưa nộp bài.')
    _require_not_frozen(contract)
    deadline = contract.job.deadline if contract.job is not None else None
    if deadline is None:
        raise LifecycleError('Hợp đồng không có hạn nộp bài nên không xét trễ hạn.')
    limit = datetime.combine(deadline, datetime.min.time()) + timedelta(days=1, hours=refunds.LATE_GRACE_HOURS)
    if now < limit:
        raise LifecycleError('Phiên dịch viên chưa trễ hạn quá 24 giờ.')
    result = settle(contract, 100, refund_fee=True, refund_to='original',
                    cancelled_by='hirer', reason='Phiên dịch viên trễ hạn quá 24 giờ', waive_commission=True)
    _close_job(contract, reopen=True)
    return result


# ─── Phiên dịch viên hủy hoặc vắng mặt ────────────────────────────────────────

def _lead_days(contract, now):
    start = event_start(contract)
    if start is None and contract.job is not None and contract.job.deadline is not None:
        start = datetime.combine(contract.job.deadline, datetime.min.time()) - refunds.VN_OFFSET
    if start is None:
        return 0
    return refunds.hours_between(start, now) / 24.0


def violation_points(translator_id, months, now=None):
    since = _now(now) - timedelta(days=30 * months)
    rows = TranslatorViolation.query.filter(
        TranslatorViolation.translator_id == translator_id,
        TranslatorViolation.created_at >= since).all()
    return sum(r.points or 0 for r in rows)


def _record_violation(contract, points, reason, now):
    if points <= 0:
        return
    db.session.add(TranslatorViolation(
        translator_id=contract.translator_id, contract_id=contract.id,
        points=points, reason=reason[:255], created_at=now))
    db.session.flush()
    if violation_points(contract.translator_id, refunds.VIOLATION_LOCK_MONTHS, now) >= refunds.VIOLATION_LOCK_POINTS:
        user = User.query.get(contract.translator_id)
        if user is not None:
            user.is_active = False   # khóa để sàn xem xét


def cancel_by_translator(contract, *, now=None, no_show=False, excused=False, refund_to='wallet'):
    """Phiên dịch viên hủy hoặc không đến: khách luôn được hoàn 100% kể cả phí 2%.

    - Hủy từ 7 ngày trở lên: chỉ ghi vi phạm nếu trong 6 tháng qua đã có vi phạm.
    - Hủy dưới 7 ngày: 1 vi phạm.
    - Không đến hoặc không nộp bài, không báo trước: 2 vi phạm và voucher bồi thường 10% giá hợp đồng.
    - Ốm đau, tai nạn có giấy tờ (excused): không ghi vi phạm, không voucher.
    """
    now = _now(now)
    if contract.status not in FUNDED_STATUSES + ('escrow_pending',):
        raise LifecycleError('Hợp đồng ở trạng thái này không hủy được.')

    funded = contract.status in FUNDED_STATUSES
    if funded:
        settle(contract, 100, refund_fee=True, refund_to=refund_to, waive_commission=True,
               cancelled_by='translator',
               reason='Phiên dịch viên không đến' if no_show else 'Phiên dịch viên hủy')
    else:
        contract.status = 'cancelled'
        contract.cancelled_by = 'translator'
        contract.cancel_reason = 'Phiên dịch viên hủy trước khi khách thanh toán'
        _cancel_schedule(contract)
    _close_job(contract, reopen=True)

    voucher = 0
    if not excused:
        if no_show:
            _record_violation(contract, 2, 'Không đến hoặc không nộp bài, không báo trước', now)
            if funded:
                voucher = contract.agreed_price * refunds.NO_SHOW_COMPENSATION_PERCENT // 100
                if voucher > 0:
                    db.session.add(PaymentTransaction(
                        contract_id=contract.id, user_id=contract.translator_id, payee_id=contract.hirer_id,
                        kind='voucher', amount=voucher, status='completed', payment_method='voucher'))
        elif _lead_days(contract, now) >= 7:
            if violation_points(contract.translator_id, refunds.FIRST_OFFENSE_MONTHS, now) > 0:
                _record_violation(contract, 1, 'Hủy trước 7 ngày, đã có vi phạm trong 6 tháng', now)
        else:
            _record_violation(contract, 1, 'Hủy trước dưới 7 ngày', now)
    return {'voucher': voucher}


# ─── Kết luận khiếu nại ghi vào sổ tiền ───────────────────────────────────────

def apply_dispute_resolution(contract, resolution, dispute_id):
    """Kết luận khiếu nại (disputes.py) và chia tiền qua sổ giao dịch.

    keep_100: giải ngân đủ cho phiên dịch viên. refund_50: hoàn 50% giá (kèm phí 2%), phần còn lại
    cho phiên dịch viên sau hoa hồng. cancel_payment: hoàn 100% kể cả phí, miễn hoa hồng.
    Trả về giá cuối cùng phiên dịch viên được tính (để hiển thị).
    """
    price = contract.agreed_price
    if resolution == 'keep_100':
        complete_contract(contract)
        return price
    if resolution == 'refund_50':
        settle(contract, 50, refund_fee=True, cancelled_by='admin',
               reason=f'Khiếu nại #{dispute_id}: hoàn 50%', final_status='completed')
        if contract.job:
            contract.job.status = 'completed'
        return price - price * 50 // 100
    if resolution == 'cancel_payment':
        settle(contract, 100, refund_fee=True, waive_commission=True, cancelled_by='admin',
               reason=f'Khiếu nại #{dispute_id}: hoàn 100%')
        _close_job(contract, reopen=False)
        return 0
    raise LifecycleError('Kết luận không hợp lệ.')


# ─── Việc chạy định kỳ ────────────────────────────────────────────────────────

def run_scheduled_jobs(now=None, notify=None):
    """Chạy bởi cron mỗi ngày: hủy hợp đồng chưa thanh toán quá 24 giờ, nhắc nghiệm thu, tự giải ngân.

    notify(user_id, type, title, message, contract_id) tùy chọn, để gửi thông báo trong app.
    Trả về số lượng từng loại. Hợp đồng đang tranh chấp không bao giờ tự giải ngân.
    """
    now = _now(now)
    notify = notify or (lambda *a, **k: None)
    stats = {'unpaid_cancelled': 0, 'reminded': 0, 'auto_released': 0}

    cutoff = now - timedelta(hours=refunds.UNPAID_CANCEL_HOURS)
    for c in Contract.query.filter(Contract.status == 'escrow_pending', Contract.updated_at <= cutoff).all():
        c.status = 'cancelled'
        c.cancelled_by = 'system'
        c.cancel_reason = 'Khách không thanh toán trong 24 giờ'
        _cancel_schedule(c)
        _close_job(c, reopen=True)
        notify(c.hirer_id, 'CONTRACT_CANCELLED', 'Hợp đồng đã tự hủy',
               'Hợp đồng bị hủy vì quá 24 giờ chưa thanh toán, lịch đã được nhả.', c.id)
        stats['unpaid_cancelled'] += 1

    due = Contract.query.filter(Contract.status.in_(FUNDED_STATUSES), Contract.auto_release_at.isnot(None)).all()
    for c in due:
        if _has_active_dispute(c):
            continue   # đang khiếu nại: tiền bị đóng băng, không tự giải ngân
        remaining = (c.auto_release_at - now).total_seconds() / 3600.0
        if remaining <= 0:
            try:
                complete_contract(c)
            except payments.PaymentError:
                continue
            notify(c.hirer_id, 'CONTRACT_RELEASED', 'Tiền đã tự giải ngân',
                   'Quá hạn nghiệm thu nên sàn đã giải ngân cho phiên dịch viên.', c.id)
            notify(c.translator_id, 'CONTRACT_RELEASED', 'Bạn đã nhận tiền',
                   'Khách không phản hồi đúng hạn nên tiền hợp đồng đã được giải ngân vào ví của bạn.', c.id)
            stats['auto_released'] += 1
        elif remaining <= refunds.REMINDER_HOURS and c.release_reminded_at is None:
            c.release_reminded_at = now
            notify(c.hirer_id, 'CONTRACT_REMINDER', 'Sắp hết hạn nghiệm thu',
                   'Còn dưới 24 giờ để nghiệm thu hoặc yêu cầu sửa. Quá hạn tiền sẽ tự giải ngân.', c.id)
            stats['reminded'] += 1
    return stats


# ─── Dữ liệu cho giao diện ────────────────────────────────────────────────────

POLICY_LABELS = {'document': 'Dịch tài liệu', 'event': 'Phiên dịch sự kiện', 'conference': 'Hội nghị nhiều ngày, dịch cabin'}


def panel_context(contract, now=None):
    """Những gì giao diện cần để hiện nút và mức hoàn tiền dự kiến cho từng bên."""
    from disputes import active_dispute
    now = _now(now)
    payments.ensure_pricing_snapshot(contract)
    funded = contract.status in FUNDED_STATUSES
    percent, reason = (None, '')
    if funded:
        percent, reason = hirer_cancel_percent(contract, now)
    deadline = contract.job.deadline if contract.job is not None else None
    late = False
    if funded and contract.delivered_at is None and deadline is not None:
        late = now >= datetime.combine(deadline, datetime.min.time()) + timedelta(days=1, hours=refunds.LATE_GRACE_HOURS)
    frozen = active_dispute(contract.id) if funded else None
    return {
        'funded': funded,
        'policy_label': POLICY_LABELS.get(contract.refund_policy, ''),
        'is_document': contract.refund_policy == 'document',
        'cancel_percent': percent,
        'cancel_reason': reason,
        'cancel_refund_amount': (contract.agreed_price * percent // 100) if percent is not None else None,
        'can_start': funded and contract.started_at is None and contract.refund_policy == 'document' and not frozen,
        'revisions_left': max(refunds.FREE_REVISIONS - (contract.revisions_used or 0), 0),
        'can_late_cancel': late and not frozen,
        'frozen': frozen,
    }
