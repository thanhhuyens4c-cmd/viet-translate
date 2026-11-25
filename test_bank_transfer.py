import os
import time
import unittest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import app, db
from models import User, Job, Contract, PaymentTransaction
from services import bank_transfer, payments

KEY = 'test-key-123'


class BankTransferTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        os.environ.update({'PAYMENT_MODE': 'live', 'SEPAY_API_KEY': KEY, 'BANK_CODE': 'MBBank',
                           'BANK_ACCOUNT': '0123456789', 'BANK_ACCOUNT_NAME': 'CONG TY TEST'})
        self.ctx = app.app_context()
        self.ctx.push()
        u = str(time.time()).replace('.', '')
        self.h = User(name='H', email=f'h{u}@t.com', password_hash='x', role='hirer')
        self.t = User(name='T', email=f't{u}@t.com', password_hash='x', role='translator')
        db.session.add_all([self.h, self.t])
        db.session.flush()
        job = Job(hirer_id=self.h.id, title='J', description='d', status='open', category_group='translation',
                  pricing_unit='page', quantity=12)
        db.session.add(job)
        db.session.flush()
        self.c = Contract(job_id=job.id, hirer_id=self.h.id, translator_id=self.t.id,
                          agreed_price=2_160_000, status='escrow_pending')
        db.session.add(self.c)
        db.session.commit()
        self.cid = self.c.id
        self.client = app.test_client()

    def tearDown(self):
        for k in ('PAYMENT_MODE', 'SEPAY_API_KEY', 'BANK_CODE', 'BANK_ACCOUNT', 'BANK_ACCOUNT_NAME'):
            os.environ.pop(k, None)
        db.session.rollback()
        db.session.remove()
        self.ctx.pop()

    def post(self, body, key=KEY):
        headers = {'Authorization': f'Apikey {key}'} if key else {}
        return self.client.post('/api/webhooks/sepay', json=body, headers=headers)

    def hook(self, ref, amount, content=None):
        return {'id': ref, 'transferType': 'in', 'transferAmount': amount,
                'content': content or f'MBVCB.123 VT{self.cid} chuyen tien', 'code': f'VT{self.cid}'}

    def contract(self):
        db.session.expire_all()
        return Contract.query.get(self.cid)

    def test_code_extraction(self):
        self.assertEqual(bank_transfer.extract_contract_id('abc vt42 xyz'), 42)
        self.assertEqual(bank_transfer.extract_contract_id('VT7'), 7)
        self.assertIsNone(bank_transfer.extract_contract_id('khong co ma'))

    def test_wrong_or_missing_key_is_rejected_and_nothing_changes(self):
        self.assertEqual(self.post(self.hook(1, 2_203_200), key='sai').status_code, 401)
        self.assertEqual(self.post(self.hook(1, 2_203_200), key=None).status_code, 401)
        self.assertEqual(self.contract().status, 'escrow_pending')

    def test_server_without_key_configured_rejects_everything(self):
        os.environ.pop('SEPAY_API_KEY')
        self.assertEqual(self.post(self.hook(1, 2_203_200), key='').status_code, 401)
        self.assertEqual(self.post(self.hook(1, 2_203_200), key='x').status_code, 401)

    def test_exact_payment_funds_the_contract(self):
        r = self.post(self.hook(1001, 2_203_200))
        self.assertEqual((r.status_code, r.get_json()['result']), (200, 'funded'))
        c = self.contract()
        self.assertEqual(c.status, 'in_progress')
        self.assertIsNotNone(c.paid_at)
        d = PaymentTransaction.query.filter_by(contract_id=self.cid, kind='deposit').one()
        self.assertEqual((d.amount, d.status, d.payment_method, d.transaction_ref),
                         (2_203_200, 'escrow_pending', 'bank_transfer', 'sepay:1001'))

    def test_replayed_webhook_is_idempotent(self):
        self.post(self.hook(1002, 2_203_200))
        r = self.post(self.hook(1002, 2_203_200))
        self.assertEqual(r.get_json()['result'], 'duplicate')
        self.assertEqual(PaymentTransaction.query.filter_by(contract_id=self.cid, kind='deposit').count(), 1)

    def test_wrong_amount_does_not_fund_but_is_recorded_for_admin(self):
        for ref, amount in ((2001, 2_160_000), (2002, 3_000_000)):   # thiếu phí 2% và thừa
            r = self.post(self.hook(ref, amount))
            self.assertEqual(r.get_json()['result'], 'mismatch')
        self.assertEqual(self.contract().status, 'escrow_pending')
        self.assertEqual(PaymentTransaction.query.filter_by(contract_id=self.cid, kind='deposit').count(), 0)
        self.assertEqual(PaymentTransaction.query.filter_by(contract_id=self.cid, kind='unmatched').count(), 2)
        # Khách chuyển bù đúng số tiền sau đó vẫn kích hoạt được.
        self.assertEqual(self.post(self.hook(3000, 2_203_200)).get_json()['result'], 'funded')

    def test_money_out_and_unrelated_transfers_are_ignored(self):
        out = self.hook(4000, 2_203_200); out['transferType'] = 'out'
        self.assertEqual(self.post(out).get_json()['result'], 'ignored')
        self.assertEqual(self.post({'id': 4001, 'transferType': 'in', 'transferAmount': 5, 'content': 'an trua'}).get_json()['result'], 'ignored')
        self.assertEqual(self.contract().status, 'escrow_pending')

    def test_payment_for_cancelled_contract_is_not_funded(self):
        c = self.contract(); c.status = 'cancelled'; db.session.commit()
        self.assertEqual(self.post(self.hook(5000, 2_203_200)).get_json()['result'], 'cannot_fund')
        self.assertEqual(self.contract().status, 'cancelled')

    def test_unknown_contract(self):
        r = self.post({'id': 6000, 'transferType': 'in', 'transferAmount': 100000, 'content': 'VT999999'})
        self.assertEqual(r.get_json()['result'], 'unknown_contract')

    def test_live_mode_blocks_the_fake_pay_button(self):
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
            s['admin_csrf_token'] = 'tok'
        r = self.client.post(f'/payment-mockup/{self.cid}', data={'_csrf_token': 'tok'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.contract().status, 'escrow_pending')
        self.assertEqual(PaymentTransaction.query.filter_by(contract_id=self.cid).count(), 0)

    def test_live_page_shows_qr_with_exact_amount_and_code(self):
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
        body = self.client.get(f'/payment-mockup/{self.cid}').get_data(as_text=True)
        self.assertIn('qr.sepay.vn/img', body)
        self.assertIn('amount=2203200', body)
        self.assertIn(f'des=VT{self.cid}', body)
        self.assertNotIn('4123 4567 8901 2345', body)

    def test_sandbox_shows_prefilled_qr_and_keeps_fake_button(self):
        os.environ['PAYMENT_MODE'] = 'sandbox'
        os.environ.pop('SEPAY_API_KEY')
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
        body = self.client.get(f'/payment-mockup/{self.cid}').get_data(as_text=True)
        self.assertIn('amount=2203200', body)
        self.assertIn(f'des=VT{self.cid}', body)
        self.assertIn('4123 4567 8901 2345', body)       # nút thanh toán giả vẫn có trong sandbox

    def test_no_bank_configured_shows_no_qr(self):
        os.environ['PAYMENT_MODE'] = 'sandbox'
        os.environ.pop('BANK_ACCOUNT')
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
        self.assertNotIn('qr.sepay.vn', self.client.get(f'/payment-mockup/{self.cid}').get_data(as_text=True))

    def test_live_without_key_refuses_to_show_qr(self):
        os.environ.pop('SEPAY_API_KEY')
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
        body = self.client.get(f'/payment-mockup/{self.cid}').get_data(as_text=True)
        self.assertNotIn('qr.sepay.vn', body)
        self.assertIn('chưa cấu hình', body)

    def test_sandbox_mode_still_works_for_hirer_only(self):
        os.environ['PAYMENT_MODE'] = 'sandbox'
        with self.client.session_transaction() as s:
            s['user_id'] = self.t.id
            s['admin_csrf_token'] = 'tok'
        self.client.post(f'/payment-mockup/{self.cid}', data={'_csrf_token': 'tok'})
        self.assertEqual(self.contract().status, 'escrow_pending')      # phiên dịch viên không tự "thanh toán" được
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
            s['admin_csrf_token'] = 'tok'
        self.client.post(f'/payment-mockup/{self.cid}', data={'_csrf_token': 'tok'})
        self.assertEqual(self.contract().status, 'in_progress')

    def test_payment_post_without_csrf_token_is_rejected(self):
        os.environ['PAYMENT_MODE'] = 'sandbox'
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
            s['admin_csrf_token'] = 'tok'
        self.client.post(f'/payment-mockup/{self.cid}')
        self.client.post(f'/payment-mockup/{self.cid}', data={'_csrf_token': 'sai'})
        self.assertEqual(self.contract().status, 'escrow_pending')

    def test_status_endpoint_flips_after_payment(self):
        with self.client.session_transaction() as s:
            s['user_id'] = self.h.id
        self.assertFalse(self.client.get(f'/payment/{self.cid}/status').get_json()['paid'])
        self.post(self.hook(7000, 2_203_200))
        self.assertTrue(self.client.get(f'/payment/{self.cid}/status').get_json()['paid'])


if __name__ == '__main__':
    unittest.main()
