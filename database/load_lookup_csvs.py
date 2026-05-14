#!/usr/bin/env python3
"""
Populate SQLite lookup / ocean tables from CSVs.

  portcode_portcity.csv     -> portcode_portcity  (optional if file missing)
  dischargeport_country.csv -> dischargeport_country
  countrycode_country.csv   -> countrycode_country
  470OceanRatesExtract.csv  -> ocean_rates_extract
  excel_orig/otr_transit_lookup.csv -> otr_transit_lookup

Each row gets is_active = 1. Lookup tables are replaced on each run (DROP + CREATE + INSERT)
except you can use --merge-portcode to upsert port codes only (no DROP for that table).

Data directory resolution (first match wins):
  1. COSTINGS_DATA_DIR environment variable (absolute or relative path)
  2. --data-dir PATH
  3. <project>/data
  4. <project>/delete_data   (if you renamed data/)

From project root:
  python database/load_lookup_csvs.py
  python database/load_lookup_csvs.py --data-dir delete_data

Database: COSTINGS_DB_PATH if set, else <project_root>/database/costings.db
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _db_path() -> Path:
    return Path(os.environ.get("COSTINGS_DB_PATH", str(_project_root() / "database" / "costings.db")))


def _resolve_data_dir(cli_dir: str | None) -> Path | None:
    if cli_dir:
        p = Path(cli_dir).expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        return p if p.is_dir() else None
    env = (os.environ.get("COSTINGS_DATA_DIR") or "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_absolute():
            p = _project_root() / p
        if p.is_dir():
            return p
    root = _project_root()
    for name in ("data", "delete_data"):
        p = root / name
        if p.is_dir():
            return p
    return None


def _qident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_portcode_portcity(conn: sqlite3.Connection, path: Path, *, merge_only: bool = False) -> int:
    if merge_only:
        n = 0
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for raw in csv.DictReader(f, skipinitialspace=True):
                pc = str(raw.get("PortCode", raw.get("portcode", ""))).strip()
                if not pc:
                    continue
                city = str(raw.get("PortCity", raw.get("port_city", ""))).strip()
                conn.execute(
                    "INSERT OR REPLACE INTO portcode_portcity (PortCode, PortCity, is_active) VALUES (?, ?, 1)",
                    (pc, city),
                )
                n += 1
        return n

    conn.execute("DROP TABLE IF EXISTS portcode_portcity")
    conn.execute(
        """
        CREATE TABLE portcode_portcity (
            PortCode TEXT NOT NULL PRIMARY KEY,
            PortCity TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    n = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f, skipinitialspace=True):
            pc = str(raw.get("PortCode", raw.get("portcode", ""))).strip()
            if not pc:
                continue
            city = str(raw.get("PortCity", raw.get("port_city", ""))).strip()
            conn.execute(
                "INSERT OR REPLACE INTO portcode_portcity (PortCode, PortCity, is_active) VALUES (?, ?, 1)",
                (pc, city),
            )
            n += 1
    return n


