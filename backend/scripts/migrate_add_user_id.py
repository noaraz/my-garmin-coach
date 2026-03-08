from __future__ import annotations

"""Migration: add user_id columns and create auth tables.

Adds user_id FK column to workouttemplate, scheduledworkout, hrzone, and
pacezone tables. Sets all existing rows to user_id = 1 (the admin user who
owns all pre-auth data). Also creates the user and invitecode tables if they
do not yet exist.

Safe to run multiple times (idempotent).

Usage:
    python scripts/migrate_add_user_id.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("/data/garmincoach.db")


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


def run_migration(db_path: Path) -> None:
    print(f"Connecting to {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # 1. Create user table if not present
    # ------------------------------------------------------------------
    if not table_exists(cursor, "user"):
        print("Creating 'user' table ...")
        cursor.execute(
            """
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        print("  Created 'user' table.")
    else:
        print("'user' table already exists, skipping.")

    # ------------------------------------------------------------------
    # 2. Create invitecode table if not present
    # ------------------------------------------------------------------
    if not table_exists(cursor, "invitecode"):
        print("Creating 'invitecode' table ...")
        cursor.execute(
            """
            CREATE TABLE invitecode (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                created_by INTEGER NOT NULL REFERENCES user(id),
                used_by INTEGER REFERENCES user(id),
                used_at TEXT
            )
            """
        )
        print("  Created 'invitecode' table.")
    else:
        print("'invitecode' table already exists, skipping.")

    # ------------------------------------------------------------------
    # 3. Add user_id columns (idempotent — checks before ALTER)
    # ------------------------------------------------------------------
    tables_to_migrate: list[str] = [
        "workouttemplate",
        "scheduledworkout",
        "hrzone",
        "pacezone",
    ]

    for table in tables_to_migrate:
        if not table_exists(cursor, table):
            print(f"Table '{table}' does not exist, skipping user_id column add.")
            continue

        if column_exists(cursor, table, "user_id"):
            print(f"Column user_id already exists in '{table}', skipping.")
        else:
            print(f"Adding user_id column to '{table}' ...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES user(id)")
            print(f"  Added user_id to '{table}'.")

        # Set existing NULL user_id rows to 1 (legacy admin)
        cursor.execute(
            f"UPDATE {table} SET user_id = 1 WHERE user_id IS NULL"  # noqa: S608
        )
        updated = cursor.rowcount
        if updated:
            print(f"  Set user_id=1 on {updated} existing rows in '{table}'.")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Nothing to migrate.")
    else:
        run_migration(DB_PATH)
