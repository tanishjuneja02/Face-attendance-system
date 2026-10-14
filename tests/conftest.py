"""Shared test fixtures. Every test gets its own empty temporary database."""
import pytest

from core import database


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    database.init_db(path)
    return path


@pytest.fixture
def student_id(db_path):
    """One registered student with a fake 3-number face embedding."""
    return database.add_student(
        "101", "Rahul Sharma", "CS-3A", embedding=[1.0, 0.0, 0.0], db_path=db_path
    )


@pytest.fixture
def subject_id(db_path):
    return database.list_subjects(db_path)[0]["id"]
