import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

if "is_deleted" not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN is_deleted INTEGER DEFAULT 0")
    print("Added is_deleted column.")
else:
    print("Column already exists.")

conn.commit()
conn.close()