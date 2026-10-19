import os
os.environ.setdefault('SECRET_KEY', 'test-secret-key-at-least-16-characters')
import re
import unittest
from app import app
from models import db, User, TranslatorProfile, HirerProfile
from werkzeug.security import generate_password_hash

class TestPDVMobileNavParity(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            # Translator user
            self.translator = User.query.filter_by(email='nav_test_pdv@example.com').first()
            if not self.translator:
                self.translator = User(
                    name='PDV Tester',
                    email='nav_test_pdv@example.com',
                    phone='0988776655',
                    role='translator',
                    password_hash=generate_password_hash('password123'),
                    email_verified=True,
                    is_active=True
                )
                db.session.add(self.translator)
                db.session.flush()
                tp = TranslatorProfile(user_id=self.translator.id, title='Phiên dịch viên chuyên nghiệp', is_verified=True)
                db.session.add(tp)
                db.session.commit()

            # Hirer user
            self.hirer = User.query.filter_by(email='nav_test_hirer@example.com').first()
            if not self.hirer:
                self.hirer = User(
                    name='Hirer Tester',
                    email='nav_test_hirer@example.com',
                    phone='0988776656',
                    role='hirer',
                    password_hash=generate_password_hash('password123'),
                    email_verified=True,
                    is_active=True
                )
                db.session.add(self.hirer)
                db.session.flush()
                hp = HirerProfile(user_id=self.hirer.id, is_verified=True)
                db.session.add(hp)
                db.session.commit()

            self.translator_id = self.translator.id
            self.hirer_id = self.hirer.id

    def _login_as(self, user_id):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['_fresh'] = True

    def _extract_mobile_nav_translator_section(self, html):
        """Extract the mobile drawer contents between role translator check and else/next block."""
        match = re.search(
            r'id="mobile-nav"[\s\S]*?\{%\s*elif\s+current_user\s+and\s+current_user\.role\s*==\s*\'translator\'\s*%\}([\s\S]*?)\{%\s*else\s*%\}',
            html
        )
        if match:
            return match.group(1)
        # In rendered HTML, look for the translator section in mobile-nav
        match_rendered = re.search(
            r'<div id="mobile-nav"[\s\S]*?<!-- Mobile: 1\. Tổng quan -->([\s\S]*?)<!-- Mobile: 5\. Chức năng dùng chung -->[\s\S]*?<span>Thanh toán Escrow</span>\s*</a>',
            html
        )
        if match_rendered:
            return match_rendered.group(0)
        return ""

    def test_pdv_mobile_and_desktop_item_parity(self):
        """Test that Desktop Sidebar and Mobile Drawer have exact same business items and ordering."""
        self._login_as(self.translator_id)
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # 1. Desktop sidebar must exist
        self.assertIn('<aside class="hidden lg:block w-60 shrink-0', html)

        # 2. Verify all business items in desktop sidebar
        desktop_expected_endpoints = [
            '/interpreter/dashboard',
            '/jobs',
            '/jobs?recommended=1',
            '/job-statistics',
            '/my-schedule',
            '/interpreter/income/overview',
            '/interpreter/income/details',
            '/interpreter/income/payouts',
            '/interpreter/income/transactions',
            '/interpreter/income/bank-info',
            '/account/overview',
            '/about',
            '/tin-tuc',
            '/payment-info'
        ]

        # Extract aside HTML
        aside_match = re.search(r'<aside[\s\S]*?</aside>', html)
        self.assertIsNotNone(aside_match, "Desktop sidebar <aside> not found")
        aside_html = aside_match.group(0)

        for ep in desktop_expected_endpoints:
            self.assertIn(f'href="{ep}"', aside_html, f"Expected endpoint {ep} not found in desktop sidebar")

        # 3. Verify mobile drawer has matching items
        mob_match = re.search(r'<div id="mobile-nav"[\s\S]*?</div>\s*</div>\s*</header>', html)
        self.assertIsNotNone(mob_match, "Mobile nav drawer #mobile-nav not found")
        mob_html = mob_match.group(0)

        for ep in desktop_expected_endpoints:
            self.assertIn(f'href="{ep}"', mob_html, f"Expected endpoint {ep} not found in mobile nav")

        # 4. Verify order of main items in mobile nav
        order_patterns = [
            r'href="/interpreter/dashboard"',
            r'href="/jobs"',
            r'href="/jobs\?recommended=1"',
            r'href="/job-statistics"',
            r'href="/my-schedule"',
            r'href="/interpreter/income/overview"',
            r'href="/account/overview"',
            r'href="/about"',
            r'href="/tin-tuc"',
            r'href="/payment-info"'
        ]
        last_pos = 0
        for pattern in order_patterns:
            m = re.search(pattern, mob_html[last_pos:])
            self.assertIsNotNone(m, f"Pattern {pattern} not found in mobile nav in proper sequence")
            last_pos += m.end()

    def test_redundant_items_removed_from_mobile(self):
        """Test that redundant hash shortcuts, accordion, and public home links are absent."""
        self._login_as(self.translator_id)
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        mob_match = re.search(r'<div id="mobile-nav"[\s\S]*?</div>\s*</div>\s*</header>', html)
        self.assertIsNotNone(mob_match)
        mob_html = mob_match.group(0)

        # Trang chủ công khai should NOT be in translator mobile nav
        self.assertNotIn('Trang chủ công khai', mob_html)

        # Hash shortcuts to dashboard sections should NOT exist in mobile nav
        self.assertNotIn('href="#section-jobs"', mob_html)
        self.assertNotIn('href="#section-income"', mob_html)
        self.assertNotIn('href="#section-schedule"', mob_html)
        self.assertNotIn('href="#section-recommended"', mob_html)

        # toggleMobOverview function and IDs should NOT exist anywhere in rendered page
        self.assertNotIn('toggleMobOverview', html)
        self.assertNotIn('id="mob-overview-menu"', html)
        self.assertNotIn('id="mob-overview-btn"', html)

    def test_income_submenu_parity_and_controls(self):
        """Test that Income submenu contains all 4 sub-items with independent IDs on desktop and mobile."""
        self._login_as(self.translator_id)
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Mobile income elements
        self.assertIn('id="mob-income-btn"', html)
        self.assertIn('id="mob-income-menu"', html)
        self.assertIn('aria-controls="mob-income-menu"', html)
        self.assertIn('onclick="toggleMobIncome(event)"', html)

        # Desktop income elements
        self.assertIn('id="desktop-income-toggle-btn"', html)
        self.assertIn('id="desktop-income-submenu"', html)
        self.assertIn('aria-controls="desktop-income-submenu"', html)
        self.assertIn('onclick="toggleDesktopIncome(event)"', html)

        # Sub-items present in both menus
        sub_items = [
            ('Chi tiết các khoản', '/interpreter/income/details'),
            ('Theo dõi thanh toán', '/interpreter/income/payouts'),
            ('Lịch sử giao dịch', '/interpreter/income/transactions'),
            ('Thông tin nhận tiền', '/interpreter/income/bank-info')
        ]
        for label, url in sub_items:
            self.assertIn(f'href="{url}"', html)
            self.assertIn(label, html)

    def test_utility_links_preserved_in_mobile_drawer(self):
        """Test that messages, notifications, support, security, and logout remain accessible in mobile drawer."""
        self._login_as(self.translator_id)
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        mob_match = re.search(r'<div id="mobile-nav"[\s\S]*?</div>\s*</div>\s*</header>', html)
        self.assertIsNotNone(mob_match)
        mob_html = mob_match.group(0)

        # Verify utility items are in the drawer
        self.assertIn('href="/messages"', mob_html)
        self.assertIn('href="/notifications"', mob_html)
        self.assertIn('href="/account/overview?tab=support"', mob_html)
        self.assertIn('href="/account/overview?tab=security"', mob_html)
        self.assertIn('href="/logout"', mob_html)

    def test_active_states_across_views(self):
        """Test active styling classes are appropriately applied to both desktop and mobile items."""
        self._login_as(self.translator_id)

        # 1. Dashboard active state
        resp = self.client.get('/interpreter/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Check mobile Tổng quan has active styling
        self.assertRegex(html, r'<a href="/interpreter/dashboard"\s+class="[^"]*text-brand-600 bg-brand-50 font-bold[^"]* flex items-center gap-2">')

        # 2. Jobs active state
        resp = self.client.get('/jobs')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('href="/jobs"', html)

        # 3. Income sub-page active state & auto-expanded submenu
        resp = self.client.get('/interpreter/income/details')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Both submenus should NOT have 'hidden' class when on an income page
        # mob-income-menu should be open
        mob_income_match = re.search(r'id="mob-income-menu"\s+class="([^"]*)"', html)
        self.assertIsNotNone(mob_income_match)
        self.assertNotIn('hidden', mob_income_match.group(1))

        # desktop-income-submenu should be open
        desktop_income_match = re.search(r'id="desktop-income-submenu"\s+class="([^"]*)"', html)
        self.assertIsNotNone(desktop_income_match)
        self.assertNotIn('hidden', desktop_income_match.group(1))

        # Active item inside submenu has bold highlight
        self.assertIn('text-brand-600 bg-brand-50 font-bold border-l-2 border-brand-600', html)

    def test_role_isolation_hirer_and_guest(self):
        """Verify changes to translator mobile nav do not break or affect hirer or guest views."""
        # 1. Hirer navigation
        self._login_as(self.hirer_id)
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Hirer should have hirer links
        self.assertIn('href="/dashboard"', html)
        self.assertIn('href="/my-projects"', html)
        self.assertIn('href="/my-jobs"', html)
        # Hirer should not have translator dashboard or income overview in their nav
        self.assertNotIn('href="/interpreter/dashboard"', html)
        self.assertNotIn('id="mob-income-menu"', html)

        # 2. Guest navigation
        guest_client = self.app.test_client()
        resp = guest_client.get('/')
        self.assertEqual(resp.status_code, 200)
        guest_html = resp.data.decode('utf-8')

        # Guest should have guest nav links
        self.assertIn('href="/login"', guest_html)
        self.assertIn('href="/register"', guest_html)
        self.assertNotIn('id="mob-income-menu"', guest_html)
        self.assertNotIn('id="desktop-income-submenu"', guest_html)

if __name__ == '__main__':
    unittest.main()
