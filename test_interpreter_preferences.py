"""
test_interpreter_preferences.py
Bộ kiểm thử toàn diện cho Tab "Tiêu chí nhận việc" (Job Preferences - Mục 5.4).

Kiểm tra:
1. Model InterpreterPreference và các helper methods (languages, specializations, work_mode, locations, min_rate, max_rate, allow_outside_rate, available_hours, to_dict).
2. Endpoint POST /account/preferences/save:
   - Lưu đầy đủ các trường thiết lập.
   - Trả về cảnh báo khi chọn cặp ngôn ngữ chưa khai báo biểu phí tại mục Năng lực.
3. RÀNG BUỘC NGHIỆP VỤ:
   - Cập nhật tiêu chí chỉ dùng để gợi ý job mới, tuyệt đối không tự động hủy hoặc thay đổi các lịch ca (TranslatorSchedule) hoặc hợp đồng (Contract) đã xác nhận trước đó.
4. Tải lại trang (GET /account/profile?tab=preferences) dữ liệu hiển thị chính xác sau khi lưu.
5. Tích hợp Smart Matching (translator_accepts_job, calculate_job_match_score).
"""

import unittest
import uuid
from datetime import datetime, date, time
from app import app, db, translator_accepts_job
from models import (
    User, InterpreterService, InterpreterPreference, 
    TranslatorSchedule, Contract, Job, Proposal
)
from services.matching import calculate_job_match_score


class TestInterpreterPreferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

        uid_str = uuid.uuid4().hex[:8]
        # Tạo translator user
        self.translator = User(
            name='Nguyễn Phiên Dịch Viên',
            email=f'test_trans_{uid_str}@example.com',
            password_hash='dummy_hash',
            role='translator',
            city='Hà Nội',
            is_active=True
        )
        # Tạo hirer user
        self.hirer = User(
            name='Công Ty Tuyển Dụng',
            email=f'test_hirer_{uid_str}@example.com',
            password_hash='dummy_hash',
            role='hirer',
            city='Hà Nội',
            is_active=True
        )
        db.session.add_all([self.translator, self.hirer])
        db.session.commit()

        # Tạo 1 dịch vụ đã khai báo ở Tab Năng lực (Tab 5.2): Tiếng Việt ➔ Tiếng Anh
        self.service1 = InterpreterService(
            user_id=self.translator.id,
            source_lang='Tiếng Việt',
            target_lang='Tiếng Anh',
            interpreting_type='Dịch nối tiếp (Consecutive)',
            specialization='Kinh doanh & Thương mại',
            hourly_rate=800000.0,
            session_rate=3000000.0,
            currency='VND',
            is_active=True
        )
        db.session.add(self.service1)
        db.session.commit()

    def tearDown(self):
        try:
            # Xóa các liên kết
            TranslatorSchedule.query.filter_by(translator_id=self.translator.id).delete()
            Contract.query.filter_by(translator_id=self.translator.id).delete()
            Job.query.filter_by(hirer_id=self.hirer.id).delete()
            InterpreterService.query.filter_by(user_id=self.translator.id).delete()
            InterpreterPreference.query.filter_by(user_id=self.translator.id).delete()
            db.session.delete(self.translator)
            db.session.delete(self.hirer)
            db.session.commit()
        except Exception:
            db.session.rollback()
        self.app_context.pop()

    def test_01_model_crud_and_helpers(self):
        """Kiểm tra tạo, đọc, sửa và các hàm helper của InterpreterPreference."""
        pref = InterpreterPreference(
            user_id=self.translator.id,
            work_mode='both',
            min_rate=500000.0,
            max_rate=3000000.0,
            allow_outside_rate=True
        )
        pref.set_languages_list(['Tiếng Việt ➔ Tiếng Anh', 'Tiếng Việt ➔ Tiếng Hàn'])
        pref.set_specializations_list(['Đàm phán thương mại', 'Khảo sát Nhà máy & Kỹ thuật'])
        pref.set_locations_list(['Hà Nội', 'Bắc Ninh'])
        pref.set_available_hours_list(['Ca sáng', 'Ca chiều'])

        db.session.add(pref)
        db.session.commit()

        loaded = InterpreterPreference.query.filter_by(user_id=self.translator.id).first()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.work_mode, 'both')
        self.assertEqual(loaded.min_rate, 500000.0)
        self.assertEqual(loaded.max_rate, 3000000.0)
        self.assertTrue(loaded.allow_outside_rate)
        self.assertIn('Tiếng Việt ➔ Tiếng Anh', loaded.get_languages_list())
        self.assertIn('Tiếng Việt ➔ Tiếng Hàn', loaded.get_languages_list())
        self.assertIn('Đàm phán thương mại', loaded.get_specializations_list())
        self.assertIn('Hà Nội', loaded.get_locations_list())
        self.assertIn('Ca sáng', loaded.get_available_hours_list())

        pref_dict = loaded.to_dict()
        self.assertEqual(pref_dict['user_id'], self.translator.id)
        self.assertEqual(len(pref_dict['languages']), 2)
        self.assertEqual(len(pref_dict['specializations']), 2)

    def test_02_endpoint_save_preferences_with_warning(self):
        """Kiểm tra lưu tiêu chí qua POST /account/preferences/save và cảnh báo ngôn ngữ thiếu biểu phí."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id
            sess['_fresh'] = True

        # Gửi lưu: Cặp 'Tiếng Việt ➔ Tiếng Anh' (ĐÃ CÓ ở Năng lực) và 'Tiếng Việt ➔ Tiếng Nhật' (CHƯA CÓ)
        payload = {
            'languages': ['Tiếng Việt ➔ Tiếng Anh', 'Tiếng Việt ➔ Tiếng Nhật'],
            'specializations': ['Đàm phán thương mại', 'Du lịch & Tháp tùng'],
            'mode_offline': True,
            'mode_online': True,
            'locations': ['Hà Nội', 'Đà Nẵng'],
            'min_rate': '1.000.000',
            'max_rate': '5.000.000',
            'allow_outside_rate': True,
            'available_hours': ['Ca sáng', 'Cuối tuần']
        }

        response = self.client.post('/account/preferences/save', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # Kiểm tra cảnh báo màu vàng cho cặp ngôn ngữ chưa khai báo biểu phí tại mục Năng lực
        self.assertIsNotNone(data.get('warning'))
        self.assertIn('chưa khai báo biểu phí', data['warning'])
        self.assertIn('Tiếng Việt ➔ Tiếng Nhật', data.get('missing_fee_pairs', []))

        # Kiểm tra dữ liệu trong DB
        pref = InterpreterPreference.query.filter_by(user_id=self.translator.id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.work_mode, 'both')
        self.assertEqual(pref.min_rate, 1000000.0)
        self.assertEqual(pref.max_rate, 5000000.0)
        self.assertTrue(pref.allow_outside_rate)
        self.assertIn('Tiếng Việt ➔ Tiếng Nhật', pref.get_languages_list())
        self.assertIn('Đà Nẵng', pref.get_locations_list())
        self.assertIn('Cuối tuần', pref.get_available_hours_list())

    def test_03_constraint_confirmed_schedules_not_cancelled(self):
        """
        RÀNG BUỘC NGHIỆP VỤ BẮT BUỘC:
        Cập nhật tiêu chí nhận việc không được tự động hủy các lịch ca đã xác nhận trước đó.
        """
        # Tạo hợp đồng và ca làm việc đã xác nhận
        job = Job(
            hirer_id=self.hirer.id,
            title='Phiên dịch hội thảo quốc tế đã chốt lịch',
            description='Chi tiết phiên dịch song song',
            category='interpretation',
            source_lang='Tiếng Việt',
            target_lang='Tiếng Anh',
            status='assigned'
        )
        db.session.add(job)
        db.session.commit()

        contract = Contract(
            job_id=job.id,
            hirer_id=self.hirer.id,
            translator_id=self.translator.id,
            agreed_price=2500000.0,
            status='active'
        )
        db.session.add(contract)
        db.session.commit()

        confirmed_shift = TranslatorSchedule(
            translator_id=self.translator.id,
            contract_id=contract.id,
            scheduled_date=date(2026, 11, 20),
            start_time=time(8, 0),
            end_time=time(12, 0),
            status='reserved'
        )
        db.session.add(confirmed_shift)
        db.session.commit()

        shift_id = confirmed_shift.id
        contract_id = contract.id

        # Thực hiện cập nhật tiêu chí nhận việc
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id
            sess['_fresh'] = True

        new_payload = {
            'languages': ['Tiếng Việt ➔ Tiếng Hàn'],  # Đổi hẳn sang tiếng Hàn
            'specializations': ['Y tế & Chăm sóc sức khỏe'],
            'mode_offline': False,
            'mode_online': True,  # Đổi sang chỉ Online
            'locations': [],
            'min_rate': '2.000.000',
            'max_rate': '8.000.000',
            'allow_outside_rate': False,
            'available_hours': ['Ca tối']  # Đổi ca
        }

        resp = self.client.post('/account/preferences/save', json=new_payload)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra rằng ca làm việc và hợp đồng đã xác nhận vẫn TỒN TẠI NGUYÊN VẸN, không bị hủy
        checked_shift = TranslatorSchedule.query.get(shift_id)
        self.assertIsNotNone(checked_shift, "Ca làm việc đã xác nhận không được bị xóa!")
        self.assertEqual(checked_shift.status, 'reserved', "Trạng thái ca làm việc không được bị đổi!")
        self.assertEqual(checked_shift.contract_id, contract_id)

        checked_contract = Contract.query.get(contract_id)
        self.assertIsNotNone(checked_contract, "Hợp đồng đã xác nhận không được bị xóa!")
        self.assertEqual(checked_contract.status, 'active')

    def test_04_get_account_profile_page_displays_preferences(self):
        """Kiểm tra tải lại trang (GET /account/profile?tab=preferences) hiển thị đúng dữ liệu đã lưu."""
        # Lưu trước tiêu chí
        pref = InterpreterPreference(
            user_id=self.translator.id,
            work_mode='offline',
            min_rate=750000.0,
            max_rate=3500000.0,
            allow_outside_rate=True
        )
        pref.set_languages_list(['Tiếng Việt ➔ Tiếng Anh', 'Tiếng Việt ➔ Tiếng Đức'])
        pref.set_specializations_list(['Hội thảo & Hội nghị'])
        pref.set_locations_list(['Hải Phòng', 'Quảng Ninh'])
        pref.set_available_hours_list(['Ca sáng', 'Ca chiều'])
        db.session.add(pref)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.translator.id
            sess['_fresh'] = True

        response = self.client.get('/account/profile?tab=preferences')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Kiểm tra sự xuất hiện của các trường và dữ liệu
        self.assertIn('Tiêu chí nhận việc & Smart Matching', html)
        self.assertIn('Tiếng Việt ➔ Tiếng Anh', html)
        self.assertIn('Tiếng Việt ➔ Tiếng Đức', html)
        self.assertIn('Hội thảo &amp; Hội nghị', html)
        self.assertIn('Hải Phòng', html)
        self.assertIn('Quảng Ninh', html)
        self.assertIn('750000', html)
        self.assertIn('3500000', html)
        self.assertIn('id="pref-allow-outside-rate"', html)

    def test_05_smart_matching_integration(self):
        """Kiểm tra tích hợp InterpreterPreference vào bộ lọc nhận việc translator_accepts_job."""
        pref = InterpreterPreference(
            user_id=self.translator.id,
            work_mode='online',
            min_rate=1000000.0,
            max_rate=5000000.0,
            allow_outside_rate=False
        )
        pref.set_languages_list(['Tiếng Việt ➔ Tiếng Anh'])
        db.session.add(pref)
        db.session.commit()

        # Job 1: Khớp Tiếng Việt -> Tiếng Anh, online, ngân sách 1.5tr -> Phải chấp nhận
        job1 = Job(
            hirer_id=self.hirer.id,
            title='Dịch họp trực tuyến',
            description='Họp trực tuyến qua zoom',
            category='interpretation',
            source_lang='Tiếng Việt',
            target_lang='Tiếng Anh',
            event_location='Online / Zoom',
            budget_min=1500000,
            budget_max=2000000,
            status='open'
        )
        self.assertTrue(translator_accepts_job(self.translator, job1))

        # Job 2: Khác ngôn ngữ (Tiếng Pháp) -> Không chấp nhận
        job2 = Job(
            hirer_id=self.hirer.id,
            title='Dịch tiếng Pháp',
            description='Phiên dịch tiếng Pháp',
            category='interpretation',
            source_lang='Tiếng Việt',
            target_lang='Tiếng Pháp',
            event_location='Online',
            budget_min=1500000,
            status='open'
        )
        self.assertFalse(translator_accepts_job(self.translator, job2))

        # Job 3: Trực tiếp onsite nhưng PDV chỉ nhận Online -> Không chấp nhận
        job3 = Job(
            hirer_id=self.hirer.id,
            title='Dịch tại văn phòng Hà Nội',
            description='Phiên dịch trực tiếp tại văn phòng',
            category='interpretation',
            source_lang='Tiếng Việt',
            target_lang='Tiếng Anh',
            event_location='Tòa nhà Landmark 72, Hà Nội',
            budget_min=1500000,
            status='open'
        )
        self.assertFalse(translator_accepts_job(self.translator, job3))


if __name__ == '__main__':
    unittest.main()
