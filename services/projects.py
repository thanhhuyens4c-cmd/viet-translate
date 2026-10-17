"""Quản lý dự án (Contract) phía khách thuê: trạng thái hiển thị, chuyển trạng thái, lịch sử.

Dùng lại mô hình Contract / Deliverable / Message / PaymentTransaction / Review.
Backend là nơi duy nhất quyết định chuyển trạng thái; frontend chỉ gọi hành động.

Máy trạng thái (Contract.status):
    awaiting_translator ─(PDV xác nhận)→ escrow_pending ─(thanh toán Escrow)→ in_progress
    in_progress ─(khách nghiệm thu, cần ≥1 tệp bàn giao)→ completed
    in_progress ─(khách yêu cầu chỉnh sửa, cần ≥1 tệp bàn giao)→ revision_requested
    revision_requested ─(PDV bàn giao lại)→ in_progress
    cancelled (do hệ thống/admin)
"Chờ nghiệm thu" là trạng thái hiển thị: in_progress đã có tệp bàn giao.
"""
import logging
from datetime import date, datetime

from models import db, Contract, ContractEvent, Deliverable, Message, PaymentTransaction, TranslatorProfile, Proposal

logger = logging.getLogger(__name__)

# key hiển thị -> nhãn
DISPLAY_STATUS = {
    'awaiting_translator': 'Chờ phiên dịch viên xác nhận',
    'pending_payment': 'Đã xác nhận · chờ thanh toán',
    'in_progress': 'Đang thực hiện',
    'awaiting_acceptance': 'Chờ nghiệm thu',
    'revision_requested': 'Yêu cầu chỉnh sửa',
    'completed': 'Hoàn thành',
    'cancelled': 'Đã hủy',
}
STAGES = ['Xác nhận', 'Thanh toán Escrow', 'Thực hiện', 'Bàn giao', 'Nghiệm thu']
REVISION_NOTE_MIN, REVISION_NOTE_MAX = 10, 2000

EVENT_LABELS = {
    'created': 'Hợp đồng được tạo',
    'paid': 'Khách thanh toán vào Escrow',
    'delivered': 'Phiên dịch viên bàn giao tệp',
    'revision_requested': 'Khách yêu cầu chỉnh sửa',
    'redelivered': 'Phiên dịch viên bàn giao lại sau chỉnh sửa',
    'completed': 'Khách xác nhận hoàn thành',
}


class ProjectError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def display_status(contract, deliverable_count=None):
    n = len(contract.deliverables) if deliverable_count is None else deliverable_count
    s = contract.status
    if s == 'escrow_pending':
        key = 'pending_payment'
    elif s == 'in_progress' and n > 0:
        key = 'awaiting_acceptance'
    elif s in DISPLAY_STATUS:
        key = s
    elif s in ('active', 'escrow_held'):
        key = 'in_progress'
    else:
        key = s
    return key, DISPLAY_STATUS.get(key, s or '')


def stage_index(contract, deliverable_count=None):
    """Chỉ số giai đoạn hiện tại (0..4; 5 = xong tất cả). Dựa trên trạng thái thật, không phải % ước lượng."""
    key, _ = display_status(contract, deliverable_count)
    return {'awaiting_translator': 0, 'pending_payment': 1, 'in_progress': 2, 'revision_requested': 2,
            'awaiting_acceptance': 3, 'completed': 5, 'cancelled': -1}.get(key, 0)


def project_title(c):
    if c.job:
        return c.job.title
    if c.service:
        return c.service.name
    if getattr(c, 'interpreter_service', None):
        isvc = c.interpreter_service
        spec = f" - {isvc.specialization}" if isvc.specialization else ""
        return f"Phiên dịch {isvc.source_lang} → {isvc.target_lang} ({isvc.interpreting_type}){spec}"
    return f'Hợp đồng #{c.id}'


def language_pair(c):
    if c.job and (c.job.source_lang or c.job.target_lang):
        return ' → '.join(x for x in (c.job.source_lang, c.job.target_lang) if x)
    if c.service and c.service.languages:
        return c.service.languages
    if getattr(c, 'interpreter_service', None):
        return f"{c.interpreter_service.source_lang} → {c.interpreter_service.target_lang}"
    return ''


def project_deadline(c):
    """Deadline thật: ngày hạn của yêu cầu, nếu không có thì ngày lịch của hợp đồng."""
    if c.job and c.job.deadline:
        return c.job.deadline
    raw = (c.scheduled_date or '').strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def log_event(contract_id, actor_id, event_type, note=None):
    db.session.add(ContractEvent(contract_id=contract_id, actor_id=actor_id, event_type=event_type, note=note))


