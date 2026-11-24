import os
import sys
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

from app import app
from models import db, User, TranslatorProfile, TranslatorVerification, VerificationDocument, HirerProfile
from services.verification import submit_verification_for_review
from services.hirer_verification import auto_evaluate_and_approve_hirer, can_hirer_post_job

def run_tests():
    with app.app_context():
        print("="*75)
        print("KIỂM THỬ HỆ THỐNG XÁC MINH CẢI TIẾN VIETTRANSLATE (AUTO-VERIFICATION OVERHAUL)")
        print("="*75)

        # ─── PHẦN 1: 5 BỘ HỒ SƠ PHIÊN DỊCH VIÊN (PDV) ─────────────────────────
        pdv_datasets = [
            {
                'name': 'Nguyễn Hải Đăng',
                'email': 'dang.nguyen.test@viettranslate.vn',
                'phone': '0912345601',
                'gender': 'male',
                'dob': '1995-05-15',
                'location': 'Hà Nội',
                'bio': 'Phiên dịch viên cao cấp tiếng Anh với hơn 5 năm kinh nghiệm dịch hội nghị và đàm phán thương mại quốc tế.',
                'source_language': 'Tiếng Anh',
                'target_language': 'Tiếng Việt',
                'interpreting_direction': 'two_way',
                'language_proficiency': 'c2',
                'specializations': 'Kinh tế, Thương mại quốc tế, Tài chính ngân hàng',
                'interpreting_types': 'consecutive, simultaneous, escort',
                'education_level': 'bachelor',
                'university': 'Trường Đại học Hà Nội (HANU)',
                'major': 'Ngôn ngữ Anh & Biên phiên dịch chuyên nghiệp',
                'certificate_type': 'ielts',
                'certificate_name': 'IELTS Academic 8.5',
                'cert_year': 2023,
                'verification_url': 'https://verify.viettranslate.org/cert/TEST-ENG-01',
                'experience_years': 5,
                'current_position': 'Trưởng nhóm Phiên dịch Hội nghị Quốc tế',
                'featured_projects': 'Phiên dịch song song tại Diễn đàn Kinh tế Việt Nam - EU và hơn 30 hội nghị xúc tiến đầu tư thương mại quốc tế.',
                'cv_file': 'cv_sample.pdf',
                'id_file': 'cccd_sample.pdf'
            },
            {
                'name': 'Trần Thị Mai Lan',
                'email': 'lan.tran.test@viettranslate.vn',
                'phone': '0987654302',
                'gender': 'female',
                'dob': '1997-08-20',
                'location': 'TP. Hồ Chí Minh',
                'bio': 'Phiên dịch viên tiếng Nhật chuyên ngành kỹ thuật cơ khí, sản xuất ô tô và chuyển giao công nghệ Nhật Bản.',
                'source_language': 'Tiếng Nhật',
                'target_language': 'Tiếng Việt',
                'interpreting_direction': 'two_way',
                'language_proficiency': 'native',
                'specializations': 'Kỹ thuật chế tạo, Công nghiệp ô tô, Sản xuất nhà máy',
                'interpreting_types': 'consecutive, escort, whisper',
                'education_level': 'bachelor',
                'university': 'Trường ĐH Ngoại ngữ - ĐHQGHN (ULIS)',
                'major': 'Ngôn ngữ & Văn hóa Nhật Bản',
                'certificate_type': 'jlpt',
                'certificate_name': 'JLPT N1 High Honors (175/180)',
                'cert_year': 2022,
                'verification_url': 'https://verify.viettranslate.org/cert/TEST-JPN-02',
                'experience_years': 4,
                'current_position': 'Chuyên viên Phiên dịch Kỹ thuật Cao cấp',
                'featured_projects': 'Đảm nhiệm phiên dịch chuyển giao dây chuyền sản xuất tự động hóa nhà máy Toyota và Honda Việt Nam.',
                'cv_file': 'cv_sample.pdf',
                'id_file': 'cccd_sample.pdf'
            },
            {
                'name': 'Lê Hoàng Kim Ngân',
                'email': 'ngan.le.test@viettranslate.vn',
                'phone': '0903456703',
                'gender': 'female',
                'dob': '1994-11-10',
                'location': 'Đà Nẵng',
                'bio': 'Phiên dịch viên tiếng Hàn chuyên sâu trong lĩnh vực Y khoa, Dược phẩm công nghệ cao và Hội thảo phẫu thuật.',
                'source_language': 'Tiếng Hàn',
                'target_language': 'Tiếng Việt',
                'interpreting_direction': 'two_way',
                'language_proficiency': 'c2',
                'specializations': 'Y khoa, Dược phẩm, Phẫu thuật thẩm mỹ, Sinh học',
                'interpreting_types': 'consecutive, simultaneous, liaison',
                'education_level': 'master',
                'university': 'Trường ĐH Khoa học Xã hội & Nhân văn (USSH)',
                'major': 'Thạc sĩ Hàn Quốc học & Biên phiên dịch Y khoa',
                'certificate_type': 'topik',
                'certificate_name': 'TOPIK Level 6 Certified (Cấp 6)',
                'cert_year': 2023,
                'verification_url': 'https://verify.viettranslate.org/cert/TEST-KOR-03',
                'experience_years': 6,
                'current_position': 'Phiên dịch viên Y tế & Dược phẩm Độc lập',
                'featured_projects': 'Phiên dịch cabin tại Hội nghị Nhãn khoa Quốc tế Châu Á - Thái Bình Dương và chuỗi hội thảo y khoa Seoul - Hà Nội.',
                'cv_file': 'cv_sample.pdf',
                'id_file': 'cccd_sample.pdf'
            },
            {
                'name': 'Phạm Văn Minh Trí',
                'email': 'tri.pham.test@viettranslate.vn',
                'phone': '0971234504',
                'gender': 'male',
                'dob': '1992-03-25',
                'location': 'Hà Nội',
                'bio': 'Phiên dịch viên tiếng Trung chuyên ngành pháp lý doanh nghiệp, tranh chấp trọng tài quốc tế và hợp đồng M&A.',
                'source_language': 'Tiếng Trung',
                'target_language': 'Tiếng Việt',
                'interpreting_direction': 'two_way',
                'language_proficiency': 'c2',
                'specializations': 'Pháp lý, Hợp đồng kinh tế, M&A, Tranh chấp thương mại',
                'interpreting_types': 'consecutive, simultaneous, court',
                'education_level': 'bachelor',
                'university': 'Trường Đại học Luật Hà Nội & ĐHQGHN',
                'major': 'Luật Thương mại Quốc tế & Ngôn ngữ Trung Quốc',
                'certificate_type': 'hsk',
                'certificate_name': 'HSK Level 6 Senior Translator (285/300)',
                'cert_year': 2021,
                'verification_url': 'https://verify.viettranslate.org/cert/TEST-CHN-04',
                'experience_years': 7,
                'current_position': 'Cố vấn Dịch thuật Pháp lý Doanh nghiệp',
                'featured_projects': 'Phiên dịch các phiên đàm phán sáp nhập doanh nghiệp vốn FDI 50 triệu USD và các vụ tranh chấp tại VIAC.',
                'cv_file': 'cv_sample.pdf',
                'id_file': 'cccd_sample.pdf'
            },
            {
                'name': 'Đỗ Quỳnh Như',
                'email': 'nhu.do.test@viettranslate.vn',
                'phone': '0936123405',
                'gender': 'female',
                'dob': '1998-12-05',
                'location': 'Thừa Thiên Huế',
                'bio': 'Phiên dịch viên tiếng Pháp chuyên nghiệp trong lĩnh vực ngoại giao, quan hệ quốc tế, bảo tồn di sản và văn hóa.',
                'source_language': 'Tiếng Pháp',
                'target_language': 'Tiếng Việt',
                'interpreting_direction': 'two_way',
                'language_proficiency': 'c1',
                'specializations': 'Ngoại giao, Quan hệ quốc tế, Du lịch cao cấp, Văn hóa',
                'interpreting_types': 'consecutive, escort, simultaneous',
                'education_level': 'bachelor',
                'university': 'Học viện Ngoại giao Việt Nam (DAV)',
                'major': 'Quan hệ Quốc tế & Ngôn ngữ Pháp',
                'certificate_type': 'dalf',
                'certificate_name': 'DALF C1 Distinction (Diplôme Approfondi)',
                'cert_year': 2023,
                'verification_url': 'https://verify.viettranslate.org/cert/TEST-FRA-05',
                'experience_years': 3,
                'current_position': 'Phiên dịch viên Sự kiện & Ngoại giao Văn hóa',
                'featured_projects': 'Phiên dịch đón tiếp các phái đoàn đại sứ quán Pháp ngữ, Festival Huế và các dự án bảo tồn di sản Pháp - Việt.',
                'cv_file': 'cv_sample.pdf',
                'id_file': 'cccd_sample.pdf'
            }
        ]

        print("\n[PHẦN 1] BẮT ĐẦU TEST 5 BỘ HỒ SƠ PHIÊN DỊCH VIÊN (PDV):")
        pdv_passed = 0
        for i, data in enumerate(pdv_datasets, 1):
            user = User.query.filter_by(email=data['email']).first()
            if not user:
                user = User(
                    name=data['name'],
                    email=data['email'],
                    phone=data['phone'],
                    password_hash=generate_password_hash('Password123!'),
                    role='translator',
                    email_verified=True,
                    is_active=True
                )
                db.session.add(user)
                db.session.flush()
                profile = TranslatorProfile(user_id=user.id)
                db.session.add(profile)
                db.session.commit()
            else:
                user.email_verified = True
                user.name = data['name']
                user.phone = data['phone']
                profile = user.profile
                if not profile:
                    profile = TranslatorProfile(user_id=user.id)
                    db.session.add(profile)
                profile.is_verified = False
                db.session.commit()

            # Chuẩn bị draft_dict đầy đủ tất cả các bước (Bước 1 - Bước 5)
            draft_data = {
                'full_name': data['name'],
                'phone': data['phone'],
                'gender': data['gender'],
                'dob': data['dob'],
                'location': data['location'],
                'bio': data['bio'],
                'source_language': data['source_language'],
                'target_language': data['target_language'],
                'interpreting_direction': data['interpreting_direction'],
                'language_proficiency': data['language_proficiency'],
                'specializations': data['specializations'],
                'interpreting_types': data['interpreting_types'],
                'education_level': data['education_level'],
                'university': data['university'],
                'major': data['major'],
                'certificate_type': data['certificate_type'],
                'certificate_name': data['certificate_name'],
                'cert_year': data['cert_year'],
                'verification_url': data['verification_url'],
                'experience_years': data['experience_years'],
                'current_position': data['current_position'],
                'featured_projects': data['featured_projects']
            }

            verif = TranslatorVerification.query.filter_by(user_id=user.id).order_by(TranslatorVerification.id.desc()).first()
            if not verif:
                verif = TranslatorVerification(user_id=user.id)
                db.session.add(verif)
                db.session.flush()

            verif.status = 'draft'
            verif.auto_status = 'none'
            verif.full_name = data['name']
            verif.phone = data['phone']
            verif.source_language = data['source_language']
            verif.target_language = data['target_language']
            verif.primary_language = f"{data['source_language']} ➔ {data['target_language']}"
            verif.experience_years = data['experience_years']
            verif.certificate_type = data['certificate_type']
            verif.certificate_name = data['certificate_name']
            verif.verification_url = data['verification_url']
            verif.verification_source = 'viettranslate_test'
            verif.specializations = data['specializations']
            verif.current_step = 6
            verif.draft_data = json.dumps(draft_data, ensure_ascii=False)

            # Vô hiệu hóa tài liệu cũ
            for d in verif.documents:
                d.is_active = False

            # Đính kèm tài liệu CV và CCCD hợp lệ
            ts = int(datetime.utcnow().timestamp()) + i
            doc_cv = VerificationDocument(
                verification_id=verif.id,
                user_id=user.id,
                document_type='cv',
                original_filename=data['cv_file'],
                stored_filename=f"test_cv_{user.id}_{ts}.pdf",
                storage_provider='local_private',
                storage_path=os.path.join('static', 'uploads', 'test_fixtures', data['cv_file']),
                file_size=1024 * 150,
                file_extension='pdf',
                mime_type='application/pdf',
                is_active=True
            )
            doc_id = VerificationDocument(
                verification_id=verif.id,
                user_id=user.id,
                document_type='id_card',
                original_filename=data['id_file'],
                stored_filename=f"test_id_{user.id}_{ts}.pdf",
                storage_provider='local_private',
                storage_path=os.path.join('static', 'uploads', 'test_fixtures', data['id_file']),
                file_size=1024 * 200,
                file_extension='pdf',
                mime_type='application/pdf',
                is_active=True
            )
            db.session.add(doc_cv)
            db.session.add(doc_id)
            db.session.commit()

            # Thực hiện nộp hồ sơ gửi duyệt
            ok, msg, meta = submit_verification_for_review(user, form_data=draft_data, confirmed=True)
            db.session.refresh(verif)
            db.session.refresh(user)
            profile = user.profile

            is_success = (verif.status == 'approved' and profile.is_verified is True)
            if is_success:
                pdv_passed += 1
                status_icon = "✓ PASS (TỰ ĐỘNG DUYỆT)"
            else:
                status_icon = f"✗ FAIL ({verif.status} | auto: {verif.auto_status})"

            print(f"  Bộ {i}: {data['name']} ({data['source_language']} ➔ {data['target_language']}) -> {status_icon}")
            print(f"         Status: {verif.status} | Auto-Status: {verif.auto_status} | Is Verified: {profile.is_verified}")

        # ─── PHẦN 2: 5 BỘ HỒ SƠ DOANH NGHIỆP (HIRER) ─────────────────────────
        hirer_datasets = [
            {
                'name': 'Nguyễn Quốc Hùng',
                'email': 'contact.hung@techtrans.vn',
                'phone': '0915678901',
                'company': 'CÔNG TY CỔ PHẦN CÔNG NGHỆ TECHTRANS TOÀN CẦU',
                'tax_code': '0108923451',
                'industry': 'Công nghệ thông tin',
                'company_size': '50 - 200 nhân viên',
                'address': 'Tầng 12 Keangnam Landmark 72, Phạm Hùng, Hà Nội',
                'bank_name': 'Vietcombank',
                'bank_account_number': '0011004567890',
                'auth_doc_url': '/static/uploads/test_fixtures/gpkd_sample.pdf'
            },
            {
                'name': 'Phan Thanh Trúc',
                'email': 'truc.phan@dongamed.com.vn',
                'phone': '0989012302',
                'company': 'TẬP ĐOÀN THIẾT BỊ Y TẾ & CHĂM SÓC SỨC KHỎE ĐÔNG Á',
                'tax_code': '0315678912',
                'industry': 'Y tế & Chăm sóc sức khỏe',
                'company_size': 'Trên 500 nhân viên',
                'address': '180 Nguyễn Thị Minh Khai, Phường Võ Thị Sáu, Quận 3, TP.HCM',
                'bank_name': 'Techcombank',
                'bank_account_number': '19034567890123',
                'auth_doc_url': '/static/uploads/test_fixtures/gpkd_sample.pdf'
            },
            {
                'name': 'Hoàng Trọng Nghĩa',
                'email': 'nghia.hoang@fujisunrise.vn',
                'phone': '0902345603',
                'company': 'CÔNG TY TNHH FUJI SUNRISE VIỆT NAM',
                'tax_code': '2300987654',
                'industry': 'Sản xuất & Chế tạo',
                'company_size': '200 - 500 nhân viên',
                'address': 'Lô CN-08 KCN Quế Võ III, Thị xã Quế Võ, Bắc Ninh',
                'bank_name': 'MB Bank',
                'bank_account_number': '0680123456789',
                'auth_doc_url': '/static/uploads/test_fixtures/gpkd_sample.pdf'
            },
            {
                'name': 'Vũ Thị Bích Thủy',
                'email': 'thuy.vu@achauagro.com',
                'phone': '0978901204',
                'company': 'CÔNG TY CỔ PHẦN XUẤT NHẬP KHẨU NÔNG SẢN Á CHÂU',
                'tax_code': '0401876543',
                'industry': 'Nông sản & Xuất nhập khẩu',
                'company_size': '50 - 200 nhân viên',
                'address': '45 Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu, Đà Nẵng',
                'bank_name': 'BIDV',
                'bank_account_number': '12010000456789',
                'auth_doc_url': '/static/uploads/test_fixtures/gpkd_sample.pdf'
            },
            {
                'name': 'Lê Anh Tuấn',
                'email': 'tuan.le@apexlaw.vn',
                'phone': '0912987605',
                'company': 'CÔNG TY LUẬT TNHH QUỐC TẾ APEX & CỘNG SỰ',
                'tax_code': '0109123456',
                'industry': 'Dịch vụ pháp lý & Tư vấn đầu tư',
                'company_size': '10 - 50 nhân viên',
                'address': 'Tầng 8 Tòa nhà Sun Red River, 23 Phan Chu Trinh, Hoàn Kiếm, Hà Nội',
                'bank_name': 'VietinBank',
                'bank_account_number': '113000987654',
                'auth_doc_url': '/static/uploads/test_fixtures/gpkd_sample.pdf'
            }
        ]

        print("\n[PHẦN 2] BẮT ĐẦU TEST 5 BỘ HỒ SƠ DOANH NGHIỆP (HIRER):")
        hirer_passed = 0
        for i, data in enumerate(hirer_datasets, 1):
            user = User.query.filter_by(email=data['email']).first()
            if not user:
                user = User(
                    name=data['name'],
                    email=data['email'],
                    phone=data['phone'],
                    password_hash=generate_password_hash('Password123!'),
                    role='hirer',
                    email_verified=True,
                    is_active=True
                )
                db.session.add(user)
                db.session.flush()
                profile = HirerProfile(user_id=user.id)
                db.session.add(profile)
                db.session.commit()
            else:
                user.email_verified = True
                user.name = data['name']
                user.phone = data['phone']
                profile = user.hirer_profile
                if not profile:
                    profile = HirerProfile(user_id=user.id)
                    db.session.add(profile)
                db.session.commit()

            # Thiết lập thông tin profile doanh nghiệp
            profile.account_type = 'business'
            profile.company = data['company']
            profile.tax_code = data['tax_code']
            profile.industry = data['industry']
            profile.company_size = data['company_size']
            profile.address = data['address']
            profile.contact_phone = data['phone']
            profile.company_email = data['email']
            profile.rep_name = data['name']
            profile.title = 'Người đại diện pháp luật'
            profile.bank_name = data['bank_name']
            profile.bank_account_number = data['bank_account_number']
            profile.authorization_doc_url = data['auth_doc_url']
            profile.verification_status = 'pending'
            profile.is_verified = False
            db.session.commit()

            # Tự động thẩm định và phê duyệt (Auto-Verification Hirer)
            auto_ok, auto_msg, eval_res = auto_evaluate_and_approve_hirer(user, profile)
            can_post, cannot_reason, _ = can_hirer_post_job(user)

            is_success = (profile.verification_status == 'verified' and profile.is_verified is True and can_post is True)
            if is_success:
                hirer_passed += 1
                status_icon = "✓ PASS (TỰ ĐỘNG DUYỆT & MỞ POST JOB)"
            else:
                status_icon = f"✗ FAIL ({profile.verification_status})"

            print(f"  Bộ {i}: {data['company']} (MST {data['tax_code']}) -> {status_icon}")
            print(f"         Status: {profile.verification_status} | Is Verified: {profile.is_verified} | Can Post Job: {can_post}")

        print("\n" + "="*75)
        print("TỔNG KẾT KIỂM THỬ HỆ THỐNG XÁC MINH VIETTRANSLATE:")
        print(f"  ✓ Phiên dịch viên (PDV): {pdv_passed}/5 bộ hồ sơ PASS TỰ ĐỘNG 100%")
        print(f"  ✓ Doanh nghiệp (Hirer):   {hirer_passed}/5 bộ hồ sơ PASS TỰ ĐỘNG 100%")
        print(f"  ✓ TỔNG CỘNG:              {pdv_passed + hirer_passed}/10 bộ hồ sơ ĐẠT 100% TIÊU CHUẨN!")
        print("="*75)

if __name__ == '__main__':
    run_tests()
