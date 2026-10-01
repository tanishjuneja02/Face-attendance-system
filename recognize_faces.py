import cv2
import os
import sqlite3
from datetime import datetime
from deepface import DeepFace

KNOWN_FACES_DIR = "known_faces"
DB_PATH = "attendance_system.db"

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------- Ask which subject this class is for ----------
def choose_subject():
    conn = get_connection()
    subjects = conn.execute("SELECT id, name FROM subjects ORDER BY id").fetchall()
    conn.close()

    if not subjects:
        raise SystemExit("No subjects found in the database. Add subjects first.")

    print("\nWhich class is this attendance for?")
    for sid, sname in subjects:
        print(f"  {sid}. {sname}")

    valid = {sid: sname for sid, sname in subjects}
    while True:
        try:
            choice = int(input("Enter subject number: "))
            if choice in valid:
                print(f"Marking attendance for: {valid[choice]}\n")
                return choice, valid[choice]
        except ValueError:
            pass
        print("Invalid choice, try again.")


SUBJECT_ID, SUBJECT_NAME = choose_subject()

# ---------- Load known faces and link each one to a user id ----------
print("Loading known faces...")
known_files = {}  # person name -> image path
for f in os.listdir(KNOWN_FACES_DIR):
    if f.lower().endswith(IMAGE_EXTS):
        known_files[os.path.splitext(f)[0]] = os.path.join(KNOWN_FACES_DIR, f)

conn = get_connection()


rows = conn.execute("SELECT id, full_name, username FROM users WHERE role = 'student'").fetchall()
conn.close()
name_to_id = {}
for uid, full_name, username in rows:
        name_to_id[full_name.strip().lower()] = uid
        name_to_id[username.strip().lower()] = uid

# Keep only the photos that match a user in the database
known_people = []
for person in known_files:
    if person.strip().lower() in name_to_id:
        known_people.append(person)
    else:
        print(f"Skipped '{person}': no user with this full_name in the database")

print(f"Loaded: {known_people}")
if not known_people:
    raise SystemExit("No known faces match users in the database.")


def already_marked_today(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM attendance WHERE user_id = ? AND subject_id = ? AND date = ?",
        (user_id, SUBJECT_ID, today),
    ).fetchone()
    conn.close()
    return row is not None


def mark_attendance(name):
    if name in ["Unknown", "No face detected", "Scanning..."]:
        return False
    if name in marked_today_cache:
        return False

    user_id = name_to_id[name.strip().lower()]
    if already_marked_today(user_id):
        marked_today_cache.add(name)
        return False

    now = datetime.now()
    conn = get_connection()
    conn.execute(
        "INSERT INTO attendance (user_id, subject_id, date, time) VALUES (?, ?, ?, ?)",
        (user_id, SUBJECT_ID, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")),
    )
    conn.commit()
    conn.close()

    print(f"✓ Marked attendance for {name} ({SUBJECT_NAME})")
    marked_today_cache.add(name)
    return True


video_capture = cv2.VideoCapture(0)
print("Starting webcam. Press 'q' to quit.")

frame_count = 0
display_name = "Scanning..."
marked_today_cache = set()
just_marked = ""
just_marked_timer = 0

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    frame_count += 1

    if frame_count % 15 == 0:
        try:
            cv2.imwrite("temp_frame.jpg", frame)

            best_match = "Unknown"
            best_distance = 1.0

            for person in known_people:
                known_path = known_files[person]
                try:
                    result = DeepFace.verify(
                        img1_path="temp_frame.jpg",
                        img2_path=known_path,
                        enforce_detection=False,
                        detector_backend="mtcnn",
                    )
                    if result["verified"] and result["distance"] < best_distance:
                        best_distance = result["distance"]
                        best_match = person
                except Exception as inner_e:
                    print(f"Compare with {person} failed: {inner_e}")
                    continue

            print(f"Detected: {best_match}")
            display_name = best_match

            if mark_attendance(best_match):
                just_marked = f"{best_match} marked present!"
                just_marked_timer = 45

        except Exception as e:
            print("OUTER ERROR:", str(e))
            display_name = "No face detected"

    cv2.putText(frame, display_name, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"Subject: {SUBJECT_NAME}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    if just_marked_timer > 0:
        cv2.putText(frame, just_marked, (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        just_marked_timer -= 1

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
if os.path.exists("temp_frame.jpg"):
    os.remove("temp_frame.jpg")