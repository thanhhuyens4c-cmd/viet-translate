import unittest
import os
import io
from app import app
from models import db, User, TranslatorProfile, TranslatorVerification, VerificationDocument, Job, Proposal, Contract
from services.verification import resolve_document_file_path, save_private_document

class TestCvComprehensiveAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_active_cv_document_excludes_rejected_and_replaced(self):
        """Kiểm tra active_cv_document loại trừ trạng thái rejected, replaced, deleted"""
        user = User.query.filter_by(role='translator').first()
        self.assertIsNotNone(user)

        # Tạo doc 1: rejected
        doc_rejected = VerificationDocument(
            verification_id=user.verifications[0].id if user.verifications else 1,
            user_id=user.id,
            document_type='cv',
            original_filename='rejected_cv.pdf',
            stored_filename='test_rejected_cv.pdf',
            storage_path='instance/storage/private_verifications/test_rejected_cv.pdf',
            status='rejected',
            is_active=True,
            file_extension='pdf',
            mime_type='application/pdf'
        )
        db.session.add(doc_rejected)
        db.session.commit()

        # Nếu chỉ có doc_rejected thì active_cv_document không được trả về doc này
        active_doc = user.profile.active_cv_document if user.profile else user.active_cv_document
        if active_doc:
            self.assertNotEqual(active_doc.id, doc_rejected.id)

        # Cleanup
        db.session.delete(doc_rejected)
        db.session.commit()

    def test_02_effective_cv_properties_on_verification(self):
        """Kiểm tra effective_cv_filename và effective_cv_url ưu tiên VerificationDocument"""
        user = User.query.filter_by(role='translator').first()
        self.assertIsNotNone(user)

        verif = user.latest_verification
        if not verif:
            verif = TranslatorVerification(user_id=user.id, status='verified')
            db.session.add(verif)
            db.session.commit()

        # Tạo VerificationDocument hợp lệ gắn với verif
        cv_doc = VerificationDocument(
            verification_id=verif.id,
            user_id=user.id,
            document_type='cv',
            original_filename='Ho_So_Chuyen_Mon_2026.pdf',
            stored_filename='pdoc_test_cv_2026.pdf',
            storage_path='instance/storage/private_verifications/pdoc_test_cv_2026.pdf',
            status='approved',
            is_active=True,
            file_extension='pdf',
            mime_type='application/pdf'
        )
        db.session.add(cv_doc)
        db.session.commit()

        self.assertEqual(verif.effective_cv_filename, 'Ho_So_Chuyen_Mon_2026.pdf')
        self.assertEqual(verif.effective_cv_url, f"/account/verification/documents/{cv_doc.id}/download")

        # Cleanup
        db.session.delete(cv_doc)
        db.session.commit()

    def test_03_format_aware_public_cv_view_vs_download(self):
        """Kiểm tra DOCX tự động chuyển thành attachment, PDF hỗ trợ inline"""
        user = User.query.filter_by(role='translator').first()
        self.assertIsNotNone(user)

        if not user.profile:
            user.profile = TranslatorProfile(user_id=user.id)
            db.session.add(user.profile)
            db.session.commit()

        # Tạo file PDF thực tế
        test_folder = 'instance/storage/private_verifications'
        os.makedirs(test_folder, exist_ok=True)
        pdf_path = os.path.join(test_folder, f"audit_test_{user.id}.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(b"%PDF-1.4 test audit pdf")

        # Tạo file DOCX thực tế
        docx_path = os.path.join(test_folder, f"audit_test_{user.id}.docx")
        with open(docx_path, 'wb') as f:
            f.write(b"PK\x03\x04 test docx binary content")

        # 1. Test với file PDF
        pdf_doc = VerificationDocument(
            verification_id=user.verifications[0].id if user.verifications else 1,
            user_id=user.id,
            document_type='cv',
            original_filename='My_Resume.pdf',
            stored_filename=os.path.basename(pdf_path),
            storage_path=pdf_path,
            status='approved',
            is_active=True,
            file_extension='pdf',
            mime_type='application/pdf'
        )
        db.session.add(pdf_doc)
        user.profile.is_cv_public = True
        db.session.commit()

        # Gọi mode=view cho PDF -> phải là inline (Content-Disposition: inline)
        resp_pdf = self.client.get(f'/translator/{user.profile.id}/cv?mode=view')
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf.content_type, 'application/pdf')
        content_disp = resp_pdf.headers.get('Content-Disposition', '')
        self.assertIn('inline', content_disp)

        # 2. Test với file DOCX: mode=view phải tự động chuyển thành attachment
        pdf_doc.is_active = False
        pdf_doc.status = 'replaced'

        docx_doc = VerificationDocument(
            verification_id=user.verifications[0].id if user.verifications else 1,
            user_id=user.id,
            document_type='cv',
            original_filename='My_Resume.docx',
            stored_filename=os.path.basename(docx_path),
            storage_path=docx_path,
            status='approved',
            is_active=True,
            file_extension='docx',
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        db.session.add(docx_doc)
        db.session.commit()

        resp_docx = self.client.get(f'/translator/{user.profile.id}/cv?mode=view')
        self.assertEqual(resp_docx.status_code, 200)
        docx_disp = resp_docx.headers.get('Content-Disposition', '')
        self.assertIn('attachment', docx_disp)
        self.assertIn('My_Resume.docx', docx_disp)

        # Cleanup
        resp_pdf.close()
        resp_docx.close()
        db.session.delete(docx_doc)
        db.session.delete(pdf_doc)
        db.session.commit()
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass
        if os.path.exists(docx_path):
            try:
                os.remove(docx_path)
            except OSError:
                pass

    def test_04_privacy_guarantees(self):
        """Bảo vệ quyền riêng tư: khách vãng lai không thể xem CV khi is_cv_public=False"""
        user = User.query.filter_by(role='translator').first()
        self.assertIsNotNone(user)

        user.profile.is_cv_public = False
        db.session.commit()

        # Khách vãng lai (không đăng nhập) truy cập /translator/<id>/cv
        resp = self.client.get(f'/translator/{user.profile.id}/cv')
        # Phải redirect về trang hồ sơ kèm cảnh báo, không được trả file
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f'/translator/{user.profile.id}', resp.location)

    def test_05_legacy_fallback_resolution(self):
        """Kiểm tra legacy fallback khi chỉ có verification.cv_filename hoặc cv_url"""
        user = User.query.filter_by(role='translator').first()
        self.assertIsNotNone(user)

        user.profile.is_cv_public = True
        verif = user.latest_verification

        # Tạo file legacy trên disk
        test_folder = 'instance/storage/private_verifications'
        os.makedirs(test_folder, exist_ok=True)
        legacy_file = os.path.join(test_folder, f"legacy_cv_{user.id}.pdf")
        with open(legacy_file, 'wb') as f:
            f.write(b"%PDF-1.4 legacy cv content")

        old_filename = verif.cv_filename
        verif.cv_filename = os.path.basename(legacy_file)
        db.session.commit()

        # Khi không có VerificationDocument nào active
        VerificationDocument.query.filter_by(user_id=user.id, document_type='cv').update({'is_active': False})
        db.session.commit()

        resp = self.client.get(f'/translator/{user.profile.id}/cv')
        self.assertEqual(resp.status_code, 200)
        resp.close()

        # Revert
        VerificationDocument.query.filter_by(user_id=user.id, document_type='cv').update({'is_active': True})
        verif.cv_filename = old_filename
        db.session.commit()
        if os.path.exists(legacy_file):
            try:
                os.remove(legacy_file)
            except OSError:
                pass

if __name__ == '__main__':
    unittest.main()
