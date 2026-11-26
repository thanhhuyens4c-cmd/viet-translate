"""Ví cá nhân: nạp ví, trả hợp đồng bằng ví, rút tiền và admin từ chối rút tiền.

Mọi số dư được tính từ sổ PaymentTransaction (services/payments.wallet_balance).
"""
import os
import time
import unittest
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('PAYMENT_MODE', None)

from app import app, db
from models import User, Job, Contract, PaymentTransaction, AdminNotification, Notification
from services import payments, lifecycle, bank_transfer, pricing


class WalletBase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        u = str(time.time()).replace('.', '')
        self.hirer = User(name='Hirer', email=f'wh{u}@t.com', password_hash='x', role='hirer')
        self.trans = User(name='Trans', email=f'wt{u}@t.com', password_hash='x', role='translator')
        db.session.add_all([self.hirer, self.trans])
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        self.ctx.pop()

    def pending_contract(self, price=1_000_000):
        """Hợp đồng dịch tài liệu chờ thanh toán (không có lịch giữ chỗ)."""
        job = Job(hirer_id=self.hirer.id, title='J', description='d', status='in_progress',
                  category_group='translation', pricing_unit='page', quantity=10)
        db.session.add(job)
        db.session.flush()
        c = Contract(job_id=job.id, hirer_id=self.hirer.id, translator_id=self.trans.id,
                     agreed_price=price, status='escrow_pending')
        db.session.add(c)
        db.session.commit()
        return c


class WalletServiceTests(WalletBase):
    def test_parse_amount(self):
        self.assertEqual(payments.parse_amount('1.500.000'), 1_500_000)
        self.assertEqual(payments.parse_amount('1,500,000'), 1_500_000)
        self.assertEqual(payments.parse_amount(250000), 250_000)
        for bad in ('', None, 'abc', '-5', '0'):
            with self.assertRaises(payments.PaymentError):
                payments.parse_amount(bad)

    def test_topup_without_contract_adds_to_balance(self):
        tx = payments.topup(self.hirer.id, 500_000)
        db.session.commit()
        self.assertIsNone(tx.contract_id)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 500_000)

    def test_topup_limits(self):
        with self.assertRaises(payments.PaymentError):
            payments.topup(self.hirer.id, payments.TOPUP_MIN - 1)
        with self.assertRaises(payments.PaymentError):
            payments.topup(self.hirer.id, payments.TOPUP_MAX + 1)

    def test_pay_from_wallet_requires_enough_balance(self):
        c = self.pending_contract()
        payments.topup(self.hirer.id, 100_000)
        with self.assertRaises(payments.PaymentError):
            payments.pay_from_wallet(c, self.hirer.id)

    def test_only_hirer_can_pay_from_wallet(self):
        c = self.pending_contract()
        payments.topup(self.trans.id, 5_000_000)
        with self.assertRaises(payments.PaymentError):
            payments.pay_from_wallet(c, self.trans.id)

    def test_wallet_payment_full_cycle_keeps_money_conserved(self):
        c = self.pending_contract(price=1_000_000)
        payments.topup(self.hirer.id, 2_000_000)
        due = payments.amount_to_pay(c)
        payments.pay_from_wallet(c, self.hirer.id)
        bank_transfer.fund_contract(c, self.hirer.id, 'wallet')
        db.session.commit()
        self.assertEqual(c.status, 'in_progress')
        self.assertEqual(payments.wallet_balance(self.hirer.id), 2_000_000 - due)
        deposit = PaymentTransaction.query.filter_by(contract_id=c.id, kind='deposit').one()
        self.assertEqual((deposit.amount, deposit.payment_method), (due, 'wallet'))

        payments.release_funds(c)
        db.session.commit()
        self.assertEqual(payments.wallet_balance(self.trans.id), c.translator_net)
        # Lần trả thứ hai cho cùng hợp đồng bị chặn.
        with self.assertRaises(payments.PaymentError):
            payments.pay_from_wallet(c, self.hirer.id)

    def test_refund_of_wallet_paid_contract_goes_back_to_wallet(self):
        c = self.pending_contract(price=1_000_000)
        payments.topup(self.hirer.id, 2_000_000)
        payments.pay_from_wallet(c, self.hirer.id)
        bank_transfer.fund_contract(c, self.hirer.id, 'wallet')
        db.session.flush()
        # Admin hoàn về "phương thức gốc": với khoản trả bằng ví thì phương thức gốc chính là ví.
        lifecycle.settle(c, 100, refund_fee=True, refund_to='original', waive_commission=True,
                         cancelled_by='admin', reason='test')
        db.session.commit()
        refund = PaymentTransaction.query.filter_by(contract_id=c.id, kind='refund').one()
        self.assertEqual((refund.payment_method, refund.status), ('wallet', 'completed'))
        self.assertEqual(payments.wallet_balance(self.hirer.id), 2_000_000)

    def test_withdraw_topup_only_balance_and_reject_returns_money(self):
        payments.topup(self.hirer.id, 1_000_000)
        w = payments.request_withdrawal(self.hirer.id, '400.000')
        db.session.commit()
        self.assertIsNone(w.contract_id)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 600_000)
        self.assertEqual(payments.pending_withdrawal_total(self.hirer.id), 400_000)

        payments.reject_withdrawal(w, 'Sai tên chủ tài khoản')
        db.session.commit()
        self.assertEqual((w.status, w.note), ('rejected', 'Sai tên chủ tài khoản'))
        self.assertEqual(payments.wallet_balance(self.hirer.id), 1_000_000)
        with self.assertRaises(payments.PaymentError):
            payments.reject_withdrawal(w)
        with self.assertRaises(payments.PaymentError):
            payments.complete_withdrawal(w)

    def test_cannot_withdraw_more_than_balance(self):
        payments.topup(self.trans.id, pricing.WITHDRAW_MIN)
        with self.assertRaises(payments.PaymentError):
            payments.request_withdrawal(self.trans.id, pricing.WITHDRAW_MIN + 1)


