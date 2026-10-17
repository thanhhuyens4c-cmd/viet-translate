"""
tests/test_hirer_verification_flow.py
Bộ kiểm thử toàn diện cho luồng xác minh người thuê (Hirer Verification)
và luồng kiểm duyệt Job (Job Moderation) theo chuẩn nghiệp vụ VietTranslate.
"""

import unittest
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, _apply_hirer_profile_form
from models import User, HirerProfile, Job, AdminAuditLog, AdminNotification
from services.hirer_verification import can_hirer_post_job, evaluate_hirer_criteria


class HirerVerificationFlowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        self.app_ctx = app.app_context()
        self.app_ctx.push()

    def tearDown(self):
        db.session.rollback()
        self.app_ctx.pop()

    def test_01_profile_completion_does_not_auto_verify(self):
        """Task 1.1: Điền đủ thông tin hợp lệ chỉ đưa hồ sơ vào trạng thái pending, KHÔNG tự động verified."""
        ts = int(datetime.utcnow().timestamp())
        user = User(
            name=f"Hirer Test {ts}",
            email=f"hirer_{ts}@example.com",
            role='hirer',
            is_active=True,
            password_hash='test_hash_123'
        )
        db.session.add(user)
        db.session.flush()

        profile = HirerProfile(user_id=user.id, verification_status='unverified', is_verified=False)
        db.session.add(profile)
        db.session.flush()

        form_data = {
            'account_type': 'individual',
            'full_name': 'Nguyen Van Hirer',
            'contact_phone': '0912345678',
            'location': 'Hà Nội',
            'hiring_field': ['Thương mại', 'Du lịch'],
            'hiring_languages': ['Tiếng Anh', 'Tiếng Nhật'],
            'hiring_services': ['Dịch tháp tùng', 'Dịch hội thảo'],
            'about': 'Giới thiệu nhu cầu thuê phiên dịch viên',
            'is_verified': 'true',  # Client giả mạo trường
            'verification_status': 'verified',  # Client giả mạo trường
        }

        class MockMultiDict(dict):
            def getlist(self, key):
                v = self.get(key, [])
                return v if isinstance(v, list) else [v]

        errors = _apply_hirer_profile_form(user, profile, MockMultiDict(form_data), {})
        self.assertEqual(errors, [], f"Form application failed: {errors}")

        # KHÔNG được tự động chuyển thành verified
        self.assertFalse(profile.is_verified, "LỖI: is_verified tự động bật True!")
        self.assertEqual(profile.verification_status, 'pending', "LỖI: verification_status không chuyển thành pending!")
        self.assertIsNone(profile.verified_at, "LỖI: verified_at tự động được sinh!")

        # Hirer ở trạng thái pending KHÔNG được quyền đăng job
        can_post, msg, _ = can_hirer_post_job(user)
        self.assertFalse(can_post, "LỖI: Hirer pending vẫn được phép đăng job!")
        self.assertIn('chờ Ban quản trị xét duyệt', msg)

    def test_02_needs_revision_profile_resubmission_goes_to_pending(self):
        """Task 1.5: Hồ sơ ở trạng thái needs_revision khi sửa form chỉ chuyển sang pending, không tự verified."""
        ts = int(datetime.utcnow().timestamp())
        user = User(
            name=f"Hirer Rev {ts}",
            email=f"hirer_rev_{ts}@example.com",
            role='hirer',
            is_active=True,
            password_hash='test_hash_123'
        )
        db.session.add(user)
        db.session.flush()

        profile = HirerProfile(
            user_id=user.id,
            verification_status='needs_revision',
            is_verified=False,
            rejection_reason='Vui lòng bổ sung SĐT bàn'
        )
        db.session.add(profile)
        db.session.flush()

        form_data = {
            'account_type': 'individual',
            'full_name': 'Nguyen Van Rev',
            'contact_phone': '0987654321',
            'location': 'Đà Nẵng',
            'hiring_field': ['Đàm phán / Thương mại'],
            'hiring_languages': ['Tiếng Anh'],
            'hiring_services': ['Dịch tháp tùng'],
            'about': 'Cập nhật lại thông tin',
        }

        class MockMultiDict(dict):
            def getlist(self, key):
                v = self.get(key, [])
                return v if isinstance(v, list) else [v]

        errors = _apply_hirer_profile_form(user, profile, MockMultiDict(form_data), {})
        self.assertEqual(errors, [])
        self.assertFalse(profile.is_verified)
        self.assertEqual(profile.verification_status, 'pending')

    def test_03_rejected_profile_cannot_self_verify_on_edit(self):
        """Task 1.5: Hồ sơ bị rejected không được tự động chuyển thành verified khi sửa form."""
        ts = int(datetime.utcnow().timestamp())
        user = User(
            name=f"Hirer Rej {ts}",
            email=f"hirer_rej_{ts}@example.com",
            role='hirer',
            is_active=True,
            password_hash='test_hash_123'
        )
        db.session.add(user)
        db.session.flush()

        profile = HirerProfile(
            user_id=user.id,
            verification_status='rejected',
            is_verified=False,
            rejection_reason='Vi phạm chính sách lừa đảo'
        )
        db.session.add(profile)
        db.session.flush()

        form_data = {
            'account_type': 'individual',
            'full_name': 'Nguyen Van Rej',
            'contact_phone': '0911223344',
            'location': 'Hải Phòng',
            'hiring_field': ['Đàm phán / Thương mại'],
            'hiring_languages': ['Tiếng Trung'],
            'hiring_services': ['Dịch tháp tùng'],
            'about': 'Sửa lại hồ sơ sau khi bị từ chối',
        }

        class MockMultiDict(dict):
            def getlist(self, key):
                v = self.get(key, [])
                return v if isinstance(v, list) else [v]

        errors = _apply_hirer_profile_form(user, profile, MockMultiDict(form_data), {})
        self.assertEqual(errors, [])
        self.assertFalse(profile.is_verified)
        self.assertEqual(profile.verification_status, 'rejected')

    def test_04_can_hirer_post_job_enforces_strict_admin_verification(self):
        """Task 2.1: can_hirer_post_job chỉ cho phép khi cả is_verified và verification_status='verified'."""
        user = User(name="Test Gate", email="gate@example.com", role='hirer', is_active=True, password_hash='test_hash_123')
        db.session.add(user)
        db.session.flush()

        # Case A: Chưa có profile
        can, msg, _ = can_hirer_post_job(user)
        self.assertFalse(can)

        # Case B: Profile unverified
        profile = HirerProfile(user_id=user.id, verification_status='unverified', is_verified=False)
        db.session.add(profile)
        db.session.flush()
        db.session.refresh(user)
        can, msg, _ = can_hirer_post_job(user)
        self.assertFalse(can)

        # Case C: Profile pending
        profile.verification_status = 'pending'
        profile.is_verified = False
        db.session.flush()
        can, msg, _ = can_hirer_post_job(user)
        self.assertFalse(can)
        self.assertIn('chờ Ban quản trị xét duyệt', msg)

        # Case D: Profile có is_verified=True nhưng status='revoked' (bất nhất dữ liệu)
        profile.is_verified = True
        profile.verification_status = 'revoked'
        db.session.flush()
        can, msg, _ = can_hirer_post_job(user)
        self.assertFalse(can, "LỖI: Trạng thái revoked nhưng is_verified=True vẫn cho qua!")

        # Case E: Profile được Admin duyệt hợp lệ (cả 2 cờ đều chuẩn)
        profile.is_verified = True
        profile.verification_status = 'verified'
        profile.verified_at = datetime.utcnow()
        db.session.flush()
        can, msg, _ = can_hirer_post_job(user)
        self.assertTrue(can, "LỖI: Hirer đã verified hợp lệ nhưng không được đăng job!")

    def test_05_admin_hirer_review_requires_explicit_action(self):
        """Task 1.4: Endpoint /admin/hirers/<id>/review từ chối request thiếu action hoặc action sai, không mặc định verify."""
        ts = int(datetime.utcnow().timestamp())
        hirer = User(name=f"Hirer Under Review {ts}", email=f"review_{ts}@example.com", role='hirer', is_active=True, password_hash='test_hash_123')
        db.session.add(hirer)
        db.session.flush()
        profile = HirerProfile(user_id=hirer.id, verification_status='pending', is_verified=False)
        db.session.add(profile)
        db.session.commit()

        # Tạo session admin
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['admin_role'] = 'super_admin'
            sess['admin_session_created'] = now_ts
            sess['admin_session_last_seen'] = now_ts
            sess['admin_csrf_token'] = 'valid_test_admin_csrf_token'

        # POST thiếu trường action -> phải bị từ chối, KHÔNG được tự verify
        res = self.client.post(
            f'/admin/hirers/{hirer.id}/review',
            data={'_csrf_token': 'valid_test_admin_csrf_token'},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)

        # Kiểm tra lại profile trong DB: vẫn là pending, không bị verify
        db.session.expire_all()
        re_check = HirerProfile.query.filter_by(user_id=hirer.id).first()
        self.assertEqual(re_check.verification_status, 'pending')
        self.assertFalse(re_check.is_verified)

    def test_06_job_creation_enters_moderation_queue(self):
        """Task 3 & 4: Khi job được lưu, moderation_status và status đều là pending, xuất hiện trong admin_jobs."""
        ts = int(datetime.utcnow().timestamp())
        hirer = User(name=f"Verified Hirer {ts}", email=f"vh_{ts}@example.com", role='hirer', is_active=True, password_hash='test_hash_123')
        db.session.add(hirer)
        db.session.flush()
        profile = HirerProfile(user_id=hirer.id, verification_status='verified', is_verified=True, verified_at=datetime.utcnow())
        db.session.add(profile)

        # Tạo job mới
        from app import _submit_for_moderation
        job = Job(
            hirer_id=hirer.id,
            title="Phiên dịch hội thảo thương mại quốc tế Việt - Nhật",
            description="Cần phiên dịch viên tiếng Nhật cabin cho hội thảo kinh tế 2 ngày tại Trung tâm Hội nghị Quốc gia.",
            source_lang="Tiếng Việt",
            target_lang="Tiếng Nhật",
            category_group="interpretation",
            service_type="conference",
            budget_type="fixed",
            budget_min=5000000
        )
        db.session.add(job)
        db.session.flush()

        _submit_for_moderation(job, hirer, is_new=True)
        db.session.commit()

        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.moderation_status, 'pending')
        self.assertEqual(job.submission_version, 1)
        self.assertIsNotNone(job.moderation_checklist_data)

        # Kiểm tra query admin_jobs pending
        all_pending_jobs = Job.query.filter(
            db.or_(Job.moderation_status == 'pending', db.and_(Job.status == 'pending', Job.moderation_status.is_(None))),
            db.or_(Job.is_flagged == False, Job.is_flagged.is_(None))
        ).all()
        self.assertIn(job.id, [j.id for j in all_pending_jobs])


if __name__ == '__main__':
    unittest.main()
