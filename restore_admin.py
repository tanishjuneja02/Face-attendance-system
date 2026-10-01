import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

cursor.execute("UPDATE users SET is_deleted = 0 WHERE username = 'admin'")
conn.commit()

cursor.execute("SELECT id, username, role, is_deleted FROM users WHERE username = 'admin'")
print(cursor.fetchone())

conn.close()
print("Admin restored.")
