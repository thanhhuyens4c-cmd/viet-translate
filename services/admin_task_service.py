"""
services/admin_task_service.py
Dịch vụ quản trị tập trung Trung tâm Tác vụ (Admin Task Center).
Tổng hợp, phân loại, lọc và phân trang các công việc cần xử lý từ nhiều phân hệ:
1. Duyệt Job (Job Moderation)
2. Xác minh Hồ sơ Phiên dịch viên (Translator Verification)
3. Xác minh Người đăng tuyển (Hirer Verification)
4. Báo cáo vi phạm (User / Content Reports)
5. Khiếu nại / Tranh chấp đơn thuê (Disputes)
"""

from datetime import datetime, timedelta
from flask import url_for
from models import db, Job, User, TranslatorProfile, TranslatorVerification, HirerProfile, Report, Dispute, AdminAuditLog
from services.admin_job_service import evaluate_job_safety, check_quick_approve_eligibility

def safe_url_for(endpoint, **values):
    try:
        return url_for(endpoint, **values)
    except Exception:
        if endpoint == 'admin_job_review':
            return f"/admin/jobs/{values.get('job_id')}/review"
        elif endpoint == 'admin_approve_job':
            return f"/admin/jobs/{values.get('job_id')}/approve"
        elif endpoint == 'admin_verification_detail':
            return f"/admin/verifications/{values.get('verification_id')}"
        elif endpoint == 'admin_hirer_verify':
            return f"/admin/hirers/{values.get('hirer_id')}/verify"
        elif endpoint == 'admin_reports':
            return "/admin/reports"
        elif endpoint == 'admin_dispute_detail':
            return f"/admin/disputes/{values.get('dispute_id')}"
        elif endpoint == 'admin_disputes':
            return "/admin/disputes"
        return f"/admin/{endpoint}"

