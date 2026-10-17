from __future__ import annotations

import unittest
import json
from datetime import datetime, timedelta

from app import app
from models import (
    db,
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument,
    VerificationSubmissionVersion,
    AdminNotification,
    Notification,
    VERIFICATION_NOTIFICATION_TYPES,
    ADMIN_AUDIT_ACTIONS,
    AdminAuditLog
)
from services.verification import (
    send_verification_notification,
    sanitize_verification_message,
    request_policy_reverification,
    get_translator_verification_notifications,
    mark_verification_notification_read,
    mark_all_verification_notifications_read,
    submit_verification_for_review,
    review_verification_request,
    resubmit_verification
)


class VerificationNotificationsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # 1. Tạo hoặc lấy Translator User
        self.translator = User.query.filter_by(email='trans_notif_test@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Vũ Hoàng Long',
                email='trans_notif_test@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0988776655',
                role='translator'
            )
            db.session.add(self.translator)
            db.session.commit()

        # 2. Tạo hoặc lấy Hirer User (non-translator)
        self.hirer = User.query.filter_by(email='hirer_notif_test@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Công ty Dịch Thuật Toàn Cầu',
                email='hirer_notif_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='client'
            )
            db.session.add(self.hirer)
            db.session.commit()

        # 3. Tạo hoặc lấy Admin User
        self.admin = User.query.filter_by(email='admin_notif_test@example.com').first()
        if not self.admin:
            self.admin = User(
                name='Ban Quản Trị Viên',
                email='admin_notif_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='admin'
            )
            db.session.add(self.admin)
            db.session.commit()

        # 4. Người dùng translator thứ 2 (để test quyền hạn không đọc chéo)
        self.translator2 = User.query.filter_by(email='trans2_notif_test@example.com').first()
        if not self.translator2:
            self.translator2 = User(
                name='Nguyễn Thị Mai',
                email='trans2_notif_test@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0977665544',
                role='translator'
            )
            db.session.add(self.translator2)
            db.session.commit()

        self._clean_data()

    def tearDown(self):
        self._clean_data()
        self.ctx.pop()

    def _clean_data(self):
        Notification.query.filter(Notification.user_id.in_([self.translator.id, self.translator2.id])).delete()
        VerificationSubmissionVersion.query.filter(VerificationSubmissionVersion.user_id.in_([self.translator.id, self.translator2.id])).delete()
        VerificationDocument.query.filter(VerificationDocument.user_id.in_([self.translator.id, self.translator2.id])).delete()
        TranslatorVerification.query.filter(TranslatorVerification.user_id.in_([self.translator.id, self.translator2.id])).delete()
        if self.translator.profile:
            self.translator.profile.is_verified = False
        if self.translator2.profile:
            self.translator2.profile.is_verified = False
        db.session.commit()

    def _create_base_verification(self, user=None, status='pending'):
        u = user or self.translator
        v = TranslatorVerification(
            user_id=u.id,
            full_name=u.name,
            phone='0988776655',
            source_language='vi',
            target_language='en',
            interpreting_direction='two_way',
            language_proficiency='native',
            specializations='["business", "tech"]',
            interpreting_types='["simultaneous"]',
            education_level='bachelor',
            certificate_type='IELTS',
            certificate_name='IELTS 8.0',
            experience_years=5,
            notes='Kinh nghiệm hội nghị quốc tế.',
            status=status,
            submission_version=1,
            submitted_at=datetime.utcnow()
        )
        db.session.add(v)
        db.session.commit()
        return v

    # ─── 1. KIỂM THỬ TẠO 5 LOẠI THÔNG BÁO TỪ SỰ KIỆN THỰC TẾ ──────────────────────

    def test_01_event_submitted_notification(self):
        """Loại 1: Sự kiện hồ sơ đã được gửi và tiếp nhận (VERIFICATION_SUBMITTED)."""
        ok, notif, is_dup = send_verification_notification(
            user_id=self.translator.id,
            notif_type='VERIFICATION_SUBMITTED',
            title='Hồ sơ xác minh đã gửi thành công! ⏳',
            message='Hồ sơ của bạn (Phiên bản #1) đã được tiếp nhận và chuyển tới hàng đợi xét duyệt.',
            url='/account/verification/status',
            version=1
        )
        db.session.commit()

        self.assertTrue(ok)
        self.assertFalse(is_dup)
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, 'VERIFICATION_SUBMITTED')
        self.assertEqual(notif.user_id, self.translator.id)
        self.assertFalse(notif.is_read)
        self.assertIn('/account/verification/status', notif.url)
        self.assertIn('#1', notif.message)

    def test_02_event_needs_revision_notification(self):
        """Loại 2: Sự kiện Admin yêu cầu bổ sung (VERIFICATION_NEEDS_REVISION)."""
        verif = self._create_base_verification()

        ok, msg = review_verification_request(
            verification_id=verif.id,
            admin_user=self.admin,
            action='needs_revision',
            reason='Ảnh bằng tốt nghiệp bị lóa sáng, vui lòng bổ sung ảnh chụp rõ nét.'
        )
        self.assertTrue(ok)

        notif = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_NEEDS_REVISION'
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, 'VERIFICATION_NEEDS_REVISION')
        self.assertIn('bổ sung', notif.title.lower())
        self.assertIn('lóa sáng', notif.message)
        self.assertEqual(notif.url, '/account/verification/revision')
        self.assertFalse(notif.is_read)

    def test_03_event_approved_notification(self):
        """Loại 3: Sự kiện hồ sơ được xác minh (VERIFICATION_APPROVED)."""
        verif = self._create_base_verification()

        ok, msg = review_verification_request(
            verification_id=verif.id,
            admin_user=self.admin,
            action='approve'
        )
        self.assertTrue(ok)

        notif = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_APPROVED'
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, 'VERIFICATION_APPROVED')
        self.assertIn('xác minh thành công', notif.title.lower())
        self.assertEqual(notif.url, '/account/verification/status')
        self.assertFalse(notif.is_read)

    def test_04_event_rejected_notification(self):
        """Loại 4: Sự kiện hồ sơ bị từ chối (VERIFICATION_REJECTED)."""
        verif = self._create_base_verification()

        ok, msg = review_verification_request(
            verification_id=verif.id,
            admin_user=self.admin,
            action='reject',
            reason='Chứng chỉ không nằm trong danh mục chứng chỉ hợp lệ theo chính sách hiện hành.'
        )
        self.assertTrue(ok)

        notif = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_REJECTED'
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, 'VERIFICATION_REJECTED')
        self.assertIn('chưa được phê duyệt', notif.title)
        self.assertIn('chính sách hiện hành', notif.message)
        self.assertEqual(notif.url, '/account/verification/status')
        self.assertFalse(notif.is_read)

    def test_05_event_policy_update_required_notification(self):
        """Loại 5: Sự kiện hồ sơ cần cập nhật hoặc xác minh lại khi chính sách yêu cầu."""
        verif = self._create_base_verification(status='approved')

        ok, msg, notif = request_policy_reverification(
            translator_user=self.translator,
            reason='Chính sách nền tảng 2026: Yêu cầu chứng chỉ ngoại ngữ còn thời hạn dưới 2 năm.',
            policy_name='Chính sách năng lực 2026',
            admin_user=self.admin
        )
        self.assertTrue(ok)
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, 'VERIFICATION_POLICY_UPDATE_REQUIRED')
        self.assertIn('chính sách', notif.title.lower())
        self.assertIn('Chính sách năng lực 2026', notif.message)
        self.assertIn('/account/verification/revision', notif.url)
        self.assertFalse(notif.is_read)

        # Kiểm tra hồ sơ được cập nhật trạng thái
        updated_v = TranslatorVerification.query.get(verif.id)
        self.assertEqual(updated_v.status, 'needs_revision')

        # Kiểm tra Audit Log được ghi nhận
        audit = AdminAuditLog.query.filter_by(
            admin_id=self.admin.id,
            action=ADMIN_AUDIT_ACTIONS.get('REQUEST_POLICY_UPDATE', 'REQUEST_POLICY_UPDATE')
        ).first()
        self.assertIsNotNone(audit)

    # ─── 2. NGĂN CHẶN GỬI THÔNG BÁO TRÙNG LẶP (IDEMPOTENCY) ────────────────────────

    def test_06_prevent_duplicate_submission_notification(self):
        """Ngăn gửi trùng thông báo khi sự kiện nộp hồ sơ cùng phiên bản bị gửi lặp."""
        # Lần 1: Tạo mới thành công
        ok1, notif1, is_dup1 = send_verification_notification(
            user_id=self.translator.id,
            notif_type='VERIFICATION_SUBMITTED',
            message='Hồ sơ (Phiên bản #1) đã được tiếp nhận.',
            version=1
        )
        db.session.commit()
        self.assertTrue(ok1)
        self.assertFalse(is_dup1)

        # Lần 2: Gửi lặp cùng phiên bản #1
        ok2, notif2, is_dup2 = send_verification_notification(
            user_id=self.translator.id,
            notif_type='VERIFICATION_SUBMITTED',
            message='Hồ sơ (Phiên bản #1) đã được tiếp nhận.',
            version=1
        )
        self.assertFalse(ok2)
        self.assertTrue(is_dup2)
        self.assertEqual(notif1.id, notif2.id)

        # Tổng số bản ghi trong DB chỉ là 1
        count = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_SUBMITTED'
        ).count()
        self.assertEqual(count, 1)

    def test_07_prevent_duplicate_review_notifications(self):
        """Ngăn gửi lặp thông báo khi Admin bấm nút xét duyệt nhiều lần."""
        verif = self._create_base_verification()

        # Admin duyệt lần 1
        review_verification_request(
            verification_id=verif.id,
            admin_user=self.admin,
            action='needs_revision',
            reason='Thiếu CCCD mặt sau.'
        )

        # Admin submit lại form lần 2 cùng lý do
        review_verification_request(
            verification_id=verif.id,
            admin_user=self.admin,
            action='needs_revision',
            reason='Thiếu CCCD mặt sau.'
        )

        notifs = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_NEEDS_REVISION'
        ).all()
        self.assertEqual(len(notifs), 1)

    def test_08_prevent_duplicate_policy_update(self):
        """Ngăn gửi lặp yêu cầu cập nhật chính sách nếu thông báo chưa đọc đã tồn tại."""
        self._create_base_verification(status='approved')

        ok1, _, notif1 = request_policy_reverification(
            translator_user=self.translator,
            reason='Yêu cầu cập nhật định kỳ.'
        )
        self.assertTrue(ok1)

        # Gọi lại lần 2
        ok2, msg2, notif2 = request_policy_reverification(
            translator_user=self.translator,
            reason='Yêu cầu cập nhật định kỳ.'
        )
        self.assertTrue(ok2)
        self.assertIn('thông báo tương tự đã được gửi', msg2)
        self.assertEqual(notif1.id, notif2.id)

        count = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_POLICY_UPDATE_REQUIRED'
        ).count()
        self.assertEqual(count, 1)

    # ─── 3. BẢO MẬT: KHÔNG ĐƯA DỮ LIỆU NHẠY CẢM VÀO THÔNG BÁO ────────────────────

    def test_09_sanitize_sensitive_data_in_notification(self):
        """Kiểm tra loại bỏ số CCCD, đường dẫn tệp nội bộ và mã lỗi database."""
        raw_msg = (
            "Hồ sơ bị từ chối: Số CCCD 001234567890 lưu tại /tmp/private_verifications/doc_123.pdf "
            "gặp lỗi sqlite3.OperationalError: table locked."
        )
        cleaned = sanitize_verification_message(raw_msg)

        # Số CCCD phải được ẩn
        self.assertNotIn('001234567890', cleaned)
        self.assertIn('001****90', cleaned)

        # Đường dẫn tệp nội bộ không xuất hiện
        self.assertNotIn('/tmp/private_verifications/doc_123.pdf', cleaned)

        # Mã lỗi kỹ thuật DB không xuất hiện
        self.assertNotIn('sqlite3.OperationalError', cleaned)

    # ─── 4. HIỂN THỊ, TRẠNG THÁI VÀ ĐÁNH DẤU ĐÃ ĐỌC (API & UI) ────────────────────

    def test_10_api_get_notifications_and_filtering(self):
        """Kiểm tra API trả về danh sách, số lượng chưa đọc và các bộ lọc."""
        # Tạo 3 thông báo mẫu
        send_verification_notification(self.translator.id, 'VERIFICATION_SUBMITTED', 'Tiếp nhận hồ sơ #1', 'Nội dung 1', force=True)
        send_verification_notification(self.translator.id, 'VERIFICATION_NEEDS_REVISION', 'Bổ sung hồ sơ', 'Nội dung 2', force=True)
        send_verification_notification(self.translator.id, 'VERIFICATION_APPROVED', 'Đã duyệt hồ sơ', 'Nội dung 3', force=True)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        # 1. Lấy tất cả
        resp = self.client.get('/api/account/verification/notifications')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)['data']
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['unread_count'], 3)
        self.assertEqual(len(data['notifications']), 3)

        # 2. Lọc theo danh mục 'revision'
        resp_rev = self.client.get('/api/account/verification/notifications?category=revision')
        data_rev = json.loads(resp_rev.data)['data']
        self.assertEqual(len(data_rev['notifications']), 1)
        self.assertEqual(data_rev['notifications'][0]['type'], 'VERIFICATION_NEEDS_REVISION')

        # 3. Lọc theo danh mục 'approved'
        resp_app = self.client.get('/api/account/verification/notifications?category=approved')
        data_app = json.loads(resp_app.data)['data']
        self.assertEqual(len(data_app['notifications']), 1)
        self.assertEqual(data_app['notifications'][0]['type'], 'VERIFICATION_APPROVED')

    def test_11_mark_single_notification_read(self):
        """Kiểm tra đánh dấu đã đọc một thông báo qua API."""
        _, notif, _ = send_verification_notification(
            self.translator.id, 'VERIFICATION_SUBMITTED', 'Tiếp nhận #1', 'Nội dung', force=True
        )
        db.session.commit()
        self.assertFalse(notif.is_read)

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        # Đánh dấu đã đọc
        resp = self.client.post(f'/api/account/verification/notifications/{notif.id}/read')
        self.assertEqual(resp.status_code, 200)
        res_data = json.loads(resp.data)
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['unread_count'], 0)

        # Kiểm tra trong DB
        refreshed = Notification.query.get(notif.id)
        self.assertTrue(refreshed.is_read)

    def test_12_mark_all_notifications_read(self):
        """Kiểm tra đánh dấu tất cả thông báo xác minh là đã đọc."""
        send_verification_notification(self.translator.id, 'VERIFICATION_SUBMITTED', 'N1', 'M1', force=True)
        send_verification_notification(self.translator.id, 'VERIFICATION_NEEDS_REVISION', 'N2', 'M2', force=True)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.post('/api/account/verification/notifications/read-all')
        self.assertEqual(resp.status_code, 200)
        res_data = json.loads(resp.data)
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['updated_count'], 2)
        self.assertEqual(res_data['unread_count'], 0)

        unread_count = Notification.query.filter_by(
            user_id=self.translator.id, is_read=False
        ).count()
        self.assertEqual(unread_count, 0)

    # ─── 5. PHÂN QUYỀN VÀ TRUY CẬP AN TOÀN ──────────────────────────────────────

    def test_13_unauthorized_and_cross_user_access_prevented(self):
        """Không cho phép khách vãng lai, hirer, hoặc user đọc chéo thông báo của người khác."""
        # 1. Chưa đăng nhập
        resp = self.client.get('/account/verification/notifications')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

        # 2. Đăng nhập với tài khoản Hirer (phải bị từ chối)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.hirer.id

        resp_hirer = self.client.get('/account/verification/notifications')
        self.assertEqual(resp_hirer.status_code, 302)
        api_hirer = self.client.get('/api/account/verification/notifications')
        self.assertEqual(api_hirer.status_code, 403)

        # 3. Đọc chéo: Translator 2 không được đánh dấu đọc thông báo của Translator 1
        _, notif1, _ = send_verification_notification(
            self.translator.id, 'VERIFICATION_SUBMITTED', 'T1', 'M1', force=True
        )
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator2.id

        resp_cross = self.client.post(f'/api/account/verification/notifications/{notif1.id}/read')
        self.assertEqual(resp_cross.status_code, 400)
        res_cross = json.loads(resp_cross.data)
        self.assertFalse(res_cross['success'])

    def test_14_page_renders_successfully(self):
        """Trang giao diện trung tâm thông báo trả về mã 200 OK cho phiên dịch viên."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/notifications')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Thông báo Xác minh', resp.data.decode('utf-8'))
        self.assertIn('notif-loading', resp.data.decode('utf-8'))
        self.assertIn('notif-empty', resp.data.decode('utf-8'))
        self.assertIn('notif-error', resp.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
