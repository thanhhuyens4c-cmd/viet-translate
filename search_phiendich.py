import sqlite3
conn = sqlite3.connect('instance/database.db')
c = conn.cursor()
print("Translators:")
c.execute("SELECT id, name, email, phone FROM user WHERE role = 'translator' ORDER BY id DESC LIMIT 15")
for r in c.fetchall():
    print(r)

print("\nJobs:")
c.execute("SELECT id, title, status FROM job ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(r)
