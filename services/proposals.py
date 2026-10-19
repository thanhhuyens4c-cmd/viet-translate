"""Quản lý báo giá (Proposal) phía khách thuê: dựng dữ liệu hiển thị, chấp nhận, từ chối.

Dùng lại mô hình sẵn có: Job -> Proposal -> Contract (qua services.booking.create_contract_booking).
Chỉ dữ liệu thật được hiển thị; không có điểm xếp hạng tự tính.
"""
import logging
from datetime import date, datetime

from models import db, Job, Proposal, Contract, TranslatorProfile

logger = logging.getLogger(__name__)

PROPOSAL_STATUS_LABELS = {
    'pending': 'Đang chờ',
    'accepted': 'Đã chấp nhận',
    'rejected': 'Đã từ chối',
    'not_selected': 'Không được chọn',
    'expired': 'Hết hạn',
}

NOTE_MAX = 500


class ProposalError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def is_expired(p, today=None):
    today = today or date.today()
    return p.status == 'pending' and bool(getattr(p, 'valid_until', None)) and p.valid_until < today


def effective_status(p):
    return 'expired' if is_expired(p) else (p.status or 'pending')


def job_accepts_selection(job):
    """Yêu cầu còn cho phép tuyển chọn: đã duyệt, không bị gắn cờ, đang mở và chưa đóng."""
    is_closed = (getattr(job, 'status', '') == 'closed') or (getattr(job, 'closed_at', None) is not None)
    return (getattr(job, 'status', '') == 'open' and not getattr(job, 'is_flagged', False)
            and not is_closed
            and getattr(job, 'moderation_status', None) == 'approved')



def build_proposal_views(job):
    """Danh sách báo giá của một yêu cầu, mới nhất trước, kèm dữ liệu so sánh có thật."""
    proposals = sorted(job.proposals, key=lambda p: (p.created_at or datetime.min), reverse=True)
    selectable = job_accepts_selection(job)
    prices = [p.price for p in proposals if p.price and effective_status(p) in ('pending', 'accepted')]
    lowest = min(prices) if prices else None
    views = []
    for p in proposals:
        t = p.translator
        prof = t.profile if t else None
        status = effective_status(p)
        reviews = (prof.total_reviews or 0) if prof else 0
        views.append({
            'id': p.id,
            'translator_id': t.id if t else None,
            'translator_name': t.name if t else '(đã xóa)',
            'avatar_url': t.avatar_url if t else None,
            'initial': (t.name[0].upper() if t and t.name else '?'),
            'title': (prof.title or '') if prof else '',
            'profile_id': prof.id if prof else None,
            'is_verified': bool(prof and prof.is_verified),
            'rating': float(prof.rating or 0) if prof and reviews else None,
            'total_reviews': reviews,
            'total_jobs': (prof.total_jobs or 0) if prof else 0,
            'response_time': (prof.response_time or '') if prof else '',
            'price': p.price,
            'is_lowest_price': bool(lowest is not None and p.price == lowest and status in ('pending', 'accepted')
                                    and len(prices) > 1),
            'time_estimate': p.time_estimate or '',
            'scope': p.scope or '',
            'delivery_terms': p.delivery_terms or '',
            'revision_terms': p.revision_terms or '',
            'note': p.cover_letter or '',
            'valid_until': p.valid_until.strftime('%d/%m/%Y') if p.valid_until else '',
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else '',
            'status': status,
            'status_label': PROPOSAL_STATUS_LABELS.get(status, status),
            'response_note': p.response_note or '',
            'can_accept': bool(selectable and status == 'pending' and t is not None and t.is_active),
            'can_reject': bool(job.status in ('open', 'closed') and status in ('pending', 'expired') and p.status == 'pending'),
        })
    return views


def _notify(user_id, ntype, title, message, job, proposal):
    try:
        from app import create_notification
        create_notification(user_id=user_id, notification_type=ntype, title=title, message=message,
                            url=f'/job/{job.id}', related_job_id=job.id, related_proposal_id=proposal.id)
    except Exception:  # thông báo không được làm hỏng nghiệp vụ chính
        logger.exception('notify failed')


