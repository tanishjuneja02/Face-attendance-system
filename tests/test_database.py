import sqlite3

import pytest

from core import attendance, database


def test_init_creates_all_tables(db_path):
    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"students", "staff", "subjects", "attendance"} <= names


def test_default_subjects_are_added(db_path):
    names = {s["name"] for s in database.list_subjects(db_path)}
    assert names == set(database.DEFAULT_SUBJECTS)


def test_init_twice_does_not_duplicate_subjects(db_path):
    database.init_db(db_path)
    assert len(database.list_subjects(db_path)) == len(database.DEFAULT_SUBJECTS)


def test_add_and_get_student(db_path):
    sid = database.add_student("102", " Tanish ", "CS-3A", db_path=db_path)
    student = database.get_student(sid, db_path)
    assert student["roll_no"] == "102"
    assert student["name"] == "Tanish"  # spaces trimmed
    assert student["class_name"] == "CS-3A"
    assert student["embedding"] is None


def test_embedding_round_trip(db_path):
    sid = database.add_student("103", "Ann", "CS-3B", embedding=[0.1, 0.2, 0.3], db_path=db_path)
    assert database.get_student(sid, db_path)["embedding"] == [0.1, 0.2, 0.3]


def test_get_student_by_roll(db_path, student_id):
    assert database.get_student_by_roll("101", db_path)["id"] == student_id
    assert database.get_student_by_roll("999", db_path) is None


def test_duplicate_roll_number_is_rejected(db_path, student_id):
    with pytest.raises(database.DuplicateError):
        database.add_student("101", "Someone Else", "CS-3B", db_path=db_path)


@pytest.mark.parametrize("roll, name, cls", [("", "A", "X"), ("1", "  ", "X"), ("1", "A", "")])
def test_blank_fields_are_rejected(db_path, roll, name, cls):
    with pytest.raises(ValueError):
        database.add_student(roll, name, cls, db_path=db_path)


def test_list_students_can_filter_by_class(db_path):
    database.add_student("1", "A", "CS-3A", db_path=db_path)
    database.add_student("2", "B", "CS-3B", db_path=db_path)
    assert [s["name"] for s in database.list_students("CS-3B", db_path)] == ["B"]
    assert len(database.list_students(db_path=db_path)) == 2


def test_only_students_with_faces_are_returned_for_matching(db_path, student_id):
    database.add_student("200", "No Face", "CS-3A", db_path=db_path)
    with_faces = database.get_students_with_embeddings(db_path)
    assert [s["id"] for s in with_faces] == [student_id]


def test_deleting_a_student_removes_their_attendance(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, db_path=db_path)
    assert database.delete_student(student_id, db_path) is True
    assert database.get_attendance(db_path=db_path) == []
    assert database.delete_student(student_id, db_path) is False


def test_add_subject_and_reject_duplicate(db_path):
    database.add_subject("Electronics", db_path)
    assert "Electronics" in {s["name"] for s in database.list_subjects(db_path)}
    with pytest.raises(database.DuplicateError):
        database.add_subject("Electronics", db_path)


# ------------------------------------------------ soft delete (deactivate / restore)
def test_deactivated_student_is_hidden_but_not_gone(db_path, student_id):
    assert database.deactivate_student(student_id, db_path) is True
    assert database.list_students(db_path=db_path) == []
    assert [s["id"] for s in database.list_students(db_path=db_path, deleted=True)] == [student_id]
    assert database.get_students_with_embeddings(db_path) == []  # no longer matched by face
    assert database.get_student(student_id, db_path)["is_deleted"] == 1


def test_restore_brings_the_student_back(db_path, student_id):
    database.deactivate_student(student_id, db_path)
    assert database.restore_student(student_id, db_path) is True
    assert [s["id"] for s in database.list_students(db_path=db_path)] == [student_id]
    assert [s["id"] for s in database.get_students_with_embeddings(db_path)] == [student_id]
    assert database.list_students(db_path=db_path, deleted=True) == []


def test_deactivate_keeps_attendance_history(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, db_path=db_path)
    database.deactivate_student(student_id, db_path)
    assert len(database.get_attendance(db_path=db_path)) == 1


def test_deactivate_unknown_student_returns_false(db_path):
    assert database.deactivate_student(9999, db_path) is False
    assert database.restore_student(9999, db_path) is False


def test_deactivated_roll_number_cannot_be_reused(db_path, student_id):
    database.deactivate_student(student_id, db_path)
    with pytest.raises(database.DuplicateError):
        database.add_student("101", "Newcomer", "CS-3A", db_path=db_path)


def test_permanent_delete_after_deactivate(db_path, student_id):
    database.deactivate_student(student_id, db_path)
    assert database.delete_student(student_id, db_path) is True
    assert database.get_student(student_id, db_path) is None
    assert database.list_students(db_path=db_path, deleted=True) == []


def test_counts_only_include_active_students(db_path, subject_id):
    a = database.add_student("1", "A", "X", db_path=db_path)
    b = database.add_student("2", "B", "X", db_path=db_path)
    attendance.mark_attendance(a, subject_id, db_path=db_path)
    attendance.mark_attendance(b, subject_id, db_path=db_path)
    today = attendance.now_ist().strftime("%Y-%m-%d")
    assert database.count_students(db_path) == 2
    assert database.count_present_on(today, db_path) == 2
    database.deactivate_student(b, db_path)
    assert database.count_students(db_path) == 1
    assert database.count_present_on(today, db_path) == 1
    assert database.count_present_on("2000-01-01", db_path) == 0


def test_old_database_without_is_deleted_is_upgraded(tmp_path):
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.executescript(
        """
        CREATE TABLE students (
            id INTEGER PRIMARY KEY AUTOINCREMENT, roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, class_name TEXT NOT NULL, photo_path TEXT, embedding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO students (roll_no, name, class_name) VALUES ('7', 'Old Student', 'CS-1A');
        """
    )
    conn.commit()
    conn.close()

    database.init_db(old)
    database.init_db(old)  # running twice is safe
    students = database.list_students(db_path=old)
    assert [s["name"] for s in students] == ["Old Student"]
