"""SQLite storage: students, staff, subjects and attendance.

Every function takes an optional ``db_path`` so tests can use a temporary
database instead of the real one.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

try:  # only needed when the hosted (Turso) database is used
    import libsql
except ImportError:  # pragma: no cover
    libsql = None

DEFAULT_DB_PATH = os.environ.get("ATTENDANCE_DB", "data/attendance.db")
DEFAULT_SUBJECTS = ["Mathematics", "Physics", "Chemistry", "English", "Computer Science"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no     TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    class_name  TEXT NOT NULL,
    photo_path  TEXT,
    embedding   TEXT,
    is_deleted  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staff (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK(role IN ('teacher', 'admin')),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS photo_store (
    path  TEXT PRIMARY KEY,
    data  BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,
    time        TEXT NOT NULL,
    UNIQUE(student_id, subject_id, date)
);
"""


class DuplicateError(Exception):
    """Raised when a unique value (roll number, username, subject) already exists."""


# ------------------------------------------------------------ hosted database
# On Streamlit Community Cloud the app's disk is wiped whenever the app sleeps, reboots or
# redeploys, so a local SQLite file loses all data. Set TURSO_DATABASE_URL and
# TURSO_AUTH_TOKEN (Streamlit Secrets or environment variables) to keep the data in a hosted
# Turso database instead. Without them the app uses the local file, as before.
@lru_cache(maxsize=1)
def _secrets_config():
    try:
        import streamlit as st
        url = st.secrets.get("TURSO_DATABASE_URL")
        token = st.secrets.get("TURSO_AUTH_TOKEN")
        return (str(url), str(token) if token else None) if url else None
    except Exception:  # no secrets file, or streamlit not available
        return None


def _remote_config():
    """(url, token) of the hosted database, or None to use the local SQLite file."""
    url = os.environ.get("TURSO_DATABASE_URL")
    if url:
        return url, os.environ.get("TURSO_AUTH_TOKEN")
    return _secrets_config()


def using_remote():
    """True when data is stored in the hosted database (so it survives app restarts)."""
    return _remote_config() is not None


class _Row:
    """A result row that works like sqlite3.Row: row["name"], row[0], dict(row)."""

    def __init__(self, names, values):
        self._names, self._values = list(names), tuple(values)

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return self._values[self._names.index(key)]
            except ValueError:
                raise IndexError(f"No column named '{key}'") from None
        return self._values[key]

    def keys(self):
        return list(self._names)

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


class _Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def _names(self):
        return [d[0] for d in (self._cursor.description or [])]

    def fetchone(self):
        names = self._names()
        row = self._cursor.fetchone()
        return None if row is None else _Row(names, row)

    def fetchall(self):
        names = self._names()
        return [_Row(names, r) for r in self._cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class _LibsqlConnection:
    """Makes a libsql connection behave like the sqlite3 one the rest of this file expects."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        try:
            return _Cursor(self._conn.execute(sql, tuple(params)))
        except ValueError as exc:  # libsql reports constraint errors as ValueError
            if "constraint failed" in str(exc).lower():
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        close = getattr(self._conn, "close", None)
        if close:
            close()


def _open_remote():
    if libsql is None:
        raise RuntimeError("The 'libsql' package is needed for the hosted database. "
                           "Run: pip install libsql")
    url, token = _remote_config()
    return _LibsqlConnection(libsql.connect(url, auth_token=token or ""))


def _open_local(path):
    path = str(path or DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect(db_path=None):
    """Open a connection, commit on success, roll back on error, always close.

    An explicit db_path always means a local SQLite file (tests). With no path, the hosted
    database is used when it is configured, otherwise the default local file.
    """
    conn = _open_remote() if (db_path is None and using_remote()) else _open_local(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(conn):
    """Upgrade databases created by older versions of the app."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(students)")}
    if "is_deleted" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")


_remote_ready = False


def init_db(db_path=None):
    """Create the tables (if missing), upgrade old databases, add default subjects.

    Streamlit runs every page on every click, so for the hosted database this is done only
    once per app process (each call would otherwise cost several network round trips).
    """
    global _remote_ready
    remote = db_path is None and using_remote()
    if remote and _remote_ready:
        return
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        for name in DEFAULT_SUBJECTS:
            conn.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
    if remote:
        _remote_ready = True


# ---------------------------------------------------------------- students
def _clean(value, label):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value


def add_student(roll_no, name, class_name, photo_path=None, embedding=None, db_path=None):
    """Add a student and return the new id."""
    roll_no = _clean(roll_no, "Roll number")
    name = _clean(name, "Name")
    class_name = _clean(class_name, "Class")
    embedding_json = json.dumps(list(embedding)) if embedding is not None else None
    try:
        with connect(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO students (roll_no, name, class_name, photo_path, embedding) "
                "VALUES (?, ?, ?, ?, ?)",
                (roll_no, name, class_name, photo_path, embedding_json),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Roll number '{roll_no}' already exists.") from exc


def _student_row(row):
    data = dict(row)
    raw = data.pop("embedding", None)
    data["embedding"] = json.loads(raw) if raw else None
    return data


def get_student(student_id, db_path=None):
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return _student_row(row) if row else None


def get_student_by_roll(roll_no, db_path=None):
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE roll_no = ?", (str(roll_no).strip(),)
        ).fetchone()
    return _student_row(row) if row else None