def load_dischargeport_country(conn: sqlite3.Connection, path: Path) -> int:
    conn.execute("DROP TABLE IF EXISTS dischargeport_country")
    conn.execute(
        """
        CREATE TABLE dischargeport_country (
            discharge_port TEXT NOT NULL PRIMARY KEY,
            country TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    n = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f, skipinitialspace=True):
            dp = str(raw.get("dischargePort", "")).strip()
            if not dp:
                continue
            co = str(raw.get("Country", "")).strip()
            conn.execute(
                "INSERT OR REPLACE INTO dischargeport_country (discharge_port, country, is_active) VALUES (?, ?, 1)",
                (dp, co),
            )
            n += 1
    return n


def load_countrycode_country(conn: sqlite3.Connection, path: Path) -> int:
    conn.execute("DROP TABLE IF EXISTS countrycode_country")
    conn.execute(
        """
        CREATE TABLE countrycode_country (
            countrycode TEXT NOT NULL PRIMARY KEY,
            country TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    n = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f, skipinitialspace=True):
            cc = str(raw.get("countrycode", "")).strip()
            if not cc:
                continue
            name = str(raw.get("country", "")).strip()
            conn.execute(
                "INSERT OR REPLACE INTO countrycode_country (countrycode, country, is_active) VALUES (?, ?, 1)",
                (cc, name),
            )
            n += 1
    return n


def load_ocean_rates_extract(conn: sqlite3.Connection, path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        if not reader.fieldnames:
            raise SystemExit(f"No header row in {path}")
        cols = [h for h in reader.fieldnames if h is not None and str(h).strip() != ""]

    conn.execute("DROP TABLE IF EXISTS ocean_rates_extract")
    col_defs = ", ".join(f"{_qident(c)} TEXT" for c in cols)
    insert_cols = ", ".join(_qident(c) for c in cols)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"""
        CREATE TABLE ocean_rates_extract (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {col_defs},
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    sql = f"INSERT INTO ocean_rates_extract ({insert_cols}, is_active) VALUES ({placeholders}, 1)"

    n = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for raw in reader:
            row = ["" if raw.get(c) is None else str(raw.get(c, "")) for c in cols]
            conn.execute(sql, row)
            n += 1
    return n


def load_otr_transit_lookup(conn: sqlite3.Connection, path: Path) -> int:
    conn.execute("DROP TABLE IF EXISTS otr_transit_lookup")
    conn.execute(
        """
        CREATE TABLE otr_transit_lookup (
            origin_city TEXT NOT NULL,
            dest_port TEXT NOT NULL,
            lh REAL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            PRIMARY KEY (origin_city, dest_port)
        )
        """
    )
    n = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f, skipinitialspace=True):
            oc = str(raw.get("ORIGIN_CITY", "")).strip()
            dp = str(raw.get("DEST_PORT", "")).strip()
            if not oc or not dp:
                continue
            lh_s = str(raw.get("LH", "")).strip()
            try:
                lh = float(lh_s) if lh_s else None
            except ValueError:
                lh = None
            conn.execute(
                "INSERT OR REPLACE INTO otr_transit_lookup (origin_city, dest_port, lh, is_active) VALUES (?, ?, ?, 1)",
                (oc, dp, lh),
            )
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Populate lookup / ocean tables from CSVs.")
    ap.add_argument(
        "--data-dir",
        metavar="PATH",
        help="Folder containing the CSVs (default: data, delete_data, or COSTINGS_DATA_DIR)",
    )
    ap.add_argument(
        "--merge-portcode",
        action="store_true",
        help="Upsert portcode_portcity only (table must already exist); do not DROP it.",
    )
    args = ap.parse_args()

    data = _resolve_data_dir(args.data_dir)
    if data is None:
        print(
            "No data directory found. Create ./data or ./delete_data with the CSVs, or set "
            "COSTINGS_DATA_DIR / pass --data-dir.",
            file=sys.stderr,
        )
        return 1

    db_path = _db_path()
    paths_required = {
        "dischargeport_country": data / "dischargeport_country.csv",
        "countrycode_country": data / "countrycode_country.csv",
        "470OceanRatesExtract": data / "470OceanRatesExtract.csv",
        "otr_transit_lookup": data / "excel_orig" / "otr_transit_lookup.csv",
    }
    missing = [k for k, p in paths_required.items() if not p.is_file()]
    if missing:
        for k in missing:
            print(f"Missing CSV ({k}): {paths_required[k]}", file=sys.stderr)
        return 1

    path_portcode = data / "portcode_portcity.csv"
    has_portcode = path_portcode.is_file()

    print(f"Database: {db_path}")
    print(f"Data dir: {data}")
    conn = _connect(db_path)
    try:
        n_pc = 0
        if has_portcode:
            n_pc = load_portcode_portcity(conn, path_portcode, merge_only=args.merge_portcode)
        n1 = load_dischargeport_country(conn, paths_required["dischargeport_country"])
        n2 = load_countrycode_country(conn, paths_required["countrycode_country"])
        n3 = load_ocean_rates_extract(conn, paths_required["470OceanRatesExtract"])
        n4 = load_otr_transit_lookup(conn, paths_required["otr_transit_lookup"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if has_portcode:
        print(f"portcode_portcity:     {n_pc} rows")
    else:
        print("portcode_portcity:     (skipped — no portcode_portcity.csv)")
    print(f"dischargeport_country: {n1} rows")
    print(f"countrycode_country:   {n2} rows")
    print(f"ocean_rates_extract:   {n3} rows")
    print(f"otr_transit_lookup:    {n4} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
