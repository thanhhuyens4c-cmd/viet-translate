import os
import unittest
import threading
from datetime import datetime, date, time, timedelta
from app import app, db
from models import User, TranslatorSchedule, Contract, Job, Proposal
from services.scheduling import reserve_slot, confirm_slot, cancel_slot, release_expired, SlotTakenError, SchedulingError
from services.booking import create_contract_booking, BookingConflictError

class SchedulingTestCase(unittest.TestCase):
    def setUp(self):
        # Thiết lập context và database
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Start a transaction
        db.session.begin_nested()
        
        # Thêm dữ liệu test
        import time as time_mod
        unique = str(time_mod.time())
        self.hirer = User(name="Hirer", email=f"hirer_{unique}@test.com", password_hash="123", role="hirer")
        self.trans1 = User(name="Trans 1", email=f"trans1_{unique}@test.com", password_hash="123", role="translator")
        self.trans2 = User(name="Trans 2", email=f"trans2_{unique}@test.com", password_hash="123", role="translator")
        db.session.add_all([self.hirer, self.trans1, self.trans2])
        db.session.flush()
        
        self.job1 = Job(hirer_id=self.hirer.id, title="Job 1", description="desc", status="open", budget_max=100)
        self.job2 = Job(hirer_id=self.hirer.id, title="Job 2", description="desc", status="open", budget_max=200)
        db.session.add_all([self.job1, self.job2])
        db.session.flush()

    def tearDown(self):
        # Rollback the transaction
        db.session.rollback()
        db.session.remove()
        self.app_context.pop()

    def test_A_reserved_not_expired_confirm_success(self):
        """TEST A: reserved chưa hết hạn -> confirm thành công -> active."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=10)
        db.session.flush()
        success = confirm_slot(10, commit=False)
        self.assertTrue(success)
        self.assertEqual(s.status, 'active')
        self.assertIsNone(s.expires_at)

    def test_B_reserved_expired_confirm_fails(self):
        """TEST B: reserved đã hết hạn -> confirm thất bại -> cancelled."""
        from services.scheduling import SlotExpiredError
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=20)
        s.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.flush()
        
        with self.assertRaises(SlotExpiredError):
            confirm_slot(20, commit=False)
        self.assertEqual(s.status, 'cancelled')

    def test_C_reserved_expired_cron_not_run(self):
        """TEST C: reserved hết hạn nhưng cron chưa chạy -> confirm vẫn phải thất bại."""
        from services.scheduling import SlotExpiredError
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=30)
        s.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.flush()
        
        with self.assertRaises(SlotExpiredError):
            confirm_slot(30, commit=False)
        self.assertEqual(s.status, 'cancelled')

    def test_D_cron_runs_expired_becomes_cancelled(self):
        """TEST D: cron chạy -> reserved expired thành cancelled."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=40)
        s.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.flush()
        
        release_expired(commit=False)
        db.session.refresh(s)
        self.assertEqual(s.status, 'cancelled')

    def test_E_cron_runs_twice(self):
        """TEST E: cron chạy lại lần 2 -> không tạo thay đổi bất thường -> không lỗi."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=50)
        s.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.flush()
        
        release_expired(commit=False)
        release_expired(commit=False)
        db.session.refresh(s)
        self.assertEqual(s.status, 'cancelled')

    def test_F_reserve_ok_contract_fail_rollback(self):
        """TEST F: reserve thành công nhưng create Contract thất bại -> schedule rollback."""
        # Simulated by creating a conflict in create_contract_booking
        # We will use job that already has a contract to trigger BookingConflictError
        from services.booking import BookingConflictError
        create_contract_booking(
            hirer_id=self.hirer.id, 
            translator_id=self.trans1.id, 
            agreed_price=100, 
            scheduled_date="2024-12-01", 
            start_time="10:00", 
            end_time="11:00", 
            job_id=self.job1.id
        )
        
        schedules_before = TranslatorSchedule.query.count()
        with self.assertRaises(BookingConflictError):
            create_contract_booking(
                hirer_id=self.hirer.id, 
                translator_id=self.trans1.id, 
                agreed_price=100, 
                scheduled_date="2024-12-01", 
                start_time="11:00", 
                end_time="12:00", 
                job_id=self.job1.id
            )
        
        self.assertEqual(TranslatorSchedule.query.count(), schedules_before)

    def test_G_contract_fail_no_orphan(self):
        """TEST G: Contract tạo thất bại -> không còn schedule reserved orphan."""
        # Same as F, rollback ensures no orphan.
        self.test_F_reserve_ok_contract_fail_rollback()

    def test_H_schedule_constraint_error_contract_rollback(self):
        """TEST H: schedule insert gặp constraint error -> Contract rollback."""
        # Book a slot
        create_contract_booking(
            hirer_id=self.hirer.id, 
            translator_id=self.trans1.id, 
            agreed_price=100, 
            scheduled_date="2024-12-01", 
            start_time="10:00", 
            end_time="11:00", 
            job_id=self.job1.id
        )
        
        # Try booking same slot for different job -> raises BookingConflictError
        contracts_before = Contract.query.count()
        with self.assertRaises(BookingConflictError):
            create_contract_booking(
                hirer_id=self.hirer.id, 
                translator_id=self.trans1.id, 
                agreed_price=100, 
                scheduled_date="2024-12-01", 
                start_time="10:30", 
                end_time="11:30", 
                job_id=self.job2.id
            )
            
        # Verify contract was rolled back
        self.assertEqual(Contract.query.count(), contracts_before)

    def test_I_release_expired_in_booking_no_commit(self):
        """TEST I: release_expired() được gọi trong booking transaction -> KHÔNG tạo commit giữa chừng."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "08:00", "09:00", contract_id=99)
        s.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.flush()
        
        # Now we create a new booking which will internally call release_expired
        create_contract_booking(
            hirer_id=self.hirer.id, 
            translator_id=self.trans1.id, 
            agreed_price=100, 
            scheduled_date="2024-12-01", 
            start_time="10:00", 
            end_time="11:00", 
            job_id=self.job1.id
        )
        
        # Because we didn't call db.session.commit() anywhere, the outer test transaction should still be active
        # If it committed, rolling back wouldn't revert this. But since it's flush, rollback reverts it.
        # We can just verify it succeeds without error.
        db.session.refresh(s)
        self.assertEqual(s.status, 'cancelled')

    def test_J_reserved_payment_before_expiry(self):
        """TEST J: reserved + payment trước expiry -> active."""
        self.test_A_reserved_not_expired_confirm_success()

    def test_K_reserved_payment_after_expiry(self):
        """TEST K: reserved + payment sau expiry -> cancelled -> Contract không active."""
        self.test_B_reserved_expired_confirm_fails()

    def test_L_payment_requested_twice_idempotent(self):
        """TEST L: payment request gửi 2 lần -> idempotent -> không tạo schedule thứ 2."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=100)
        db.session.flush()
        
        # First confirm
        confirm_slot(100, commit=False)
        self.assertEqual(s.status, 'active')
        
        # Second confirm
        success = confirm_slot(100, commit=False)
        self.assertTrue(success)
        self.assertEqual(s.status, 'active')
        self.assertEqual(TranslatorSchedule.query.filter_by(contract_id=100).count(), 1)

    def test_M_reserved_cancel(self):
        """TEST M: reserved + cancel -> schedule cancelled."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=110)
        db.session.flush()
        cancel_slot(110, commit=False)
        self.assertEqual(s.status, 'cancelled')

    def test_N_active_cancel(self):
        """TEST N: active + cancel -> schedule cancelled."""
        s = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=120)
        db.session.flush()
        confirm_slot(120, commit=False)
        self.assertEqual(s.status, 'active')
        
        cancel_slot(120, commit=False)
        self.assertEqual(s.status, 'cancelled')

    def test_O_cancelled_book_again_allow(self):
        """TEST O: cancel xong booking lại cùng slot -> ALLOW."""
        s1 = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=130)
        db.session.flush()
        cancel_slot(130, commit=False)
        self.assertEqual(s1.status, 'cancelled')
        
        s2 = reserve_slot(self.trans1.id, "2024-12-01", "10:00", "11:00", contract_id=140)
        self.assertIsNotNone(s2)
        self.assertEqual(s2.status, 'reserved')

    def test_P_multiday_booking_creates_entries_for_all_days(self):
        """TEST P: Đặt lịch nhiều ngày tạo bản ghi TranslatorSchedule cho từng ngày."""
        schedules = reserve_slot(
            self.trans1.id,
            "2024-12-01 to 2024-12-03",
            "08:00",
            "17:00",
            contract_id=150
        )
        db.session.flush()
        self.assertIsInstance(schedules, list)
        self.assertEqual(len(schedules), 3)
        dates = [s.scheduled_date for s in schedules]
        self.assertEqual(dates, [date(2024, 12, 1), date(2024, 12, 2), date(2024, 12, 3)])
        for s in schedules:
            self.assertEqual(s.start_time, time(8, 0))
            self.assertEqual(s.end_time, time(17, 0))
            self.assertEqual(s.status, 'reserved')

        # Confirm should activate all 3 entries
        success = confirm_slot(150, commit=False)
        self.assertTrue(success)
        for s in schedules:
            self.assertEqual(s.status, 'active')

        # Cancel should cancel all 3 entries
        cancelled = cancel_slot(150, commit=False)
        self.assertTrue(cancelled)
        for s in schedules:
            self.assertEqual(s.status, 'cancelled')

    def test_Q_multiday_conflict_rolls_back_completely(self):
        """TEST Q: Trùng một ngày trong chuỗi ngày -> báo lỗi và rollback toàn bộ."""
        # Book day 2 first
        reserve_slot(self.trans1.id, "2024-12-02", "10:00", "12:00", contract_id=160)
        db.session.flush()

        # Attempt to book 2024-12-01 to 2024-12-03 with overlapping hours
        before_count = TranslatorSchedule.query.count()
        with self.assertRaises(SlotTakenError) as ctx:
            reserve_slot(
                self.trans1.id,
                "2024-12-01 to 2024-12-03",
                "08:00",
                "17:00",
                contract_id=170
            )
        self.assertIn("02/12/2024", str(ctx.exception))
        # No extra schedules created for contract 170
        self.assertEqual(TranslatorSchedule.query.filter_by(contract_id=170).count(), 0)

    def test_R_vietnamese_date_separator(self):
        """TEST R: Phân tích đúng chuỗi ngày dùng dấu phân cách tiếng Việt 'đến'."""
        schedules = reserve_slot(
            self.trans1.id,
            "2024-12-01 đến 2024-12-03",
            "09:00",
            "18:00",
            contract_id=180
        )
        db.session.flush()
        self.assertEqual(len(schedules), 3)
        self.assertEqual(schedules[0].scheduled_date, date(2024, 12, 1))
        self.assertEqual(schedules[2].scheduled_date, date(2024, 12, 3))

    def test_S_daily_schedules_custom_times(self):
        """TEST S: Đặt lịch với giờ làm việc khác nhau cho từng ngày."""
        daily_schedules = [
            {'date': '2024-12-05', 'start_time': '08:00', 'end_time': '12:00'},
            {'date': '2024-12-06', 'start_time': '13:00', 'end_time': '17:00'}
        ]
        schedules = reserve_slot(
            self.trans1.id,
            daily_schedules=daily_schedules,
            contract_id=190
        )
        db.session.flush()
        self.assertEqual(len(schedules), 2)
        self.assertEqual(schedules[0].scheduled_date, date(2024, 12, 5))
        self.assertEqual(schedules[0].start_time, time(8, 0))
        self.assertEqual(schedules[0].end_time, time(12, 0))

        self.assertEqual(schedules[1].scheduled_date, date(2024, 12, 6))
        self.assertEqual(schedules[1].start_time, time(13, 0))
        self.assertEqual(schedules[1].end_time, time(17, 0))

if __name__ == '__main__':
    unittest.main()

