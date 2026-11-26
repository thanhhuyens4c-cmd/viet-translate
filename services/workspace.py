"""
Phòng làm việc (Workspace) — máy trạng thái cho hợp đồng giữa Khách hàng và Phiên dịch viên.

Quy trình (cả 2 hình thức):
    escrow_pending ──(khách ký quỹ)──▶ funded ──(PDV nhận việc)──▶ in_progress
    in_progress ──(PDV gửi nghiệm thu)──▶ submitted
    submitted ──(khách chấp nhận / quá hạn 72h)──▶ completed  ⇒ GIẢI NGÂN
    submitted ──(khách yêu cầu chỉnh sửa, tối đa 2 lần)──▶ revision ──▶ submitted
    funded ──(PDV từ chối / khách hủy)──▶ cancelled  ⇒ HOÀN TIỀN 100%
    in_progress | revision | submitted ──(khiếu nại)──▶ disputed ──(Admin phân xử)──▶ completed | cancelled

Hình thức:
    document : dịch tài liệu — PDV cập nhật % tiến độ, bàn giao file, khách kiểm tra file.
    onsite   : phiên dịch trực tiếp — PDV check-in/check-out từng ca tại địa điểm, khách xác nhận
               có mặt, PDV gửi biên bản (tổng giờ thực tế) để nghiệm thu.

Tiền chỉ được giải ngân sau khi nghiệm thu được chấp nhận (thủ công hoặc tự động khi quá hạn).
Mọi thời gian lưu ở UTC; hiển thị theo giờ Việt Nam (UTC+7).
"""
import json
import os
import uuid
from datetime import datetime, timedelta

from models import (
    db, User, Contract, ContractWorkflow, ContractEvent, WorkSubmission, AttendanceSession,
    WorkspaceFile, PaymentTransaction, TranslatorProfile, TranslatorSchedule, AdminNotification, Message,
)

PLATFORM_FEE_RATE = 0.10
ACCEPT_HOURS = 24          # PDV phải nhận việc trong 24h sau khi khách ký quỹ
REVIEW_HOURS = 72          # Khách có 72h để nghiệm thu, quá hạn hệ thống tự chấp nhận
MAX_REVISIONS = 2          # Số lần yêu cầu chỉnh sửa tối đa
CHECKIN_EARLY_HOURS = 2    # Được check-in sớm tối đa 2h trước giờ hẹn
VN_OFFSET = timedelta(hours=7)

ACTIVE_STATUSES = ('in_progress', 'revision')
OPEN_STATUSES = ('escrow_pending', 'funded', 'in_progress', 'revision', 'submitted', 'disputed')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'zip', 'rar',
                      'png', 'jpg', 'jpeg', 'webp', 'srt', 'odt'}


class WorkflowError(Exception):
    """Thao tác không hợp lệ ở trạng thái hiện tại — thông điệp hiển thị trực tiếp cho người dùng."""


# ─── NHÃN HIỂN THỊ ─────────────────────────────────────────────────────────────

STATUS_META = {
    'escrow_pending': {'vi': 'Chờ ký quỹ', 'en': 'Awaiting escrow', 'tone': 'amber'},
    'funded': {'vi': 'Chờ nhận việc', 'en': 'Awaiting acceptance', 'tone': 'violet'},
    'in_progress': {'vi': 'Đang thực hiện', 'en': 'In progress', 'tone': 'brand'},
    'revision': {'vi': 'Đang chỉnh sửa', 'en': 'Revising', 'tone': 'orange'},
    'submitted': {'vi': 'Chờ nghiệm thu', 'en': 'Awaiting approval', 'tone': 'cyan'},
    'completed': {'vi': 'Đã nghiệm thu · Đã giải ngân', 'en': 'Approved · Paid out', 'tone': 'emerald'},
    'disputed': {'vi': 'Đang tranh chấp', 'en': 'In dispute', 'tone': 'rose'},
    'cancelled': {'vi': 'Đã hủy', 'en': 'Cancelled', 'tone': 'slate'},
}

MODE_META = {
    'document': {'vi': 'Dịch tài liệu', 'en': 'Document translation', 'icon': '📄'},
    'onsite': {'vi': 'Phiên dịch trực tiếp', 'en': 'On-site interpreting', 'icon': '🎙️'},
}

