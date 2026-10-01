import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

# Users table: stores admin, teacher, and student accounts
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
    full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Attendance table: links each entry to a real user account
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

conn.commit()

# Create one default admin account so you can log in immediately
cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO users (username, password, role, full_name)
        VALUES (?, ?, ?, ?)
    """, ("admin", "admin123", "admin", "System Admin"))
    conn.commit()
    print("Default admin created — username: admin, password: admin123")
else:
    print("Admin already exists.")

conn.close()
print("Database setup complete: attendance_system.db")