def list_students(class_name=None, db_path=None, deleted=False):
    """Students (without face data). Active ones by default; deleted=True for deactivated ones."""
    query = "SELECT id, roll_no, name, class_name, photo_path FROM students WHERE is_deleted = ?"
    params = [1 if deleted else 0]
    if class_name:
        query += " AND class_name = ?"
        params.append(class_name)
    query += " ORDER BY class_name, roll_no"
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_students_with_embeddings(db_path=None, include_deleted=False):
    """Students that have a stored face, as dicts with an 'embedding' list.

    Only active students by default. include_deleted=True also returns deactivated ones
    (used to stop the same face being registered again under a new name).
    """
    query = "SELECT * FROM students WHERE embedding IS NOT NULL"
    if not include_deleted:
        query += " AND is_deleted = 0"
    with connect(db_path) as conn:
        rows = conn.execute(query).fetchall()
    return [_student_row(r) for r in rows]


def _set_deleted(student_id, flag, db_path):
    with connect(db_path) as conn:
        cur = conn.execute("UPDATE students SET is_deleted = ? WHERE id = ?", (flag, student_id))
        return cur.rowcount > 0


def update_student(student_id, roll_no, name, class_name, photo_path=None, embedding=None, db_path=None):
    """Edit a student. photo_path and embedding are only changed when they are given.

    Returns True if the student exists. Raises DuplicateError if the roll number is taken.
    """
    roll_no = _clean(roll_no, "Roll number")
    name = _clean(name, "Name")
    class_name = _clean(class_name, "Class")
    sets, params = ["roll_no = ?", "name = ?", "class_name = ?"], [roll_no, name, class_name]
    if photo_path is not None:
        sets.append("photo_path = ?")
        params.append(photo_path)
    if embedding is not None:
        sets.append("embedding = ?")
        params.append(json.dumps(list(embedding)))
    params.append(student_id)
    try:
        with connect(db_path) as conn:
            cur = conn.execute(f"UPDATE students SET {', '.join(sets)} WHERE id = ?", params)
            return cur.rowcount > 0
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Roll number '{roll_no}' already exists.") from exc


def deactivate_student(student_id, db_path=None):
    """Soft delete: hide the student and stop matching them, but keep their records."""
    return _set_deleted(student_id, 1, db_path)


def restore_student(student_id, db_path=None):
    """Undo a soft delete."""
    return _set_deleted(student_id, 0, db_path)


def count_students(db_path=None):
    """Number of active students."""
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM students WHERE is_deleted = 0").fetchone()[0]


def count_present_on(date, db_path=None):
    """Number of different active students marked present on a date (any subject)."""
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT a.student_id) FROM attendance a "
            "JOIN students s ON a.student_id = s.id WHERE a.date = ? AND s.is_deleted = 0",
            (date,),
        ).fetchone()[0]


def delete_student(student_id, db_path=None):
    """PERMANENTLY delete a student and their attendance. Returns True if a row was removed."""
    with connect(db_path) as conn:
        conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        return cur.rowcount > 0


# ------------------------------------------------------------ photo storage
# Photos live on disk, which the hosted app loses on restart, so a copy is kept in the database.
def save_photo_blob(path, data, db_path=None):
    with connect(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO photo_store (path, data) VALUES (?, ?)", (str(path), data))


def get_photo_blob(path, db_path=None):
    with connect(db_path) as conn:
        row = conn.execute("SELECT data FROM photo_store WHERE path = ?", (str(path),)).fetchone()
    return bytes(row["data"]) if row else None


def move_photo_blob(old_path, new_path, db_path=None):
    """Re-key a stored photo. Returns True if there was one to move."""
    with connect(db_path) as conn:
        row = conn.execute("SELECT data FROM photo_store WHERE path = ?", (str(old_path),)).fetchone()
        if row is None:
            return False
        conn.execute("INSERT OR REPLACE INTO photo_store (path, data) VALUES (?, ?)",
                     (str(new_path), row["data"]))
        if str(old_path) != str(new_path):
            conn.execute("DELETE FROM photo_store WHERE path = ?", (str(old_path),))
        return True


def delete_photo_blob(path, db_path=None):
    with connect(db_path) as conn:
        conn.execute("DELETE FROM photo_store WHERE path = ?", (str(path),))


# ---------------------------------------------------------------- subjects
def add_subject(name, db_path=None):
    name = _clean(name, "Subject name")
    try:
        with connect(db_path) as conn:
            return conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,)).lastrowid
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Subject '{name}' already exists.") from exc


def list_subjects(db_path=None):
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT id, name FROM subjects ORDER BY name")]


