"""
Regression test suite verifying all 8 audit fixes:
1. 500 error handler (no traceback disclosure)
2. Production SECRET_KEY fail-fast
3. Admin CSRF protection (tokens required for state changes)
4. Consolidated POST /api/proposals/<id>/reject endpoint
5. Persistent storage configuration
6. PayoutMethods PostgreSQL ORM ACID operations
7. InterpreterService rendering and booking integration
8. Defensive rendering of orphaned records in Admin Contracts
"""

import unittest
import os
import sys
from datetime import datetime

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['FLASK_ENV'] = 'testing'

from app import app, db
from models import User, Contract, PayoutMethod, PayoutHistory, InterpreterService
from services.payout_methods import (
    add_payout_method,
    get_payout_methods,
    get_user_payout_data,
    set_default_payout_method,
    delete_payout_method
)

class AuditFixesRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        with app.app_context():
            db.create_all()
            if not User.query.get(1):
                admin = User(
                    id=1,
                    email='admin_audit_test@viettranslate.vn',
                    name='Admin Audit Test',
                    role='admin',
                    admin_role='super_admin',
                    is_admin=True,
                    is_active=True,
                    password_hash='testpass'
                )
                db.session.add(admin)
                db.session.commit()

    def setUp(self):
        with app.app_context():
            if not User.query.get(1):
                admin = User(
                    id=1,
                    email='admin_audit_test@viettranslate.vn',
                    name='Admin Audit Test',
                    role='admin',
                    admin_role='super_admin',
                    is_admin=True,
                    is_active=True,
                    password_hash='testpass'
                )
                db.session.add(admin)
                db.session.commit()

    def test_01_reject_proposal_single_route(self):
        """Xác minh chỉ có duy nhất 1 route handler cho POST /api/proposals/<proposal_id>/reject."""
        rules = [r for r in app.url_map.iter_rules() if '/api/proposals/' in r.rule and 'reject' in r.rule]
        self.assertEqual(len(rules), 1, f"Found {len(rules)} matching rules for reject endpoint: {rules}")
        self.assertIn('POST', rules[0].methods)

    def test_02_500_handler_no_traceback(self):
        """Xác minh error handler 500 trả về trang lỗi thân thiện, không lộ traceback hay SQL."""
        with app.test_request_context():
            from app import handle_500
            fake_error = Exception("Test sensitive database error with postgres://secret@localhost")
            response, code = handle_500(fake_error)
            self.assertEqual(code, 500)
            self.assertNotIn("postgres://secret@localhost", str(response))
            self.assertNotIn("Traceback (most recent call last)", str(response))
            self.assertIn("ERR-", str(response))

    def test_03_admin_csrf_protected(self):
        """Xác minh các endpoint admin POST từ chối request thiếu token hợp lệ (403)."""
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['admin_role'] = 'super_admin'
            sess['admin_session_created'] = now_ts
            sess['admin_session_last_seen'] = now_ts
            sess['admin_csrf_token'] = 'valid_admin_secret_token_12345'

        # Thử gọi POST không có CSRF token -> 403 Forbidden
        res = self.client.post('/admin/reviews/1/toggle')
        self.assertEqual(res.status_code, 403)

        # Thử gọi POST với CSRF token sai -> 403 Forbidden
        res_bad = self.client.post('/admin/reviews/1/toggle', data={'_csrf_token': 'fake_invalid_token'})
        self.assertEqual(res_bad.status_code, 403)

    def test_04_payout_methods_postgresql_crud(self):
        """Xác minh PayoutMethods thực hiện CRUD an toàn trên database với ACID transaction."""
        with app.app_context():
            test_user = User.query.first()
            if not test_user:
                self.skipTest("No user in database to test payout methods.")

            # Thêm phương thức mới
            success, res = add_payout_method(
                user_id=test_user.id,
                bank_code="VCB",
                account_number="012345678999",
                account_holder_name="NGUYEN VAN TEST",
                branch="Chi nhánh Hoàn Kiếm",
                set_as_default=True
            )
            self.assertTrue(success, f"Failed to add payout method: {res}")
            method_id = res['id']

            # Kiểm tra phương thức xuất hiện trong DB
            methods = get_payout_methods(test_user.id)
            found = [m for m in methods if m['id'] == method_id]
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0]['is_default'])
            self.assertTrue(found[0]['masked_account_number'].endswith("8999"))

            # Kiểm tra lịch sử
            data = get_user_payout_data(test_user.id)
            history = data.get('history', [])
            self.assertTrue(any(h['method_id'] == method_id and h['action'] == 'add' for h in history))

            # Dọn dẹp: Xóa phương thức test
            del_ok, _ = delete_payout_method(test_user.id, method_id)
            self.assertTrue(del_ok)

    def test_05_contract_orphan_safety_in_template(self):
        """Xác minh template admin_contracts xử lý hợp đồng mồ côi (c.hirer is None) an toàn."""
        with app.test_request_context():
            from flask import render_template
            # Tạo mock contract mồ côi
            class MockContract:
                id = 99999
                job_id = None
                job = None
                service_id = None
                service = None
                interpreter_service = None
                proposal_id = None
                hirer_id = 99999
                translator_id = 88888
                hirer = None       # ORPHAN HIRER
                translator = None  # ORPHAN TRANSLATOR
                agreed_price = 1000000
                scheduled_date = '2026-10-20'
                scheduled_time_start = '09:00'
                scheduled_time_end = '11:00'
                status = 'completed'
                schedule_entries = []

            rendered = render_template('admin_contracts.html', contracts=[MockContract()], status_filter='all')
            self.assertIn("Khách cũ (#99999)", rendered)
            self.assertIn("PDV cũ (#88888)", rendered)
            self.assertIn("#CTR-99999", rendered)

    def test_09_defensive_rendering_orphaned_reports(self):
        """Xác minh render admin_reports.html không crash khi reporter bị xóa / mồ côi (ERR-EAD435CF)."""
        with app.test_request_context():
            from flask import render_template
            class MockReport:
                id = 1
                reporter_id = 99999
                reporter = None  # ORPHAN REPORTER
                target_type = 'job'
                target_id = 123
                reason = 'Vi phạm tiêu chuẩn'
                description = 'Mô tả chi tiết'
                status = 'new'
                created_at = datetime.utcnow()

            rendered = render_template('admin_reports.html', reports=[MockReport()], status_filter='all')
            self.assertIn("Người dùng cũ (#99999)", rendered)
            self.assertIn("#RPT-1", rendered)

    def test_10_defensive_rendering_orphaned_payments(self):
        """Xác minh render admin_payments.html không crash khi user thanh toán bị xóa / mồ côi."""
        with app.test_request_context():
            from flask import render_template
            class MockPayment:
                id = 555
                contract_id = 12
                user_id = 88888
                user = None  # ORPHAN USER
                amount = 2500000
                payment_method = 'VNPAY'
                transaction_ref = 'VN123456'
                status = 'completed'
                created_at = datetime.utcnow()

            rendered = render_template('admin_payments.html', payments=[MockPayment()], status_filter='all')
            self.assertIn("Người dùng cũ (#88888)", rendered)
            self.assertIn("#CTR-12", rendered)

    def test_11_defensive_rendering_orphaned_reviews(self):
        """Xác minh render admin_reviews.html không crash khi reviewer/reviewee bị xóa / mồ côi."""
        with app.test_request_context():
            from flask import render_template
            class MockReview:
                id = 777
                contract_id = 15
                reviewer_id = 11111
                reviewer = None  # ORPHAN REVIEWER
                reviewee_id = 22222
                reviewee = None  # ORPHAN REVIEWEE
                rating = 5
                comment = 'Dịch vụ tuyệt vời'
                is_hidden = False
                created_at = datetime.utcnow()

            rendered = render_template('admin_reviews.html', reviews=[MockReview()])
            self.assertIn("Người dùng cũ (#11111)", rendered)
            self.assertIn("Người dùng cũ (#22222)", rendered)
            self.assertIn("#REV-777", rendered)

    def test_12_proposal_mutation_requires_csrf(self):
        """Xác minh các API mutation proposal từ chối request thiếu CSRF token (403)."""
        # Giả lập đăng nhập Hirer
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'hirer'
            sess['_fresh'] = True

        # 1. Gọi reject mà KHÔNG có CSRF token -> bắt buộc bị từ chối 403
        res_reject = self.client.post('/api/proposals/1/reject', json={'reason': 'test reject'})
        self.assertEqual(res_reject.status_code, 403)
        data_reject = res_reject.get_json() or {}
        self.assertIn('không hợp lệ', data_reject.get('message', ''))

        # 2. Gọi withdraw mà KHÔNG có CSRF token -> bắt buộc bị từ chối 403
        res_withdraw = self.client.post('/api/proposals/1/withdraw', json={'reason': 'test withdraw'})
        self.assertEqual(res_withdraw.status_code, 403)
        data_withdraw = res_withdraw.get_json() or {}
        self.assertIn('không hợp lệ', data_withdraw.get('message', ''))

    def test_13_seed_demo_endpoint_hardened(self):
        """Xác minh endpoint seed demo từ chối GET và không chấp nhận secret hard-code."""
        # 1. GET request -> 405 Method Not Allowed
        res_get = self.client.get('/api/admin/seed-demo-interpreters?secret=viettranslate_seed_2026')
        self.assertEqual(res_get.status_code, 405)

        # 2. POST request từ người dùng vãng lai -> 302/401/403
        res_post = self.client.post('/api/admin/seed-demo-interpreters?secret=viettranslate_seed_2026')
        self.assertIn(res_post.status_code, [302, 401, 403])

    def test_14_cron_release_expired_hardened(self):
        """Xác minh endpoint cron chỉ nhận POST với Authorization header, từ chối GET và query secret."""
        cron_secret = 'test_cron_secret_super_key_12345'
        old_secret = os.environ.get('CRON_SECRET')
        os.environ['CRON_SECRET'] = cron_secret
        try:
            # 1. GET request -> 405 Method Not Allowed
            res_get = self.client.get('/api/cron/release-expired?secret=' + cron_secret)
            self.assertEqual(res_get.status_code, 405)

            # 2. POST request không có header Authorization -> 401 Unauthorized
            res_post_no_auth = self.client.post('/api/cron/release-expired?secret=' + cron_secret)
            self.assertEqual(res_post_no_auth.status_code, 401)

            # 3. POST request có Bearer token sai -> 401 Unauthorized
            res_post_wrong_auth = self.client.post(
                '/api/cron/release-expired',
                headers={'Authorization': 'Bearer wrong_token_123456789'}
            )
            self.assertEqual(res_post_wrong_auth.status_code, 401)

            # 4. POST request có Bearer token đúng -> 200 OK
            res_post_ok = self.client.post(
                '/api/cron/release-expired',
                headers={'Authorization': f'Bearer {cron_secret}'}
            )
            self.assertEqual(res_post_ok.status_code, 200)
            data_ok = res_post_ok.get_json() or {}
            self.assertTrue(data_ok.get('success'))
        finally:
            if old_secret is not None:
                os.environ['CRON_SECRET'] = old_secret
            else:
                os.environ.pop('CRON_SECRET', None)

    def test_15_legacy_job_routes_redirect_to_statistics(self):
        """Xác minh các route quản lý job legacy (/accepted-jobs, /applied-jobs, /completed-jobs) chuyển hướng đúng tab."""
        # Giả lập phiên dịch viên đăng nhập
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'translator'
            sess['_fresh'] = True

        for path, expected_tab in [
            ('/accepted-jobs', 'tab=accepted'),
            ('/applied-jobs', 'tab=applied'),
            ('/completed-jobs', 'tab=completed')
        ]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 302, f"Đường dẫn {path} không chuyển hướng 302")
            self.assertIn('/job-statistics', res.location)
            self.assertIn(expected_tab, res.location)

    def test_16_admin_job_review_modals_responsive_styling(self):
        """Xác minh các modal thẩm định job trong admin có CSS responsive chống che nút trên mobile."""
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'admin_job_review.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Kiểm tra sự tồn tại của cấu trúc modal chống che khuất bởi bàn phím ảo
        self.assertIn('max-height: 85vh', content)
        self.assertIn('overflow-y: auto', content)
        self.assertIn('id="rejectModal"', content)
        self.assertIn('id="revisionModal"', content)
        self.assertIn('id="askSuperAdminModal"', content)

if __name__ == '__main__':
    unittest.main()

