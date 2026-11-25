"""
tests/test_verification_form_qr.py
Unit & Integration tests cho Bước 3: Giao diện Phiên Dịch Viên,
Biểu mẫu xác minh có trường QR/Digital Badge và lưu trữ dữ liệu.
Bao gồm TC-3.1 đến TC-3.5.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import json
from app import app
from models import db, User, TranslatorVerification, VerificationDocument
from services.verification import (
    save_verification_draft,
    submit_verification_for_review,
    get_or_create_verification_draft
)


class VerificationFormQRTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo translator test user
        self.user = User.query.filter_by(email='test_form_qr_pdv@example.com').first()
        if not self.user:
            self.user = User(
                name='Phạm Thị Hồng',
                email='test_form_qr_pdv@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.user)
            db.session.commit()

        # Dọn dẹp hồ sơ cũ nếu có
        VerificationDocument.query.filter_by(user_id=self.user.id).delete()
        TranslatorVerification.query.filter_by(user_id=self.user.id).delete()
        db.session.commit()

        self.draft = get_or_create_verification_draft(self.user)

    def tearDown(self):
        self.ctx.pop()

    def test_tc3_1_form_html_contains_qr_elements(self):
        """TC-3.1: Trang biểu mẫu xác minh chứa đầy đủ các trường QR và Digital Badge"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        res = self.client.get('/account/verification/form')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('input-verification_url', html)
        self.assertIn('input-certificate_id', html)
        self.assertIn('qr-scan-input', html)
        self.assertIn('cert-precheck-box', html)
        self.assertIn('rev-verification_status', html)

    def test_tc3_2_save_draft_with_online_cert(self):
        """TC-3.2: Lưu nháp hồ sơ kèm thông tin QR/Digital Badge thành công"""
        form_payload = {
            'certificate_type': 'TOPIK',
            'certificate_name': 'TOPIK Level 6',
            'cert_year': 2023,
            'certificate_id': 'TOPIK-2023-9988',
            'verification_url': 'https://www.credly.com/badges/topik-6-sample',
            'verification_source': 'credly',
            'verification_metadata': json.dumps({'cert_name': 'TOPIK 6', 'issuer': 'NIIED'}),
            'is_online_verified': 'true'
        }

        ok, verif, msg = save_verification_draft(self.user, form_payload, target_step=4)
        self.assertTrue(ok, f"Save draft failed: {msg}")

        # Kiểm tra dữ liệu được lưu trong database
        saved_verif = TranslatorVerification.query.filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(saved_verif)
        self.assertEqual(saved_verif.certificate_id, 'TOPIK-2023-9988')
        self.assertEqual(saved_verif.verification_url, 'https://www.credly.com/badges/topik-6-sample')
        self.assertEqual(saved_verif.verification_source, 'credly')
        self.assertTrue(saved_verif.is_online_verified)
        self.assertIn('TOPIK 6', saved_verif.verification_metadata)

    def test_tc3_3_submit_full_verification_with_online_cert(self):
        """TC-3.3 & TC-3.5: Nộp hồ sơ xét duyệt đầy đủ kèm CV và thông tin chứng thực số"""
        # 1. Thêm tài liệu CV bắt buộc để đạt điều kiện nộp
        cv_doc = VerificationDocument(
            verification_id=self.draft.id,
            user_id=self.user.id,
            document_type='cv',
            original_filename='cv_pham_thi_hong.pdf',
            stored_filename='test_cv_pham_thi_hong_stored.pdf',
            storage_provider='local_private',
            storage_path='/test/cv.pdf',
            file_size=1024,
            mime_type='application/pdf',
            file_extension='pdf',
            status='uploaded',
            is_active=True
        )
        db.session.add(cv_doc)
        db.session.commit()

        form_payload = {
            'full_name': 'Phạm Thị Hồng',
            'phone': '0901234567',
            'gender': 'female',
            'dob': '1995-05-15',
            'location': 'Hà Nội',
            'bio': 'Phiên dịch viên chuyên nghiệp tiếng Anh và tiếng Hàn với nhiều năm kinh nghiệm thực chiến.',
            'source_language': 'Tiếng Hàn',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'c2',
            'specializations': 'Thương mại, Hội thảo',
            'interpreting_types': 'Simultaneous, Consecutive',
            'education_level': 'Đại học',
            'university': 'Đại học Ngoại ngữ Hà Nội',
            'major': 'Ngôn ngữ Hàn Quốc',
            'certificate_type': 'TOPIK',
            'certificate_name': 'TOPIK Level 6',
            'cert_year': 2023,
            'certificate_id': 'TOPIK-2023-9988',
            'verification_url': 'https://www.credly.com/badges/topik-6-sample',
            'verification_source': 'credly',
            'verification_metadata': json.dumps({'cert_name': 'TOPIK 6'}),
            'is_online_verified': 'true',
            'experience_years': 4,
            'current_position': 'Senior Korean Interpreter',
            'notable_clients': 'Samsung, LG Electronics',
            'featured_projects': 'Dự án thông dịch hội nghị cấp cao công nghệ 2023 đạt chuẩn hơn 30 ký tự.',
            'notes': 'Tôi đã đính kèm link xác thực Credly.'
        }

        ok, msg, meta = submit_verification_for_review(
            user=self.user,
            form_data=form_payload,
            confirmed=True
        )

        self.assertTrue(ok, f"Submit failed: {msg} - Errors: {meta.get('errors')}")

        verif = TranslatorVerification.query.filter_by(user_id=self.user.id).first()
        self.assertEqual(verif.status, 'pending')
        self.assertTrue(verif.is_online_verified)
        self.assertEqual(verif.certificate_id, 'TOPIK-2023-9988')


if __name__ == '__main__':
    unittest.main()
