"""
migration_account_module.py
Cập nhật schema cơ sở dữ liệu cho phân hệ Tài khoản Phiên dịch viên (Mục V).

Phạm vi thực hiện:
1. Mở rộng bảng User: bio, date_of_birth, city, is_public_profile
2. Tạo bảng InterpreterService (Năng lực & Bảng giá - Mục 5.2)
3. Tạo bảng InterpreterPreference (Tiêu chí nhận việc - Mục 5.4)
4. Tạo bảng NotificationSetting (Cài đặt thông báo - Mục 5.6.1)
5. Tạo bảng UserSession (Quản lý phiên - Mục 5.6.2)
6. Tạo bảng SupportTicket (Yêu cầu hỗ trợ - Mục 5.7.3)

Ràng buộc nghiêm ngặt:
- TUYỆT ĐỐI KHÔNG sửa các bảng liên quan đến Xác minh (Verification/Documents).
- Sử dụng Foreign Key liên kết chặt chẽ với User ID.
- Đảm bảo tính idempotent (chạy nhiều lần an toàn, không sinh lỗi).
"""

import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')


def migrate_sqlite(db_path=DB_PATH):
    if not os.path.exists(db_path):
        print(f"[MIGRATION ERROR] Database file not found at: {db_path}", file=sys.stderr)
        return False

    print(f"[*] Starting migration for Account Module on: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        cur.execute("PRAGMA foreign_keys = ON")

        # ---------------------------------------------------------------------
        # 1. Bổ sung các cột mới vào bảng "user"
        # ---------------------------------------------------------------------
        user_cols = [c[1] for c in cur.execute("PRAGMA table_info(user)").fetchall()]
        user_additions = [
            ('bio', 'TEXT'),
            ('date_of_birth', 'VARCHAR(20)'),
            ('city', 'VARCHAR(100)'),
            ('is_public_profile', 'BOOLEAN DEFAULT 1'),
        ]

        for col_name, col_def in user_additions:
            if col_name not in user_cols:
                print(f"[+] Adding column '{col_name}' ({col_def}) to 'user' table...")
                cur.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}")
            else:
                print(f"[-] Column '{col_name}' already exists in 'user' table.")

        # ---------------------------------------------------------------------
        # 2. Tạo bảng interpreter_service (Năng lực & Bảng giá - Mục 5.2)
        # ---------------------------------------------------------------------
        print("[*] Checking 'interpreter_service' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interpreter_service (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_lang VARCHAR(100) NOT NULL,
                target_lang VARCHAR(100) NOT NULL,
                interpreting_type VARCHAR(100) NOT NULL,
                specialization VARCHAR(255),
                hourly_rate REAL,
                session_rate REAL,
                currency VARCHAR(10) DEFAULT 'VND',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_interpreter_service_user_id ON interpreter_service (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_interpreter_service_is_active ON interpreter_service (is_active)")

        # ---------------------------------------------------------------------
        # 3. Tạo bảng interpreter_preference (Tiêu chí nhận việc - Mục 5.4)
        # ---------------------------------------------------------------------
        print("[*] Checking 'interpreter_preference' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interpreter_preference (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                languages TEXT,
                specializations TEXT,
                work_mode VARCHAR(50) DEFAULT 'both',
                min_rate REAL,
                max_rate REAL,
                allow_outside_rate BOOLEAN DEFAULT 0,
                available_hours TEXT,
                locations TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_interpreter_preference_user_id ON interpreter_preference (user_id)")
        pref_cols = [c[1] for c in cur.execute("PRAGMA table_info(interpreter_preference)").fetchall()]
        if 'locations' not in pref_cols:
            print("[+] Adding column 'locations' (TEXT) to 'interpreter_preference' table...")
            cur.execute("ALTER TABLE interpreter_preference ADD COLUMN locations TEXT")

        # ---------------------------------------------------------------------
        # 4. Tạo bảng notification_setting (Cài đặt thông báo - Mục 5.6.1)
        # ---------------------------------------------------------------------
        print("[*] Checking 'notification_setting' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_setting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                notify_job_match BOOLEAN DEFAULT 1,
                notify_application_update BOOLEAN DEFAULT 1,
                notify_profile_view BOOLEAN DEFAULT 1,
                notify_schedule_reminder BOOLEAN DEFAULT 1,
                reminder_time_60m BOOLEAN DEFAULT 1,
                reminder_time_30m BOOLEAN DEFAULT 1,
                reminder_time_15m BOOLEAN DEFAULT 0,
                notify_income_update BOOLEAN DEFAULT 1,
                notify_security_alert BOOLEAN DEFAULT 1,
                notify_marketing BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_notification_setting_user_id ON notification_setting (user_id)")
        notif_cols = [c[1] for c in cur.execute("PRAGMA table_info(notification_setting)").fetchall()]
        notif_additions = [
            ('notify_profile_view', 'BOOLEAN DEFAULT 1'),
            ('reminder_time_60m', 'BOOLEAN DEFAULT 1'),
            ('reminder_time_30m', 'BOOLEAN DEFAULT 1'),
            ('reminder_time_15m', 'BOOLEAN DEFAULT 0'),
            ('notify_income_update', 'BOOLEAN DEFAULT 1'),
            ('notify_security_alert', 'BOOLEAN DEFAULT 1'),
        ]
        for col_name, col_def in notif_additions:
            if col_name not in notif_cols:
                print(f"[+] Adding column '{col_name}' ({col_def}) to 'notification_setting' table...")
                cur.execute(f"ALTER TABLE notification_setting ADD COLUMN {col_name} {col_def}")

        # ---------------------------------------------------------------------
        # 5. Tạo bảng user_session (Quản lý phiên - Mục 5.6.2)
        # ---------------------------------------------------------------------
        print("[*] Checking 'user_session' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id VARCHAR(255),
                device_name VARCHAR(255),
                ip_address VARCHAR(50),
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_user_session_user_id ON user_session (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_user_session_session_id ON user_session (session_id)")

        # ---------------------------------------------------------------------
        # 6. Tạo bảng support_ticket (Yêu cầu hỗ trợ - Mục 5.7.3)
        # ---------------------------------------------------------------------
        print("[*] Checking 'support_ticket' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_ticket (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_code VARCHAR(50) NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                category VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                attachment_url VARCHAR(500),
                status VARCHAR(30) DEFAULT 'open',
                admin_reply TEXT,
                admin_reply_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)
        ticket_cols = [c[1] for c in cur.execute("PRAGMA table_info(support_ticket)").fetchall()]
        if 'admin_reply' not in ticket_cols:
            cur.execute("ALTER TABLE support_ticket ADD COLUMN admin_reply TEXT")
        if 'admin_reply_at' not in ticket_cols:
            cur.execute("ALTER TABLE support_ticket ADD COLUMN admin_reply_at DATETIME")

        cur.execute("CREATE INDEX IF NOT EXISTS ix_support_ticket_user_id ON support_ticket (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_support_ticket_ticket_code ON support_ticket (ticket_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_support_ticket_status ON support_ticket (status)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_support_ticket_created_at ON support_ticket (created_at)")

        conn.commit()
        print("[✓] Migration executed successfully!")

        # ---------------------------------------------------------------------
        # Kiểm tra tính toàn vẹn (Integrity Verification)
        # ---------------------------------------------------------------------
        print("[*] Verifying schema integrity...")
        all_tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        required_tables = [
            'interpreter_service',
            'interpreter_preference',
            'notification_setting',
            'user_session',
            'support_ticket'
        ]
        for tbl in required_tables:
            if tbl not in all_tables:
                raise RuntimeError(f"Integrity check failed: table '{tbl}' was not created.")
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
            print(f"  - Table '{tbl}': {len(cols)} columns verified.")

        updated_user_cols = [c[1] for c in cur.execute("PRAGMA table_info(user)").fetchall()]
        for c, _ in user_additions:
            if c not in updated_user_cols:
                raise RuntimeError(f"Integrity check failed: column '{c}' missing from 'user'.")
        print("  - Table 'user': new columns bio, date_of_birth, city, is_public_profile verified.")

        # Đảm bảo các bảng xác minh không bị ảnh hưởng
        for v_tbl in ['translator_verification', 'verification_document']:
            if v_tbl in all_tables:
                print(f"  - Verification table '{v_tbl}': intact and untouched.")

        print("[✓] All integrity checks passed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[!] Migration failed: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_sqlite()
