import os
import tempfile
import unittest
import time

# DB tạm: không đụng instance/database.db
_TMP = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TMP.close()
os.environ['DATABASE_URL'] = 'sqlite:///' + _TMP.name.replace(chr(92), '/')

from app import app, db
from models import User, Contract, PaymentTransaction
from services.transactions import display_status, list_hirer_transactions


class TransactionHistoryTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        u = str(time.time())
        self.h1 = User(name="H1", email=f"h1_{u}@t.com", password_hash="x", role="hirer")
        self.h2 = User(name="H2", email=f"h2_{u}@t.com", password_hash="x", role="hirer")
        self.tr = User(name="T", email=f"t_{u}@t.com", password_hash="x", role="translator")
        db.session.add_all([self.h1, self.h2, self.tr])
        db.session.flush()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _contract(self, hirer, status='escrow_pending'):
        c = Contract(hirer_id=hirer.id, translator_id=self.tr.id, agreed_price=100000, status=status)
        db.session.add(c)
        db.session.flush()
        return c

    def _pay(self, c, status, ref=None):
        p = PaymentTransaction(contract_id=c.id, user_id=c.hirer_id, amount=c.agreed_price,
                               status=status, transaction_ref=ref)
        db.session.add(p)
        db.session.flush()
        db.session.refresh(c)
        return p

    def test_status_mapping_from_backend_records(self):
        for pay, expected in [('pending', 'awaiting_payment'), ('escrow_pending', 'processing'),
                              ('completed', 'success'), ('failed', 'failed'), ('refunded', 'refunded')]:
            c = self._contract(self.h1)
            p = self._pay(c, pay)
            self.assertEqual(display_status(c, p), expected)

    def test_no_payment_record_is_never_success(self):
        self.assertEqual(display_status(self._contract(self.h1, 'escrow_pending'), None), 'awaiting_payment')
        # luồng thanh toán giả đã đưa hợp đồng sang in_progress/completed mà không có bản ghi
        self.assertEqual(display_status(self._contract(self.h1, 'in_progress'), None), 'unrecorded')
        self.assertEqual(display_status(self._contract(self.h1, 'completed'), None), 'unrecorded')
        self.assertEqual(display_status(self._contract(self.h1, 'cancelled'), None), 'cancelled')

    def test_list_only_own_contracts_and_filters(self):
        c1 = self._contract(self.h1)
        self._pay(c1, 'completed', ref='REF-ABC')
        self._contract(self.h1)
        self._contract(self.h2)
        rows, total, _, _ = list_hirer_transactions(self.h1.id)
        self.assertEqual(total, 2)
        rows, total, _, _ = list_hirer_transactions(self.h1.id, status='success')
        self.assertEqual(total, 1)
        rows, total, _, _ = list_hirer_transactions(self.h1.id, q='ref-abc')
        self.assertEqual(total, 1)
        rows, total, _, _ = list_hirer_transactions(self.h1.id, q='nope')
        self.assertEqual(total, 0)

    def test_pagination_clamps(self):
        for _ in range(12):
            self._contract(self.h1)
        rows, total, page, pages = list_hirer_transactions(self.h1.id, page=99)
        self.assertEqual((total, pages, page, len(rows)), (12, 2, 2, 2))

    def test_latest_payment_wins(self):
        c = self._contract(self.h1)
        self._pay(c, 'failed')
        self._pay(c, 'completed')
        self.assertEqual(list_hirer_transactions(self.h1.id)[0][0]['status'], 'success')

    def test_detail_access_control(self):
        c = self._contract(self.h1)
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as s:
            s['user_id'] = self.h2.id
        self.assertEqual(client.get(f'/account/history/{c.id}').status_code, 403)
        with client.session_transaction() as s:
            s['user_id'] = self.tr.id
        self.assertEqual(client.get(f'/account/history/{c.id}').status_code, 403)
        with client.session_transaction() as s:
            s['user_id'] = self.h1.id
        self.assertEqual(client.get(f'/account/history/{c.id}').status_code, 200)
        self.assertEqual(client.get('/account/history').status_code, 200)
        self.assertEqual(client.get('/account/history?status=success&q=x&page=abc').status_code, 200)


if __name__ == '__main__':
    unittest.main()
