#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Acceptance test suite for 100 demo interpreter profiles on Viettranslate.
Tests:
1. Exact count of 100 demo users and 100 demo profiles without duplicates.
2. Verification distribution: ~75% Verified, ~15% Partially verified, ~10% Unverified.
3. Strict 10 languages representation: Anh, Hàn, Trung, Nhật, Pháp, Đức, Nga, Thái, Tây Ban Nha, Bồ Đào Nha.
4. Diversity in specializations (20 industries).
5. Diversity in Vietnamese locations (Hà Nội, TP.HCM, Đà Nẵng, Hải Phòng, Bắc Ninh, Quảng Ninh, Bình Dương, Đồng Nai, Vũng Tàu, Huế, Nha Trang).
6. Experience tiers (Junior, Mid-level, Senior, Expert) and rates.
7. Translators search API and filters.
8. Translator profile detail page rendering.
9. Translators directory page rendering.
10. Smart Matching recommendation engine verification.
"""

import unittest
from app import app, db
from models import User, TranslatorProfile, Job, TranslatorVerification, Service, InterpreterPreference, TranslatorPreference
from services.matching import get_recommended_translators_for_job

class TestDemoInterpretersAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def test_01_exact_count_and_uniqueness(self):
        with app.app_context():
            demo_users = User.query.filter_by(is_demo=True).all()
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            real_users = User.query.filter((User.is_demo == False) | (User.is_demo == None)).count()
            real_profiles = TranslatorProfile.query.filter(
                (TranslatorProfile.is_demo == False) | (TranslatorProfile.is_demo == None)
            ).count()

            print(f"\n[TEST 1] Demo Users: {len(demo_users)}, Demo Profiles: {len(demo_profiles)}, Real Profiles: {real_profiles}")
            self.assertEqual(len(demo_users), 100, "Phải có chính xác 100 demo users")
            self.assertEqual(len(demo_profiles), 100, "Phải có chính xác 100 demo profiles")
            self.assertGreater(real_users, 0, "Các tài khoản thật phải được bảo tồn nguyên vẹn")

            emails = [u.email for u in demo_users]
            self.assertEqual(len(set(emails)), 100, "Tất cả 100 email demo phải là duy nhất")

    def test_02_verification_distribution(self):
        with app.app_context():
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            verified = [p for p in demo_profiles if p.is_verified]
            unverified = [p for p in demo_profiles if not p.is_verified]

            print(f"[TEST 2] Verification: {len(verified)} Verified, {len(unverified)} Unverified")
            self.assertGreaterEqual(len(verified), 70, "Tỷ lệ Verified phải đạt 70-80%")
            self.assertLessEqual(len(verified), 80, "Tỷ lệ Verified không vượt quá 80%")
            self.assertGreaterEqual(len(unverified), 20, "Tỷ lệ Unverified/Partially verified phải từ 20-30%")

            for p in demo_profiles:
                self.assertTrue(p.is_demo, f"Hồ sơ {p.id} phải có is_demo=True")
                self.assertTrue(p.bio and len(p.bio) >= 50, f"Hồ sơ {p.id} phải có bio chuyên nghiệp đầy đủ")
                self.assertTrue(p.title and len(p.title) > 0, f"Hồ sơ {p.id} phải có tiêu đề")

    def test_03_language_diversity(self):
        with app.app_context():
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            all_langs = set()
            for p in demo_profiles:
                if p.languages:
                    langs = [l.strip() for l in p.languages.split(",") if l.strip()]
                    all_langs.update(langs)
                if p.source_language:
                    all_langs.add(p.source_language)
                if p.target_language:
                    all_langs.add(p.target_language)

            print(f"[TEST 3] Các ngôn ngữ đại diện: {all_langs}")
            expected_core = [
                "Tiếng Anh", "Tiếng Trung", "Tiếng Nhật", "Tiếng Hàn", "Tiếng Pháp",
                "Tiếng Đức", "Tiếng Nga", "Tiếng Thái", "Tiếng Tây Ban Nha", "Tiếng Bồ Đào Nha"
            ]
            for lang in expected_core:
                self.assertIn(lang, all_langs, f"Ngôn ngữ {lang} phải có mặt trong 10 ngôn ngữ demo")

    def test_04_industry_specializations_diversity(self):
        with app.app_context():
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            all_specs = set()
            for p in demo_profiles:
                if p.specializations:
                    specs = [s.strip() for s in p.specializations.split(",") if s.strip()]
                    all_specs.update(specs)

            print(f"[TEST 4] Số chuyên ngành đại diện: {len(all_specs)} ngành")
            self.assertGreaterEqual(len(all_specs), 20, "Phải đại diện ít nhất 20 chuyên ngành khác nhau")

    def test_05_location_diversity(self):
        with app.app_context():
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            locations = set(p.user.city for p in demo_profiles if p.user and p.user.city)

            print(f"[TEST 5] Số địa điểm tại Việt Nam: {len(locations)} thành phố/tỉnh -> {locations}")
            self.assertIn("Hà Nội", locations)
            self.assertIn("TP. Hồ Chí Minh", locations)
            self.assertIn("Đà Nẵng", locations)
            self.assertIn("Hải Phòng", locations)
            self.assertIn("Bắc Ninh", locations)
            self.assertIn("Quảng Ninh", locations)
            self.assertIn("Bình Dương", locations)
            self.assertIn("Đồng Nai", locations)
            self.assertIn("Vũng Tàu", locations)

    def test_06_experience_tiers_and_rates(self):
        with app.app_context():
            demo_profiles = TranslatorProfile.query.filter_by(is_demo=True).all()
            exp_years = [p.experience_years for p in demo_profiles]
            entry = [e for e in exp_years if e <= 2]
            intermediate = [e for e in exp_years if 3 <= e <= 5]
            experienced = [e for e in exp_years if 6 <= e <= 10]
            senior = [e for e in exp_years if e > 10]

            print(f"[TEST 6] Phân bổ kinh nghiệm: Junior (0-2y): {len(entry)}, Mid (3-5y): {len(intermediate)}, Senior (6-10y): {len(experienced)}, Expert (>10y): {len(senior)}")
            self.assertEqual(len(entry), 15)
            self.assertEqual(len(intermediate), 35)
            self.assertEqual(len(experienced), 35)
            self.assertEqual(len(senior), 15)

            for p in demo_profiles:
                self.assertIsNotNone(p.hourly_rate)
                self.assertIsNotNone(p.daily_rate)
                self.assertGreater(p.daily_rate, p.hourly_rate, f"Profile {p.id}: daily_rate > hourly_rate")

    def test_07_api_translators_endpoint(self):
        res = self.client.get("/api/translators")
        self.assertEqual(res.status_code, 200)
        items = res.get_json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 100)

        # Test demo filter: demo=demo
        res_demo = self.client.get("/api/translators?demo=demo")
        self.assertEqual(res_demo.status_code, 200)
        demo_items = res_demo.get_json()
        self.assertEqual(len(demo_items), 100, "Bộ lọc demo=demo phải trả về chính xác 100 hồ sơ demo")

        # Test demo filter: demo=hide
        res_hide = self.client.get("/api/translators?demo=hide")
        self.assertEqual(res_hide.status_code, 200)
        hide_items = res_hide.get_json()
        for item in hide_items:
            self.assertFalse(item.get("is_demo"), "Bộ lọc demo=hide không được chứa hồ sơ demo")

    def test_08_translator_profile_page(self):
        with app.app_context():
            demo_profile = TranslatorProfile.query.filter_by(is_demo=True).first()
            self.assertIsNotNone(demo_profile)
            profile_id = demo_profile.id

        res = self.client.get(f"/translator/{profile_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("HỒ SƠ MẪU MINH HỌA (DEMO PROFILE)", html)
        self.assertIn("Dữ liệu mẫu (Demo Profile)", html)

    def test_09_translator_directory_page(self):
        res = self.client.get("/translators")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Tìm Kiếm Phiên Dịch Viên Chuyên Nghiệp", html)
        self.assertIn("Hồ sơ demo", html)

    def test_10_smart_matching_recommendation(self):
        with app.app_context():
            test_hirer = User.query.filter_by(role='hirer').first() or User.query.first()
            job = Job(
                title='Đàm phán thương mại Việt - Hàn tại Hà Nội',
                description='Cần phiên dịch viên tiếng Hàn đàm phán hợp đồng kinh doanh thương mại với đối tác Seoul tại Hà Nội.',
                category='interpretation',
                category_group='interpretation',
                service_type='business',
                source_lang='Tiếng Việt',
                target_lang='Tiếng Hàn',
                specialty='Thương mại & Kinh doanh',
                event_location='Hà Nội',
                event_time_start='14:00',
                budget_min=1500000,
                budget_max=2500000,
                status='open',
                hirer_id=test_hirer.id,
            )
            db.session.add(job)
            db.session.flush()

            recommended = get_recommended_translators_for_job(job.id, limit=5, lang='vi')
            print(f"[TEST 10] Smart Matching trả về: {len(recommended)} ứng viên phù hợp")
            self.assertGreater(len(recommended), 0, "Smart Matching phải tìm thấy ứng viên phù hợp")
            top_match = recommended[0]
            self.assertGreaterEqual(top_match["match_score"], 80, "Ứng viên hàng đầu phải có điểm >= 80")
            self.assertTrue(top_match["is_verified"], "Ứng viên đề xuất phải có cờ is_verified=True")
            self.assertIn("Tiếng Hàn", top_match["languages"])

            db.session.rollback()

if __name__ == "__main__":
    unittest.main()
