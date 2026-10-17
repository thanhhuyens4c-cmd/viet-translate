"""
test_header_popovers.py
Unit tests for Header Popovers (Messages, Notifications, Help, Settings):
1. Verify popover trigger buttons (button type="button", aria-haspopup, aria-expanded, aria-controls, title).
2. Verify popovers do not navigate immediately upon click (no direct href on trigger button).
3. Verify Messages & Notifications popover structure, badges, dynamic list containers, and bottom CTAs.
4. Verify Help & Settings Popover structure and quick actions.
5. Verify removal of Messages and Notifications from sidebar Chung menu (only Về VietTranslate & Thanh toán Escrow remain).
6. Verify unauthenticated users do not see popovers.
7. Verify responsive bounds and accessibility attributes.
"""

import unittest
from app import app, db
from models import User


class TestHeaderPopovers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Clean old test users
        User.query.filter_by(email='test_popover_pdv@example.com').delete()
        db.session.commit()

        # Create test interpreter
        self.user = User(
            name='Nguyễn Phiên Dịch Viên',
            email='test_popover_pdv@example.com',
            password_hash='pbkdf2:sha256:dummy_popover_hash',
            role='translator'
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        try:
            User.query.filter_by(id=self.user.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
        self.app_context.pop()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

    def test_01_authenticated_user_has_all_four_popover_structures(self):
        """Kiểm tra người dùng đã đăng nhập có đầy đủ 4 Popover trên Header (Tin nhắn, Thông báo, Trợ giúp, Cài đặt)."""
        self._login()
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Wrapper elements for all 4 icons
        self.assertIn('id="nav-msg-wrapper"', html)
        self.assertIn('id="nav-notif-wrapper"', html)
        self.assertIn('id="nav-help-wrapper"', html)
        self.assertIn('id="nav-settings-wrapper"', html)

        # Trigger buttons must all be <button type="button"> (not direct <a> navigation)
        self.assertIn('<button type="button" id="nav-msg-btn"', html)
        self.assertIn('<button type="button" id="nav-notif-btn"', html)
        self.assertIn('<button type="button" id="nav-help-btn"', html)
        self.assertIn('<button type="button" id="nav-settings-btn"', html)

        # Unread badges must be retained on trigger buttons
        self.assertIn('id="msg-badge"', html)
        self.assertIn('id="notif-badge"', html)

        # Popover panels must be hidden by default
        self.assertIn('id="nav-msg-popover"', html)
        self.assertIn('id="nav-notif-popover"', html)
        self.assertIn('id="nav-help-popover"', html)
        self.assertIn('id="nav-settings-popover"', html)
        self.assertIn('class="header-popover-panel hidden', html)

        # Accessibility attributes
        for p_id in ['nav-msg-popover', 'nav-notif-popover', 'nav-help-popover', 'nav-settings-popover']:
            self.assertIn(f'aria-controls="{p_id}"', html)

    def test_02_messages_popover_content_and_cta(self):
        """Kiểm tra nội dung Popover Tin nhắn: header, list container và CTA Xem tất cả tin nhắn."""
        self._login()
        resp = self.client.get('/')
        html = resp.data.decode('utf-8')

        self.assertIn('id="nav-msg-popover"', html)
        self.assertIn('Tin nhắn', html)
        self.assertIn('Đoạn chat gần đây', html)
        self.assertIn('id="nav-msg-list"', html)
        self.assertIn('Xem tất cả tin nhắn', html)

    def test_03_notifications_popover_content_and_cta(self):
        """Kiểm tra nội dung Popover Thông báo: header, action đánh dấu đã đọc, list container và CTA."""
        self._login()
        resp = self.client.get('/')
        html = resp.data.decode('utf-8')

        self.assertIn('id="nav-notif-popover"', html)
        self.assertIn('Thông báo', html)
        self.assertIn('Thông báo mới nhận', html)
        self.assertIn('id="header-notif-mark-all-read"', html)
        self.assertIn('Đánh dấu đã đọc', html)
        self.assertIn('id="nav-notif-list"', html)
        self.assertIn('Xem tất cả thông báo', html)

    def test_04_help_and_settings_popover_quick_items_and_cta(self):
        """Kiểm tra nội dung Popover Trợ giúp & Cài đặt vẫn giữ nguyên vẹn."""
        self._login()
        resp = self.client.get('/')
        html = resp.data.decode('utf-8')

        # Help
        self.assertIn('Trợ giúp & Hỗ trợ', html)
        self.assertIn('Bạn cần hỗ trợ gì?', html)
        self.assertIn('24/7', html)
        self.assertIn('Câu hỏi thường gặp', html)
        self.assertIn('Hướng dẫn sử dụng', html)
        self.assertIn('Liên hệ hỗ trợ', html)
        self.assertIn('Trung tâm trợ giúp', html)

        # Settings
        self.assertIn('Cài đặt', html)
        self.assertIn('Quản lý tài khoản của bạn', html)
        self.assertIn('Bảo mật tài khoản', html)
        self.assertIn('Cài đặt tài khoản', html)
        self.assertIn('Cài đặt thông báo', html)
        self.assertIn('Xem tất cả cài đặt', html)

    def test_05_sidebar_chung_menu_does_not_contain_messages_or_notifications(self):
        """Kiểm tra menu CHUNG ở sidebar đã xóa Tin nhắn và Thông báo, chỉ còn Về VietTranslate và Thanh toán Escrow."""
        self._login()
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Find the sidebar "Chung" section
        self.assertIn('<p class="side-title">Chung</p>', html)
        sidebar_chung_part = html.split('<p class="side-title">Chung</p>')[1].split('</nav>')[0]

        # Verify Tin nhắn and Thông báo are NOT in sidebar Chung
        self.assertNotIn('Tin nhắn', sidebar_chung_part)
        self.assertNotIn('Thông báo', sidebar_chung_part)

        # Verify Về VietTranslate and Thanh toán Escrow ARE in sidebar Chung
        self.assertIn('Về VietTranslate', sidebar_chung_part)
        self.assertIn('Thanh toán Escrow', sidebar_chung_part)

    def test_06_unauthenticated_user_does_not_see_popovers(self):
        """Người dùng chưa đăng nhập không hiển thị bất kỳ popover nào."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        for p_id in ['nav-msg-popover', 'nav-notif-popover', 'nav-help-popover', 'nav-settings-popover']:
            self.assertNotIn(f'id="{p_id}"', html)
        for b_id in ['nav-msg-btn', 'nav-notif-btn', 'nav-help-btn', 'nav-settings-btn']:
            self.assertNotIn(f'id="{b_id}"', html)

    def test_07_popover_js_and_css_animations_present(self):
        """Kiểm tra JavaScript điều khiển 4 Popovers và CSS keyframe animation có mặt trong base template."""
        self._login()
        resp = self.client.get('/')
        html = resp.data.decode('utf-8')

        # CSS animation
        self.assertIn('@keyframes headerPopoverFadeIn', html)
        self.assertIn('.header-popover-panel:not(.hidden)', html)

        # JavaScript functions and arrays
        self.assertIn("ALL_HEADER_POPOVER_TYPES = ['msg', 'notif', 'help', 'settings']", html)
        self.assertIn('function toggleHeaderPopover', html)
        self.assertIn('function closeAllHeaderPopovers', html)
        self.assertIn('function adjustPopoverPosition', html)
        self.assertIn('function loadHeaderMessages', html)
        self.assertIn('function loadHeaderNotifications', html)
        self.assertIn('function handleHeaderNotifClick', html)
        self.assertIn('function markAllHeaderNotificationsRead', html)
        self.assertIn('function updateTriggerButtonState', html)


if __name__ == '__main__':
    unittest.main()

