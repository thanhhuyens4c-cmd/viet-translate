"""
tests/test_cert_whitelist.py
Unit tests cho Bước 1: Danh sách tên miền tin cậy (Domain Whitelist)
và Schema cơ sở dữ liệu cho kiểm thực chứng chỉ trực tuyến.
Bao gồm TC-1.1 đến TC-1.7.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
from services.cert_whitelist import (
    is_whitelisted_domain,
    normalize_cert_url,
    get_issuer_info,
    get_issuer_display_name,
    OFFICIAL_CERT_WHITELIST
)
from app import app
from models import db, User, TranslatorProfile, TranslatorVerification


class CertWhitelistTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_tc1_1_credly_valid_domain(self):
        """TC-1.1: URL hợp lệ của Credly"""
        url = "https://www.credly.com/badges/abc-123-def/public_url"
        is_valid, issuer = is_whitelisted_domain(url)
        self.assertTrue(is_valid)
        self.assertEqual(issuer, 'credly')
        self.assertIn('Credly', get_issuer_display_name(issuer))

    def test_tc1_2_accredible_valid_domain(self):
        """TC-1.2: URL hợp lệ của Accredible / Credential.net"""
        url = "https://credential.net/99887766-test"
        is_valid, issuer = is_whitelisted_domain(url)
        self.assertTrue(is_valid)
        self.assertEqual(issuer, 'accredible')

        # Test subdomain
        url2 = "https://sub.accredible.com/verify/123"
        is_valid2, issuer2 = is_whitelisted_domain(url2)
        self.assertTrue(is_valid2)
        self.assertEqual(issuer2, 'accredible')

    def test_tc1_3_subdomain_spoofing_prevention(self):
        """TC-1.3: Chống giả mạo Subdomain (Subdomain Spoofing)"""
        # Kẻ gian đặt tên miền kẻ tấn công dạng credly.com.attacker.com
        url = "https://credly.com.attacker.com/badges/fake"
        is_valid, issuer = is_whitelisted_domain(url)
        self.assertFalse(is_valid)
        self.assertIsNone(issuer)

    def test_tc1_4_phishing_keyword_prevention(self):
        """TC-1.4: Chống tên miền nhái (Phishing Keyword)"""
        url = "https://fakecredly.com/badges/123"
        is_valid, issuer = is_whitelisted_domain(url)
        self.assertFalse(is_valid)
        self.assertIsNone(issuer)

        url2 = "https://mycoursera.org/view"
        is_valid2, issuer2 = is_whitelisted_domain(url2)
        self.assertFalse(is_valid2)
        self.assertIsNone(issuer2)

    def test_tc1_5_google_drive_rejection(self):
        """TC-1.5: Từ chối link Google Drive / Cloud storage cá nhân"""
        drive_url = "https://drive.google.com/file/d/1A2B3C4D5E/view?usp=sharing"
        is_valid, issuer = is_whitelisted_domain(drive_url)
        self.assertFalse(is_valid)
        self.assertIsNone(issuer)

        dropbox_url = "https://www.dropbox.com/s/xyz/cert.pdf"
        is_valid2, issuer2 = is_whitelisted_domain(dropbox_url)
        self.assertFalse(is_valid2)
        self.assertIsNone(issuer2)

    def test_tc1_6_malformed_and_script_injection(self):
        """TC-1.6: Xử lý an toàn với URL dị dạng hoặc inject script"""
        bad_inputs = [
            "",
            None,
            "javascript:alert(1)",
            "ftp://credly.com/file",
            "not-a-url",
            "   ",
            "http://",
            "https://   "
        ]
        for bad in bad_inputs:
            is_valid, issuer = is_whitelisted_domain(bad)
            self.assertFalse(is_valid, f"Failed on input: {bad}")
            self.assertIsNone(issuer)

    def test_tc1_7_model_persistence(self):
        """TC-1.7: Kiểm tra tính toàn vẹn của Model ORM và Schema DB"""
        user = User.query.filter_by(role='translator').first()
        if not user:
            user = User(name='Test Trans Cert', email='test_trans_cert@example.com', role='translator')
            db.session.add(user)
            db.session.commit()

        # Test TranslatorVerification new fields
        tv = TranslatorVerification(
            user_id=user.id,
            certificate_type='IELTS',
            certificate_name='IELTS Academic 8.0',
            certificate_id='TRF-2024-998811',
            verification_url='https://www.credly.com/badges/sample-badge',
            verification_source='credly',
            verification_metadata='{"score": 8.0, "status": "active"}',
            is_online_verified=True,
            online_verified_at=datetime.utcnow()
        )
        db.session.add(tv)
        db.session.commit()

        # Re-query
        saved_tv = TranslatorVerification.query.get(tv.id)
        self.assertEqual(saved_tv.certificate_id, 'TRF-2024-998811')
        self.assertEqual(saved_tv.verification_source, 'credly')
        self.assertTrue(saved_tv.is_online_verified)
        self.assertIn('8.0', saved_tv.verification_metadata)

        # Test TranslatorProfile new fields
        profile = TranslatorProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = TranslatorProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

        profile.has_digital_credential = True
        profile.credential_public_url = 'https://www.credly.com/badges/sample-badge'
        profile.credential_issuer = 'Credly'
        profile.credential_badge_name = 'IELTS Academic 8.0'
        db.session.commit()

        saved_profile = TranslatorProfile.query.filter_by(user_id=user.id).first()
        self.assertTrue(saved_profile.has_digital_credential)
        self.assertEqual(saved_profile.credential_issuer, 'Credly')

        # Dọn dẹp test record
        db.session.delete(saved_tv)
        db.session.commit()


if __name__ == '__main__':
    unittest.main()
