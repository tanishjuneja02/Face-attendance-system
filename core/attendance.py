"""Attendance marking rules: one mark per student, per subject, per day."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.database import connect

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(IST)


def to_12h(time_str):
    """'14:30:05' -> '2:30:05 PM'. Times stay 24-hour in the database; this is display only."""
    try:
        return datetime.strptime(time_str, "%H:%M:%S").strftime("%I:%M:%S %p").lstrip("0")
    except (ValueError, TypeError):
        return time_str


@dataclass
class MarkResult:
    status: str  # "marked" or "already_marked"
    date: str
    time: str

    @property
    def marked(self):
        return self.status == "marked"


def mark_attendance(student_id, subject_id, now=None, db_path=None):
    """Mark a student present. A repeat for the same subject and day is not added again."""
    now = now or now_ist()
    date, time = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    with connect(db_path) as conn:
        student = conn.execute(
            "SELECT is_deleted FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if student is None:
            raise ValueError(f"Unknown student id {student_id}.")
        if student["is_deleted"]:
            raise ValueError(f"Student id {student_id} is deactivated.")
        if conn.execute("SELECT 1 FROM subjects WHERE id = ?", (subject_id,)).fetchone() is None:
            raise ValueError(f"Unknown subject id {subject_id}.")

        existing = conn.execute(
            "SELECT time FROM attendance WHERE student_id = ? AND subject_id = ? AND date = ?",
            (student_id, subject_id, date),
        ).fetchone()
        if existing:
            return MarkResult("already_marked", date, existing["time"])

        conn.execute(
            "INSERT INTO attendance (student_id, subject_id, date, time) VALUES (?, ?, ?, ?)",
            (student_id, subject_id, date, time),
        )
    return MarkResult("marked", date, time)
