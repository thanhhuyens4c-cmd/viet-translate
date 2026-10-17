import sqlite3
import os

db_path = 'instance/database.db'

def alter_table():
    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE translator_preference ADD COLUMN auto_reply_enabled BOOLEAN DEFAULT 0")
        print("Added auto_reply_enabled")
    except sqlite3.OperationalError as e:
        print(f"auto_reply_enabled: {e}")

    try:
        cursor.execute("ALTER TABLE translator_preference ADD COLUMN auto_reply_message TEXT")
        print("Added auto_reply_message")
    except sqlite3.OperationalError as e:
        print(f"auto_reply_message: {e}")

    try:
        cursor.execute("ALTER TABLE translator_preference ADD COLUMN auto_reply_cooldown_hours INTEGER DEFAULT 24")
        print("Added auto_reply_cooldown_hours")
    except sqlite3.OperationalError as e:
        print(f"auto_reply_cooldown_hours: {e}")

    try:
        cursor.execute("ALTER TABLE message ADD COLUMN is_auto_reply BOOLEAN DEFAULT 0 NOT NULL")
        print("Added is_auto_reply to message")
    except sqlite3.OperationalError as e:
        print(f"is_auto_reply in message: {e}")

    try:
        cursor.execute("ALTER TABLE direct_message ADD COLUMN is_auto_reply BOOLEAN DEFAULT 0 NOT NULL")
        print("Added is_auto_reply to direct_message")
    except sqlite3.OperationalError as e:
        print(f"is_auto_reply in direct_message: {e}")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == '__main__':
    alter_table()
