"""
services/admin_job_service.py
Dịch vụ kiểm duyệt và phê duyệt công việc (Job) an toàn dành cho Quản trị viên (Admin).

Nguyên tắc cốt lõi:
1. Hợp nhất logic duyệt: Cả duyệt nhanh (Quick Approve) và duyệt chi tiết (Detail Review) đều phải tuân thủ cùng quy tắc nghiệp vụ.
2. An toàn tuyệt đối: Không cho phép duyệt nhanh nếu:
   - Job có vi phạm nghiêm trọng (C1, C2, C3, C6, C9, C10).
   - Người đăng tuyển chưa được xác minh danh tính.
   - Job đã bị gắn cờ, đã từ chối hoặc đã lưu trữ.
   - Lỗi engine đánh giá tiêu chí (cần kiểm tra thủ công).
3. Đầy đủ vết kiểm toán (Audit Trail) và thông báo đa kênh.
"""

import json
from datetime import datetime
from models import db, Job, User, HirerProfile, ADMIN_AUDIT_ACTIONS
from services.job_moderation import evaluate_job_39_criteria

def evaluate_job_safety(job):
    """
    Chạy engine đánh giá 39 tiêu chí với cơ chế cô lập lỗi từng bản ghi.
    Đảm bảo nếu một bản ghi có dữ liệu bất thường, hệ thống vẫn an toàn.
    """
    try:
        eval_res = evaluate_job_39_criteria(job)
    except Exception as e:
        eval_res = {
            'total_critical': 0,
            'total_warnings': 0,
            'total_passed': 0,
            'summary_label': 'Chưa đánh giá được — cần kiểm tra thủ công',
            'summary_badge': 'badge-warning',
            'needs_manual_review': True,
            'eval_error': str(e),
            'criteria': {},
            'groups': {}
        }
    return eval_res

def check_quick_approve_eligibility(job, eval_res=None):
    """
    Kiểm tra xem Job có đủ điều kiện để Duyệt Nhanh (Quick Approve) trực tiếp hay không.
    Trả về: (is_eligible: bool, reason: str, eval_res: dict)
    """
    if not job:
        return False, "Công việc không tồn tại.", {}

    # 1. Trạng thái cơ bản
    if getattr(job, 'is_flagged', False):
        return False, "Công việc đang bị gắn cờ vi phạm — cần thẩm định chi tiết.", eval_res or {}
    
    if getattr(job, 'status', None) == 'archived' or getattr(job, 'moderation_status', None) == 'archived':
        return False, "Công việc đã được lưu trữ, không thể duyệt nhanh.", eval_res or {}

    if getattr(job, 'closed_at', None) is not None or getattr(job, 'status', None) in ('closed', 'cancelled'):
        return False, "Công việc đã bị người đăng gỡ hoặc đóng trước đó.", eval_res or {}

    if getattr(job, 'status', None) in ('contracted', 'in_progress', 'completed'):
        return False, "Công việc đã chốt hợp đồng hoặc kết thúc, không thể duyệt nhanh.", eval_res or {}

    if getattr(job, 'moderation_status', None) == 'rejected':
        return False, "Công việc đã bị từ chối trước đó.", eval_res or {}

    if getattr(job, 'status', None) == 'open' and getattr(job, 'moderation_status', None) == 'approved':
        return False, "Công việc đã được phê duyệt công khai trước đó.", eval_res or {}

    # 2. Đánh giá tiêu chí
    if eval_res is None:
        eval_res = evaluate_job_safety(job)

    if eval_res.get('needs_manual_review'):
        return False, "Có lỗi khi quét tự động — Bắt buộc kiểm tra thủ công.", eval_res

    total_critical = eval_res.get('total_critical', 0)
    if total_critical > 0:
        return False, f"Phát hiện {total_critical} vi phạm nghiêm trọng (Nhóm C) — Bắt buộc kiểm tra chi tiết.", eval_res

    # 3. Kiểm tra xác minh người đăng tuyển (Hirer)
    hirer = getattr(job, 'hirer', None)
    if not hirer:
        return False, "Không xác định được tài khoản người đăng tuyển.", eval_res

    hirer_profile = getattr(hirer, 'hirer_profile', None)
    is_hirer_verified = bool(
        hirer_profile and (
            getattr(hirer_profile, 'is_verified', False) is True or 
            getattr(hirer_profile, 'verification_status', None) == 'verified'
        )
    )
    if not is_hirer_verified:
        return False, "Người đăng tuyển chưa hoàn tất xác minh danh tính (Chưa có tích xanh).", eval_res

    return True, "Đủ điều kiện phê duyệt nhanh an toàn.", eval_res

