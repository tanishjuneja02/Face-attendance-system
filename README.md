# 📷 Face Attendance System

Students mark attendance by scanning their face. The system finds the student in the
database, shows their details (name, roll number, class, subject, time) and records the
attendance. Teachers and admins log in separately to view reports and manage students.

Built with **Python, Streamlit, DeepFace (Facenet) and SQLite**.

## How it works

```
Scan page (home) -> pick subject -> take photo
        |
Face -> embedding -> compared with every registered student
        |
   match found  -> show roll no, name, class, subject, time -> "Attendance marked"
   no match     -> "Face not recognised"

Menu: Staff Login -> Attendance (teacher + admin) / Register (admin only)
```

| Role | What they can do |
|---|---|
| **Student** | Scan face to mark attendance (no account needed) |
| **Teacher** | View, filter and download attendance |
| **Admin** | Everything a teacher can, plus register students, deactivate / restore / permanently delete them, add subjects, create staff accounts |

Rules: one attendance mark per student, per subject, per day. Times are in IST.

**Deleting students is two-step.** *Deactivate* hides a student and stops face matching for them,
but keeps their attendance history. They appear under *Recently deleted*, where an admin can
*restore* them or *delete them permanently* (this also removes their photo and attendance).

## Project structure

```
app.py                  Scan page (home)
pages/                  Staff Login, Attendance report, Register (admin)
core/
  database.py           Tables and all SQL queries
  face.py               Face embeddings and matching
  auth.py               Password hashing and login check
  attendance.py         Marking rules (no duplicates)
  photos.py             Saving student photos
  ui.py                 Small Streamlit helpers
  components.py         HTML/CSS blocks for the home page
tests/                  Automatic tests (pytest)
scripts/                init_db.py and webcam_test.py (manual helpers)
.streamlit/config.toml  Theme colour
data/                   Database and student photos (created automatically, not in Git)
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements-dev.txt
```

## Run the app

```bash
streamlit run app.py
```

1. Open **Staff Login** in the menu. The first time, create the admin account.
2. Log in, open **Register**, and register each student with a clear front-facing photo.
3. Go back to the home page. Students pick a subject and scan their face.
4. Teachers log in and open **Attendance** to filter and download records.

## Run the tests

```bash
pytest
```

The tests use a temporary database and fake face data, so they need no webcam.

## Settings (optional environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `ATTENDANCE_DB` | `data/attendance.db` | Database file |
| `ATTENDANCE_PHOTO_DIR` | `data/photos` | Where student photos are saved |
| `FACE_THRESHOLD` | `0.40` | Match strictness (lower = stricter) |
| `FACE_DETECTOR` | `mtcnn` | Face detector (`opencv` is faster but less accurate) |

## Known limitations

- No liveness check: a photo of a student shown to the camera may be accepted.
- Match accuracy depends on lighting and photo quality. Tune `FACE_THRESHOLD` with your own class.
- Student photos and the database contain personal data. They are in `data/`, which is git-ignored. Never commit them.
