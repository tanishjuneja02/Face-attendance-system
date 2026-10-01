import sqlite3

conn = sqlite3.connect("attendance_system.db")
cursor = conn.cursor()

# Create subjects table
cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)
""")

# Add some default subjects if none exist
default_subjects = ["Mathematics", "Physics", "Chemistry", "English", "Computer Science"]
for subject in default_subjects:
    cursor.execute("SELECT * FROM subjects WHERE name = ?", (subject,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO subjects (name) VALUES (?)", (subject,))

conn.commit()

# Add subject_id column to attendance table if it doesn't already exist
cursor.execute("PRAGMA table_info(attendance)")
columns = [col[1] for col in cursor.fetchall()]

if "subject_id" not in columns:
    cursor.execute("ALTER TABLE attendance ADD COLUMN subject_id INTEGER REFERENCES subjects(id)")
    print("Added subject_id column to attendance table.")
else:
    print("subject_id column already exists.")

conn.commit()
conn.close()
print("Database updated successfully.")