def accept_proposal_for_hirer(proposal_id, hirer_id):
    """Chấp nhận một báo giá và tạo hợp đồng. Trả về Contract hoặc ném ProposalError.

    An toàn khi đồng thời: (1) UPDATE có điều kiện status='pending' là bước "giành" báo giá,
    (2) create_contract_booking khóa job, kiểm tra còn 'open' và Contract.job_id là UNIQUE,
    cả hai chạy trong cùng một transaction nên lỗi sẽ rollback toàn bộ.
    """
    from services.booking import create_contract_booking, BookingConflictError, BookingValidationError
    from services.schedule import ScheduleCheckError

    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        raise ProposalError('Không tìm thấy báo giá.', 404)
    job = db.session.get(Job, proposal.job_id)
    if not job or job.hirer_id != hirer_id:
        raise ProposalError('Bạn không có quyền với yêu cầu này.', 403)
    if not job_accepts_selection(job):
        raise ProposalError('Yêu cầu này không còn ở trạng thái cho phép tuyển chọn.', 409)
    if proposal.status != 'pending':
        raise ProposalError('Báo giá này đã được xử lý.', 409)
    if is_expired(proposal):
        raise ProposalError('Báo giá đã hết hạn hiệu lực.', 409)
    if Contract.query.filter_by(job_id=job.id).first():
        raise ProposalError('Yêu cầu này đã có hợp đồng.', 409)

    translator_id, price, job_id = proposal.translator_id, proposal.price, job.id
    claimed = (Proposal.query.filter(Proposal.id == proposal_id, Proposal.status == 'pending')
               .update({'status': 'accepted'}, synchronize_session=False))
    if claimed != 1:
        db.session.rollback()
        raise ProposalError('Báo giá này vừa được xử lý bởi thao tác khác.', 409)

    try:
        contract = create_contract_booking(
            hirer_id=hirer_id, translator_id=translator_id, agreed_price=price,
            scheduled_date=job.event_date, start_time=job.event_time_start, end_time=job.event_time_end,
            location=job.event_location, job_id=job_id, proposal_id=proposal_id)
    except (BookingConflictError, BookingValidationError, ScheduleCheckError) as e:
        db.session.rollback()
        raise ProposalError(str(e), 409)
    except Exception:
        db.session.rollback()
        logger.exception('accept proposal failed')
        raise ProposalError('Đã xảy ra lỗi hệ thống. Vui lòng thử lại.', 500)

    # Đã có hợp đồng (escrow_pending, CHƯA thanh toán). Đóng các báo giá còn lại.
    try:
        job = db.session.get(Job, job_id)
        now = datetime.utcnow()
        accepted = db.session.get(Proposal, proposal_id)
        accepted.responded_at = now
        others = Proposal.query.filter(Proposal.job_id == job_id, Proposal.id != proposal_id,
                                       Proposal.status == 'pending').all()
        for o in others:
            o.status = 'not_selected'
            o.responded_at = now
        db.session.commit()
        _notify(translator_id, 'PROPOSAL_ACCEPTED', 'Báo giá được chấp nhận',
                f'Báo giá của bạn cho "{job.title}" đã được khách hàng chấp nhận.', job, accepted)
        for o in others:
            _notify(o.translator_id, 'PROPOSAL_CLOSED', 'Yêu cầu đã chọn phiên dịch viên khác',
                    f'Yêu cầu "{job.title}" đã chọn một phiên dịch viên khác.', job, o)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('post-accept cleanup failed')
    return contract


def reject_proposal_for_hirer(proposal_id, hirer_id, note=''):
    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        raise ProposalError('Không tìm thấy báo giá.', 404)
    job = db.session.get(Job, proposal.job_id)
    if not job or job.hirer_id != hirer_id:
        raise ProposalError('Bạn không có quyền với yêu cầu này.', 403)
    if job.status not in ('open', 'closed'):
        raise ProposalError('Yêu cầu này không còn cho phép xử lý báo giá.', 409)
    note = (note or '').strip()[:NOTE_MAX]
    changed = (Proposal.query.filter(Proposal.id == proposal_id, Proposal.status == 'pending')
               .update({'status': 'rejected', 'responded_at': datetime.utcnow(), 'response_note': note or None},
                       synchronize_session=False))
    if changed != 1:
        db.session.rollback()
        raise ProposalError('Báo giá này đã được xử lý.', 409)
    db.session.commit()
    _notify(proposal.translator_id, 'PROPOSAL_REJECTED', 'Báo giá bị từ chối',
            f'Báo giá của bạn cho "{job.title}" đã bị từ chối.', job, proposal)
    db.session.commit()
    return proposal