# type -> (icon, tone, vi, en). Chuỗi có thể chứa {placeholder} lấy từ event.data
EVENT_META = {
    'created': ('📝', 'slate', 'Hợp đồng #{code} được tạo', 'Contract #{code} created'),
    'funded': ('🔒', 'emerald', 'Khách hàng đã ký quỹ {amount} VND vào Escrow', 'Client deposited {amount} VND into escrow'),
    'accepted': ('🤝', 'brand', '{actor} đã nhận việc — bắt đầu thực hiện', '{actor} accepted the job — work started'),
    'declined': ('↩️', 'rose', '{actor} từ chối nhận việc', '{actor} declined the job'),
    'cancelled': ('⛔', 'rose', '{actor} đã hủy hợp đồng', '{actor} cancelled the contract'),
    'refunded': ('💸', 'slate', 'Đã hoàn {amount} VND về cho khách hàng', '{amount} VND refunded to the client'),
    'progress': ('📈', 'brand', 'Cập nhật tiến độ: {percent}%', 'Progress update: {percent}%'),
    'progress_note': ('📈', 'brand', 'Cập nhật tình hình công việc', 'Work status update'),
    'progress_requested': ('🔔', 'amber', '{actor} yêu cầu cập nhật tiến độ', '{actor} requested a progress update'),
    'checkin': ('📍', 'brand', '{actor} đã check-in có mặt tại địa điểm', '{actor} checked in on site'),
    'checkout': ('🏁', 'brand', '{actor} đã check-out — ca làm {hours} giờ', '{actor} checked out — {hours} h session'),
    'attendance_confirmed': ('✅', 'emerald', '{actor} xác nhận phiên dịch viên có mặt', '{actor} confirmed the interpreter is present'),
    'reference_uploaded': ('📎', 'slate', '{actor} đã thêm tài liệu tham khảo', '{actor} added reference material'),
    'submitted': ('📦', 'cyan', '{actor} đã gửi nghiệm thu (lần {round})', '{actor} submitted for approval (round {round})'),
    'revision_requested': ('✏️', 'orange', '{actor} yêu cầu chỉnh sửa (lần {n}/{max})', '{actor} requested revisions ({n}/{max})'),
    'approved': ('🎉', 'emerald', '{actor} đã chấp nhận nghiệm thu', '{actor} approved the work'),
    'auto_approved': ('⏱️', 'emerald', 'Hệ thống tự động nghiệm thu do quá hạn {hours}h', 'Auto-approved after the {hours}h review window'),
    'released': ('💰', 'emerald', 'Đã giải ngân {amount} VND cho phiên dịch viên', '{amount} VND released to the interpreter'),
    'disputed': ('⚠️', 'rose', '{actor} đã mở khiếu nại', '{actor} opened a dispute'),
    'dispute_resolved': ('⚖️', 'slate', 'Ban quản trị đã phân xử: {outcome}', 'Admin resolved the dispute: {outcome}'),
}


def lang_text(vi, en, lang):
    return vi if lang == 'vi' else en


def status_label(status, lang='vi'):
    meta = STATUS_META.get(status)
    return meta[lang if lang in ('vi', 'en') else 'vi'] if meta else status


def fmt_vnd(value):
    try:
        return '{:,.0f}'.format(float(value or 0))
    except (TypeError, ValueError):
        return str(value)


def to_local(dt):
    return dt + VN_OFFSET if dt else None


def now_utc():
    return datetime.utcnow()


