import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()

print("All users currently in the database:")
for row in rows:
    print(row)

conn.close()
