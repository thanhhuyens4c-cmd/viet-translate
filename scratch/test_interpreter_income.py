import sys
import os
import unittest
from datetime import datetime, date, timedelta

# Import Flask app
from app import app, db
from models import User, Contract, Job, TranslatorProfile, HirerProfile
from services.payout_methods import (
    get_payout_methods,
    get_user_payout_data,
    add_payout_method,
    set_default_payout_method,
    delete_payout_method,
    mask_account_number,
    _get_store_path
)

class InterpreterIncomeModuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def test_01_syntax_and_route_registration(self):
        """Kiểm tra các route của cả 5 trang phân hệ thu nhập đã đăng ký chính xác trong Flask."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn('/interpreter/income', rules)
        self.assertIn('/interpreter/income/overview', rules)
        self.assertIn('/interpreter/income/details', rules)
        self.assertIn('/interpreter/income/payouts', rules)
        self.assertIn('/interpreter/income/transactions', rules)
        self.assertIn('/interpreter/income/bank-info', rules)

    def test_02_rbac_unauthenticated_redirects(self):
        """Khách vãng lai chưa đăng nhập phải bị chuyển hướng về trang /login."""
        with app.test_client() as c:
            for endpoint in ['overview', 'details', 'payouts', 'transactions', 'bank-info']:
                resp = c.get(f'/interpreter/income/{endpoint}', follow_redirects=False)
                self.assertEqual(resp.status_code, 302, f"Failed for {endpoint}")
                self.assertIn('/login', resp.headers['Location'])

    def test_03_rbac_hirer_forbidden(self):
        """Tài khoản khách hàng (Hirer) không được phép truy cập bất kỳ trang nào của Interpreter Income."""
        with app.app_context():
            hirer = User.query.filter_by(role='hirer').first()
            if not hirer:
                self.skipTest("Không tìm thấy user hirer trong DB để test")
            
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = hirer.id
                
                for endpoint in ['overview', 'details', 'payouts', 'transactions', 'bank-info']:
                    resp = c.get(f'/interpreter/income/{endpoint}', follow_redirects=False)
                    self.assertEqual(resp.status_code, 302, f"Hirer not redirected on {endpoint}")
                    self.assertEqual(resp.headers['Location'], '/')

    def test_04_translator_access_overview(self):
        """Tài khoản phiên dịch viên (Translator) truy cập trang Overview thành công (HTTP 200)."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator trong DB để test")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id
                
                resp = c.get('/interpreter/income/overview')
                self.assertEqual(resp.status_code, 200)
                html = resp.get_data(as_text=True)
                self.assertIn("Tổng quan thu nhập", html)
                self.assertIn("Thu nhập ròng (Thực nhận)", html)
                self.assertIn("Tổng thu nhập gộp", html)
                self.assertIn("Đang chờ thanh toán", html)
                self.assertIn("Đang giữ trong Escrow", html)

    def test_05_time_filters(self):
        """Kiểm tra 3 chế độ lọc: current_month, last_month, custom trên trang Tổng quan."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                # Tháng này
                r1 = c.get('/interpreter/income/overview?period=current_month')
                self.assertEqual(r1.status_code, 200)
                self.assertIn("Tháng này", r1.get_data(as_text=True))

                # Tháng trước
                r2 = c.get('/interpreter/income/overview?period=last_month')
                self.assertEqual(r2.status_code, 200)
                self.assertIn("Tháng trước", r2.get_data(as_text=True))

                # Tùy chọn ngày
                r3 = c.get('/interpreter/income/overview?period=custom&start_date=2026-01-01&end_date=2026-12-31')
                self.assertEqual(r3.status_code, 200)
                self.assertIn("2026", r3.get_data(as_text=True))

    def test_06_all_five_subpages_render(self):
        """Kiểm tra cả 5 trang chức năng render thành công và chứa tiêu đề tương ứng."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                subpages = [
                    ('/interpreter/income/overview', 'Tổng quan thu nhập'),
                    ('/interpreter/income/details', 'Chi tiết các khoản thu nhập'),
                    ('/interpreter/income/payouts', 'Theo dõi thanh toán'),
                    ('/interpreter/income/transactions', 'Lịch sử giao dịch'),
                    ('/interpreter/income/bank-info', 'Thông tin nhận tiền')
                ]
                for path, expected_title in subpages:
                    resp = c.get(path)
                    self.assertEqual(resp.status_code, 200, f"Route {path} failed with {resp.status_code}")
                    self.assertIn(expected_title, resp.get_data(as_text=True))

    def test_07_details_and_payouts_elements(self):
        """Kiểm tra các thành phần giao diện đặc thù của Chi tiết thu nhập và Theo dõi thanh toán."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                r_det = c.get('/interpreter/income/details')
                self.assertEqual(r_det.status_code, 200)
                self.assertIn("Chi tiết các khoản thu nhập", r_det.get_data(as_text=True))

                r_pay = c.get('/interpreter/income/payouts')
                self.assertEqual(r_pay.status_code, 200)
                self.assertIn("Theo dõi thanh toán", r_pay.get_data(as_text=True))
                self.assertIn("Ký quỹ Escrow", r_pay.get_data(as_text=True))

    def test_08_transactions_page_elements(self):
        """Kiểm tra trang Lịch sử giao dịch render đầy đủ bảng sổ cái, bộ lọc, thẻ KPI và modal chi tiết."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                resp = c.get('/interpreter/income/transactions')
                self.assertEqual(resp.status_code, 200)
                html = resp.get_data(as_text=True)
                self.assertIn("Lịch sử giao dịch", html)
                self.assertIn("Mã GD & Tham chiếu", html)
                self.assertIn("txDetailModal", html)

    def test_09_bank_info_page_render_and_modals(self):
        """Kiểm tra trang Thông tin nhận tiền render đầy đủ tiêu đề, modal thêm, modal xóa."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                resp = c.get('/interpreter/income/bank-info')
                self.assertEqual(resp.status_code, 200)
                html = resp.get_data(as_text=True)
                self.assertIn("Thông tin nhận tiền", html)
                self.assertIn("addMethodModal", html)
                self.assertIn("deleteMethodModal", html)
                self.assertIn("Thêm tài khoản nhận tiền", html)
                self.assertIn("Vietcombank", html)

    def test_10_bank_info_input_validation(self):
        """Kiểm tra xác thực đầu vào khi thêm tài khoản ngân hàng."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                # 1. Ngân hàng không hợp lệ
                r1 = c.post('/interpreter/income/bank-info', data={
                    'action': 'add',
                    'bank_code': 'INVALID_BANK',
                    'account_number': '1234567890',
                    'account_holder_name': 'TRANSLATOR TEST'
                }, follow_redirects=True)
                self.assertIn("Vui lòng chọn ngân hàng hợp lệ", r1.get_data(as_text=True))

                # 2. Số tài khoản có chữ cái hoặc quá ngắn
                r2 = c.post('/interpreter/income/bank-info', data={
                    'action': 'add',
                    'bank_code': 'VCB',
                    'account_number': '12abc34',
                    'account_holder_name': 'TRANSLATOR TEST'
                }, follow_redirects=True)
                self.assertIn("Số tài khoản ngân hàng không hợp lệ", r2.get_data(as_text=True))

    def test_11_bank_info_add_default_and_masking(self):
        """Kiểm tra luồng thêm phương thức nhận tiền hợp lệ, tự động đặt mặc định và che dữ liệu nhạy cảm."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            test_acc = "1029384756"
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                # Thêm tài khoản Vietcombank
                resp = c.post('/interpreter/income/bank-info', data={
                    'action': 'add',
                    'bank_code': 'VCB',
                    'account_number': test_acc,
                    'account_holder_name': 'nguyen van a',
                    'branch': 'Hội sở Hà Nội'
                }, follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                html = resp.get_data(as_text=True)
                self.assertIn("Đã thêm tài khoản ngân hàng", html)

                # Kiểm tra số tài khoản được che bảo mật trên giao diện
                masked = mask_account_number(test_acc)
                self.assertIn(masked, html)
                # Số tài khoản thô tuyệt đối không xuất hiện ở text thông thường
                self.assertNotIn(f"<span>{test_acc}</span>", html)

                # Tên chủ tài khoản được tự động viết hoa chuẩn hóa
                self.assertIn("NGUYEN VAN A", html)

    def test_12_bank_info_multiple_methods_and_set_default(self):
        """Kiểm tra quản lý nhiều phương thức và thay đổi phương thức mặc định."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                # Thêm tài khoản thứ hai (Techcombank)
                r_add = c.post('/interpreter/income/bank-info', data={
                    'action': 'add',
                    'bank_code': 'TCB',
                    'account_number': '1903699999999',
                    'account_holder_name': 'NGUYEN VAN A',
                    'branch': 'Chi nhánh Cầu Giấy'
                }, follow_redirects=True)
                self.assertIn("Techcombank", r_add.get_data(as_text=True))

                methods = get_payout_methods(translator.id)
                self.assertGreaterEqual(len(methods), 2)
                tcb_method = next((m for m in methods if m['bank_code'] == 'TCB'), None)
                self.assertIsNotNone(tcb_method)

                # Đặt Techcombank làm mặc định
                r_def = c.post('/interpreter/income/bank-info', data={
                    'action': 'set_default',
                    'method_id': tcb_method['id']
                }, follow_redirects=True)
                self.assertEqual(r_def.status_code, 200)
                self.assertIn("Đã cập nhật phương thức nhận tiền mặc định", r_def.get_data(as_text=True))

                # Kiểm tra lại trạng thái default trong store
                methods_after = get_payout_methods(translator.id)
                tcb_after = next((m for m in methods_after if m['id'] == tcb_method['id']), None)
                self.assertTrue(tcb_after['is_default'])

    def test_13_bank_info_delete_method(self):
        """Kiểm tra thao tác xóa phương thức nhận tiền an toàn."""
        with app.app_context():
            translator = User.query.filter_by(role='translator').first()
            if not translator:
                self.skipTest("Không tìm thấy user translator")

            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = translator.id

                methods_before = get_payout_methods(translator.id)
                if not methods_before:
                    self.skipTest("Chưa có phương thức nào để xóa")

                target_id = methods_before[-1]['id']

                resp = c.post('/interpreter/income/bank-info', data={
                    'action': 'delete',
                    'method_id': target_id
                }, follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Đã xóa phương thức nhận tiền thành công", resp.get_data(as_text=True))

                methods_after = get_payout_methods(translator.id)
                self.assertIsNone(next((m for m in methods_after if m['id'] == target_id), None))

    def test_14_cross_user_isolation(self):
        """Kiểm tra bảo mật cô lập: Translator A không thể thao tác trên phương thức của Translator B."""
        with app.app_context():
            translators = User.query.filter_by(role='translator').limit(2).all()
            if len(translators) < 2:
                self.skipTest("Cần ít nhất 2 user translator để kiểm tra phân quyền cô lập")

            user_a, user_b = translators[0], translators[1]

            # Thêm phương thức cho user_b
            success, b_method = add_payout_method(
                user_id=user_b.id,
                bank_code='MB',
                account_number='0987654321',
                account_holder_name='TRANSLATOR B'
            )

            # User A cố gắng xóa phương thức của user B
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = user_a.id

                resp = c.post('/interpreter/income/bank-info', data={
                    'action': 'delete',
                    'method_id': b_method['id']
                }, follow_redirects=True)
                self.assertIn("Phương thức nhận tiền không tồn tại hoặc bạn không có quyền thao tác", resp.get_data(as_text=True))

                # Xác nhận phương thức của B vẫn nguyên vẹn
                b_methods = get_payout_methods(user_b.id)
                self.assertTrue(any(m['id'] == b_method['id'] for m in b_methods))

if __name__ == '__main__':
    unittest.main()
