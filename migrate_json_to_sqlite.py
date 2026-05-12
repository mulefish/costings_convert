#!/usr/bin/env python3
"""
One-time migration: read the 6 JSON config files in data/ and populate costings.db.

Run from the project root:
    python migrate_json_to_sqlite.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "html"))

from database import DB_PATH, migrate_from_json  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"

if __name__ == "__main__":
    if DB_PATH.exists():
        print(f"Database already exists at {DB_PATH}")
        resp = input("Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            sys.exit(0)
        DB_PATH.unlink()
        print("Removed old database.")

    print(f"Migrating JSON files from {DATA_DIR} -> {DB_PATH} ...")
    migrate_from_json(DATA_DIR)
    print("Done.")
