from app import app
from models import db, User, TranslatorProfile, EmailVerificationToken, TranslatorVerification, VerificationDocument
from services.verification import review_verification_request, submit_verification_for_review
from werkzeug.security import check_password_hash
import json

def run_tests():
    with app.app_context():
        print("--- STARTING END-TO-END TEST ---")
        
        # 1. Clear old test data
        old_user = User.query.filter_by(email='test_translator@example.com').first()
        if old_user:
            db.session.delete(old_user)
        old_admin = User.query.filter_by(email='test_admin@example.com').first()
        if old_admin:
            db.session.delete(old_admin)
        db.session.commit()

        # 2. Create Admin
        admin = User(name='Admin', email='test_admin@example.com', password_hash='hash', role='admin', is_admin=True, email_verified=True)
        db.session.add(admin)
        db.session.commit()

        # 3. Registration Simulation
        user = User(name='Test PDV', email='test_translator@example.com', password_hash='hash', role='translator', email_verified=False)
        db.session.add(user)
        db.session.flush()
        
        profile = TranslatorProfile(user_id=user.id)
        db.session.add(profile)
        
        import datetime
        token = EmailVerificationToken(user_id=user.id, token_hash='hash_abc', expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=1))
        db.session.add(token)
        db.session.commit()
        
        print("User created. Email Verified:", user.email_verified)
        assert user.email_verified == False
        
        # 4. Email Verification Simulation
        user.email_verified = True
        token.is_used = True
        db.session.commit()
        print("Email Verified Successfully.")
        assert user.email_verified == True

        # 5. Submit Verification
        # Create draft first
        draft = TranslatorVerification(user_id=user.id, current_step=5)
        db.session.add(draft)
        db.session.commit()
        
        form_data = {
            'full_name': 'Test PDV',
            'phone': '0123456789',
            'gender': 'male',
            'dob': '1990-01-01',
            'location': 'Hanoi',
            'bio': 'Toi la phien dich vien chuyen nghiep',
            'source_language': 'Vietnamese',
            'target_language': 'English',
            'interpreting_direction': 'two_way',
            'language_proficiency': 'native',
            'specializations': 'IT, Medical',
            'interpreting_types': 'simultaneous, consecutive',
            'education_level': 'bachelor',
            'university': 'HNU',
            'major': 'English',
            'certificate_type': 'IELTS',
            'certificate_name': 'IELTS 8.0',
            'cert_year': '2020',
            'current_position': 'Freelance Interpreter',
            'notable_clients': 'Google',
            'featured_projects': 'Project ABC which is very long and has more than 30 characters in total',
            'confirmed': 'true'
        }
        
        cv_doc = VerificationDocument(
            user_id=user.id,
            verification_id=draft.id,
            document_type='cv',
            original_filename='cv.pdf',
            stored_filename='cv.pdf',
            storage_path='/dummy/cv.pdf',
            file_size=100,
            mime_type='application/pdf',
            file_extension='pdf',
            is_active=True
        )
        db.session.add(cv_doc)
        draft.cv_url = '/static/cv.pdf'
        db.session.commit()
        ok, msg, meta = submit_verification_for_review(user, form_data=form_data, confirmed=True)
        print("Submit Verification:", ok, msg.encode('utf-8'))
        print("Errors:", [e.encode('utf-8') for e in meta.get('error_list', [])])
        assert ok == True

        verif = TranslatorVerification.query.filter_by(user_id=user.id).first()
        print("Verification Status after submit:", verif.status, "| Version:", verif.submission_version)
        assert verif.status == 'pending'
        
        # 6. Admin Review (Reject)
        ok, msg = review_verification_request(verif.id, admin, 'reject', reason='Missing ID card')
        print("Admin Reject:", ok, msg.encode('utf-8'))
        assert verif.status == 'rejected'
        assert user.profile.is_verified == False

        # 7. Resubmit
        ok, msg, meta = submit_verification_for_review(user, form_data=form_data, confirmed=True)
        print("Resubmit Verification:", ok, msg.encode('utf-8'))
        assert ok == True
        print("Verification Status after resubmit:", verif.status, "| Version:", verif.submission_version)
        assert verif.status == 'pending'
        assert verif.submission_version == 2

        # 8. Admin Review (Approve with Checklist)
        checklist = {'A1': True, 'A2': True, 'D1': True, 'D2': True}
        ok, msg = review_verification_request(verif.id, admin, 'approve', checklist_data=checklist)
        print("Admin Approve:", ok, msg.encode('utf-8'))
        assert verif.status == 'approved'
        assert user.profile.is_verified == True
        print("Checklist Data:", verif.checklist_data)
        assert json.loads(verif.checklist_data)['A1'] == True
        
        print("--- ALL TESTS PASSED ---")

if __name__ == '__main__':
    run_tests()
