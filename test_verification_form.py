import unittest
import json
from datetime import datetime
from app import app
from models import db, User, TranslatorVerification, TranslatorProfile
from services.verification import (
    get_or_create_verification_draft,
    validate_step_data,
    save_verification_draft
)

class VerificationFormTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Find or create a test translator user
        self.user = User.query.filter_by(email='trans_test_verif@example.com').first()
        if not self.user:
            self.user = User(
                name='Nguyễn Văn Minh',
                email='trans_test_verif@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0912345678',
                role='translator'
            )
            db.session.add(self.user)
            db.session.commit()

        # Clear any existing verification for clean test
        TranslatorVerification.query.filter_by(user_id=self.user.id).delete()
        db.session.commit()

    def tearDown(self):
        # Cleanup
        TranslatorVerification.query.filter_by(user_id=self.user.id).delete()
        db.session.commit()
        self.ctx.pop()

    def test_01_get_or_create_draft(self):
        """Kiểm tra khởi tạo bản nháp mới tự động lấy thông tin từ User."""
        draft = get_or_create_verification_draft(self.user)
        self.assertIsNotNone(draft)
        self.assertEqual(draft.status, 'draft')
        self.assertEqual(draft.current_step, 1)
        self.assertEqual(draft.full_name, 'Nguyễn Văn Minh')
        self.assertEqual(draft.phone, '0912345678')

    def test_02_validation_step_1(self):
        """Kiểm tra logic validation Bước 1: Thông tin cá nhân."""
        # Thiếu họ tên, số điện thoại sai định dạng, tuổi < 18, bio quá ngắn
        invalid_data = {
            'full_name': 'A',
            'phone': '123',
            'gender': '',
            'dob': '2020-01-01',  # 4 tuổi
            'location': '',
            'bio': 'Ngắn'
        }
        is_valid, errors = validate_step_data(1, invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('full_name', errors)
        self.assertIn('phone', errors)
        self.assertIn('gender', errors)
        self.assertIn('dob', errors)
        self.assertIn('location', errors)
        self.assertIn('bio', errors)

        # Dữ liệu hợp lệ
        valid_data = {
            'full_name': 'Nguyễn Văn Minh',
            'phone': '0912345678',
            'gender': 'male',
            'dob': '1995-05-15',
            'location': 'Hà Nội',
            'bio': 'Phiên dịch viên chuyên nghiệp với hơn 5 năm kinh nghiệm dịch cabin hội nghị quốc tế.'
        }
        is_valid, errors = validate_step_data(1, valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_03_validation_step_2(self):
        """Kiểm tra logic validation Bước 2: Ngôn ngữ & Chiều phiên dịch."""
        # Ngôn ngữ nguồn trùng ngôn ngữ đích
        same_lang = {
            'source_language': 'Tiếng Việt',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'c1'
        }
        is_valid, errors = validate_step_data(2, same_lang)
        self.assertFalse(is_valid)
        self.assertIn('target_language', errors)

        # Hợp lệ
        valid_lang = {
            'source_language': 'Tiếng Việt',
            'target_language': 'Tiếng Anh',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'c1'
        }
        is_valid, errors = validate_step_data(2, valid_lang)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_04_validation_step_3(self):
        """Kiểm tra logic validation Bước 3: Lĩnh vực chuyên môn."""
        # Chưa chọn gì
        is_valid, errors = validate_step_data(3, {})
        self.assertFalse(is_valid)
        self.assertIn('specializations', errors)
        self.assertIn('interpreting_types', errors)

        # Hợp lệ
        valid_specs = {
            'specializations': ['Y tế & Dược phẩm', 'Công nghệ thông tin & Viễn thông'],
            'interpreting_types': ['Dịch song song / Cabin (Simultaneous)']
        }
        is_valid, errors = validate_step_data(3, valid_specs)
        self.assertTrue(is_valid)

    def test_05_validation_step_4_and_5(self):
        """Kiểm tra logic validation Bước 4 & Bước 5."""
        # Bước 4 hợp lệ
        valid_edu = {
            'education_level': 'Cử nhân (Đại học)',
            'university': 'ĐH Ngoại ngữ - ĐHQGHN',
            'major': 'Ngôn ngữ Anh',
            'certificate_type': 'IELTS',
            'certificate_name': 'IELTS 8.0',
            'cert_year': 2022
        }
        is_valid, errors = validate_step_data(4, valid_edu)
        self.assertTrue(is_valid)

        # Bước 5 hợp lệ
        valid_exp = {
            'experience_years': 5,
            'current_position': 'Chuyên viên phiên dịch cao cấp',
            'notable_clients': 'Samsung, Đại sứ quán',
            'featured_projects': 'Đảm nhận phiên dịch song song tại Diễn đàn Kinh tế Việt Nam 2023 và Hội nghị Cấp cao APEC.'
        }
        is_valid, errors = validate_step_data(5, valid_exp)
        self.assertTrue(is_valid)

    def test_06_database_persistence_and_reload(self):
        """Kiểm tra việc lưu nháp, sửa đổi và đọc lại từ DB (Reload test)."""
        # 1. Lưu nháp bước 1 & 2
        step1_data = {
            'full_name': 'Nguyễn Văn Minh',
            'phone': '0987654321',
            'gender': 'male',
            'dob': '1992-10-20',
            'location': 'Đà Nẵng',
            'bio': 'Phiên dịch viên tiếng Nhật N1 với 6 năm kinh nghiệm đàm phán hợp đồng thương mại.',
            'source_language': 'Tiếng Nhật',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'c2'
        }
        ok, verif, err = save_verification_draft(self.user, step1_data, target_step=2)
        self.assertTrue(ok)
        self.assertIsNotNone(verif)
        self.assertEqual(verif.current_step, 2)
        self.assertEqual(verif.phone, '0987654321')
        self.assertEqual(verif.location, 'Đà Nẵng')

        # 2. Giả lập người dùng tắt trình duyệt và tải lại trang:
        # Truy vấn trực tiếp từ DB mới
        db.session.expire_all()
        reloaded = TranslatorVerification.query.filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(reloaded)
        draft_dict = reloaded.get_draft_dict()
        self.assertEqual(draft_dict.get('full_name'), 'Nguyễn Văn Minh')
        self.assertEqual(draft_dict.get('phone'), '0987654321')
        self.assertEqual(draft_dict.get('location'), 'Đà Nẵng')
        self.assertEqual(draft_dict.get('source_language'), 'Tiếng Nhật')
        self.assertEqual(draft_dict.get('target_language'), 'Tiếng Việt')
        self.assertEqual(reloaded.current_step, 2)

        # 3. Người dùng sửa lại số điện thoại và địa điểm ở bước 1 rồi lưu lại
        update_data = {
            'phone': '0909999888',
            'location': 'TP. Hồ Chí Minh'
        }
        ok2, verif2, err2 = save_verification_draft(self.user, update_data, target_step=2)
        self.assertTrue(ok2)

        # 4. Kiểm tra lại sau khi cập nhật
        db.session.expire_all()
        reloaded2 = TranslatorVerification.query.filter_by(user_id=self.user.id).first()
        self.assertEqual(reloaded2.phone, '0909999888')
        self.assertEqual(reloaded2.location, 'TP. Hồ Chí Minh')
        # Các trường khác vẫn nguyên vẹn
        self.assertEqual(reloaded2.full_name, 'Nguyễn Văn Minh')
        self.assertEqual(reloaded2.source_language, 'Tiếng Nhật')

    def test_07_http_routes(self):
        """Kiểm tra các HTTP endpoint qua Flask test_client."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['user_name'] = self.user.name
            sess['user_role'] = 'translator'

        # GET form page
        resp = self.client.get('/account/verification/form')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Biểu Mẫu Khai Báo Thông Tin Xác Minh'.encode('utf-8'), resp.data)

        # POST save_draft via AJAX
        post_data = {
            'action': 'save_draft',
            'step': 1,
            'full_name': 'Nguyễn Văn Minh',
            'phone': '0912345678',
            'gender': 'male',
            'dob': '1995-05-15',
            'location': 'Hà Nội',
            'bio': 'Tóm tắt giới thiệu bản thân phiên dịch viên chuyên nghiệp.'
        }
        resp_post = self.client.post(
            '/account/verification/form',
            data=json.dumps(post_data),
            content_type='application/json',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_post.status_code, 200)
        res_json = json.loads(resp_post.data)
        self.assertTrue(res_json.get('success'))
        self.assertIn('Đã lưu nháp', res_json.get('message'))

        # POST next_step with invalid data should return 400
        invalid_post = {
            'action': 'next_step',
            'step': 1,
            'full_name': '',  # Empty
            'phone': 'invalid'
        }
        resp_invalid = self.client.post(
            '/account/verification/form',
            data=json.dumps(invalid_post),
            content_type='application/json',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_invalid.status_code, 400)
        res_inv_json = json.loads(resp_invalid.data)
        self.assertFalse(res_inv_json.get('success'))
        self.assertIn('full_name', res_inv_json.get('errors'))

if __name__ == '__main__':
    unittest.main()
