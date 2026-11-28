import os
import unittest

# Dùng DB trong bộ nhớ để test không đụng file instance/database.db.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import app, db
from models import User, Job, Contract, PaymentTransaction
from services import pricing, payments


class PricingFormulaTests(unittest.TestCase):
    def test_quote_is_unit_price_times_quantity_plus_surcharge(self):
        self.assertEqual(pricing.compute_quote(150_000, 12, 360_000), 2_160_000)
        self.assertEqual(pricing.compute_quote(2_500_000, 2), 5_000_000)

    def test_bad_quantity_falls_back_to_one(self):
        self.assertEqual(pricing.normalize_quantity(None), 1)
        self.assertEqual(pricing.normalize_quantity('abc'), 1)
        self.assertEqual(pricing.normalize_quantity(0), 1)
        self.assertEqual(pricing.normalize_quantity('12'), 12)

    def test_default_unit_follows_category_group(self):
        self.assertEqual(pricing.normalize_unit(None, 'translation'), 'page')
        self.assertEqual(pricing.normalize_unit('', 'interpretation_other'), 'hour')
        self.assertEqual(pricing.normalize_unit('day'), 'day')
        self.assertEqual(pricing.normalize_unit('bogus', 'translation'), 'page')

    def test_document_example_from_terms(self):
        fees = pricing.compute_fees(2_160_000)
        self.assertEqual(fees['client_fee'], 43_200)
        self.assertEqual(fees['commission'], 216_000)
        self.assertEqual(fees['translator_net'], 1_944_000)
        self.assertEqual(fees['client_total'], 2_203_200)
        self.assertEqual(fees['platform_revenue'], 259_200)

    def test_conference_example_from_terms(self):
        fees = pricing.compute_fees(5_000_000)
        self.assertEqual(fees['client_fee'], 100_000)
        self.assertEqual(fees['commission'], 500_000)
        self.assertEqual(fees['platform_revenue'], 600_000)

    def test_no_minimums_fee_is_exact_percent(self):
        # Đơn nhỏ vẫn thu đúng 2% / 10%, không nâng lên mức tối thiểu.
        fees = pricing.compute_fees(23_000)
        self.assertEqual(fees['client_fee'], 460)
        self.assertEqual(fees['commission'], 2_300)
        self.assertEqual(fees['translator_net'], 20_700)
        fees = pricing.compute_fees(33_000)
        self.assertEqual(fees['client_fee'], 660)
        self.assertEqual(fees['client_total'], 33_660)
        self.assertEqual(fees['translator_net'], 29_700)

    def test_interpretation_never_priced_per_page(self):
        self.assertEqual(pricing.normalize_unit('page', 'interpretation_other'), 'hour')
        self.assertEqual(pricing.normalize_unit('hour', 'translation'), 'page')
        self.assertEqual(pricing.normalize_unit('day', 'interpretation_other'), 'day')

    def test_loyal_tier_applies_only_to_part_above_ten_million(self):
        # Đã có 9 triệu với cùng khách: 1 triệu đầu 10%, 2 triệu sau 5%.
        fees = pricing.compute_fees(3_000_000, prior_revenue=9_000_000)
        self.assertEqual(fees['commission'], 100_000 + 100_000)

    def test_fully_loyal_order(self):
        fees = pricing.compute_fees(4_000_000, prior_revenue=12_000_000)
        self.assertEqual(fees['commission'], 200_000)

    def test_money_adds_up(self):
        for price in (1, 99_999, 1_234_567, 25_000_000):
            for prior in (0, 8_000_000, 50_000_000):
                f = pricing.compute_fees(price, prior)
                self.assertEqual(f['translator_net'] + f['commission'], price)
                self.assertEqual(f['client_total'], price + f['client_fee'])
                self.assertEqual(f['client_total'], f['translator_net'] + f['platform_revenue'])


class PaymentFlowTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        import time
        u = str(time.time()).replace('.', '')
        self.hirer = User(name='Hirer', email=f'h{u}@t.com', password_hash='x', role='hirer')
        self.trans = User(name='Trans', email=f't{u}@t.com', password_hash='x', role='translator')
        db.session.add_all([self.hirer, self.trans])
        db.session.flush()

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        self.ctx.pop()

    def _contract(self, price, quantity=12, unit='page', group='translation'):
        job = Job(hirer_id=self.hirer.id, title='J', description='d', status='open',
                  category_group=group, pricing_unit=unit, quantity=quantity)
        db.session.add(job)
        db.session.flush()
        c = Contract(job_id=job.id, hirer_id=self.hirer.id, translator_id=self.trans.id,
                     agreed_price=price, status='escrow_pending')
        db.session.add(c)
        db.session.flush()
        return c

    def test_snapshot_comes_from_job_quantity(self):
        c = self._contract(2_160_000, quantity=12)
        payments.ensure_pricing_snapshot(c)
        self.assertEqual((c.pricing_unit, c.quantity, c.unit_price), ('page', 12, 180_000))
        self.assertEqual(c.client_fee, 43_200)
        self.assertEqual(c.commission, 216_000)
        self.assertEqual(payments.amount_to_pay(c), 2_203_200)

    def test_interpretation_job_uses_same_model(self):
        c = self._contract(5_000_000, quantity=2, unit='day', group='interpretation_other')
        payments.ensure_pricing_snapshot(c)
        self.assertEqual((c.pricing_unit, c.quantity, c.unit_price), ('day', 2, 2_500_000))
        self.assertEqual(c.commission, 500_000)

    def test_snapshot_is_frozen_once_paid(self):
        c = self._contract(1_000_000)
        payments.record_deposit(c, self.hirer.id)
        db.session.flush()
        before = (c.client_fee, c.commission)
        c.agreed_price = 9_000_000
        payments.ensure_pricing_snapshot(c)
        self.assertEqual((c.client_fee, c.commission), before)

    def test_unpaid_snapshot_follows_current_fee_table(self):
        # Hợp đồng chưa thanh toán mang phí cũ (tối thiểu 10.000 / 20.000) được tính lại đúng 2% / 10%.
        c = self._contract(33_000)
        c.client_fee, c.commission, c.translator_net = 10_000, 20_000, 13_000
        payments.ensure_pricing_snapshot(c)
        self.assertEqual((c.client_fee, c.commission, c.translator_net), (660, 3_300, 29_700))
        self.assertEqual(payments.amount_to_pay(c), 33_660)

    def test_unpaid_cabin_contract_priced_per_hour(self):
        c = self._contract(33_000, quantity=1, unit='page', group='interpretation_other')
        payments.ensure_pricing_snapshot(c)
        self.assertEqual(c.pricing_unit, 'hour')

    def test_deposit_then_release_balances_to_the_dong(self):
        c = self._contract(2_160_000)
        deposit = payments.record_deposit(c, self.hirer.id)
        db.session.flush()
        self.assertEqual((deposit.kind, deposit.status, deposit.amount), ('deposit', 'escrow_pending', 2_203_200))

        payments.release_funds(c)
        db.session.flush()
        rows = PaymentTransaction.query.filter_by(contract_id=c.id).all()
        by_kind = {r.kind: r for r in rows}
        self.assertEqual(deposit.status, 'completed')
        self.assertEqual(by_kind['release'].amount, 1_944_000)
        self.assertEqual(by_kind['release'].payee_id, self.trans.id)
        self.assertEqual(by_kind['platform_fee'].amount, 259_200)
        self.assertEqual(by_kind['release'].amount + by_kind['platform_fee'].amount, deposit.amount)

    def test_deposit_is_idempotent(self):
        c = self._contract(1_000_000)
        a = payments.record_deposit(c, self.hirer.id)
        db.session.flush()
        b = payments.record_deposit(c, self.hirer.id)
        self.assertIs(a, b)

    def test_cannot_release_twice(self):
        c = self._contract(1_000_000)
        payments.record_deposit(c, self.hirer.id)
        payments.release_funds(c)
        db.session.flush()
        with self.assertRaises(payments.PaymentError):
            payments.release_funds(c)

    def test_wallet_and_withdrawal(self):
        c = self._contract(2_160_000)
        payments.record_deposit(c, self.hirer.id)
        payments.release_funds(c)
        db.session.flush()
        self.assertEqual(payments.wallet_balance(self.trans.id), 1_944_000)

        with self.assertRaises(payments.PaymentError):
            payments.request_withdrawal(self.trans.id, 50_000)          # dưới mức tối thiểu
        with self.assertRaises(payments.PaymentError):
            payments.request_withdrawal(self.trans.id, 5_000_000)       # vượt số dư
        with self.assertRaises(payments.PaymentError):
            payments.request_withdrawal(self.trans.id, 'abc')

        w = payments.request_withdrawal(self.trans.id, 1_000_000)
        db.session.flush()
        self.assertEqual(w.status, 'pending')
        self.assertEqual(payments.wallet_balance(self.trans.id), 944_000)   # tiền chờ rút không dùng lại được

        payments.complete_withdrawal(w)
        self.assertEqual(w.status, 'completed')
        self.assertEqual(payments.wallet_balance(self.trans.id), 944_000)
        with self.assertRaises(payments.PaymentError):
            payments.complete_withdrawal(w)

    def test_document_job_without_time_needs_no_slot_but_interpreting_does(self):
        from services.booking import job_needs_time_slot, contract_has_no_time_slot
        doc = Job(hirer_id=self.hirer.id, title='D', description='d', category_group='translation')
        talk = Job(hirer_id=self.hirer.id, title='I', description='d', category_group='interpretation_other')
        self.assertFalse(job_needs_time_slot(doc, '', '', ''))
        self.assertTrue(job_needs_time_slot(doc, '2026-12-01', '09:00', '11:00'))   # đã ghi giờ thì vẫn giữ lịch
        self.assertTrue(job_needs_time_slot(talk, '', '', ''))                       # phiên dịch bắt buộc có lịch
        self.assertTrue(job_needs_time_slot(None, '', '', ''))                       # đặt gói dịch vụ bắt buộc có lịch

        c = self._contract(1_000_000)                                                # job dịch viết, chưa có lịch
        self.assertTrue(contract_has_no_time_slot(c))
        c2 = self._contract(1_000_000, quantity=2, unit='hour', group='interpretation_other')
        self.assertFalse(contract_has_no_time_slot(c2))

    def test_loyal_rate_uses_completed_history_with_same_client(self):
        first = self._contract(9_000_000)
        first.status = 'completed'
        db.session.flush()
        second = self._contract(3_000_000)
        payments.ensure_pricing_snapshot(second)
        self.assertEqual(second.commission, 200_000)


if __name__ == '__main__':
    unittest.main()
