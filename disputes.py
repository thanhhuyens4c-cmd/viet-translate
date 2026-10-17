"""Khiếu nại đơn thuê: khách gửi -> admin duyệt -> PDV kháng đơn (24h) -> admin kết luận.

Toàn bộ trạng thái và số tiền do backend quyết định; frontend chỉ gửi lựa chọn.
Routes được đăng ký bằng register(app) ở cuối app.py.
"""
import os
import uuid
from datetime import datetime, timedelta

from flask import (abort, flash, g, redirect, render_template, request, send_from_directory,
                   session, url_for)
from werkzeug.utils import secure_filename

from models import (AdminNotification, Contract, ContractEvent, Deliverable, Dispute,
                    DisputeEvidence, PaymentTransaction, db)

RESPONSE_HOURS = 24
MAX_EVIDENCE = 5
# Hợp đồng còn giữ tiền (chưa giải ngân / chưa hủy) thì mới được khiếu nại
DISPUTABLE_STATUSES = ('in_progress', 'escrow_paid', 'delivered', 'revision_requested')

STATUS_LABELS = {
    'pending_review': 'Chờ xác nhận',
    'rejected': 'Đơn khiếu nại bị bác bỏ',
    'awaiting_response': 'Chờ PDV phản hồi',
    'under_review': 'Admin đang xem xét',
    'resolved': 'Đã có kết quả',
}


def active_dispute(contract_id):
    return Dispute.query.filter(
        Dispute.contract_id == contract_id,
        Dispute.status.in_(('pending_review', 'awaiting_response', 'under_review'))).first()


def refresh(d):
    """Quá hạn 24h mà PDV chưa phản hồi -> tự chuyển sang 'under_review'."""
    if d.status == 'awaiting_response' and d.response_deadline and datetime.utcnow() > d.response_deadline:
        d.status = 'under_review'
        db.session.commit()
    return d


def tracker_steps(d):
    """Các mốc tiến trình hiển thị cho cả hai bên: [(nhãn, trạng thái 'done'|'current'|'todo'|'failed', thời gian)]."""
    s = d.status
    steps = [('Gửi đơn', 'done', d.created_at)]
    steps.append(('Chờ xác nhận', 'current' if s == 'pending_review' else 'done', d.created_at))
    if s == 'rejected':
        steps.append(('Đơn khiếu nại bị bác bỏ', 'failed', d.updated_at))
        return steps
    fwd = ('Chuyển bước tiếp theo — PDV phản hồi trong 24h',
           'todo' if s == 'pending_review' else ('current' if s == 'awaiting_response' else 'done'),
           d.forwarded_at)
    steps.append(fwd)
    steps.append(('Admin tổng hợp thông tin hai bên',
                  'todo' if s in ('pending_review', 'awaiting_response') else ('current' if s == 'under_review' else 'done'),
                  None))
    steps.append(('Kết quả', 'done' if s == 'resolved' else 'todo', d.resolved_at))
    return steps


def _notify(user_id, title, message, url):
    from app import create_notification
    try:
        create_notification(user_id=user_id, notification_type='SYSTEM', title=title,
                            message=message, url=url, force=True)
    except Exception:
        pass


def _save_evidence(d, files, uploader_id, side):
    """Lưu tối đa MAX_EVIDENCE tệp bằng chứng. Trả về thông báo lỗi hoặc None."""
    from app import DELIVERABLE_FOLDER, JOB_FILE_MAX_BYTES, _detect_ok, allowed_file
    files = [f for f in files if f and f.filename]
    already = DisputeEvidence.query.filter_by(dispute_id=d.id, side=side).count()
    if already + len(files) > MAX_EVIDENCE:
        return f'Tối đa {MAX_EVIDENCE} tệp bằng chứng cho mỗi bên.'
    folder = os.path.join(DELIVERABLE_FOLDER, 'disputes')
    os.makedirs(folder, exist_ok=True)
    for f in files:
        name = secure_filename(f.filename)
        if not name or not allowed_file(name):
            return f'Loại tệp không được hỗ trợ: {f.filename}'
        ext = name.rsplit('.', 1)[-1].lower()
        f.stream.seek(0, 2)
        size = f.stream.tell()
        f.stream.seek(0)
        if size == 0 or size > JOB_FILE_MAX_BYTES:
            return f'Tệp rỗng hoặc vượt quá 10MB: {name}'
        head = f.stream.read(8)
        f.stream.seek(0)
        if not _detect_ok(ext, head):
            return f'Nội dung tệp không khớp định dạng: {name}'
        stored = f'{uuid.uuid4().hex}.{ext}'
        f.save(os.path.join(folder, stored))
        db.session.add(DisputeEvidence(dispute_id=d.id, uploader_id=uploader_id, side=side,
                                       filename=name, filepath=stored))
    return None


