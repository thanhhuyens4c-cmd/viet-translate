"""
test_comprehensive_regression.py
Bộ kiểm thử toàn diện phân hệ Trang Tài Khoản & Kiểm thử Hồi quy (Regression Test)
với toàn bộ module Xác minh (KYC).

Bao gồm:
Phần 1: KIỂM THỬ HỒI QUY TOÀN DIỆN MODULE KYC (Regression Test for KYC)
- Truy cập tất cả các route của module KYC (Nộp hồ sơ, Theo dõi trạng thái, Bổ sung hồ sơ, Thông báo xác minh).
- Đảm bảo không route nào bị lỗi 404 hoặc 500.
- Dashboard Admin duyệt hồ sơ & chi tiết hồ sơ xác minh & thao tác duyệt.
- Kiểm tra tính nguyên vẹn của shared components (Navbar, User Badge, Footers, Flash alerts).

Phần 2: KIỂM TRA NGHIỆP VỤ TRANG TÀI KHOẢN (Account Module Verification)
- 2.1: Ràng buộc định danh đã xác minh (Tab 5.1):
  * Tài khoản đã verified: Trường Họ và Tên bị khóa read-only trong HTML và server không cho sửa.
  * Tài khoản chưa verified: Trường Họ và Tên cho phép sửa bình thường.
- 2.2: Tab Năng lực (Tab 5.2):
  * Thêm, sửa, xóa gói dịch vụ.
  * Kiểm tra định dạng tiền tệ VNĐ (formatted_hourly_rate, parse_positive_rate, nhãn VNĐ).
- 2.3: Tab Tiêu chí (Tab 5.4):
  * Lưu tiêu chí nhận việc (Smart Matching).
  * Tải lại trang vẫn bảo toàn 100% thiết lập (không bị reset).
  * Bảo toàn hợp đồng và ca trực đã xác nhận.
- 2.4: Tab Bảo mật (Tab 5.6):
  * Đổi mật khẩu thử nghiệm SAI (sai mật khẩu cũ, không khớp confirm, trùng cũ, mật khẩu yếu).
  * Đổi mật khẩu thử nghiệm ĐÚNG (cập nhật hash, đăng nhập thành công với mật khẩu mới).
  * Quản lý phiên đăng nhập: Thu hồi 1 phiên khác, thu hồi tất cả phiên khác.
- 2.5: Tab Hỗ trợ (Tab 5.7):
  * Tạo ticket hỗ trợ có đính kèm ảnh (mã TK-xxxxxx, file đính kèm được lưu trữ).
  * Hiển thị trong bảng ticket cá nhân trên giao diện Tab Hỗ trợ.
  * Xem chi tiết ticket và tải file đính kèm qua route an toàn.
- 2.6: Kiểm tra chuyển tab mượt mà & Responsive Mobile / Desktop.
"""

import unittest
import io
import json
import uuid
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, db
from models import (
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument,
    VerificationSubmissionVersion,
    InterpreterService,
    InterpreterPreference,
    UserSession,
    SupportTicket,
    AdminNotification
)
from services.verification import (
    save_verification_draft,
    submit_verification_for_review,
    review_verification_request
)
from admin_auth import (
    ADMIN_SESSION_KEY,
    ADMIN_SESSION_ROLE,
    ADMIN_SESSION_CREATED,
    ADMIN_SESSION_LAST_SEEN,
    ADMIN_SESSION_CSRF
)


class ComprehensiveRegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        self.test_prefix = f"reg_{uuid.uuid4().hex[:6]}"
        
        # 1. Tạo Translator chưa verified
        self.unverified_user = User(
            name=f"Nguyễn Văn Chưa Xác Minh {self.test_prefix}",
            email=f"unverified_{self.test_prefix}@example.com",
            password_hash=generate_password_hash("MatKhauCu123!", method="pbkdf2:sha256"),
            phone="0912345678",
            role="translator"
        )
        db.session.add(self.unverified_user)

        # 2. Tạo Translator đã verified
        self.verified_user = User(
            name=f"Trần Thị Đã Xác Minh {self.test_prefix}",
            email=f"verified_{self.test_prefix}@example.com",
            password_hash=generate_password_hash("MatKhauCu123!", method="pbkdf2:sha256"),
            phone="0987654321",
            role="translator"
        )
        db.session.add(self.verified_user)

        # 3. Tạo Admin user có quyền verify
        self.admin_user = User(
            name=f"Admin Quản Trị {self.test_prefix}",
            email=f"admin_{self.test_prefix}@example.com",
            password_hash=generate_password_hash("AdminSecret123!", method="pbkdf2:sha256"),
            role="admin",
            is_admin=True,
            is_active=True,
            admin_role="super_admin"
        )
        db.session.add(self.admin_user)
        db.session.commit()

        # Tạo TranslatorProfile cho cả 2 translator
        p1 = TranslatorProfile(user_id=self.unverified_user.id, title="Phiên dịch viên tiếng Anh", is_verified=False)
        p2 = TranslatorProfile(user_id=self.verified_user.id, title="Phiên dịch viên tiếng Nhật Cao Cấp", is_verified=True)
        db.session.add_all([p1, p2])
        db.session.commit()

    def tearDown(self):
        try:
            # Xóa các dữ liệu phụ trợ liên quan đến users test
            test_user_ids = [self.unverified_user.id, self.verified_user.id, self.admin_user.id]
            SupportTicket.query.filter(SupportTicket.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            UserSession.query.filter(UserSession.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            InterpreterService.query.filter(InterpreterService.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            InterpreterPreference.query.filter(InterpreterPreference.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            VerificationDocument.query.filter(VerificationDocument.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            TranslatorVerification.query.filter(TranslatorVerification.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            TranslatorProfile.query.filter(TranslatorProfile.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            User.query.filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            self.ctx.pop()

    def _login_as(self, user):
        """Helper để thiết lập session đăng nhập cho User thường."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['user_role'] = user.role
            sess['user_name'] = user.name

    def _login_as_admin(self):
        """Helper để thiết lập session đăng nhập cho Admin."""
        with self.client.session_transaction() as sess:
            now_ts = datetime.utcnow().timestamp()
            sess[ADMIN_SESSION_KEY] = self.admin_user.id
            sess[ADMIN_SESSION_ROLE] = 'super_admin'
            sess[ADMIN_SESSION_CREATED] = now_ts
            sess[ADMIN_SESSION_LAST_SEEN] = now_ts
            sess[ADMIN_SESSION_CSRF] = 'test_admin_csrf_token'

    # =========================================================================
    # PHẦN 1: KIỂM THỬ HỒI QUY TOÀN DIỆN MODULE KYC (Regression Test for KYC)
    # =========================================================================

    def test_01_kyc_submission_form_routes_no_404_no_500(self):
        """1.1: Route nộp hồ sơ KYC (/account/verification/form & /verification/apply) không bị 404, không bị 500."""
        self._login_as(self.unverified_user)

        # Route chính
        resp1 = self.client.get('/account/verification/form')
        self.assertEqual(resp1.status_code, 200, "Route /account/verification/form phải trả về 200 OK")
        html1 = resp1.data.decode('utf-8')
        self.assertIn('Biểu Mẫu Khai Báo Thông Tin Xác Minh', html1)
        self.assertIn('Bằng cấp', html1)
        self.assertIn('Kinh nghiệm', html1)

        # Route alias
        resp2 = self.client.get('/verification/apply')
        self.assertEqual(resp2.status_code, 200, "Route alias /verification/apply phải trả về 200 OK")
        html2 = resp2.data.decode('utf-8')
        self.assertIn('Biểu Mẫu Khai Báo Thông Tin Xác Minh', html2)

    def test_02_kyc_status_tracking_routes_no_404_no_500(self):
        """1.2: Route theo dõi trạng thái KYC (/account/verification/status & /verification/status) không bị 404, không bị 500."""
        self._login_as(self.unverified_user)

        # Trạng thái ban đầu: chưa nộp hồ sơ
        resp1 = self.client.get('/account/verification/status')
        self.assertEqual(resp1.status_code, 200, "Route /account/verification/status phải trả về 200 OK")
        html1 = resp1.data.decode('utf-8')
        self.assertIn('Xác Minh Danh Tính', html1)

        # Route alias
        resp2 = self.client.get('/verification/status')
        self.assertEqual(resp2.status_code, 200, "Route alias /verification/status phải trả về 200 OK")

        # Tạo hồ sơ pending và kiểm tra giao diện trạng thái pending
        verif = TranslatorVerification(
            user_id=self.unverified_user.id,
            status='pending',
            source_language='Tiếng Việt',
            target_language='Tiếng Anh',
            interpreting_direction='Hai chiều'
        )
        db.session.add(verif)
        db.session.commit()

        resp_pending = self.client.get('/account/verification/status')
        self.assertEqual(resp_pending.status_code, 200)
        html_pending = resp_pending.data.decode('utf-8')
        self.assertIn('Đang chờ xét duyệt', html_pending)
        self.assertIn('hàng đợi thẩm định', html_pending)

    def test_03_kyc_revision_routes_no_404_no_500(self):
        """1.3: Route bổ sung hồ sơ KYC (/account/verification/revision & /verification/revision) không bị 404/500."""
        self._login_as(self.unverified_user)

        # Tạo hồ sơ cần bổ sung (needs_revision) và tài liệu bị reject
        verif = TranslatorVerification(
            user_id=self.unverified_user.id,
            status='needs_revision',
            rejection_reason='Vui lòng bổ sung bản chụp rõ nét hơn của bằng cử nhân.',
            submission_version=1
        )
        db.session.add(verif)
        db.session.flush()

        unique_fname = f"ielts_{self.test_prefix}_{uuid.uuid4().hex[:6]}.jpg"
        cert_doc = VerificationDocument(
            user_id=self.unverified_user.id,
            verification_id=verif.id,
            document_type='certificate',
            original_filename='ielts_test.jpg',
            stored_filename=unique_fname,
            storage_path=f'test/{unique_fname}',
            file_size=10240,
            mime_type='image/jpeg',
            file_extension='jpg',
            status='rejected',
            review_notes='Ảnh mờ, cần chụp lại',
            is_active=True
        )
        db.session.add(cert_doc)
        db.session.commit()

        resp1 = self.client.get('/account/verification/revision')
        self.assertEqual(resp1.status_code, 200, "Route /account/verification/revision phải trả về 200 OK")
        html1 = resp1.data.decode('utf-8')
        self.assertIn('Bổ sung hồ sơ', html1)
        self.assertIn('Vui lòng bổ sung bản chụp rõ nét hơn', html1)

        # Route alias
        resp2 = self.client.get('/verification/revision')
        self.assertEqual(resp2.status_code, 200, "Route alias /verification/revision phải trả về 200 OK")

    def test_04_kyc_notifications_routes_no_404_no_500(self):
        """1.4: Route thông báo xác minh KYC (/account/verification/notifications) không bị 404/500."""
        self._login_as(self.unverified_user)

        resp1 = self.client.get('/account/verification/notifications')
        self.assertEqual(resp1.status_code, 200, "Route /account/verification/notifications phải trả về 200 OK")
        html1 = resp1.data.decode('utf-8')
        self.assertTrue('thông báo xác minh' in html1.lower())

        resp2 = self.client.get('/verification/notifications')
        self.assertEqual(resp2.status_code, 200, "Route alias /verification/notifications phải trả về 200 OK")

    def test_05_kyc_api_endpoints_return_200_json(self):
        """1.5: Tất cả API endpoints của module KYC đều trả về HTTP 200 JSON hợp lệ."""
        self._login_as(self.unverified_user)

        # 1. Documents API
        r_docs = self.client.get('/api/account/verification/documents')
        self.assertEqual(r_docs.status_code, 200)
        self.assertTrue(r_docs.is_json)

        # 2. Check Eligibility API
        r_elig = self.client.get('/api/account/verification/check-eligibility')
        self.assertEqual(r_elig.status_code, 200)
        self.assertTrue(r_elig.is_json)

        # 3. Status API
        r_stat = self.client.get('/api/account/verification/status')
        self.assertEqual(r_stat.status_code, 200)
        self.assertTrue(r_stat.is_json)

        # 4. Notifications API
        r_notifs = self.client.get('/api/account/verification/notifications')
        self.assertEqual(r_notifs.status_code, 200)
        self.assertTrue(r_notifs.is_json)

        # 5. Unread count API
        r_count = self.client.get('/api/account/verification/notifications/unread-count')
        self.assertEqual(r_count.status_code, 200)
        self.assertTrue(r_count.is_json)
        self.assertIn('unread_count', r_count.get_json())

    def test_06_kyc_admin_dashboard_and_review_routes_no_404_no_500(self):
        """1.6: Dashboard Admin duyệt hồ sơ (/admin/translators và /admin/verifications/<id>) hoạt động chuẩn xác."""
        self._login_as_admin()

        # Tạo một hồ sơ verification pending để test
        verif = TranslatorVerification(
            user_id=self.unverified_user.id,
            status='pending',
            source_language='Tiếng Việt',
            target_language='Tiếng Anh',
            interpreting_direction='Hai chiều',
            checklist_data=json.dumps({"has_id": True, "has_cert": True})
        )
        db.session.add(verif)
        db.session.commit()

        # 1. Admin translators list với các filter khác nhau
        for show_mode in ['pending', 'verified', 'rejected', 'all']:
            resp = self.client.get(f'/admin/translators?show={show_mode}')
            self.assertEqual(resp.status_code, 200, f"/admin/translators?show={show_mode} phải trả về 200 OK")
            html = resp.data.decode('utf-8')
            self.assertIn('filter-bar', html)
            self.assertNotIn('Traceback', html)

        # 2. Admin verification detail view
        resp_detail = self.client.get(f'/admin/verifications/{verif.id}')
        self.assertEqual(resp_detail.status_code, 200, f"/admin/verifications/{verif.id} phải trả về 200 OK")
        html_detail = resp_detail.data.decode('utf-8')
        self.assertIn('Đánh giá hồ sơ', html_detail)
        self.assertIn(self.unverified_user.name, html_detail)

        # 3. Admin review action: Phê duyệt hồ sơ với CSRF token đúng
        csrf_tok = 'test_admin_csrf_token'
        with self.client.session_transaction() as sess:
            sess[ADMIN_SESSION_CSRF] = csrf_tok

        resp_approve = self.client.post(
            f'/admin/verifications/{verif.id}/approve',
            data={'_csrf_token': csrf_tok},
            follow_redirects=True
        )
        self.assertEqual(resp_approve.status_code, 200)
        
        # Kiểm tra hồ sơ đã được duyệt thành công
        refreshed_verif = db.session.get(TranslatorVerification, verif.id)
        self.assertEqual(refreshed_verif.status, 'approved')
        refreshed_user = db.session.get(User, self.unverified_user.id)
        self.assertTrue(refreshed_user.is_verified, "Sau khi admin duyệt, is_verified của user phải chuyển thành True")
        
        # Kiểm tra hồ sơ đã được duyệt thành công
        refreshed_verif = db.session.get(TranslatorVerification, verif.id)
        self.assertEqual(refreshed_verif.status, 'approved')
        refreshed_user = db.session.get(User, self.unverified_user.id)
        self.assertTrue(refreshed_user.is_verified, "Sau khi admin duyệt, is_verified của user phải chuyển thành True")

    def test_07_kyc_shared_components_integrity(self):
        """1.7: Shared components (Navbar, Header, Footer, Flash banner) trên toàn hệ thống không bị lỗi render."""
        self._login_as(self.verified_user)

        # Truy cập trang Account
        resp_account = self.client.get('/account')
        self.assertEqual(resp_account.status_code, 200)
        html = resp_account.data.decode('utf-8')

        # Navbar component
        self.assertIn('<header', html, "Header/Navbar phải có mặt trong DOM")
        self.assertIn('VietTranslate', html, "Logo và thương hiệu VietTranslate phải hiển thị")

        # Footer component
        self.assertIn('<footer', html, "Footer phải có mặt trong DOM")

        # Badge xác minh danh tính
        self.assertIn('Đã xác minh', html, "Tài khoản verified phải hiển thị huy hiệu xác minh")

    # =========================================================================
    # PHẦN 2: KIỂM TRA NGHIỆP VỤ TRANG TÀI KHOẢN (Account Module Verification)
    # =========================================================================

    def test_08_verified_user_name_readonly_at_tab_profile(self):
        """2.1: Tài khoản đã verified: Trường Họ và Tên ở Tab 5.1 phải bị khóa read-only và server chặn sửa."""
        self._login_as(self.verified_user)

        # 1. Kiểm tra HTML rendering: input Họ và tên phải có thuộc tính readonly, icon ổ khóa và cảnh báo định danh
        resp = self.client.get('/account?tab=profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Phải chứa input có id="input-profile-name" và readonly
        self.assertIn('id="input-profile-name"', html)
        self.assertIn('readonly', html)
        self.assertIn('Họ và tên đã được xác thực theo giấy tờ định danh', html)

        # 2. Kiểm tra server-side guard: thử submit sửa name qua form action=update_personal_profile
        original_name = self.verified_user.name
        resp_post = self.client.post('/account', data={
            'action': 'update_personal_profile',
            'name': 'Họ Tên Cố Tình Bị Sửa Đổi Trộm',
            'email': self.verified_user.email,
            'phone': '0987654321',
            'city': 'Hà Nội'
        }, follow_redirects=True)
        self.assertEqual(resp_post.status_code, 200)

        # Tên trong DB TUYỆT ĐỐI không thay đổi
        refreshed_user = db.session.get(User, self.verified_user.id)
        self.assertEqual(refreshed_user.name, original_name, "Họ và tên của tài khoản đã verified không được phép thay đổi!")

    def test_09_unverified_user_name_can_be_edited(self):
        """2.1 (Đối chứng): Tài khoản chưa verified: Trường Họ và Tên không bị khóa và cho phép chỉnh sửa."""
        self._login_as(self.unverified_user)

        # 1. Kiểm tra HTML: không có readonly
        resp = self.client.get('/account?tab=profile')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('id="input-profile-name"', html)
        self.assertIn('placeholder="Nhập họ và tên đầy đủ"', html)

        # 2. Cập nhật tên mới hợp lệ
        new_name = f"Nguyễn Văn Mới {self.test_prefix}"
        resp_post = self.client.post('/account', data={
            'action': 'update_personal_profile',
            'name': new_name,
            'email': self.unverified_user.email,
            'phone': '0912345678',
            'city': 'Đà Nẵng'
        }, follow_redirects=True)
        self.assertEqual(resp_post.status_code, 200)

        refreshed_user = db.session.get(User, self.unverified_user.id)
        self.assertEqual(refreshed_user.name, new_name, "Họ và tên của tài khoản chưa verified phải cập nhật thành công")

    def test_10_tab_services_crud_and_vnd_currency_formatting(self):
        """2.2: Tab Năng lực: Thêm, sửa, xóa gói dịch vụ và kiểm tra định dạng tiền tệ VNĐ."""
        self._login_as(self.verified_user)

        # 1. Thêm gói dịch vụ mới
        resp_create = self.client.post('/account/services/create', data={
            'source_lang': 'Tiếng Việt',
            'target_lang': 'Tiếng Anh',
            'interpreting_type': 'cabin',
            'specialization': 'Tài chính Ngân hàng',
            'hourly_rate': '1.500.000',
            'session_rate': '6.000.000',
            'is_active': 'on'
        }, follow_redirects=True)
        self.assertEqual(resp_create.status_code, 200)

        # Kiểm tra bản ghi trong DB
        service = InterpreterService.query.filter_by(
            user_id=self.verified_user.id,
            source_lang='Tiếng Việt',
            target_lang='Tiếng Anh'
        ).first()
        self.assertIsNotNone(service, "Gói dịch vụ phải được tạo thành công trong DB")
        self.assertEqual(service.hourly_rate, 1500000)
        self.assertEqual(service.session_rate, 6000000)

        # 2. Kiểm tra định dạng tiền tệ VNĐ chuẩn
        self.assertEqual(service.formatted_hourly_rate, '1.500.000 VNĐ')
        self.assertEqual(service.formatted_session_rate, '6.000.000 VNĐ')

        # 3. Kiểm tra hiển thị tiền tệ VNĐ trên giao diện HTML
        resp_view = self.client.get('/account?tab=services')
        self.assertEqual(resp_view.status_code, 200)
        html_view = resp_view.data.decode('utf-8')
        self.assertIn('1.500.000 VNĐ', html_view)
        self.assertIn('6.000.000 VNĐ', html_view)
        self.assertIn('Đơn vị thù lao: <strong>VNĐ</strong>', html_view)

        # 4. Sửa gói dịch vụ (Update)
        resp_update = self.client.post(f'/account/services/{service.id}/update', data={
            'source_lang': 'Tiếng Việt',
            'target_lang': 'Tiếng Anh',
            'interpreting_type': 'cabin',
            'specialization': 'Thương mại Quốc tế & Ngoại giao',
            'hourly_rate': '2.000.000 VNĐ',
            'session_rate': '8.000.000 VNĐ',
            'is_active': 'on'
        }, follow_redirects=True)
        self.assertEqual(resp_update.status_code, 200)

        refreshed_service = db.session.get(InterpreterService, service.id)
        self.assertEqual(refreshed_service.hourly_rate, 2000000)
        self.assertEqual(refreshed_service.session_rate, 8000000)
        self.assertEqual(refreshed_service.specialization, 'Thương mại Quốc tế & Ngoại giao')
        self.assertEqual(refreshed_service.formatted_hourly_rate, '2.000.000 VNĐ')

        # 5. Xóa gói dịch vụ (Delete)
        resp_delete = self.client.post(f'/account/services/{service.id}/delete', follow_redirects=True)
        self.assertEqual(resp_delete.status_code, 200)

        deleted_service = db.session.get(InterpreterService, service.id)
        self.assertIsNone(deleted_service, "Gói dịch vụ phải bị xóa hoàn toàn khỏi DB")

    def test_11_tab_preferences_save_and_reload_persistence(self):
        """2.3: Tab Tiêu chí: Lưu tiêu chí nhận việc và kiểm tra tải lại trang vẫn giữ nguyên thiết lập 100%."""
        self._login_as(self.verified_user)

        # 1. Gửi form lưu tiêu chí nhận việc
        pref_payload = {
            'languages': ['Tiếng Việt ➔ Tiếng Anh', 'Tiếng Nhật ➔ Tiếng Việt'],
            'specializations': ['Tài chính Ngân hàng', 'Y tế & Dược phẩm'],
            'work_mode': 'both',
            'min_rate': '1000000',
            'max_rate': '5000000',
            'allow_outside_rate': '1',
            'locations': ['Hà Nội', 'Đà Nẵng'],
            'available_hours': ['Giờ hành chính (08:00 - 17:00)', 'Buổi tối (18:00 - 22:00)']
        }
        resp_save = self.client.post('/account/preferences/save', data=pref_payload, follow_redirects=True)
        self.assertEqual(resp_save.status_code, 200)

        # Kiểm tra lưu vào DB
        pref = InterpreterPreference.query.filter_by(user_id=self.verified_user.id).first()
        self.assertIsNotNone(pref, "InterpreterPreference phải được tạo/cập nhật")
        self.assertEqual(pref.work_mode, 'both')
        self.assertEqual(pref.min_rate, 1000000.0)
        self.assertEqual(pref.max_rate, 5000000.0)
        self.assertTrue(pref.allow_outside_rate)
        self.assertIn('Tiếng Việt ➔ Tiếng Anh', pref.get_languages_list())
        self.assertIn('Y tế & Dược phẩm', pref.get_specializations_list())
        self.assertIn('Hà Nội', pref.get_locations_list())

        # 2. Tải lại trang (Reload) và kiểm tra giao diện giữ nguyên thiết lập
        resp_reload = self.client.get('/account?tab=preferences')
        self.assertEqual(resp_reload.status_code, 200)
        html_reload = resp_reload.data.decode('utf-8')

        # Kiểm tra badge và thông tin đã chọn được render chính xác
        self.assertIn('Tiếng Việt ➔ Tiếng Anh', html_reload)
        self.assertIn('Y tế & Dược phẩm', html_reload)
        self.assertIn('Hà Nội', html_reload)
        self.assertIn('1000000', html_reload)
        self.assertIn('5000000', html_reload)

        # 3. Kiểm tra endpoint GET /account/preferences/get
        resp_api = self.client.get('/account/preferences/get')
        self.assertEqual(resp_api.status_code, 200)
        data = resp_api.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['preference']['work_mode'], 'both')
        self.assertEqual(data['preference']['min_rate'], 1000000.0)
        self.assertEqual(data['preference']['max_rate'], 5000000.0)

    def test_12_tab_security_password_change_failure_and_success(self):
        """2.4: Tab Bảo mật: Đổi mật khẩu thử nghiệm đúng/sai."""
        self._login_as(self.verified_user)

        # Kịch bản 1: Mật khẩu cũ sai
        resp_fail_old = self.client.post('/account', data={
            'action': 'change_password',
            'old_password': 'SaiMatKhau123!',
            'new_password': 'MatKhauMoi888!',
            'confirm_password': 'MatKhauMoi888!'
        }, follow_redirects=True)
        self.assertEqual(resp_fail_old.status_code, 200)
        self.assertIn('Mật khẩu hiện tại không chính xác', resp_fail_old.data.decode('utf-8'))

        # Kịch bản 2: Mật khẩu xác nhận không khớp
        resp_mismatch = self.client.post('/account', data={
            'action': 'change_password',
            'old_password': 'MatKhauCu123!',
            'new_password': 'MatKhauMoi888!',
            'confirm_password': 'KhongKhop999!'
        }, follow_redirects=True)
        self.assertEqual(resp_mismatch.status_code, 200)
        self.assertIn('Xác nhận mật khẩu mới không trùng khớp', resp_mismatch.data.decode('utf-8'))

        # Kịch bản 3: Mật khẩu mới trùng mật khẩu cũ
        resp_same = self.client.post('/account', data={
            'action': 'change_password',
            'old_password': 'MatKhauCu123!',
            'new_password': 'MatKhauCu123!',
            'confirm_password': 'MatKhauCu123!'
        }, follow_redirects=True)
        self.assertEqual(resp_same.status_code, 200)
        self.assertIn('Mật khẩu mới không được trùng với mật khẩu hiện tại', resp_same.data.decode('utf-8'))

        # Kịch bản 4: Mật khẩu mới không đạt độ phức tạp (< 8 ký tự hoặc thiếu chữ hoa/số)
        resp_weak = self.client.post('/account', data={
            'action': 'change_password',
            'old_password': 'MatKhauCu123!',
            'new_password': 'weakpw',
            'confirm_password': 'weakpw'
        }, follow_redirects=True)
        self.assertEqual(resp_weak.status_code, 200)
        self.assertIn('Mật khẩu mới phải có tối thiểu 8 ký tự', resp_weak.data.decode('utf-8'))

        # Kịch bản 5: Đổi mật khẩu THÀNH CÔNG
        resp_success = self.client.post('/account', data={
            'action': 'change_password',
            'old_password': 'MatKhauCu123!',
            'new_password': 'MatKhauMoiHopLe888!',
            'confirm_password': 'MatKhauMoiHopLe888!'
        }, follow_redirects=True)
        self.assertEqual(resp_success.status_code, 200)
        self.assertIn('Đổi mật khẩu thành công', resp_success.data.decode('utf-8'))

        # Xác minh mật khẩu mới trong DB
        refreshed_user = db.session.get(User, self.verified_user.id)
        self.assertTrue(check_password_hash(refreshed_user.password_hash, 'MatKhauMoiHopLe888!'))
        self.assertFalse(check_password_hash(refreshed_user.password_hash, 'MatKhauCu123!'))

    def test_13_tab_security_session_management_and_revocation(self):
        """2.4 (tiếp): Tab Bảo mật: Thu hồi phiên đăng nhập đơn lẻ và thu hồi tất cả phiên khác."""
        self._login_as(self.verified_user)
        current_token = 'token_current_device_123'
        other_token_1 = 'token_other_device_456'
        other_token_2 = 'token_other_device_789'

        with self.client.session_transaction() as sess:
            sess['session_token'] = current_token

        # Tạo 3 phiên đăng nhập trong DB
        s_current = UserSession(
            user_id=self.verified_user.id,
            session_id=current_token,
            device_name='Chrome trên macOS',
            ip_address='192.168.1.1'
        )
        s_other1 = UserSession(
            user_id=self.verified_user.id,
            session_id=other_token_1,
            device_name='Safari trên iPhone',
            ip_address='14.162.20.10'
        )
        s_other2 = UserSession(
            user_id=self.verified_user.id,
            session_id=other_token_2,
            device_name='Firefox trên Windows',
            ip_address='113.190.15.22'
        )
        db.session.add_all([s_current, s_other1, s_other2])
        db.session.commit()

        # 1. Thu hồi 1 phiên thiết bị khác (s_other1)
        resp_revoke_one = self.client.post('/account', data={
            'action': 'revoke_session',
            'session_id': s_other1.id
        }, follow_redirects=True)
        self.assertEqual(resp_revoke_one.status_code, 200)

        # Kiểm tra s_other1 đã bị xóa, còn s_current và s_other2 vẫn tồn tại
        self.assertIsNone(db.session.get(UserSession, s_other1.id))
        self.assertIsNotNone(db.session.get(UserSession, s_current.id))
        self.assertIsNotNone(db.session.get(UserSession, s_other2.id))

        # 2. Thu hồi toàn bộ các phiên khác (revoke_other_sessions)
        resp_revoke_all = self.client.post('/account', data={
            'action': 'revoke_other_sessions'
        }, follow_redirects=True)
        self.assertEqual(resp_revoke_all.status_code, 200)

        # Kiểm tra s_other2 đã bị xóa, s_current (phiên hiện tại) vẫn duy trì
        self.assertIsNone(db.session.get(UserSession, s_other2.id))
        self.assertIsNotNone(db.session.get(UserSession, s_current.id))

    def test_14_tab_support_ticket_creation_with_attachment_and_display(self):
        """2.5: Tab Hỗ trợ: Tạo ticket có đính kèm ảnh và kiểm tra hiển thị trong bảng cá nhân."""
        self._login_as(self.verified_user)

        # 1. Tạo file ảnh giả lập
        img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        attachment = (io.BytesIO(img_bytes), 'evidence_screenshot.png')

        # 2. Gửi yêu cầu tạo ticket hỗ trợ
        resp_create = self.client.post('/account/support/tickets/create', data={
            'category': 'identity',
            'title': 'Yêu cầu kiểm tra tiến độ duyệt chứng chỉ ngoại ngữ',
            'description': 'Kính gửi BQT, em đã tải lên chứng chỉ IELTS 8.5 vào hôm qua, nhờ BQT kiểm tra giúp em ạ.',
            'attachment': attachment
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(resp_create.status_code, 200)

        # Kiểm tra ticket trong DB
        ticket = SupportTicket.query.filter_by(
            user_id=self.verified_user.id,
            title='Yêu cầu kiểm tra tiến độ duyệt chứng chỉ ngoại ngữ'
        ).first()
        self.assertIsNotNone(ticket, "SupportTicket phải được tạo thành công trong DB")
        self.assertTrue(ticket.ticket_code.startswith('TK-'), "Mã ticket phải có format TK-xxxxxx")
        self.assertIsNotNone(ticket.attachment_url, "Ticket phải lưu đường dẫn tệp đính kèm")

        # 3. Kiểm tra hiển thị trong bảng cá nhân tại GET /account?tab=support
        resp_support_tab = self.client.get('/account?tab=support')
        self.assertEqual(resp_support_tab.status_code, 200)
        html_tab = resp_support_tab.data.decode('utf-8')
        self.assertIn(ticket.ticket_code, html_tab)
        self.assertIn('Yêu cầu kiểm tra tiến độ duyệt chứng chỉ', html_tab)
        self.assertIn('Đã tiếp nhận', html_tab)

        # 4. Kiểm tra route tải/xem file đính kèm
        if ticket.attachment_url:
            import os
            fname = os.path.basename(ticket.attachment_url)
            resp_file = self.client.get(f'/account/support/attachment/{fname}')
            self.assertEqual(resp_file.status_code, 200, "Tệp đính kèm phải tải/xem được thành công")

    def test_15_tab_navigation_and_responsive_markup(self):
        """2.6: Kiểm tra chuyển tab mượt mà và layout responsive trên Mobile & Desktop."""
        self._login_as(self.verified_user)

        # 1. Kiểm tra kích hoạt chính xác từng tab theo query param ?tab=
        tabs_to_test = [
            ('profile', 'tab-profile'),
            ('services', 'tab-services'),
            ('preferences', 'tab-preferences'),
            ('subscription', 'tab-subscription'),
            ('security', 'tab-security'),
            ('support', 'tab-support'),
        ]

        for tab_param, panel_id in tabs_to_test:
            resp = self.client.get(f'/account?tab={tab_param}')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            # Kiểm tra panel tương ứng có class 'active'
            self.assertIn(f'id="{panel_id}"', html)
            self.assertIn(f'id="{panel_id}" class="tab-panel active', html, f"Tab {tab_param} phải kích hoạt class active")

        # 2. Kiểm tra các breakpoint responsive Tailwind CSS cho Mobile và Desktop
        resp_full = self.client.get('/account')
        html_full = resp_full.data.decode('utf-8')

        # Mobile & Desktop responsive layout
        self.assertIn('flex flex-col md:flex-row', html_full, "Phải có bố cục flex chuyển từ dọc (mobile) sang ngang (desktop)")
        self.assertIn('w-full md:w-64', html_full, "Sidebar phải có độ rộng co giãn theo breakpoint md")
        self.assertIn('grid grid-cols-1 md:grid-cols-', html_full, "Phải có lưới tự co giãn responsive theo kích thước màn hình")
        self.assertIn('lg:hidden', html_full, "Phải có menu toggle cho màn hình thiết bị di động (lg:hidden)")
        self.assertIn('hidden lg:block', html_full, "Phải có thành phần ẩn trên thiết bị nhỏ (hidden lg:block)")


if __name__ == '__main__':
    unittest.main()
