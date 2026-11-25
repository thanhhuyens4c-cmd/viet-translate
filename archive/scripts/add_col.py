import sqlite3

db_path = 'instance/database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE translator_verification ADD COLUMN checklist_data TEXT;")
    conn.commit()
    print("Added checklist_data")
except Exception as e:
    print(f"Error: {e}")

try:
    cursor.execute("ALTER TABLE user ADD COLUMN email_verified BOOLEAN DEFAULT 0;")
    conn.commit()
    print("Added email_verified")
except Exception as e:
    print(f"Error: {e}")

conn.close()
