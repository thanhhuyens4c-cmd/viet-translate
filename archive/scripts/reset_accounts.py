#!/usr/bin/env python3
"""
reset_accounts.py — Xóa toàn bộ tài khoản khách thuê / phiên dịch viên và dữ liệu đi kèm
để làm lại quy trình đăng ký - đăng nhập từ đầu.

GIỮ LẠI: tài khoản admin (is_admin = true) và nhật ký kiểm toán admin (admin_audit_log).
XÓA:     mọi bảng còn lại (job, hợp đồng, tin nhắn, đánh giá, thông báo, thanh toán, hồ sơ xác minh...).

CÁCH DÙNG (chạy từ thư mục gốc dự án):
    python reset_accounts.py            # hỏi xác nhận, in ra database đang trỏ tới
    python reset_accounts.py --yes      # bỏ qua bước hỏi (dùng cho script)

Database nào bị xóa phụ thuộc biến môi trường DATABASE_URL (xem .env).
  - Không đặt DATABASE_URL  -> SQLite local (sao lưu tự động sang <file>.bak-<thời gian>)
  - DATABASE_URL = Supabase -> XÓA TRÊN WEB THẬT, KHÔNG sao lưu tự động.
"""
import os
import shutil
import sys
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KEEP_TABLES = {'admin_audit_log'}   # giữ nguyên
USER_TABLE = 'user'                 # chỉ xóa dòng không phải admin


def describe(url):
    p = urlparse(str(url))
    if p.scheme.startswith('sqlite'):
        return f'SQLite: {p.path or url}'
    return f'{p.scheme}://{p.hostname}:{p.port}{p.path}'


def main():
    from sqlalchemy import text
    from app import app
    from models import db

    with app.app_context():
        url = db.engine.url
        print('Database mục tiêu :', describe(url))
        is_sqlite = url.get_backend_name() == 'sqlite'

        if '--yes' not in sys.argv:
            if input('Gõ RESET để xóa toàn bộ tài khoản (trừ admin) và dữ liệu liên quan: ').strip() != 'RESET':
                print('Đã hủy, không có gì bị xóa.')
                return

        if is_sqlite and url.database and os.path.exists(url.database):
            backup = f"{url.database}.bak-{datetime.now():%Y%m%d-%H%M%S}"
            shutil.copy2(url.database, backup)
            print('Đã sao lưu        :', backup)

        with db.engine.begin() as conn:
            if is_sqlite:
                conn.execute(text('PRAGMA foreign_keys=OFF'))
            # Bảng con trước, bảng cha sau
            for table in reversed(db.metadata.sorted_tables):
                if table.name in KEEP_TABLES:
                    continue
                if table.name == USER_TABLE:
                    res = conn.execute(text('DELETE FROM "user" WHERE is_admin IS NULL OR is_admin = :f'),
                                       {'f': False})
                else:
                    res = conn.execute(table.delete())
                print(f'  {table.name:<28} đã xóa {res.rowcount} dòng')
            if is_sqlite:
                conn.execute(text('PRAGMA foreign_keys=ON'))

        left = db.session.execute(text('SELECT COUNT(*) FROM "user"')).scalar()
        print(f'Xong. Còn lại {left} tài khoản (admin).')
        print('Lưu ý: ảnh đại diện đã tải lên trong static/uploads/ (nếu có) cần xóa tay.')


if __name__ == '__main__':
    main()
