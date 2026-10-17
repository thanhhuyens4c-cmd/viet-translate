import unittest
import os
import io
from app import app
from models import db, User, TranslatorProfile, VerificationDocument, TranslatorVerification, Job, Proposal, Contract

class TestCvAndProfileSave(unittest.TestCase):
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

    def test_01_translator_update_title_and_cv_public(self):
        """Test translator updating title and is_cv_public via update_personal_profile"""
        with self.client.session_transaction() as sess:
            # Find or use a translator user
            t_user = User.query.filter_by(role='translator').first()
            if not t_user:
                self.skipTest("No translator user found in db")
            sess['user_id'] = t_user.id
            sess['_fresh'] = True
            user_id = t_user.id

        # Post update_personal_profile
        resp = self.client.post('/account/profile', data={
            'action': 'update_personal_profile',
            'email': t_user.email,
            'name': t_user.name,
            'phone': '0912345678',
            'title': 'Senior Japanese - Vietnamese Interpreter',
            'is_cv_public': '1',
            'has_cv_public_field': '1'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['title'], 'Senior Japanese - Vietnamese Interpreter')
        self.assertTrue(data['user']['is_cv_public'])

        # Verify in DB
        db.session.expire_all()
        reloaded_user = User.query.get(user_id)
        self.assertEqual(reloaded_user.profile.title, 'Senior Japanese - Vietnamese Interpreter')
        self.assertTrue(reloaded_user.profile.is_cv_public)

    def test_02_update_profile_title_action(self):
        """Test quick update of title via update_profile_title"""
        t_user = User.query.filter_by(role='translator').first()
        if not t_user:
            self.skipTest("No translator user found in db")

        with self.client.session_transaction() as sess:
            sess['user_id'] = t_user.id
            sess['_fresh'] = True

        resp = self.client.post('/account/profile', data={
            'action': 'update_profile_title',
            'title': 'Chuyên gia phiên dịch Hội thảo'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'Chuyên gia phiên dịch Hội thảo')

        db.session.expire_all()
        reloaded_user = User.query.get(t_user.id)
        self.assertEqual(reloaded_user.profile.title, 'Chuyên gia phiên dịch Hội thảo')

    def test_03_cv_access_resolution(self):
        """Test public CV and proposal-based hirer CV access"""
        t_user = User.query.filter_by(role='translator').first()
        h_user = User.query.filter_by(role='hirer').first()
        if not t_user or not h_user:
            self.skipTest("Translator or hirer not found")

        # Ensure translator has active profile and a mock CV document
        if not t_user.profile:
            t_user.profile = TranslatorProfile(user_id=t_user.id)
            db.session.add(t_user.profile)
            db.session.commit()

        # Find or create a CV document
        cv_doc = VerificationDocument.query.filter_by(
            user_id=t_user.id,
            document_type='cv',
            is_active=True
        ).first()

        if not cv_doc:
            # Create a mock verification request and document
            vr = TranslatorVerification.query.filter_by(user_id=t_user.id).first()
            if not vr:
                vr = TranslatorVerification(user_id=t_user.id, status='verified')
                db.session.add(vr)
                db.session.flush()

            # Create a dummy local file so resolver can find it
            test_folder = app.config.get('PRIVATE_VERIFICATION_FOLDER', 'instance/storage/private_verifications')
            os.makedirs(test_folder, exist_ok=True)
            test_filename = f"test_cv_{t_user.id}.pdf"
            test_filepath = os.path.join(test_folder, test_filename)
            with open(test_filepath, 'wb') as f:
                f.write(b"%PDF-1.4 test dummy CV file content")

            cv_doc = VerificationDocument(
                verification_id=vr.id,
                user_id=t_user.id,
                document_type='cv',
                stored_filename=test_filename,
                original_filename='My_CV.pdf',
                storage_path=test_filepath,
                storage_provider='local',
                mime_type='application/pdf',
                file_extension='pdf',
                file_size=1024,
                file_hash='test_hash_123',
                is_active=True
            )
            db.session.add(cv_doc)
            db.session.commit()

        # Test A: When CV is public, anyone can access /translator/<id>/cv
        t_user.profile.is_cv_public = True
        db.session.commit()

        resp = self.client.get(f'/translator/{t_user.profile.id}/cv')
        self.assertIn(resp.status_code, [200, 302]) # 200 or redirect to file/view

        # Test B: When CV is private, but Hirer has received proposal from translator
        t_user.profile.is_cv_public = False
        db.session.commit()

        # Hirer session
        with self.client.session_transaction() as sess:
            sess['user_id'] = h_user.id
            sess['_fresh'] = True

        # Check proposal link
        proposal = Proposal.query.filter_by(translator_id=t_user.id).first()
        if not proposal:
            job = Job.query.filter_by(hirer_id=h_user.id).first()
            if not job:
                job = Job(
                    hirer_id=h_user.id,
                    title='Test Conference Job',
                    source_language='vi',
                    target_language='en',
                    category='simultaneous',
                    status='open'
                )
                db.session.add(job)
                db.session.flush()
            proposal = Proposal(
                job_id=job.id,
                translator_id=t_user.id,
                price=5000000,
                status='submitted'
            )
            db.session.add(proposal)
            db.session.commit()

        # Now hirer tries to access /translator/<id>/cv
        resp = self.client.get(f'/translator/{t_user.profile.id}/cv')
        self.assertIn(resp.status_code, [200, 302])

        # Test C: Direct view of verification document by hirer
        resp_doc = self.client.get(f'/account/verification/documents/{cv_doc.id}/view')
        self.assertEqual(resp_doc.status_code, 200)

if __name__ == '__main__':
    unittest.main()
