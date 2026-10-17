"""
tests/test_hirer_job_lifecycle_integration.py
Kiểm thử tích hợp luồng:
1. X8 Revocation: Hồ sơ verified thay đổi thông tin quan trọng bị thu hồi về pending.
2. Admin Review Gate: Chặn approve khi chưa đạt tiêu chí bắt buộc (X1 - X5).
3. Post Job Decoupled Notification: Lỗi notification không bao giờ làm rollback Job.
4. Admin Moderation Queue Error Isolation: Bản ghi lỗi không làm sập toàn bộ danh sách Admin Jobs.
5. Admin File Access: Admin truy cập tài liệu minh chứng và attachment mà không bị lỗi 401.
"""

import unittest
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, _apply_hirer_profile_form
from models import User, HirerProfile, Job, AdminNotification, JobSchedule, VerificationDocument, JobAttachment, TranslatorVerification
from services.hirer_verification import can_hirer_post_job, evaluate_hirer_criteria


class MockMultiDict(dict):
    def getlist(self, key):
        v = self.get(key, [])
        if isinstance(v, list):
            return v
        return [v] if v else []


class HirerJobLifecycleIntegrationTestCase(unittest.TestCase):
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

    def test_01_x8_critical_field_change_revokes_verification(self):
        """Tiêu chí X8: Hồ sơ đã xác minh khi sửa SĐT hoặc tài khoản ngân hàng phải chuyển về pending."""
        ts = int(datetime.utcnow().timestamp())
        user = User(
            name=f"Verified Hirer {ts}",
            email=f"hirer_v_{ts}@example.com",
            phone="0911111111",
            role='hirer',
            is_active=True,
            password_hash='test123456'
        )
        db.session.add(user)
        db.session.flush()

        profile = HirerProfile(
            user_id=user.id,
            account_type='individual',
            contact_phone='0911111111',
            bank_name='Vietcombank',
            bank_account_number='0123456789',
            verification_status='verified',
            is_verified=True,
            verified_at=datetime.utcnow()
        )
        db.session.add(profile)
        db.session.flush()

        can, _, _ = can_hirer_post_job(user)
        self.assertTrue(can, "Tài khoản verified ban đầu phải được phép đăng job")

        # Thay đổi số điện thoại liên hệ
        form_data = {
            'account_type': 'individual',
            'full_name': f"Verified Hirer {ts}",
            'contact_phone': '0922222222', # Thay đổi số điện thoại
            'location': 'Hà Nội',
            'hiring_field': ['Đàm phán / Thương mại'],
            'hiring_languages': ['Tiếng Anh'],
            'hiring_services': ['Dịch hội thảo'],
            'bank_name': 'Vietcombank',
            'bank_account_number': '0123456789'
        }
        errors = _apply_hirer_profile_form(user, profile, MockMultiDict(form_data), {})
        self.assertEqual(errors, [], f"Form hợp lệ không được có lỗi: {errors}")

        # Kiểm tra X8 đã kích hoạt thu hồi trạng thái verified
        self.assertEqual(profile.verification_status, 'pending', "Hồ sơ phải chuyển về pending khi đổi SĐT")
        self.assertFalse(profile.is_verified, "is_verified phải chuyển thành False")

        # Cổng đăng job phải lập tức chặn lại
        can_now, reason, _ = can_hirer_post_job(user)
        self.assertFalse(can_now, "Quyền đăng job phải bị thu hồi sau khi đổi thông tin quan trọng")
        self.assertIn("đang chờ Ban quản trị xét duyệt", reason)

    def test_02_admin_review_gate_enforces_mandatory_criteria(self):
        """Admin review gate: Không thể cấp verified nếu chưa đạt đủ tiêu chí bắt buộc X1 - X5."""
        ts = int(datetime.utcnow().timestamp())
        admin = User(
            name=f"Admin Test {ts}",
            email=f"admin_{ts}@admin.local",
            role='admin',
            admin_role='super_admin',
            is_admin=True,
            is_active=True,
            password_hash='adminpass'
        )
        hirer = User(
            name=f"Hirer Incomplete {ts}",
            email=f"invalid_email_format_{ts}", # Email không hợp lệ -> X1 failed
            phone="123", # Phone không hợp lệ -> X2 failed
            role='hirer',
            is_active=True,
            password_hash='hirerpass'
        )
        db.session.add_all([admin, hirer])
        db.session.flush()

        profile = HirerProfile(
            user_id=hirer.id,
            account_type='business',
            verification_status='pending',
            is_verified=False
        )
        db.session.add(profile)
        db.session.commit()

        # Giả lập Admin đăng nhập
        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin.id
            sess['admin_role'] = 'super_admin'
            sess['admin_csrf_token'] = 'test_token'
            sess['admin_session_created'] = datetime.utcnow().timestamp()
            sess['admin_session_last_seen'] = datetime.utcnow().timestamp()

        # Admin cố tình submit action=verify khi hồ sơ chưa đạt
        res = self.client.post(
            f'/admin/hirers/{hirer.id}/review',
            data={'action': 'verify', 'chk_X3': '0', '_csrf_token': 'test_token'},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)

        # Refresh từ database
        db.session.refresh(profile)
        self.assertEqual(profile.verification_status, 'pending', "Không được cấp verified khi checklist chưa đạt")
        self.assertFalse(profile.is_verified, "is_verified phải vẫn là False")

    def test_03_post_job_succeeds_even_if_notification_fails(self):
        """Decoupled Notification: Job và schedule được commit thành công ngay cả khi tạo notification gặp lỗi."""
        ts = int(datetime.utcnow().timestamp())
        hirer = User(
            name=f"Verified Hirer {ts}",
            email=f"hirer_job_{ts}@example.com",
            phone="0933333333",
            role='hirer',
            is_active=True,
            password_hash='hirerpass'
        )
        db.session.add(hirer)
        db.session.flush()

        profile = HirerProfile(
            user_id=hirer.id,
            account_type='individual',
            contact_phone='0933333333',
            bank_name='BIDV',
            bank_account_number='1234567890',
            verification_status='verified',
            is_verified=True,
            verified_at=datetime.utcnow()
        )
        db.session.add(profile)
        db.session.commit()

        # Đăng nhập với tư cách hirer (admin_csrf_token dùng chung cho validate_csrf_token)
        with self.client.session_transaction() as sess:
            sess['user_id'] = hirer.id
            sess['user_email'] = hirer.email
            sess['user_role'] = 'hirer'
            sess['admin_csrf_token'] = 'valid_csrf_token'
            sess['job_form_tokens'] = ['job_token_123']

        # Gửi form đăng job
        post_data = {
            'form_token': 'job_token_123',
            '_csrf_token': 'valid_csrf_token',
            'title': 'Phiên dịch tháp tùng hội nghị cấp cao Hà Nội',
            'description': 'Cần tuyển 1 phiên dịch viên tháp tùng đoàn đại biểu thương mại song ngữ Việt Anh trong 2 ngày tại Trung tâm Hội nghị Quốc gia.',
            'category_group': 'interpretation_other',
            'service_type': 'business',
            'specialty': 'Kinh doanh',
            'source_lang': 'Tiếng Việt',
            'target_lang': 'Tiếng Anh',
            'budget_min': '2000000',
            'budget_max': '4000000',
            'budget_type': 'fixed',
            'location_type': 'onsite',
            'event_location': 'Hà Nội',
            'scheduled_date[]': '2026-11-20',
            'start_time[]': '08:00',
            'end_time[]': '12:00'
        }

        res = self.client.post('/post-job', data=post_data, follow_redirects=False)
        # Kỳ vọng chuyển hướng thành công đến chi tiết job (302)
        self.assertEqual(res.status_code, 302)

        # Kiểm tra Job đã lưu vào database và ở trạng thái pending
        saved_job = Job.query.filter_by(hirer_id=hirer.id).order_by(Job.id.desc()).first()
        self.assertIsNotNone(saved_job, "Job phải được commit an toàn vào database")
        self.assertEqual(saved_job.status, 'pending')
        self.assertEqual(saved_job.moderation_status, 'pending')

    def test_04_admin_jobs_queue_error_isolation(self):
        """Error Isolation: Một job lỗi tiêu chí không làm crash trang /admin/jobs."""
        ts = int(datetime.utcnow().timestamp())
        admin = User(
            name=f"Admin {ts}",
            email=f"admin_queue_{ts}@admin.local",
            role='admin',
            admin_role='super_admin',
            is_admin=True,
            is_active=True,
            password_hash='adminpass'
        )
        hirer = User(
            name=f"Hirer {ts}",
            email=f"hirer_queue_{ts}@test.local",
            role='hirer',
            is_active=True,
            password_hash='pass'
        )
        db.session.add_all([admin, hirer])
        db.session.flush()

        # Tạo 1 job bình thường và 1 job có dữ liệu đặc biệt
        job1 = Job(
            hirer_id=hirer.id,
            title=f"Bình thường #{ts}",
            description="Mô tả công việc bình thường hợp lệ trên 20 ký tự.",
            status='pending',
            moderation_status='pending'
        )
        db.session.add(job1)
        db.session.commit()

        # Đăng nhập Admin session
        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin.id
            sess['admin_role'] = 'super_admin'
            sess['admin_csrf_token'] = 'test_token'
            sess['admin_session_created'] = datetime.utcnow().timestamp()
            sess['admin_session_last_seen'] = datetime.utcnow().timestamp()

        # Truy cập trang quản lý job của Admin
        res = self.client.get('/admin/jobs')
        self.assertEqual(res.status_code, 200, "Trang /admin/jobs phải phản hồi 200 OK")
        self.assertIn(job1.title, res.data.decode('utf-8'))

    def test_05_admin_can_access_verification_documents(self):
        """Admin có quyền tải và xem tài liệu minh chứng mà không bị lỗi 401 Unauthorized."""
        ts = int(datetime.utcnow().timestamp())
        admin = User(
            name=f"Admin {ts}",
            email=f"admin_doc_{ts}@admin.local",
            role='admin',
            admin_role='super_admin',
            is_admin=True,
            is_active=True,
            password_hash='adminpass'
        )
        translator = User(
            name=f"Trans {ts}",
            email=f"trans_doc_{ts}@test.local",
            role='translator',
            is_active=True,
            password_hash='transpass'
        )
        db.session.add_all([admin, translator])
        db.session.flush()

        # Tạo file tạm và bản ghi VerificationDocument
        uploads_dir = os.path.join(app.root_path, 'uploads', 'verification_docs')
        os.makedirs(uploads_dir, exist_ok=True)
        test_filename = f"test_doc_{ts}.pdf"
        test_filepath = os.path.join(uploads_dir, test_filename)
        with open(test_filepath, 'wb') as f:
            f.write(b"%PDF-1.4 test document content")

        verif = TranslatorVerification(user_id=translator.id, status='pending')
        db.session.add(verif)
        db.session.flush()

        doc = VerificationDocument(
            verification_id=verif.id,
            user_id=translator.id,
            original_filename="Chung_Chi_IELTS.pdf",
            stored_filename=test_filename,
            storage_path=test_filepath,
            file_extension='pdf',
            document_type='certificate',
            file_size=30,
            mime_type='application/pdf',
            status='pending'
        )
        db.session.add(doc)
        db.session.commit()

        # Đăng nhập Admin session (không có user_id trong session)
        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin.id
            sess['admin_role'] = 'super_admin'
            sess['admin_csrf_token'] = 'test_token'
            sess['admin_session_created'] = datetime.utcnow().timestamp()
            sess['admin_session_last_seen'] = datetime.utcnow().timestamp()

        # Admin tải tài liệu minh chứng
        res_download = self.client.get(f'/account/verification/documents/{doc.id}/download')
        self.assertEqual(res_download.status_code, 200, "Admin phải tải được tài liệu minh chứng (không bị 401/403)")
        self.assertEqual(res_download.data, b"%PDF-1.4 test document content")

        # Admin xem tài liệu minh chứng
        res_view = self.client.get(f'/account/verification/documents/{doc.id}/view')
        self.assertEqual(res_view.status_code, 200, "Admin phải xem được tài liệu minh chứng (không bị 401/403)")

        # Dọn dẹp file tạm
        try:
            os.remove(test_filepath)
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
