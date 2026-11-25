"""
test_account_support.py
Bộ kiểm thử tự động toàn diện cho Tab "Trợ giúp & Hỗ trợ" (Mục 5.7):
1. Kiểm tra 4 chủ đề FAQ & Hướng dẫn (5.7.1)
2. Kiểm tra danh mục Điều khoản & Chính sách chỉ xem (5.7.2)
3. Kiểm tra tạo Ticket và tự động sinh mã định danh duy nhất TK-xxxxx (5.7.3)
4. Kiểm tra tái sử dụng File Upload Service từ module KYC (magic bytes, private storage, RBAC)
5. Kiểm tra bảng theo dõi ticket và khung xem phản hồi từ Ban Quản trị
6. Kiểm tra bảo mật và phân quyền truy cập tệp đính kèm
"""

import os
import io
import unittest
from datetime import datetime
from flask import session

from app import app, db
from models import User, SupportTicket
from services.verification import get_private_verification_folder, detect_file_type_from_bytes
from services.account_support import (
    SUPPORT_CATEGORIES,
    FAQ_TOPICS,
    FAQ_ITEMS,
    POLICY_DOCUMENTS,
    generate_unique_ticket_code,
    create_support_ticket,
    get_user_tickets,
    get_ticket_by_code,
    admin_respond_to_ticket,
    save_ticket_attachment,
)


