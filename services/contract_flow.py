"""Xác nhận / từ chối / hủy hợp đồng và chính sách hoàn tiền."""
import logging
from datetime import datetime, timedelta

from models import Contract, PaymentTransaction, Job, Proposal
from services.schedule import normalize_schedule_datetime

logger = logging.getLogger(__name__)

PAYMENT_WINDOW_HOURS = 2  # thời gian khách thanh toán sau khi PDV xác nhận


class ContractFlowError(Exception):
    pass


def _notify(user_id, ntype, title, message, contract_id):
    from app import create_notification
    try:
        create_notification(
            user_id=user_id, notification_type=ntype, title=title, message=message,
            url=f'/transaction/{contract_id}', related_contract_id=contract_id,
        )
    except Exception:
        logger.exception('notify failed')


def _release_job(contract):
    """Mở lại job/đề xuất khi hợp đồng bị hủy để khách tiếp tục tìm người."""
    if contract.job_id:
        job = Job.query.get(contract.job_id)
        if job and job.status == 'contracted':
            job.status = 'open'
        if contract.proposal_id:
            prop = Proposal.query.get(contract.proposal_id)
            if prop:
                prop.status = 'rejected'


def accept_booking(contract, user_id):
    from app import db
    from services.scheduling import _release_expired_schedules
    _release_expired_schedules()
    if contract.translator_id != user_id:
        raise ContractFlowError('Bạn không có quyền xác nhận hợp đồng này.')
    if contract.status != 'awaiting_translator':
        raise ContractFlowError('Hợp đồng này không còn chờ xác nhận (có thể đã hết hạn hoặc bị hủy).')
    contract.status = 'escrow_pending'
    sched = contract.schedule
    if sched and sched.status == 'reserved':
        sched.expires_at = datetime.utcnow() + timedelta(hours=PAYMENT_WINDOW_HOURS)
    _notify(contract.hirer_id, 'CONTRACT_ACCEPTED', 'Phiên dịch viên đã xác nhận',
            f'{contract.translator.name} đã nhận lịch. Vui lòng thanh toán trong {PAYMENT_WINDOW_HOURS} giờ để giữ chỗ.',
            contract.id)
    db.session.commit()


def decline_booking(contract, user_id):
    from app import db
    from services.scheduling import cancel_slot
    if contract.translator_id != user_id:
        raise ContractFlowError('Bạn không có quyền từ chối hợp đồng này.')
    if contract.status != 'awaiting_translator':
        raise ContractFlowError('Hợp đồng này không còn chờ xác nhận.')
    contract.status = 'cancelled'
    cancel_slot(contract.id)
    _notify(contract.hirer_id, 'CONTRACT_DECLINED', 'Phiên dịch viên không thể nhận lịch',
            f'{contract.translator.name} chưa thể nhận lịch này. Bạn có thể chọn phiên dịch viên khác.',
            contract.id)
    db.session.commit()


def refund_percent(contract, cancelled_by_hirer, now=None):
    """Hirer hủy: >=48h trước giờ hẹn hoàn 100%, 24-48h hoàn 50%, <24h không hoàn.
    Phiên dịch viên hủy: luôn hoàn 100%."""
    if not cancelled_by_hirer:
        return 100
    now = now or datetime.utcnow()
    try:
        d, start, _ = normalize_schedule_datetime(
            contract.scheduled_date, contract.scheduled_time_start, contract.scheduled_time_end)
    except Exception:
        d = start = None
    if not d or not start:
        return 100  # không rõ giờ hẹn: ưu tiên bảo vệ khách
    hours = (datetime.combine(d, start) - now).total_seconds() / 3600
    if hours >= 48:
        return 100
    if hours >= 24:
        return 50
    return 0


def cancel_contract(contract, user_id):
    """Hủy hợp đồng. Trả về phần trăm hoàn tiền (0 nếu chưa thanh toán)."""
    from app import db
    from services.scheduling import cancel_slot
    if user_id not in (contract.hirer_id, contract.translator_id):
        raise ContractFlowError('Bạn không có quyền hủy hợp đồng này.')
    if contract.status not in ('awaiting_translator', 'escrow_pending', 'in_progress'):
        raise ContractFlowError('Hợp đồng ở trạng thái này không thể hủy.')
    if contract.deliverables:
        raise ContractFlowError('Phiên dịch viên đã bàn giao tệp, không thể hủy. Hãy liên hệ hỗ trợ nếu có vấn đề.')

    by_hirer = user_id == contract.hirer_id
    pct = 0
    if contract.status in ('in_progress', 'revision_requested'):
        # Tiền đang được sàn giữ: chia theo điều khoản (mục 5 đến 7) và ghi vào sổ giao dịch.
        from services import lifecycle
        try:
            if by_hirer:
                kind, _ = lifecycle.cancel_by_hirer(contract, user_id)
                if kind == 'dispute':
                    raise ContractFlowError('Phiên dịch viên đang làm việc nên sàn cần phân xử mức hoàn. Vui lòng gửi khiếu nại.')
                pct = lifecycle.hirer_cancel_percent_applied(contract)
            else:
                lifecycle.cancel_by_translator(contract)
                pct = 100
        except lifecycle.LifecycleError as e:
            raise ContractFlowError(str(e))
        other_id = contract.translator_id if by_hirer else contract.hirer_id
        who = contract.hirer.name if by_hirer else contract.translator.name
        msg = f'{who} đã hủy hợp đồng #{contract.id}.'
        if by_hirer and pct:
            msg += f' Hoàn tiền cho khách: {pct}%.'
        _notify(other_id, 'CONTRACT_CANCELLED', 'Hợp đồng đã bị hủy', msg, contract.id)
        db.session.commit()
        return pct

    contract.status = 'cancelled'
    cancel_slot(contract.id)
    _release_job(contract)

    other_id = contract.translator_id if by_hirer else contract.hirer_id
    who = contract.hirer.name if by_hirer else contract.translator.name
    msg = f'{who} đã hủy hợp đồng #{contract.id}.'
    if by_hirer and pct:
        msg += f' Hoàn tiền cho khách: {pct}%.'
    _notify(other_id, 'CONTRACT_CANCELLED', 'Hợp đồng đã bị hủy', msg, contract.id)
    db.session.commit()
    return pct
