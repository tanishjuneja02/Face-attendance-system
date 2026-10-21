"""Check that the hosted (Turso) database works, before you deploy.

Run from the project folder (PowerShell example):
    $env:TURSO_DATABASE_URL="libsql://your-db-your-org.turso.io"
    $env:TURSO_AUTH_TOKEN="your-token"
    python scripts/check_turso.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import database  # noqa: E402

if not database.using_remote():
    sys.exit("TURSO_DATABASE_URL is not set, so the local SQLite file would be used.")

try:
    database.init_db()
    print("Connected to the hosted database and the tables are ready.")
    print("Students:", database.count_students(), "| Subjects:", len(database.list_subjects()))
except Exception as exc:
    sys.exit(f"Could not use the hosted database: {exc}")