def iso_utc(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else None


def contract_code(contract):
    return f'HD{contract.id:06d}'


# ─── TRUY CẬP & KHỞI TẠO ───────────────────────────────────────────────────────

def role_of(user_id, contract):
    if user_id == contract.hirer_id:
        return 'hirer'
    if user_id == contract.translator_id:
        return 'translator'
    return None


def detect_work_mode(contract):
    job = contract.job
    if job is not None:
        return 'document' if job.display_category_group == 'translation' else 'onsite'
    service = contract.service
    if service is not None:
        cat = (service.category or '').lower()
        return 'document' if ('dịch viết' in cat or 'tài liệu' in cat or 'translation' in cat) else 'onsite'
    return 'onsite' if contract.location else 'document'


def get_workflow(contract):
    """Lấy (hoặc tạo) ContractWorkflow. Hợp đồng cũ được ánh xạ về trạng thái tương đương."""
    wf = contract.workflow
    if wf is not None:
        return wf
    wf = ContractWorkflow(contract_id=contract.id, work_mode=detect_work_mode(contract))
    if contract.status not in ('escrow_pending',):
        # Hợp đồng cũ đã thanh toán trước khi có quy trình mới
        wf.funded_at = contract.created_at
        wf.accepted_at = contract.created_at if contract.status != 'funded' else None
    if contract.status == 'completed':
        wf.completed_at = contract.updated_at or contract.created_at
        wf.released_at = wf.completed_at
    db.session.add(wf)
    contract.workflow = wf
    db.session.flush()
    return wf


def log_event(contract, type_, actor_id=None, note=None, **data):
    ev = ContractEvent(contract_id=contract.id, actor_id=actor_id, type=type_,
                       note=(note or None), data=json.dumps(data, ensure_ascii=False) if data else None)
    db.session.add(ev)
    db.session.flush()
    return ev


def _notify(contract, user_id, title, message, ntype='CONTRACT_UPDATE'):
    """Gửi thông báo trong ứng dụng cho một bên. Lỗi thông báo không làm hỏng giao dịch."""
    try:
        from app import create_notification
        from services.notifications import should_notify
        user = User.query.get(user_id)
        if not user or not should_notify(user, ntype):
            return
        # Đường dẫn tĩnh (không dùng url_for) để chạy được cả ngoài request: cron, admin script
        create_notification(user_id=user_id, notification_type=ntype, title=title, message=message,
                            url=f'/workspace/{contract.id}', related_contract_id=contract.id)
    except Exception as e:  # pragma: no cover - best effort
        print(f'[workspace notify error] {e}')


def _other_party(contract, user_id):
    return contract.translator_id if user_id == contract.hirer_id else contract.hirer_id


def _require(cond, message):
    if not cond:
        raise WorkflowError(message)


def _require_role(user_id, contract, role):
    _require(role_of(user_id, contract) == role,
             'Chỉ khách hàng mới được thực hiện thao tác này.' if role == 'hirer'
             else 'Chỉ phiên dịch viên mới được thực hiện thao tác này.')


def _require_status(contract, *statuses):
    _require(contract.status in statuses,
             f'Không thể thực hiện ở trạng thái "{status_label(contract.status)}".')


# ─── TIỀN: KÝ QUỸ / GIẢI NGÂN / HOÀN TIỀN ─────────────────────────────────────

def _escrow_txn(contract):
    return (PaymentTransaction.query
            .filter_by(contract_id=contract.id)
            .filter(PaymentTransaction.status.in_(['escrow_pending', 'completed']))
            .order_by(PaymentTransaction.created_at.asc())
            .first())


def fee_breakdown(contract):
    fee = int(round(contract.agreed_price * PLATFORM_FEE_RATE))
    return {'total': contract.agreed_price, 'fee': fee, 'payout': contract.agreed_price - fee,
            'fee_rate': int(PLATFORM_FEE_RATE * 100)}


def mark_funded(contract, payer_id, method='mockup'):
    """Khách hàng đã thanh toán ký quỹ thành công. Gọi sau confirm_slot()."""
    _require_role(payer_id, contract, 'hirer')
    _require_status(contract, 'escrow_pending')
    wf = get_workflow(contract)
    now = now_utc()
    contract.status = 'funded'
    wf.funded_at = now
    wf.accept_deadline = now + timedelta(hours=ACCEPT_HOURS)
    db.session.add(PaymentTransaction(
        contract_id=contract.id, user_id=payer_id, amount=contract.agreed_price,
        status='escrow_pending', payment_method=method,
        transaction_ref=f'ESC-{contract_code(contract)}-{now.strftime("%y%m%d%H%M%S")}'))
    log_event(contract, 'funded', payer_id, amount=fmt_vnd(contract.agreed_price))
    _notify(contract, contract.translator_id, 'Bạn có việc mới cần xác nhận',
            f'Khách hàng đã ký quỹ {fmt_vnd(contract.agreed_price)} VND. Vui lòng nhận việc trong {ACCEPT_HOURS} giờ.',
            ntype='CONTRACT_CREATED')


def _release_funds(contract, wf):
    now = now_utc()
    b = fee_breakdown(contract)
    txn = _escrow_txn(contract)
    if txn is None:  # hợp đồng cũ chưa có bản ghi ký quỹ
        txn = PaymentTransaction(contract_id=contract.id, user_id=contract.hirer_id, amount=contract.agreed_price,
                                 payment_method='escrow')
        db.session.add(txn)
    txn.status = 'completed'
    txn.transaction_ref = f'REL-{contract_code(contract)}-{now.strftime("%y%m%d%H%M%S")}'
    wf.released_at = now
    wf.payout_amount = b['payout']
    wf.platform_fee = b['fee']
    contract.status = 'completed'
    if contract.job:
        contract.job.status = 'completed'
    sched = TranslatorSchedule.query.filter_by(contract_id=contract.id).first()
    if sched and sched.status in ('reserved', 'active'):
        sched.status = 'completed'
    prof = TranslatorProfile.query.filter_by(user_id=contract.translator_id).first()
    if prof:
        prof.total_jobs = (prof.total_jobs or 0) + 1
    log_event(contract, 'released', None, amount=fmt_vnd(b['payout']))
    _notify(contract, contract.translator_id, 'Đã giải ngân thù lao',
            f'{fmt_vnd(b["payout"])} VND (sau phí nền tảng {b["fee_rate"]}%) đã được giải ngân cho bạn.', ntype='PAYMENT')


def _refund_funds(contract, wf):
    now = now_utc()
    txn = _escrow_txn(contract)
    if txn is not None:
        txn.status = 'refunded'
    if wf.funded_at:
        wf.refunded_at = now
        log_event(contract, 'refunded', None, amount=fmt_vnd(contract.agreed_price))
    contract.status = 'cancelled'
    wf.cancelled_at = now
    sched = TranslatorSchedule.query.filter_by(contract_id=contract.id).first()
    if sched and sched.status in ('reserved', 'active'):
        sched.status = 'cancelled'
    if contract.job and contract.job.status not in ('completed',):
        contract.job.status = 'cancelled'


# ─── HÀNH ĐỘNG CỦA PHIÊN DỊCH VIÊN ─────────────────────────────────────────────

def accept_job(contract, user_id, note=None):
    _require_role(user_id, contract, 'translator')
    _require_status(contract, 'funded')
    wf = get_workflow(contract)
    wf.accepted_at = now_utc()
    contract.status = 'in_progress'
    if wf.work_mode == 'document':
        wf.progress_percent = max(wf.progress_percent or 0, 5)
        wf.last_progress_at = wf.accepted_at
    log_event(contract, 'accepted', user_id, note=note)
    _notify(contract, contract.hirer_id, 'Phiên dịch viên đã nhận việc',
            f'{contract.translator.name} đã xác nhận nhận việc và bắt đầu thực hiện.')


def decline_job(contract, user_id, reason):
    _require_role(user_id, contract, 'translator')
    _require_status(contract, 'funded')
    _require(reason and reason.strip(), 'Vui lòng nêu lý do từ chối.')
    wf = get_workflow(contract)
    wf.cancel_reason = reason.strip()
    log_event(contract, 'declined', user_id, note=reason.strip())
    _refund_funds(contract, wf)
    _notify(contract, contract.hirer_id, 'Phiên dịch viên từ chối nhận việc',
            f'{contract.translator.name} không thể nhận việc. Tiền ký quỹ đã được hoàn 100%.')


def post_progress(contract, user_id, percent=None, note=None):
    _require_role(user_id, contract, 'translator')
    _require_status(contract, *ACTIVE_STATUSES)
    wf = get_workflow(contract)
    note = (note or '').strip()
    if wf.work_mode == 'document':
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            raise WorkflowError('Phần trăm tiến độ không hợp lệ.')
        _require(0 <= percent <= 95, 'Tiến độ từ 0–95%. Để hoàn tất, hãy dùng "Gửi nghiệm thu".')
        _require(note, 'Vui lòng mô tả ngắn công việc đã làm.')
        wf.progress_percent = percent
        ev = log_event(contract, 'progress', user_id, note=note, percent=percent)
    else:
        _require(note, 'Vui lòng nhập nội dung cập nhật.')
        ev = log_event(contract, 'progress_note', user_id, note=note)
    wf.last_progress_at = now_utc()
    wf.progress_requested_at = None
    _notify(contract, contract.hirer_id, 'Cập nhật tiến độ mới',
            f'{contract.translator.name} vừa cập nhật tiến độ công việc.')
    return ev


def checkin(contract, user_id, lat=None, lng=None, note=None):
    _require_role(user_id, contract, 'translator')
    _require_status(contract, *ACTIVE_STATUSES)
    wf = get_workflow(contract)
    _require(wf.work_mode == 'onsite', 'Check-in chỉ áp dụng cho phiên dịch trực tiếp.')
    _require(open_session(contract) is None, 'Bạn đang có một ca chưa check-out.')
    start = scheduled_start_local(contract)
    if start is not None:
        earliest = start - timedelta(hours=CHECKIN_EARLY_HOURS)
        _require(to_local(now_utc()) >= earliest,
                 f'Chỉ được check-in từ {earliest.strftime("%H:%M %d/%m/%Y")} (sớm nhất {CHECKIN_EARLY_HOURS} giờ trước giờ hẹn).')
    s = AttendanceSession(contract_id=contract.id, checkin_at=now_utc(), checkin_note=(note or '').strip()[:500] or None,
                          checkin_lat=_float_or_none(lat), checkin_lng=_float_or_none(lng))
    db.session.add(s)
    wf.last_progress_at = s.checkin_at
    wf.progress_requested_at = None
    log_event(contract, 'checkin', user_id, note=s.checkin_note,
              located=bool(s.checkin_lat is not None and s.checkin_lng is not None))
    _notify(contract, contract.hirer_id, 'Phiên dịch viên đã có mặt',
            f'{contract.translator.name} vừa check-in tại địa điểm. Vui lòng xác nhận có mặt.')


def checkout(contract, user_id, note=None):
    _require_role(user_id, contract, 'translator')
    _require_status(contract, *ACTIVE_STATUSES)
    s = open_session(contract)
    _require(s is not None, 'Chưa có ca nào đang mở để check-out.')
    s.checkout_at = now_utc()
    s.checkout_note = (note or '').strip()[:500] or None
    get_workflow(contract).last_progress_at = s.checkout_at
    log_event(contract, 'checkout', user_id, note=s.checkout_note, hours=s.hours)


def submit_work(contract, user_id, note, files=None, confirm=False):
    """PDV gửi nghiệm thu. files: list FileStorage đã lọc rỗng."""
    _require_role(user_id, contract, 'translator')
    _require_status(contract, *ACTIVE_STATUSES)
    _require(confirm, 'Vui lòng xác nhận cam kết trước khi gửi nghiệm thu.')
    wf = get_workflow(contract)
    files = [f for f in (files or []) if f and f.filename]
    note = (note or '').strip()
    hours = None
    if wf.work_mode == 'document':
        _require(files, 'Vui lòng đính kèm ít nhất 1 tệp bàn giao.')
    else:
        sessions = contract.attendance_sessions
        _require(sessions, 'Chưa có ca làm việc nào được check-in. Hãy check-in/check-out trước khi gửi biên bản.')
        _require(open_session(contract) is None, 'Vui lòng check-out ca đang mở trước khi gửi biên bản.')
        hours = round(sum(s.hours or 0 for s in sessions), 2)
        _require(note, 'Vui lòng tóm tắt nội dung buổi phiên dịch trong biên bản.')
    round_no = len(contract.submissions) + 1
    sub = WorkSubmission(contract_id=contract.id, round_no=round_no, note=note or None, actual_hours=hours)
    db.session.add(sub)
    db.session.flush()
    for f in files:
        save_upload(f, contract, user_id, 'deliverable' if wf.work_mode == 'document' else 'evidence',
                    submission_id=sub.id)
    now = now_utc()
    contract.status = 'submitted'
    wf.submitted_at = now
    wf.review_deadline = now + timedelta(hours=REVIEW_HOURS)
    wf.progress_requested_at = None
    wf.last_progress_at = now
    if wf.work_mode == 'document':
        wf.progress_percent = 100
    log_event(contract, 'submitted', user_id, note=note or None, round=round_no, submission_id=sub.id,
              hours=hours, files=len(files))
    _notify(contract, contract.hirer_id, 'Có kết quả cần nghiệm thu',
            f'{contract.translator.name} đã gửi nghiệm thu. Bạn có {REVIEW_HOURS} giờ để kiểm tra.')
    return sub


# ─── HÀNH ĐỘNG CỦA KHÁCH HÀNG ──────────────────────────────────────────────────

def cancel_contract(contract, user_id, reason):
    _require_role(user_id, contract, 'hirer')
    _require_status(contract, 'escrow_pending', 'funded')
    _require(reason and reason.strip(), 'Vui lòng nêu lý do hủy.')
    wf = get_workflow(contract)
    wf.cancel_reason = reason.strip()
    log_event(contract, 'cancelled', user_id, note=reason.strip())
    _refund_funds(contract, wf)
    _notify(contract, contract.translator_id, 'Khách hàng đã hủy hợp đồng',
            f'Hợp đồng {contract_code(contract)} đã bị hủy trước khi bắt đầu.')


def request_progress(contract, user_id, note=None):
    _require_role(user_id, contract, 'hirer')
    _require_status(contract, *ACTIVE_STATUSES)
    wf = get_workflow(contract)
    _require(wf.progress_requested_at is None,
             'Bạn đã gửi yêu cầu, vui lòng chờ phiên dịch viên phản hồi.')
    wf.progress_requested_at = now_utc()
    log_event(contract, 'progress_requested', user_id, note=(note or '').strip() or None)
    _notify(contract, contract.translator_id, 'Khách hàng yêu cầu cập nhật tiến độ',
            f'{contract.hirer.name} muốn biết tình hình công việc. Vui lòng cập nhật sớm.')


def confirm_attendance(contract, user_id, session_id):
    _require_role(user_id, contract, 'hirer')
    _require(contract.status in ACTIVE_STATUSES + ('submitted',), 'Không thể xác nhận ở trạng thái hiện tại.')
    s = AttendanceSession.query.filter_by(id=session_id, contract_id=contract.id).first()
    _require(s is not None, 'Không tìm thấy ca làm việc.')
    _require(s.confirmed_at is None, 'Ca này đã được xác nhận.')
    s.confirmed_at = now_utc()
    log_event(contract, 'attendance_confirmed', user_id, session_id=s.id)


def approve_work(contract, user_id, confirm=False, auto=False):
    if not auto:
        _require_role(user_id, contract, 'hirer')
        _require(confirm, 'Vui lòng xác nhận đã kiểm tra kết quả trước khi nghiệm thu.')
    _require_status(contract, 'submitted')
    wf = get_workflow(contract)
    now = now_utc()
    sub = latest_submission(contract)
    if sub:
        sub.status = 'auto_accepted' if auto else 'accepted'
        sub.reviewed_at = now
    wf.completed_at = now
    wf.auto_approved = bool(auto)
    if auto:
        log_event(contract, 'auto_approved', None, hours=REVIEW_HOURS)
    else:
        log_event(contract, 'approved', user_id)
    _release_funds(contract, wf)
    _notify(contract, contract.hirer_id, 'Hợp đồng đã hoàn tất',
            'Nghiệm thu thành công. Hãy để lại đánh giá cho phiên dịch viên.', ntype='CONTRACT_COMPLETED')


def request_revision(contract, user_id, feedback):
    _require_role(user_id, contract, 'hirer')
    _require_status(contract, 'submitted')
    wf = get_workflow(contract)
    _require(wf.revision_count < MAX_REVISIONS,
             f'Đã hết {MAX_REVISIONS} lượt yêu cầu chỉnh sửa. Vui lòng nghiệm thu hoặc mở khiếu nại.')
    feedback = (feedback or '').strip()
    _require(len(feedback) >= 10, 'Vui lòng mô tả cụ thể nội dung cần chỉnh sửa (tối thiểu 10 ký tự).')
    wf.revision_count += 1
    sub = latest_submission(contract)
    if sub:
        sub.status = 'revision_requested'
        sub.feedback = feedback
        sub.reviewed_at = now_utc()
    contract.status = 'revision'
    wf.review_deadline = None
    if wf.work_mode == 'document':
        wf.progress_percent = 90
    log_event(contract, 'revision_requested', user_id, note=feedback, n=wf.revision_count, max=MAX_REVISIONS)
    _notify(contract, contract.translator_id, 'Khách hàng yêu cầu chỉnh sửa',
            f'Lần {wf.revision_count}/{MAX_REVISIONS}: {feedback[:120]}')


# ─── TRANH CHẤP ────────────────────────────────────────────────────────────────

def open_dispute(contract, user_id, reason):
    _require(role_of(user_id, contract) is not None, 'Không có quyền.')
    _require_status(contract, 'in_progress', 'revision', 'submitted')
    reason = (reason or '').strip()
    _require(len(reason) >= 20, 'Vui lòng mô tả chi tiết vấn đề (tối thiểu 20 ký tự).')
    wf = get_workflow(contract)
    wf.dispute_prev_status = contract.status
    wf.disputed_at = now_utc()
    wf.dispute_by = user_id
    wf.dispute_reason = reason
    wf.review_deadline = None  # tạm dừng tự động nghiệm thu
    sub = latest_submission(contract)
    if sub and sub.status == 'pending':
        sub.status = 'disputed'
    contract.status = 'disputed'
    log_event(contract, 'disputed', user_id, note=reason)
    db.session.add(AdminNotification(
        type='CONTRACT_DISPUTE', title=f'Khiếu nại hợp đồng {contract_code(contract)}',
        message=reason[:500], url=f'/admin/contracts?status=disputed', related_id=contract.id))
    _notify(contract, _other_party(contract, user_id), 'Hợp đồng đang bị khiếu nại',
            'Tiền ký quỹ được giữ nguyên cho đến khi Ban quản trị phân xử.')


def resolve_dispute(contract, outcome, admin_note=None):
    """Admin phân xử. outcome: 'release' (trả PDV) | 'refund' (hoàn khách)."""
    _require_status(contract, 'disputed')
    wf = get_workflow(contract)
    label = {'release': 'giải ngân cho phiên dịch viên', 'refund': 'hoàn tiền cho khách hàng'}.get(outcome)
    _require(label, 'Kết quả phân xử không hợp lệ.')
    log_event(contract, 'dispute_resolved', None, note=(admin_note or '').strip() or None, outcome=label)
    if outcome == 'release':
        wf.completed_at = now_utc()
        _release_funds(contract, wf)
    else:
        wf.cancel_reason = f'Phân xử tranh chấp: {admin_note or "hoàn tiền"}'
        _refund_funds(contract, wf)
    for uid in (contract.hirer_id, contract.translator_id):
        _notify(contract, uid, 'Tranh chấp đã được phân xử', f'Kết quả: {label}.')


# ─── TỰ ĐỘNG NGHIỆM THU ────────────────────────────────────────────────────────

def maybe_auto_approve(contract):
    """Nếu khách không phản hồi quá REVIEW_HOURS → tự nghiệm thu & giải ngân. Trả về True nếu đã chạy."""
    if contract.status != 'submitted':
        return False
    wf = contract.workflow
    if not wf or not wf.review_deadline or wf.review_deadline > now_utc():
        return False
    approve_work(contract, None, auto=True)
    return True


def run_auto_approvals():
    count = 0
    rows = (Contract.query.join(ContractWorkflow, ContractWorkflow.contract_id == Contract.id)
            .filter(Contract.status == 'submitted', ContractWorkflow.review_deadline <= now_utc()).all())
    for c in rows:
        if maybe_auto_approve(c):
            count += 1
    return count


# ─── TỆP ───────────────────────────────────────────────────────────────────────

def _float_or_none(v):
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def save_upload(file, contract, uploader_id, category, message_id=None, event_id=None, submission_id=None):
    from flask import current_app
    original = os.path.basename((file.filename or '').replace('\\', '/')).strip()[:200]
    _require(original and '.' in original, 'Tên tệp không hợp lệ.')
    ext = original.rsplit('.', 1)[1].lower()
    _require(ext in ALLOWED_EXTENSIONS, f'Định dạng .{ext} không được hỗ trợ.')
    stored = f'ws{contract.id}_{uuid.uuid4().hex}.{ext}'
    folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, stored)
    file.save(path)
    wf = WorkspaceFile(contract_id=contract.id, uploader_id=uploader_id, category=category,
                       original_name=original, stored_name=stored, size=os.path.getsize(path),
                       message_id=message_id, event_id=event_id, submission_id=submission_id)
    db.session.add(wf)
    db.session.flush()
    return wf