class TopupWebhookTests(WalletBase):
    def payload(self, ref, amount, content):
        return {'id': ref, 'transferType': 'in', 'transferAmount': amount, 'content': content}

    def test_topup_code_does_not_look_like_contract_code(self):
        code = bank_transfer.topup_code(self.hirer.id)
        self.assertEqual(bank_transfer.extract_topup_user_id(code), self.hirer.id)
        self.assertIsNone(bank_transfer.extract_contract_id(code))

    def test_webhook_credits_topup_once(self):
        code = bank_transfer.topup_code(self.hirer.id)
        outcome, _ = bank_transfer.process_webhook(self.payload('w1', 300_000, f'{code} chuyen tien'))
        db.session.commit()
        self.assertEqual(outcome, 'topped_up')
        self.assertEqual(payments.wallet_balance(self.hirer.id), 300_000)
        outcome, _ = bank_transfer.process_webhook(self.payload('w1', 300_000, code))
        self.assertEqual(outcome, 'duplicate')
        self.assertEqual(payments.wallet_balance(self.hirer.id), 300_000)

    def test_webhook_topup_out_of_limits_is_flagged_not_credited(self):
        code = bank_transfer.topup_code(self.hirer.id)
        outcome, _ = bank_transfer.process_webhook(self.payload('w2', 5_000, code))
        db.session.commit()
        self.assertEqual(outcome, 'mismatch')
        self.assertEqual(payments.wallet_balance(self.hirer.id), 0)
        self.assertEqual(PaymentTransaction.query.filter_by(transaction_ref='sepay:w2', kind='unmatched').count(), 1)

    def test_webhook_topup_for_unknown_user(self):
        outcome, _ = bank_transfer.process_webhook(self.payload('w3', 300_000, bank_transfer.topup_code(987654)))
        self.assertEqual(outcome, 'unknown_user')