def update_subject(subject_id, name, db_path=None):
    """Rename a subject. Its attendance records stay attached to it."""
    name = _clean(name, "Subject name")
    try:
        with connect(db_path) as conn:
            return conn.execute("UPDATE subjects SET name = ? WHERE id = ?", (name, subject_id)).rowcount > 0
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Subject '{name}' already exists.") from exc


def delete_subject(subject_id, db_path=None):
    """PERMANENTLY delete a subject and all attendance recorded for it."""
    with connect(db_path) as conn:
        conn.execute("DELETE FROM attendance WHERE subject_id = ?", (subject_id,))
        return conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,)).rowcount > 0


# ------------------------------------------------------------------- staff
def add_staff(username, password_hash, role, db_path=None):
    try:
        with connect(db_path) as conn:
            return conn.execute(
                "INSERT INTO staff (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            ).lastrowid
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Username '{username}' already exists.") from exc


def get_staff(username, db_path=None):
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM staff WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_staff_by_id(staff_id, db_path=None):
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()
    return dict(row) if row else None


def update_staff(staff_id, username, role, password_hash=None, db_path=None):
    """Change a username and role; the password only changes when a new hash is given."""
    sets, params = ["username = ?", "role = ?"], [username, role]
    if password_hash is not None:
        sets.append("password_hash = ?")
        params.append(password_hash)
    params.append(staff_id)
    try:
        with connect(db_path) as conn:
            return conn.execute(f"UPDATE staff SET {', '.join(sets)} WHERE id = ?", params).rowcount > 0
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Username '{username}' already exists.") from exc


def delete_staff(staff_id, db_path=None):
    with connect(db_path) as conn:
        return conn.execute("DELETE FROM staff WHERE id = ?", (staff_id,)).rowcount > 0


def count_staff(role=None, db_path=None):
    query, params = "SELECT COUNT(*) FROM staff", []
    if role:
        query += " WHERE role = ?"
        params.append(role)
    with connect(db_path) as conn:
        return conn.execute(query, params).fetchone()[0]


def list_staff(db_path=None):
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT id, username, role FROM staff ORDER BY username")]


# -------------------------------------------------------------- attendance
def get_attendance(start_date=None, end_date=None, subject_id=None,
                   class_name=None, roll_no=None, db_path=None):
    """Attendance rows joined with student and subject details.

    Dates are 'YYYY-MM-DD' strings (inclusive). Newest first.
    """
    query = """
        SELECT s.roll_no, s.name, s.class_name, sub.name AS subject, a.date, a.time
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE 1 = 1
    """
    params = []
    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
    if subject_id:
        query += " AND a.subject_id = ?"
        params.append(subject_id)
    if class_name:
        query += " AND s.class_name = ?"
        params.append(class_name)
    if roll_no:
        query += " AND s.roll_no = ?"
        params.append(str(roll_no).strip())
    query += " ORDER BY a.date DESC, a.time DESC"
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]




def get_attendance_summary(student_id, db_path=None):
    """Per-subject attendance for one student.

    "Classes held" for a subject = the number of days on which anyone was marked
    present for it, counted from the day the student was registered. Subjects with
    no classes yet are left out.
    """
    with connect(db_path) as conn:
        student = conn.execute(
            "SELECT date(created_at) AS since FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if student is None:
            return []
        rows = conn.execute(
            """
            SELECT sub.name AS subject,
                   (SELECT COUNT(DISTINCT a.date) FROM attendance a
                     WHERE a.subject_id = sub.id AND a.date >= ?) AS total,
                   (SELECT COUNT(*) FROM attendance a
                     WHERE a.subject_id = sub.id AND a.student_id = ?) AS attended
            FROM subjects sub
            ORDER BY sub.name
            """,
            (student["since"], student_id),
        ).fetchall()
    summary = []
    for row in rows:
        if row["total"] == 0:
            continue
        attended = min(row["attended"], row["total"])
        summary.append({
            "subject": row["subject"],
            "attended": attended,
            "total": row["total"],
            "percent": round(100 * attended / row["total"], 1),
        })
    return summary


def get_attendance_history(student_id, db_path=None):
    """Every class held for one student, newest first, marked present or absent.

    A class counts as "held" when anyone was marked present for that subject on that
    day (counted from the day the student was registered). Each row is a dict with
    subject, date, time (None when absent) and present (True or False).
    """
    with connect(db_path) as conn:
        student = conn.execute(
            "SELECT date(created_at) AS since FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if student is None:
            return []
        rows = conn.execute(
            """
            SELECT sub.name AS subject, d.date AS date, a.time AS time
            FROM (SELECT DISTINCT subject_id, date FROM attendance WHERE date >= ?) d
            JOIN subjects sub ON sub.id = d.subject_id
            LEFT JOIN attendance a
                   ON a.subject_id = d.subject_id AND a.date = d.date AND a.student_id = ?
            ORDER BY d.date DESC, sub.name
            """,
            (student["since"], student_id),
        ).fetchall()
    return [
        {"subject": r["subject"], "date": r["date"], "time": r["time"], "present": r["time"] is not None}
        for r in rows
    ]