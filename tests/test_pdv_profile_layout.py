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

        resp = self.client.post('/resend-verification-email')
        self.assertIn(resp.status_code, (200, 302))

if __name__ == '__main__':
    unittest.main()
