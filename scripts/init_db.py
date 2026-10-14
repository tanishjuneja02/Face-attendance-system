"""Create the database and the first admin from the command line.

Run from the project folder:  python scripts/init_db.py
(You can also create the first admin from the Staff Login page.)
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import auth, database  # noqa: E402

database.init_db()
print(f"Database ready: {database.DEFAULT_DB_PATH}")

if auth.has_admin():
    print("An admin account already exists. Nothing more to do.")
else:
    username = input("Choose an admin username: ").strip()
    password = getpass.getpass("Choose a password (min 6 characters): ")
    auth.create_staff(username, password, "admin")
    print(f"Admin '{username}' created.")
