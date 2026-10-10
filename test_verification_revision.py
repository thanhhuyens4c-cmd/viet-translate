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
    save_private_document,
    submit_verification_for_review,
    can_user_revise_verification,
    get_actual_revision_items,
    get_verification_revision_details,
    validate_revision_submission,
    resubmit_verification
)


class VerificationRevisionTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # 1. Tạo hoặc lấy Translator User
        self.translator = User.query.filter_by(email='trans_revision_test@example.com').first()
        if not self.translator:
            self.translator = User(
                name='Nguyễn Văn An',
                email='trans_revision_test@example.com',
                password_hash='pbkdf2:sha256:test',
                phone='0988776655',
                role='translator'
            )
            db.session.add(self.translator)
            db.session.commit()

        # 2. Tạo hoặc lấy Client/Hirer User (test phân quyền)
        self.hirer = User.query.filter_by(email='hirer_revision_test@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Công ty Global Connect',
                email='hirer_revision_test@example.com',
                password_hash='pbkdf2:sha256:test',
                role='client'
            )
            db.session.add(self.hirer)
            db.session.commit()

        # Dọn dẹp dữ liệu cũ của translator
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
        if self.translator.profile:
            self.translator.profile.is_verified = False
        db.session.commit()

    def _create_submitted_verification(self):
        """Khởi tạo một hồ sơ đã nộp thành công ở Phiên bản v1 với CV và Chứng chỉ."""
        verif = TranslatorVerification(
            user_id=self.translator.id,
            status='pending',
            current_step=6,
            full_name='Nguyễn Văn An',
            phone='0988776655',
            gender='male',
            dob='1992-04-15',
            location='Hà Nội',
            bio='Phiên dịch viên tiếng Anh có hơn 4 năm kinh nghiệm dịch hội nghị.',
            source_language='Tiếng Anh',
            target_language='Tiếng Việt',
            primary_language='Tiếng Anh ➔ Tiếng Việt',
            interpreting_direction='two_way',
            language_proficiency='native',
            specializations='Kinh tế, Thương mại',
            interpreting_types='consecutive, simultaneous',
            education_level='bachelor',
            university='Đại học Hà Nội',
            major='Ngôn ngữ Anh',
            certificate_type='IELTS',
            certificate_name='IELTS 8.0',
            cert_year=2021,
            experience_years=4,
            current_position='Conference Interpreter',
            notes='Đã từng dịch cho nhiều sự kiện quốc tế.',
            submission_version=1,
            submitted_at=datetime.utcnow()
        )
        db.session.add(verif)
        db.session.flush()

        # Đính kèm CV
        cv_doc = VerificationDocument(
            user_id=self.translator.id,
            verification_id=verif.id,
            document_type='cv',
            original_filename='NguyenVanAn_CV.pdf',
            stored_filename=f'test_cv_{self.translator.id}_v1.pdf',
            storage_path=f'test/cv_{self.translator.id}.pdf',
            file_size=204800,
            mime_type='application/pdf',
            file_extension='pdf',
            status='uploaded',
            is_active=True
        )
        db.session.add(cv_doc)

        # Đính kèm Chứng chỉ
        cert_doc = VerificationDocument(
            user_id=self.translator.id,
            verification_id=verif.id,
            document_type='certificate',
            original_filename='ielts_blurry.jpg',
            stored_filename=f'test_cert_{self.translator.id}_v1.jpg',
            storage_path=f'test/cert_{self.translator.id}.jpg',
            file_size=153600,
            mime_type='image/jpeg',
            file_extension='jpg',
            status='uploaded',
            is_active=True
        )
        db.session.add(cert_doc)
        db.session.flush()

        # Lưu snapshot v1 vào VerificationSubmissionVersion
        snap_v1 = {
            'version': 1,
            'user': {'id': self.translator.id, 'name': self.translator.name},
            'form_data': verif.get_draft_dict(),
            'documents': [
                {'document_type': 'cv', 'original_filename': 'NguyenVanAn_CV.pdf'},
                {'document_type': 'certificate', 'original_filename': 'ielts_blurry.jpg'}
            ]
        }
        sub_v1 = VerificationSubmissionVersion(
            verification_id=verif.id,
            user_id=self.translator.id,
            version_number=1,
            status='pending',
            snapshot_data=json.dumps(snap_v1, ensure_ascii=False),
            submitted_at=datetime.utcnow()
        )
        verif.submitted_snapshot = json.dumps(snap_v1, ensure_ascii=False)
        db.session.add(sub_v1)
        db.session.commit()
        return verif, cv_doc, cert_doc

    # ─── 1. KIỂM TRA PHÂN QUYỀN TRUY CẬP VÀ TRẠNG THÁI ─────────────────────────

    def test_01_access_permissions_and_state_checks(self):
        """Kiểm tra phân quyền: Chưa đăng nhập, không phải translator, hoặc trạng thái không hợp lệ."""
        # Khách vãng lai
        resp = self.client.get('/account/verification/revision')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

        # Người dùng role 'client'
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.hirer.id
        resp_hirer = self.client.get('/account/verification/revision')
        self.assertEqual(resp_hirer.status_code, 302)
        self.assertIn('/account', resp_hirer.headers['Location'])

        # API role 'client' trả về 403 Forbidden
        api_hirer = self.client.get('/api/account/verification/revision')
        self.assertEqual(api_hirer.status_code, 403)

        # Translator chưa có hồ sơ (not_started)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id
        resp_not_started = self.client.get('/account/verification/revision')
        self.assertEqual(resp_not_started.status_code, 302)
        self.assertTrue(any(x in resp_not_started.headers['Location'] for x in ('/verification/apply', '/account/verification/form', '/form')))

        # Translator có hồ sơ đang 'pending' (không được sửa)
        verif, _, _ = self._create_submitted_verification()
        self.assertEqual(verif.status, 'pending')

        can_rev, rev_err = can_user_revise_verification(self.translator, verif)
        self.assertFalse(can_rev)
        self.assertIn('đang trong hàng đợi xét duyệt', rev_err)

        resp_pending = self.client.get('/account/verification/revision')
        self.assertEqual(resp_pending.status_code, 302)
        self.assertIn('/status', resp_pending.headers['Location'])

        # Translator có hồ sơ đã 'approved' (không cần sửa)
        verif.status = 'approved'
        db.session.commit()
        can_rev_appr, _ = can_user_revise_verification(self.translator, verif)
        self.assertFalse(can_rev_appr)

    # ─── 2. HIỂN THỊ YÊU CẦU BỔ SUNG THỰC TẾ TỪ ADMIN ─────────────────────────

    def test_02_display_actual_admin_revision_items(self):
        """
        Kiểm tra hệ thống hiển thị danh sách hạng mục Admin yêu cầu bổ sung thực tế:
        - Admin reject tài liệu chứng chỉ kèm lý do cụ thể.
        - Admin đặt trạng thái needs_revision và yêu cầu bổ sung kinh nghiệm.
        - Dữ liệu cũ được pre-filled đầy đủ (không bắt nhập lại từ đầu).
        """
        verif, _, cert_doc = self._create_submitted_verification()

        # Admin thẩm định và yêu cầu bổ sung:
        # 1. Từ chối chứng chỉ
        cert_doc.status = 'rejected'
        cert_doc.review_notes = 'Ảnh chụp chứng chỉ IELTS bị mờ góc dưới bên phải, không đọc được số hiệu ID.'
        cert_doc.reviewed_at = datetime.utcnow()

        # 2. Đặt trạng thái hồ sơ và yêu cầu bổ sung kinh nghiệm
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Vui lòng tải lại chứng chỉ rõ nét và bổ sung kinh nghiệm phiên dịch hội nghị chi tiết hơn.'
        verif.reviewed_at = datetime.utcnow()
        db.session.commit()

        # Kiểm tra can_user_revise_verification
        can_rev, _ = can_user_revise_verification(self.translator, verif)
        self.assertTrue(can_rev)

        # Lấy danh sách hạng mục thực tế
        items = get_actual_revision_items(verif, self.translator)
        self.assertEqual(len(items), 2)

        # Mục 1: Tài liệu chứng chỉ bị từ chối
        doc_item = next((i for i in items if i['item_type'] == 'document'), None)
        self.assertIsNotNone(doc_item)
        self.assertEqual(doc_item['document_type'], 'certificate')
        self.assertIn('Chứng chỉ', doc_item['title'])
        self.assertEqual(doc_item['reason'], cert_doc.review_notes)
        self.assertTrue(any(w in doc_item['instruction'].lower() for w in ('chứng chỉ', 'scan', 'thay thế', 'tải lên')))
        self.assertEqual(doc_item['current_filename'], 'ielts_blurry.jpg')
        self.assertFalse(doc_item['is_resolved'])

        # Mục 2: Trường kinh nghiệm
        exp_item = next((i for i in items if i['item_type'] == 'field'), None)
        self.assertIsNotNone(exp_item)
        self.assertIn('Kinh nghiệm', exp_item['title'])
        self.assertIn('bổ sung kinh nghiệm', exp_item['reason'])
        self.assertFalse(exp_item['is_resolved'])

        # Kiểm tra chi tiết đầy đủ từ service get_verification_revision_details
        details = get_verification_revision_details(self.translator)
        self.assertTrue(details['can_revise'])
        self.assertEqual(details['current_version'], 1)
        self.assertEqual(details['next_version'], 2)
        self.assertEqual(details['total_items_count'], 2)
        self.assertEqual(details['resolved_count'], 0)
        self.assertFalse(details['is_all_resolved'])

        # Đảm bảo toàn bộ form_data cũ được bảo lưu (pre-filled)
        self.assertEqual(details['form_data']['full_name'], 'Nguyễn Văn An')
        self.assertEqual(details['form_data']['source_language'], 'Tiếng Anh')
        self.assertEqual(details['form_data']['university'], 'Đại học Hà Nội')

        # Kiểm tra gọi HTTP GET /account/verification/revision trả về 200 và render đủ thông tin
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        resp = self.client.get('/account/verification/revision')
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('Bổ Sung & Hoàn Thiện Hồ Sơ', content)
        self.assertIn('Ảnh chụp chứng chỉ IELTS bị mờ', content)
        self.assertIn('ielts_blurry.jpg', content)
        self.assertIn('Nguyễn Văn An', content)

    # ─── 3. SỬA THIẾU MỤC: HỆ THỐNG TỪ CHỐI GỬI LẠI ────────────────────────────

    def test_03_partially_revised_missing_items_fails(self):
        """
        Kiểm tra trường hợp người dùng SỬA THIẾU MỤC:
        Admin yêu cầu 2 mục (thay thế chứng chỉ + cập nhật kinh nghiệm).
        Người dùng chỉ cập nhật kinh nghiệm nhưng CHƯA thay thế chứng chỉ.
        Hệ thống phải từ chối gửi lại và báo rõ hạng mục còn thiếu.
        """
        verif, _, cert_doc = self._create_submitted_verification()
        cert_doc.status = 'rejected'
        cert_doc.review_notes = 'Chứng chỉ bị mờ, vui lòng chụp lại.'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Cần tải lại chứng chỉ và bổ sung kinh nghiệm phiên dịch hội nghị.'
        db.session.commit()

        # Người dùng chỉ gửi form_data cập nhật kinh nghiệm, KHÔNG gửi tệp chứng chỉ mới
        partial_form = {
            'notes': 'Đã bổ sung kinh nghiệm tham gia dịch 5 hội nghị cấp bộ ngành.',
            'experience_years': 5
        }

        # Kiểm tra validate_revision_submission
        is_val, missing, msg = validate_revision_submission(verif, form_data=partial_form, files={})
        self.assertFalse(is_val)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['document_type'], 'certificate')
        self.assertIn('Chứng chỉ', msg)

        # Thử gọi resubmit_verification -> Thất bại
        ok, res_msg, meta = resubmit_verification(self.translator, form_data=partial_form, files={})
        self.assertFalse(ok)
        self.assertIn('chưa hoàn tất bổ sung', res_msg)
        self.assertEqual(len(meta.get('missing_items', [])), 1)

        # Hồ sơ vẫn giữ nguyên trạng thái needs_revision và version = 1
        db.session.refresh(verif)
        self.assertEqual(verif.status, 'needs_revision')
        self.assertEqual(verif.submission_version, 1)

        # Thử gọi HTTP POST /account/verification/revision/resubmit
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        http_resp = self.client.post(
            '/account/verification/revision/resubmit',
            data=partial_form,
            headers={'Accept': 'application/json'}
        )
        self.assertEqual(http_resp.status_code, 400)
        data = json.loads(http_resp.data)
        self.assertFalse(data['success'])
        self.assertTrue(len(data['missing_items']) > 0)

    # ─── 4. SỬA ĐÚNG MỤC: GỬI LẠI THÀNH CÔNG VÀ LẬP PHIÊN BẢN MỚI ──────────────

    def test_04_correctly_revised_resubmission_succeeds(self):
        """
        Kiểm tra trường hợp người dùng SỬA ĐÚNG VÀ ĐỦ TẤT CẢ CÁC MỤC:
        - Tải lên tệp chứng chỉ mới thay thế tệp bị từ chối.
        - Cập nhật thông tin kinh nghiệm chi tiết.
        - Kết quả:
          * Chuyển hồ sơ về 'pending' (vào hàng đợi xử lý).
          * Tăng submission_version từ 1 -> 2.
          * Lưu snapshot bất biến v2 và giữ nguyên bản ghi v1 để đối chiếu.
          * Xếp thông báo AdminNotification và Notification.
          * Hiển thị thông báo kết quả thực tế.
        """
        verif, _, cert_doc = self._create_submitted_verification()
        cert_doc.status = 'rejected'
        cert_doc.review_notes = 'Chứng chỉ bị mờ, vui lòng chụp lại.'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Cần tải lại chứng chỉ và bổ sung kinh nghiệm phiên dịch hội nghị.'
        db.session.commit()

        # Tạo file ảnh chứng chỉ hợp lệ (JPEG có magic bytes)
        valid_jpeg_bytes = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'dummy_cert_data_123'
        file_obj = (io.BytesIO(valid_jpeg_bytes), 'ielts_clear_scan.jpg')

        revised_form = {
            'notes': 'Đã bổ sung chi tiết: 5 năm kinh nghiệm phiên dịch hội nghị cấp cao, 12 dự án hoàn thành.',
            'experience_years': 5,
            'current_position': 'Lead Conference Interpreter',
            'confirmed': '1'
        }
        revised_files = {
            'doc_file_certificate': file_obj
        }

        ok, success_msg, meta = resubmit_verification(
            user=self.translator,
            form_data=revised_form,
            files=revised_files,
            ip_address='10.0.0.88',
            user_agent='Mozilla/5.0 TestBrowser Resubmit'
        )

        self.assertTrue(ok)
        self.assertIn('thành công', success_msg.lower())
        self.assertEqual(meta['version'], 2)
        self.assertEqual(meta['previous_version'], 1)
        self.assertEqual(meta['status'], 'pending')

        # 1. Kiểm tra trạng thái hồ sơ trong DB
        db.session.refresh(verif)
        self.assertEqual(verif.status, 'pending')
        self.assertEqual(verif.submission_version, 2)
        self.assertIsNotNone(verif.submitted_at)
        self.assertIsNone(verif.rejection_reason)  # Đã làm sạch để chuyển sang vòng duyệt mới

        # 2. Kiểm tra snapshot v2 bất biến
        snap_v2 = verif.get_submitted_snapshot()
        self.assertEqual(snap_v2['version'], 2)
        self.assertEqual(snap_v2['previous_version'], 1)
        self.assertTrue(snap_v2.get('is_revision'))
        self.assertEqual(snap_v2['form_data']['experience_years'], 5)
        self.assertEqual(snap_v2['form_data']['current_position'], 'Lead Conference Interpreter')
        self.assertEqual(snap_v2['ip_address'], '10.0.0.88')

        # Kiểm tra diff được ghi lại trong snapshot
        self.assertIn('diff', snap_v2)
        self.assertIn('experience_years', snap_v2['diff'])
        self.assertEqual(snap_v2['diff']['experience_years']['old'], 4)
        self.assertEqual(snap_v2['diff']['experience_years']['new'], 5)

        # 3. Kiểm tra bảo toàn cả 2 phiên bản trong bảng VerificationSubmissionVersion
        all_versions = VerificationSubmissionVersion.query.filter_by(
            verification_id=verif.id
        ).order_by(VerificationSubmissionVersion.version_number.asc()).all()

        self.assertEqual(len(all_versions), 2)
        self.assertEqual(all_versions[0].version_number, 1)
        self.assertEqual(all_versions[1].version_number, 2)
        self.assertEqual(all_versions[1].status, 'pending')
        self.assertEqual(all_versions[1].ip_address, '10.0.0.88')

        # 4. Kiểm tra tài liệu cũ được đánh dấu 'replaced' và tài liệu mới 'uploaded'
        active_cert = VerificationDocument.query.filter_by(
            verification_id=verif.id, document_type='certificate', is_active=True
        ).first()
        self.assertIsNotNone(active_cert)
        self.assertEqual(active_cert.original_filename, 'ielts_clear_scan.jpg')
        self.assertEqual(active_cert.status, 'uploaded')

        old_cert = VerificationDocument.query.get(cert_doc.id)
        self.assertFalse(old_cert.is_active)
        self.assertEqual(old_cert.status, 'replaced')

        # 5. Kiểm tra thông báo hàng đợi Admin và thông báo người dùng
        admin_notif = AdminNotification.query.filter_by(related_id=verif.id).first()
        self.assertIsNotNone(admin_notif)
        self.assertIn('bổ sung hồ sơ và gửi lại', admin_notif.message)
        self.assertIn('Phiên bản #2', admin_notif.message)

        user_notif = Notification.query.filter_by(
            user_id=self.translator.id, type='VERIFICATION_RESUBMITTED'
        ).first()
        self.assertIsNotNone(user_notif)
        self.assertIn('Phiên bản #2', user_notif.message)

    # ─── 5. NGĂN CHẶN GỬI LẶP VÀ XỬ LÝ LỖI AN TOÀN ─────────────────────────────

    def test_05_prevent_duplicate_resubmission(self):
        """Kiểm tra khi hồ sơ đã được gửi lại và đang 'pending', yêu cầu tiếp theo bị chặn với is_duplicate."""
        verif, _, cert_doc = self._create_submitted_verification()
        # Chỉ có yêu cầu cập nhật ghi chú kinh nghiệm
        cert_doc.status = 'uploaded'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Cần cập nhật kinh nghiệm.'
        db.session.commit()

        # Gửi lại lần 1 thành công
        revised_form = {'notes': 'Cập nhật kinh nghiệm hoàn chỉnh.'}
        ok1, _, meta1 = resubmit_verification(self.translator, form_data=revised_form)
        self.assertTrue(ok1)
        self.assertEqual(meta1['version'], 2)
        self.assertEqual(verif.status, 'pending')

        # Gửi lại lần 2 (người dùng double-click hoặc lặp request)
        ok2, msg2, meta2 = resubmit_verification(self.translator, form_data=revised_form)
        self.assertFalse(ok2)
        self.assertTrue(meta2.get('is_duplicate'))
        self.assertIn('đang trong hàng đợi xử lý', msg2)

        # Đảm bảo không tạo thêm version 3
        count_versions = VerificationSubmissionVersion.query.filter_by(verification_id=verif.id).count()
        self.assertEqual(count_versions, 2)

    def test_06_database_error_rollback_and_safe_retry(self):
        """
        Kiểm tra xử lý lỗi CSDL:
        - Rollback an toàn khi commit thất bại.
        - Không để lại bản ghi rác.
        - Cho phép người dùng thử lại thành công.
        """
        verif, _, cert_doc = self._create_submitted_verification()
        cert_doc.status = 'uploaded'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Cần cập nhật kinh nghiệm.'
        db.session.commit()

        revised_form = {'notes': 'Cập nhật kinh nghiệm chuẩn xác.'}

        # Mô phỏng lỗi CSDL
        with patch('models.db.session.commit', side_effect=Exception('DB Disk I/O Timeout')):
            ok_err, msg_err, meta_err = resubmit_verification(self.translator, form_data=revised_form)
            self.assertFalse(ok_err)
            self.assertIn('Lỗi kết nối', msg_err)

        # Hồ sơ vẫn an toàn, không bị duplicate
        self.assertEqual(TranslatorVerification.query.filter_by(user_id=self.translator.id).count(), 1)
        self.assertEqual(VerificationSubmissionVersion.query.filter_by(verification_id=verif.id).count(), 1)

        # Thử lại lần nữa -> Thành công bình thường
        ok_retry, _, meta_retry = resubmit_verification(self.translator, form_data=revised_form)
        self.assertTrue(ok_retry)
        self.assertEqual(meta_retry['version'], 2)

    # ─── 6. CHỐNG THAO TÚNG DỮ LIỆU TỪ CLIENT ─────────────────────────────────

    def test_07_prevent_tampering_status_or_admin_notes(self):
        """
        Kiểm tra người dùng không thể tự xóa yêu cầu bổ sung hoặc tự đổi trạng thái hồ sơ
        bằng cách truyền param độc hại như status='approved' hay rejection_reason=''.
        """
        verif, _, cert_doc = self._create_submitted_verification()
        cert_doc.status = 'uploaded'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Yêu cầu của Admin'
        db.session.commit()

        # Gửi payload cố tình thao túng status và xóa lý do
        tampered_form = {
            'status': 'approved',
            'rejection_reason': '',
            'notes': 'Thông tin hợp lệ'
        }

        # Thực thi resubmit_verification
        ok, _, meta = resubmit_verification(self.translator, form_data=tampered_form)
        self.assertTrue(ok)

        # Trạng thái PHẢI là 'pending' do máy trạng thái của hệ thống thiết lập, KHÔNG thể là 'approved'
        db.session.refresh(verif)
        self.assertEqual(verif.status, 'pending')
        self.assertNotEqual(verif.status, 'approved')

    # ─── 7. KIỂM TRA HTTP ENDPOINTS VÀ API CHI TIẾT ────────────────────────────

    def test_08_http_revision_endpoints(self):
        """Kiểm tra toàn bộ HTTP Endpoints: GET page, GET api, POST upload document, POST resubmit."""
        verif, _, cert_doc = self._create_submitted_verification()
        cert_doc.status = 'rejected'
        cert_doc.review_notes = 'Ảnh chứng chỉ bị cắt góc.'
        verif.status = 'needs_revision'
        verif.rejection_reason = 'Cần tải lại chứng chỉ.'
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id

        # 1. API GET /api/account/verification/revision
        api_resp = self.client.get('/api/account/verification/revision')
        self.assertEqual(api_resp.status_code, 200)
        api_data = json.loads(api_resp.data)
        self.assertTrue(api_data['success'])
        self.assertEqual(len(api_data['data']['revision_items']), 1)
        self.assertEqual(api_data['data']['current_version'], 1)

        # 2. AJAX Upload replacement document: POST /account/verification/revision/upload-document
        valid_jpeg = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'dummy_cert_ajax'
        upload_resp = self.client.post(
            '/account/verification/revision/upload-document',
            data={
                'document_type': 'certificate',
                'file': (io.BytesIO(valid_jpeg), 'ajax_cert_scan.jpg')
            },
            content_type='multipart/form-data'
        )
        self.assertEqual(upload_resp.status_code, 200)
        upload_data = json.loads(upload_resp.data)
        self.assertTrue(upload_data['success'])
        self.assertEqual(upload_data['document']['status'], 'uploaded')

        # 3. HTTP POST Resubmit qua API: /api/account/verification/revision/resubmit
        resubmit_resp = self.client.post(
            '/api/account/verification/revision/resubmit',
            json={'confirmed': True, 'notes': 'Đã tải chứng chỉ qua AJAX.'},
            headers={'Accept': 'application/json'}
        )
        self.assertEqual(resubmit_resp.status_code, 200)
        resubmit_data = json.loads(resubmit_resp.data)
        self.assertTrue(resubmit_data['success'])
        self.assertEqual(resubmit_data['version'], 2)
        self.assertEqual(resubmit_data['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
