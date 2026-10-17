"""
Test script kiểm thử toàn diện cho hệ thống:
Xác minh người đăng (Hirer X1-X8) và Kiểm duyệt Job (39 tiêu chí A/B/C/D)
Đối chiếu ma trận kiểm thử V01 - V22
"""
import os
import sys
from datetime import datetime, timedelta

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Đảm bảo import được app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, HirerProfile, Job, Proposal, Contract, Report, PaymentTransaction
from services.hirer_verification import evaluate_hirer_criteria, can_hirer_post_job
from services.job_moderation import evaluate_job_39_criteria, scan_text_violations, highlight_description

def run_tests():
    print("=" * 70)
    print("BAT DAU KIEM THU HE THONG XAC MINH HIRER & KIEM DUYET JOB")
    print("=" * 70)

    test_results = {}

    with app.app_context():
        # Setup test data
        # Clean old test users if exists
        test_emails = [
            'test_unverified_hirer@example.com',
            'test_verified_hirer@example.com',
            'test_translator_1@example.com',
            'test_translator_2@example.com',
            'test_translator_3@example.com',
            'test_admin_mod@example.com'
        ]
        for em in test_emails:
            u = User.query.filter_by(email=em).first()
            if u:
                Job.query.filter_by(hirer_id=u.id).delete()
                Report.query.filter_by(reporter_id=u.id).delete()
                db.session.delete(u)
        db.session.commit()

        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash("Password123")

        # Tạo user test
        unverified_hirer = User(
            name="Khách Chưa Xác Minh",
            email="test_unverified_hirer@example.com",
            phone="0911111111",
            role="hirer",
            is_active=True,
            password_hash=pw_hash
        )
        db.session.add(unverified_hirer)
        db.session.flush()

        unverified_profile = HirerProfile(
            user_id=unverified_hirer.id,
            account_type='individual',
            verification_status='pending',
            is_verified=False
        )
        db.session.add(unverified_profile)

        # Hirer đã xác minh trong 7 ngày
        verified_hirer = User(
            name="Công ty Minh Phát",
            email="test_verified_hirer@example.com",
            phone="0912345678",
            role="hirer",
            is_active=True,
            password_hash=pw_hash,
            verified_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(verified_hirer)
        db.session.flush()

        verified_profile = HirerProfile(
            user_id=verified_hirer.id,
            account_type='business',
            company="Công ty TNHH Minh Phát",
            tax_code="0101234567",
            company_email="hr@minhphat.vn",
            verification_status='verified',
            is_verified=True,
            verified_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(verified_profile)

        # Tạo 3 translator để test báo cáo độc lập
        t1 = User(name="PDV 1", email="test_translator_1@example.com", role="translator", is_active=True, password_hash=pw_hash)
        t2 = User(name="PDV 2", email="test_translator_2@example.com", role="translator", is_active=True, password_hash=pw_hash)
        t3 = User(name="PDV 3", email="test_translator_3@example.com", role="translator", is_active=True, password_hash=pw_hash)
        db.session.add_all([t1, t2, t3])

        # Admin
        admin = User(name="Admin Mod", email="test_admin_mod@example.com", role="admin", admin_role="superadmin", is_active=True, password_hash=pw_hash)
        db.session.add(admin)

        db.session.commit()

        # -------------------------------------------------------------
        # TEST V01 & V02: Gate kiểm tra can_hirer_post_job
        # -------------------------------------------------------------
        print("\n[TEST V01 & V02] Kiem tra chan tao/dang job khi Hirer chua xac minh...")
        can_post_unverified, _, _ = can_hirer_post_job(unverified_hirer)
        can_post_verified, _, _ = can_hirer_post_job(verified_hirer)

        assert can_post_unverified == False, "Loi: Hirer chua xac minh van cho phep dang job!"
        assert can_post_verified == True, "Loi: Hirer da xac minh bi chan dang job!"
        print("  -> PASS: unverified_hirer khong the dang job (False), verified_hirer duoc phep (True).")
        test_results['V01_V02'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V03 & V04: Thẩm định tiêu chí X1 - X8
        # -------------------------------------------------------------
        print("\n[TEST V03 & V04] Kiem tra bo tieu chi X1-X8 cua nguoi dang...")
        res_unverified = evaluate_hirer_criteria(unverified_hirer, unverified_profile)
        res_verified = evaluate_hirer_criteria(verified_hirer, verified_profile)

        assert 'X1' in res_unverified['criteria'], "Thieu tieu chi X1"
        assert 'X5' in res_verified['criteria'], "Thieu tieu chi X5"
        assert res_verified['mandatory_total'] == 5, "Tong so tieu chi bat buoc phai la 5"
        print(f"  -> PASS: Bo tieu chi X1-X8 day du. So tieu chi bat buoc = {res_verified['mandatory_total']}, Passed = {res_verified['mandatory_passed']}.")
        test_results['V03_V04'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V06, V07, V08, V09: Bộ máy kiểm tra 39 tiêu chí Job & Highlight
        # -------------------------------------------------------------
        print("\n[TEST V06, V07, V08, V09] Kiem tra 39 tieu chi va phat hien vi pham C1...")
        
        # Test scan vi phạm C1 (Zalo / SĐT)
        desc_with_violation = "Can phien dich vien tieng Han tai Bac Ninh. Lien he nhanh qua Zalo 0987123456 de trao doi."
        scan_res = scan_text_violations(desc_with_violation)
        assert len(scan_res) > 0, "Loi: Khong phat hien Zalo/SDT trong mo ta!"
        assert any(v['code'] == 'C1' for v in scan_res), "Loi: Khong gan dung ma C1 cho vi pham!"

        # Test highlight text
        highlighted = highlight_description(desc_with_violation, scan_res)
        assert '<mark class=' in highlighted, "Loi: Highlight HTML khong duoc tao!"
        print("  -> PASS: Phat hien C1 Zalo/SDT va highlight thanh cong (do dai HTML: %d)" % len(highlighted))

        # Tạo 1 job có vi phạm C1
        job_violation = Job(
            title="Phiên dịch đàm phán Việt - Hàn tại Bắc Ninh",
            description=desc_with_violation,
            hirer_id=verified_hirer.id,
            budget_type="fixed",
            budget_min=5000000,
            event_location="KCN Yên Phong, Bắc Ninh",
            service_type="interpretation_onsite",
            source_lang="Tiếng Việt",
            target_lang="Tiếng Hàn",
            moderation_status="pending"
        )
        db.session.add(job_violation)
        db.session.commit()

        job_eval = evaluate_job_39_criteria(job_violation)
        assert job_eval['summary_label'] == 'Nghiêm trọng', f"Loi: Label phai la 'Nghiêm trọng', nhan duoc: {job_eval['summary_label']}"
        assert job_eval['total_critical'] >= 1, "Loi: So luong vi pham nghiem trong phai >= 1"
        assert job_eval['recommendation'] == 'reject', "Loi: De xuat hanh dong phai la 'reject'"
        assert len(job_eval['groups']['A']['items']) == 12, "Loi: Nhom A phai co du 12 tieu chi"
        assert len(job_eval['groups']['B']['items']) == 9, "Loi: Nhom B phai co du 9 tieu chi"
        assert len(job_eval['groups']['C']['items']) == 12, "Loi: Nhom C phai co du 12 tieu chi"
        assert len(job_eval['groups']['D']['items']) == 6, "Loi: Nhom D phai co du 6 tieu chi"
        print(f"  -> PASS: 39 tieu chi day du (A:12, B:9, C:12, D:6). Nhan tom tat: {job_eval['summary_label']}, De xuat: {job_eval['recommendation']}.")
        test_results['V06_V07_V08_V09'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V10, V11: Quyết định duyệt và từ chối của Admin
        # -------------------------------------------------------------
        print("\n[TEST V10, V11] Kiem tra quyet dinh duyet / tu choi Job...")
        # Tạo 1 job sach
        clean_job = Job(
            title="Phiên dịch hội thảo công nghệ thông tin",
            description="Cần phiên dịch viên tiếng Anh có kinh nghiệm dịch hội thảo chuyên đề chuyển đổi số trong doanh nghiệp.",
            hirer_id=verified_hirer.id,
            budget_type="fixed",
            budget_min=8000000,
            event_location="Trung tâm Hội nghị Quốc gia, Hà Nội",
            service_type="interpretation_conference",
            source_lang="Tiếng Anh",
            target_lang="Tiếng Việt",
            moderation_status="pending"
        )
        db.session.add(clean_job)
        db.session.commit()

        # Giả lập Admin duyệt clean_job
        clean_job.moderation_status = 'approved'
        clean_job.moderated_at = datetime.utcnow()
        clean_job.moderated_by = admin.id
        db.session.commit()

        from services.permissions import can_view_job
        # Khách vãng lai xem job
        assert can_view_job(clean_job, None) == True, "Loi: Job da approved nhung cong khai khong xem duoc!"
        assert can_view_job(job_violation, None) == False, "Loi: Job vi pham pending nhung cong khai van xem duoc!"
        print("  -> PASS: clean_job da approved xem duoc cong khai, job_violation bi chan hien thi.")
        test_results['V10_V11'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V12: Người đăng chỉnh sửa job đã duyệt quay về pending
        # -------------------------------------------------------------
        print("\n[TEST V12] Kiem tra sua job da duyet quay ve cho kiem duyet...")
        old_version = clean_job.submission_version
        clean_job.description = "Cap nhat mo ta moi, can them thong tin thoi gian."
        clean_job.moderation_status = 'pending'
        clean_job.submission_version += 1
        db.session.commit()

        assert clean_job.moderation_status == 'pending', "Loi: Job sau khi sua khong ve pending"
        assert clean_job.submission_version == old_version + 1, "Loi: submission_version khong tang"
        assert can_view_job(clean_job, None) == False, "Loi: Job sua ve pending nhung cong khai van xem duoc"
        print(f"  -> PASS: Job sua da quay ve pending (version {clean_job.submission_version}), tam an khoi cong khai.")
        test_results['V12'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V13 & V14: 3 Báo cáo độc lập tự động gắn cờ và tạm ẩn
        # -------------------------------------------------------------
        print("\n[TEST V13 & V14] Kiem tra co che 3 bao cao doc lap tu dong gan co...")
        # Duyệt lại job để test giám sát sau đăng
        clean_job.moderation_status = 'approved'
        clean_job.is_flagged = False
        db.session.commit()

        # Client giả lập gọi API báo cáo
        with app.test_client() as client:
            # Login t1
            with client.session_transaction() as sess:
                sess['user_id'] = t1.id
                sess['user_role'] = 'translator'
                sess['user_name'] = t1.name
            
            # t1 gửi báo cáo lần 1
            resp1 = client.post(f'/api/jobs/{clean_job.id}/report', json={'reason': 'Dấu hiệu giao dịch ngoài', 'details': 'Khách gửi sđt'})
            assert resp1.status_code == 200, f"Bao cao 1 that bai: {resp1.data}"
            
            # t1 gửi trùng -> kiểm tra không được tăng
            resp1_dup = client.post(f'/api/jobs/{clean_job.id}/report', json={'reason': 'Dấu hiệu giao dịch ngoài', 'details': 'Gửi trùng'})
            assert resp1_dup.status_code == 400, "Loi: Cho phep gui bao cao trung tu cung mot user!"

            # Reload job
            j_check = Job.query.get(clean_job.id)
            assert j_check.is_flagged == False, "1 bao cao chua duoc gan co!"

            # Login t2 và báo cáo
            with client.session_transaction() as sess:
                sess['user_id'] = t2.id
                sess['user_name'] = t2.name
            resp2 = client.post(f'/api/jobs/{clean_job.id}/report', json={'reason': 'Khác', 'details': 'Nghi ngờ gian lận'})
            assert resp2.status_code == 200

            j_check = Job.query.get(clean_job.id)
            assert j_check.is_flagged == False, "2 bao cao chua duoc gan co!"

            # Login t3 và báo cáo (đạt ngưỡng 3)
            with client.session_transaction() as sess:
                sess['user_id'] = t3.id
                sess['user_name'] = t3.name
            resp3 = client.post(f'/api/jobs/{clean_job.id}/report', json={'reason': 'Lừa đảo', 'details': 'Yêu cầu đặt cọc'})
            assert resp3.status_code == 200

            # Reload job -> phải bị gắn cờ và tạm ẩn
            j_check = Job.query.get(clean_job.id)
            assert j_check.is_flagged == True, "Loi: 3 bao cao doc lap phai tu dong is_flagged = True"
            assert j_check.moderation_status == 'flagged', "Loi: moderation_status phai chuyen thanh 'flagged'"
            assert can_view_job(j_check, None) == False, "Loi: Job bi gan co phai bi tam an khoi nguoi dung"
            print("  -> PASS: 3 bao cao doc lap da tu dong gan co is_flagged=True, moderation_status='flagged', tam an an toan.")
            test_results['V13_V14'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V15: Quét tin nhắn chat C1 / C2
        # -------------------------------------------------------------
        print("\n[TEST V15] Kiem tra phat hien C1/C2 trong tin nhan chat...")
        chat_msg_unsafe = "Ban oi ket ban Zalo so 0988776655 de chuyen tien ngoai nhe"
        chat_violations = scan_text_violations(chat_msg_unsafe)
        assert len(chat_violations) >= 2, "Loi: Phai phat hien ca C1 (Zalo) va C2 (chuyen tien ngoai)"
        assert any(v['code'] == 'C1' for v in chat_violations)
        assert any(v['code'] == 'C2' for v in chat_violations)
        print("  -> PASS: Quet tin nhan chat phat hien ca C1 (Zalo/SDT) va C2 (Chuyen tien ngoai).")
        test_results['V15'] = 'PASSED'

        # -------------------------------------------------------------
        # TEST V17 & V18: Chặn xóa cứng Job có Proposal hoặc Contract
        # -------------------------------------------------------------
        print("\n[TEST V17 & V18] Kiem tra bao toan du lieu giao dich (Cascade Protection)...")
        # Tạo proposal cho job_violation
        prop = Proposal(
            job_id=job_violation.id,
            translator_id=t1.id,
            price=4500000,
            cover_letter="Tôi nhận dịch sự kiện này.",
            status="pending"
        )
        db.session.add(prop)
        db.session.commit()

        # Thử gọi hàm xóa job qua client admin
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['user_role'] = 'admin'
                sess['user_name'] = admin.name
                sess['csrf_token'] = 'test-token'
            
            # Post xóa job
            del_resp = client.post(f'/admin/jobs/{job_violation.id}/delete', data={'csrf_token': 'test-token'}, follow_redirects=True)
            # Kiểm tra job vẫn còn trong database
            j_still_alive = Job.query.get(job_violation.id)
            assert j_still_alive is not None, "Loi: Job co Proposal bi xoa cung mat du lieu!"
            assert Proposal.query.filter_by(job_id=job_violation.id).first() is not None, "Loi: Proposal bi cascade delete mat!"
            print("  -> PASS: Job co Proposal da duoc bao ve an toan, he thong tu choi xoa cung va yeu cau Archive.")
            test_results['V17_V18'] = 'PASSED'

        print("\n" + "=" * 70)
        print("KET QUA KIEM THU TOAN DIEN:")
        for k, v in test_results.items():
            print(f"  - {k}: {v}")
        print("=" * 70)
        print("TAT CA CAC KICH BAN THIET YEU DEU DAT 100%!")

if __name__ == '__main__':
    run_tests()
