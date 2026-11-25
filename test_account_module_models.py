"""
test_account_module_models.py
Kiểm thử tính toàn vẹn của Model và Schema cho phân hệ Tài khoản Phiên dịch viên (Mục V).
"""

import unittest
from datetime import datetime
from app import app, db
from models import (
    User, InterpreterService, InterpreterPreference, NotificationSetting,
    UserSession, SupportTicket, TranslatorVerification, VerificationDocument
)

class TestAccountModuleModels(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def test_01_user_extended_columns(self):
        """Kiểm tra các trường mở rộng trên bảng User."""
        test_email = 'test_acc_user@example.com'
        user = User.query.filter_by(email=test_email).first()
        if not user:
            user = User(
                name='Nguyễn Văn Test',
                email=test_email,
                password_hash='dummy_hash',
                role='translator',
                phone='0987654321',
                bio='Phiên dịch viên chuyên nghiệp tiếng Hàn - Việt.',
                date_of_birth='1995-08-15',
                city='Hà Nội',
                is_public_profile=True
            )
            db.session.add(user)
            db.session.commit()

        # Query lại và kiểm tra
        loaded = User.query.filter_by(email=test_email).first()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.bio, 'Phiên dịch viên chuyên nghiệp tiếng Hàn - Việt.')
        self.assertEqual(loaded.date_of_birth, '1995-08-15')
        self.assertEqual(loaded.city, 'Hà Nội')
        self.assertTrue(loaded.is_public_profile)

        # Cleanup
        db.session.delete(loaded)
        db.session.commit()

    def test_02_interpreter_service_crud_and_relationship(self):
        """Kiểm tra tạo và liên kết InterpreterService với User."""
        user = User(
            name='Trần Dịch Vụ',
            email='trans_service_test@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()

        service = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Hàn',
            target_lang='Tiếng Việt',
            interpreting_type='cabin',
            specialization='Kinh doanh & Thương mại',
            hourly_rate=500000.0,
            session_rate=3500000.0,
            currency='VND',
            is_active=True
        )
        db.session.add(service)
        db.session.commit()

        # Kiểm tra quan hệ
        self.assertEqual(len(user.interpreter_services), 1)
        self.assertEqual(user.interpreter_services[0].interpreting_type, 'cabin')
        self.assertEqual(user.interpreter_services[0].hourly_rate, 500000.0)

        # Cascade delete
        db.session.delete(user)
        db.session.commit()
        self.assertIsNone(InterpreterService.query.filter_by(id=service.id).first())

    def test_03_interpreter_preference_and_helpers(self):
        """Kiểm tra InterpreterPreference và các hàm helper danh sách."""
        user = User(
            name='Lê Tiêu Chí',
            email='trans_pref_test@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()

        pref = InterpreterPreference(
            user_id=user.id,
            work_mode='both',
            min_rate=300000.0,
            max_rate=800000.0,
            allow_outside_rate=True,
            available_hours='["Ca sáng", "Ca chiều"]'
        )
        pref.set_languages_list(['Tiếng Việt ➔ Tiếng Anh', 'Tiếng Việt ➔ Tiếng Nhật'])
        pref.set_specializations_list(['Công nghệ thông tin', 'Y tế'])
        pref.set_locations_list(['Hà Nội', 'Đà Nẵng'])
        db.session.add(pref)
        db.session.commit()

        # Query lại và kiểm tra
        loaded = InterpreterPreference.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(loaded)
        self.assertIn('Tiếng Việt ➔ Tiếng Anh', loaded.get_languages_list())
        self.assertIn('Y tế', loaded.get_specializations_list())
        self.assertIn('Hà Nội', loaded.get_locations_list())
        self.assertIn('Ca sáng', loaded.get_available_hours_list())
        self.assertTrue(loaded.allow_outside_rate)
        self.assertEqual(user.interpreter_preference.min_rate, 300000.0)
        
        pref_dict = loaded.to_dict()
        self.assertEqual(pref_dict['work_mode'], 'both')
        self.assertEqual(pref_dict['min_rate'], 300000.0)
        self.assertIn('Đà Nẵng', pref_dict['locations'])

        # Cleanup
        db.session.delete(user)
        db.session.commit()

    def test_04_notification_setting_crud(self):
        """Kiểm tra NotificationSetting và quan hệ 1-1 với User."""
        user = User(
            name='Phạm Thông Báo',
            email='user_notif_test@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()

        setting = NotificationSetting(
            user_id=user.id,
            notify_job_match=True,
            notify_schedule_reminder=True,
            notify_application_update=True,
            notify_marketing=False
        )
        db.session.add(setting)
        db.session.commit()

        self.assertIsNotNone(user.notification_setting)
        self.assertTrue(user.notification_setting.notify_job_match)
        self.assertFalse(user.notification_setting.notify_marketing)

        # Cleanup
        db.session.delete(user)
        db.session.commit()

    def test_05_user_session_management(self):
        """Kiểm tra UserSession và theo dõi phiên đăng nhập."""
        user = User(
            name='Vũ Phiên Đăng Nhập',
            email='user_session_test@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()

        sess = UserSession(
            user_id=user.id,
            session_id='sess_tok_abc_123',
            device_name='Chrome on MacOS',
            ip_address='127.0.0.1',
            is_current=True
        )
        db.session.add(sess)
        db.session.commit()

        self.assertEqual(len(user.user_sessions), 1)
        self.assertEqual(user.user_sessions[0].device_name, 'Chrome on MacOS')
        self.assertTrue(user.user_sessions[0].is_current)

        # Cleanup
        db.session.delete(user)
        db.session.commit()

    def test_06_support_ticket_creation(self):
        """Kiểm tra SupportTicket, sinh ticket_code và phân loại."""
        user = User(
            name='Đỗ Hỗ Trợ',
            email='user_ticket_test@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()

        code = f"TK-{int(datetime.utcnow().timestamp())}"
        ticket = SupportTicket(
            ticket_code=code,
            user_id=user.id,
            category='account_security',
            title='Yêu cầu hỗ trợ xác minh bảo mật hai lớp',
            description='Tôi muốn tìm hiểu thêm về cài đặt bảo mật.',
            status='open'
        )
        db.session.add(ticket)
        db.session.commit()

        loaded_ticket = SupportTicket.query.filter_by(ticket_code=code).first()
        self.assertIsNotNone(loaded_ticket)
        self.assertEqual(loaded_ticket.status, 'open')
        self.assertEqual(loaded_ticket.user.email, 'user_ticket_test@example.com')

        # Cleanup
        db.session.delete(user)
        db.session.commit()

    def test_07_verification_tables_untouched(self):
        """Bảo đảm các bảng và model xác minh (KYC) nguyên vẹn 100%."""
        self.assertTrue(hasattr(TranslatorVerification, 'rejection_reason'))
        self.assertTrue(hasattr(TranslatorVerification, 'status'))
        self.assertTrue(hasattr(VerificationDocument, 'storage_path'))
        self.assertTrue(hasattr(VerificationDocument, 'document_type'))

if __name__ == '__main__':
    unittest.main()