def get_admin_tasks_summary():
    """
    Tính toán các chỉ số KPI thực tế cho Task Center từ cơ sở dữ liệu.
    Không sử dụng số liệu giả lập.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Số lượng việc chờ theo phân hệ
    pending_jobs_count = Job.query.filter(
        db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
        db.or_(Job.is_flagged == False, Job.is_flagged.is_(None)),
        Job.status != 'closed',
        Job.status != 'cancelled',
        Job.closed_at.is_(None)
    ).count()

    flagged_jobs_count = Job.query.filter_by(is_flagged=True).count()
    
    pending_translators_count = TranslatorVerification.query.filter_by(status='pending').count()
    if pending_translators_count == 0:
        # Fallback đếm hồ sơ chưa xác minh
        pending_translators_count = TranslatorProfile.query.filter_by(is_verified=False).count()

    pending_hirers_count = HirerProfile.query.filter_by(verification_status='pending').count()
    pending_reports_count = Report.query.filter(Report.status.in_(['new', 'investigating'])).count()
    
    pending_disputes_count = 0
    try:
        pending_disputes_count = Dispute.query.filter(Dispute.status.in_(['pending_review', 'awaiting_response', 'under_review', 'open', 'mediating', 'escalated'])).count()
    except Exception:
        pass

    total_pending = pending_jobs_count + pending_translators_count + pending_hirers_count + pending_reports_count + pending_disputes_count

    # 2. Đã xử lý hôm nay (Lấy từ Audit Log)
    resolved_actions = [
        'APPROVE_JOB', 'REJECT_JOB', 'REQUEST_JOB_REVISION',
        'VERIFY_TRANSLATOR', 'REJECT_TRANSLATOR',
        'VERIFY_HIRER', 'REJECT_HIRER', 'REQUEST_HIRER_REVISION',
        'RESOLVE_REPORT', 'REJECT_REPORT'
    ]
    resolved_today_count = AdminAuditLog.query.filter(
        AdminAuditLog.created_at >= today_start,
        AdminAuditLog.action.in_(resolved_actions)
    ).count()

    # 3. Tác vụ khẩn cấp / ưu tiên cao (Vi phạm nghiêm trọng hoặc bị gắn cờ)
    critical_count = flagged_jobs_count
    # Quét nhanh các job pending để đếm job có vi phạm C
    try:
        pending_jobs_sample = Job.query.filter(
            db.or_(Job.moderation_status == 'pending', Job.status == 'pending'),
            Job.status != 'closed',
            Job.status != 'cancelled',
            Job.closed_at.is_(None)
        ).limit(50).all()
        for j in pending_jobs_sample:
            ev = evaluate_job_safety(j)
            if ev.get('total_critical', 0) > 0:
                critical_count += 1
    except Exception:
        pass

    return {
        'total_pending': total_pending,
        'critical_count': critical_count,
        'resolved_today': resolved_today_count,
        'pending_jobs': pending_jobs_count,
        'pending_translators': pending_translators_count,
        'pending_hirers': pending_hirers_count,
        'pending_reports': pending_reports_count,
        'pending_disputes': pending_disputes_count,
    }

def query_admin_tasks(filters, page=1, per_page=15, admin_user=None):
    """
    Truy vấn và tổng hợp danh sách tác vụ đa điều kiện.
    Filters hỗ trợ:
    - q: Từ khóa tìm kiếm (mã, tiêu đề, tên/email người liên quan)
    - type: Loại tác vụ ('all', 'job', 'translator', 'hirer', 'report', 'dispute')
    - status: Trạng thái ('all', 'pending', 'critical', 'needs_revision', 'resolved')
    - priority: Mức độ ưu tiên ('all', 'critical', 'warning', 'normal')
    - time_range: Khoảng thời gian ('all', 'today', '7d', '30d')
    """
    q = (filters.get('q') or '').strip().lower()
    task_type = filters.get('type') or 'all'
    status_filter = filters.get('status') or 'all'
    priority_filter = filters.get('priority') or 'all'
    time_range = filters.get('time_range') or 'all'

    now = datetime.utcnow()
    since_date = None
    if time_range == 'today':
        since_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == '7d':
        since_date = now - timedelta(days=7)
    elif time_range == '30d':
        since_date = now - timedelta(days=30)

    tasks = []

    # ── 1. NHÓM TÁC VỤ JOB ──────────────────────────────────────────────────
    if task_type in ('all', 'job'):
        job_query = Job.query
        if since_date:
            job_query = job_query.filter(Job.created_at >= since_date)
        
        # Mặc định lấy các job cần xử lý (pending, flagged, needs_revision)
        if status_filter == 'pending':
            job_query = job_query.filter(
                db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
                db.or_(Job.is_flagged == False, Job.is_flagged.is_(None)),
                Job.status != 'closed',
                Job.status != 'cancelled',
                Job.closed_at.is_(None)
            )
        elif status_filter == 'critical':
            job_query = job_query.filter(db.or_(Job.is_flagged == True, Job.moderation_status == 'flagged'))
        elif status_filter == 'needs_revision':
            job_query = job_query.filter_by(moderation_status='needs_revision')
        elif status_filter == 'all':
            # Ưu tiên các job pending/flagged chưa bị đóng
            job_query = job_query.filter(
                db.or_(
                    db.and_(
                        Job.moderation_status.in_(['pending', 'needs_revision']),
                        Job.status != 'closed',
                        Job.status != 'cancelled',
                        Job.closed_at.is_(None)
                    ),
                    Job.moderation_status == 'flagged',
                    Job.is_flagged == True
                )
            )

        jobs = job_query.order_by(Job.created_at.desc()).limit(100).all()

        for j in jobs:
            ev = evaluate_job_safety(j)
            is_crit = (ev.get('total_critical', 0) > 0) or j.is_flagged
            is_warn = (ev.get('total_warnings', 0) > 0) or (j.moderation_status == 'needs_revision')
            
            prio = 'critical' if is_crit else ('warning' if is_warn else 'normal')
            prio_label = 'Nghiêm trọng' if is_crit else ('Cần xem xét' if is_warn else 'Bình thường')
            prio_badge = 'badge-red' if is_crit else ('badge-warning' if is_warn else 'badge-gray')

            # Kiểm tra duyệt nhanh
            can_quick, quick_reason, _ = check_quick_approve_eligibility(j, eval_res=ev)

            is_closed = (getattr(j, 'status', '') in ('closed', 'cancelled')) or (getattr(j, 'closed_at', None) is not None)
            if j.is_flagged or getattr(j, 'moderation_status', None) == 'flagged':
                st_key = 'flagged'
                st_label = 'Bị gắn cờ'
                st_badge = 'badge-red'
            elif getattr(j, 'moderation_status', None) == 'rejected':
                st_key = 'rejected'
                st_label = 'Bị từ chối'
                st_badge = 'badge-red'
            elif getattr(j, 'moderation_status', None) == 'needs_revision':
                st_key = 'needs_revision'
                st_label = 'Cần sửa'
                st_badge = 'badge-warning'
            elif getattr(j, 'moderation_status', None) == 'approved':
                st_key = 'approved'
                if is_closed:
                    st_label = 'Đã duyệt (Đã đóng)'
                    st_badge = 'badge-gray'
                elif getattr(j, 'status', '') == 'contracted':
                    st_label = 'Đã ký HĐ'
                    st_badge = 'badge-blue'
                else:
                    st_label = 'Đang hoạt động'
                    st_badge = 'badge-green'
            else:
                st_key = 'pending'
                st_label = 'Chờ duyệt'
                st_badge = 'badge-warning'

            hirer_name = j.hirer.name if j.hirer else 'Khách ẩn danh'
            hirer_email = j.hirer.email if j.hirer else ''

            tasks.append({
                'id': f"JOB-{j.id}",
                'raw_id': j.id,
                'type': 'job',
                'type_label': 'Duyệt Job',
                'type_badge': 'badge-blue',
                'title': j.title,
                'subtitle': f"{j.category or 'Phiên dịch'} • {j.source_lang} → {j.target_lang}",
                'user_name': hirer_name,
                'user_sub': hirer_email,
                'is_user_verified': bool(j.hirer and j.hirer.hirer_profile and (j.hirer.hirer_profile.is_verified or j.hirer.hirer_profile.verification_status == 'verified')),
                'created_at': j.created_at,
                'status': st_key,
                'status_label': st_label,
                'status_badge': st_badge,
                'priority': prio,
                'priority_label': prio_label,
                'priority_badge': prio_badge,
                'detail_url': safe_url_for('admin_job_review', job_id=j.id),
                'can_quick_approve': can_quick,
                'quick_approve_reason': quick_reason,
                'quick_approve_url': safe_url_for('admin_approve_job', job_id=j.id),
                'eval_summary': ev.get('summary_label', 'Đạt 39/39'),
                'eval_badge': ev.get('summary_badge', 'badge-green')
            })

    # ── 2. NHÓM TÁC VỤ XÁC MINH PHIÊN DỊCH VIÊN ─────────────────────────────
    if task_type in ('all', 'translator') and status_filter in ('all', 'pending'):
        tr_query = TranslatorVerification.query.filter_by(status='pending')
        if since_date:
            tr_query = tr_query.filter(TranslatorVerification.created_at >= since_date)
        verifs = tr_query.order_by(TranslatorVerification.created_at.desc()).limit(50).all()

        for v in verifs:
            u = v.user
            uname = u.name if u else 'PDV'
            uemail = u.email if u else ''
            full_name = getattr(v, 'full_name', '') or uname
            phone = getattr(v, 'phone', '')
            tasks.append({
                'id': f"TR-V{v.id}",
                'raw_id': v.id,
                'type': 'translator',
                'type_label': 'Hồ sơ PDV',
                'type_badge': 'badge-indigo',
                'title': f"Xác minh danh tính & chứng chỉ: {full_name}",
                'subtitle': f"SĐT: {phone} • Đã nộp tài liệu xác minh" if phone else "Đã nộp tài liệu xác minh danh tính",
                'user_name': uname,
                'user_sub': uemail,
                'is_user_verified': False,
                'created_at': v.created_at,
                'status': 'pending',
                'status_label': 'Chờ xác minh',
                'status_badge': 'badge-warning',
                'priority': 'warning',
                'priority_label': 'Cần kiểm tra',
                'priority_badge': 'badge-warning',
                'detail_url': safe_url_for('admin_verification_detail', verification_id=v.id),
                'can_quick_approve': False,
                'quick_approve_reason': 'Bắt buộc đối chiếu hình ảnh CCCD và chứng chỉ trong chi tiết',
                'quick_approve_url': None,
                'eval_summary': 'Hồ sơ mới gửi',
                'eval_badge': 'badge-gray'
            })

    # ── 3. NHÓM TÁC VỤ XÁC MINH NGƯỜI ĐĂNG TUYỂN ───────────────────────────
    if task_type in ('all', 'hirer') and status_filter in ('all', 'pending'):
        h_query = HirerProfile.query.filter_by(verification_status='pending')
        h_profiles = h_query.order_by(HirerProfile.user_id.desc()).limit(50).all()

        for hp in h_profiles:
            u = hp.user
            if not u:
                continue
            tasks.append({
                'id': f"HIRER-{u.id}",
                'raw_id': u.id,
                'type': 'hirer',
                'type_label': 'Người đăng',
                'type_badge': 'badge-cyan',
                'title': f"Xác minh thông tin doanh nghiệp/cá nhân: {u.name}",
                'subtitle': f"Đơn vị: {getattr(hp, 'company', None) or 'Cá nhân tuyển dụng'}",
                'user_name': u.name,
                'user_sub': u.email,
                'is_user_verified': False,
                'created_at': getattr(hp, 'submitted_at', None) or getattr(u, 'created_at', None) or now,
                'status': 'pending',
                'status_label': 'Chờ thẩm định',
                'status_badge': 'badge-warning',
                'priority': 'normal',
                'priority_label': 'Đúng hạn',
                'priority_badge': 'badge-gray',
                'detail_url': safe_url_for('admin_hirer_verify', hirer_id=u.id),
                'can_quick_approve': False,
                'quick_approve_reason': 'Cần kiểm tra hồ sơ giấy tờ pháp lý trước khi cấp tích xanh',
                'quick_approve_url': None,
                'eval_summary': 'Chờ duyệt',
                'eval_badge': 'badge-warning'
            })

    # ── 4. NHÓM TÁC VỤ BÁO CÁO VI PHẠM ──────────────────────────────────────
    if task_type in ('all', 'report') and status_filter in ('all', 'pending', 'new'):
        rep_query = Report.query.filter(Report.status.in_(['new', 'investigating']))
        if since_date:
            rep_query = rep_query.filter(Report.created_at >= since_date)
        reps = rep_query.order_by(Report.created_at.desc()).limit(50).all()

        for r in reps:
            reporter_name = r.reporter.name if r.reporter else 'Ẩn danh'
            reporter_email = r.reporter.email if r.reporter else ''
            target_info = f"{getattr(r, 'target_type', 'user').upper()} #{getattr(r, 'target_id', '')}"
            tasks.append({
                'id': f"REP-{r.id}",
                'raw_id': r.id,
                'type': 'report',
                'type_label': 'Báo cáo',
                'type_badge': 'badge-red',
                'title': f"Báo cáo vi phạm: {r.reason or 'Hành vi đáng ngờ'}",
                'subtitle': f"Đối tượng: {target_info} • Lý do: {r.reason or 'Cần điều tra'}",
                'user_name': reporter_name,
                'user_sub': reporter_email,
                'is_user_verified': False,
                'created_at': r.created_at,
                'status': r.status,
                'status_label': 'Mới nhận' if r.status == 'new' else 'Đang điều tra',
                'status_badge': 'badge-red' if r.status == 'new' else 'badge-warning',
                'priority': 'critical',
                'priority_label': 'Ưu tiên cao',
                'priority_badge': 'badge-red',
                'detail_url': safe_url_for('admin_reports'),
                'can_quick_approve': False,
                'quick_approve_reason': 'Báo cáo vi phạm bắt buộc điều tra và ghi rõ kết luận',
                'quick_approve_url': None,
                'eval_summary': 'Cần điều tra',
                'eval_badge': 'badge-red'
            })

    # ── 5. NHÓM TÁC VỤ KHIẾU NẠI / TRANH CHẤP ──────────────────────────────
    if task_type in ('all', 'dispute') and status_filter in ('all', 'pending'):
        try:
            disp_query = Dispute.query.filter(Dispute.status.in_(['pending_review', 'awaiting_response', 'under_review', 'open', 'mediating', 'escalated']))
            if since_date:
                disp_query = disp_query.filter(Dispute.created_at >= since_date)
            disps = disp_query.order_by(Dispute.created_at.desc()).limit(50).all()

            for d in disps:
                p_label = 'Khẩn cấp' if d.status == 'escalated' else 'Đang xử lý'
                p_badge = 'badge-red' if d.status == 'escalated' else 'badge-warning'
                creator_name = d.hirer.name if getattr(d, 'hirer', None) else 'Bên khiếu nại'
                creator_email = d.hirer.email if getattr(d, 'hirer', None) else ''

                tasks.append({
                    'id': f"DISP-{d.id}",
                    'raw_id': d.id,
                    'type': 'dispute',
                    'type_label': 'Khiếu nại',
                    'type_badge': 'badge-yellow',
                    'title': f"Khiếu nại hợp đồng #{d.contract_id or d.id}: {d.category or 'Tranh chấp ca dịch'}",
                    'subtitle': f"Chi tiết: {d.description or 'Cần đối chiếu hợp đồng'}",
                    'user_name': creator_name,
                    'user_sub': creator_email,
                    'is_user_verified': False,
                    'created_at': d.created_at,
                    'status': d.status,
                    'status_label': 'Mở hòa giải' if d.status in ('open', 'pending_review') else 'Leo thang',
                    'status_badge': 'badge-red' if d.status == 'escalated' else 'badge-warning',
                    'priority': 'critical' if d.status == 'escalated' else 'warning',
                    'priority_label': p_label,
                    'priority_badge': p_badge,
                    'detail_url': safe_url_for('admin_dispute_detail', dispute_id=d.id) if 'admin_dispute_detail' in globals() else safe_url_for('admin_disputes'),
                    'can_quick_approve': False,
                    'quick_approve_reason': 'Tranh chấp hợp đồng/tiền bắt buộc quy trình hòa giải hai bên',
                    'quick_approve_url': None,
                    'eval_summary': 'Tranh chấp tiền',
                    'eval_badge': 'badge-red'
                })
        except Exception:
            pass

    # ── LỌC THEO TỪ KHÓA (q) ────────────────────────────────────────────────
    if q:
        filtered = []
        for t in tasks:
            searchable = f"{t['id']} {t['title']} {t['subtitle']} {t['user_name']} {t['user_sub']}".lower()
            if q in searchable:
                filtered.append(t)
        tasks = filtered

    # ── LỌC THEO MỨC ƯU TIÊN (priority) ──────────────────────────────────────
    if priority_filter != 'all':
        tasks = [t for t in tasks if t['priority'] == priority_filter]

    # ── SẮP XẾP: Ưu tiên critical trước, sau đó theo thời gian giảm dần ───────
    def sort_key(item):
        prio_weight = 3 if item['priority'] == 'critical' else (2 if item['priority'] == 'warning' else 1)
        created = item['created_at'] or datetime.min
        return (prio_weight, created)

    tasks.sort(key=sort_key, reverse=True)

    # ── PHÂN TRANG (PAGINATION) ──────────────────────────────────────────────
    total_count = len(tasks)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = tasks[start_idx:end_idx]

    return paginated_items, total_count, total_pages, page
