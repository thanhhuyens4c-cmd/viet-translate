"""
test_account_security.py
Bộ kiểm thử toàn diện tính năng "Bảo mật tài khoản" (Mục 5.6.2 & 5.6.3):
1. Đổi mật khẩu:
   - Validate mật khẩu mới tối thiểu 8 ký tự, có chữ hoa, số.
   - Kiểm tra đúng mật khẩu cũ qua đúng Auth provider hiện tại (werkzeug.security check_password_hash).
   - Trả về thông báo lỗi rõ ràng nếu nhập sai mật khẩu cũ hoặc không đủ điều kiện.
   - Cập nhật password_hash chính xác khi đổi thành công.
2. Quản lý phiên đăng nhập:
   - Hiển thị danh sách phiên từ bảng UserSession (Tên thiết bị, IP, thời gian hoạt động, tag "Phiên hiện tại").
   - Thu hồi token/hủy session thực sự ở backend:
     + Đăng xuất khỏi thiết bị này.
     + Đăng xuất tất cả thiết bị khác.
     + Kiểm tra cơ chế backend: Khi phiên bị xóa khỏi DB, request tiếp theo từ thiết bị đó bị thu hồi ngay lập tức.
3. Kiểm thử API JSON và Form POST.
"""

import unittest
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, db, get_current_user
from models import User, UserSession, Notification
from services.account_security import (
    validate_password_complexity,
    change_user_password,
    hash_password,
    parse_device_name,
    get_client_ip,
    register_user_session,
    get_active_sessions,
    revoke_user_session,
    revoke_all_other_sessions
)


class TestAccountSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Tạo người dùng kiểm thử
        self.initial_password = 'OldPassword123'
        self.user = User(
            name='Nguyễn Văn Bảo Mật',
            email=f'security_test_{uuid.uuid4().hex[:8]}@example.com',
            password_hash=hash_password(self.initial_password),
            role='translator'
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        try:
            UserSession.query.filter_by(user_id=self.user.id).delete()
            Notification.query.filter_by(user_id=self.user.id).delete()
            User.query.filter_by(id=self.user.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
        self.app_context.pop()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. KIỂM THỬ VALIDATE ĐỘ PHỨC TẠP MẬT KHẨU
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_password_complexity_validation(self):
        """Validate mật khẩu mới: tối thiểu 8 ký tự, có chữ hoa, số."""
        # Thiếu độ dài (< 8 ký tự)
        valid, msg = validate_password_complexity('Abc1')
        self.assertFalse(valid)
        self.assertIn("tối thiểu 8 ký tự", msg)

        # Thiếu chữ in hoa (chỉ có chữ thường và số)
        valid, msg = validate_password_complexity('password123')
        self.assertFalse(valid)
        self.assertIn("chữ cái in hoa", msg)

        # Thiếu chữ số (chỉ có chữ hoa và thường)
        valid, msg = validate_password_complexity('PasswordAbc')
        self.assertFalse(valid)
        self.assertIn("chữ số", msg)

        # Đạt đầy đủ tiêu chuẩn
        valid, msg = validate_password_complexity('ValidPass2026')
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. KIỂM THỬ NGHIỆP VỤ ĐỔI MẬT KHẨU
    # ─────────────────────────────────────────────────────────────────────────

    def test_02_change_password_incorrect_old_password(self):
        """Kiểm tra báo lỗi rõ ràng khi nhập sai mật khẩu cũ."""
        success, msg = change_user_password(
            user=self.user,
            old_password='WrongOldPassword999',
            new_password='NewValidPass123',
            confirm_password='NewValidPass123'
        )
        self.assertFalse(success)
        self.assertIn("Mật khẩu hiện tại không chính xác", msg)

        # Mật khẩu cũ vẫn không đổi
        self.assertTrue(check_password_hash(self.user.password_hash, self.initial_password))

    def test_03_change_password_mismatched_confirmation(self):
        """Kiểm tra báo lỗi khi xác nhận mật khẩu không khớp."""
        success, msg = change_user_password(
            user=self.user,
            old_password=self.initial_password,
            new_password='NewValidPass123',
            confirm_password='DifferentPass123'
        )
        self.assertFalse(success)
        self.assertIn("không trùng khớp", msg)

    def test_04_change_password_same_as_old(self):
        """Kiểm tra cảnh báo khi mật khẩu mới trùng mật khẩu cũ."""
        success, msg = change_user_password(
            user=self.user,
            old_password=self.initial_password,
            new_password=self.initial_password,
            confirm_password=self.initial_password
        )
        self.assertFalse(success)
        self.assertIn("không được trùng với mật khẩu hiện tại", msg)

    def test_05_change_password_success(self):
        """Đổi mật khẩu thành công và kiểm tra hash mật khẩu mới."""
        new_pw = 'NewSecurePass2026'
        success, msg = change_user_password(
            user=self.user,
            old_password=self.initial_password,
            new_password=new_pw,
            confirm_password=new_pw
        )
        self.assertTrue(success)
        self.assertIn("thành công", msg.lower())

        # Kiểm tra xác thực bằng đúng provider (check_password_hash)
        self.assertTrue(check_password_hash(self.user.password_hash, new_pw))
        self.assertFalse(check_password_hash(self.user.password_hash, self.initial_password))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. KIỂM THỬ QUẢN LÝ PHIÊN ĐĂNG NHẬP (USERSESSION)
    # ─────────────────────────────────────────────────────────────────────────

    def test_06_device_name_and_ip_parsing(self):
        """Kiểm tra phân tích chuỗi User-Agent và địa chỉ IP."""
        class MockRequest:
            def __init__(self, ua, ip):
                self.headers = {'User-Agent': ua, 'X-Forwarded-For': ip}
                self.remote_addr = '127.0.0.1'

        req_mac = MockRequest('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0', '118.69.182.45')
        self.assertEqual(parse_device_name(req_mac), 'Chrome trên macOS')
        self.assertEqual(get_client_ip(req_mac), '118.69.182.45')

        req_iphone = MockRequest('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1', '14.161.20.10')
        self.assertEqual(parse_device_name(req_iphone), 'Safari trên iPhone')

    def test_07_user_session_registration_and_listing(self):
        """Kiểm tra tạo bản ghi UserSession và phân định tag Phiên hiện tại."""
        sess1 = UserSession(
            user_id=self.user.id,
            session_id='token_device_1',
            device_name='Chrome trên macOS',
            ip_address='192.168.1.10',
            last_active=datetime.utcnow(),
            is_current=True
        )
        sess2 = UserSession(
            user_id=self.user.id,
            session_id='token_device_2',
            device_name='Safari trên iPhone',
            ip_address='14.161.20.10',
            last_active=datetime.utcnow(),
            is_current=False
        )
        db.session.add_all([sess1, sess2])
        db.session.commit()

        # Lấy danh sách phiên với current_token = 'token_device_1'
        sessions = get_active_sessions(self.user, current_session_token='token_device_1')
        self.assertEqual(len(sessions), 2)

        # Kiểm tra tag is_current
        sess1_dict = next(s for s in sessions if s['session_id'] == 'token_device_1')
        sess2_dict = next(s for s in sessions if s['session_id'] == 'token_device_2')

        self.assertTrue(sess1_dict['is_current'])
        self.assertFalse(sess2_dict['is_current'])
        self.assertEqual(sess1_dict['device_type'], 'desktop')
        self.assertEqual(sess2_dict['device_type'], 'mobile')

    def test_08_revoke_specific_session_backend(self):
        """Kiểm tra thu hồi phiên cụ thể thực sự bị xóa khỏi bảng UserSession ở backend."""
        sess1 = UserSession(
            user_id=self.user.id,
            session_id='token_current_dev',
            device_name='Chrome trên Windows',
            ip_address='127.0.0.1'
        )
        sess2 = UserSession(
            user_id=self.user.id,
            session_id='token_other_dev',
            device_name='Edge trên Android',
            ip_address='10.0.0.1'
        )
        db.session.add_all([sess1, sess2])
        db.session.commit()

        # Thu hồi thiết bị 2
        success, msg, is_cur = revoke_user_session(self.user.id, sess2.id, current_token='token_current_dev')
        self.assertTrue(success)
        self.assertFalse(is_cur)

        # Kiểm tra backend: sess2 không còn trong DB
        remaining = UserSession.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].session_id, 'token_current_dev')

    def test_09_revoke_all_other_sessions_backend(self):
        """Kiểm tra Đăng xuất tất cả thiết bị khác: giữ lại duy nhất phiên hiện tại."""
        sess_current = UserSession(
            user_id=self.user.id,
            session_id='token_keep_me',
            device_name='Chrome trên macOS',
            ip_address='127.0.0.1'
        )
        sess_other1 = UserSession(
            user_id=self.user.id,
            session_id='token_other_1',
            device_name='Safari trên iPhone',
            ip_address='113.1.2.3'
        )
        sess_other2 = UserSession(
            user_id=self.user.id,
            session_id='token_other_2',
            device_name='Firefox trên Linux',
            ip_address='113.1.2.4'
        )
        db.session.add_all([sess_current, sess_other1, sess_other2])
        db.session.commit()

        # Thực hiện thu hồi tất cả thiết bị khác
        success, msg, count = revoke_all_other_sessions(self.user.id, current_token='token_keep_me')
        self.assertTrue(success)
        self.assertEqual(count, 2)

        # Kiểm tra backend: chỉ còn duy nhất sess_current
        remaining = UserSession.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].session_id, 'token_keep_me')

    def test_10_backend_session_revocation_enforcement(self):
        """Kiểm tra cơ chế backend: khi token bị xóa, get_current_user() thu hồi session ngay lập tức."""
        revoked_token = 'token_revoked_at_backend'

        # Đưa vào cookie session nhưng không có trong UserSession (đã bị thu hồi)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['session_token'] = revoked_token

        # Gọi request đến route yêu cầu xác thực
        res = self.client.get('/account/profile')

        # get_current_user phát hiện token không tồn tại -> session bị clear -> redirect về login
        self.assertIn(res.status_code, (302, 401))
        self.assertTrue('/login' in res.location if res.status_code == 302 else True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. KIỂM THỬ API ENDPOINTS (JSON)
    # ─────────────────────────────────────────────────────────────────────────

    def test_11_api_change_password(self):
        """Kiểm thử API POST /api/account/change-password."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        # 1. Sai mật khẩu cũ -> 400
        res = self.client.post('/api/account/change-password', json={
            'old_password': 'IncorrectPassword',
            'new_password': 'ValidNewPass2026',
            'confirm_password': 'ValidNewPass2026'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Mật khẩu hiện tại không chính xác", data['message'])

        # 2. Thành công -> 200
        res_ok = self.client.post('/api/account/change-password', json={
            'old_password': self.initial_password,
            'new_password': 'ValidNewPass2026',
            'confirm_password': 'ValidNewPass2026'
        })
        self.assertEqual(res_ok.status_code, 200)
        data_ok = res_ok.get_json()
        self.assertTrue(data_ok['success'])

        # Xác thực mật khẩu trong DB
        u = User.query.get(self.user.id)
        self.assertTrue(check_password_hash(u.password_hash, 'ValidNewPass2026'))

    def test_12_api_sessions_and_revoke(self):
        """Kiểm thử các API /api/account/sessions và /api/account/sessions/revoke."""
        sess_token = 'api_tok_1'
        sess = UserSession(
            user_id=self.user.id,
            session_id=sess_token,
            device_name='Chrome trên macOS',
            ip_address='127.0.0.1'
        )
        db.session.add(sess)
        db.session.commit()

        with self.client.session_transaction() as client_sess:
            client_sess['user_id'] = self.user.id
            client_sess['session_token'] = sess_token

        # GET /api/account/sessions
        res = self.client.get('/api/account/sessions')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['total'], 1)

        # POST /api/account/sessions/revoke (thu hồi phiên)
        res_revoke = self.client.post('/api/account/sessions/revoke', json={
            'session_id': sess.id
        })
        self.assertEqual(res_revoke.status_code, 200)
        data_rev = res_revoke.get_json()
        self.assertTrue(data_rev['success'])

        # Xác nhận đã xóa khỏi DB
        self.assertIsNone(UserSession.query.get(sess.id))


if __name__ == '__main__':
    unittest.main()
