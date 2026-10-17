import unittest
import os
import io
import json
import zipfile
from app import app
from models import db, User, TranslatorProfile, TranslatorVerification, VerificationDocument
from services.verification import (
    DOCUMENT_POLICIES,
    detect_file_type_from_bytes,
    save_private_document,
    get_private_verification_folder,
    can_user_access_document,
    can_user_modify_verification_documents
)

class VerificationDocumentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Tạo / Tìm Translator User A (Chủ sở hữu)
        self.translator_a = User.query.filter_by(email='test_trans_a@example.com').first()
        if not self.translator_a:
            self.translator_a = User(
                name='Nguyễn Văn A',
                email='test_trans_a@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.translator_a)
            db.session.commit()

        # Tạo / Tìm Translator User B (Người dùng khác)
        self.translator_b = User.query.filter_by(email='test_trans_b@example.com').first()
        if not self.translator_b:
            self.translator_b = User(
                name='Trần Thị B',
                email='test_trans_b@example.com',
                password_hash='pbkdf2:sha256:test',
                role='translator'
            )
            db.session.add(self.translator_b)
            db.session.commit()

        # Tạo / Tìm Client Hirer (Khách hàng)
        self.hirer = User.query.filter_by(email='test_hirer_doc@example.com').first()
        if not self.hirer:
            self.hirer = User(
                name='Khách Hàng C',
                email='test_hirer_doc@example.com',
                password_hash='pbkdf2:sha256:test',
                role='client'
            )
            db.session.add(self.hirer)
            db.session.commit()

        # Tạo / Tìm Admin User
        self.admin = User.query.filter_by(email='test_admin_doc@example.com').first()
        if not self.admin:
            self.admin = User(
                name='Admin Quản Trị',
                email='test_admin_doc@example.com',
                password_hash='pbkdf2:sha256:test',
                role='admin'
            )
            db.session.add(self.admin)
            db.session.commit()

        # Dọn dẹp dữ liệu kiểm thử cũ của user A và B
        VerificationDocument.query.filter(VerificationDocument.user_id.in_([self.translator_a.id, self.translator_b.id])).delete()
        TranslatorVerification.query.filter(TranslatorVerification.user_id.in_([self.translator_a.id, self.translator_b.id])).delete()
        db.session.commit()

    def tearDown(self):
        # Dọn dẹp dữ liệu
        VerificationDocument.query.filter(VerificationDocument.user_id.in_([self.translator_a.id, self.translator_b.id])).delete()
        TranslatorVerification.query.filter(TranslatorVerification.user_id.in_([self.translator_a.id, self.translator_b.id])).delete()
        db.session.commit()
        self.ctx.pop()

    def create_mock_pdf(self, content=b'%PDF-1.4 mock pdf content for verification'):
        return io.BytesIO(content)

    def create_mock_png(self, content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'):
        return io.BytesIO(content)

    def create_mock_docx(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types></Types>')
            z.writestr('word/document.xml', '<w:document></w:document>')
        buf.seek(0)
        return buf

    # ─── 1. KIỂM TRA CHỮ KÝ NHỊ PHÂN MÁY CHỦ (MAGIC BYTES) ───────────────────────

    def test_01_magic_bytes_detection(self):
        """Kiểm tra máy chủ nhận diện đúng định dạng nhị phân và từ chối tệp giả mạo."""
        # PDF thật
        self.assertEqual(detect_file_type_from_bytes(b'%PDF-1.5 Sample'), 'pdf')
        # PNG thật
        self.assertEqual(detect_file_type_from_bytes(b'\x89PNG\r\n\x1a\n'), 'png')
        # JPEG thật
        self.assertEqual(detect_file_type_from_bytes(b'\xff\xd8\xff\xe0\x00\x10JFIF'), 'jpeg')
        # DOCX thật
        docx_bytes = self.create_mock_docx().getvalue()
        self.assertEqual(detect_file_type_from_bytes(docx_bytes), 'docx')

        # TỆP GIẢ MẠO: Nội dung HTML/Script nhưng người dùng đổi tên thành .pdf hoặc .jpg
        fake_pdf = b'<html><script>alert("hack")</script></html>'
        self.assertIsNone(detect_file_type_from_bytes(fake_pdf))

        # TỆP GIẢ MẠO: File zip thông thường đổi tên thành .docx
        generic_zip = io.BytesIO()
        with zipfile.ZipFile(generic_zip, 'w') as z:
            z.writestr('script.sh', 'rm -rf /')
        self.assertIsNone(detect_file_type_from_bytes(generic_zip.getvalue()))

    # ─── 2. KIỂM TRA TẢI TỆP THÀNH CÔNG VÀ LƯU VÙNG RIÊNG TƯ ─────────────────────

    def test_02_successful_upload_and_private_storage(self):
        """Kiểm tra tải lên tài liệu thành công, lưu metadata và bảo mật vùng riêng tư."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        pdf_data = (self.create_mock_pdf(), 'my_cv.pdf')
        resp = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': pdf_data
        }, headers={'X-Requested-With': 'XMLHttpRequest'})

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIn('document', data)
        doc_info = data['document']
        self.assertEqual(doc_info['document_type'], 'cv')
        self.assertEqual(doc_info['original_filename'], 'my_cv.pdf')
        self.assertEqual(doc_info['status'], 'uploaded')  # Trạng thái ban đầu

        # Kiểm tra CSDL
        doc_record = VerificationDocument.query.get(doc_info['id'])
        self.assertIsNotNone(doc_record)
        self.assertEqual(doc_record.user_id, self.translator_a.id)
        self.assertEqual(doc_record.mime_type, 'application/pdf')
        self.assertTrue(doc_record.is_active)

        # Kiểm tra tệp được lưu ở thư mục riêng tư và KHÔNG nằm trong static
        self.assertTrue(os.path.exists(doc_record.storage_path))
        self.assertNotIn('static', doc_record.storage_path)

        # Kiểm tra tên tệp vật lý ngẫu nhiên bảo mật (không lộ tên gốc)
        self.assertTrue(doc_record.stored_filename.startswith('pdoc_cv_'))
        self.assertNotEqual(doc_record.stored_filename, 'my_cv.pdf')

        # NGUYÊN TẮC QUAN TRỌNG: Tải thành công KHÔNG đồng nghĩa tài khoản đã được xác minh!
        profile = TranslatorProfile.query.filter_by(user_id=self.translator_a.id).first()
        if profile:
            self.assertFalse(profile.is_verified)

    # ─── 3. KIỂM TRA TẢI TỆP THẤT BẠI VÀ THÔNG BÁO LỖI CỤ THỂ ───────────────────

    def test_03_upload_failures_with_specific_errors(self):
        """Kiểm tra hệ thống từ chối tải lên và trả về lỗi cụ thể trong các tình huống vi phạm."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        # 3.1: Không chọn tệp
        resp1 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp1.status_code, 400)
        data1 = json.loads(resp1.data)
        self.assertFalse(data1['success'])
        self.assertIn('Vui lòng chọn tệp', data1['message'])

        # 3.2: Loại tài liệu không hợp lệ (ngoài chính sách)
        resp2 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'unsupported_type',
            'file': (self.create_mock_pdf(), 'test.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp2.status_code, 400)
        data2 = json.loads(resp2.data)
        self.assertIn('không nằm trong chính sách', data2['message'])

        # 3.3: Định dạng mở rộng không được hỗ trợ (ví dụ file .exe)
        resp3 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (io.BytesIO(b'MZ executable payload'), 'malware.exe')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp3.status_code, 400)
        data3 = json.loads(resp3.data)
        self.assertIn('không được hỗ trợ', data3['message'])

        # 3.4: Tệp rỗng (0 bytes)
        resp4 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (io.BytesIO(b''), 'empty.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp4.status_code, 400)
        data4 = json.loads(resp4.data)
        self.assertIn('rỗng', data4['message'])

        # 3.5: Giả mạo định dạng (Đổi đuôi .html thành .pdf)
        fake_content = b'<!DOCTYPE html><html><body><h1>Fake Document</h1></body></html>'
        resp5 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (io.BytesIO(fake_content), 'fake_resume.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp5.status_code, 400)
        data5 = json.loads(resp5.data)
        self.assertIn('chữ ký nhị phân', data5['message'])

        # 3.6: Vượt quá dung lượng tối đa cho phép (> 10MB)
        # Giả lập 10.5 MB dữ liệu PDF
        large_bytes = b'%PDF-1.4 ' + (b'0' * (10 * 1024 * 1024 + 500 * 1024))
        resp6 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (io.BytesIO(large_bytes), 'huge.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp6.status_code, 400)
        data6 = json.loads(resp6.data)
        self.assertIn('vượt quá giới hạn', data6['message'])

    # ─── 4. KIỂM TRA THAY THẾ TÀI LIỆU THEO TRẠNG THÁI HỒ SƠ ────────────────────

    def test_04_replace_document_by_profile_status(self):
        """Kiểm tra thay thế tài liệu thành công khi ở draft/rejected, và chặn khi pending."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        # Tải tài liệu lần 1 (CV v1)
        resp1 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (self.create_mock_pdf(b'%PDF-1.4 version 1'), 'cv_v1.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        doc1_id = json.loads(resp1.data)['document']['id']
        doc1 = VerificationDocument.query.get(doc1_id)
        self.assertTrue(doc1.is_active)

        # Tải tài liệu lần 2 (CV v2 - Thay thế khi đang ở draft)
        resp2 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (self.create_mock_pdf(b'%PDF-1.4 version 2'), 'cv_v2.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp2.status_code, 200)
        doc2_id = json.loads(resp2.data)['document']['id']

        db.session.refresh(doc1)
        doc2 = VerificationDocument.query.get(doc2_id)
        # Bản cũ bị đánh dấu đã thay thế
        self.assertFalse(doc1.is_active)
        self.assertEqual(doc1.status, 'replaced')
        # Bản mới hoạt động
        self.assertTrue(doc2.is_active)
        self.assertEqual(doc2.status, 'uploaded')

        # CHUYỂN HỒ SƠ SANG TRẠNG THÁI 'pending' (Đang xét duyệt)
        verif = TranslatorVerification.query.filter_by(user_id=self.translator_a.id).first()
        verif.status = 'pending'
        db.session.commit()

        # Thử thay thế tài liệu khi hồ sơ pending -> PHẢI BỊ CHẶN
        resp3 = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'cv',
            'file': (self.create_mock_pdf(b'%PDF-1.4 version 3'), 'cv_v3.pdf')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp3.status_code, 400)
        data3 = json.loads(resp3.data)
        self.assertIn('thẩm định', data3['message'])

    # ─── 5. KIỂM TRA KIỂM SOÁT QUYỀN TRUY CẬP (BACKEND RBAC SECURITY) ────────────

    def test_05_unauthorized_access_and_rbac(self):
        """Kiểm tra chặn truy cập trái phép vào tài liệu riêng tư (401, 403) và cho phép chủ sở hữu / Admin."""
        # Tải tài liệu bí mật của User A (CCCD)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        resp = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'id_card',
            'file': (self.create_mock_png(), 'cccd_private.png')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        doc_id = json.loads(resp.data)['document']['id']

        # 5.1: KHÁCH VÃNG LAI (Chưa đăng nhập) -> Bị chuyển hướng hoặc chặn (401 / redirect)
        with self.client.session_transaction() as sess:
            sess.clear()

        unauth_resp = self.client.get(f'/account/verification/documents/{doc_id}/download')
        self.assertEqual(unauth_resp.status_code, 302)  # Redirect tới trang đăng nhập

        unauth_view = self.client.get(f'/account/verification/documents/{doc_id}/view')
        self.assertEqual(unauth_view.status_code, 302)

        # 5.2: NGƯỜI DÙNG KHÁC (Translator B) cố truy cập tài liệu của A -> 403 FORBIDDEN
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_b.id

        forbidden_download = self.client.get(f'/account/verification/documents/{doc_id}/download')
        self.assertEqual(forbidden_download.status_code, 403)

        forbidden_view = self.client.get(f'/account/verification/documents/{doc_id}/view')
        self.assertEqual(forbidden_view.status_code, 403)

        forbidden_delete = self.client.post(f'/account/verification/documents/{doc_id}/delete', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertIn(forbidden_delete.status_code, (400, 403))  # Lỗi không có quyền truy cập / từ chối thao tác

        # 5.3: CLIENT HIRER (Khách thuê dịch) cố truy cập tài liệu riêng tư -> 403 FORBIDDEN
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.hirer.id

        hirer_download = self.client.get(f'/account/verification/documents/{doc_id}/download')
        self.assertEqual(hirer_download.status_code, 403)

        # 5.4: CHÍNH CHỦ SỞ HỮU (Translator A) truy cập -> 200 OK
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        owner_download = self.client.get(f'/account/verification/documents/{doc_id}/download')
        self.assertEqual(owner_download.status_code, 200)
        self.assertEqual(owner_download.headers.get('X-Content-Type-Options'), 'nosniff')

        owner_view = self.client.get(f'/account/verification/documents/{doc_id}/view')
        self.assertEqual(owner_view.status_code, 200)

        # 5.5: QUẢN TRỊ VIÊN (Admin) truy cập để xét duyệt -> 200 OK
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin.id

        admin_download = self.client.get(f'/account/verification/documents/{doc_id}/download')
        self.assertEqual(admin_download.status_code, 200)

        admin_view = self.client.get(f'/account/verification/documents/{doc_id}/view')
        self.assertEqual(admin_view.status_code, 200)

    # ─── 6. KIỂM TRA HIỂN THỊ KẾT QUẢ ĐÁNH GIÁ TÀI LIỆU ─────────────────────────

    def test_06_document_evaluation_status_sync(self):
        """Kiểm tra hiển thị trạng thái đánh giá tài liệu nếu có kết quả thẩm định từ Ban quản trị."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        # Tải tài liệu
        resp = self.client.post('/account/verification/documents/upload', data={
            'document_type': 'certificate',
            'file': (self.create_mock_png(), 'ielts_80.png')
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        doc_id = json.loads(resp.data)['document']['id']
        doc = VerificationDocument.query.get(doc_id)
        self.assertEqual(doc.status, 'uploaded')

        # Giả lập Admin đánh giá từ chối với lý do
        from services.verification import review_verification_request
        verif = doc.verification
        review_verification_request(verif.id, self.admin, action='reject', reason='Ảnh chứng chỉ bị mờ, không rõ ngày cấp.')

        db.session.refresh(doc)
        self.assertEqual(doc.status, 'rejected')
        self.assertEqual(doc.review_notes, 'Ảnh chứng chỉ bị mờ, không rõ ngày cấp.')
        self.assertIsNotNone(doc.reviewed_at)

        # API trả về đúng kết quả đánh giá cho giao diện
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator_a.id

        api_resp = self.client.get('/api/account/verification/documents')
        self.assertEqual(api_resp.status_code, 200)
        api_data = json.loads(api_resp.data)
        doc_api = next((d for d in api_data['documents'] if d['id'] == doc_id), None)
        self.assertIsNotNone(doc_api)
        self.assertEqual(doc_api['status'], 'rejected')
        self.assertEqual(doc_api['review_notes'], 'Ảnh chứng chỉ bị mờ, không rõ ngày cấp.')

if __name__ == '__main__':
    unittest.main()
