"""
migration_hirer_job_moderation.py
Cập nhật schema SQLite và đồng bộ dữ liệu cho:
- User (verified_at)
- HirerProfile (verification_status, verified_at, bank_name, bank_account_number, authorization_doc_url, verification_checklist_data, rejection_reason)
- Job (moderation_status, moderation_checklist_data, moderation_notes, moderated_at, moderated_by, submission_version)
- Đồng bộ an toàn cho các job và hirer cũ.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. User table
    user_cols = [c[1] for c in cur.execute("PRAGMA table_info(user)").fetchall()]
    if 'verified_at' not in user_cols:
        print("Adding verified_at to user...")
        cur.execute("ALTER TABLE user ADD COLUMN verified_at DATETIME")

    # 2. HirerProfile table
    hp_cols = [c[1] for c in cur.execute("PRAGMA table_info(hirer_profile)").fetchall()]
    hp_additions = [
        ('verification_status', "VARCHAR(20) DEFAULT 'unverified'"),
        ('verified_at', "DATETIME"),
        ('bank_name', "VARCHAR(100)"),
        ('bank_account_number', "VARCHAR(50)"),
        ('authorization_doc_url', "VARCHAR(500)"),
        ('verification_checklist_data', "TEXT"),
        ('rejection_reason', "TEXT"),
    ]
    for col_name, col_def in hp_additions:
        if col_name not in hp_cols:
            print(f"Adding {col_name} to hirer_profile...")
            cur.execute(f"ALTER TABLE hirer_profile ADD COLUMN {col_name} {col_def}")

    # 3. Job table
    job_cols = [c[1] for c in cur.execute("PRAGMA table_info(job)").fetchall()]
    job_additions = [
        ('moderation_status', "VARCHAR(20) DEFAULT 'pending'"),
        ('moderation_checklist_data', "TEXT"),
        ('moderation_notes', "TEXT"),
        ('moderated_at', "DATETIME"),
        ('moderated_by', "INTEGER REFERENCES user(id)"),
        ('submission_version', "INTEGER DEFAULT 1"),
    ]
    for col_name, col_def in job_additions:
        if col_name not in job_cols:
            print(f"Adding {col_name} to job...")
            cur.execute(f"ALTER TABLE job ADD COLUMN {col_name} {col_def}")

    # 4. Migrate existing job moderation_status
    print("Syncing existing job moderation statuses...")
    # Flagged jobs
    cur.execute("UPDATE job SET moderation_status = 'flagged' WHERE is_flagged = 1")
    # Open / contracted / completed jobs that are not flagged -> approved
    cur.execute("UPDATE job SET moderation_status = 'approved' WHERE (status IN ('open', 'contracted', 'completed') OR status IS NULL) AND (is_flagged = 0 OR is_flagged IS NULL)")
    # Pending jobs
    cur.execute("UPDATE job SET moderation_status = 'pending' WHERE status = 'pending' AND (is_flagged = 0 OR is_flagged IS NULL)")

    # 5. Migrate existing hirer profiles
    print("Syncing existing hirer profile statuses...")
    cur.execute("UPDATE hirer_profile SET verification_status = 'verified' WHERE is_verified = 1")
    cur.execute("UPDATE hirer_profile SET verification_status = 'unverified' WHERE is_verified = 0 OR is_verified IS NULL")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate()
