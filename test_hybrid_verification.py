# -*- coding: utf-8 -*-
"""
Test Suite: Hybrid Auto-Verification System
Kiểm thử toàn diện 4 trụ cột nghiệp vụ:
1. Xác minh nguồn cấp và phòng thủ SSRF (Safe Destination Check).
2. Thuật toán so khớp họ tên 3 vùng tin cậy (3-zone Confidence Model).
3. Đánh giá điều kiện độc lập: Email, CCCD, CV, Chứng chỉ số.
4. Chế độ quét thử nghiệm (Dry-Run Batch Evaluation) và Phê duyệt an toàn.
"""

import unittest
from app import app, db
from models import User, TranslatorProfile, TranslatorVerification, AdminAuditLog
from services.cert_verifier import is_safe_destination, calculate_name_match, verify_certificate
from services.auto_verification_service import (
    evaluate_verification_submission,
    auto_approve_submission,
    batch_evaluate_pending_submissions,
    batch_auto_approve_eligible,
    get_auto_verification_settings,
    save_auto_verification_settings
)


class TestHybridVerificationSystem(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.rollback()
        self.ctx.pop()

    # -------------------------------------------------------------------------
    # 1. SSRF DEFENSE & SAFE DESTINATION TESTS
    # -------------------------------------------------------------------------
    def test_ssrf_prevention(self):
        """Kiểm tra cơ chế chặn các dải IP nội bộ, loopback và metadata cloud."""
        # Loopback
        ok, reason = is_safe_destination("http://127.0.0.1/admin")
        self.assertFalse(ok)
        
        ok, reason = is_safe_destination("http://localhost:5000")
        self.assertFalse(ok)
        
        # Cloud metadata service (AWS/GCP/Azure)
        ok, reason = is_safe_destination("http://169.254.169.254/latest/meta-data")
        self.assertFalse(ok)
        
        # Private LAN
        ok, reason = is_safe_destination("http://192.168.1.1/secret")
        self.assertFalse(ok)
        ok, reason = is_safe_destination("http://10.0.0.1/internal")
        self.assertFalse(ok)
        
        # Valid Public Domains
        ok, reason = is_safe_destination("https://www.credly.com/badges/sample-id")
        self.assertTrue(ok)
        ok, reason = is_safe_destination("https://www.coursera.org/verify/sample-code")
        self.assertTrue(ok)

    # -------------------------------------------------------------------------
    # 2. NAME MATCH SCORE & 3-ZONE CONFIDENCE MODEL
    # -------------------------------------------------------------------------
    def test_name_match_zones(self):
        """Kiểm tra mô hình phân vùng độ khớp họ tên (score, is_match, confidence)."""
        # Zone 1: Khớp cao (>= 0.85) - Hoán đổi họ tên tiếng Việt / Không dấu
        score1, is_m1, conf1 = calculate_name_match("Nguyễn Văn A", "Nguyen Van A")
        self.assertGreaterEqual(score1, 0.85)
        self.assertEqual(conf1, 'high')

        score2, is_m2, conf2 = calculate_name_match("Trần Thị Bích", "Bich Tran Thi")
        self.assertGreaterEqual(score2, 0.85)
        self.assertEqual(conf2, 'high')

        # Zone 3: Khác họ (nguy cơ mạo danh người khác) -> Không được xếp 'high'
        score3, is_m3, conf3 = calculate_name_match("Trần Văn A", "Nguyễn Văn A")
        self.assertLess(score3, 0.85)
        self.assertNotEqual(conf3, 'high')

        # Tên rỗng / không xác định
        score4, is_m4, conf4 = calculate_name_match("", "Test Name")
        self.assertEqual(score4, 0.0)
        self.assertEqual(conf4, 'low')

    # -------------------------------------------------------------------------
    # 3. INDEPENDENT CONDITIONS & AUTO-EVALUATION TESTS
    # -------------------------------------------------------------------------
    def test_unverified_email_blocks_auto_approval(self):
        """Tài khoản chưa xác thực email KHÔNG BAO GIỜ được tự động duyệt."""
        # Tạo user test chưa xác thực email
        user = User.query.filter_by(role='translator', email_verified=False).first()
        if not user:
            user = User(
                name="Test Email Guard",
                email="test_guard@viettranslate.local",
                password_hash="dummy_hash",
                role="translator",
                email_verified=False,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()

        # Tạo submission xác minh
        verif = TranslatorVerification.query.filter_by(user_id=user.id).first()
        if not verif:
            verif = TranslatorVerification(
                user_id=user.id,
                status='pending',
                full_name=user.name,
                source_language='Tiếng Anh',
                target_language='Tiếng Việt',
                verification_url='https://www.credly.com/badges/test-id',
                certificate_id='TEST-123'
            )
            db.session.add(verif)
            db.session.commit()

        eval_res = evaluate_verification_submission(verif.id)
        self.assertFalse(eval_res['checks']['email']['passed'])
        self.assertNotEqual(eval_res['auto_status'], 'auto_eligible')
        self.assertIn(eval_res['auto_status'], ['manual_review', 'not_eligible'])

    # -------------------------------------------------------------------------
    # 4. DRY RUN SCANNER & BATCH CONTROLS
    # -------------------------------------------------------------------------
    def test_dry_run_batch_evaluation(self):
        """Kiểm tra batch scan: chỉ tính toán auto_status mà KHÔNG tự ý đổi trạng thái duyệt thật."""
        # Lưu số lượng pending ban đầu
        pending_count_before = TranslatorVerification.query.filter_by(status='pending').count()

        # Chạy batch scan giới hạn 5 bản ghi
        res = batch_evaluate_pending_submissions(limit=5)
        self.assertTrue(res['success'])
        self.assertIn('total_scanned', res)
        self.assertIn('auto_eligible_count', res)

        # Trạng thái status của hồ sơ trong DB vẫn phải là pending (không bị tự động approve ngầm)
        pending_count_after = TranslatorVerification.query.filter_by(status='pending').count()
        self.assertEqual(pending_count_before, pending_count_after)

    # -------------------------------------------------------------------------
    # 5. CONFIGURATION & AUDIT LOG CONTROLS
    # -------------------------------------------------------------------------
    def test_auto_verification_settings(self):
        """Kiểm tra cơ chế lưu và đọc cấu hình bộ máy duyệt tự động."""
        settings = get_auto_verification_settings()
        self.assertIn('auto_approve_enabled', settings)
        self.assertIn('dry_run_mode', settings)
        self.assertIn('min_name_match_score', settings)
        self.assertIn('batch_size', settings)

        # Lưu thay đổi an toàn
        ok, msg = save_auto_verification_settings({
            'min_name_match_score': 0.88,
            'batch_size': 12
        })
        self.assertTrue(ok)

        updated = get_auto_verification_settings()
        self.assertEqual(updated['min_name_match_score'], 0.88)
        self.assertEqual(updated['batch_size'], 12)


if __name__ == '__main__':
    unittest.main()
