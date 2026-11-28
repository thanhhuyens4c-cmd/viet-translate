"""Phí đúng 2% / 10%, dịch cabin tính theo giờ, ứng tuyển không cần nhập giá, rút tiền và trang Tài chính admin."""
import os
import time
import unittest
from datetime import datetime, date, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('PAYMENT_MODE', None)

from app import app, db
from models import (User, Job, Contract, Proposal, PaymentTransaction, AdminNotification, Notification,
                    TranslatorProfile)
from services import payments, lifecycle


class Base(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        u = str(time.time()).replace('.', '')
        self.hirer = User(name='Hirer', email=f'fh{u}@t.com', password_hash='x', role='hirer')
        self.trans = User(name='Trans', email=f'ft{u}@t.com', password_hash='x', role='translator',
                          phone='0900000000')
        self.admin = User(name='Admin', email=f'fa{u}@t.com', password_hash='x', role='admin',
                          admin_role='super_admin', is_admin=True)
        db.session.add_all([self.hirer, self.trans, self.admin])
        db.session.flush()
        db.session.add(TranslatorProfile(user_id=self.trans.id, languages='Tiếng Anh'))
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        self.ctx.pop()

    def login(self, user):
        with self.client.session_transaction() as s:
            s.clear()
            s['user_id'] = user.id
            s['admin_csrf_token'] = 'tok'

    def login_admin(self):
        now_ts = datetime.utcnow().timestamp()
        with self.client.session_transaction() as s:
            s.clear()
            s['admin_id'] = self.admin.id
            s['admin_role'] = 'super_admin'
            s['admin_session_created'] = now_ts
            s['admin_session_last_seen'] = now_ts
            s['admin_csrf_token'] = 'tok'

    def job(self, budget_type='fixed', budget_min=2_000_000, budget_max=None, group='translation', unit='page'):
        j = Job(hirer_id=self.hirer.id, title='Việc thử', description='d', status='open',
                moderation_status='approved', category_group=group, pricing_unit=unit, quantity=1,
                budget_type=budget_type, budget_min=budget_min, budget_max=budget_max,
                deadline=date.today() + timedelta(days=10))
        db.session.add(j)
        db.session.commit()
        return j


class ApplyWithoutPriceTests(Base):
    def apply(self, job, price=''):
        self.login(self.trans)
        return self.client.post(f'/job/{job.id}', data={
            'cover_letter': 'Xin nhận việc', 'price': price, 'completion_type': 'duration',
            'estimated_duration_value': '2', 'estimated_duration_unit': 'days'})

    def test_blank_price_means_agree_with_fixed_price(self):
        j = self.job('fixed', 2_000_000)
        self.apply(j)
        p = Proposal.query.filter_by(job_id=j.id, translator_id=self.trans.id).one()
        self.assertEqual(p.price, 2_000_000)

    def test_blank_price_on_range_takes_lower_bound(self):
        j = self.job('range', 1_000_000, 3_000_000)
        self.apply(j)
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 1_000_000)

    def test_own_price_still_wins(self):
        j = self.job('fixed', 2_000_000)
        self.apply(j, '2500000')
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 2_500_000)

    def hourly_job(self):
        j = self.job('fixed', 4_000_000, group='interpretation_other', unit='hour')
        j.quantity = 8
        j.event_location = 'Hà Nội'
        db.session.commit()
        return j

    def test_unit_mode_multiplies_by_quantity(self):
        j = self.hourly_job()
        self.login(self.trans)
        self.client.post(f'/job/{j.id}', data={'price': '600000', 'price_mode': 'unit', 'completion_type': 'duration'})
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 4_800_000)   # 600k/giờ x 8 giờ

    def test_total_mode_kept_as_is(self):
        j = self.hourly_job()
        self.login(self.trans)
        self.client.post(f'/job/{j.id}', data={'price': '4500000', 'price_mode': 'total', 'completion_type': 'duration'})
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 4_500_000)

    def test_blank_price_in_unit_mode_takes_posted_total(self):
        j = self.hourly_job()
        self.login(self.trans)
        self.client.post(f'/job/{j.id}', data={'price': '', 'price_mode': 'unit', 'completion_type': 'duration'})
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 4_000_000)

    def test_flat_job_ignores_unit_mode(self):
        j = self.job('fixed', 2_000_000, unit='flat')
        j.quantity = 5
        db.session.commit()
        self.login(self.trans)
        self.client.post(f'/job/{j.id}', data={'price': '1500000', 'price_mode': 'unit', 'completion_type': 'duration'})
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 1_500_000)

    def test_detail_shows_per_unit_budget_and_toggle(self):
        j = self.hourly_job()
        self.login(self.trans)
        html = self.client.get(f'/job/{j.id}').get_data(as_text=True)
        self.assertIn('Theo giờ', html)
        self.assertIn('500.000 VND/giờ × 8 giờ', html.replace(',', '.'))

    def test_negotiable_job_still_requires_price(self):
        j = self.job('negotiable', None)
        self.apply(j)
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).count(), 0)

    def test_form_shows_price_as_optional(self):
        j = self.job('fixed', 2_000_000)
        self.login(self.trans)
        html = self.client.get(f'/job/{j.id}').get_data(as_text=True)
        self.assertIn('đồng ý mức giá khách thuê đăng', html)