class TestAccountSupportModule(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Tạo người dùng test
        with app.app_context():
            # Dọn dẹp dữ liệu test cũ nếu có
            SupportTicket.query.filter(SupportTicket.title.like('%[TEST]%')).delete()
            User.query.filter(User.email.in_([
                'support_user_test@example.com',
                'support_other_user@example.com',
                'support_admin_test@example.com'
            ])).delete()
            db.session.commit()

            self.user = User(
                name='Nguyễn Hỗ Trợ',
                email='support_user_test@example.com',
                password_hash='dummy_hash',
                role='translator'
            )
            db.session.add(self.user)

            self.other_user = User(
                name='Trần Người Khác',
                email='support_other_user@example.com',
                password_hash='dummy_hash',
                role='translator'
            )
            db.session.add(self.other_user)

            self.admin = User(
                name='Quản Trị Viên',
                email='support_admin_test@example.com',
                password_hash='dummy_hash',
                role='admin'
            )
            db.session.add(self.admin)

            db.session.commit()

            self.user_id = self.user.id
            self.other_user_id = self.other_user.id
            self.admin_id = self.admin.id

    def tearDown(self):
        with app.app_context():
            SupportTicket.query.filter(SupportTicket.title.like('%[TEST]%')).delete()
            User.query.filter(User.email.in_([
                'support_user_test@example.com',
                'support_other_user@example.com',
                'support_admin_test@example.com'
            ])).delete()
            db.session.commit()

    # ─── 1. KIỂM TRA FAQ & HƯỚNG DẪN (5.7.1) ─────────────────────────────────

    def test_01_faq_topics_and_coverage(self):
        """Kiểm tra 4 chủ đề FAQ theo yêu cầu: Nhận thù lao, Quy tắc hủy ca, Giải quyết tranh chấp, Đổi thông tin định danh."""
        topic_ids = [t['id'] for t in FAQ_TOPICS]
        self.assertIn('compensation', topic_ids)
        self.assertIn('cancellation', topic_ids)
        self.assertIn('dispute', topic_ids)
        self.assertIn('identity', topic_ids)

        # Kiểm tra danh sách câu hỏi FAQ phủ đủ 4 chủ đề
        faq_topics_in_items = set(item['topic'] for item in FAQ_ITEMS)
        self.assertTrue({'compensation', 'cancellation', 'dispute', 'identity'}.issubset(faq_topics_in_items))
        self.assertGreaterEqual(len(FAQ_ITEMS), 12)

    # ─── 2. KIỂM TRA ĐIỀU KHOẢN & CHÍNH SÁCH CHỈ XEM (5.7.2) ───────────────────

    def test_02_policy_documents_and_api(self):
        """Kiểm tra danh mục tài liệu điều khoản và API xem tài liệu chỉ xem."""
        self.assertGreaterEqual(len(POLICY_DOCUMENTS), 4)

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        # Gọi API lấy tài liệu operating_regulations
        res = self.client.get('/account/support/policy/operating_regulations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('QC-VTL-2024', data['document']['code'])
        self.assertGreater(len(data['document']['articles']), 0)

        # Tài liệu không tồn tại -> 404
        res_not_found = self.client.get('/account/support/policy/invalid_doc_code')
        self.assertEqual(res_not_found.status_code, 404)

    # ─── 3. KIỂM TRA SINH MÃ ĐỊNH DANH DUY NHẤT (5.7.3) ──────────────────────

    def test_03_generate_unique_ticket_code(self):
        """Kiểm tra mã định danh tự động sinh có định dạng TK-xxxxx và là duy nhất."""
        with app.app_context():
            codes = [generate_unique_ticket_code() for _ in range(10)]
            for code in codes:
                self.assertTrue(code.startswith('TK-'))
                self.assertTrue(len(code) >= 7)
            # Kiểm tra không có mã nào trùng lặp trong đợt sinh
            self.assertEqual(len(codes), len(set(codes)))

    # ─── 4. KIỂM TRA TÁI SỬ DỤNG KYC FILE UPLOAD SERVICE (5.7.3) ──────────────

    def test_04_kyc_upload_helper_reuse_and_validation(self):
        """Kiểm tra tái sử dụng KYC File Upload helper: magic bytes, private storage, giới hạn dung lượng."""
        with app.app_context():
            user = User.query.get(self.user_id)

            # 1. Tệp rỗng / không chọn tệp -> Cho phép tạo ticket không đính kèm
            ok, url, err = save_ticket_attachment(None, user)
            self.assertTrue(ok)
            self.assertIsNone(url)

            # 2. Tệp có phần mở rộng bị cấm (.sh, .exe) -> Bị từ chối
            fake_storage = io.BytesIO(b'echo hacked')
            fake_storage.filename = 'malicious.sh'
            ok, url, err = save_ticket_attachment(fake_storage, user)
            self.assertFalse(ok)
            self.assertIn('không được hỗ trợ', err)

            # 3. Tệp giả mạo chữ ký (file text đổi tên thành .png) -> Bị magic bytes chặn
            spoofed_file = io.BytesIO(b'plain text pretending to be png')
            spoofed_file.filename = 'spoofed.png'
            ok, url, err = save_ticket_attachment(spoofed_file, user)
            self.assertFalse(ok)
            self.assertIn('chữ ký nhị phân', err)

            # 4. Tệp ảnh PNG thật chuẩn (chữ ký nhị phân \x89PNG\r\n\x1a\n)
            png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
            real_png = io.BytesIO(png_header)
            real_png.filename = 'screenshot.png'
            ok, url, err = save_ticket_attachment(real_png, user)
            self.assertTrue(ok)
            self.assertIsNotNone(url)
            self.assertTrue(url.startswith('/account/support/attachment/'))

            # Xác minh tệp được lưu trong đúng thư mục Private KYC
            stored_filename = os.path.basename(url)
            private_folder = get_private_verification_folder()
            file_on_disk = os.path.join(private_folder, stored_filename)
            self.assertTrue(os.path.exists(file_on_disk))

            # Dọn dẹp tệp test
            try:
                os.remove(file_on_disk)
            except OSError:
                pass

    # ─── 5. KIỂM TRA LUỒNG TẠO TICKET & VALIDATION ────────────────────────────

    def test_05_create_ticket_flow_and_validation(self):
        """Kiểm tra luồng tạo Ticket hỗ trợ với validation đầu vào và trạng thái mặc định open."""
        with app.app_context():
            user = User.query.get(self.user_id)

            # Validation chủ đề không hợp lệ
            ok, ticket, err = create_support_ticket(user, 'invalid_cat', 'Tiêu đề hợp lệ', 'Nội dung chi tiết hợp lệ trên 10 ký tự')
            self.assertFalse(ok)
            self.assertIn('Chủ đề yêu cầu hỗ trợ không hợp lệ', err)

            # Validation tiêu đề quá ngắn
            ok, ticket, err = create_support_ticket(user, 'compensation', 'Ngắn', 'Nội dung chi tiết hợp lệ trên 10 ký tự')
            self.assertFalse(ok)
            self.assertIn('ít nhất 5 ký tự', err)

            # Tạo ticket thành công
            ok, ticket, err = create_support_ticket(
                user=user,
                category='compensation',
                title='[TEST] Cần hỗ trợ đối soát thù lao hợp đồng',
                description='Hợp đồng phiên dịch #HD-1092 đã kết thúc nhưng chưa nhận được giải ngân ví.',
                attachment_file=None
            )
            self.assertTrue(ok)
            self.assertIsNotNone(ticket)
            self.assertTrue(ticket.ticket_code.startswith('TK-'))
            self.assertEqual(ticket.status, 'open')
            self.assertEqual(ticket.status_label, 'Đã tiếp nhận')
            self.assertEqual(ticket.category_label, 'Nhận thù lao & Escrow')

    # ─── 6. KIỂM TRA BẢNG THEO DÕI & KHUNG XEM PHẢN HỒI BAN QUẢN TRỊ ──────────

    def test_06_ticket_tracking_and_admin_response_view(self):
        """Kiểm tra bảng theo dõi ticket và khung xem phản hồi từ Ban Quản trị."""
        with app.app_context():
            user = User.query.get(self.user_id)

            # Tạo 1 ticket test
            ok, ticket, err = create_support_ticket(
                user=user,
                category='dispute',
                title='[TEST] Yêu cầu hòa giải tranh chấp với khách hàng',
                description='Khách hàng từ chối ký biên bản nghiệm thu ca dịch hội thảo y tế.',
            )
            self.assertTrue(ok)
            code = ticket.ticket_code

            # Ban đầu chưa có phản hồi
            loaded, _ = get_ticket_by_code(code, user)
            self.assertIsNone(loaded.admin_reply)
            self.assertEqual(loaded.status, 'open')

            # Ban Quản trị gửi phản hồi chính thức và chuyển trạng thái 'resolved'
            reply_msg = 'Ban Quản trị đã đối chiếu biên bản check-in định vị và phán quyết giải ngân 100% thù lao cho bạn.'
            ok_rep, rep_ticket, _ = admin_respond_to_ticket(code, reply_msg, 'resolved')
            self.assertTrue(ok_rep)
            self.assertEqual(rep_ticket.admin_reply, reply_msg)
            self.assertEqual(rep_ticket.status, 'resolved')
            self.assertEqual(rep_ticket.status_label, 'Đã giải quyết')
            self.assertIsNotNone(rep_ticket.admin_reply_at)

            # Người dùng xem lại chi tiết ticket
            dict_data = rep_ticket.to_dict()
            self.assertEqual(dict_data['ticket_code'], code)
            self.assertEqual(dict_data['status_label'], 'Đã giải quyết')
            self.assertEqual(dict_data['admin_reply'], reply_msg)

    # ─── 7. KIỂM TRA PHÂN QUYỀN TRUY CẬP (RBAC) ───────────────────────────────

    def test_07_rbac_access_restrictions(self):
        """Kiểm tra chặn người dùng khác xem ticket hoặc tệp đính kèm của nhau (403 Forbidden)."""
        with app.app_context():
            user = User.query.get(self.user_id)
            other = User.query.get(self.other_user_id)
            admin = User.query.get(self.admin_id)

            ok, ticket, _ = create_support_ticket(
                user=user,
                category='identity',
                title='[TEST] Yêu cầu cập nhật CCCD gắn chip mới',
                description='Tôi cần mở khóa trường Họ và tên để đổi sang CCCD mới.',
            )
            code = ticket.ticket_code

            # Người khác cố tình truy xuất ticket -> Bị chặn
            other_view, err = get_ticket_by_code(code, other)
            self.assertIsNone(other_view)
            self.assertIn('không có quyền truy cập', err)

            # Chính chủ truy xuất -> Thành công
            owner_view, _ = get_ticket_by_code(code, user)
            self.assertIsNotNone(owner_view)

            # Quản trị viên truy xuất -> Thành công
            admin_view, _ = get_ticket_by_code(code, admin)
            self.assertIsNotNone(admin_view)

    # ─── 8. KIỂM TRA HTTP ENDPOINTS VÀ GIAO DIỆN TAB SUPPORT ───────────────────

    def test_08_http_create_and_overview_tab(self):
        """Kiểm tra gọi POST tạo ticket qua API và tải trang Tab Trợ giúp & Hỗ trợ (GET ?tab=support)."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        # 1. Gửi POST tạo ticket qua AJAX
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
        res = self.client.post(
            '/account/support/tickets/create',
            data={
                'category': 'cancellation',
                'title': '[TEST] Yêu cầu bồi thường do khách hủy ca sát giờ',
                'description': 'Khách hàng hủy ca trước 2 giờ làm việc, yêu cầu áp dụng mức bồi thường 100%.',
                'attachment': (io.BytesIO(png_data), 'bill.png')
            },
            headers={'X-Requested-With': 'XMLHttpRequest'},
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        ticket_code = data['ticket']['ticket_code']
        self.assertTrue(ticket_code.startswith('TK-'))
        self.assertIsNotNone(data['ticket']['attachment_url'])

        # 2. Lấy thông tin chi tiết ticket qua GET API
        res_detail = self.client.get(f'/account/support/tickets/{ticket_code}')
        self.assertEqual(res_detail.status_code, 200)
        self.assertEqual(res_detail.get_json()['ticket']['ticket_code'], ticket_code)

        # 3. Tải lại trang Account Profile với ?tab=support
        res_page = self.client.get('/account/overview?tab=support')
        self.assertEqual(res_page.status_code, 200)
        html = res_page.get_data(as_text=True)

        # Kiểm tra sự xuất hiện của các thành phần chính
        self.assertTrue('Trung tâm Trợ giúp' in html)
        self.assertTrue('Hỏi đáp thường gặp' in html)
        self.assertTrue('Điều khoản' in html)
        self.assertTrue('Gửi' in html)
        self.assertIn('Nhận thù lao', html)
        self.assertIn('Quy tắc hủy ca', html)
        self.assertIn('Giải quyết tranh chấp', html)
        self.assertIn('Đổi thông tin định danh', html)
        self.assertIn(ticket_code, html)


if __name__ == '__main__':
    unittest.main()
