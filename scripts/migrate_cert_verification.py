"""
scripts/migrate_cert_verification.py
Migration script: Thêm các cột phục vụ Xác thực trực tuyến qua mã QR & Digital Badge
cho TranslatorVerification và TranslatorProfile.
Hỗ trợ cả PostgreSQL 16 và SQLite an toàn (idempotent - chạy nhiều lần không lỗi).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from sqlalchemy import text, inspect

def run_migration():
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)
        dialect = engine.dialect.name
        print(f"[*] Đang thực hiện migration trên cơ sở dữ liệu ({dialect})...")

        # 1. Bảng translator_verification
        tv_cols = [c['name'] for c in inspector.get_columns('translator_verification')]
        tv_additions = [
            ('certificate_id', 'VARCHAR(100)'),
            ('verification_url', 'VARCHAR(500)'),
            ('verification_source', 'VARCHAR(50)'),
            ('verification_metadata', 'TEXT'),
            ('is_online_verified', 'BOOLEAN DEFAULT FALSE'),
            ('online_verified_at', 'TIMESTAMP')
        ]

        with engine.connect() as conn:
            for col_name, col_type in tv_additions:
                if col_name not in tv_cols:
                    print(f"  + Thêm cột '{col_name}' vào bảng 'translator_verification'...")
                    try:
                        conn.execute(text(f"ALTER TABLE translator_verification ADD COLUMN {col_name} {col_type};"))
                        conn.commit()
                        print(f"    ✓ Thành công: {col_name}")
                    except Exception as e:
                        print(f"    ✗ Lỗi khi thêm {col_name}: {e}")
                else:
                    print(f"  - Cột '{col_name}' đã tồn tại trong 'translator_verification'.")

            # 2. Bảng translator_profile
            tp_cols = [c['name'] for c in inspector.get_columns('translator_profile')]
            tp_additions = [
                ('has_digital_credential', 'BOOLEAN DEFAULT FALSE'),
                ('credential_public_url', 'VARCHAR(500)'),
                ('credential_issuer', 'VARCHAR(100)'),
                ('credential_badge_name', 'VARCHAR(255)')
            ]

            for col_name, col_type in tp_additions:
                if col_name not in tp_cols:
                    print(f"  + Thêm cột '{col_name}' vào bảng 'translator_profile'...")
                    try:
                        conn.execute(text(f"ALTER TABLE translator_profile ADD COLUMN {col_name} {col_type};"))
                        conn.commit()
                        print(f"    ✓ Thành công: {col_name}")
                    except Exception as e:
                        print(f"    ✗ Lỗi khi thêm {col_name}: {e}")
                else:
                    print(f"  - Cột '{col_name}' đã tồn tại trong 'translator_profile'.")

        print("[✓] Migration hoàn tất thành công!")

if __name__ == '__main__':
    run_migration()

