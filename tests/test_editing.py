"""Editing students, subjects and staff accounts (admin features)."""
import pytest

from core import attendance, auth, database, photos


# ---------------------------------------------------------------- students
def test_update_student_changes_details_and_keeps_face(db_path, student_id):
    database.update_student(student_id, " 201 ", "Rahul S", "CS-4A", db_path=db_path)
    s = database.get_student(student_id, db_path)
    assert (s["roll_no"], s["name"], s["class_name"]) == ("201", "Rahul S", "CS-4A")
    assert s["embedding"] == [1.0, 0.0, 0.0]  # face untouched


def test_update_student_can_replace_face(db_path, student_id):
    database.update_student(student_id, "101", "Rahul", "CS-3A", embedding=[0.0, 1.0, 0.0], db_path=db_path)
    assert database.get_student(student_id, db_path)["embedding"] == [0.0, 1.0, 0.0]


def test_update_student_rejects_duplicate_roll(db_path, student_id):
    other = database.add_student("102", "Ann", "CS-3A", db_path=db_path)
    with pytest.raises(database.DuplicateError):
        database.update_student(other, "101", "Ann", "CS-3A", db_path=db_path)


def test_update_student_rejects_empty_fields(db_path, student_id):
    with pytest.raises(ValueError):
        database.update_student(student_id, "101", "  ", "CS-3A", db_path=db_path)


def test_rename_photo_moves_the_file(tmp_path):
    old = tmp_path / "101.jpg"
    old.write_bytes(b"x")
    new = photos.rename_photo(str(old), "205", photo_dir=tmp_path)
    assert new.endswith("205.jpg") and not old.exists()
    assert (tmp_path / "205.jpg").exists()


# ---------------------------------------------------------------- subjects
def test_rename_subject_keeps_attendance(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, db_path=db_path)
    database.update_subject(subject_id, "Maths", db_path=db_path)
    rows = database.get_attendance(db_path=db_path)
    assert rows[0]["subject"] == "Maths"


def test_rename_subject_rejects_duplicate(db_path):
    first, second = database.list_subjects(db_path)[:2]
    with pytest.raises(database.DuplicateError):
        database.update_subject(first["id"], second["name"], db_path=db_path)


def test_delete_subject_removes_its_attendance(db_path, student_id, subject_id):
    attendance.mark_attendance(student_id, subject_id, db_path=db_path)
    assert database.delete_subject(subject_id, db_path=db_path) is True
    assert database.get_attendance(db_path=db_path) == []


# ------------------------------------------------------------------- staff
def test_update_staff_keeps_password_when_blank(db_path):
    sid = auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    auth.update_staff(sid, "madam", "teacher", None, db_path=db_path)
    assert auth.authenticate("madam", "secret123", db_path=db_path) is not None


def test_update_staff_changes_password_and_role(db_path):
    auth.create_staff("boss", "adminpass", "admin", db_path=db_path)
    sid = auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    auth.update_staff(sid, "mam", "admin", "newpass99", db_path=db_path)
    user = auth.authenticate("mam", "newpass99", db_path=db_path)
    assert user["role"] == "admin"
    assert auth.authenticate("mam", "secret123", db_path=db_path) is None


def test_update_staff_validates(db_path):
    sid = auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    with pytest.raises(ValueError):
        auth.update_staff(sid, "mam", "teacher", "abc", db_path=db_path)  # too short
    with pytest.raises(ValueError):
        auth.update_staff(sid, "mam", "principal", None, db_path=db_path)  # bad role
    with pytest.raises(ValueError):
        auth.update_staff(sid, "  ", "teacher", None, db_path=db_path)


def test_update_staff_rejects_duplicate_username(db_path):
    auth.create_staff("a", "secret123", "teacher", db_path=db_path)
    b = auth.create_staff("b", "secret123", "teacher", db_path=db_path)
    with pytest.raises(database.DuplicateError):
        auth.update_staff(b, "a", "teacher", None, db_path=db_path)


def test_last_admin_cannot_be_demoted_or_deleted(db_path):
    sid = auth.create_staff("boss", "adminpass", "admin", db_path=db_path)
    with pytest.raises(ValueError):
        auth.update_staff(sid, "boss", "teacher", None, db_path=db_path)
    with pytest.raises(ValueError):
        auth.delete_staff(sid, db_path=db_path)


def test_a_second_admin_can_be_deleted(db_path):
    auth.create_staff("boss", "adminpass", "admin", db_path=db_path)
    second = auth.create_staff("other", "adminpass", "admin", db_path=db_path)
    assert auth.delete_staff(second, db_path=db_path) is True
    assert database.get_staff("other", db_path) is None
