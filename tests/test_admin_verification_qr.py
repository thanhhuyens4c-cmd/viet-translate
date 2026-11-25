"""
tests/test_admin_verification_qr.py
Unit & Integration tests cho Bước 4: Giao diện Quản trị viên (Admin Review Assistant)
và kế thừa trạng thái xác minh số vào TranslatorProfile.
Bao gồm TC-4.1 đến TC-4.5.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import json
from app import app
from models import db, User, TranslatorVerification, TranslatorProfile
from services.verification import review_verification_request


class AdminVerificationQRTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo Super Admin
        self.admin = User.query.filter_by(email='super_admin_cert_test@example.com').first()
        if not self.admin:
            self.admin = User(
                name='Super Admin Reviewer',
                email='super_admin_cert_test@example.com',
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
            self.admin.admin_role = 'super_admin'
            db.session.commit()

        # Tạo translator 1 có chứng thực số
        self.user_online = User.query.filter_by(email='pdv_online_qr@example.com').first()
        if not self.user_online:
            self.user_online = User(
                name='Đặng Hoàng Long',
                email='pdv_online_qr@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.user_online)
            db.session.commit()

        # Tạo profile cho translator 1
        self.profile_online = TranslatorProfile.query.filter_by(user_id=self.user_online.id).first()
        if not self.profile_online:
            self.profile_online = TranslatorProfile(user_id=self.user_online.id)
            db.session.add(self.profile_online)
            db.session.commit()

        # Tạo hồ sơ verification có link QR
        TranslatorVerification.query.filter_by(user_id=self.user_online.id).delete()
        self.verif_online = TranslatorVerification(
            user_id=self.user_online.id,
            status='pending',
            certificate_type='IELTS',
            certificate_name='IELTS Academic 8.0',
            certificate_id='TRF-2024-998811',
            verification_url='https://www.credly.com/badges/ielts-8-long',
            verification_source='credly',
            verification_metadata=json.dumps({
                'cert_name': 'IELTS Academic 8.0',
                'recipient_name': 'Dang Hoang Long',
                'name_match': True,
                'issued_date': '2024-05-10',
                'is_expired': False
            }),
            is_online_verified=True
        )
        db.session.add(self.verif_online)

        # Tạo translator 2 truyền thống (không có link QR)
        self.user_trad = User.query.filter_by(email='pdv_trad_test@example.com').first()
        if not self.user_trad:
            self.user_trad = User(
                name='Lê Văn Truyền',
                email='pdv_trad_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.user_trad)
            db.session.commit()

        TranslatorVerification.query.filter_by(user_id=self.user_trad.id).delete()
        self.verif_trad = TranslatorVerification(
            user_id=self.user_trad.id,
            status='pending',
            certificate_type='Bằng Cử Nhân',
            certificate_name='Cử nhân Ngoại ngữ',
            verification_url=None,
            is_online_verified=False
        )
        db.session.add(self.verif_trad)
        db.session.commit()

    def tearDown(self):
        self.ctx.pop()

    def test_tc4_1_admin_detail_shows_assistant_box(self):
        """TC-4.1: Trang admin hiển thị Trợ lý Thẩm định Trực tuyến và bảng đối soát khi có link"""
        from datetime import datetime
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id
            sess['admin_role'] = 'super_admin'
            sess['admin_session_created'] = now_ts
            sess['admin_session_last_seen'] = now_ts
            sess['admin_csrf_token'] = 'test_token'

        res = self.client.get(f'/admin/verifications/{self.verif_online.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Trợ Lý Thẩm Định Trực Tuyến', html)
        self.assertIn('Đã kiểm thực số', html)
        self.assertIn('Tên miền chính thức được bảo đảm', html)
        self.assertIn('Dang Hoang Long', html)
        self.assertIn('Khớp 100%', html)
        self.assertIn('https://www.credly.com/badges/ielts-8-long', html)

    def test_tc4_2_admin_detail_traditional_cert_notice(self):
        """TC-4.2: Trang admin hiển thị thông báo nhã nhặn khi là hồ sơ truyền thống"""
        from datetime import datetime
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id
            sess['admin_role'] = 'super_admin'
            sess['admin_session_created'] = now_ts
            sess['admin_session_last_seen'] = now_ts
            sess['admin_csrf_token'] = 'test_token'

        res = self.client.get(f'/admin/verifications/{self.verif_trad.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Hồ sơ truyền thống', html)
        self.assertIn('Ứng viên không đính kèm đường link kiểm thực số', html)

    def test_tc4_3_approve_verification_updates_digital_credential_on_profile(self):
        """TC-4.3 & TC-4.4: Khi Admin phê duyệt, TranslatorProfile được gán huy hiệu số và link gốc"""
        checklist_data = {
            'A1': True, 'A2': True, 'A3': True, 'A4': True, 'A5': True,
            'B1': True, 'B2': True, 'B3': True, 'B4': True,
            'C1': True, 'C2': True, 'C3': True, 'C4': True, 'C5': True,
            'D1': True, 'D2': True
        }

        ok, msg = review_verification_request(
            verification_id=self.verif_online.id,
            admin_user=self.admin,
            action='approve',
            checklist_data=checklist_data
        )

        self.assertTrue(ok, f"Review failed: {msg}")

        # Kiểm tra trạng thái hồ sơ verification
        verif = TranslatorVerification.query.get(self.verif_online.id)
        self.assertEqual(verif.status, 'approved')

        # Kiểm tra kế thừa trên TranslatorProfile
        profile = TranslatorProfile.query.filter_by(user_id=self.user_online.id).first()
        self.assertTrue(profile.is_verified)
        self.assertTrue(profile.has_digital_credential)
        self.assertEqual(profile.credential_public_url, 'https://www.credly.com/badges/ielts-8-long')
        self.assertEqual(profile.credential_issuer, 'credly')
        self.assertEqual(profile.credential_badge_name, 'IELTS Academic 8.0')


if __name__ == '__main__':
    unittest.main()
