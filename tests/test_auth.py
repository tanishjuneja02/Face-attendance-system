import pytest

from core import auth, database


def test_hash_does_not_contain_the_password():
    assert "secret123" not in auth.hash_password("secret123")


def test_same_password_gives_different_hashes():
    # A random salt is used each time.
    assert auth.hash_password("secret123") != auth.hash_password("secret123")


def test_verify_password():
    stored = auth.hash_password("secret123")
    assert auth.verify_password("secret123", stored) is True
    assert auth.verify_password("wrong-pass", stored) is False


@pytest.mark.parametrize("bad", ["", "plain-text", "a$b$c", "md5$1$00$00", "pbkdf2$x$zz$zz"])
def test_malformed_hash_never_verifies(bad):
    assert auth.verify_password("secret123", bad) is False


def test_create_staff_stores_a_hash_not_the_password(db_path):
    auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    stored = database.get_staff("mam", db_path)["password_hash"]
    assert stored != "secret123"
    assert stored.startswith("pbkdf2$")


def test_authenticate_success_and_failures(db_path):
    auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    user = auth.authenticate("mam", "secret123", db_path=db_path)
    assert user["username"] == "mam" and user["role"] == "teacher"
    assert "password_hash" not in user
    assert auth.authenticate("mam", "wrong-pass", db_path=db_path) is None
    assert auth.authenticate("nobody", "secret123", db_path=db_path) is None


def test_duplicate_username_is_rejected(db_path):
    auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    with pytest.raises(database.DuplicateError):
        auth.create_staff("mam", "another-pass", "admin", db_path=db_path)


def test_invalid_role_username_and_short_password(db_path):
    with pytest.raises(ValueError):
        auth.create_staff("x", "secret123", "student", db_path=db_path)
    with pytest.raises(ValueError):
        auth.create_staff("  ", "secret123", "teacher", db_path=db_path)
    with pytest.raises(ValueError):
        auth.create_staff("x", "123", "teacher", db_path=db_path)


def test_has_admin_ignores_teachers(db_path):
    assert auth.has_admin(db_path) is False
    auth.create_staff("mam", "secret123", "teacher", db_path=db_path)
    assert auth.has_admin(db_path) is False
    auth.create_staff("boss", "secret123", "admin", db_path=db_path)
    assert auth.has_admin(db_path) is True
