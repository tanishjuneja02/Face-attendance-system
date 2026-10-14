"""Staff accounts: password hashing (standard library only) and login checks."""
import hashlib
import hmac
import os

from core import database

ROLES = ("teacher", "admin")
MIN_PASSWORD_LENGTH = 6
ITERATIONS = 200_000


def hash_password(password):
    """Return 'pbkdf2$iterations$salt$hash' (a new random salt every time)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """True if the password matches the stored hash. Bad formats return False."""
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_staff(username, password, role, db_path=None):
    """Create a teacher or admin account and return its id."""
    username = (username or "").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return database.add_staff(username, hash_password(password), role, db_path=db_path)


def update_staff(staff_id, username, role, new_password=None, db_path=None):
    """Edit an account. Leave new_password empty to keep the current password."""
    username = (username or "").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}.")
    if new_password and len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    current = database.get_staff_by_id(staff_id, db_path=db_path)
    if current is None:
        raise ValueError("Account not found.")
    if current["role"] == "admin" and role != "admin" and database.count_staff("admin", db_path=db_path) <= 1:
        raise ValueError("You cannot remove the last admin.")
    password_hash = hash_password(new_password) if new_password else None
    return database.update_staff(staff_id, username, role, password_hash, db_path=db_path)


def delete_staff(staff_id, db_path=None):
    """Delete an account. The last admin cannot be deleted."""
    current = database.get_staff_by_id(staff_id, db_path=db_path)
    if current is None:
        raise ValueError("Account not found.")
    if current["role"] == "admin" and database.count_staff("admin", db_path=db_path) <= 1:
        raise ValueError("You cannot delete the last admin.")
    return database.delete_staff(staff_id, db_path=db_path)


def authenticate(username, password, db_path=None):
    """Return {'id', 'username', 'role'} for valid credentials, else None."""
    staff = database.get_staff((username or "").strip(), db_path=db_path)
    if staff and verify_password(password or "", staff["password_hash"]):
        return {"id": staff["id"], "username": staff["username"], "role": staff["role"]}
    return None


def has_admin(db_path=None):
    return database.count_staff(role="admin", db_path=db_path) > 0
