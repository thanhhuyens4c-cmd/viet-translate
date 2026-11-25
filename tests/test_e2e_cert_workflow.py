"""
tests/test_e2e_cert_workflow.py
End-to-End (E2E) Integration Tests cho Hệ thống Xác minh Chứng chỉ
qua mã QR & Digital Badge (0 đồng).
Bao gồm TC-5.1 đến TC-5.4.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import json
from datetime import datetime

from app import app
from models import db, User, TranslatorProfile, TranslatorVerification, VerificationDocument
from services.verification import (
    get_or_create_verification_draft,
    save_verification_draft,
    submit_verification_for_review,
    review_verification_request
)


class E2ECertVerificationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # 1. Super Admin
        self.admin = User.query.filter_by(email='e2e_super_admin@example.com').first()
        if not self.admin:
            self.admin = User(
                name='Admin Tổng',
                email='e2e_super_admin@example.com',
                password_hash='pbkdf2:sha256:test',
                role='admin',
                admin_role='super_admin',
                is_admin=True,
                is_active=True
            )
            db.session.add(self.admin)
            db.session.commit()
        else:
            self.admin.is_admin = True
            self.admin.is_active = True
            db.session.commit()

        # 2. Doanh nghiệp (Hirer)
        self.hirer = User.query.filter_by(email='e2e_hirer@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Tập Đoàn Công Nghệ SunTech',
                email='e2e_hirer@example.com',
                password_hash='pbkdf2:sha256:test',
                role='hirer',
                is_active=True
            )
            db.session.add(self.hirer)
            db.session.commit()

        # 3. Phiên dịch viên E2E
        self.translator = User.query.filter_by(email='e2e_translator@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Vũ Minh Khang',
                email='e2e_translator@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator',
                is_active=True
            )
            db.session.add(self.translator)
            db.session.commit()

        # Profile phiên dịch viên
        self.profile = TranslatorProfile.query.filter_by(user_id=self.translator.id).first()
        if not self.profile:
            self.profile = TranslatorProfile(
                user_id=self.translator.id,
                title='Chuyên gia Phiên dịch Hội thảo Tiếng Anh',
                languages='Tiếng Anh, Tiếng Việt',
                is_public=True
            )
            db.session.add(self.profile)
            db.session.commit()

        # Dọn dẹp dữ liệu cũ của phiên dịch viên này
        VerificationDocument.query.filter_by(user_id=self.translator.id).delete()
        TranslatorVerification.query.filter_by(user_id=self.translator.id).delete()
        self.profile.is_verified = False
        self.profile.has_digital_credential = False
        self.profile.credential_public_url = None
        db.session.commit()

    def tearDown(self):
        self.ctx.pop()

    def test_tc5_1_and_5_2_hirer_profile_visibility(self):
        """TC-5.1 & TC-5.2: Doanh nghiệp xem hồ sơ hiển thị chuẩn xác huy hiệu và link kiểm thực gốc"""
        # Trạng thái ban đầu: chưa có chứng thực số
        res = self.client.get(f'/translator/{self.profile.id}')
        if res.status_code == 200:
            html = res.get_data(as_text=True)
            self.assertNotIn('🌐 Chứng thực số', html)

        # Cấp chứng thực số cho profile
        self.profile.is_verified = True
        self.profile.has_digital_credential = True
        self.profile.credential_public_url = 'https://www.credly.com/badges/sample-e2e-badge'
        self.profile.credential_issuer = 'Credly Digital Badge'
        self.profile.cert_name = 'IELTS 8.5'
        db.session.commit()

        res2 = self.client.get(f'/translator/{self.profile.id}')
        self.assertEqual(res2.status_code, 200)
        html2 = res2.get_data(as_text=True)

        self.assertIn('🌐 Chứng thực số (Live Verified)', html2)
        self.assertIn('https://www.credly.com/badges/sample-e2e-badge', html2)
        self.assertIn('Xem chứng chỉ gốc tại Credly Digital Badge', html2)
        self.assertIn('Đã kiểm thực trực tuyến từ cơ sở dữ liệu số', html2)

    def test_tc5_3_api_translators_returns_digital_credential_flag(self):
        """TC-5.3: API /api/translators trả về trường has_digital_credential cho Card"""
        self.profile.is_verified = True
        self.profile.has_digital_credential = True
        self.profile.credential_issuer = 'Credly'
        self.profile.rating = 5.0
        db.session.commit()

        res = self.client.get('/api/translators')
        self.assertEqual(res.status_code, 200)
        cards = res.get_json()
        target_card = next((c for c in cards if c.get('user_id') == self.translator.id), None)
        self.assertIsNotNone(target_card, "Translator card not found in API")
        self.assertTrue(target_card.get('has_digital_credential'))
        self.assertEqual(target_card.get('credential_issuer'), 'Credly')

    def test_tc5_4_complete_end_to_end_journey(self):
        """TC-5.4: Toàn bộ quy trình khép kín: PDV khai báo QR -> Hệ thống lưu -> Admin duyệt -> Khách xem"""
        # Bước A: Khởi tạo draft cho PDV
        draft = get_or_create_verification_draft(self.translator)

        # Thêm tài liệu CV bắt buộc
        cv = VerificationDocument(
            verification_id=draft.id,
            user_id=self.translator.id,
            document_type='cv',
            original_filename='cv_minh_khang.pdf',
            stored_filename='cv_minh_khang_stored.pdf',
            storage_provider='local_private',
            storage_path='/test/cv.pdf',
            file_size=2048,
            mime_type='application/pdf',
            file_extension='pdf',
            status='uploaded',
            is_active=True
        )
        db.session.add(cv)
        db.session.commit()

        # Bước B: PDV lưu thông tin quét QR
        cert_payload = {
            'full_name': 'Vũ Minh Khang',
            'phone': '0988776655',
            'gender': 'male',
            'dob': '1992-08-20',
            'location': 'TP. Hồ Chí Minh',
            'bio': 'Phiên dịch viên cabin cấp cao với hơn 8 năm kinh nghiệm.',
            'source_language': 'Tiếng Anh',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'native',
            'specializations': 'Tài chính, Y tế, Hội thảo',
            'interpreting_types': 'Simultaneous, Consecutive',
            'education_level': 'Thạc sĩ',
            'university': 'Đại học Khoa học Xã hội và Nhân văn TP.HCM',
            'major': 'Ngôn ngữ Anh',
            'certificate_type': 'IELTS',
            'certificate_name': 'IELTS Academic 8.5',
            'cert_year': 2024,
            'certificate_id': 'TRF-VN-2024-8899',
            'verification_url': 'https://www.credly.com/badges/khang-ielts-85',
            'verification_source': 'credly',
            'verification_metadata': json.dumps({
                'cert_name': 'IELTS Academic 8.5',
                'recipient_name': 'Vu Minh Khang',
                'name_match': True,
                'issued_date': '2024-03-01'
            }),
            'is_online_verified': 'true',
            'experience_years': 8,
            'current_position': 'Lead Conference Interpreter',
            'notable_clients': 'UNESCO, World Bank, Vinamilk',
            'featured_projects': 'Hội nghị Thượng đỉnh Kinh tế Châu Á - Thái Bình Dương 2024.',
            'notes': 'Chứng chỉ đã được quét QR và kiểm thực qua Credly.'
        }

        # Submit hồ sơ
        ok_submit, msg_submit, _ = submit_verification_for_review(
            user=self.translator,
            form_data=cert_payload,
            confirmed=True
        )
        self.assertTrue(ok_submit, f"Submission failed: {msg_submit}")

        verif_record = TranslatorVerification.query.filter_by(user_id=self.translator.id).first()
        self.assertEqual(verif_record.status, 'pending')
        self.assertTrue(verif_record.is_online_verified)

        # Bước C: Admin thẩm định và Phê duyệt
        checklist = {
            'A1': True, 'A2': True, 'A3': True, 'A4': True, 'A5': True,
            'B1': True, 'B2': True, 'B3': True, 'B4': True,
            'C1': True, 'C2': True, 'C3': True, 'C4': True, 'C5': True,
            'D1': True, 'D2': True
        }

        ok_approve, msg_approve = review_verification_request(
            verification_id=verif_record.id,
            admin_user=self.admin,
            action='approve',
            checklist_data=checklist
        )
        self.assertTrue(ok_approve, f"Approval failed: {msg_approve}")

        # Bước D: Kiểm tra dữ liệu được đồng bộ lên Profile công khai
        profile_after = TranslatorProfile.query.filter_by(user_id=self.translator.id).first()
        self.assertTrue(profile_after.is_verified)
        self.assertTrue(profile_after.has_digital_credential)
        self.assertEqual(profile_after.credential_public_url, 'https://www.credly.com/badges/khang-ielts-85')
        self.assertEqual(profile_after.credential_issuer, 'credly')

        # Bước E: Khách hàng truy cập xem hồ sơ công khai
        res_view = self.client.get(f'/translator/{profile_after.id}')
        self.assertEqual(res_view.status_code, 200)
        html_view = res_view.get_data(as_text=True)

        self.assertIn('🌐 Chứng thực số (Live Verified)', html_view)
        self.assertIn('https://www.credly.com/badges/khang-ielts-85', html_view)
        self.assertIn('Đã kiểm thực trực tuyến từ cơ sở dữ liệu số', html_view)


if __name__ == '__main__':
    unittest.main()