def safe_approve_job(job, admin_id=None, is_quick=False, manual_overrides=None, audit_logger=None):
    """
    Thực hiện phê duyệt công việc một cách an toàn và nhất quán.
    - is_quick: Nếu True, bắt buộc thỏa mãn 100% điều kiện duyệt nhanh.
    - manual_overrides: Dict ghi đè thủ công (ví dụ {'C7': True}) khi duyệt từ màn hình chi tiết.
    - audit_logger: Hàm ghi audit log (nếu có, mặc định dùng _audit_log nội bộ).
    Trả về: (success: bool, message: str, eval_res: dict)
    """
    if not job:
        return False, "Công việc không tồn tại.", {}

    # Đảm bảo lấy dữ liệu mới nhất nếu job đang nằm trong db session
    try:
        if hasattr(job, 'id') and job.id and job in db.session:
            db.session.refresh(job)
    except Exception:
        pass

    # Đánh giá tiêu chí kèm manual_overrides nếu có
    try:
        eval_res = evaluate_job_39_criteria(job, manual_overrides=manual_overrides or {})
    except Exception as e:
        eval_res = evaluate_job_safety(job)

    # Nếu là duyệt nhanh, kiểm tra nghiêm ngặt
    if is_quick:
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_res)
        if not eligible:
            return False, f"Không thể duyệt nhanh: {reason}", eval_res
    else:
        # Nếu là duyệt chi tiết, vẫn chặn nếu có vi phạm nghiêm trọng mà không có lý do hợp lệ
        if eval_res.get('total_critical', 0) > 0 and not manual_overrides:
            return False, "Công việc có vi phạm nghiêm trọng. Không thể phê duyệt nếu chưa xử lý vi phạm.", eval_res

    # Xác định trạng thái vòng đời hiện tại của job
    is_closed_or_withdrawn = bool(
        getattr(job, 'closed_at', None) is not None or
        getattr(job, 'status', '') in ('closed', 'cancelled')
    )
    is_contracted_or_done = bool(
        getattr(job, 'status', '') in ('contracted', 'in_progress', 'completed')
    )

    # Cập nhật kết quả kiểm duyệt
    job.moderation_status = 'approved'
    job.is_flagged = False
    job.moderated_at = datetime.utcnow()
    job.moderated_by = admin_id
    job.moderation_checklist_data = json.dumps(eval_res)

    # QUY TẮC BẢO TOÀN VÒNG ĐỜI:
    # Tuyệt đối không kích hoạt lại công việc nếu người thuê đã gỡ hoặc đã chốt hợp đồng
    if is_closed_or_withdrawn:
        # Giữ nguyên trạng thái closed/cancelled và closed_at
        status_msg = "Job đã bị người đăng gỡ/đóng trước đó nên được giữ nguyên trạng thái đóng."
    elif is_contracted_or_done:
        # Giữ nguyên trạng thái hợp đồng / hoàn tất
        status_msg = "Job đang trong tiến độ hợp đồng nên được giữ nguyên trạng thái."
    else:
        # Chuyển sang mở công khai bình thường
        job.status = 'open'
        status_msg = "Job đã hiển thị công khai."

    # Ghi nhận Audit Log
    if audit_logger:
        try:
            audit_logger(
                action=ADMIN_AUDIT_ACTIONS['APPROVE_JOB'],
                target_type='job',
                target_id=job.id,
                description=f'{"Duyệt nhanh" if is_quick else "Xét duyệt chi tiết"} job "{job.title}" (ID={job.id}) đạt kiểm duyệt. {status_msg}',
                extra_data={
                    'is_quick': is_quick,
                    'checklist_summary': eval_res.get('summary_label', 'Đạt 39/39'),
                    'total_passed': eval_res.get('total_passed', 39),
                    'lifecycle_status': job.status,
                    'was_closed': is_closed_or_withdrawn
                }
            )
        except Exception:
            pass

    # Gửi thông báo cho Người đăng tuyển (Hirer)
    if getattr(job, 'hirer_id', None):
        try:
            from app import create_notification
            from flask import url_for
            hirer_msg = (
                f'Công việc "{job.title}" của bạn đã được kiểm duyệt hợp lệ (giữ trạng thái đã đóng).'
                if is_closed_or_withdrawn else
                f'Công việc "{job.title}" của bạn đã được kiểm duyệt và hiển thị công khai trên sàn.'
            )
            create_notification(
                user_id=job.hirer_id,
                notification_type='JOB_APPROVED',
                title='Công việc đã được phê duyệt',
                message=hirer_msg,
                url=url_for('job_detail', job_id=job.id),
                related_job_id=job.id
            )
        except Exception:
            pass

    # Gửi thông báo cho các phiên dịch viên phù hợp (CHỈ KHI JOB THỰC SỰ MỞ CÔNG KHAI)
    if not is_closed_or_withdrawn and not is_contracted_or_done:
        try:
            from services.matching import notify_matching_translators_for_new_job
            notify_matching_translators_for_new_job(job)
        except Exception:
            pass

    return True, f'Đã phê duyệt công việc #{job.id} thành công. {status_msg}', eval_res