def upload_reference(contract, user_id, files, note=None):
    _require(role_of(user_id, contract) is not None, 'Không có quyền.')
    _require(contract.status in OPEN_STATUSES, 'Hợp đồng đã đóng, không thể tải thêm tài liệu.')
    files = [f for f in (files or []) if f and f.filename]
    _require(files, 'Vui lòng chọn tệp.')
    ev = log_event(contract, 'reference_uploaded', user_id, note=(note or '').strip() or None, files=len(files))
    for f in files:
        save_upload(f, contract, user_id, 'reference', event_id=ev.id)
    return ev


def chat_attachment(contract, user_id, file, caption=None):
    _require(role_of(user_id, contract) is not None, 'Không có quyền.')
    _require(contract.status != 'cancelled', 'Hợp đồng đã hủy.')
    _require(file and file.filename, 'Vui lòng chọn tệp.')
    name = os.path.basename(file.filename.replace('\\', '/'))[:200]
    caption = (caption or '').strip()
    msg = Message(contract_id=contract.id, sender_id=user_id,
                  content=f'{caption}\n📎 {name}' if caption else f'📎 {name}')
    db.session.add(msg)
    db.session.flush()
    save_upload(file, contract, user_id, 'chat', message_id=msg.id)
    return msg


def file_url(f):
    from flask import url_for
    return url_for('workspace_file', contract_id=f.contract_id, file_id=f.id)


