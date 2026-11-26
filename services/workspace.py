"""Phòng làm việc: tiến độ, yêu cầu cập nhật, chấm công phiên dịch trực tiếp, dòng sự kiện cho khung chat.

Không thay thế vòng đời tiền. Mọi chuyển trạng thái liên quan đến tiền (thanh toán, nghiệm thu,
sửa bài, hủy, tranh chấp, tự giải ngân) vẫn do services/lifecycle.py, services/projects.py,
services/contract_flow.py và disputes.py đảm nhiệm. Module này chỉ bổ sung:

  * Dịch tài liệu: PDV cập nhật % tiến độ; khách yêu cầu cập nhật (chặn gửi lặp khi PDV chưa trả lời).
  * Phiên dịch trực tiếp: check-in (mở sớm nhất 2 giờ trước giờ hẹn, kèm định vị nếu có), check-out,
    khách xác nhận có mặt từng ca, PDV gửi biên bản (tổng giờ). Gửi biên bản ghi mốc `delivered_at`
    qua lifecycle.register_delivery nên khách nghiệm thu bằng đúng luồng projects.accept_delivery.

Các hàm KHÔNG tự commit; route gọi chịu trách nhiệm commit/rollback.
"""
from datetime import datetime, timedelta

from models import db, AttendanceSession, Contract, ContractEvent, Deliverable, Message, WorkspaceState

CHECKIN_EARLY_HOURS = 2
VN_OFFSET = timedelta(hours=7)
FUNDED = ('in_progress', 'revision_requested')

# Nhãn sự kiện mới (bổ sung cho services.projects.EVENT_LABELS): (icon, tone, vi, en)
EVENT_META = {
    'created': ('📝', 'slate', 'Hợp đồng được tạo', 'Contract created'),
    'paid': ('🔒', 'emerald', 'Khách đã thanh toán vào Escrow', 'Client paid into escrow'),
    'started': ('🚀', 'brand', 'Phiên dịch viên bắt đầu làm việc', 'Interpreter started work'),
    'delivered': ('📦', 'cyan', 'Phiên dịch viên bàn giao tệp — chờ nghiệm thu', 'Files delivered — awaiting approval'),
    'redelivered': ('📦', 'cyan', 'Bàn giao lại sau chỉnh sửa — chờ nghiệm thu', 'Re-delivered after revision'),
    'revision_requested': ('✏️', 'orange', 'Khách yêu cầu chỉnh sửa', 'Client requested revisions'),
    'completed': ('🎉', 'emerald', 'Khách nghiệm thu — tiền đã giải ngân', 'Approved — payment released'),
    'progress': ('📈', 'brand', 'Cập nhật tiến độ', 'Progress update'),
    'progress_requested': ('🔔', 'amber', 'Khách yêu cầu cập nhật tiến độ', 'Client asked for an update'),
    'checkin': ('📍', 'brand', 'Phiên dịch viên check-in có mặt', 'Interpreter checked in'),
    'checkout': ('🏁', 'brand', 'Phiên dịch viên check-out kết thúc ca', 'Interpreter checked out'),
    'attendance_confirmed': ('✅', 'emerald', 'Khách xác nhận phiên dịch viên có mặt', 'Client confirmed attendance'),
    'onsite_report': ('📋', 'cyan', 'Phiên dịch viên gửi biên bản nghiệm thu', 'Sign-off report submitted'),
}


class WorkspaceError(Exception):
    pass


# ─── Tiện ích ─────────────────────────────────────────────────────────────────

def now_utc():
    return datetime.utcnow()


def to_local(dt):
    return dt + VN_OFFSET if dt else None


