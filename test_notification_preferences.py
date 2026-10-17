"""
test_notification_preferences.py
Bộ kiểm thử tính năng "Cài đặt thông báo" (Notification Preferences) trong Tab Cài đặt & Bảo mật.

Kiểm tra:
1. Mô hình NotificationSetting: các cột 4 nhóm cấu hình, giá trị mặc định, phương thức to_dict và alias properties.
2. Lưu và cập nhật cấu hình: Nhóm công việc, nhóm lịch trình (các mốc 60p, 30p, 15p), nhóm thu nhập.
3. Ràng buộc bảo mật: Nhóm Bảo mật & Hệ thống ("Cảnh báo đăng nhập lạ và bảo mật") luôn BẬT và KHÓA không cho tắt.
4. Kiểm tra điều kiện cờ (flag): create_notification kiểm tra NotificationSetting trước khi ghi vào Notification Center.
5. API /api/account/notification-settings: Lấy và cập nhật cấu hình qua JSON.
6. Giao diện form POST /account/profile với action='save_notification_settings'.
"""

import unittest
from app import app, db, create_notification, is_notification_allowed, get_user_notification_setting
from models import User, NotificationSetting, Notification
from werkzeug.security import generate_password_hash


class TestNotificationPreferences(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Tạo người dùng kiểm thử
        self.user = User(
            name='Nguyễn Văn Phiên Dịch',
            email='test_notif_pref@example.com',
            password_hash='pbkdf2:sha256:dummy_test_hash',
            role='translator'
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        # Dọn dẹp dữ liệu kiểm thử
        try:
            Notification.query.filter_by(user_id=self.user.id).delete()
            NotificationSetting.query.filter_by(user_id=self.user.id).delete()
            User.query.filter_by(id=self.user.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
        self.app_context.pop()

    def test_01_model_defaults_and_structure(self):
        """Kiểm tra khởi tạo mô hình NotificationSetting và các giá trị mặc định của 4 nhóm cấu hình."""
        setting = get_user_notification_setting(self.user)
        self.assertIsNotNone(setting)
        self.assertEqual(setting.user_id, self.user.id)

        # 1. Nhóm Công việc
        self.assertTrue(setting.notify_job_match)
        self.assertTrue(setting.notify_application_update)
        self.assertTrue(setting.notify_profile_view)

        # 2. Nhóm Lịch trình
        self.assertTrue(setting.notify_schedule_reminder)
        self.assertTrue(setting.reminder_time_60m)
        self.assertTrue(setting.reminder_time_30m)
        self.assertFalse(setting.reminder_time_15m)
        self.assertTrue(setting.reminder_60m)
        self.assertTrue(setting.reminder_30m)
        self.assertFalse(setting.reminder_15m)

        # 3. Nhóm Thu nhập
        self.assertTrue(setting.notify_income_update)
        self.assertTrue(setting.notify_payout)

        # 4. Nhóm Bảo mật & Hệ thống
        self.assertTrue(setting.notify_security_alert)

        # Kiểm tra to_dict()
        data = setting.to_dict()
        self.assertEqual(data['user_id'], self.user.id)
        self.assertTrue(data['notify_job_match'])
        self.assertTrue(data['notify_application_update'])
        self.assertTrue(data['notify_profile_view'])
        self.assertTrue(data['notify_schedule_reminder'])
        self.assertTrue(data['reminder_time_60m'])
        self.assertTrue(data['reminder_time_30m'])
        self.assertFalse(data['reminder_time_15m'])
        self.assertTrue(data['notify_income_update'])
        self.assertTrue(data['notify_security_alert'])

    def test_02_update_preferences_persistence(self):
        """Kiểm tra việc lưu và cập nhật các nhóm cấu hình vào CSDL."""
        setting = get_user_notification_setting(self.user)

        # Thay đổi một số tùy chọn
        setting.notify_job_match = False
        setting.notify_profile_view = False
        setting.reminder_time_60m = False
        setting.reminder_time_15m = True
        setting.notify_income_update = False
        db.session.commit()

        # Tải lại từ DB
        reloaded = NotificationSetting.query.filter_by(user_id=self.user.id).first()
        self.assertFalse(reloaded.notify_job_match)
        self.assertTrue(reloaded.notify_application_update)
        self.assertFalse(reloaded.notify_profile_view)
        self.assertTrue(reloaded.notify_schedule_reminder)
        self.assertFalse(reloaded.reminder_time_60m)
        self.assertTrue(reloaded.reminder_time_30m)
        self.assertTrue(reloaded.reminder_time_15m)
        self.assertFalse(reloaded.notify_income_update)
        self.assertTrue(reloaded.notify_security_alert)

    def test_03_security_alert_always_locked_on(self):
        """Kiểm tra Nhóm Bảo mật & Hệ thống luôn BẬT và không cho phép tắt."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        # Gửi request cố gắng tắt bảo mật
        resp = self.client.post('/api/account/notification-settings', json={
            'notify_security_alert': False,
            'field': 'notify_security_alert',
            'value': False
        })
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra giá trị trong DB vẫn phải là True
        setting = NotificationSetting.query.filter_by(user_id=self.user.id).first()
        self.assertTrue(setting.notify_security_alert)

    def test_04_create_notification_flag_checks(self):
        """Kiểm tra cấu hình NotificationSetting làm cờ kiểm tra (flag) trước khi tạo thông báo."""
        setting = get_user_notification_setting(self.user)

        # 1. Nhóm Công việc: Bật/Tắt "Job mới phù hợp tiêu chí"
        setting.notify_job_match = False
        db.session.commit()
        self.assertFalse(is_notification_allowed(self.user.id, 'JOB_MATCH'))
        notif_blocked = create_notification(self.user.id, 'JOB_MATCH', 'Việc mới', 'Có việc mới cho bạn')
        self.assertIsNone(notif_blocked)
        self.assertEqual(Notification.query.filter_by(user_id=self.user.id, type='JOB_MATCH').count(), 0)

        setting.notify_job_match = True
        db.session.commit()
        self.assertTrue(is_notification_allowed(self.user.id, 'JOB_MATCH'))
        notif_allowed = create_notification(self.user.id, 'JOB_MATCH', 'Việc mới', 'Có việc mới cho bạn')
        self.assertIsNotNone(notif_allowed)
        self.assertEqual(Notification.query.filter_by(user_id=self.user.id, type='JOB_MATCH').count(), 1)

        # 2. Nhóm Công việc: Bật/Tắt "Trạng thái đơn ứng tuyển"
        setting.notify_application_update = False
        db.session.commit()
        self.assertFalse(is_notification_allowed(self.user.id, 'PROPOSAL_ACCEPTED'))
        self.assertIsNone(create_notification(self.user.id, 'PROPOSAL_ACCEPTED', 'Chấp nhận', 'Đơn được duyệt'))

        setting.notify_application_update = True
        db.session.commit()
        self.assertIsNotNone(create_notification(self.user.id, 'PROPOSAL_ACCEPTED', 'Chấp nhận', 'Đơn được duyệt'))

        # 3. Nhóm Công việc: Bật/Tắt "Khách đã xem hồ sơ"
        setting.notify_profile_view = False
        db.session.commit()
        self.assertFalse(is_notification_allowed(self.user.id, 'PROFILE_VIEW'))
        self.assertIsNone(create_notification(self.user.id, 'PROFILE_VIEW', 'Lượt xem', 'Khách đã xem hồ sơ'))

        setting.notify_profile_view = True
        db.session.commit()
        self.assertIsNotNone(create_notification(self.user.id, 'PROFILE_VIEW', 'Lượt xem', 'Khách đã xem hồ sơ'))

        # 4. Nhóm Lịch trình: Bật/Tắt "Nhắc lịch ca dịch sắp tới"
        setting.notify_schedule_reminder = False
        db.session.commit()
        self.assertFalse(is_notification_allowed(self.user.id, 'SCHEDULE_REMINDER'))
        self.assertIsNone(create_notification(self.user.id, 'SCHEDULE_REMINDER', 'Nhắc lịch', 'Ca dịch 10h'))

        setting.notify_schedule_reminder = True
        db.session.commit()
        self.assertIsNotNone(create_notification(self.user.id, 'SCHEDULE_REMINDER', 'Nhắc lịch', 'Ca dịch 10h'))

        # 5. Nhóm Thu nhập: Bật/Tắt "Cập nhật thù lao và giải ngân"
        setting.notify_income_update = False
        db.session.commit()
        self.assertFalse(is_notification_allowed(self.user.id, 'PAYMENT'))
        self.assertIsNone(create_notification(self.user.id, 'PAYMENT', 'Thanh toán', 'Đã giải ngân tiền'))

        setting.notify_income_update = True
        db.session.commit()
        self.assertIsNotNone(create_notification(self.user.id, 'PAYMENT', 'Thanh toán', 'Đã giải ngân tiền'))

        # 6. Nhóm Bảo mật & Hệ thống: Luôn cho phép tạo thông báo
        self.assertTrue(is_notification_allowed(self.user.id, 'SECURITY_ALERT'))
        self.assertIsNotNone(create_notification(self.user.id, 'SECURITY_ALERT', 'Bảo mật', 'Cảnh báo đăng nhập lạ'))

    def test_05_api_endpoints(self):
        """Kiểm tra API /api/account/notification-settings (GET và POST JSON)."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        # GET settings
        get_res = self.client.get('/api/account/notification-settings')
        self.assertEqual(get_res.status_code, 200)
        json_data = get_res.get_json()
        self.assertTrue(json_data['success'])
        self.assertIn('settings', json_data)

        # POST update settings
        payload = {
            'notify_job_match': False,
            'notify_application_update': True,
            'notify_profile_view': False,
            'notify_schedule_reminder': True,
            'reminder_time_60m': True,
            'reminder_time_30m': False,
            'reminder_time_15m': True,
            'notify_income_update': False
        }
        post_res = self.client.post('/api/account/notification-settings', json=payload)
        self.assertEqual(post_res.status_code, 200)
        res_json = post_res.get_json()
        self.assertTrue(res_json['success'])
        self.assertFalse(res_json['settings']['notify_job_match'])
        self.assertFalse(res_json['settings']['notify_profile_view'])
        self.assertTrue(res_json['settings']['reminder_time_15m'])
        self.assertFalse(res_json['settings']['reminder_time_30m'])
        self.assertFalse(res_json['settings']['notify_income_update'])
        self.assertTrue(res_json['settings']['notify_security_alert'])

    def test_06_account_profile_form_submission(self):
        """Kiểm tra form submit action='save_notification_settings' trong /account/profile."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        form_data = {
            'action': 'save_notification_settings',
            'notify_job_match': '1',
            'notify_application_update': '1',
            'notify_schedule_reminder': '1',
            'reminder_time_60m': '1',
            'reminder_time_30m': '1'
            # notify_profile_view, reminder_time_15m, notify_income_update bị bỏ chọn (unchecked)
        }

        resp = self.client.post('/account/profile', data=form_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra giá trị lưu trong DB
        setting = NotificationSetting.query.filter_by(user_id=self.user.id).first()
        self.assertTrue(setting.notify_job_match)
        self.assertTrue(setting.notify_application_update)
        self.assertFalse(setting.notify_profile_view)
        self.assertTrue(setting.notify_schedule_reminder)
        self.assertTrue(setting.reminder_time_60m)
        self.assertTrue(setting.reminder_time_30m)
        self.assertFalse(setting.reminder_time_15m)
        self.assertFalse(setting.notify_income_update)
        self.assertTrue(setting.notify_security_alert)


if __name__ == '__main__':
    unittest.main()
