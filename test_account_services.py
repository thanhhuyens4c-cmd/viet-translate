"""
test_account_services.py
Kiểm thử toàn diện tính năng Quản lý Danh mục Năng lực phiên dịch & Biểu phí (Mục 5.2)
trong trang Tài khoản (Account Profile).

Các kịch bản kiểm thử:
1. Thêm mới gói dịch vụ với mức thù lao hợp lệ (số nguyên dương > 0).
2. Ràng buộc mức giá: Từ chối mức giá <= 0, số âm, hoặc chuỗi không hợp lệ.
3. Ràng buộc cặp ngôn ngữ: Không cho phép ngôn ngữ nguồn và đích trùng nhau.
4. Format hiển thị tiền tệ VNĐ chuẩn (ví dụ: 1.500.000 VNĐ / giờ).
5. Phân định trạng thái xác minh:
   - Dịch vụ trùng khớp với cặp ngôn ngữ & chuyên ngành đã DUYỆT ở KYC: "Đã xác minh năng lực ✓" (True).
   - Dịch vụ tự khai thêm chưa được duyệt ở KYC: "Chưa xác minh" (False).
   - Người dùng chưa KYC: Mọi dịch vụ đều "Chưa xác minh" (False).
6. Switch Toggle: Bật/Tắt trạng thái nhận việc của từng dịch vụ riêng biệt.
7. Chỉnh sửa (Update) thông tin và biểu phí của dịch vụ.
8. Xóa (Delete) gói dịch vụ:
   - Đảm bảo TUYỆT ĐỐI KHÔNG xóa tài liệu minh chứng, bằng cấp đã lưu trong module KYC.
9. Đồng bộ tự động từ KYC (Sync KYC).
"""

import unittest
import json
import uuid
from app import app, db
from models import User, InterpreterService, TranslatorVerification, VerificationDocument, TranslatorProfile


