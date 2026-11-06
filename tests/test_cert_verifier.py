"""
tests/test_cert_verifier.py
Unit & Integration tests cho Bước 2: Bộ bóc tách dữ liệu chứng chỉ
(Backend Parser Engine) và API Pre-check.
Bao gồm TC-2.1 đến TC-2.6.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock

from app import app
from models import db, User
from services.cert_verifier import (
    remove_accents,
    calculate_name_match,
    extract_cert_data_from_html,
    verify_certificate
)


class CertVerifierTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo hoặc lấy user translator để test API
        self.translator = User.query.filter_by(email='test_verifier_pdv@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Nguyễn Văn Đạt',
                email='test_verifier_pdv@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.translator)
            db.session.commit()

        # Tạo hoặc lấy user hirer để test phân quyền API
        self.hirer = User.query.filter_by(email='test_verifier_hirer@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Công ty Dịch thuật ABC',
                email='test_verifier_hirer@example.com',
                password_hash='pbkdf2:sha256:test',
                role='hirer'
            )
            db.session.add(self.hirer)
            db.session.commit()

    def tearDown(self):
        self.ctx.pop()

    def test_tc2_1_json_ld_open_badges_parsing(self):
        """TC-2.1: Bóc tách cấu trúc JSON-LD Open Badges v2/v3"""
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://w3id.org/openbadges/v2",
                "type": "Assertion",
                "id": "https://www.credly.com/badges/sample-123",
                "badge": {
                    "name": "IELTS Academic Band 8.5 Master",
                    "description": "High level English proficiency certification",
                    "issuer": {
                        "name": "British Council & IDP"
                    }
                },
                "recipient": {
                    "type": "email",
                    "name": "Nguyen Van Dat",
                    "identity": "dat@example.com"
                },
                "issuedOn": "2024-06-15T00:00:00Z"
            }
            </script>
        </head>
        <body>Chứng chỉ Credly</body>
        </html>
        """
        data = extract_cert_data_from_html(mock_html)
        self.assertEqual(data['cert_name'], 'IELTS Academic Band 8.5 Master')
        self.assertEqual(data['recipient_name'], 'Nguyen Van Dat')
        self.assertEqual(data['issued_date'], '2024-06-15')
        self.assertEqual(data['parse_method'], 'json-ld')
        self.assertFalse(data['is_expired'])

    def test_tc2_2_open_graph_fallback_parsing(self):
        """TC-2.2: Fallback sang thẻ Open Graph meta tags khi không có JSON-LD"""
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="og:title" content="JLPT N1 Certificate issued to Tran Thi Mai by Japan Foundation" />
            <meta property="og:description" content="Official Japanese Language Proficiency Test certificate." />
            <meta property="og:site_name" content="Japan Foundation" />
        </head>
        <body>Trang chứng nhận JLPT</body>
        </html>
        """
        data = extract_cert_data_from_html(mock_html)
        self.assertIn('JLPT N1 Certificate', data['cert_name'])
        self.assertEqual(data['recipient_name'], 'Tran Thi Mai')
        self.assertEqual(data['issuer_name'], 'Japan Foundation')
        self.assertEqual(data['parse_method'], 'open-graph')

    def test_tc2_3_accent_insensitive_name_matching(self):
        """TC-2.3: Thuật toán so khớp tên không phân biệt dấu và thứ tự"""
        # Trùng khớp hoàn toàn bỏ dấu
        is_match, score = calculate_name_match('Nguyễn Văn Đạt', 'Nguyen Van Dat')
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

        # Đảo thứ tự tên (International format)
        is_match2, score2 = calculate_name_match('Nguyễn Văn Đạt', 'Dat Nguyen Van')
        self.assertTrue(is_match2)
        self.assertEqual(score2, 1.0)

        # Viết hoa / thường lẫn lộn
        is_match3, score3 = calculate_name_match('TRẦN THỊ MỸ DUYÊN', 'tran thi my duyen')
        self.assertTrue(is_match3)
        self.assertEqual(score3, 1.0)

    def test_tc2_4_name_mismatch_detection(self):
        """TC-2.4: Phát hiện không trùng khớp khi dùng chứng chỉ của người khác"""
        is_match, score = calculate_name_match('Nguyễn Văn Đạt', 'Lê Hoàng Nam')
        self.assertFalse(is_match)
        self.assertLess(score, 0.5)

    @patch('services.cert_verifier.fetch_url_html')
    def test_tc2_5_network_error_and_timeout_handling(self, mock_fetch):
        """TC-2.5: Xử lý an toàn khi mạng timeout hoặc lỗi 404/500"""
        mock_fetch.return_value = (None, "Yêu cầu kết nối quá thời gian chờ (Timeout sau 5s)")

        res = verify_certificate(
            user_name='Nguyễn Văn Đạt',
            raw_url='https://www.credly.com/badges/timeout-test'
        )
        self.assertFalse(res['success'])
        self.assertFalse(res['is_valid'])
        self.assertIn('Timeout', res['error'])

    def test_tc2_6_api_precheck_endpoint_permissions_and_response(self):
        """TC-2.6: Kiểm tra API Pre-check /api/account/verification/precheck-cert"""
        # 1. Chưa đăng nhập -> 302 Redirect hoặc 401
        res = self.client.post('/api/account/verification/precheck-cert', json={'url': 'https://www.credly.com/test'})
        self.assertIn(res.status_code, [302, 401])

        # 2. Đăng nhập bằng Hirer -> 403 Forbidden
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.hirer.id
        res_hirer = self.client.post('/api/account/verification/precheck-cert', json={'url': 'https://www.credly.com/test'})
        self.assertEqual(res_hirer.status_code, 403)

        # 3. Đăng nhập bằng Translator -> Thành công gọi API
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        # Mock verify_certificate để test controller
        with patch('services.cert_verifier.fetch_url_html') as mock_fetch:
            mock_fetch.return_value = ("""
            <script type="application/ld+json">
            {
                "@context": "https://w3id.org/openbadges/v2",
                "badge": {"name": "TOPIK Level 6 Master"},
                "recipient": {"name": "Nguyen Van Dat"}
            }
            </script>
            """, None)

            res_pdv = self.client.post(
                '/api/account/verification/precheck-cert',
                json={'url': 'https://www.credly.com/badges/topik-sample', 'certificate_name': 'TOPIK 6'}
            )
            self.assertEqual(res_pdv.status_code, 200)
            data = res_pdv.get_json()
            self.assertTrue(data['success'])
            self.assertTrue(data['is_valid'])
            self.assertEqual(data['cert_name'], 'TOPIK Level 6 Master')
            self.assertTrue(data['name_match'])


if __name__ == '__main__':
    unittest.main()
