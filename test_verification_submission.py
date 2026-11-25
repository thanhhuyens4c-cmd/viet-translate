import unittest
import io
import json
from unittest.mock import patch
from datetime import datetime

from app import app
from models import (
    db,
    User,
    TranslatorProfile,
    TranslatorVerification,
    VerificationDocument,
    VerificationSubmissionVersion,
    AdminNotification,
    Notification
)
from services.verification import (
    get_or_create_verification_draft,
    save_verification_draft,
    validate_verification_eligibility,
    submit_verification_for_review,
    can_user_modify_verification_documents,
    save_private_document
)


class VerificationSubmissionTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # 1. Tạo hoặc lấy Translator User
        self.translator = User.query.filter_by(email='trans_submit_test@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Lê Hoàng Nam',
                email='trans_submit_test@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0987654321',
                role='translator'
            )
            db.session.add(self.translator)
            db.session.commit()

        # 2. Tạo hoặc lấy Hirer User (để test phân quyền không phải translator)
        self.hirer = User.query.filter_by(email='hirer_submit_test@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Công ty ABC',
                email='hirer_submit_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='client'
            )
            db.session.add(self.hirer)
            db.session.commit()

        # Dọn sạch dữ liệu test cũ của user
        self._clean_data()

    def tearDown(self):
        self._clean_data()
        self.ctx.pop()

    def _clean_data(self):
        VerificationSubmissionVersion.query.filter_by(user_id=self.translator.id).delete()
        VerificationDocument.query.filter_by(user_id=self.translator.id).delete()
        AdminNotification.query.filter(AdminNotification.title.like('%xác minh%')).delete()
        Notification.query.filter_by(user_id=self.translator.id).delete()
        TranslatorVerification.query.filter_by(user_id=self.translator.id).delete()
        db.session.commit()

    def _fill_complete_draft(self, verification):
        """Điền đầy đủ dữ liệu hợp lệ cho tất cả các bước khai báo (Bước 1-5)."""
        draft_data = {
            # Bước 1: Cá nhân
            'full_name': 'Lê Hoàng Nam',
            'phone': '0987654321',
            'gender': 'male',
            'dob': '1995-05-20',
            'location': 'Hà Nội',
            'bio': 'Phiên dịch viên chuyên nghiệp hơn 5 năm kinh nghiệm trong lĩnh vực hội nghị quốc tế.',
            # Bước 2: Ngôn ngữ
            'source_language': 'Tiếng Anh',
            'target_language': 'Tiếng Việt',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'native',
            # Bước 3: Lĩnh vực
            'specializations': 'Công nghệ, Kinh tế, Y tế',
            'interpreting_types': 'simultaneous, consecutive',
            # Bước 4: Học vấn & Chứng chỉ
            'education_level': 'bachelor',
            'university': 'Đại học Ngoại ngữ - ĐHQGHN',
            'major': 'Ngôn ngữ Anh',
            'certificate_type': 'IELTS',
            'certificate_name': 'IELTS Academic 8.5',
            'cert_year': 2021,
            # Bước 5: Kinh nghiệm
            'experience_years': 5,
            'current_position': 'Senior Conference Interpreter',
            'notable_clients': 'Tập đoàn FPT, Viettel',
            'featured_projects': 'Diễn đàn Kinh tế Việt Nam 2023',
            'notes': 'Sẵn sàng đi công tác nước ngoài.'
        }
        for k, v in draft_data.items():
            setattr(verification, k, v)
        verification.primary_language = 'Tiếng Anh ➔ Tiếng Việt'
        verification.draft_data = json.dumps(draft_data, ensure_ascii=False)
        verification.current_step = 6
        db.session.commit()
        return draft_data

    def _attach_cv_document(self, verification):
        """Đính kèm tài liệu CV (bắt buộc theo chính sách DOCUMENT_POLICIES)."""
        cv_doc = VerificationDocument(
            user_id=self.translator.id,
            verification_id=verification.id,
            document_type='cv',
            original_filename='LeHoangNam_CV_2026.pdf',
            stored_filename=f'test_cv_{self.translator.id}_{int(datetime.utcnow().timestamp())}.pdf',
            storage_path=f'test/path/cv_{self.translator.id}.pdf',
            file_size=1024 * 350,
            mime_type='application/pdf',
            file_extension='pdf',
            file_hash='fake_hash_123',
            is_active=True,
            status='uploaded'
        )
        db.session.add(cv_doc)
        db.session.commit()
        return cv_doc

    # ─── 1. KIỂM TRA DỮ LIỆU BẮT BUỘC Ở BACKEND (BƯỚC 1 - 5) ───────────────────

    def test_01_eligibility_validation_missing_fields(self):
        """Kiểm tra backend từ chối nếu hồ sơ thiếu các trường khai báo bắt buộc."""
        draft = get_or_create_verification_draft(self.translator)
        self.assertEqual(draft.status, 'draft')

        # Dữ liệu chỉ mới có tên và sđt (mới ở Bước 1)
        is_eligible, errors_dict, error_messages = validate_verification_eligibility(
            draft, additional_data={'confirmed': True}, require_confirmation=True
        )

        self.assertFalse(is_eligible)
        self.assertIn('source_language', errors_dict)
        self.assertIn('target_language', errors_dict)
        self.assertIn('specializations', errors_dict)
        self.assertIn('education_level', errors_dict)
        self.assertIn('document_cv', errors_dict)
        self.assertTrue(len(error_messages) > 0)

        # Thử gọi submit_verification_for_review -> phải thất bại và giữ nguyên draft
        ok, msg, meta = submit_verification_for_review(self.translator, confirmed=True)
        self.assertFalse(ok)
        self.assertIn('chưa đủ điều kiện', msg)
        self.assertTrue(len(meta.get('error_list', [])) > 0)
        self.assertEqual(draft.status, 'draft')

    # ─── 2. KIỂM TRA TÀI LIỆU CẦN THIẾT THEO CHÍNH SÁCH (CV LÀ BẮT BUỘC) ────────

    def test_02_eligibility_validation_missing_required_cv(self):
        """Kiểm tra backend từ chối khi đã điền đầy đủ form nhưng thiếu CV bắt buộc."""
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)

        # Chưa tải CV lên -> eligibility check phải báo lỗi tài liệu bắt buộc
        is_eligible, errors_dict, error_messages = validate_verification_eligibility(
            draft, additional_data={'confirmed': True}, require_confirmation=True
        )
        self.assertFalse(is_eligible)
        self.assertIn('document_cv', errors_dict)
        self.assertTrue(any('Sơ yếu lý lịch (CV' in msg for msg in error_messages))

        # Thử gửi hồ sơ
        ok, msg, meta = submit_verification_for_review(self.translator, confirmed=True)
        self.assertFalse(ok)
        self.assertIn('document_cv', meta.get('errors', {}))
        self.assertEqual(draft.status, 'draft')

    # ─── 3. YÊU CẦU NGƯỜI DÙNG XÁC NHẬN CAM KẾT TRƯỚC KHI GỬI ──────────────────

    def test_03_require_user_confirmation_pledge(self):
        """Kiểm tra backend từ chối gửi nếu người dùng chưa tích xác nhận cam kết (confirmed=False)."""
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        # Gửi nhưng confirmed=False
        ok, msg, meta = submit_verification_for_review(self.translator, confirmed=False)
        self.assertFalse(ok)
        self.assertIn('confirmed', meta.get('errors', {}))
        self.assertTrue(any('xác nhận cam kết' in m for m in meta.get('error_list', [])))
        self.assertEqual(draft.status, 'draft')

    # ─── 4. GỬI HỒ SƠ THÀNH CÔNG, LẬP PHIÊN BẢN VÀ LƯU SNAPSHOT BẤT BIẾN ────────

    def test_04_successful_submission_and_snapshot(self):
        """
        Kiểm tra luồng gửi hồ sơ hoàn chỉnh:
        - Chuyển status -> 'pending'.
        - Ghi thời điểm submitted_at.
        - Lập submission_version = 1.
        - Lưu snapshot bất biến vào submitted_snapshot.
        - Tạo bản ghi VerificationSubmissionVersion audit trail.
        - Enqueue AdminNotification.
        """
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)
        cv = self._attach_cv_document(draft)

        ok, msg, meta = submit_verification_for_review(
            self.translator,
            confirmed=True,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 TestBrowser'
        )

        self.assertTrue(ok)
        self.assertIn('thành công', msg.lower())
        self.assertEqual(meta['version'], 1)
        self.assertEqual(meta['status'], 'pending')

        # Kiểm tra trạng thái trong DB
        db.session.refresh(draft)
        self.assertEqual(draft.status, 'pending')
        self.assertEqual(draft.submission_version, 1)
        self.assertIsNotNone(draft.submitted_at)
        self.assertIsNotNone(draft.submitted_snapshot)

        # Kiểm tra nội dung snapshot
        snapshot = draft.get_submitted_snapshot()
        self.assertEqual(snapshot['version'], 1)
        self.assertEqual(snapshot['user']['email'], self.translator.email)
        self.assertEqual(snapshot['form_data']['full_name'], 'Lê Hoàng Nam')
        self.assertEqual(snapshot['form_data']['certificate_name'], 'IELTS Academic 8.5')
        self.assertEqual(len(snapshot['documents']), 1)
        self.assertEqual(snapshot['documents'][0]['document_type'], 'cv')
        self.assertEqual(snapshot['documents'][0]['original_filename'], 'LeHoangNam_CV_2026.pdf')
        self.assertTrue(snapshot['pledge_confirmed'])
        self.assertEqual(snapshot['ip_address'], '192.168.1.100')

        # Kiểm tra bản ghi trong bảng VerificationSubmissionVersion
        version_rec = VerificationSubmissionVersion.query.filter_by(
            verification_id=draft.id, version_number=1
        ).first()
        self.assertIsNotNone(version_rec)
        self.assertEqual(version_rec.status, 'pending')
        self.assertEqual(version_rec.user_id, self.translator.id)
        self.assertEqual(version_rec.ip_address, '192.168.1.100')

        # Kiểm tra đã xếp vào hàng đợi Admin (AdminNotification)
        admin_notif = AdminNotification.query.filter_by(related_id=draft.id).first()
        self.assertIsNotNone(admin_notif)
        self.assertEqual(admin_notif.type, 'NEW_TRANSLATOR')
        self.assertIn(self.translator.name, admin_notif.message)
        self.assertIn('Phiên bản #1', admin_notif.message)

        # Kiểm tra thông báo cho translator
        user_notif = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_SUBMITTED'
        ).first()
        self.assertIsNotNone(user_notif)

    # ─── 5. NGĂN CHẶN GỬI LẶP DO BẤM NÚT NHIỀU LẦN (ANTI-DUPLICATE GUARD) ────────

    def test_05_prevent_duplicate_submission(self):
        """Kiểm tra khi hồ sơ đã ở trạng thái pending, các yêu cầu gửi tiếp theo bị từ chối với is_duplicate."""
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        # Gửi lần 1: thành công
        ok1, msg1, meta1 = submit_verification_for_review(self.translator, confirmed=True)
        self.assertTrue(ok1)
        self.assertEqual(draft.status, 'pending')

        initial_count = TranslatorVerification.query.filter_by(user_id=self.translator.id).count()
        initial_version_count = VerificationSubmissionVersion.query.filter_by(verification_id=draft.id).count()

        # Gửi lần 2 (người dùng click liên tiếp hoặc lặp request):
        ok2, msg2, meta2 = submit_verification_for_review(self.translator, confirmed=True)
        self.assertFalse(ok2)
        self.assertTrue(meta2.get('is_duplicate'))
        self.assertIn('hàng đợi xử lý', msg2)

        # Đảm bảo không tạo thêm bản ghi trùng lặp nào
        self.assertEqual(TranslatorVerification.query.filter_by(user_id=self.translator.id).count(), initial_count)
        self.assertEqual(VerificationSubmissionVersion.query.filter_by(verification_id=draft.id).count(), initial_version_count)

    # ─── 6. BẢO TOÀN TÍNH BẤT BIẾN SAU KHI GỬI (KHÔNG CHO SỬA ÂM THẦM) ──────────

    def test_06_prevent_modifications_after_submission(self):
        """Kiểm tra sau khi gửi, không cho phép sửa âm thầm draft hoặc sửa/xóa tài liệu."""
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        ok, msg, meta = submit_verification_for_review(self.translator, confirmed=True)
        self.assertTrue(ok)
        self.assertEqual(draft.status, 'pending')

        # Thử sửa nháp qua save_verification_draft -> phải bị chặn
        save_ok, _, save_msg = save_verification_draft(
            self.translator,
            form_data={'source_language': 'Tiếng Pháp'},
            target_step=2
        )
        self.assertFalse(save_ok)
        self.assertIn('quá trình Ban quản trị thẩm định', save_msg)

        # Kiểm tra quyền sửa tài liệu
        can_modify, _ = can_user_modify_verification_documents(self.translator, draft)
        self.assertFalse(can_modify)

    # ─── 7. XỬ LÝ LỖI KẾT NỐI VÀ CHO PHÉP THỬ LẠI MÀ KHÔNG TẠO HỒ SƠ TRÙNG ───────

    def test_07_connection_error_handling_and_retry_without_duplicates(self):
        """
        Kiểm tra khi xảy ra lỗi DB commit:
        - Hệ thống rollback an toàn.
        - Hồ sơ không bị duplicate.
        - Người dùng có thể thử lại và gửi thành công trên CÙNG bản ghi hồ sơ.
        """
        draft = get_or_create_verification_draft(self.translator)
        draft_id = draft.id
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        # Mô phỏng lỗi commit (ví dụ mất kết nối CSDL)
        with patch('models.db.session.commit', side_effect=Exception('DB connection timeout')):
            ok_err, msg_err, meta_err = submit_verification_for_review(self.translator, confirmed=True)
            self.assertFalse(ok_err)
            self.assertIn('Lỗi kết nối', msg_err)

        # Sau khi lỗi, số lượng bản ghi vẫn là 1 (không tạo bản trùng)
        self.assertEqual(TranslatorVerification.query.filter_by(user_id=self.translator.id).count(), 1)

        # Người dùng sửa lại và thử gửi lại lần nữa -> thành công
        ok_retry, msg_retry, meta_retry = submit_verification_for_review(self.translator, confirmed=True)
        self.assertTrue(ok_retry)
        self.assertEqual(meta_retry['version'], 1)

        # Bản ghi vẫn chính là bản ghi ban đầu (cùng ID)
        db.session.refresh(draft)
        self.assertEqual(draft.id, draft_id)
        self.assertEqual(draft.status, 'pending')
        self.assertEqual(TranslatorVerification.query.filter_by(user_id=self.translator.id).count(), 1)

    # ─── 8. GỬI LẠI SAU KHI BỊ TỪ CHỐI TĂNG PHIÊN BẢN (VERSION INCREMENT) ─────────

    def test_08_resubmission_after_rejection_increments_version(self):
        """Kiểm tra khi Admin từ chối và yêu cầu bổ sung, phiên dịch viên gửi lại sẽ tăng version = 2."""
        draft = get_or_create_verification_draft(self.translator)
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        # Lần 1: gửi thành công -> version 1
        ok1, _, meta1 = submit_verification_for_review(self.translator, confirmed=True)
        self.assertTrue(ok1)
        self.assertEqual(meta1['version'], 1)

        # Admin từ chối hồ sơ
        draft.status = 'rejected'
        draft.rejection_reason = 'Vui lòng bổ sung kinh nghiệm phiên dịch hội nghị chi tiết hơn.'
        db.session.commit()

        # Phiên dịch viên được phép chỉnh sửa lại sau khi rejected
        can_modify_after_reject, _ = can_user_modify_verification_documents(self.translator, draft)
        self.assertTrue(can_modify_after_reject)

        # Cập nhật thông tin bổ sung và gửi lại (Lần 2)
        additional_form = {'notes': 'Đã bổ sung chi tiết 3 dự án phiên nghị sự APEC.'}
        ok2, msg2, meta2 = submit_verification_for_review(self.translator, form_data=additional_form, confirmed=True)
        self.assertTrue(ok2)
        self.assertEqual(meta2['version'], 2)

        db.session.refresh(draft)
        self.assertEqual(draft.status, 'pending')
        self.assertEqual(draft.submission_version, 2)
        self.assertIsNone(draft.rejection_reason)

        # Có 2 bản ghi lịch sử trong VerificationSubmissionVersion: v1 và v2
        versions = VerificationSubmissionVersion.query.filter_by(verification_id=draft.id).order_by(
            VerificationSubmissionVersion.version_number.asc()
        ).all()
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].version_number, 1)
        self.assertEqual(versions[1].version_number, 2)

    # ─── 9. KIỂM TRA HTTP ENDPOINT (POST /account/verification/submit) ────────────

    def test_09_http_post_submission_endpoint(self):
        """Kiểm tra gọi trực tiếp HTTP POST /account/verification/submit với JSON và xác thực kết quả."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        draft = get_or_create_verification_draft(self.translator)

        # Case 1: Thiếu thông tin -> HTTP 400 và danh sách lỗi
        res1 = self.client.post(
            '/account/verification/submit',
            json={'confirmed': True},
            headers={'Accept': 'application/json'}
        )
        self.assertEqual(res1.status_code, 400)
        data1 = json.loads(res1.data)
        self.assertFalse(data1['success'])
        self.assertTrue(len(data1['error_list']) > 0)

        # Điền đủ form và đính kèm CV
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        # Case 2: Hợp lệ -> HTTP 200
        res2 = self.client.post(
            '/account/verification/submit',
            json={'confirmed': True},
            headers={'Accept': 'application/json'}
        )
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertTrue(data2['success'])
        self.assertEqual(data2['version'], 1)
        self.assertIsNotNone(data2['submitted_at'])

        # Case 3: Gửi lặp lại ngay sau đó -> HTTP 409 Conflict
        res3 = self.client.post(
            '/account/verification/submit',
            json={'confirmed': True},
            headers={'Accept': 'application/json'}
        )
        self.assertEqual(res3.status_code, 409)
        data3 = json.loads(res3.data)
        self.assertFalse(data3['success'])
        self.assertTrue(data3['is_duplicate'])

    # ─── 10. KIỂM TRA API CHECK-ELIGIBILITY ───────────────────────────────────────

    def test_10_api_check_eligibility(self):
        """Kiểm tra endpoint /api/account/verification/check-eligibility."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        draft = get_or_create_verification_draft(self.translator)

        # Khi chưa đủ điều kiện
        res1 = self.client.get('/api/account/verification/check-eligibility')
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        self.assertFalse(data1['is_eligible'])
        self.assertTrue(len(data1['errors']) > 0)

        # Sau khi điền đủ và có CV
        self._fill_complete_draft(draft)
        self._attach_cv_document(draft)

        res2 = self.client.get('/api/account/verification/check-eligibility')
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertTrue(data2['is_eligible'])
        self.assertEqual(len(data2['errors']), 0)


if __name__ == '__main__':
    unittest.main()
