"""Tạo MỘT công việc demo đã chốt hợp đồng, đang chờ khách thanh toán, để thử trả tiền thật qua QR.

Mặc định giá hợp đồng 10.000đ: phí dịch vụ 2% có mức tối thiểu 10.000đ nên khách chuyển 20.000đ.
Đây là cách thử rẻ nhất. Script dùng tài khoản CÓ SẴN, không tạo tài khoản mới.

Chạy trong thư mục dự án, đúng môi trường (.env) của web cần thử:

    python scripts/create_payment_test_job.py --hirer khach@example.com --translator pdv@example.com --yes

Tham số:
    --hirer       email khách (bắt buộc, phải là tài khoản vai trò hirer)
    --translator  email phiên dịch viên (bỏ trống thì lấy phiên dịch viên đầu tiên đang hoạt động)
    --price       giá hợp đồng, mặc định 10000
    --yes         bắt buộc nếu DATABASE_URL không phải SQLite (tức là database thật)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

parser = argparse.ArgumentParser()
parser.add_argument('--hirer', required=True)
parser.add_argument('--translator')
parser.add_argument('--price', type=int, default=10_000)
parser.add_argument('--yes', action='store_true')
args = parser.parse_args()

if args.price < 1000:
    sys.exit('Giá hợp đồng quá nhỏ (tối thiểu 1.000đ).')

url = os.environ.get('DATABASE_URL', '')
if url and not url.startswith('sqlite') and not args.yes:
    sys.exit('DATABASE_URL là database thật. Script chỉ tạo 1 việc demo, nếu đồng ý hãy thêm --yes.')

from app import app, db  # noqa: E402
from models import User, Job, Contract  # noqa: E402
from services import payments, bank_transfer  # noqa: E402

with app.app_context():
    hirer = User.query.filter_by(email=args.hirer.strip().lower(), role='hirer').first()
    if hirer is None:
        sys.exit(f'Không có khách (role hirer) với email {args.hirer}.')
    q = User.query.filter_by(role='translator', is_active=True)
    trans = q.filter_by(email=args.translator.strip().lower()).first() if args.translator else q.order_by(User.id).first()
    if trans is None:
        sys.exit('Không tìm thấy phiên dịch viên phù hợp.')

    job = Job(hirer_id=hirer.id, title='[DEMO THANH TOÁN] Dịch 1 trang để thử trả tiền',
              description='Việc demo chỉ để thử thanh toán. Không phải việc thật, có thể hủy hoặc xóa sau khi thử.',
              category='Dịch viết', category_group='translation', service_type='document_translation',
              source_lang='Tiếng Anh', target_lang='Tiếng Việt', budget_type='fixed',
              budget_min=args.price, budget_max=args.price, status='contracted', moderation_status='approved',
              pricing_unit='page', quantity=1)
    db.session.add(job)
    db.session.flush()
    contract = Contract(job_id=job.id, hirer_id=hirer.id, translator_id=trans.id,
                        agreed_price=args.price, status='escrow_pending')
    db.session.add(contract)
    db.session.flush()
    total = payments.amount_to_pay(contract)
    db.session.commit()

    print('\nĐÃ TẠO VIỆC DEMO')
    print(f'  Hợp đồng        #{contract.id}')
    print(f'  Khách           {hirer.email}')
    print(f'  Phiên dịch viên {trans.email}')
    print(f'  Giá hợp đồng    {args.price:,}đ')
    print(f'  Khách phải trả  {total:,}đ (đã gồm phí dịch vụ)')
    print(f'  Nội dung CK     {bank_transfer.transfer_code(contract.id)}')
    print(f'\nĐăng nhập bằng tài khoản khách rồi mở: /payment-mockup/{contract.id}')
    print('Chế độ:', bank_transfer.mode(), '| sẵn sàng nhận tiền thật:', bank_transfer.live_ready())
