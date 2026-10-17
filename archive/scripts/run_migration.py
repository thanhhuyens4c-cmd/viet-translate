import sqlite3

db_path = 'instance/database.db'
sql_path = 'migration_task1_email_verification_checklist.sql'

with open(sql_path, 'r', encoding='utf-8') as f:
    sql_script = f.read()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.executescript(sql_script)
    conn.commit()
    print("Migration executed successfully.")
except Exception as e:
    print(f"Migration failed: {e}")
finally:
    conn.close()