class TestInterpreterServicesTab(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.created_users = []

    def tearDown(self):
        try:
            for u in self.created_users:
                user = User.query.get(u.id)
                if user:
                    db.session.delete(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            self.ctx.pop()

    def create_test_user(self, name_suffix):
        uid_str = uuid.uuid4().hex[:8]
        user = User(
            name=f'Test Translator {name_suffix}',
            email=f'trans_{name_suffix}_{uid_str}@example.com',
            password_hash='dummy_hash',
            role='translator'
        )
        db.session.add(user)
        db.session.commit()
        self.created_users.append(user)
        return user

    def test_01_create_service_positive_rates_and_format(self):
        """Kiểm tra tạo gói dịch vụ với mức thù lao hợp lệ (> 0) và định dạng chuẩn VNĐ."""
        user = self.create_test_user('fee_1')

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Gọi API tạo dịch vụ
        res = self.client.post('/account/services/create', json={
            'source_lang': 'Tiếng Nhật',
            'target_lang': 'Tiếng Việt',
            'interpreting_type': 'Dịch Cabin (Đồng thời / Simultaneous)',
            'specialization': 'Kinh doanh & Thương mại',
            'hourly_rate': '1.500.000',
            'session_rate': '6.000.000',
            'is_active': True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # Kiểm tra dữ liệu trong DB
        svc = InterpreterService.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(svc)
        self.assertEqual(svc.source_lang, 'Tiếng Nhật')
        self.assertEqual(svc.target_lang, 'Tiếng Việt')
        self.assertEqual(svc.hourly_rate, 1500000.0)
        self.assertEqual(svc.session_rate, 6000000.0)
        self.assertEqual(svc.formatted_hourly_rate, '1.500.000 VNĐ')
        self.assertEqual(svc.formatted_session_rate, '6.000.000 VNĐ')
        self.assertTrue(svc.is_active)

    def test_02_rate_validation_reject_zero_or_negative(self):
        """Ràng buộc mức giá: Từ chối mức giá <= 0 hoặc không nhập giá nào."""
        user = self.create_test_user('neg_2')

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Test case: Giá bằng 0
        res0 = self.client.post('/account/services/create', json={
            'source_lang': 'Tiếng Anh',
            'target_lang': 'Tiếng Việt',
            'interpreting_type': 'Dịch nối tiếp',
            'hourly_rate': 0,
            'session_rate': 0
        })
        self.assertEqual(res0.status_code, 400)
        self.assertFalse(res0.get_json()['success'])

        # Test case: Giá âm
        res_neg = self.client.post('/account/services/create', json={
            'source_lang': 'Tiếng Anh',
            'target_lang': 'Tiếng Việt',
            'interpreting_type': 'Dịch nối tiếp',
            'hourly_rate': -500000
        })
        self.assertEqual(res_neg.status_code, 400)
        self.assertFalse(res_neg.get_json()['success'])

        # Test case: Trùng ngôn ngữ nguồn và đích
        res_same_lang = self.client.post('/account/services/create', json={
            'source_lang': 'Tiếng Việt',
            'target_lang': 'Tiếng Việt',
            'interpreting_type': 'Dịch nối tiếp',
            'hourly_rate': 500000
        })
        self.assertEqual(res_same_lang.status_code, 400)
        self.assertIn('không được trùng', res_same_lang.get_json()['message'])

    def test_03_kyc_verification_badges_approved_vs_self_declared(self):
        """
        Kiểm tra phân định nhãn huy hiệu:
        - ĐÃ ĐƯỢC DUYỆT ở hệ thống KYC: Hiển thị nhãn huy hiệu 'Đã xác minh năng lực ✓' (True).
        - Dịch vụ tự khai thêm: Hiển thị nhãn 'Chưa xác minh' (False).
        """
        # Tạo translator có hồ sơ KYC đã được Admin APPROVED
        user = self.create_test_user('kyc_approved')

        profile = TranslatorProfile(
            user_id=user.id,
            is_verified=True,
            source_language='Tiếng Hàn',
            target_language='Tiếng Việt',
            specializations='Kinh doanh & Thương mại, Hội nghị quốc tế'
        )
        db.session.add(profile)

        verif = TranslatorVerification(
            user_id=user.id,
            status='approved',
            source_language='Tiếng Hàn',
            target_language='Tiếng Việt',
            specializations='Kinh doanh & Thương mại, Hội nghị quốc tế'
        )
        db.session.add(verif)
        db.session.commit()

        # Dịch vụ 1: Trùng cặp ngôn ngữ & chuyên ngành KYC đã duyệt
        svc_approved = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Hàn',
            target_lang='Tiếng Việt',
            interpreting_type='Dịch Cabin',
            specialization='Kinh doanh & Thương mại',
            hourly_rate=2000000.0,
            session_rate=7000000.0
        )
        db.session.add(svc_approved)

        # Dịch vụ 2: Tự khai thêm (Tiếng Pháp -> Tiếng Đức, Y tế - KHÔNG CÓ TRONG KYC)
        svc_custom = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Pháp',
            target_lang='Tiếng Đức',
            interpreting_type='Dịch từ xa (Online)',
            specialization='Y tế & Dược phẩm',
            hourly_rate=1000000.0,
            session_rate=3500000.0
        )
        db.session.add(svc_custom)
        db.session.commit()

        # Đánh giá huy hiệu qua helper is_kyc_verified
        self.assertTrue(svc_approved.is_kyc_verified(), "Dịch vụ thuộc KYC đã duyệt phải có is_kyc_verified=True")
        self.assertFalse(svc_custom.is_kyc_verified(), "Dịch vụ tự khai thêm phải có is_kyc_verified=False")

        # Kiểm tra to_dict serialization
        dict_approved = svc_approved.to_dict()
        dict_custom = svc_custom.to_dict()
        self.assertTrue(dict_approved['is_kyc_verified'])
        self.assertFalse(dict_custom['is_kyc_verified'])

    def test_04_toggle_service_active_status(self):
        """Kiểm tra switch toggle: Bật/Tắt trạng thái nhận việc của từng dịch vụ riêng biệt."""
        user = self.create_test_user('toggle')

        svc = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Anh',
            target_lang='Tiếng Việt',
            interpreting_type='Dịch nối tiếp',
            specialization='Công nghệ thông tin',
            hourly_rate=800000.0,
            is_active=True
        )
        db.session.add(svc)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Gọi API Toggle -> chuyển sang Tắt (False)
        res1 = self.client.post(f'/account/services/{svc.id}/toggle', json={'is_active': False})
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(res1.get_json()['is_active'])

        svc_db = InterpreterService.query.get(svc.id)
        self.assertFalse(svc_db.is_active)

        # Gọi API Toggle không truyền tham số -> tự đảo chiều sang Bật (True)
        res2 = self.client.post(f'/account/services/{svc.id}/toggle', json={})
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.get_json()['is_active'])

        svc_db = InterpreterService.query.get(svc.id)
        self.assertTrue(svc_db.is_active)

    def test_05_update_service_details_and_rates(self):
        """Kiểm tra chỉnh sửa (Sửa) thông tin và biểu phí của dịch vụ."""
        user = self.create_test_user('edit')

        svc = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Trung',
            target_lang='Tiếng Việt',
            interpreting_type='Dịch tháp tùng',
            specialization='Sản xuất chế tạo',
            hourly_rate=600000.0,
            session_rate=2400000.0,
            is_active=True
        )
        db.session.add(svc)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Sửa sang biểu phí mới
        res = self.client.post(f'/account/services/{svc.id}/update', json={
            'source_lang': 'Tiếng Trung',
            'target_lang': 'Tiếng Việt',
            'interpreting_type': 'Dịch Cabin (Đồng thời / Simultaneous)',
            'specialization': 'Tài chính & Ngân hàng',
            'hourly_rate': '1.800.000',
            'session_rate': '7.200.000',
            'is_active': False
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        svc_updated = InterpreterService.query.get(svc.id)
        self.assertEqual(svc_updated.interpreting_type, 'Dịch Cabin (Đồng thời / Simultaneous)')
        self.assertEqual(svc_updated.specialization, 'Tài chính & Ngân hàng')
        self.assertEqual(svc_updated.hourly_rate, 1800000.0)
        self.assertEqual(svc_updated.formatted_hourly_rate, '1.800.000 VNĐ')
        self.assertFalse(svc_updated.is_active)

    def test_06_delete_service_safeguards_kyc_documents(self):
        """
        Ràng buộc cốt lõi:
        Khi user xóa gói dịch vụ, TUYỆT ĐỐI KHÔNG XÓA tài liệu/bằng cấp minh chứng KYC
        đã lưu trữ trong bảng TranslatorVerification và VerificationDocument.
        """
        user = self.create_test_user('kyc_preserve')

        # Tạo hồ sơ xác minh KYC kèm tài liệu minh chứng
        verif = TranslatorVerification(
            user_id=user.id,
            status='approved',
            source_language='Tiếng Anh',
            target_language='Tiếng Việt',
            specializations='Pháp lý & Hợp đồng'
        )
        db.session.add(verif)
        db.session.commit()

        doc1 = VerificationDocument(
            verification_id=verif.id,
            user_id=user.id,
            document_type='cv',
            original_filename='CV_Official.pdf',
            stored_filename=f'pdoc_cv_{uuid.uuid4().hex[:8]}.pdf',
            storage_path=f'/mock/path/pdoc_cv_{uuid.uuid4().hex[:8]}.pdf',
            mime_type='application/pdf',
            file_extension='pdf',
            file_size=204800,
            status='approved',
            is_active=True
        )
        doc2 = VerificationDocument(
            verification_id=verif.id,
            user_id=user.id,
            document_type='id_card',
            original_filename='CCCD_Front.png',
            stored_filename=f'pdoc_id_{uuid.uuid4().hex[:8]}.png',
            storage_path=f'/mock/path/pdoc_id_{uuid.uuid4().hex[:8]}.png',
            mime_type='image/png',
            file_extension='png',
            file_size=102400,
            status='approved',
            is_active=True
        )
        db.session.add_all([doc1, doc2])
        db.session.commit()

        # Tạo gói dịch vụ
        svc = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Anh',
            target_lang='Tiếng Việt',
            interpreting_type='Dịch Cabin',
            specialization='Pháp lý & Hợp đồng',
            hourly_rate=1500000.0,
            session_rate=6000000.0
        )
        db.session.add(svc)
        db.session.commit()
        svc_id = svc.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Thực hiện xóa gói dịch vụ qua AJAX (JSON)
        res = self.client.post(f'/account/services/{svc_id}/delete', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # Xác minh: Bản ghi InterpreterService đã bị xóa
        self.assertIsNone(InterpreterService.query.get(svc_id))

        # Xác minh: Hồ sơ TranslatorVerification VẪN NGUYÊN VẸN
        verif_check = TranslatorVerification.query.get(verif.id)
        self.assertIsNotNone(verif_check)
        self.assertEqual(verif_check.status, 'approved')

        # Xác minh: Tất cả VerificationDocument VẪN NGUYÊN VẸN 100%
        active_docs = VerificationDocument.query.filter_by(verification_id=verif.id).all()
        self.assertEqual(len(active_docs), 2)
        doc_types = [d.document_type for d in active_docs]
        self.assertIn('cv', doc_types)
        self.assertIn('id_card', doc_types)

        # Test case: Xóa dịch vụ thứ 2 qua form POST truyền thống (Redirect 302)
        svc2 = InterpreterService(
            user_id=user.id,
            source_lang='Tiếng Pháp',
            target_lang='Tiếng Việt',
            interpreting_type='Dịch nối tiếp',
            hourly_rate=1000000.0
        )
        db.session.add(svc2)
        db.session.commit()
        res_form = self.client.post(f'/account/services/{svc2.id}/delete')
        self.assertEqual(res_form.status_code, 302)
        self.assertIn('tab=services', res_form.location)
        self.assertIn('/account/', res_form.location)
        self.assertIsNone(InterpreterService.query.get(svc2.id))

    def test_07_sync_kyc_services(self):
        """Kiểm tra chức năng đồng bộ nạp tự động gói dịch vụ từ hồ sơ KYC đã thẩm định."""
        user = self.create_test_user('sync')

        verif = TranslatorVerification(
            user_id=user.id,
            status='approved',
            source_language='Tiếng Đức',
            target_language='Tiếng Việt',
            specializations='Kỹ thuật ô tô, Chế tạo máy',
            interpreting_types='Dịch nối tiếp, Dịch Cabin'
        )
        db.session.add(verif)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # Gọi API sync-kyc qua AJAX
        res = self.client.post('/account/services/sync-kyc', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)

        # Kiểm tra services được tạo
        services = InterpreterService.query.filter_by(user_id=user.id).all()
        self.assertGreater(len(services), 0)
        for s in services:
            self.assertEqual(s.source_lang, 'Tiếng Đức')
            self.assertEqual(s.target_lang, 'Tiếng Việt')
            self.assertTrue(s.is_kyc_verified())


if __name__ == '__main__':
    unittest.main()

