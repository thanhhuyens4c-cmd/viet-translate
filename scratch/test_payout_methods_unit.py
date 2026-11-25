import sys
import os
import unittest
import json
import shutil

# Thêm đường dẫn project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.payout_methods import (
    get_supported_banks,
    mask_account_number,
    normalize_account_holder_name,
    add_payout_method,
    get_payout_methods,
    get_default_payout_method,
    get_payout_method_by_id,
    set_default_payout_method,
    delete_payout_method,
    get_user_payout_data,
    _get_store_path
)

class PayoutMethodsServiceTest(unittest.TestCase):
    def setUp(self):
        # Dùng file json tạm cho test để không ảnh hưởng dữ liệu thật
        self.original_store = _get_store_path()
        self.test_store = self.original_store + ".test.json"
        
        import services.payout_methods as pm
        self._orig_func = pm._get_store_path
        pm._get_store_path = lambda: self.test_store
        
        if os.path.exists(self.test_store):
            os.remove(self.test_store)

    def tearDown(self):
        import services.payout_methods as pm
        pm._get_store_path = self._orig_func
        if os.path.exists(self.test_store):
            os.remove(self.test_store)

    def test_01_supported_banks_catalog(self):
        """Kiểm tra danh mục các ngân hàng Việt Nam hỗ trợ."""
        banks = get_supported_banks()
        self.assertGreaterEqual(len(banks), 10)
        codes = [b['code'] for b in banks]
        self.assertIn('VCB', codes)
        self.assertIn('TCB', codes)
        self.assertIn('BIDV', codes)
        self.assertIn('MB', codes)

    def test_02_mask_account_number(self):
        """Kiểm tra che số tài khoản: chỉ hiện 4 số cuối, tuyệt đối không lộ phần đầu."""
        masked1 = mask_account_number("0123456789")
        self.assertTrue(masked1.endswith("6789"))
        self.assertIn("••••", masked1)
        self.assertNotIn("012345", masked1)

        masked2 = mask_account_number("19036888888888")
        self.assertTrue(masked2.endswith("8888"))
        self.assertNotIn("190368", masked2)

    def test_03_normalize_holder_name(self):
        """Kiểm tra chuẩn hóa tên chủ tài khoản thành in hoa không khoảng trắng thừa."""
        self.assertEqual(normalize_account_holder_name("  nguyen   van a  "), "NGUYEN VAN A")
        self.assertEqual(normalize_account_holder_name("Trần Thị B"), "TRẦN THỊ B")

    def test_04_validation_invalid_bank_or_account(self):
        """Kiểm tra kiểm tra tính hợp lệ dữ liệu đầu vào."""
        # Ngân hàng không hợp lệ
        ok, msg = add_payout_method(1, "INVALID", "1234567890", "NGUYEN VAN A")
        self.assertFalse(ok)
        self.assertIn("Vui lòng chọn ngân hàng hợp lệ", msg)

        # Số tài khoản quá ngắn (<6 ký tự)
        ok, msg = add_payout_method(1, "VCB", "12345", "NGUYEN VAN A")
        self.assertFalse(ok)
        self.assertIn("Số tài khoản ngân hàng không hợp lệ", msg)

        # Số tài khoản chứa chữ
        ok, msg = add_payout_method(1, "VCB", "12345abc", "NGUYEN VAN A")
        self.assertFalse(ok)
        self.assertIn("Số tài khoản ngân hàng không hợp lệ", msg)

        # Tên chủ tài khoản quá ngắn
        ok, msg = add_payout_method(1, "VCB", "1234567890", "A")
        self.assertFalse(ok)
        self.assertIn("Tên chủ tài khoản", msg)

    def test_05_add_first_method_becomes_default(self):
        """Tài khoản đầu tiên thêm vào tự động trở thành mặc định."""
        user_id = 101
        ok, m1 = add_payout_method(user_id, "VCB", "0123456789", "nguyen van a", branch="CN Ba Đình")
        self.assertTrue(ok)
        self.assertTrue(m1["is_default"])
        self.assertEqual(m1["bank_short_name"], "Vietcombank")
        self.assertEqual(m1["account_holder_name"], "NGUYEN VAN A")
        self.assertEqual(m1["status"], "active")

        methods = get_payout_methods(user_id)
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0]["id"], m1["id"])

        def_method = get_default_payout_method(user_id)
        self.assertEqual(def_method["id"], m1["id"])

    def test_06_prevent_duplicate_account(self):
        """Không cho phép thêm trùng lặp số tài khoản tại cùng một ngân hàng."""
        user_id = 102
        ok1, _ = add_payout_method(user_id, "TCB", "19036888888888", "TRAN VAN B")
        self.assertTrue(ok1)

        ok2, msg2 = add_payout_method(user_id, "TCB", "19036888888888", "TRAN VAN B")
        self.assertFalse(ok2)
        self.assertIn("đã tồn tại trong danh sách", msg2)

    def test_07_add_second_method_and_set_default(self):
        """Thêm tài khoản thứ hai và thay đổi tài khoản mặc định."""
        user_id = 103
        ok1, m1 = add_payout_method(user_id, "VCB", "0123456789", "LE VAN C")
        self.assertTrue(ok1)
        self.assertTrue(m1["is_default"])

        ok2, m2 = add_payout_method(user_id, "BIDV", "12410001234567", "LE VAN C", branch="CN Cầu Giấy")
        self.assertTrue(ok2)
        self.assertFalse(m2["is_default"])  # Mặc định ban đầu vẫn là m1

        # Đặt m2 làm mặc định
        ok_def, msg_def = set_default_payout_method(user_id, m2["id"])
        self.assertTrue(ok_def)

        # Kiểm tra lại
        def_m = get_default_payout_method(user_id)
        self.assertEqual(def_m["id"], m2["id"])

        methods = get_payout_methods(user_id)
        m1_updated = next(m for m in methods if m["id"] == m1["id"])
        m2_updated = next(m for m in methods if m["id"] == m2["id"])
        self.assertFalse(m1_updated["is_default"])
        self.assertTrue(m2_updated["is_default"])

    def test_08_delete_method_and_default_promotion(self):
        """Khi xóa phương thức mặc định, phương thức còn lại tự động thăng cấp thành mặc định mới."""
        user_id = 104
        ok1, m1 = add_payout_method(user_id, "VCB", "0123456789", "PHAM THI D")
        ok2, m2 = add_payout_method(user_id, "MB", "0680123456789", "PHAM THI D")

        # m1 đang là default
        self.assertTrue(m1["is_default"])

        # Xóa m1
        ok_del, msg_del = delete_payout_method(user_id, m1["id"])
        self.assertTrue(ok_del)

        methods_after = get_payout_methods(user_id)
        self.assertEqual(len(methods_after), 1)
        self.assertEqual(methods_after[0]["id"], m2["id"])
        # m2 tự động trở thành mặc định
        self.assertTrue(methods_after[0]["is_default"])

    def test_09_user_isolation(self):
        """Bảo đảm cô lập giữa các user: User A không xem hoặc thao tác được phương thức của User B."""
        user_a = 201
        user_b = 202

        ok_a, m_a = add_payout_method(user_a, "VCB", "0111111111", "USER A")
        ok_b, m_b = add_payout_method(user_b, "TCB", "0222222222", "USER B")

        # User A chỉ thấy phương thức của mình
        methods_a = get_payout_methods(user_a)
        self.assertEqual(len(methods_a), 1)
        self.assertEqual(methods_a[0]["id"], m_a["id"])

        # User A không tìm thấy phương thức của User B
        self.assertIsNone(get_payout_method_by_id(user_a, m_b["id"]))

        # User A không thể xóa phương thức của User B
        ok_del, msg = delete_payout_method(user_a, m_b["id"])
        self.assertFalse(ok_del)

        # Phương thức của User B vẫn tồn tại
        self.assertIsNotNone(get_payout_method_by_id(user_b, m_b["id"]))

    def test_10_audit_history_logging(self):
        """Kiểm tra ghi nhận lịch sử thay đổi thông tin nhận tiền."""
        user_id = 301
        add_payout_method(user_id, "ACB", "123456789", "VO VAN E")
        data = get_user_payout_data(user_id)
        history = data.get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action"], "add")
        self.assertIn("ACB", history[0]["summary"])
        # Kiểm tra không ghi số tài khoản thô
        self.assertNotIn("123456789", json.dumps(history))

if __name__ == '__main__':
    unittest.main()