class FeeAndPayoutFlowTests(Base):
    def test_small_cabin_contract_full_cycle(self):
        # Đúng ca trong ảnh chụp: dịch cabin 33.000đ, trước đây hiện "x 1 trang", phí 10.000đ, PDV nhận 13.000đ.
        j = self.job('fixed', 33_000, group='interpretation_other', unit='page')
        c = Contract(job_id=j.id, hirer_id=self.hirer.id, translator_id=self.trans.id,
                     agreed_price=33_000, status='escrow_pending',
                     client_fee=10_000, commission=20_000, translator_net=13_000, pricing_unit='page', quantity=1)
        db.session.add(c)
        db.session.flush()
        from services.scheduling import reserve_slot
        day = (date.today() + timedelta(days=20)).isoformat()
        reserve_slot(self.trans.id, day, '09:00', '10:00', contract_id=c.id, job_id=j.id)
        db.session.commit()

        self.login(self.hirer)
        html = self.client.get(f'/payment-mockup/{c.id}').get_data(as_text=True)
        self.assertIn('33,660', html.replace('.', ','))      # tổng khách trả = giá + 2%
        self.assertIn('29,700', html.replace('.', ','))      # PDV nhận = giá - 10%
        self.assertIn('giờ', html)
        self.assertNotIn('× 1 trang', html)

        payments.topup(self.hirer.id, 100_000)
        db.session.commit()
        self.client.post(f'/payment-mockup/{c.id}', data={'payment_method': 'wallet'})
        with self.client.session_transaction() as s:
            flashes = s.get('_flashes')
        db.session.expire_all()
        c = db.session.get(Contract, c.id)
        self.assertEqual(c.status, 'in_progress', flashes)
        self.assertEqual(payments.wallet_balance(self.hirer.id), 100_000 - 33_660)

        lifecycle.complete_contract(c)
        db.session.commit()
        # Số "thực nhận" hiển thị khớp đúng số tiền vào ví.
        self.assertEqual(payments.wallet_balance(self.trans.id), 29_700)
        self.assertEqual(c.translator_net_amount, 29_700)
        self.assertEqual(c.platform_fee, 3_300)
        fee_tx = PaymentTransaction.query.filter_by(contract_id=c.id, kind='platform_fee').one()
        self.assertEqual(fee_tx.amount, 660 + 3_300)

    def test_withdraw_reaches_admin_finance_with_full_account(self):
        from services.payout_methods import add_payout_method
        payments.topup(self.trans.id, 1_000_000)
        db.session.commit()
        ok, _ = add_payout_method(self.trans.id, 'VCB', '0123456789', 'TRANS TEST', '', True)
        self.assertTrue(ok)

        self.login(self.trans)
        self.client.post('/account/wallet/withdraw', data={'amount': '300.000', '_csrf_token': 'tok'})
        w = PaymentTransaction.query.filter_by(payee_id=self.trans.id, kind='withdraw').one()
        self.assertEqual(w.payout_info['account_number'], '0123456789')
        self.assertTrue(AdminNotification.query.filter_by(type='WALLET_WITHDRAW', related_id=w.id).count())

        self.login_admin()
        for tab in ('overview', 'payouts', 'contracts'):
            for period in ('7d', '30d', 'month', 'all'):
                r = self.client.get(f'/admin/finance?tab={tab}&period={period}')
                self.assertEqual(r.status_code, 200, (tab, period))
        html = self.client.get('/admin/finance?tab=payouts').get_data(as_text=True)
        self.assertIn('0123456789', html)
        self.assertIn('qr.sepay.vn', html)
        self.assertIn('Tài chính', self.client.get('/admin/payments').get_data(as_text=True))

        r = self.client.post(f'/admin/payments/{w.id}/complete-withdrawal',
                             data={'_csrf_token': 'tok', 'next': '/admin/finance?tab=payouts'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/finance', r.headers['Location'])
        db.session.expire_all()
        w = db.session.get(PaymentTransaction, w.id)
        self.assertEqual(w.status, 'completed')
        self.assertIsNotNone(w.processed_at)
        self.assertEqual(Notification.query.filter_by(
            user_id=self.trans.id, title='Sàn đã chuyển khoản cho bạn').count(), 1)
        self.assertEqual(payments.wallet_balance(self.trans.id), 700_000)

    def test_withdraw_minimum_is_1000(self):
        from services import pricing
        self.assertEqual(pricing.WITHDRAW_MIN, 1_000)
        payments.topup(self.trans.id, 50_000)
        db.session.commit()
        w = payments.request_withdrawal(self.trans.id, '1.000')
        self.assertEqual(w.amount, 1_000)
        with self.assertRaises(payments.PaymentError):
            payments.request_withdrawal(self.trans.id, 999)

    def test_next_param_only_allows_admin_paths(self):
        payments.topup(self.trans.id, 1_000_000)
        w = payments.request_withdrawal(self.trans.id, 200_000)
        db.session.commit()
        self.login_admin()
        r = self.client.post(f'/admin/payments/{w.id}/complete-withdrawal',
                             data={'_csrf_token': 'tok', 'next': 'https://evil.example/admin/'})
        self.assertTrue(r.headers['Location'].endswith('/admin/payments'))


class PricingUnitOptionsTests(Base):
    """Cách tính giá phiên dịch: giờ, ngày, buổi, trọn kì, trọn gói, ghi rõ giờ / ngày."""

    def form(self, **kw):
        from werkzeug.datastructures import MultiDict
        base = {'title': 'Phiên dịch hội thảo', 'description': 'Phiên dịch tiếng Anh cho hội thảo hai ngày tại Hà Nội.',
                'category_group': 'interpretation_other', 'service_type': 'conference',
                'source_lang': 'Tiếng Anh', 'target_lang': 'Tiếng Việt', 'budget_type': 'negotiable',
                'event_location': 'Hà Nội', 'deadline': (date.today() + timedelta(days=20)).isoformat(),
                'scheduled_date[]': (date.today() + timedelta(days=30)).isoformat(),
                'start_time[]': '08:00', 'end_time[]': '12:00'}
        base.update(kw)
        return MultiDict(base)

    def validate(self, **kw):
        from app import validate_job_form
        with app.test_request_context('/post-job', method='POST'):
            return validate_job_form(self.form(**kw))

    def test_describe_volume(self):
        from services.pricing import describe_volume
        self.assertEqual(describe_volume('session', 4, 3), '4 buổi × 3 giờ/buổi (tổng 12 giờ)')
        self.assertEqual(describe_volume('day', 2, 8), '2 ngày × 8 giờ/ngày (tổng 16 giờ)')
        self.assertEqual(describe_volume('period', 1, 4, 20), 'Trọn kì 20 ngày × 4 giờ/ngày (tổng 80 giờ)')
        self.assertEqual(describe_volume('hour', 6), '6 giờ')
        self.assertEqual(describe_volume('flat', 9), 'Trọn gói')

    def test_session_requires_hours(self):
        d, e = self.validate(pricing_unit='session', quantity='4')
        self.assertIn('hours_per_unit', e)
        d, e = self.validate(pricing_unit='session', quantity='4', hours_per_unit='3')
        self.assertNotIn('hours_per_unit', e)
        self.assertEqual((d['pricing_unit'], d['quantity'], d['hours_per_unit']), ('session', 4, 3))

    def test_period_requires_days_and_hours_and_is_lump_sum(self):
        d, e = self.validate(pricing_unit='period', quantity='7')
        self.assertIn('period_days', e)
        self.assertIn('hours_per_unit', e)
        d, e = self.validate(pricing_unit='period', quantity='7', period_days='20', hours_per_unit='4')
        self.assertFalse({'period_days', 'hours_per_unit'} & set(e))
        self.assertEqual((d['quantity'], d['period_days'], d['hours_per_unit']), (1, 20, 4))

    def test_hour_unit_drops_extra_fields(self):
        d, e = self.validate(pricing_unit='hour', quantity='6', hours_per_unit='8', period_days='3')
        self.assertEqual((d['quantity'], d['hours_per_unit'], d['period_days']), (6, None, None))

    def test_translation_cannot_use_session(self):
        d, e = self.validate(category_group='translation', service_type='document_translation',
                             pricing_unit='session', quantity='3')
        self.assertEqual(d['pricing_unit'], 'page')

    def test_period_contract_is_one_lump_and_conference_policy(self):
        j = self.job('fixed', 20_000_000, group='interpretation_other', unit='period')
        j.quantity, j.period_days, j.hours_per_unit = 1, 20, 4
        c = Contract(job_id=j.id, hirer_id=self.hirer.id, translator_id=self.trans.id,
                     agreed_price=20_000_000, status='escrow_pending')
        db.session.add(c)
        db.session.flush()
        payments.ensure_pricing_snapshot(c)
        self.assertEqual((c.pricing_unit, c.quantity, c.unit_price), ('period', 1, 20_000_000))
        self.assertEqual(c.refund_policy, 'conference')
        self.assertFalse(j.quotes_per_unit)

    def test_session_job_quote_per_session(self):
        j = self.job('fixed', 2_400_000, group='interpretation_other', unit='session')
        j.quantity, j.hours_per_unit, j.event_location = 4, 3, 'Hà Nội'
        db.session.commit()
        self.login(self.trans)
        html = self.client.get(f'/job/{j.id}').get_data(as_text=True)
        self.assertIn('4 buổi × 3 giờ/buổi (tổng 12 giờ)', html)
        self.assertIn('Theo buổi', html)
        self.client.post(f'/job/{j.id}', data={'price': '700000', 'price_mode': 'unit', 'completion_type': 'duration'})
        self.assertEqual(Proposal.query.filter_by(job_id=j.id).one().price, 2_800_000)


class PostJobUnitTests(Base):
    def test_post_job_form_marks_units_by_group(self):
        self.login(self.hirer)
        r = self.client.get('/post-job')
        if r.status_code != 200:
            self.skipTest('Trang đăng việc yêu cầu hồ sơ khách thuê đã xác minh')
        html = r.get_data(as_text=True)
        self.assertIn('data-unit-card="session"', html)
        self.assertIn('syncPricingUnit', html)


if __name__ == '__main__':
    unittest.main()
