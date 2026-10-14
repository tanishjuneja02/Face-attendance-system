from datetime import datetime

import pytest

from core import attendance, database


def at(day, hour=9, minute=0, second=0):
    return datetime(2026, 10, day, hour, minute, second, tzinfo=attendance.IST)


def test_first_mark_is_saved(db_path, student_id, subject_id):
    result = attendance.mark_attendance(student_id, subject_id, now=at(14, 9, 5, 7), db_path=db_path)
    assert result.marked is True
    assert (result.date, result.time) == ("2026-10-14", "09:05:07")
    assert len(database.get_attendance(db_path=db_path)) == 1


def test_second_mark_same_day_is_refused_and_keeps_first_time(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, now=at(14, 9, 0), db_path=db_path)
    again = attendance.mark_attendance(student_id, subject_id, now=at(14, 11, 30), db_path=db_path)
    assert again.status == "already_marked"
    assert again.time == "09:00:00"
    assert len(database.get_attendance(db_path=db_path)) == 1


def test_other_subject_same_day_is_allowed(db_path, student_id):
    maths, physics = database.list_subjects(db_path)[:2]
    attendance.mark_attendance(student_id, maths["id"], now=at(14), db_path=db_path)
    result = attendance.mark_attendance(student_id, physics["id"], now=at(14), db_path=db_path)
    assert result.marked is True


def test_same_subject_next_day_is_allowed(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, now=at(14), db_path=db_path)
    result = attendance.mark_attendance(student_id, subject_id, now=at(15), db_path=db_path)
    assert result.marked is True


def test_unknown_student_or_subject_raises(db_path, student_id, subject_id):
    with pytest.raises(ValueError):
        attendance.mark_attendance(9999, subject_id, db_path=db_path)
    with pytest.raises(ValueError):
        attendance.mark_attendance(student_id, 9999, db_path=db_path)


def test_now_ist_is_five_thirty_ahead_of_utc():
    assert attendance.now_ist().utcoffset().total_seconds() == 5.5 * 3600


def test_attendance_report_filters(db_path, subject_id):
    maths, physics = database.list_subjects(db_path)[:2]
    a = database.add_student("1", "Asha", "CS-3A", db_path=db_path)
    b = database.add_student("2", "Bilal", "CS-3B", db_path=db_path)
    attendance.mark_attendance(a, maths["id"], now=at(13), db_path=db_path)
    attendance.mark_attendance(a, physics["id"], now=at(14), db_path=db_path)
    attendance.mark_attendance(b, maths["id"], now=at(14), db_path=db_path)

    everything = database.get_attendance(db_path=db_path)
    assert len(everything) == 3
    assert everything[0]["date"] == "2026-10-14"  # newest first
    assert {"roll_no", "name", "class_name", "subject", "date", "time"} == set(everything[0])

    assert len(database.get_attendance(subject_id=maths["id"], db_path=db_path)) == 2
    assert len(database.get_attendance(class_name="CS-3B", db_path=db_path)) == 1
    assert len(database.get_attendance(roll_no="1", db_path=db_path)) == 2
    assert len(database.get_attendance(start_date="2026-10-14", db_path=db_path)) == 2
    assert len(database.get_attendance(end_date="2026-10-13", db_path=db_path)) == 1


def test_deactivated_student_cannot_be_marked(db_path, student_id, subject_id):
    database.deactivate_student(student_id, db_path)
    with pytest.raises(ValueError):
        attendance.mark_attendance(student_id, subject_id, db_path=db_path)
    database.restore_student(student_id, db_path)
    assert attendance.mark_attendance(student_id, subject_id, db_path=db_path).marked is True