def file_dict(f):
    size = f.size or 0
    human = f'{size / 1048576:.1f} MB' if size >= 1048576 else f'{max(1, round(size / 1024))} KB'
    return {'id': f.id, 'name': f.original_name, 'size': human, 'url': file_url(f),
            'ext': f.original_name.rsplit('.', 1)[-1].lower() if '.' in f.original_name else ''}


# ─── TRUY VẤN HIỂN THỊ ─────────────────────────────────────────────────────────

def open_session(contract):
    for s in contract.attendance_sessions:
        if s.checkout_at is None:
            return s
    return None


def latest_submission(contract):
    subs = contract.submissions
    return subs[-1] if subs else None


def scheduled_start_local(contract):
    """Giờ bắt đầu theo lịch (giờ VN, naive). None nếu không xác định."""
    raw = (contract.scheduled_date or '').split(' to ')[0].strip()
    if not raw:
        return None
    try:
        d = datetime.strptime(raw, '%Y-%m-%d')
    except ValueError:
        return None
    t = (contract.scheduled_time_start or '').strip()
    if t:
        try:
            tt = datetime.strptime(t[:5], '%H:%M')
            d = d.replace(hour=tt.hour, minute=tt.minute)
        except ValueError:
            pass
    return d


def progress_percent(contract, wf):
    if contract.status == 'completed':
        return 100
    if contract.status == 'submitted':
        return 100 if wf.work_mode == 'document' else 90
    if contract.status in ('escrow_pending', 'funded', 'cancelled'):
        return 0
    if wf.work_mode == 'document':
        return wf.progress_percent or 0
    sessions = contract.attendance_sessions
    if not sessions:
        return 15
    if open_session(contract):
        return 50
    return 75


