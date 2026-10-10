import unittest
import json
from datetime import datetime

from app import app
from models import (
    db,
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument,
    VerificationSubmissionVersion
)
from services.verification import (
    get_translator_verification_status_details,
    save_verification_draft,
    submit_verification_for_review
)


class VerificationStatusTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # 1. Tạo hoặc lấy Translator User
        self.translator = User.query.filter_by(email='trans_status_test@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Trần Minh Tuấn',
                email='trans_status_test@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0912345678',
                role='translator'
            )
            db.session.add(self.translator)
            db.session.commit()

        # 2. Tạo hoặc lấy Client/Hirer User
        self.hirer = User.query.filter_by(email='hirer_status_test@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Tập Đoàn Công Nghệ',
                email='hirer_status_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='client'
            )
            db.session.add(self.hirer)
            db.session.commit()

        # Dọn dẹp dữ liệu cũ của translator
        self._clean_data()

    def tearDown(self):
        self._clean_data()
        self.ctx.pop()

    def _clean_data(self):
        VerificationSubmissionVersion.query.filter_by(user_id=self.translator.id).delete()
        VerificationDocument.query.filter_by(user_id=self.translator.id).delete()
        TranslatorVerification.query.filter_by(user_id=self.translator.id).delete()
        if self.translator.profile:
            self.translator.profile.is_verified = False
        db.session.commit()

    def test_unauthenticated_access_redirects_to_login(self):
        """Khách vãng lai chưa đăng nhập phải bị chuyển hướng tới trang đăng nhập."""
        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

        # API cũng bị từ chối
        api_resp = self.client.get('/api/account/verification/status')
        self.assertEqual(api_resp.status_code, 302)

    def test_non_translator_forbidden(self):
        """Tài khoản không phải phiên dịch viên (hirer/client) không được truy cập trang theo dõi xác minh."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.hirer.id

        resp = self.client.get('/account/verification/status', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/account', resp.headers['Location'])

        # API trả về 403 Forbidden
        api_resp = self.client.get('/api/account/verification/status')
        self.assertEqual(api_resp.status_code, 403)
        api_data = json.loads(api_resp.data)
        self.assertFalse(api_data['success'])

    def test_status_not_started(self):
        """Trạng thái khi người dùng chưa khởi tạo hồ sơ (Empty State)."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Chưa khởi tạo hồ sơ', content)
        self.assertIn('Bắt đầu khai báo hồ sơ ngay', content)

        # Kiểm tra service trả về not_started
        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'not_started')
        self.assertEqual(details['status_label'], 'Chưa khởi tạo hồ sơ')
        self.assertIsNone(details['timestamps']['submitted_at'])

    def test_status_draft(self):
        """Trạng thái hồ sơ bản nháp đang soạn thảo."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='draft',
            current_step=3,
            full_name='Trần Minh Tuấn',
            phone='0912345678',
            gender='male',
            dob='1990-01-01',
            location='Hà Nội',
            bio='Phiên dịch viên tiếng Anh có kinh nghiệm dịch hội nghị hơn 6 năm.'
        )
        db.session.add(verif)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Bản nháp đang lưu', content)
        self.assertIn('Tiếp tục hoàn thiện Bước 3/6', content)
        self.assertIn('Trần Minh Tuấn', content)

        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'draft')
        self.assertEqual(details['steps_progress'][0]['status'], 'completed')  # Bước 1 hoàn thành
        self.assertEqual(details['steps_progress'][1]['status'], 'not_started') # Bước 2 chưa nhập
        self.assertIsNone(details['timestamps']['submitted_at'])  # Không tự suy đoán ngày gửi

    def test_status_pending(self):
        """Trạng thái hồ sơ đã gửi và đang chờ Admin duyệt."""
        now = datetime.utcnow()
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='pending',
            current_step=6,
            full_name='Trần Minh Tuấn',
            phone='0912345678',
            source_language='Tiếng Anh',
            target_language='Tiếng Việt',
            primary_language='Tiếng Anh ➔ Tiếng Việt',
            submission_version=1,
            submitted_at=now
        )
        db.session.add(verif)
        db.session.commit()

        # Tạo 1 submission version
        sub = VerificationSubmissionVersion(
            verification_id=verif.id,
            user_id=self.translator.id,
            version_number=1,
            status='pending',
            snapshot_data=json.dumps({
                'version': 1,
                'user': {'name': 'Trần Minh Tuấn'},
                'form_data': {'source_language': 'Tiếng Anh', 'target_language': 'Tiếng Việt'}
            }),
            submitted_at=now
        )
        db.session.add(sub)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Đang chờ xét duyệt', content)
        self.assertIn('Phiên bản v1', content)
        self.assertIn('Xem lại thông tin hồ sơ đã gửi', content)

        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'pending')
        self.assertIsNotNone(details['timestamps']['submitted_at'])
        self.assertEqual(len(details['submission_history']), 1)

    def test_status_needs_revision_with_admin_feedback(self):
        """Trạng thái hồ sơ cần bổ sung theo yêu cầu Admin."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='needs_revision',
            rejection_reason='Ảnh chứng chỉ IELTS bị mờ, vui lòng chụp lại bản gốc có dấu đỏ.',
            current_step=6
        )
        db.session.add(verif)
        db.session.flush()

        # Đính kèm 1 tài liệu bị reject
        doc = VerificationDocument(
            verification_id=verif.id,
            user_id=self.translator.id,
            document_type='certificate',
            original_filename='ielts_blurry.jpg',
            stored_filename='pdoc_certificate_test.jpg',
            storage_path='/tmp/pdoc_test.jpg',
            file_size=204800,
            mime_type='image/jpeg',
            file_extension='jpg',
            status='rejected',
            review_notes='Ảnh bị mờ góc dưới bên phải, không đọc được số hiệu ID.',
            is_active=True
        )
        db.session.add(doc)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Cần bổ sung hồ sơ', content)
        self.assertIn('Ảnh chứng chỉ IELTS bị mờ', content)
        self.assertIn('Ảnh bị mờ góc dưới bên phải', content)
        self.assertIn('ielts_blurry.jpg', content)

        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'needs_revision')
        self.assertTrue(details['admin_feedback']['has_revision_request'])
        self.assertEqual(len(details['admin_feedback']['rejected_documents']), 1)

    def test_status_verified(self):
        """Trạng thái hồ sơ đã xác minh thành công (Tích xanh)."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='approved',
            certificate_type='IELTS',
            certificate_name='IELTS 8.5',
            primary_language='Tiếng Anh ➔ Tiếng Việt'
        )
        db.session.add(verif)
        
        prof = self.translator.profile
        if not prof:
            prof = TranslatorProfile(user_id=self.translator.id)
            db.session.add(prof)
        prof.is_verified = True
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Đã xác minh chính thức', content)
        self.assertIn('Tích xanh', content)
        self.assertIn(f'/translator/{self.translator.id}', content)

        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'verified')
        self.assertEqual(details['next_action']['type'], 'verified')

    def test_status_rejected(self):
        """Trạng thái hồ sơ bị từ chối kèm lý do từ Admin."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='rejected',
            rejection_reason='Chứng chỉ không nằm trong danh mục công nhận hoặc không thể xác minh với tổ chức cấp bằng.'
        )
        db.session.add(verif)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/status')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Hồ sơ bị từ chối', content)
        self.assertIn('Lý do từ chối từ Ban quản trị', content)
        self.assertIn('Chứng chỉ không nằm trong danh mục công nhận', content)

        details = get_translator_verification_status_details(self.translator)
        self.assertEqual(details['overall_state'], 'rejected')
        self.assertEqual(details['admin_feedback']['rejection_reason'], verif.rejection_reason)

    def test_api_status_endpoint(self):
        """Kiểm tra API /api/account/verification/status trả về dữ liệu chuẩn JSON."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='draft',
            full_name='Trần Minh Tuấn',
            experience_years=5
        )
        db.session.add(verif)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        api_resp = self.client.get('/api/account/verification/status')
        self.assertEqual(api_resp.status_code, 200)
        res = json.loads(api_resp.data)
        self.assertTrue(res['success'])
        self.assertIn('data', res)
        d = res['data']
        self.assertEqual(d['user']['id'], self.translator.id)
        self.assertEqual(d['overall_state'], 'draft')
        self.assertEqual(len(d['steps_progress']), 6)
        self.assertIn('categories_data', d)
        self.assertIn('policy_checklist', d)


if __name__ == '__main__':
    unittest.main()
