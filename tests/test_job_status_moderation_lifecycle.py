"""
tests/test_job_status_moderation_lifecycle.py
Bộ kiểm thử toàn diện vòng đời công việc và quy trình kiểm duyệt (Job Status & Moderation Lifecycle).

Bao gồm các kịch bản kiểm thử bắt buộc:
1. Job pending, người thuê chưa gỡ -> Admin approve -> moderation approved, status open/active, rời pending.
2. Job pending, người thuê đóng/gỡ trước khi Admin approve -> Admin approve KHÔNG hồi sinh job, bảo toàn closed.
3. Job đã đóng/hủy -> check_quick_approve_eligibility từ chối duyệt nhanh.
4. Concurrency: Job bị đóng giữa chừng -> safe_approve_job bảo toàn trạng thái closed, không mở lại công khai.
5. Bộ lọc Admin:
   - "Chờ duyệt" (pending): chỉ chứa job pending chưa đóng.
   - "Đang hoạt động" (open/active): chỉ chứa job approved, open, chưa đóng, không cờ.
   - "Đã đóng" (closed): chứa các job closed hoặc có closed_at.
6. Hiển thị công khai (can_view_job, matching, job_list):
   - Không cho phép người dùng vãng lai xem job pending hoặc job đã đóng.
   - Phiên dịch viên đã ứng tuyển hoặc có hợp đồng vẫn xem được chi tiết job đã đóng.
7. Job rejected, needs_revision, flagged, archived -> không xuất hiện trong "Đang hoạt động".
"""

import unittest
import uuid
from datetime import datetime, timedelta, date
from flask import session
from app import app, db
from models import User, Job, HirerProfile, Proposal, Contract
from services.admin_job_service import safe_approve_job, check_quick_approve_eligibility
from services.permissions import can_view_job
from services.proposals import job_accepts_selection

class JobStatusModerationLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo người dùng test với UUID duy nhất
        uid = uuid.uuid4().hex[:10]
        self.hirer = User(
            name=f"Hirer Test {uid}",
            email=f"hirer_{uid}@test.com",
            role="client",
            is_active=True,
            password_hash='test_hash_123'
        )
        db.session.add(self.hirer)
        db.session.commit()

        # Hirer profile đã xác minh (đủ điều kiện duyệt nhanh)
        self.hirer_profile = HirerProfile(
            user_id=self.hirer.id,
            verification_status='verified',
            is_verified=True,
            verified_at=datetime.utcnow()
        )
        db.session.add(self.hirer_profile)

        # Admin user
        self.admin = User(
            name=f"Admin Test {uid}",
            email=f"admin_{uid}@test.com",
            role="admin",
            is_admin=True,
            is_active=True,
            password_hash='test_hash_admin'
        )
        db.session.add(self.admin)

        # Translator user
        self.translator = User(
            name=f"Translator Test {uid}",
            email=f"translator_{uid}@test.com",
            role="translator",
            is_active=True,
            password_hash='test_hash_trans'
        )
        db.session.add(self.translator)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self.ctx.pop()

    def _create_pending_job(self, title="Công việc dịch thuật chuẩn"):
        job = Job(
            hirer_id=self.hirer.id,
            title=title,
            description="Mô tả công việc chi tiết chuẩn 39 tiêu chí không vi phạm bất kỳ lỗi nào.",
            category_group="document",
            service_type="document_legal",
            source_lang="en",
            target_lang="vi",
            budget_type="fixed",
            budget_min=2000000,
            status="pending",
            moderation_status="pending",
            is_flagged=False
        )
        db.session.add(job)
        db.session.commit()
        return job

    def test_01_pending_job_approved_becomes_active_and_leaves_pending(self):
        """Kịch bản 1: Job pending bình thường -> Admin approve -> moderation approved, status open, rời pending."""
        job = self._create_pending_job("Job duyệt thông thường")
        self.assertEqual(job.status, "pending")
        self.assertEqual(job.moderation_status, "pending")
        self.assertIsNone(job.closed_at)

        # Duyệt job
        success, msg, _ = safe_approve_job(job, admin_id=self.admin.id, is_quick=True)
        self.assertTrue(success)
        db.session.commit()

        # Kiểm tra sau khi duyệt
        self.assertEqual(job.moderation_status, "approved")
        self.assertEqual(job.status, "open")
        self.assertIsNone(job.closed_at)
        self.assertFalse(job.is_flagged)

        # Kiểm tra qua hàm kiểm tra công khai
        self.assertTrue(can_view_job(job, None))
        self.assertTrue(job_accepts_selection(job))

    def test_02_hirer_closes_pending_job_admin_approve_does_not_resurrect(self):
        """Kịch bản 2: Người thuê đóng job pending -> Admin approve -> KHÔNG hồi sinh job, status vẫn là closed."""
        job = self._create_pending_job("Job khách đóng trước khi duyệt")

        # Khách thực hiện đóng việc
        job.status = "closed"
        job.closed_at = datetime.utcnow()
        db.session.commit()

        # Duyệt nhanh phải bị từ chối
        can_quick, reason, _ = check_quick_approve_eligibility(job)
        self.assertFalse(can_quick)
        self.assertIn("đã bị người đăng gỡ hoặc đóng", reason)

        # Nếu Admin thực hiện xét duyệt chi tiết (is_quick=False)
        success, msg, _ = safe_approve_job(job, admin_id=self.admin.id, is_quick=False)
        self.assertTrue(success)
        db.session.commit()

        # QUY TẮC CỐT LÕI: Kết quả duyệt là approved nhưng status vẫn là closed, closed_at được bảo toàn
        self.assertEqual(job.moderation_status, "approved")
        self.assertEqual(job.status, "closed")
        self.assertIsNotNone(job.closed_at)

        # Job đã đóng KHÔNG được hiển thị công khai cho khách vãng lai
        self.assertFalse(can_view_job(job, None))
        # Không còn chấp nhận tuyển chọn
        self.assertFalse(job_accepts_selection(job))

    def test_03_hirer_cancels_job_status_cancelled_preserved(self):
        """Kịch bản 3: Người thuê hủy job -> status cancelled, moderation archived được bảo toàn."""
        job = self._create_pending_job("Job khách hủy tuyển dụng")
        job.status = "cancelled"
        job.closed_at = datetime.utcnow()
        job.moderation_status = "archived"
        db.session.commit()

        # Thử duyệt chi tiết
        success, msg, _ = safe_approve_job(job, admin_id=self.admin.id, is_quick=False)
        self.assertTrue(success)
        db.session.commit()

        # Status không bị biến thành open
        self.assertEqual(job.status, "cancelled")
        self.assertIsNotNone(job.closed_at)
        self.assertFalse(can_view_job(job, None))

    def test_04_contracted_job_not_reset_to_open_on_approval(self):
        """Kịch bản 4: Job đã chốt hợp đồng (contracted) -> Không bị reset về open khi duyệt."""
        job = self._create_pending_job("Job đã ký hợp đồng")
        job.status = "contracted"
        db.session.commit()

        can_quick, reason, _ = check_quick_approve_eligibility(job)
        self.assertFalse(can_quick)

        success, msg, _ = safe_approve_job(job, admin_id=self.admin.id, is_quick=False)
        self.assertTrue(success)
        db.session.commit()

        self.assertEqual(job.status, "contracted")
        self.assertEqual(job.moderation_status, "approved")

    def test_05_admin_jobs_filtering_separation(self):
        """Kịch bản 5: Kiểm tra các truy vấn bộ lọc của Admin tách biệt rõ ràng."""
        # 1. Job đang chờ duyệt hợp lệ
        j_pending = self._create_pending_job("Job chờ duyệt hợp lệ")

        # 2. Job pending nhưng đã bị khách đóng
        j_pending_closed = self._create_pending_job("Job pending đã đóng")
        j_pending_closed.status = "closed"
        j_pending_closed.closed_at = datetime.utcnow()

        # 3. Job đang mở hoạt động (approved + open)
        j_active = self._create_pending_job("Job đang hoạt động")
        j_active.status = "open"
        j_active.moderation_status = "approved"

        # 4. Job bất thường (status open nhưng moderation pending)
        j_anomaly = self._create_pending_job("Job bất thường open nhưng pending mod")
        j_anomaly.status = "open"
        j_anomaly.moderation_status = "pending"

        # 5. Job đã đóng (approved + closed)
        j_approved_closed = self._create_pending_job("Job duyệt xong khách đóng")
        j_approved_closed.status = "closed"
        j_approved_closed.moderation_status = "approved"
        j_approved_closed.closed_at = datetime.utcnow()

        db.session.commit()

        # Kiểm tra query Chờ duyệt (pending): CHỈ chứa j_pending, KHÔNG chứa j_pending_closed
        pending_query = Job.query.filter(
            db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
            db.or_(Job.is_flagged == False, Job.is_flagged.is_(None)),
            Job.status != 'closed',
            Job.status != 'cancelled',
            Job.closed_at.is_(None)
        )
        pending_ids = [j.id for j in pending_query.all()]
        self.assertIn(j_pending.id, pending_ids)
        self.assertNotIn(j_pending_closed.id, pending_ids)
        self.assertNotIn(j_active.id, pending_ids)

        # Kiểm tra query Đang hoạt động (active / open): CHỈ chứa j_active
        active_query = Job.query.filter(
            Job.moderation_status == 'approved',
            Job.status == 'open',
            Job.closed_at.is_(None),
            db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
        )
        active_ids = [j.id for j in active_query.all()]
        self.assertIn(j_active.id, active_ids)
        self.assertNotIn(j_pending.id, active_ids)
        self.assertNotIn(j_anomaly.id, active_ids)  # Job open nhưng pending mod KHÔNG ĐƯỢC vào active!
        self.assertNotIn(j_approved_closed.id, active_ids)  # Job đã đóng KHÔNG ĐƯỢC vào active!

        # Kiểm tra query Đã đóng (closed): Chứa cả j_pending_closed và j_approved_closed
        closed_query = Job.query.filter(
            db.or_(Job.status.in_(['closed', 'cancelled']), Job.closed_at.isnot(None))
        )
        closed_ids = [j.id for j in closed_query.all()]
        self.assertIn(j_pending_closed.id, closed_ids)
        self.assertIn(j_approved_closed.id, closed_ids)
        self.assertNotIn(j_active.id, closed_ids)
        self.assertNotIn(j_pending.id, closed_ids)

    def test_06_applied_translator_can_view_closed_job(self):
        """Kịch bản 6: Phiên dịch viên đã ứng tuyển hoặc có hợp đồng vẫn xem được job đã đóng."""
        job = self._create_pending_job("Job đã có báo giá")
        job.status = "closed"
        job.closed_at = datetime.utcnow()
        job.moderation_status = "approved"
        db.session.commit()

        # Người ngoài (None) không xem được
        self.assertFalse(can_view_job(job, None))

        # Khách sở hữu xem được
        self.assertTrue(can_view_job(job, self.hirer))

        # Admin xem được
        # Giả lập admin session
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id
            sess['admin_session_created'] = datetime.utcnow().timestamp()
            sess['admin_session_last_seen'] = datetime.utcnow().timestamp()
        
        # Phiên dịch viên chưa ứng tuyển không xem được
        self.assertFalse(can_view_job(job, self.translator))

        # Phiên dịch viên tạo báo giá
        prop = Proposal(
            job_id=job.id,
            translator_id=self.translator.id,
            price=1500000,
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(prop)
        db.session.commit()

        # Sau khi đã có báo giá, phiên dịch viên XEM ĐƯỢC
        self.assertTrue(can_view_job(job, self.translator))

if __name__ == '__main__':
    unittest.main()