class WalletRouteTests(WalletBase):
    def setUp(self):
        super().setUp()
        self.client = app.test_client()

    def login(self, user):
        with self.client.session_transaction() as s:
            s.clear()
            s['user_id'] = user.id
            s['admin_csrf_token'] = 'tok'

    def add_account(self, user, number='0123456789'):
        from services.payout_methods import add_payout_method
        ok, acc = add_payout_method(user.id, 'VCB', number, user.name.upper() + ' TEST', '', True)
        self.assertTrue(ok, acc)
        return acc if isinstance(acc, dict) else acc.to_dict()

    def test_wallet_page_renders_for_both_roles(self):
        for user in (self.hirer, self.trans):
            self.login(user)
            r = self.client.get('/account/wallet')
            self.assertEqual(r.status_code, 200)
            self.assertIn('Nạp tiền vào ví', r.get_data(as_text=True))

    def test_topup_route_sandbox(self):
        self.login(self.hirer)
        self.client.post('/account/wallet/topup', data={'amount': '1.200.000', '_csrf_token': 'tok'})
        self.assertEqual(payments.wallet_balance(self.hirer.id), 1_200_000)
        r = self.client.get('/account/wallet?kind=topup')
        self.assertIn('Nạp tiền vào ví', r.get_data(as_text=True))

    def test_topup_route_refused_in_live_mode(self):
        self.login(self.hirer)
        os.environ['PAYMENT_MODE'] = 'live'
        try:
            self.client.post('/account/wallet/topup', data={'amount': '1.200.000', '_csrf_token': 'tok'})
        finally:
            os.environ.pop('PAYMENT_MODE', None)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 0)

    def test_pay_contract_with_wallet_route(self):
        c = self.pending_contract()
        self.login(self.hirer)
        r = self.client.get(f'/payment-mockup/{c.id}')
        self.assertIn('Thanh toán bằng ví cá nhân', r.get_data(as_text=True))

        # Chưa đủ tiền: không ghim.
        self.client.post(f'/payment-mockup/{c.id}', data={'payment_method': 'wallet'})
        db.session.expire_all()
        self.assertEqual(Contract.query.get(c.id).status, 'escrow_pending')

        self.client.post('/account/wallet/topup', data={'amount': '5.000.000', '_csrf_token': 'tok'})
        r = self.client.post(f'/payment-mockup/{c.id}', data={'payment_method': 'wallet'})
        self.assertEqual(r.status_code, 302)
        db.session.expire_all()
        c = Contract.query.get(c.id)
        self.assertEqual(c.status, 'in_progress')
        due = payments.amount_to_pay(c)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 5_000_000 - due)

        # Bấm lại không trừ tiền lần nữa.
        self.client.post(f'/payment-mockup/{c.id}', data={'payment_method': 'wallet'})
        self.assertEqual(payments.wallet_balance(self.hirer.id), 5_000_000 - due)
        self.assertEqual(PaymentTransaction.query.filter_by(contract_id=c.id, kind='wallet_payment').count(), 1)

    def test_translator_cannot_pay_hirer_contract(self):
        c = self.pending_contract()
        self.login(self.trans)
        r = self.client.post(f'/payment-mockup/{c.id}', data={'payment_method': 'wallet'})
        self.assertEqual(r.status_code, 403)

    def test_withdraw_route_notifies_admin(self):
        payments.topup(self.trans.id, 1_000_000)
        db.session.commit()
        self.login(self.trans)
        self.add_account(self.trans)
        self.client.post('/account/wallet/withdraw', data={'amount': '200.000', '_csrf_token': 'tok'})
        self.assertEqual(payments.wallet_balance(self.trans.id), 800_000)
        self.assertEqual(AdminNotification.query.filter_by(type='WALLET_WITHDRAW').count() >= 1, True)

    def test_admin_reject_withdrawal_route(self):
        payments.topup(self.trans.id, 1_000_000)
        w = payments.request_withdrawal(self.trans.id, 300_000)
        admin = User(name='Admin', email=f'adm{time.time()}@t.com', password_hash='x', role='admin',
                     admin_role='super_admin', is_admin=True)
        db.session.add(admin)
        db.session.commit()
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as s:
            s['admin_id'] = admin.id
            s['admin_role'] = 'super_admin'
            s['admin_session_created'] = now_ts
            s['admin_session_last_seen'] = now_ts
            s['admin_csrf_token'] = 'tok'
        r = self.client.post(f'/admin/payments/{w.id}/reject-withdrawal',
                             data={'_csrf_token': 'tok', 'note': 'Sai STK'})
        self.assertEqual(r.status_code, 302)
        db.session.expire_all()
        w = PaymentTransaction.query.get(w.id)
        self.assertEqual((w.status, w.note), ('rejected', 'Sai STK'))
        self.assertEqual(payments.wallet_balance(self.trans.id), 1_000_000)
        self.assertEqual(Notification.query.filter_by(user_id=self.trans.id, title='Yêu cầu rút tiền bị từ chối').count(), 1)


