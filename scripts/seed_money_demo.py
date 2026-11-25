"""Tạo dữ liệu thử cho luồng giữ tiền, hủy, hoàn tiền, tự giải ngân và khiếu nại.

Chạy (từ thư mục gốc dự án):
    python scripts/seed_money_demo.py

An toàn: chỉ chạy trên SQLite (file hoặc bộ nhớ), từ chối nếu DATABASE_URL trỏ tới Postgres/Supabase,
trừ khi thêm --allow-remote. Chạy lại nhiều lần được: tài khoản dùng lại, mỗi lần tạo thêm bộ hợp đồng mới.

Tài khoản thử (email @test.local) dùng chung một mật khẩu thử, đặt ở DEMO_PASSWORD bên dưới.
Đăng nhập admin tại /admin/login bằng tài khoản tài chính.
"""
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if '--allow-remote' not in sys.argv:
    url = os.environ.get('DATABASE_URL', 'sqlite:///instance/database.db')
    if not url.startswith('sqlite'):
        sys.exit('Từ chối: DATABASE_URL không phải SQLite. Dùng SQLite để thử, '
                 'hoặc thêm --allow-remote nếu bạn chắc chắn muốn ghi vào database này.')

from werkzeug.security import generate_password_hash  # noqa: E402
from app import app, db  # noqa: E402
from models import User, Job, Contract, TranslatorProfile, Deliverable  # noqa: E402
from services import payments, lifecycle  # noqa: E402

DEMO_PASSWORD = 'Demo@2026'
TAG = '[DEMO] '


def get_user(email, name, role, **extra):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=name, email=email, password_hash=generate_password_hash(DEMO_PASSWORD),
                    role=role, email_verified=True, is_demo=True, **extra)
        db.session.add(user)
        db.session.flush()
        if role == 'translator':
            db.session.add(TranslatorProfile(user_id=user.id, title='Phiên dịch thử', languages='Anh', rating=5))
    return user


def make_contract(hirer, trans, title, price, *, group='translation', unit='page', qty=12, status='in_progress',
                  funded=True, date=None, deadline=None, paid_ago=timedelta(hours=1)):
    """Tạo một hợp đồng đã chốt giá, có thể đã thanh toán (sàn đang giữ tiền)."""
    job = Job(hirer_id=hirer.id, title=TAG + title, description='Dữ liệu thử, không phải việc thật.',
              status='open', category_group=group, pricing_unit=unit, quantity=qty,
              deadline=deadline, event_date=date or '', event_time_start='09:00' if date else '',
              event_time_end='17:00' if date else '', event_location='Hà Nội' if date else '')
    db.session.add(job)
    db.session.flush()
    c = Contract(job_id=job.id, hirer_id=hirer.id, translator_id=trans.id, agreed_price=price, status=status,
                 scheduled_date=date, scheduled_time_start='09:00' if date else None,
                 scheduled_time_end='17:00' if date else None, location='Hà Nội' if date else '')
    db.session.add(c)
    db.session.flush()
    if status == 'escrow_pending' or not funded:
        payments.ensure_pricing_snapshot(c)
        return c
    payments.record_deposit(c, hirer.id, method='demo')
    lifecycle.mark_paid(c, now=datetime.utcnow() - paid_ago)
    c.paid_at = datetime.utcnow() - paid_ago
    return c


def add_delivery(c, hours_ago=1):
    db.session.add(Deliverable(contract_id=c.id, filename='ban_dich_demo.pdf', filepath='ban_dich_chuan.pdf'))
    lifecycle.register_delivery(c, now=datetime.utcnow() - timedelta(hours=hours_ago))


