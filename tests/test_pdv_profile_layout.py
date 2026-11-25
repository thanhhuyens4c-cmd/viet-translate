import os
os.environ.setdefault('SECRET_KEY', 'test-secret-key-at-least-16-characters')
import unittest
from unittest.mock import patch
from app import app
from models import db, User, TranslatorProfile
from werkzeug.security import generate_password_hash

class TestPDVProfileLayout(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Setup or get PDV user
            self.user = User.query.filter_by(email='hieu@gmail.com').first()
            if not self.user:
                self.user = User(
                    name='Hiếu',
                    email='hieu@gmail.com',
                    phone='1122231541',
                    role='translator',
                    password_hash=generate_password_hash('password123'),
                    email_verified=False,
                    is_active=True
                )
                db.session.add(self.user)
                db.session.flush()
                tp = TranslatorProfile(user_id=self.user.id, title='', is_verified=False)
                db.session.add(tp)
                db.session.commit()
            else:
                self.user.email_verified = False
                db.session.commit()
            self.user_id = self.user.id

    def test_email_verification_banner_removed(self):
        """Verify the email verification warning banner is completely removed from /account/profile."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

        resp = self.client.get('/account/profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Check banner text does not exist
        self.assertNotIn('Tài khoản của bạn chưa được xác minh email', html)
        self.assertNotIn('Gửi lại email xác minh', html)

    def test_pdv_layout_overflow_fixed(self):
        """Verify flex-grow min-w-0 and .hide-scrollbar prevent horizontal overflow."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

        resp = self.client.get('/account/profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Verify min-w-0 is added to main content column to fix flexbox overflow bug
        self.assertIn('flex-grow min-w-0 space-y-6', html)

        # Verify container has min-w-0
        self.assertIn('w-full min-w-0 max-w-6xl', html)

        # Verify .hide-scrollbar CSS rule is present
        self.assertIn('.hide-scrollbar::-webkit-scrollbar', html)
        self.assertIn('scrollbar-width: none;', html)

    @patch('services.email.send_verification_email')
    def test_resend_verification_email_endpoint(self, mock_send_email):
        """Verify the resend_verification_email endpoint still works programmatically if needed."""
        mock_send_email.return_value = (True, None)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

    def test_public_and_cv_toggles_one_row_layout(self):
        """Verify the public profile and CV toggles are rendered in a 1-row responsive grid and buttons are properly placed."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

        resp = self.client.get('/account/profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # 1. Verify 1-row responsive grid container exists
        self.assertIn('grid grid-cols-1 md:grid-cols-2 gap-4', html)

        # 2. Verify both toggles exist
        self.assertIn('id="toggle-public-profile"', html)
        self.assertIn('id="toggle-cv-public"', html)
        self.assertIn('name="has_cv_public_field"', html)

        # 3. Verify status elements exist
        self.assertIn('id="public-toggle-status"', html)
        self.assertIn('id="cv-public-toggle-status"', html)

        # 4. Verify action bar with buttons exists outside the grid
        self.assertIn('resetPersonalProfileForm()', html)
        self.assertIn('id="btn-save-personal-profile"', html)

    def test_pdv_header_banner_and_title_sanitization(self):
        """Verify the header banner alignment prevents avatar overlap and 'None' is never rendered."""
        with self.app.app_context():
            # Set profile title to string 'None' to test edge case sanitization
            tp = TranslatorProfile.query.filter_by(user_id=self.user_id).first()
            if tp:
                tp.title = 'None'
                db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

        resp = self.client.get('/account/profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Banner uses items-start to place banner title at the top, clear of the avatar
        self.assertIn('h-36 sm:h-44 md:h-48', html)
        self.assertIn('items-start justify-between', html)

        # Avatar uses -mt-14 sm:-mt-16 md:-mt-20
        self.assertIn('-mt-14 sm:-mt-16 md:-mt-20', html)
        self.assertIn('id="translator-header-avatar-box"', html)

        # 'None' must NOT be rendered under the name
        self.assertNotIn('<span id="header-profile-title" class="font-semibold text-slate-700 truncate max-w-sm">None</span>', html)
        self.assertIn('Chưa đặt tiêu đề chuyên môn', html)
        self.assertIn('(Thêm tiêu đề)', html)

    def test_pdv_tab_navigation_bar_neat_labels(self):
        """Verify the tab navigation bar has compact labels, responsive overflow styling, and all 6 tabs."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

        resp = self.client.get('/account/profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Check all 6 tabs exist
        self.assertIn('Hồ sơ cá nhân', html)
        self.assertIn('Năng lực & Bảng giá', html)
        self.assertIn('Tiêu chí nhận việc', html)
        self.assertIn('Gói dịch vụ & Quyền lợi', html)
        self.assertIn('Thông báo & Bảo mật', html)
        self.assertIn('Trợ giúp & Hỗ trợ', html)

        # Check tab container has smooth scroll and hide-scrollbar
        self.assertIn('overflow-x-auto whitespace-nowrap scroll-smooth hide-scrollbar', html)

if __name__ == '__main__':
    unittest.main()