def apply_resolution(d, resolution, note, admin_id):
    """Kết luận khiếu nại và điều chỉnh khoản thanh toán theo kết quả. Chạy trong 1 transaction."""
    c = d.contract
    original = c.agreed_price
    pays = PaymentTransaction.query.filter(
        PaymentTransaction.contract_id == c.id,
        PaymentTransaction.status.in_(('escrow_pending', 'completed'))).all()

    if resolution == 'keep_100':
        final = original
        if c.status in ('in_progress', 'delivered', 'revision_requested'):
            c.status = 'completed'
            for p in pays:
                p.status = 'completed'
    elif resolution == 'refund_50':
        final = original // 2
        c.agreed_price = final
        if c.status in ('in_progress', 'delivered', 'revision_requested'):
            c.status = 'completed'
        for p in pays:
            p.amount = final
            p.status = 'completed'
            p.transaction_ref = f'dispute:{d.id}:50%'
    elif resolution == 'cancel_payment':
        final = 0
        c.status = 'cancelled'
        for p in pays:
            p.status = 'refunded'
            p.transaction_ref = f'dispute:{d.id}:refund'
        if getattr(c, 'schedule', None):
            c.schedule.status = 'cancelled'
    else:
        raise ValueError('resolution')

    d.resolution = resolution
    d.resolution_note = note or None
    d.original_amount = original
    d.final_amount = final
    d.resolved_by = admin_id
    d.resolved_at = datetime.utcnow()
    d.status = 'resolved'
    db.session.add(ContractEvent(contract_id=c.id, actor_id=admin_id, event_type='dispute_resolved',
                                 note=f'Khiếu nại #{d.id}: {Dispute.RESOLUTIONS[resolution]}'))


def money(v):
    return '{:,.0f}'.format(v or 0).replace(',', '.')


# ─── ROUTES ────────────────────────────────────────────────────────────────────