with app.app_context():
    hirer = get_user('khach.thu@test.local', 'Khách Thử', 'hirer')
    trans = get_user('pdv.thu@test.local', 'Phiên Dịch Viên Thử', 'translator')
    admin = get_user('tai.chinh@test.local', 'Admin Tài Chính Thử', 'admin', is_admin=True, admin_role='finance')
    admin.is_admin, admin.admin_role = True, 'finance'
    db.session.flush()

    today = datetime.utcnow().date()
    in_days = lambda n: (today + timedelta(days=n)).isoformat()
    made = []

    def add(label, c):
        made.append((c.id, label))

    add('Chờ khách thanh toán (vào trang thanh toán để thử nút giả hoặc QR)',
        make_contract(hirer, trans, 'Dịch hợp đồng 12 trang', 2_160_000, status='escrow_pending', funded=False))

    add('Tài liệu, mới thanh toán 1 giờ, CHƯA bắt đầu: khách hủy được hoàn 100% vào ví',
        make_contract(hirer, trans, 'Dịch tài liệu chưa bắt đầu', 2_160_000))

    c = make_contract(hirer, trans, 'Dịch tài liệu đang làm', 1_500_000, qty=8, paid_ago=timedelta(hours=3))
    c.started_at = datetime.utcnow() - timedelta(hours=2)
    add('Tài liệu, phiên dịch viên ĐÃ bắt đầu: khách hủy sẽ phải gửi khiếu nại', c)

    c = make_contract(hirer, trans, 'Dịch tài liệu đã nộp bài', 2_160_000, paid_ago=timedelta(days=1))
    add_delivery(c)
    add('Tài liệu đã nộp bài: thử Nghiệm thu, Yêu cầu sửa bài (tối đa 2 lần), Khiếu nại', c)

    c = make_contract(hirer, trans, 'Dịch tài liệu quá hạn nghiệm thu', 1_000_000, qty=5, paid_ago=timedelta(days=8))
    add_delivery(c, hours_ago=24 * 6)
    c.auto_release_at = datetime.utcnow() - timedelta(hours=2)
    add('Tài liệu QUÁ HẠN nghiệm thu: gọi cron sẽ tự giải ngân cho phiên dịch viên', c)

    c = make_contract(hirer, trans, 'Dịch tài liệu sắp hết hạn', 1_000_000, qty=5, paid_ago=timedelta(days=5))
    add_delivery(c, hours_ago=24 * 4 + 2)
    c.auto_release_at = datetime.utcnow() + timedelta(hours=12)
    add('Tài liệu còn 12 giờ nữa hết hạn: gọi cron sẽ gửi nhắc nghiệm thu', c)

    c = make_contract(hirer, trans, 'Dịch tài liệu trễ hạn', 1_200_000, qty=6, paid_ago=timedelta(days=6),
                      deadline=today - timedelta(days=3))
    c.started_at = datetime.utcnow() - timedelta(days=5)
    add('Tài liệu phiên dịch viên TRỄ HẠN quá 24 giờ: khách hủy hoàn 100% về phương thức gốc', c)

    add('Phiên dịch sự kiện 10 ngày nữa: hủy hoàn 100%',
        make_contract(hirer, trans, 'Phiên dịch hội thảo (10 ngày nữa)', 1_000_000, group='interpretation_other',
                      unit='hour', qty=4, date=in_days(10)))
    add('Phiên dịch sự kiện 4 ngày nữa: hủy hoàn 50%, phiên dịch viên giữ 50%',
        make_contract(hirer, trans, 'Phiên dịch họp đối tác (4 ngày nữa)', 1_000_000, group='interpretation_other',
                      unit='hour', qty=4, date=in_days(4)))
    add('Phiên dịch sự kiện ngày mai: hủy KHÔNG được hoàn tiền',
        make_contract(hirer, trans, 'Phiên dịch gặp mặt (ngày mai)', 1_000_000, group='interpretation_other',
                      unit='hour', qty=4, date=in_days(1)))
    add('Hội nghị 2 ngày, 10 ngày nữa: mức chặt hơn, hủy hoàn 50%',
        make_contract(hirer, trans, 'Hội nghị 2 ngày (10 ngày nữa)', 5_000_000, group='interpretation_other',
                      unit='day', qty=2, date=in_days(10)))

    db.session.commit()

    print('\nĐÃ TẠO DỮ LIỆU THỬ\n')
    print('Tài khoản (mật khẩu trong DEMO_PASSWORD ở đầu file scripts/seed_money_demo.py):')
    print('  Khách            khach.thu@test.local        đăng nhập tại /login')
    print('  Phiên dịch viên  pdv.thu@test.local          đăng nhập tại /login')
    print('  Admin tài chính  tai.chinh@test.local        đăng nhập tại /admin/login\n')
    print('Hợp đồng (mở /transaction/<mã> bằng tài khoản khách hoặc phiên dịch viên):')
    for cid, label in made:
        print(f'  #{cid:<4} {label}')
    print('\nCron thử:  $env:CRON_SECRET="s"  rồi mở  /api/cron/release-expired?secret=s')