def step_index(contract, wf):
    """0 Ký quỹ · 1 Nhận việc · 2 Thực hiện · 3 Nghiệm thu · 4 Giải ngân · 5 Đánh giá"""
    status = contract.status
    if status == 'disputed':
        status = wf.dispute_prev_status or 'in_progress'
    return {'escrow_pending': 0, 'funded': 1, 'in_progress': 2, 'revision': 2,
            'submitted': 3, 'completed': 5}.get(status, 0)


def event_view(ev, lang='vi'):
    meta = EVENT_META.get(ev.type, ('•', 'slate', ev.type, ev.type))
    data = ev.get_data()
    data.setdefault('actor', ev.actor.name if ev.actor else ('Hệ thống' if lang == 'vi' else 'System'))
    data.setdefault('code', contract_code(ev.contract) if ev.contract else '')
    template = meta[2] if lang == 'vi' else meta[3]
    try:
        label = template.format(**data)
    except (KeyError, IndexError, ValueError):
        label = template
    return {'icon': meta[0], 'tone': meta[1], 'label': label, 'note': ev.note, 'type': ev.type}


def build_feed(contract, lang='vi'):
    """Gộp tin nhắn chat + sự kiện hệ thống theo thời gian."""
    files_by_msg, files_by_event, files_by_sub = {}, {}, {}
    for f in contract.workspace_files:
        if f.message_id:
            files_by_msg.setdefault(f.message_id, []).append(file_dict(f))
        elif f.event_id:
            files_by_event.setdefault(f.event_id, []).append(file_dict(f))
        elif f.submission_id:
            files_by_sub.setdefault(f.submission_id, []).append(file_dict(f))

    items = []
    for m in Message.query.filter_by(contract_id=contract.id).all():
        attached = files_by_msg.get(m.id, [])
        content = m.content
        if attached:  # ẩn dòng "📎 tên tệp" vì đã hiển thị dạng thẻ tệp
            content = '\n'.join(line for line in content.split('\n') if not line.startswith('📎 ')).strip()
        items.append({'kind': 'message', 'key': f'm{m.id}', 'ts': m.created_at,
                      'sender_id': m.sender_id, 'sender_name': m.sender.name if m.sender else '',
                      'content': content, 'files': attached, 'is_read': m.is_read})
    for ev in contract.events:
        v = event_view(ev, lang)
        sub_id = ev.get_data().get('submission_id')
        v.update({'kind': 'event', 'key': f'e{ev.id}', 'ts': ev.created_at, 'actor_id': ev.actor_id,
                  'files': files_by_event.get(ev.id, []) + (files_by_sub.get(sub_id, []) if sub_id else [])})
        items.append(v)
    items.sort(key=lambda x: (x['ts'] or datetime.min, x['key']))
    for it in items:
        local = to_local(it['ts'])
        it['time'] = local.strftime('%H:%M') if local else ''
        it['date'] = local.strftime('%d/%m/%Y') if local else ''
        it['ts'] = iso_utc(it['ts'])
    return items
