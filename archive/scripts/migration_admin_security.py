"""
migration_admin_security.py — Tạo bảng login_attempt và admin_audit_log.

CÁCH DÙNG:
    python migration_admin_security.py

Script an toàn — chỉ tạo bảng mới nếu chưa tồn tại (CREATE TABLE IF NOT EXISTS).
Không xóa hay sửa bảng hiện có.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    print('[MIGRATION] Admin Security — tạo bảng login_attempt và admin_audit_log')

    try:
        from app import app
        from models import db, LoginAttempt, AdminAuditLog
    except ImportError as e:
        print(f'[ERROR] Import thất bại: {e}')
        sys.exit(1)

    with app.app_context():
        try:
            # db.create_all() chỉ tạo bảng mới — không xóa bảng cũ
            db.create_all()
            print('[MIGRATION] db.create_all() thành công.')

            # Kiểm tra bảng đã tồn tại
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if 'login_attempt' in tables:
                print('[MIGRATION] ✅ Bảng login_attempt đã tồn tại.')
            else:
                print('[MIGRATION] ⚠️  Bảng login_attempt CHƯA được tạo.')

            if 'admin_audit_log' in tables:
                print('[MIGRATION] ✅ Bảng admin_audit_log đã tồn tại.')
            else:
                print('[MIGRATION] ⚠️  Bảng admin_audit_log CHƯA được tạo.')

            print('[MIGRATION] Hoàn thành.')
        except Exception as e:
            print(f'[MIGRATION ERROR] {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    run_migration()
