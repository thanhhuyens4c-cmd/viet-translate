"""
tests/test_admin_tasks_and_quick_approve.py
Bộ kiểm thử toàn diện cho Trung tâm Tác vụ Quản trị (Admin Task Center),
Bộ lọc đa năng, Cơ chế Duyệt nhanh an toàn và Tối ưu Mobile.
"""

import unittest
import os
import sys
from datetime import datetime, timedelta

os.environ['FLASK_ENV'] = 'testing'

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, Job, HirerProfile, TranslatorProfile, Report, Dispute
from services.admin_task_service import get_admin_tasks_summary, query_admin_tasks
from services.admin_job_service import check_quick_approve_eligibility, safe_approve_job, evaluate_job_safety

class AdminTasksAndQuickApproveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        with app.app_context():
            db.create_all()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _login_admin(self, client):
        """Helper to simulate an active Super Admin session."""
        admin = User.query.get(1)
        if not admin:
            admin = User(
                id=1,
                email='superadmin_test@viettranslate.vn',
                name='Super Admin Test',
                role='admin',
                admin_role='super_admin',
                is_admin=True,
                is_active=True,
                password_hash='testpass'
            )
            db.session.add(admin)
        else:
            admin.admin_role = 'super_admin'
            admin.is_admin = True
            admin.is_active = True
        db.session.commit()

        now_ts = datetime.utcnow().timestamp()
        with client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['admin_role'] = 'super_admin'
            sess['admin_permissions'] = ['view_dashboard', 'view_jobs', 'approve_job', 'reject_job', 'flag_job', 'view_translators', 'view_hirers', 'view_reports']
            sess['admin_session_created'] = now_ts
            sess['admin_session_last_seen'] = now_ts
            sess['admin_csrf_token'] = 'valid_test_admin_token'

    # ═════════════════════════════════════════════════════════════════
    # 1. KIỂM THỬ TỔNG HỢP KPI CHỈ SỐ THỰC TẾ
    # ═════════════════════════════════════════════════════════════════
    def test_01_admin_tasks_summary_structure(self):
        """Xác minh get_admin_tasks_summary tính toán đầy đủ các chỉ số thật từ database."""
        summary = get_admin_tasks_summary()
        self.assertIsInstance(summary, dict)
        required_keys = [
            'total_pending', 'critical_count', 'resolved_today',
            'pending_jobs', 'pending_translators', 'pending_hirers',
            'pending_reports', 'pending_disputes'
        ]
        for key in required_keys:
            self.assertIn(key, summary)
            self.assertIsInstance(summary[key], int)
            self.assertGreaterEqual(summary[key], 0)

        # Tính nhất quán: total_pending = jobs + translators + hirers + reports + disputes
        expected_total = (
            summary['pending_jobs'] +
            summary['pending_translators'] +
            summary['pending_hirers'] +
            summary['pending_reports'] +
            summary['pending_disputes']
        )
        self.assertEqual(summary['total_pending'], expected_total)

    # ═════════════════════════════════════════════════════════════════
    # 2. KIỂM THỬ BỘ LỌC ĐA NĂNG (QUERY ADMIN TASKS)
    # ═════════════════════════════════════════════════════════════════
    def test_02_query_admin_tasks_filters(self):
        """Xác minh bộ lọc tác vụ hoạt động chính xác theo loại, ưu tiên, thời gian và từ khóa."""
        # 1. Lọc mặc định (all)
        tasks, total_count, total_pages, page = query_admin_tasks(filters={
            'q': '', 'type': 'all', 'status': 'all', 'priority': 'all', 'time_range': 'all'
        }, page=1, per_page=10)
        self.assertIsInstance(tasks, list)
        self.assertGreaterEqual(total_count, 0)
        self.assertGreaterEqual(total_pages, 1)

        # 2. Lọc theo loại 'job'
        job_tasks, j_count, _, _ = query_admin_tasks(filters={
            'q': '', 'type': 'job', 'status': 'all', 'priority': 'all', 'time_range': 'all'
        }, page=1, per_page=10)
        for t in job_tasks:
            self.assertEqual(t['type'], 'job')
            self.assertIn('raw_id', t)
            self.assertIn('detail_url', t)

        # 3. Lọc theo độ ưu tiên 'critical'
        crit_tasks, c_count, _, _ = query_admin_tasks(filters={
            'q': '', 'type': 'all', 'status': 'all', 'priority': 'critical', 'time_range': 'all'
        }, page=1, per_page=10)
        for t in crit_tasks:
            self.assertEqual(t['priority'], 'critical')

        # 4. Lọc theo từ khóa không tồn tại
        empty_tasks, e_count, _, _ = query_admin_tasks(filters={
            'q': 'xyz_non_existent_search_query_99999', 'type': 'all', 'status': 'all', 'priority': 'all', 'time_range': 'all'
        }, page=1, per_page=10)
        self.assertEqual(len(empty_tasks), 0)
        self.assertEqual(e_count, 0)

    # ═════════════════════════════════════════════════════════════════
    # 3. KIỂM THỬ QUY TẮC DUYỆT NHANH AN TOÀN (ELIGIBILITY RULES)
    # ═════════════════════════════════════════════════════════════════
    def test_03_quick_approve_eligibility_rules(self):
        """Xác minh các điều kiện chặn nghiêm ngặt của Duyệt nhanh."""
        # Tạo mock / đối tượng Job giả lập
        job = Job()
        job.id = 9999
        job.title = "Phiên dịch hội nghị Tiếng Nhật"
        job.status = "pending"
        job.moderation_status = "pending"
        job.is_flagged = False

        # Hirer giả lập
        hirer = User()
        hirer.id = 8888
        hirer.name = "Công ty TNHH ABC"
        hirer_profile = HirerProfile()
        hirer_profile.verification_status = "verified"
        hirer_profile.is_verified = True
        hirer.hirer_profile = hirer_profile
        job.hirer = hirer

        # Trường hợp 1: Đủ điều kiện (0 vi phạm nhóm C, hirer đã xác minh, pending)
        eval_safe = {'total_critical': 0, 'total_warnings': 1, 'needs_manual_review': False}
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_safe)
        self.assertTrue(eligible)
        self.assertIn("Đủ điều kiện", reason)

        # Trường hợp 2: Bị chặn vì có vi phạm nghiêm trọng (Nhóm C)
        eval_critical = {'total_critical': 2, 'total_warnings': 0, 'needs_manual_review': False}
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_critical)
        self.assertFalse(eligible)
        self.assertIn("vi phạm nghiêm trọng", reason)

        # Trường hợp 3: Bị chặn vì khách đăng chưa xác minh danh tính
        hirer_profile.verification_status = "pending"
        hirer_profile.is_verified = False
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_safe)
        self.assertFalse(eligible)
        self.assertIn("chưa hoàn tất xác minh danh tính", reason)

        # Trường hợp 4: Bị chặn vì Job đang bị gắn cờ vi phạm
        hirer_profile.verification_status = "verified"
        hirer_profile.is_verified = True
        job.is_flagged = True
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_safe)
        self.assertFalse(eligible)
        self.assertIn("gắn cờ vi phạm", reason)

        # Trường hợp 5: Bị chặn vì Job đã được lưu trữ (archived)
        job.is_flagged = False
        job.status = "archived"
        eligible, reason, _ = check_quick_approve_eligibility(job, eval_res=eval_safe)
        self.assertFalse(eligible)
        self.assertIn("đã được lưu trữ", reason)

    # ═════════════════════════════════════════════════════════════════
    # 4. KIỂM THỬ THỰC THI DUYỆT AN TOÀN (SAFE APPROVE JOB)
    # ═════════════════════════════════════════════════════════════════
    def test_04_safe_approve_job_execution(self):
        """Xác minh hàm safe_approve_job cập nhật đúng trạng thái và ghi nhận audit log."""
        job = Job()
        job.id = 9998
        job.title = "Phiên dịch cabin Tiếng Hàn tại Hà Nội"
        job.category = "simultaneous"
        job.source_lang = "ko"
        job.target_lang = "vi"
        job.description = "Tuyển phiên dịch viên cabin hội nghị quốc tế chuyên ngành tại Hà Nội. Đảm bảo chế độ tiêu chuẩn cao."
        job.event_location = "Trung tâm Hội nghị Quốc gia, Hà Nội"
        job.event_date = datetime.utcnow() + timedelta(days=5)
        job.budget_min = 2500000
        job.status = "pending"
        job.moderation_status = "pending"
        job.is_flagged = False

        hirer = User()
        hirer.id = 8887
        hirer.name = "Tập đoàn XYZ"
        hirer_profile = HirerProfile()
        hirer_profile.verification_status = "unverified"
        hirer_profile.is_verified = False
        hirer.hirer_profile = hirer_profile
        job.hirer = hirer

        audit_logs = []
        def mock_audit(action, target_type, target_id, description, extra_data=None):
            audit_logs.append({
                'action': action,
                'target_type': target_type,
                'target_id': target_id,
                'description': description
            })

        # Khi gọi duyệt nhanh (is_quick=True) trên job chưa đủ điều kiện -> BỊ TỪ CHỐI
        success, msg, _ = safe_approve_job(job, admin_id=1, is_quick=True, audit_logger=mock_audit)
        self.assertFalse(success)
        self.assertIn("Không thể duyệt nhanh", msg)
        self.assertEqual(job.status, "pending")
        self.assertEqual(len(audit_logs), 0)

        # Cấp quyền xác minh cho hirer để thỏa mãn điều kiện
        hirer_profile.verification_status = "verified"
        hirer_profile.is_verified = True

        # Khi gọi duyệt nhanh (is_quick=True) trên job đủ điều kiện -> THÀNH CÔNG
        success, msg, _ = safe_approve_job(job, admin_id=1, is_quick=True, audit_logger=mock_audit)
        self.assertTrue(success)
        self.assertEqual(job.status, "open")
        self.assertEqual(job.moderation_status, "approved")
        self.assertFalse(job.is_flagged)
        self.assertIsNotNone(job.moderated_at)
        self.assertEqual(job.moderated_by, 1)
        self.assertGreater(len(audit_logs), 0)
        self.assertEqual(audit_logs[0]['target_id'], 9998)

    # ═════════════════════════════════════════════════════════════════
    # 5. KIỂM THỬ ROUTE VÀ GIAO DIỆN /admin/tasks
    # ═════════════════════════════════════════════════════════════════
    def test_05_admin_tasks_endpoint_and_authorization(self):
        """Xác minh endpoint /admin/tasks phân quyền đúng và render đầy đủ giao diện."""
        # 1. Chưa đăng nhập Admin -> Bị chuyển hướng đăng nhập
        res_anon = self.client.get('/admin/tasks')
        self.assertEqual(res_anon.status_code, 302)

        # 2. Đã đăng nhập Super Admin -> Truy cập thành công (200 OK)
        self._login_admin(self.client)
        res_admin = self.client.get('/admin/tasks')
        self.assertEqual(res_admin.status_code, 200)

        html = res_admin.get_data(as_text=True)
        # Xác minh các khối UI chính: KPI Summary, Unified Filter, Mobile Cards
        self.assertIn("Trung tâm Tác vụ cần xử lý", html)
        self.assertIn("Bộ lọc tác vụ thống nhất", html)
        self.assertIn("Tổng tác vụ chờ xử lý", html)
        self.assertIn("Ưu tiên cao / Cảnh báo", html)

    # ═════════════════════════════════════════════════════════════════
    # 6. KIỂM THỬ RESPONSIVE MOBILE STICKY ACTION BAR TRONG REVIEW
    # ═════════════════════════════════════════════════════════════════
    def test_06_mobile_sticky_action_bar_responsive_css(self):
        """Xác minh templates/admin_job_review.html đã được sửa dứt điểm lỗi left: var(--sidebar-w) trên mobile."""
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'admin_job_review.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Phải có lớp sticky-review-bar và responsive media query
        self.assertIn("sticky-review-bar", content)
        self.assertIn("@media (max-width: 768px)", content)
        self.assertIn("left: 0 !important;", content)

if __name__ == '__main__':
    unittest.main()