def build_timeline(c):
    """Lịch sử xử lý: sự kiện đã lưu + mốc suy ra từ dữ liệu thật (tạo hợp đồng, tệp bàn giao)."""
    items = []
    stored_types = set()
    for e in ContractEvent.query.filter_by(contract_id=c.id).order_by(ContractEvent.created_at.asc(), ContractEvent.id.asc()).all():
        stored_types.add(e.event_type)
        items.append({'at': e.created_at, 'label': EVENT_LABELS.get(e.event_type, e.event_type), 'note': e.note or '',
                      'actor': e.actor.name if getattr(e, 'actor', None) else ''})
    if 'created' not in stored_types and c.created_at:
        items.append({'at': c.created_at, 'label': EVENT_LABELS['created'], 'note': '', 'actor': ''})
    for d in c.deliverables:
        items.append({'at': d.created_at, 'label': 'Tệp bàn giao: ' + d.filename, 'note': '', 'actor': c.translator.name if c.translator else ''})
    items.sort(key=lambda x: x['at'] or datetime.min)
    for i in items:
        i['at_str'] = i['at'].strftime('%d/%m/%Y %H:%M') if i['at'] else ''
    return items


def _get_owned(contract_id, hirer_id):
    c = db.session.get(Contract, contract_id)
    if not c or c.hirer_id != hirer_id:
        raise ProjectError('Không tìm thấy dự án.', 404)
    return c


def _notify(user_id, ntype, title, message, contract):
    try:
        from app import create_notification
        create_notification(user_id=user_id, notification_type=ntype, title=title, message=message,
                            url=f'/transaction/{contract.id}', related_contract_id=contract.id)
    except Exception:
        logger.exception('notify failed')


def accept_delivery(contract_id, hirer_id):
    """Khách xác nhận hoàn thành. in_progress + có tệp bàn giao → completed (nguyên tử)."""
    c = _get_owned(contract_id, hirer_id)
    if c.status != 'in_progress':
        raise ProjectError('Dự án không ở trạng thái cho phép nghiệm thu.', 409)
    if Deliverable.query.filter_by(contract_id=c.id).count() == 0:
        raise ProjectError('Phiên dịch viên chưa bàn giao tệp nào để nghiệm thu.', 409)
    claimed = (Contract.query.filter(Contract.id == c.id, Contract.status == 'in_progress')
               .update({'status': 'completed', 'updated_at': datetime.utcnow()}, synchronize_session=False))
    if claimed != 1:
        db.session.rollback()
        raise ProjectError('Dự án vừa được xử lý bởi thao tác khác.', 409)
    try:
        for pay in PaymentTransaction.query.filter_by(contract_id=c.id, status='escrow_pending').all():
            pay.status = 'completed'
        c = db.session.get(Contract, contract_id)
        if c.job:
            c.job.status = 'completed'
        prof = TranslatorProfile.query.filter_by(user_id=c.translator_id).first()
        if prof:
            prof.total_jobs = (prof.total_jobs or 0) + 1
        log_event(c.id, hirer_id, 'completed')
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('accept_delivery failed')
        raise ProjectError('Đã xảy ra lỗi hệ thống. Vui lòng thử lại.', 500)
    _notify(c.translator_id, 'PROJECT_COMPLETED', 'Dự án được nghiệm thu',
            f'Khách hàng đã xác nhận hoàn thành "{project_title(c)}".', c)
    db.session.commit()
    return c


def request_revision(contract_id, hirer_id, note):
    """Khách yêu cầu chỉnh sửa. in_progress + có tệp bàn giao → revision_requested (nguyên tử)."""
    c = _get_owned(contract_id, hirer_id)
    note = (note or '').strip()
    if len(note) < REVISION_NOTE_MIN:
        raise ProjectError(f'Vui lòng mô tả vấn đề cần chỉnh sửa (tối thiểu {REVISION_NOTE_MIN} ký tự).', 400)
    if len(note) > REVISION_NOTE_MAX:
        raise ProjectError(f'Mô tả quá dài (tối đa {REVISION_NOTE_MAX} ký tự).', 400)
    if c.status != 'in_progress':
        raise ProjectError('Dự án không ở trạng thái cho phép yêu cầu chỉnh sửa.', 409)
    if Deliverable.query.filter_by(contract_id=c.id).count() == 0:
        raise ProjectError('Phiên dịch viên chưa bàn giao tệp nào.', 409)
    claimed = (Contract.query.filter(Contract.id == c.id, Contract.status == 'in_progress')
               .update({'status': 'revision_requested', 'updated_at': datetime.utcnow()}, synchronize_session=False))
    if claimed != 1:
        db.session.rollback()
        raise ProjectError('Dự án vừa được xử lý bởi thao tác khác.', 409)
    try:
        log_event(c.id, hirer_id, 'revision_requested', note)
        db.session.add(Message(contract_id=c.id, sender_id=hirer_id, content='🔄 Yêu cầu chỉnh sửa: ' + note))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('request_revision failed')
        raise ProjectError('Đã xảy ra lỗi hệ thống. Vui lòng thử lại.', 500)
    _notify(c.translator_id, 'REVISION_REQUESTED', 'Khách yêu cầu chỉnh sửa',
            f'Khách hàng yêu cầu chỉnh sửa bản bàn giao của "{project_title(c)}".', c)
    db.session.commit()
    return c


def record_delivery(contract, actor_id):
    """Gọi khi phiên dịch viên tải tệp bàn giao (trong cùng transaction với lưu Deliverable)."""
    if contract.status == 'revision_requested':
        contract.status = 'in_progress'
        log_event(contract.id, actor_id, 'redelivered')
    else:
        log_event(contract.id, actor_id, 'delivered')
