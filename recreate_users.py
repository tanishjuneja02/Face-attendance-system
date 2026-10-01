import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

users_to_restore = [
    ("admin", "admin123", "admin", "System Admin"),
    ("Rahul", "rahul123", "student", "Rahul"),
    ("Tanish juneja", "tanish123", "student", "Tanish juneja"),
]

for username, password, role, full_name in users_to_restore:
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (username, password, role, full_name, is_deleted)
            VALUES (?, ?, ?, ?, 0)
        """, (username, password, role, full_name))
        print(f"Recreated: {username}")
    else:
        print(f"Already exists: {username}")

conn.commit()
conn.close()
print("Done.")