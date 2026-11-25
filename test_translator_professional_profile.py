import unittest
import io
import json
import os
from datetime import datetime

from app import app
from models import (
    db,
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument
)


class TranslatorProfessionalProfileTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo hoặc lấy tài khoản Translator 1 (Đã xác minh, công khai)
        self.trans_verified = User.query.filter_by(email='trans_verified_test@example.com').first()
        if not self.trans_verified:
            self.trans_verified = User(
                name='Nguyễn Văn Minh (Xác minh)',
                email='trans_verified_test@example.com',
                password_hash='dummyhash',
                role='translator',
                is_active=True
            )
            db.session.add(self.trans_verified)
            db.session.commit()

        if not self.trans_verified.profile:
            self.profile_verified = TranslatorProfile(
                user_id=self.trans_verified.id,
                title='Phiên dịch viên Tiếng Anh Cao Cấp',
                bio='Hơn 8 năm kinh nghiệm phiên dịch hội nghị, pháp lý và thương mại quốc tế.',
                languages='Tiếng Anh, Tiếng Việt',
                badges='Hội nghị, Pháp lý',
                rating=4.9,
                total_reviews=28,
                total_jobs=45,
                response_time='1 giờ',
                is_verified=True,
                is_public=True,
                is_cv_public=True,
                source_language='Tiếng Việt',
                target_language='Tiếng Anh',
                interpreting_direction='Hai chiều (Song phương)',
                language_proficiency='Bản ngữ / C2',
                specializations='Pháp lý & Hợp đồng, Hội nghị quốc tế, Kinh tế FDI',
                interpreting_types='Dịch song song (Cabin), Dịch nối tiếp (Consecutive)',
                work_modes='Trực tiếp tại địa điểm (On-site), Trực tuyến / Từ xa (Online)',
                education_level='Thạc sĩ',
                university='Đại học Ngoại ngữ - ĐHQGHN',
                major='Ngôn ngữ Anh & Phiên dịch hội nghị',
                cert_name='IELTS 8.5',
                cert_year=2023,
                experience_years=8,
                current_position='Phiên dịch viên Cabin Trưởng',
                notable_clients='Bộ Ngoại giao, Samsung Vietnam, Phái đoàn EU',
                featured_projects='Hội nghị Bộ trưởng Kinh tế ASEAN 2023'
            )
            db.session.add(self.profile_verified)
            db.session.commit()
        else:
            self.profile_verified = self.trans_verified.profile
            self.profile_verified.is_verified = True
            self.profile_verified.is_public = True
            self.profile_verified.is_cv_public = True
            self.profile_verified.cert_name = 'IELTS 8.5'
            self.profile_verified.experience_years = 8
            db.session.commit()

        # Tạo hồ sơ xác minh liên kết có tài liệu CV và CCCD (để kiểm tra bảo mật không lộ CCCD)
        verif_doc = TranslatorVerification.query.filter_by(user_id=self.trans_verified.id).first()
        if not verif_doc:
            verif_doc = TranslatorVerification(
                user_id=self.trans_verified.id,
                status='approved',
                certificate_type='IELTS',
                certificate_name='IELTS 8.5',
                full_name='Nguyễn Văn Minh',
                phone='0987654321',
                source_language='Tiếng Việt',
                target_language='Tiếng Anh',
                interpreting_direction='Hai chiều (Song phương)',
                specializations='Pháp lý, Hội nghị'
            )
            db.session.add(verif_doc)
            db.session.commit()

        # Thêm file CV minh chứng vào storage
        from services.verification import get_private_verification_folder
        folder = get_private_verification_folder()
        os.makedirs(folder, exist_ok=True)
        cv_storage_path = os.path.join(folder, 'pdoc_cv_test_minh.pdf')
        with open(cv_storage_path, 'wb') as f:
            f.write(b'%PDF-1.4 test cv document content for public viewing')

        doc_cv = VerificationDocument.query.filter_by(user_id=self.trans_verified.id, document_type='cv').first()
        if not doc_cv:
            doc_cv = VerificationDocument(
                verification_id=verif_doc.id,
                user_id=self.trans_verified.id,
                document_type='cv',
                original_filename='CV_Nguyen_Van_Minh.pdf',
                stored_filename='pdoc_cv_test_minh.pdf',
                storage_path=cv_storage_path,
                mime_type='application/pdf',
                file_extension='pdf',
                file_size=1024,
                status='approved',
                is_active=True
            )
            db.session.add(doc_cv)
            db.session.commit()

        # Thêm file CCCD minh chứng bí mật (ID Card)
        id_storage_path = os.path.join(folder, 'pdoc_id_card_test_minh.png')
        with open(id_storage_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\nsecret id card cccd')

        doc_id = VerificationDocument.query.filter_by(user_id=self.trans_verified.id, document_type='id_card').first()
        if not doc_id:
            doc_id = VerificationDocument(
                verification_id=verif_doc.id,
                user_id=self.trans_verified.id,
                document_type='id_card',
                original_filename='CCCD_Nguyen_Van_Minh_Private.png',
                stored_filename='pdoc_id_card_test_minh.png',
                storage_path=id_storage_path,
                mime_type='image/png',
                file_extension='png',
                file_size=2048,
                status='approved',
                is_active=True
            )
            db.session.add(doc_id)
            db.session.commit()

        # Tạo Translator 2 (Chưa xác minh, CV tắt công khai)
        self.trans_unverified = User.query.filter_by(email='trans_unverified_test@example.com').first()
        if not self.trans_unverified:
            self.trans_unverified = User(
                name='Trần Thu Hà (Chưa xác minh)',
                email='trans_unverified_test@example.com',
                password_hash='dummyhash',
                role='translator',
                is_active=True
            )
            db.session.add(self.trans_unverified)
            db.session.commit()

        if not self.trans_unverified.profile:
            self.profile_unverified = TranslatorProfile(
                user_id=self.trans_unverified.id,
                title='Phiên dịch viên Tiếng Hàn Thương Mại',
                bio='Phiên dịch tiếng Hàn đàm phán thương mại và du lịch.',
                languages='Tiếng Hàn, Tiếng Việt',
                is_verified=False,
                is_public=True,
                is_cv_public=False,
                source_language='Tiếng Hàn',
                target_language='Tiếng Việt',
                experience_years=2
            )
            db.session.add(self.profile_unverified)
            db.session.commit()
        else:
            self.profile_unverified = self.trans_unverified.profile
            self.profile_unverified.is_verified = False
            self.profile_unverified.is_public = True
            self.profile_unverified.is_cv_public = False
            db.session.commit()

        # Tạo Translator 3 (Hồ sơ Riêng tư / Không công khai)
        self.trans_private = User.query.filter_by(email='trans_private_test@example.com').first()
        if not self.trans_private:
            self.trans_private = User(
                name='Lê Hoàng Long (Riêng tư)',
                email='trans_private_test@example.com',
                password_hash='dummyhash',
                role='translator',
                is_active=True
            )
            db.session.add(self.trans_private)
            db.session.commit()

        if not self.trans_private.profile:
            self.profile_private = TranslatorProfile(
                user_id=self.trans_private.id,
                title='Biên phiên dịch Tiếng Nhật',
                bio='Chuyên dịch hồ sơ kỹ thuật và cơ khí chế tạo.',
                languages='Tiếng Nhật, Tiếng Việt',
                is_verified=False,
                is_public=False, # Không công khai
                is_cv_public=False
            )
            db.session.add(self.profile_private)
            db.session.commit()
        else:
            self.profile_private = self.trans_private.profile
            self.profile_private.title = 'Biên phiên dịch Tiếng Nhật'
            self.profile_private.bio = 'Chuyên dịch hồ sơ kỹ thuật và cơ khí chế tạo.'
            self.profile_private.languages = 'Tiếng Nhật, Tiếng Việt'
            self.profile_private.current_position = None
            self.profile_private.is_public = False
            self.profile_private.is_cv_public = False
            db.session.commit()

        # Tạo Translator 4 (Tài khoản bị giới hạn / khóa is_active = False)
        self.trans_banned = User.query.filter_by(email='trans_banned_test@example.com').first()
        if not self.trans_banned:
            self.trans_banned = User(
                name='Phạm Quốc Bị Khóa',
                email='trans_banned_test@example.com',
                password_hash='dummyhash',
                role='translator',
                is_active=False # Bị khóa
            )
            db.session.add(self.trans_banned)
            db.session.commit()

        if not self.trans_banned.profile:
            self.profile_banned = TranslatorProfile(
                user_id=self.trans_banned.id,
                title='Phiên dịch viên tiếng Trung',
                bio='Hồ sơ đã bị tạm khóa do vi phạm chính sách.',
                languages='Tiếng Trung',
                is_verified=True,
                is_public=True
            )
            db.session.add(self.profile_banned)
            db.session.commit()
        else:
            self.profile_banned = self.trans_banned.profile
            self.trans_banned.is_active = False
            db.session.commit()

        # Tạo Client User (Người xem vãng lai / Khách hàng)
        self.hirer_user = User.query.filter_by(email='hirer_viewer_test@example.com').first()
        if not self.hirer_user:
            self.hirer_user = User(
                name='Khách Thuê Dịch Vụ',
                email='hirer_viewer_test@example.com',
                password_hash='dummyhash',
                role='hirer',
                is_active=True
            )
            db.session.add(self.hirer_user)
            db.session.commit()

    def tearDown(self):
        self.ctx.pop()

    # =========================================================================
    # KỊCH BẢN 1: HỒ SƠ ĐÃ XÁC MINH (VERIFIED PROFILE)
    # =========================================================================
    def test_01_verified_profile_displays_badge_and_transparency_box(self):
        """Hồ sơ đã xác minh phải hiển thị huy hiệu, phạm vi thẩm định và tuyên bố minh bạch; không lộ CCCD."""
        res = self.client.get(f'/translator/{self.profile_verified.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Có tên và huy hiệu đã xác minh
        self.assertIn('Nguyễn Văn Minh', html)
        self.assertIn('Đã xác minh', html)

        # 2. Khối minh bạch xác minh từ VietTranslate
        self.assertIn('Thông tin xác minh chính thức từ VietTranslate', html)
        self.assertIn('Phạm vi thông tin đã được đối soát:', html)
        self.assertIn('bằng tốt nghiệp', html.lower())
        self.assertIn('chứng chỉ ngoại ngữ', html.lower())

        # 3. Tuyên bố minh bạch: không khẳng định chứng nhận năng lực toàn diện
        self.assertIn('Lưu ý minh bạch', html)
        self.assertIn('không mang ý nghĩa chứng nhận năng lực', html)

        # 4. Hiển thị thông tin cặp ngôn ngữ và chuyên môn
        self.assertIn('Tiếng Việt', html)
        self.assertIn('Tiếng Anh', html)
        self.assertIn('Hai chiều (Song phương)', html)
        self.assertTrue('Pháp lý & Hợp đồng' in html or 'Pháp lý &amp; Hợp đồng' in html)
        self.assertIn('IELTS 8.5', html)

        # 5. BẢO MẬT: Tuyệt đối không để lộ CCCD, hộ chiếu hoặc tài liệu định danh nhạy cảm
        self.assertNotIn('CCCD_Nguyen_Van_Minh_Private.png', html)
        self.assertNotIn('secret id card', html)
        self.assertNotIn('pdoc_id_card', html)

    # =========================================================================
    # KỊCH BẢN 2: HỒ SƠ CHƯA XÁC MINH (UNVERIFIED PROFILE)
    # =========================================================================
    def test_02_unverified_profile_does_not_display_verified_badge(self):
        """Hồ sơ chưa xác minh không được hiển thị huy hiệu xác minh hay khối thẩm định tích xanh."""
        res = self.client.get(f'/translator/{self.profile_unverified.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Tên hiển thị bình thường
        self.assertIn('Trần Thu Hà', html)

        # 2. Không hiển thị khối xác minh chính thức tích xanh
        self.assertNotIn('Thông tin xác minh chính thức từ VietTranslate', html)
        self.assertNotIn('Đã xác minh (Tích xanh)', html)
        self.assertIn('Chưa thẩm định giấy tờ', html)

        # 3. Hiển thị ngôn ngữ tự công bố
        self.assertIn('Tiếng Hàn', html)

    # =========================================================================
    # KỊCH BẢN 3: HỒ SƠ KHÔNG CÔNG KHAI / RIÊNG TƯ (PRIVATE PROFILE)
    # =========================================================================
    def test_03_private_profile_blocks_visitors(self):
        """Khách ngoài truy cập hồ sơ riêng tư (is_public=False) bị chặn, hiển thị trang thông báo riêng tư."""
        # Khách vãng lai chưa đăng nhập
        res = self.client.get(f'/translator/{self.profile_private.id}')
        self.assertEqual(res.status_code, 200) # Trả về trang thông báo thân thiện
        html = res.get_data(as_text=True)

        self.assertIn('Hồ sơ ở chế độ riêng tư', html)
        self.assertIn('chưa công khai', html.lower())
        # Không lộ bio hoặc dữ liệu nhạy cảm
        self.assertNotIn('Lê Hoàng Long (Riêng tư)', html)
        self.assertNotIn('cơ khí chế tạo', html)

    def test_04_private_profile_accessible_by_owner_in_preview_mode(self):
        """Chính chủ truy cập hồ sơ riêng tư của mình được xem ở chế độ Xem trước (Preview Mode) kèm hướng dẫn."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.trans_private.id

        res = self.client.get(f'/translator/{self.profile_private.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Có banner xem trước và hướng dẫn
        self.assertIn('CHẾ ĐỘ XEM TRƯỚC (PREVIEW MODE)', html)
        self.assertIn('Riêng tư', html)
        self.assertIn('Chỉnh sửa hồ sơ', html)
        # Xem được nội dung của chính mình
        self.assertIn('Lê Hoàng Long', html)
        self.assertIn('Biên phiên dịch Tiếng Nhật', html)

    def test_05_private_profile_accessible_by_admin(self):
        """Admin truy cập hồ sơ riêng tư được xem ở chế độ Xem trước (Preview Mode)."""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['user_id'] = 999

        res = self.client.get(f'/translator/{self.profile_private.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('CHẾ ĐỘ XEM TRƯỚC (PREVIEW MODE)', html)
        self.assertIn('Lê Hoàng Long', html)

    # =========================================================================
    # KỊCH BẢN 4: HỒ SƠ BỊ GIỚI HẠN QUYỀN (RESTRICTED / BANNED PROFILE)
    # =========================================================================
    def test_06_restricted_profile_returns_403_for_visitor(self):
        """Hồ sơ có tài khoản bị vô hiệu hóa (is_active=False) bị chặn truy cập (HTTP 403) đối với người xem ngoài."""
        res = self.client.get(f'/translator/{self.profile_banned.id}')
        self.assertEqual(res.status_code, 403)
        html = res.get_data(as_text=True)

        self.assertIn('Tài khoản bị giới hạn', html)
        self.assertIn('tạm khóa', html.lower())
        self.assertNotIn('Phạm Quốc Bị Khóa', html)

    # =========================================================================
    # KỊCH BẢN 5: KIỂM SOÁT CÔNG KHAI CV CHUYÊN MÔN
    # =========================================================================
    def test_07_public_cv_download_when_opted_in(self):
        """Khi phiên dịch viên bật is_cv_public=True, khách ngoài có thể xem/tải CV an toàn qua /translator/<id>/cv."""
        res = self.client.get(f'/translator/{self.profile_verified.id}/cv?mode=view')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'application/pdf')
        data = res.get_data()
        self.assertTrue(data.startswith(b'%PDF-'))

    def test_08_private_cv_blocked_when_opted_out(self):
        """Khi phiên dịch viên tắt is_cv_public=False, khách ngoài không được phép tải CV qua /translator/<id>/cv."""
        res = self.client.get(f'/translator/{self.profile_unverified.id}/cv')
        # Chuyển hướng hoặc chặn cảnh báo
        self.assertIn(res.status_code, (302, 403))

    # =========================================================================
    # KỊCH BẢN 6: KIỂM TRA QUYỀN SỬA HỒ SƠ
    # =========================================================================
    def test_09_edit_button_only_visible_to_owner(self):
        """Nút chỉnh sửa hồ sơ chỉ hiển thị khi chính chủ đăng nhập; khách ngoài chỉ thấy nút nhắn tin/đặt việc."""
        # 1. Khách ngoài xem
        res_visitor = self.client.get(f'/translator/{self.profile_verified.id}')
        html_visitor = res_visitor.get_data(as_text=True)
        self.assertIn('Nhắn tin trao đổi', html_visitor)
        self.assertNotIn('Chỉnh sửa hồ sơ', html_visitor)

        # 2. Chính chủ xem
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.trans_verified.id
        res_owner = self.client.get(f'/translator/{self.profile_verified.id}')
        html_owner = res_owner.get_data(as_text=True)
        self.assertIn('tab=translator', html_owner)

    # =========================================================================
    # KỊCH BẢN 7: CẬP NHẬT HỒ SƠ NGHỀ NGHIỆP TRONG /account/profile
    # =========================================================================
    def test_10_translator_can_update_professional_profile(self):
        """Phiên dịch viên có thể lưu các thông tin chuyên môn, cặp ngôn ngữ và cài đặt công khai CV."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.trans_unverified.id

        post_data = {
            'action': 'translator_profile',
            'title': 'Chuyên Gia Phiên Dịch Tiếng Hàn Thương Mại & Kỹ Thuật',
            'bio': 'Cập nhật giới thiệu chuyên môn 5 năm kinh nghiệm.',
            'languages': 'Tiếng Hàn, Tiếng Việt, Tiếng Anh',
            'badges': 'Hội nghị, FDI',
            'response_time': '< 3 giờ',
            'is_public': '1',
            'is_cv_public': '1', # Bật công khai CV
            'source_language': 'Tiếng Hàn',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'Hai chiều (Song phương)',
            'language_proficiency': 'Thành thạo (TOPIK 6)',
            'specializations': 'Đầu tư FDI, Bất động sản công nghiệp',
            'work_modes': 'Trực tiếp tại địa điểm (On-site), Trực tuyến',
            'interpreting_types': 'Dịch nối tiếp, Dịch tháp tùng',
            'education_level': 'Cử nhân',
            'university': 'Đại học Quốc gia Seoul',
            'major': 'Ngôn ngữ & Văn hóa Hàn Quốc',
            'cert_name': 'TOPIK Level 6',
            'cert_year': '2022',
            'experience_years': '4',
            'current_position': 'Trưởng nhóm Dịch thuật Hàn - Việt',
            'notable_clients': 'LG Electronics, Lotte Cinema',
            'featured_projects': 'Dự án Mở rộng Nhà máy LG Hải Phòng'
        }

        res = self.client.post('/account/profile', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Kiểm tra database đã lưu đúng
        db.session.refresh(self.profile_unverified)
        self.assertEqual(self.profile_unverified.title, 'Chuyên Gia Phiên Dịch Tiếng Hàn Thương Mại & Kỹ Thuật')
        self.assertTrue(self.profile_unverified.is_public)
        self.assertTrue(self.profile_unverified.is_cv_public)
        self.assertEqual(self.profile_unverified.cert_name, 'TOPIK Level 6')
        self.assertEqual(self.profile_unverified.cert_year, 2022)
        self.assertEqual(self.profile_unverified.experience_years, 4)
        self.assertEqual(self.profile_unverified.notable_clients, 'LG Electronics, Lotte Cinema')


if __name__ == '__main__':
    unittest.main()