class WalletMethodTests(WalletBase):
    """Phương thức nạp tiền, tài khoản nhận tiền rút và CSRF của các thao tác ví."""

    def setUp(self):
        super().setUp()
        self.client = app.test_client()

    login = WalletRouteTests.login
    add_account = WalletRouteTests.add_account

    def test_topup_records_chosen_method(self):
        self.login(self.hirer)
        self.client.post('/account/wallet/topup', data={'amount': '300.000', 'method': 'momo', '_csrf_token': 'tok'})
        tx = PaymentTransaction.query.filter_by(payee_id=self.hirer.id, kind='topup').one()
        self.assertEqual((tx.amount, tx.payment_method), (300_000, 'sandbox:momo'))
        self.assertEqual(payments.method_label(tx.payment_method), 'Ví MoMo (thử nghiệm)')

    def test_unavailable_method_is_refused(self):
        self.login(self.hirer)
        self.client.post('/account/wallet/topup', data={'amount': '300.000', 'method': 'card', '_csrf_token': 'tok'})
        self.assertEqual(payments.wallet_balance(self.hirer.id), 0)

    def test_unknown_method_falls_back_to_bank(self):
        self.assertEqual(payments.normalize_topup_method('xyz'), 'bank')

    def test_topup_without_csrf_is_refused(self):
        self.login(self.hirer)
        self.client.post('/account/wallet/topup', data={'amount': '300.000'})
        self.assertEqual(payments.wallet_balance(self.hirer.id), 0)

    def test_live_topup_goes_to_qr_step_without_crediting(self):
        self.login(self.hirer)
        os.environ.update(PAYMENT_MODE='live', BANK_CODE='MBBank', BANK_ACCOUNT='0001', SEPAY_API_KEY='k')
        try:
            r = self.client.post('/account/wallet/topup', data={'amount': '250.000', 'method': 'zalopay', '_csrf_token': 'tok'})
            self.assertIn('step=pay', r.headers['Location'])
            page = self.client.get(r.headers['Location']).get_data(as_text=True)
        finally:
            for k in ('PAYMENT_MODE', 'BANK_CODE', 'BANK_ACCOUNT', 'SEPAY_API_KEY'):
                os.environ.pop(k, None)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 0)
        self.assertIn(bank_transfer.topup_code(self.hirer.id), page)
        self.assertIn('amount=250000', page)

    def test_withdraw_requires_bank_account(self):
        payments.topup(self.trans.id, 1_000_000)
        db.session.commit()
        self.login(self.trans)
        self.client.post('/account/wallet/withdraw', data={'amount': '200.000', '_csrf_token': 'tok'})
        self.assertEqual(payments.wallet_balance(self.trans.id), 1_000_000)

    def test_withdraw_records_destination_account(self):
        payments.topup(self.hirer.id, 1_000_000)
        db.session.commit()
        self.login(self.hirer)
        acc = self.add_account(self.hirer, '9988776655')
        self.client.post('/account/wallet/withdraw',
                         data={'amount': '400.000', 'payout_method_id': acc['id'], '_csrf_token': 'tok'})
        w = PaymentTransaction.query.filter_by(payee_id=self.hirer.id, kind='withdraw').one()
        self.assertEqual(w.amount, 400_000)
        self.assertIn('Vietcombank', w.transaction_ref)
        self.assertNotIn('9988776655', w.transaction_ref)  # số tài khoản được che
        self.assertEqual(payments.wallet_summary(self.hirer.id)['pending_withdraw'], 400_000)

    def test_cannot_withdraw_to_someone_elses_account(self):
        payments.topup(self.hirer.id, 1_000_000)
        db.session.commit()
        other = self.add_account(self.trans, '1122334455')
        self.login(self.hirer)
        self.client.post('/account/wallet/withdraw',
                         data={'amount': '400.000', 'payout_method_id': other['id'], '_csrf_token': 'tok'})
        self.assertEqual(PaymentTransaction.query.filter_by(payee_id=self.hirer.id, kind='withdraw').count(), 0)

    def test_manage_accounts_route(self):
        self.login(self.hirer)
        self.client.post('/account/wallet/accounts', data={
            'action': 'add', 'bank_code': 'TCB', 'account_number': '1234567890',
            'account_holder_name': 'Hirer Test', 'set_as_default': '1', '_csrf_token': 'tok'})
        from services.payout_methods import get_payout_methods
        accounts = get_payout_methods(self.hirer.id)
        self.assertEqual(len(accounts), 1)
        self.client.post('/account/wallet/accounts', data={
            'action': 'delete', 'method_id': accounts[0]['id'], '_csrf_token': 'tok'})
        self.assertEqual(get_payout_methods(self.hirer.id), [])

    def test_wallet_summary(self):
        payments.topup(self.hirer.id, 2_000_000)
        payments.request_withdrawal(self.hirer.id, 500_000)
        db.session.commit()
        summary = payments.wallet_summary(self.hirer.id)
        self.assertEqual((summary['topped_up'], summary['pending_withdraw'], summary['withdrawn']),
                         (2_000_000, 500_000, 0))

    def test_wallet_page_shows_methods_and_accounts(self):
        self.login(self.trans)
        self.add_account(self.trans)
        html = self.client.get('/account/wallet').get_data(as_text=True)
        for text in ('Phương thức nạp tiền', 'Ví MoMo', 'Tài khoản nhận tiền', 'Vietcombank', 'Sắp có'):
            self.assertIn(text, html)


if __name__ == '__main__':
    unittest.main()