def iso_utc(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else None


def is_document(contract):
    if contract.refund_policy:
        return contract.refund_policy == 'document'
    if contract.job is not None:
        return contract.job.display_category_group == 'translation'
    cat = ((contract.service.category if contract.service else '') or '').lower()
    return 'dịch viết' in cat or 'tài liệu' in cat


_TABLES_READY = False


def ensure_tables():
    """Tạo 2 bảng của phòng làm việc nếu chưa có, độc lập với db.create_all() lúc khởi động.
    Trên production, create_all() nằm trong try/except rộng: nếu nó lỗi giữa chừng thì bảng mới
    không được tạo và mọi trang /transaction/<id> lỗi 500. Kết quả thành công được nhớ theo tiến trình."""
    global _TABLES_READY
    if _TABLES_READY:
        return True
    try:
        for table in (WorkspaceState.__table__, AttendanceSession.__table__):
            table.create(bind=db.engine, checkfirst=True)
        _TABLES_READY = True
    except Exception as e:  # thiếu quyền CREATE, mất kết nối...: trang vẫn hiển thị ở chế độ rút gọn
        import logging
        logging.error('[workspace] Không tạo được bảng workspace_state/attendance_session: %s', e)
    return _TABLES_READY


def _require_ready():
    _require(ensure_tables(), 'Phòng làm việc đang được cập nhật hệ thống, vui lòng thử lại sau ít phút.')


def sessions_of(contract):
    """Danh sách ca làm; rỗng nếu bảng chấm công chưa sẵn sàng (không làm hỏng trang)."""
    if not ensure_tables():
        return []
    return list(contract.attendance_sessions)


def view_state(contract):
    """Trạng thái để HIỂN THỊ. Không ghi được DB thì trả về đối tượng tạm (không lưu)."""
    if ensure_tables():
        try:
            return get_state(contract)
        except Exception:
            db.session.rollback()
    return WorkspaceState(contract_id=contract.id, progress_percent=0)


def get_state(contract):
    _require_ready()
    st = contract.workspace_state
    if st is None:
        st = WorkspaceState(contract_id=contract.id)
        db.session.add(st)
        contract.workspace_state = st
        db.session.flush()
    return st


def _event(contract, actor_id, event_type, note=None):
    ev = ContractEvent(contract_id=contract.id, actor_id=actor_id, event_type=event_type, note=note or None)
    db.session.add(ev)
    return ev


def _notify(contract, user_id, title, message, ntype='CONTRACT_UPDATE'):
    try:
        from app import create_notification
        create_notification(user_id=user_id, notification_type=ntype, title=title, message=message,
                            url=f'/transaction/{contract.id}', related_contract_id=contract.id)
    except Exception:
        pass


def _require(cond, msg):
    if not cond:
        raise WorkspaceError(msg)


def _frozen(contract):
    from disputes import active_dispute
    return active_dispute(contract.id) is not None


def open_session(contract):
    return next((s for s in sessions_of(contract) if s.checkout_at is None), None)


def total_hours(contract):
    return round(sum(s.hours or 0 for s in sessions_of(contract)), 2)


def checkin_opens_at_local(contract):
    """Giờ (VN) bắt đầu cho phép check-in, None nếu hợp đồng không có giờ hẹn."""
    from services import lifecycle
    start = lifecycle.event_start(contract)
    return to_local(start) - timedelta(hours=CHECKIN_EARLY_HOURS) if start else None


def awaiting_acceptance(contract):
    """PDV đã bàn giao (tệp hoặc biên bản) và hợp đồng đang chờ khách nghiệm thu."""
    if contract.status != 'in_progress':
        return False
    if is_document(contract):
        return bool(contract.deliverables)
    return contract.delivered_at is not None


def heal_legacy_status(contract):
    """Sửa hợp đồng kẹt ở trạng thái 'delivered' (API báo kết thúc ca cũ) về luồng tiền chuẩn.
    'delivered' không thuộc FUNDED_STATUSES nên trước đây không nghiệm thu, hủy hay tự giải ngân được."""
    if contract.status == 'delivered':
        contract.status = 'in_progress'
        if contract.delivered_at is None:
            contract.delivered_at = contract.updated_at or now_utc()
        return True
    return False


# ─── Tiến độ ──────────────────────────────────────────────────────────────────

def post_progress(contract, user_id, percent=None, note=None):
    _require(user_id == contract.translator_id, 'Chỉ phiên dịch viên mới cập nhật tiến độ.')
    _require(contract.status in FUNDED, 'Chỉ cập nhật tiến độ khi hợp đồng đang thực hiện.')
    note = (note or '').strip()
    _require(len(note) >= 5, 'Vui lòng mô tả ngắn công việc đã làm.')
    st = get_state(contract)
    label = note
    if is_document(contract):
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            raise WorkspaceError('Phần trăm tiến độ không hợp lệ.')
        _require(0 <= percent <= 95, 'Tiến độ từ 0–95%. Hoàn tất bằng cách bàn giao tệp để khách nghiệm thu.')
        st.progress_percent = percent
        label = f'{percent}% — {note}'
    if contract.started_at is None:
        contract.started_at = now_utc()
    st.last_progress_at = now_utc()
    st.progress_requested_at = None
    _event(contract, user_id, 'progress', label[:2000])
    _notify(contract, contract.hirer_id, 'Cập nhật tiến độ mới',
            f'{contract.translator.name} vừa cập nhật tiến độ công việc.')


def request_progress(contract, user_id, note=None):
    _require(user_id == contract.hirer_id, 'Chỉ khách hàng mới yêu cầu cập nhật tiến độ.')
    _require(contract.status in FUNDED, 'Chỉ yêu cầu khi hợp đồng đang thực hiện.')
    st = get_state(contract)
    _require(st.progress_requested_at is None, 'Bạn đã gửi yêu cầu, vui lòng chờ phiên dịch viên phản hồi.')
    st.progress_requested_at = now_utc()
    _event(contract, user_id, 'progress_requested', (note or '').strip()[:1000] or None)
    _notify(contract, contract.translator_id, 'Khách hàng yêu cầu cập nhật tiến độ',
            f'{contract.hirer.name} muốn biết tình hình công việc. Vui lòng cập nhật sớm.')


# ─── Phiên dịch trực tiếp: chấm công ──────────────────────────────────────────

def _float(v):
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def checkin(contract, user_id, lat=None, lng=None, note=None, now=None):
    now = now or now_utc()
    _require_ready()
    _require(user_id == contract.translator_id, 'Chỉ phiên dịch viên phụ trách mới check-in được.')
    _require(contract.status in FUNDED, 'Chỉ check-in khi khách đã thanh toán và hợp đồng đang thực hiện.')
    _require(not is_document(contract), 'Check-in chỉ áp dụng cho phiên dịch trực tiếp.')
    _require(not _frozen(contract), 'Hợp đồng đang có khiếu nại, tạm dừng chấm công.')
    _require(contract.delivered_at is None, 'Bạn đã gửi biên bản nghiệm thu, không thể mở thêm ca.')
    _require(open_session(contract) is None, 'Bạn đang có một ca chưa check-out.')
    opens = checkin_opens_at_local(contract)
    if opens is not None:
        _require(to_local(now) >= opens,
                 f'Chỉ được check-in từ {opens.strftime("%H:%M %d/%m/%Y")} '
                 f'(sớm nhất {CHECKIN_EARLY_HOURS} giờ trước giờ hẹn).')
    s = AttendanceSession(contract_id=contract.id, checkin_at=now, checkin_lat=_float(lat), checkin_lng=_float(lng),
                          checkin_note=(note or '').strip()[:500] or None)
    db.session.add(s)
    if contract.started_at is None:
        contract.started_at = now
    st = get_state(contract)
    st.last_progress_at = now
    st.progress_requested_at = None
    located = ' (có định vị)' if s.checkin_lat is not None and s.checkin_lng is not None else ''
    _event(contract, user_id, 'checkin',
           (f'Lúc {to_local(now).strftime("%H:%M %d/%m")}{located}. ' + (s.checkin_note or '')).strip())
    _notify(contract, contract.hirer_id, 'Phiên dịch viên đã có mặt',
            f'{contract.translator.name} vừa check-in tại địa điểm. Vui lòng xác nhận có mặt.')
    return s


def checkout(contract, user_id, note=None, now=None):
    now = now or now_utc()
    _require_ready()
    _require(user_id == contract.translator_id, 'Chỉ phiên dịch viên phụ trách mới check-out được.')
    s = open_session(contract)
    _require(s is not None, 'Chưa có ca nào đang mở để check-out.')
    s.checkout_at = now
    s.checkout_note = (note or '').strip()[:500] or None
    get_state(contract).last_progress_at = now
    _event(contract, user_id, 'checkout',
           (f'Ca làm {s.hours} giờ. ' + (s.checkout_note or '')).strip())
    return s


def confirm_attendance(contract, user_id, session_id):
    _require_ready()
    _require(user_id == contract.hirer_id, 'Chỉ khách hàng mới xác nhận có mặt.')
    s = AttendanceSession.query.filter_by(id=session_id, contract_id=contract.id).first()
    _require(s is not None, 'Không tìm thấy ca làm việc.')
    _require(s.confirmed_at is None, 'Ca này đã được xác nhận.')
    s.confirmed_at = now_utc()
    _event(contract, user_id, 'attendance_confirmed', f'Ca check-in lúc {to_local(s.checkin_at).strftime("%H:%M %d/%m")}')


def submit_onsite_report(contract, user_id, note, confirm=False):
    """PDV gửi biên bản. Hợp đồng vẫn ở in_progress (đang giữ tiền) nhưng có delivered_at → chờ nghiệm thu."""
    from services import lifecycle
    _require(user_id == contract.translator_id, 'Chỉ phiên dịch viên phụ trách mới gửi biên bản.')
    _require(contract.status == 'in_progress', 'Hợp đồng không ở trạng thái cho phép gửi biên bản.')
    _require(not is_document(contract), 'Dịch tài liệu nghiệm thu bằng tệp bàn giao.')
    _require(not _frozen(contract), 'Hợp đồng đang có khiếu nại, chưa thể gửi biên bản.')
    _require(contract.delivered_at is None, 'Biên bản đã được gửi.')
    _require(confirm, 'Vui lòng xác nhận cam kết trước khi gửi biên bản.')
    _require(sessions_of(contract), 'Chưa có ca làm việc nào. Hãy check-in/check-out trước khi gửi biên bản.')
    _require(open_session(contract) is None, 'Vui lòng check-out ca đang mở trước khi gửi biên bản.')
    note = (note or '').strip()
    _require(len(note) >= 10, 'Vui lòng tóm tắt nội dung buổi phiên dịch (tối thiểu 10 ký tự).')
    hours = total_hours(contract)
    lifecycle.register_delivery(contract)   # ghi delivered_at; hạn tự giải ngân của sự kiện giữ nguyên
    st = get_state(contract)
    st.report_hours = hours
    st.progress_requested_at = None
    st.last_progress_at = now_utc()
    _event(contract, user_id, 'onsite_report',
           f'{len(sessions_of(contract))} ca · tổng {hours} giờ.\n{note}'[:2000])
    _notify(contract, contract.hirer_id, 'Ca làm đã hoàn tất — chờ bạn nghiệm thu',
            f'{contract.translator.name} đã gửi biên bản ({hours} giờ). Vui lòng kiểm tra và nghiệm thu.',
            ntype='CONTRACT_COMPLETED')


# ─── Hiển thị ─────────────────────────────────────────────────────────────────

def progress_percent(contract):
    if contract.status == 'completed':
        return 100
    if contract.status in ('awaiting_translator', 'escrow_pending', 'cancelled'):
        return 0
    if awaiting_acceptance(contract):
        return 100 if is_document(contract) else 90
    if is_document(contract):
        st = contract.workspace_state if ensure_tables() else None
        base = (st.progress_percent or 0) if st else 0
        return max(base, 5 if contract.started_at else 0)
    if not sessions_of(contract):
        return 10
    return 50 if open_session(contract) else 75


def step_index(contract):
    """0 Xác nhận · 1 Ký quỹ · 2 Thực hiện · 3 Nghiệm thu · 4 Giải ngân · 5 Đánh giá"""
    s = contract.status
    if s == 'awaiting_translator':
        return 0
    if s == 'escrow_pending':
        return 1
    if s in FUNDED:
        return 3 if awaiting_acceptance(contract) else 2
    if s in ('completed', 'reviewed'):
        return 5
    return 0


def event_view(ev, lang='vi'):
    meta = EVENT_META.get(ev.event_type)
    if meta is None:
        from services.projects import EVENT_LABELS
        label = EVENT_LABELS.get(ev.event_type, ev.event_type)
        meta = ('•', 'slate', label, label)
    return {'icon': meta[0], 'tone': meta[1], 'label': meta[2] if lang == 'vi' else meta[3],
            'actor': ev.actor.name if ev.actor else '', 'note': ev.note or ''}


def build_feed(contract, lang='vi'):
    """Gộp tin nhắn + sự kiện hợp đồng + tệp bàn giao theo thời gian (cho khung chat)."""
    items = []
    for m in Message.query.filter_by(contract_id=contract.id).all():
        items.append({'kind': 'message', 'key': f'm{m.id}', 'ts': m.created_at, 'sender_id': m.sender_id,
                      'sender_name': m.sender.name if m.sender else '', 'is_read': bool(m.is_read),
                      'content': '' if (m.content == '[Hình ảnh]' and m.image_url) else (m.content or ''),
                      'image_url': m.image_url or None})
    stored = set()
    for ev in ContractEvent.query.filter_by(contract_id=contract.id).all():
        stored.add(ev.event_type)
        v = event_view(ev, lang)
        v.update({'kind': 'event', 'key': f'e{ev.id}', 'ts': ev.created_at, 'files': []})
        items.append(v)
    if 'created' not in stored and contract.created_at:
        v = {'icon': '📝', 'tone': 'slate', 'label': EVENT_META['created'][2 if lang == 'vi' else 3],
             'actor': '', 'note': '', 'kind': 'event', 'key': 'c0', 'ts': contract.created_at, 'files': []}
        items.append(v)
    for d in Deliverable.query.filter_by(contract_id=contract.id).all():
        items.append({'kind': 'event', 'key': f'd{d.id}', 'ts': d.created_at, 'icon': '📎', 'tone': 'slate',
                      'label': ('Tệp bàn giao' if lang == 'vi' else 'Deliverable'),
                      'actor': contract.translator.name if contract.translator else '', 'note': '',
                      'files': [{'name': d.filename, 'url': f'/deliverable/{d.id}'}]})
    items.sort(key=lambda x: (x['ts'] or datetime.min, x['key']))
    for it in items:
        local = to_local(it['ts'])
        it['time'] = local.strftime('%H:%M') if local else ''
        it['date'] = local.strftime('%d/%m/%Y') if local else ''
        it['ts'] = iso_utc(it['ts'])
    return items
