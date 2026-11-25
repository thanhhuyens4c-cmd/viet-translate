"""
test_subscription_tier.py
Bộ kiểm thử tự động cho Giao diện Quản lý "Gói dịch vụ & Quyền lợi" trong trang Tài khoản (Mục 5.5).

Các kịch bản kiểm tra:
1. Model User properties:
   - user.subscription_tier trả về 'standard'
   - user.subscription_info có duration 'Vô thời hạn', name 'Gói Tiêu Chuẩn (Free)', is_pro False
2. Trang Tài khoản (GET /account/profile?tab=subscription):
   - Trả về HTTP 200 OK.
   - Hiển thị đầy đủ khu vực trạng thái gói hiện tại (Tên gói, Thời hạn Vô thời hạn).
   - Hiển thị bảng so sánh quyền lợi 2 cột:
     + Cột Gói Tiêu Chuẩn (Free): Hồ sơ cơ bản, nhận thông báo việc làm thông thường.
     + Cột Gói Phiên Dịch Viên Chuyên Nghiệp (Pro): Đẩy hồ sơ lên đầu kết quả tìm kiếm, nhận thông báo việc mới tức thì, mở khóa kho lưu trữ thuật ngữ riêng.
   - Hiển thị nút [Đăng ký quan tâm / Sắp ra mắt].
   - Có Modal thông báo tính năng thử nghiệm và an toàn thanh toán.
3. Xử lý an toàn (POST /account/subscription/interest):
   - Đăng ký quan tâm trả về success: True.
   - TUYỆT ĐỐI KHÔNG lưu trạng thái thanh toán ảo hay tự động cấp Pro giả mạo.
"""

import unittest
import uuid
from app import app, db
from models import User, Notification, PaymentTransaction


class TestSubscriptionTier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

        uid_str = uuid.uuid4().hex[:8]
        self.user = User(
            name='Trần Phiên Dịch Viên',
            email=f'trans_tier_{uid_str}@test.com',
            password_hash='dummy_hash',
            role='translator',
            phone='0987654321',
            city='TP. Hồ Chí Minh',
            is_active=True
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        try:
            Notification.query.filter_by(user_id=self.user.id).delete()
            db.session.delete(self.user)
            db.session.commit()
        except Exception:
            db.session.rollback()
        self.app_context.pop()

    def test_01_user_subscription_properties(self):
        """Kiểm tra helper properties trên model User phục vụ Mục 5.5."""
        self.assertEqual(self.user.subscription_tier, 'standard')
        info = self.user.subscription_info
        self.assertIsInstance(info, dict)
        self.assertEqual(info['tier'], 'standard')
        self.assertIn('Gói Tiêu Chuẩn', info['name'])
        self.assertEqual(info['duration'], 'Vô thời hạn')
        self.assertEqual(info['expires_at_display'], 'Vô thời hạn')
        self.assertFalse(info['is_pro'])

    def test_02_account_profile_subscription_tab_renders(self):
        """Kiểm tra giao diện Tab 5.5 render đầy đủ các thành phần theo yêu cầu."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['_user_id'] = self.user.id

        resp = self.client.get('/account/profile?tab=subscription')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Khu vực hiển thị trạng thái hiện tại
        self.assertIn('Gói Dịch Vụ & Quyền Lợi', html)
        self.assertIn('Mục 5.5', html)
        self.assertIn('Gói Tiêu Chuẩn', html)
        self.assertIn('Vô thời hạn', html)

        # 2. Bảng so sánh quyền lợi (Pricing / Tier Table)
        # Cột Free
        self.assertIn('Gói Tiêu Chuẩn (Free)', html)
        self.assertIn('Hồ sơ cơ bản', html)
        self.assertIn('Nhận thông báo việc làm thông thường', html)
        self.assertIn('Gói hiện tại đang sử dụng', html)

        # Cột Pro
        self.assertIn('Phiên Dịch Viên Chuyên Nghiệp (Pro)', html)
        self.assertIn('Đẩy hồ sơ lên đầu kết quả tìm kiếm của khách hàng', html)
        self.assertIn('Nhận thông báo việc mới tức thì', html)
        self.assertIn('Mở khóa kho lưu trữ thuật ngữ riêng', html)

        # 3. Nút đăng ký quan tâm / Sắp ra mắt & Modal
        self.assertIn('Đăng ký quan tâm / Sắp ra mắt', html)
        self.assertIn('modal-subscription-interest', html)
        self.assertIn('Tính Năng Đang Thử Nghiệm', html)
        self.assertIn('VNPAY', html)
        self.assertIn('MoMo', html)

    def test_03_subscription_interest_safe_handling(self):
        """Kiểm tra xử lý đăng ký quan tâm an toàn: KHÔNG tạo thanh toán ảo, KHÔNG đổi status bừa bãi."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['_user_id'] = self.user.id

        # Kiểm tra trước khi gửi
        initial_payments_count = PaymentTransaction.query.filter_by(user_id=self.user.id).count()

        resp = self.client.post('/account/subscription/interest', json={
            'phone': '0987654321',
            'note': 'Tôi muốn dùng thử tính năng kho lưu trữ thuật ngữ y tế'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('ghi nhận', data.get('message', '').lower())

        # RÀNG BUỘC NGHIỆM NGẶT:
        # 1. Tuyệt đối không tạo bản ghi thanh toán giả lập
        new_payments_count = PaymentTransaction.query.filter_by(user_id=self.user.id).count()
        self.assertEqual(new_payments_count, initial_payments_count)

        # 2. Gói tài khoản của user vẫn giữ nguyên gói standard an toàn
        refreshed_user = User.query.get(self.user.id)
        self.assertEqual(refreshed_user.subscription_tier, 'standard')

        # 3. Tạo thông báo trong hòm thư người dùng để xác nhận đã tiếp nhận
        notif = Notification.query.filter_by(user_id=self.user.id, type='SUBSCRIPTION_INTEREST').first()
        self.assertIsNotNone(notif)
        self.assertIn('Gói Pro', notif.title)


if __name__ == '__main__':
    unittest.main()
