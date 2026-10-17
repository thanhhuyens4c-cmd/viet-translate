"""
Migration script: JSON Payout Methods -> PostgreSQL Tables
Idempotent migration that creates payout_methods and payout_histories tables,
and safely transfers records from instance/interpreter_payout_methods.json if present.
"""

import os
import sys
import json
from datetime import datetime

# Set up project root
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, basedir)

from app import app
from models import db, PayoutMethod, PayoutHistory, User

def run_migration():
    print("[MIGRATION] Starting Payout Methods migration to PostgreSQL...")
    with app.app_context():
        # 1. Create tables if they do not exist
        try:
            PayoutMethod.__table__.create(db.engine, checkfirst=True)
            PayoutHistory.__table__.create(db.engine, checkfirst=True)
            print("[MIGRATION] Table 'payout_methods' and 'payout_histories' verified/created.")
        except Exception as e:
            print(f"[MIGRATION ERROR] Failed to create tables: {e}")
            sys.exit(1)

        # 2. Check for legacy JSON store
        json_path = os.path.join(basedir, 'instance', 'interpreter_payout_methods.json')
        if not os.path.exists(json_path):
            print(f"[MIGRATION] No legacy JSON file found at {json_path}. Database tables are ready.")
            return

        print(f"[MIGRATION] Reading legacy JSON data from {json_path}...")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[MIGRATION ERROR] Failed to read JSON file: {e}")
            sys.exit(1)

        total_users = 0
        total_methods_imported = 0
        total_methods_skipped = 0
        total_history_imported = 0

        for user_key, user_data in data.items():
            try:
                user_id = int(user_key)
            except ValueError:
                print(f"[MIGRATION WARNING] Skipping invalid user_key '{user_key}'.")
                continue

            user = User.query.get(user_id)
            if not user:
                print(f"[MIGRATION WARNING] User #{user_id} not found in database. Skipping records.")
                continue

            total_users += 1
            methods = user_data.get('methods', [])
            history = user_data.get('history', [])

            for m in methods:
                method_id = m.get('id')
                if not method_id:
                    continue

                existing = PayoutMethod.query.get(method_id)
                if existing:
                    total_methods_skipped += 1
                    continue

                created_at = datetime.utcnow()
                if m.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(m['created_at'].replace('Z', '+00:00'))
                    except Exception:
                        pass

                updated_at = created_at
                if m.get('updated_at'):
                    try:
                        updated_at = datetime.fromisoformat(m['updated_at'].replace('Z', '+00:00'))
                    except Exception:
                        pass

                pm = PayoutMethod(
                    id=method_id,
                    user_id=user_id,
                    bank_code=m.get('bank_code', ''),
                    bank_short_name=m.get('bank_short_name', ''),
                    bank_name=m.get('bank_name', ''),
                    account_number=m.get('account_number', ''),
                    masked_account_number=m.get('masked_account_number', ''),
                    account_holder_name=m.get('account_holder_name', ''),
                    branch=m.get('branch', ''),
                    is_default=bool(m.get('is_default', False)),
                    status=m.get('status', 'active'),
                    status_label=m.get('status_label', 'Khai báo hợp lệ · Đang hoạt động'),
                    created_at=created_at,
                    updated_at=updated_at
                )
                db.session.add(pm)
                total_methods_imported += 1

            for h in history:
                created_at = datetime.utcnow()
                if h.get('timestamp'):
                    try:
                        created_at = datetime.fromisoformat(h['timestamp'].replace('Z', '+00:00'))
                    except Exception:
                        pass

                ph = PayoutHistory(
                    user_id=user_id,
                    method_id=h.get('method_id'),
                    action=h.get('action', 'unknown'),
                    bank=h.get('bank'),
                    masked_account=h.get('masked_account'),
                    summary=h.get('summary'),
                    created_at=created_at
                )
                db.session.add(ph)
                total_history_imported += 1

        db.session.commit()
        print(f"[MIGRATION SUCCESS] Imported {total_methods_imported} methods (skipped {total_methods_skipped} existing), {total_history_imported} history logs across {total_users} users.")
        print(f"[MIGRATION NOTE] Legacy JSON file retained at {json_path} for safety/rollback.")

if __name__ == '__main__':
    run_migration()