def register(app):
    from app import _csrf_ok, get_current_user, login_required
    from admin_auth import (ADMIN_SESSION_KEY, admin_login_required, csrf_protected,
                            require_permission)
    from admin_auth import audit_log as _audit_log

    def _user():
        u = get_current_user()
        if not u:
            abort(403)
        return u

    def _can_view(d, u):
        if u.id == d.hirer_id:
            return True
        # PDV chỉ thấy khiếu nại sau khi admin đã chuyển bước tiếp theo
        return u.id == d.translator_id and d.forwarded_at is not None

    # --- Người dùng -----------------------------------------------------------

    @app.route('/disputes', endpoint='my_disputes')
    @login_required
    def my_disputes():
        u = _user()
        col = Dispute.hirer_id if u.role == 'hirer' else Dispute.translator_id
        q = Dispute.query.filter(col == u.id)
        if u.role != 'hirer':
            q = q.filter(Dispute.forwarded_at.isnot(None))
        items = q.order_by(Dispute.created_at.desc()).all()
        for d in items:
            refresh(d)
        return render_template('my_disputes.html', items=items, labels=STATUS_LABELS, money=money)

    @app.route('/contract/<int:contract_id>/dispute/new', methods=['GET', 'POST'], endpoint='dispute_new')
    @login_required
    def dispute_new(contract_id):
        u = _user()
        c = Contract.query.get_or_404(contract_id)
        if u.id != c.hirer_id:
            abort(403)
        existing = active_dispute(c.id)
        if existing:
            flash('Hợp đồng này đã có khiếu nại đang xử lý.', 'warning')
            return redirect(url_for('dispute_detail', dispute_id=existing.id))
        if c.status not in DISPUTABLE_STATUSES:
            flash('Chỉ có thể khiếu nại khi tiền thanh toán còn được giữ (chưa giải ngân).', 'warning')
            return redirect(url_for('transaction_detail', contract_id=c.id))

        if request.method == 'POST':
            if not _csrf_ok():
                flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
                return redirect(request.url)
            category = request.form.get('category', '')
            description = request.form.get('description', '').strip()
            if category not in Dispute.CATEGORIES:
                flash('Vui lòng chọn lý do khiếu nại.', 'error')
            elif len(description) < 20:
                flash('Vui lòng mô tả chi tiết (tối thiểu 20 ký tự).', 'error')
            else:
                d = Dispute(contract_id=c.id, hirer_id=c.hirer_id, translator_id=c.translator_id,
                            category=category, description=description[:4000])
                db.session.add(d)
                db.session.flush()
                err = _save_evidence(d, request.files.getlist('evidence'), u.id, 'hirer')
                if err:
                    db.session.rollback()
                    flash(err, 'error')
                else:
                    db.session.add(AdminNotification(
                        type='NEW_DISPUTE', title=f'Khiếu nại đơn thuê mới #{d.id}',
                        message=f'{u.name} khiếu nại hợp đồng #{c.id} ({Dispute.CATEGORIES[category]}).',
                        related_id=d.id, url=url_for('admin_dispute_detail', dispute_id=d.id)))
                    db.session.add(ContractEvent(contract_id=c.id, actor_id=u.id, event_type='dispute_opened',
                                                 note=f'Khiếu nại #{d.id}: {Dispute.CATEGORIES[category]}'))
                    db.session.commit()
                    flash('Đã gửi khiếu nại. Admin sẽ xem xét và cập nhật trạng thái cho bạn.', 'success')
                    return redirect(url_for('dispute_detail', dispute_id=d.id))
        return render_template('dispute_new.html', contract=c, categories=Dispute.CATEGORIES,
                               deliverables=Deliverable.query.filter_by(contract_id=c.id)
                               .order_by(Deliverable.created_at).all(), max_files=MAX_EVIDENCE)

    @app.route('/dispute/<int:dispute_id>', endpoint='dispute_detail')
    @login_required
    def dispute_detail(dispute_id):
        u = _user()
        d = Dispute.query.get_or_404(dispute_id)
        if not _can_view(d, u):
            abort(404)
        refresh(d)
        deliverables = Deliverable.query.filter_by(contract_id=d.contract_id).order_by(Deliverable.created_at).all()
        can_respond = (u.id == d.translator_id and d.status == 'awaiting_response'
                       and d.response_deadline and datetime.utcnow() <= d.response_deadline)
        return render_template('dispute_detail.html', d=d, u=u, steps=tracker_steps(d),
                               labels=STATUS_LABELS, deliverables=deliverables, can_respond=can_respond,
                               categories=Dispute.CATEGORIES, resolutions=Dispute.RESOLUTIONS,
                               money=money, max_files=MAX_EVIDENCE)

    @app.route('/dispute/<int:dispute_id>/respond', methods=['POST'], endpoint='dispute_respond')
    @login_required
    def dispute_respond(dispute_id):
        u = _user()
        d = Dispute.query.get_or_404(dispute_id)
        if u.id != d.translator_id:
            abort(403)
        if not _csrf_ok():
            flash('Phiên làm việc không hợp lệ. Vui lòng thử lại.', 'error')
            return redirect(url_for('dispute_detail', dispute_id=d.id))
        refresh(d)
        if d.status != 'awaiting_response' or not d.response_deadline or datetime.utcnow() > d.response_deadline:
            flash('Đã hết thời hạn 24 giờ hoặc khiếu nại không còn ở bước chờ phản hồi.', 'warning')
            return redirect(url_for('dispute_detail', dispute_id=d.id))
        text = request.form.get('response', '').strip()
        if len(text) < 20:
            flash('Vui lòng nêu lý do / giải trình (tối thiểu 20 ký tự).', 'error')
            return redirect(url_for('dispute_detail', dispute_id=d.id))
        err = _save_evidence(d, request.files.getlist('evidence'), u.id, 'translator')
        if err:
            db.session.rollback()
            flash(err, 'error')
            return redirect(url_for('dispute_detail', dispute_id=d.id))
        d.translator_response = text[:4000]
        d.translator_responded_at = datetime.utcnow()
        d.status = 'under_review'
        db.session.add(AdminNotification(
            type='DISPUTE_RESPONSE', title=f'PDV đã phản hồi khiếu nại #{d.id}',
            message=f'{u.name} đã gửi giải trình cho khiếu nại hợp đồng #{d.contract_id}.',
            related_id=d.id, url=url_for('admin_dispute_detail', dispute_id=d.id)))
        db.session.commit()
        flash('Đã gửi phản hồi tới admin.', 'success')
        return redirect(url_for('dispute_detail', dispute_id=d.id))

    @app.route('/dispute/evidence/<int:evidence_id>', endpoint='dispute_evidence_file')
    def dispute_evidence_file(evidence_id):
        from app import DELIVERABLE_FOLDER
        e = DisputeEvidence.query.get_or_404(evidence_id)
        d = e.dispute
        allowed = False
        uid = session.get('user_id')
        if uid == d.hirer_id or (uid == d.translator_id and d.forwarded_at is not None):
            allowed = True
        elif session.get(ADMIN_SESSION_KEY):
            allowed = True
        if not allowed:
            abort(404)
        folder = os.path.join(DELIVERABLE_FOLDER, 'disputes')
        name = os.path.basename(e.filepath or '')
        if not name or not os.path.exists(os.path.join(folder, name)):
            abort(404)
        resp = send_from_directory(folder, name, as_attachment=True, download_name=e.filename)
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Cache-Control'] = 'private, no-store'
        return resp

    # --- Admin ----------------------------------------------------------------

    @app.route('/admin/disputes', endpoint='admin_disputes')
    @admin_login_required
    @require_permission('view_reports')
    def admin_disputes():
        status_filter = request.args.get('status', 'pending_review')
        q = Dispute.query
        if status_filter != 'all':
            q = q.filter_by(status=status_filter)
        items = q.order_by(Dispute.created_at.desc()).all()
        for d in items:
            refresh(d)
        return render_template('admin_disputes.html', items=items, status_filter=status_filter,
                               labels=STATUS_LABELS, categories=Dispute.CATEGORIES, money=money)

    @app.route('/admin/disputes/<int:dispute_id>', endpoint='admin_dispute_detail')
    @admin_login_required
    @require_permission('view_reports')
    def admin_dispute_detail(dispute_id):
        d = Dispute.query.get_or_404(dispute_id)
        refresh(d)
        deliverables = Deliverable.query.filter_by(contract_id=d.contract_id).order_by(Deliverable.created_at).all()
        return render_template('admin_dispute_detail.html', d=d, labels=STATUS_LABELS,
                               categories=Dispute.CATEGORIES, resolutions=Dispute.RESOLUTIONS,
                               deliverables=deliverables, steps=tracker_steps(d), money=money)

    @app.route('/admin/disputes/<int:dispute_id>/<action>', methods=['POST'], endpoint='admin_dispute_action')
    @admin_login_required
    @csrf_protected
    @require_permission('resolve_report')
    def admin_dispute_action(dispute_id, action):
        d = Dispute.query.get_or_404(dispute_id)
        refresh(d)
        admin_id = session.get(ADMIN_SESSION_KEY)
        note = request.form.get('note', '').strip()
        c = d.contract
        detail_url = url_for('dispute_detail', dispute_id=d.id)

        if action == 'reject' and d.status == 'pending_review':
            if not note:
                flash('Vui lòng nhập lý do bác bỏ.', 'error')
                return redirect(url_for('admin_dispute_detail', dispute_id=d.id))
            d.status = 'rejected'
            d.admin_note = note
            _notify(d.hirer_id, 'Khiếu nại bị bác bỏ',
                    f'Đơn khiếu nại #{d.id} của bạn đã bị bác bỏ. Lý do: {note}', detail_url)
            msg = 'Đã bác bỏ đơn khiếu nại.'
        elif action == 'forward' and d.status == 'pending_review':
            now = datetime.utcnow()
            d.status = 'awaiting_response'
            d.admin_note = note or None
            d.forwarded_at = now
            d.response_deadline = now + timedelta(hours=RESPONSE_HOURS)
            _notify(d.translator_id, 'Bạn nhận được một khiếu nại',
                    f'Khách hàng khiếu nại hợp đồng #{c.id} ({Dispute.CATEGORIES[d.category]}). '
                    f'Vui lòng giải trình và gửi minh chứng trong {RESPONSE_HOURS} giờ.', detail_url)
            _notify(d.hirer_id, 'Khiếu nại được chuyển sang bước tiếp theo',
                    f'Đơn #{d.id} đã được admin chấp nhận xem xét. PDV có {RESPONSE_HOURS} giờ để phản hồi.', detail_url)
            msg = f'Đã chuyển khiếu nại tới PDV (hạn phản hồi {RESPONSE_HOURS} giờ).'
        elif action == 'resolve' and d.status in ('awaiting_response', 'under_review'):
            resolution = request.form.get('resolution', '')
            if resolution not in Dispute.RESOLUTIONS:
                flash('Vui lòng chọn kết luận.', 'error')
                return redirect(url_for('admin_dispute_detail', dispute_id=d.id))
            if d.status == 'awaiting_response':
                flash('PDV vẫn còn thời hạn phản hồi. Hãy chờ hết hạn hoặc khi PDV gửi giải trình.', 'warning')
                return redirect(url_for('admin_dispute_detail', dispute_id=d.id))
            apply_resolution(d, resolution, note, admin_id)
            summary = f'{Dispute.RESOLUTIONS[resolution]} — số tiền cuối: {money(d.final_amount)} VND.'
            for uid in (d.hirer_id, d.translator_id):
                _notify(uid, 'Khiếu nại đã có kết quả', f'Đơn #{d.id}: {summary} Bấm để xem kết quả.', detail_url)
            msg = 'Đã kết luận khiếu nại và cập nhật khoản thanh toán.'
        else:
            flash('Thao tác không hợp lệ với trạng thái hiện tại.', 'error')
            return redirect(url_for('admin_dispute_detail', dispute_id=d.id))

        _audit_log(action='PAYMENT_ACTION' if action == 'resolve' else 'RESOLVE_REPORT',
                   target_type='dispute', target_id=d.id,
                   description=f'Khiếu nại đơn thuê #{d.id}: {action}',
                   extra_data={'note': note, 'resolution': d.resolution})
        db.session.commit()
        flash(msg, 'success')
        return redirect(url_for('admin_dispute_detail', dispute_id=d.id))
