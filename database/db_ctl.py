"""Cleanly shut down or start up the costings SQLite database.

Usage:
    python db_ctl.py stop      # checkpoint WAL, close connection, clean up -wal/-shm
    python db_ctl.py start     # open the database (re-enables WAL mode)
    python db_ctl.py status    # show whether -wal/-shm files exist
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "costings.db"


def stop():
    """Checkpoint the WAL and close cleanly — removes -wal and -shm files."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.close()
    print(f"Database shut down cleanly: {DB_PATH}")
    for suffix in ("-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + suffix)
        if p.exists():
            print(f"  Removed {p.name}")
        else:
            print(f"  {p.name} already gone")


def start():
    """Open the database and re-enable WAL mode."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()
    print(f"Database started (WAL mode enabled): {DB_PATH}")


def status():
    """Show current state of the database files."""
    print(f"Database: {DB_PATH}  {'EXISTS' if DB_PATH.exists() else 'MISSING'}")
    for suffix in ("-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + suffix)
        if p.exists():
            size = p.stat().st_size
            print(f"  {p.name}: {size:,} bytes")
        else:
            print(f"  {p.name}: not present")


if __name__ == "__main__":
    cmds = {"stop": stop, "start": start, "status": status}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(f"Usage: python {Path(__file__).name} [stop|start|status]")
        sys.exit(1)
    cmds[sys.argv[1]]()
