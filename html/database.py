import json
import os
import re
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH: Path = Path(os.environ.get("COSTINGS_DB_PATH", str(_ROOT / "database" / "costings.db")))

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.row_factory = sqlite3.Row
        _ensure_schema(_conn)
    return _conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    _ensure_is_active_columns(conn)
    conn.execute("DROP TABLE IF EXISTS ocean_costing_lanes")
    _ensure_themes_type_column(conn)
    _ensure_themes_seeded(conn)
    _ensure_document_cif_gri_column(conn)
    _ensure_drayage_gri_column(conn)
    _ensure_cif_regions_drop_brz_aus(conn)
    conn.commit()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS control_panel (
    key       TEXT PRIMARY KEY,
    value     REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS consolidation (
    region    TEXT PRIMARY KEY,
    bale      REAL NOT NULL DEFAULT 0,
    storage   REAL NOT NULL DEFAULT 0,
    month     REAL NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS consolidation_days_storage (
    id        INTEGER PRIMARY KEY CHECK (id = 1),
    days      REAL NOT NULL DEFAULT 14.0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS drayage (
    region     TEXT PRIMARY KEY,
    gri        REAL NOT NULL DEFAULT 0,
    line_haul  REAL NOT NULL DEFAULT 0,
    chas_split REAL NOT NULL DEFAULT 0,
    contrainer REAL NOT NULL DEFAULT 0,
    bale       REAL NOT NULL DEFAULT 0,
    ocean_base REAL NOT NULL DEFAULT 0,
    updated    TEXT NOT NULL DEFAULT '',
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS document_cif (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    country   TEXT NOT NULL,
    code      TEXT NOT NULL DEFAULT '',
    lc        REAL,
    ins       REAL,
    cont      REAL,
    com       REAL,
    cof       REAL,
    ciq_qc    REAL,
    gri       REAL NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usa_forwarding_cost (
    key       TEXT PRIMARY KEY,
    value     TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cif_regions (
    sort_order INTEGER PRIMARY KEY,
    region     TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL DEFAULT '',
    body       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS otr_rates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_city      TEXT NOT NULL DEFAULT '',
    origin_state     TEXT NOT NULL DEFAULT '',
    dest_city        TEXT NOT NULL DEFAULT '',
    dest_state       TEXT NOT NULL DEFAULT '',
    cargo_type       TEXT NOT NULL DEFAULT '',
    base_rate        REAL NOT NULL DEFAULT 0,
    update_date      TEXT NOT NULL DEFAULT '',
    expiration_date  TEXT NOT NULL DEFAULT '',
    prior_base_rate  REAL,
    is_active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS seam_tariffs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse   TEXT NOT NULL DEFAULT '',
    name        TEXT NOT NULL DEFAULT '',
    city        TEXT NOT NULL DEFAULT '',
    state       TEXT NOT NULL DEFAULT '',
    county      TEXT NOT NULL DEFAULT '',
    terms       TEXT NOT NULL DEFAULT '',
    verified    TEXT NOT NULL DEFAULT '',
    points      TEXT NOT NULL DEFAULT '',
    recv        TEXT NOT NULL DEFAULT '',
    strg        TEXT NOT NULL DEFAULT '',
    load        TEXT NOT NULL DEFAULT '',
    compr       TEXT NOT NULL DEFAULT '',
    class       TEXT NOT NULL DEFAULT '',
    mark        TEXT NOT NULL DEFAULT '',
    eff_date    TEXT NOT NULL DEFAULT '',
    bales       TEXT NOT NULL DEFAULT '',
    rail        TEXT NOT NULL DEFAULT '',
    ice_ref     TEXT NOT NULL DEFAULT '',
    capacity    TEXT NOT NULL DEFAULT '',
    cert_load   TEXT NOT NULL DEFAULT '',
    cert_compr  TEXT NOT NULL DEFAULT '',
    cert_mark   TEXT NOT NULL DEFAULT '',
    cert_recv   TEXT NOT NULL DEFAULT '',
    cert_strg   TEXT NOT NULL DEFAULT '',
    cert_class  TEXT NOT NULL DEFAULT '',
    min_storage TEXT NOT NULL DEFAULT '',
    basis_adj   TEXT NOT NULL DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS regions_and_ports (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse            TEXT NOT NULL DEFAULT '',
    name                 TEXT NOT NULL DEFAULT '',
    city                 TEXT NOT NULL DEFAULT '',
    state                TEXT NOT NULL DEFAULT '',
    region               TEXT NOT NULL DEFAULT '',
    export               TEXT NOT NULL DEFAULT '',
    port                 TEXT NOT NULL DEFAULT '',
    eso                  TEXT NOT NULL DEFAULT '',
    flat_bed_fees        TEXT NOT NULL DEFAULT '',
    late_fees            TEXT NOT NULL DEFAULT '',
    transportation_adjust TEXT NOT NULL DEFAULT '',
    misc_fees            TEXT NOT NULL DEFAULT '',
    consol_interest      TEXT NOT NULL DEFAULT '',
    is_active            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ocean_costing_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    city        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    country     TEXT NOT NULL DEFAULT '',
    logic       TEXT NOT NULL DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS themes (
    Country     TEXT NOT NULL,
    CountryAbbr TEXT NOT NULL PRIMARY KEY,
    Color       TEXT NOT NULL,
    "type"      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS portcode_portcity (
    PortCode  TEXT NOT NULL PRIMARY KEY,
    PortCity  TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dischargeport_country (
    discharge_port TEXT NOT NULL PRIMARY KEY,
    country        TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS countrycode_country (
    countrycode TEXT NOT NULL PRIMARY KEY,
    country     TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ocean_rates_extract (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    unOrig          TEXT,
    unVia           TEXT,
    unDest          TEXT,
    orig            TEXT,
    via             TEXT,
    dest            TEXT,
    dischargePort   TEXT,
    scacCode        TEXT,
    carrierName     TEXT,
    contractNumber  TEXT,
    rateType        TEXT,
    amendmentNumber TEXT,
    effectiveDate   TEXT,
    expirationDate  TEXT,
    updateTime      TEXT,
    "40FT"          TEXT,
    "40HC"          TEXT,
    "DTHC40FT"      TEXT,
    "DTHC40HC"      TEXT,
    "ALLIN40FT"     TEXT,
    "ALLIN40HC"     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS otr_transit_lookup (
    origin_city TEXT NOT NULL,
    dest_port   TEXT NOT NULL,
    lh          REAL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    PRIMARY KEY (origin_city, dest_port)
);
"""


_ALL_TABLES = (
    "control_panel", "consolidation", "consolidation_days_storage",
    "drayage", "document_cif", "usa_forwarding_cost", "cif_regions", "notes",
    "otr_rates", "seam_tariffs", "regions_and_ports", "ocean_costing_rules",
    "portcode_portcity", "dischargeport_country", "countrycode_country", "ocean_rates_extract", "otr_transit_lookup",
)


def _ensure_is_active_columns(conn: sqlite3.Connection) -> None:
    """Add is_active column to any existing table that lacks it (migration for existing DBs)."""
    for table in _ALL_TABLES:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info([{table}])").fetchall()}
        if "is_active" not in cols:
            conn.execute(f"ALTER TABLE [{table}] ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    conn.commit()


def _ensure_document_cif_gri_column(conn: sqlite3.Connection) -> None:
    """Add document_cif.gri for DBs created before that column existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_cif'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(document_cif)").fetchall()}
    if "gri" not in cols:
        conn.execute("ALTER TABLE document_cif ADD COLUMN gri REAL NOT NULL DEFAULT 0")
        conn.commit()


_RETIRED_CIF_REGIONS = frozenset({"BRZ", "AUS"})


def _ensure_cif_regions_drop_brz_aus(conn: sqlite3.Connection) -> None:
    """Remove retired BRZ/AUS rows from cif_regions and re-pack sort_order."""
    try:
        rows = conn.execute(
            "SELECT region FROM cif_regions ORDER BY sort_order"
        ).fetchall()
    except sqlite3.OperationalError:
        return
    if not rows:
        return
    regions = [str(r["region"]).strip() for r in rows]
    filtered = [r for r in regions if r and r not in _RETIRED_CIF_REGIONS]
    if len(filtered) == len(regions):
        return
    conn.execute("DELETE FROM cif_regions")
    conn.executemany(
        "INSERT INTO cif_regions (sort_order, region) VALUES (?, ?)",
        [(i, r) for i, r in enumerate(filtered)],
    )


def _ensure_drayage_gri_column(conn: sqlite3.Connection) -> None:
    """Add drayage.gri for DBs created before that column existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='drayage'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(drayage)").fetchall()}
    if "gri" not in cols:
        conn.execute("ALTER TABLE drayage ADD COLUMN gri REAL NOT NULL DEFAULT 0")
        conn.commit()


def _ensure_themes_type_column(conn: sqlite3.Connection) -> None:
    """Add themes.type column for DBs created before that field existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='themes'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(themes)").fetchall()}
    if "type" not in cols:
        conn.execute('ALTER TABLE themes ADD COLUMN "type" TEXT NOT NULL DEFAULT \'\'')
        conn.commit()


def _ensure_themes_seeded(conn: sqlite3.Connection) -> None:
    """One-time seed from chart colors (hex). Skips if themes already has rows."""
    row = conn.execute("SELECT COUNT(*) AS n FROM themes").fetchone()
    if row and int(row["n"] or row[0]) > 0:
        return
    # Order matches chart IDs 1–21; ES = El Salvador (green block with Latin America).
    seed: tuple[tuple[str, str, str, str], ...] = (
        ("China", "CN", "#FF0000", ""),
        ("Bangladesh", "BD", "#FFC000", ""),
        ("Pakistan", "PK", "#FFC000", ""),
        ("India", "IN", "#FFC000", ""),
        ("Vietnam", "VN", "#00B0F0", ""),
        ("Korea", "KO", "#00B0F0", ""),
        ("Japan", "JP", "#00B0F0", ""),
        ("Malaysia", "MA", "#00B0F0", ""),
        ("Taiwan", "TW", "#00B0F0", ""),
        ("Indonesia", "ID", "#00B0F0", ""),
        ("Thailand", "TH", "#00B0F0", ""),
        ("Mexico", "MX", "#00B050", ""),
        ("Peru", "PE", "#00B050", ""),
        ("Colombia", "CO", "#00B050", ""),
        ("Ecuador", "EC", "#00B050", ""),
        ("Guatemala", "GU", "#00B050", ""),
        ("Honduras", "HO", "#00B050", ""),
        ("El Salvador", "ES", "#00B050", ""),
        ("Turkey", "TR", "#7030A0", ""),
        ("Other International", "OI", "#FFCCFF", ""),
        ("Total", "TO", "#FFFFFF", ""),
    )
    conn.executemany(
        'INSERT INTO themes (Country, CountryAbbr, Color, "type") VALUES (?, ?, ?, ?)',
        seed,
    )


def _normalize_theme_color_hex(raw: object) -> str:
    """Collapse ##hex to #hex; accept 3/6/8 hex digits. Pass through rgb()/hsl() unchanged."""
    s = str(raw or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low.startswith("rgb") or low.startswith("hsl"):
        return s
    t = s
    while t.startswith("#"):
        t = t[1:].strip()
    if not t:
        return ""
    if re.fullmatch(r"[0-9a-fA-F]{3}", t) or re.fullmatch(r"[0-9a-fA-F]{6}", t) or re.fullmatch(
        r"[0-9a-fA-F]{8}", t
    ):
        return "#" + t.lower()
    return ""


def get_themes() -> list[dict[str, str]]:
    conn = _get_conn()
    rows = conn.execute(
        'SELECT Country, CountryAbbr, Color, "type" AS type FROM themes ORDER BY CountryAbbr'
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        orig = str(d.get("Color") or "").strip()
        fixed = _normalize_theme_color_hex(orig)
        d["Color"] = fixed if fixed else orig
        out.append(d)
    return out


def save_themes_rows(rows: list) -> int:
    """Replace all theme rows. Each dict: Country, CountryAbbr, Color, type (optional)."""
    conn = _get_conn()
    if not isinstance(rows, list):
        raise TypeError("rows must be a list")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM themes")
        sql = 'INSERT INTO themes (Country, CountryAbbr, Color, "type") VALUES (?, ?, ?, ?)'
        n = 0
        for r in rows:
            if not isinstance(r, dict):
                continue
            abbr = str(r.get("CountryAbbr", "")).strip().upper()
            if not abbr:
                continue
            color_raw = str(r.get("Color", "")).strip()
            color = _normalize_theme_color_hex(color_raw) or color_raw
            conn.execute(
                sql,
                (
                    str(r.get("Country", "")).strip(),
                    abbr,
                    color,
                    str(r.get("type", "")).strip(),
                ),
            )
            n += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return n


# ---------------------------------------------------------------------------
# control_panel
# ---------------------------------------------------------------------------

def get_control_panel() -> dict:
    conn = _get_conn()
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(control_panel)").fetchall()}
    has_active = "is_active" in cols
    wh = " WHERE COALESCE(is_active, 1) = 1" if has_active else ""
    cur = conn.execute(
        f'SELECT [key] AS cp_k, [value] AS cp_v FROM control_panel{wh}'
    )
    out: dict[str, float] = {}
    for r in cur:
        k = r["cp_k"]
        if k is None or str(k).strip() == "":
            continue
        v = r["cp_v"]
        out[str(k).strip()] = float(v) if v is not None else 0.0
    return out


def save_control_panel(data: dict) -> None:
    conn = _get_conn()
    conn.executemany(
        "INSERT OR REPLACE INTO control_panel (key, value) VALUES (?, ?)",
        [(k, float(v)) for k, v in data.items()],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# consolidation
# ---------------------------------------------------------------------------

def get_consolidation() -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT region, bale, storage, month FROM consolidation").fetchall()
    return {r["region"]: {"bale": r["bale"], "storage": r["storage"], "month": r["month"]} for r in rows}


def save_consolidation(data: dict) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM consolidation")
    conn.executemany(
        "INSERT INTO consolidation (region, bale, storage, month) VALUES (?, ?, ?, ?)",
        [
            (region, inner.get("bale", 0), inner.get("storage", 0), inner.get("month", 0))
            for region, inner in data.items()
            if isinstance(inner, dict)
        ],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# consolidation_days_storage
# ---------------------------------------------------------------------------

def get_consolidation_days_storage() -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT days FROM consolidation_days_storage WHERE id = 1").fetchone()
    if row is None:
        return {"Days Storage": 14.0}
    return {"Days Storage": row["days"]}


def save_consolidation_days_storage(data: dict) -> None:
    conn = _get_conn()
    days = float(data.get("Days Storage", 14.0))
    conn.execute(
        "INSERT OR REPLACE INTO consolidation_days_storage (id, days) VALUES (1, ?)",
        (days,),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# drayage
# ---------------------------------------------------------------------------

def get_drayage() -> dict:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT region, gri, line_haul, chas_split, contrainer, bale, ocean_base, updated "
        "FROM drayage"
    ).fetchall()
    return {
        r["region"]: {
            "GRI": r["gri"],
            "LineHaul": r["line_haul"],
            "ChasSplit": r["chas_split"],
            "Contrainer": r["contrainer"],
            "Bale": r["bale"],
            "OceanBase": r["ocean_base"],
            "Updated": r["updated"],
        }
        for r in rows
    }


def save_drayage(data: dict) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM drayage")
    params: list[tuple] = []
    for region, inner in data.items():
        if not isinstance(inner, dict):
            continue
        gri_v = inner.get("GRI")
        try:
            gri_f = 0.0 if gri_v is None else float(gri_v)
        except (TypeError, ValueError):
            gri_f = 0.0
        params.append(
            (
                region,
                gri_f,
                inner.get("LineHaul", 0),
                inner.get("ChasSplit", 0),
                inner.get("Contrainer", 0),
                inner.get("Bale", 0),
                inner.get("OceanBase", 0),
                str(inner.get("Updated", "")),
            )
        )
    conn.executemany(
        "INSERT INTO drayage (region, gri, line_haul, chas_split, contrainer, bale, ocean_base, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        params,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# document_cif
# ---------------------------------------------------------------------------

def get_document_cif() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT country, code, lc, ins, cont, com, cof, ciq_qc, gri "
        "FROM document_cif ORDER BY id"
    ).fetchall()
    return [
        {
            "country": r["country"],
            "code": r["code"],
            "LC": r["lc"],
            "INS": r["ins"],
            "CONT": r["cont"],
            "COM": r["com"],
            "COF": r["cof"],
            "CIQ_QC": r["ciq_qc"],
            "GRI": r["gri"],
        }
        for r in rows
    ]


def save_document_cif(data: list[dict]) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM document_cif")
    params: list[tuple] = []
    for row in data:
        gri_v = row.get("GRI")
        try:
            gri_f = 0.0 if gri_v is None else float(gri_v)
        except (TypeError, ValueError):
            gri_f = 0.0
        params.append(
            (
                row.get("country", ""),
                row.get("code", ""),
                row.get("LC"),
                row.get("INS"),
                row.get("CONT"),
                row.get("COM"),
                row.get("COF"),
                row.get("CIQ_QC"),
                gri_f,
            )
        )
    conn.executemany(
        "INSERT INTO document_cif (country, code, lc, ins, cont, com, cof, ciq_qc, gri) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        params,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# usa_forwarding_cost  (flat key-value store + separate cif_regions list)
# ---------------------------------------------------------------------------

def get_usa_forwarding_cost() -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT key, value FROM usa_forwarding_cost").fetchall()
    out: dict = {}
    for r in rows:
        k, v = r["key"], r["value"]
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = v

    region_rows = conn.execute("SELECT region FROM cif_regions ORDER BY sort_order").fetchall()
    out["cif_regions"] = [r["region"] for r in region_rows]
    return out


def save_usa_forwarding_cost(data: dict) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM usa_forwarding_cost")
    conn.execute("DELETE FROM cif_regions")

    kv_rows = []
    cif_regions = []
    for k, v in data.items():
        if k == "cif_regions":
            if isinstance(v, list):
                cif_regions = [
                    str(r).strip()
                    for r in v
                    if str(r).strip() and str(r).strip() not in _RETIRED_CIF_REGIONS
                ]
            continue
        kv_rows.append((k, str(v)))

    conn.executemany(
        "INSERT INTO usa_forwarding_cost (key, value) VALUES (?, ?)",
        kv_rows,
    )
    conn.executemany(
        "INSERT INTO cif_regions (sort_order, region) VALUES (?, ?)",
        [(i, str(r).strip()) for i, r in enumerate(cif_regions)],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# notes
# ---------------------------------------------------------------------------

def get_notes() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, body, created_at, updated_at FROM notes ORDER BY updated_at DESC"
    ).fetchall()
    return [
        {"id": r["id"], "title": r["title"], "body": r["body"],
         "created_at": r["created_at"], "updated_at": r["updated_at"]}
        for r in rows
    ]


def save_note(note_id: int | None, title: str, body: str) -> dict:
    conn = _get_conn()
    if note_id is not None:
        conn.execute(
            "UPDATE notes SET title = ?, body = ?, updated_at = datetime('now') WHERE id = ?",
            (title, body, note_id),
        )
        conn.commit()
        row = conn.execute("SELECT id, title, body, created_at, updated_at FROM notes WHERE id = ?", (note_id,)).fetchone()
    else:
        cur = conn.execute(
            "INSERT INTO notes (title, body) VALUES (?, ?)",
            (title, body),
        )
        conn.commit()
        row = conn.execute("SELECT id, title, body, created_at, updated_at FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"id": row["id"], "title": row["title"], "body": row["body"],
            "created_at": row["created_at"], "updated_at": row["updated_at"]}


def delete_note(note_id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# otr_rates
# ---------------------------------------------------------------------------

def get_otr_rates(active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    where = " WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        f"SELECT id, origin_city, origin_state, dest_city, dest_state, cargo_type, "
        f"base_rate, update_date, expiration_date, prior_base_rate, is_active "
        f"FROM otr_rates{where} ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def insert_otr_rate(row: dict) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO otr_rates (origin_city, origin_state, dest_city, dest_state, "
        "cargo_type, base_rate, update_date, expiration_date, prior_base_rate) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row.get("origin_city", ""), row.get("origin_state", ""),
            row.get("dest_city", ""), row.get("dest_state", ""),
            row.get("cargo_type", ""), row.get("base_rate", 0),
            row.get("update_date", ""), row.get("expiration_date", ""),
            row.get("prior_base_rate"),
        ),
    )
    conn.commit()


def deactivate_otr_rate(row_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE otr_rates SET is_active = 0 WHERE id = ?", (row_id,))
    conn.commit()


def _otr_compound_key(row: dict) -> str:
    return (
        f"{row.get('origin_city', '').upper()}|{row.get('origin_state', '').upper()}"
        f"|{row.get('dest_city', '').upper()}|{row.get('dest_state', '').upper()}"
    )


# ---------------------------------------------------------------------------
# seam_tariffs
# ---------------------------------------------------------------------------

_SEAM_COLS = (
    "warehouse", "name", "city", "state", "county", "terms", "verified",
    "points", "recv", "strg", "load", "compr", "class", "mark", "eff_date",
    "bales", "rail", "ice_ref", "capacity", "cert_load", "cert_compr",
    "cert_mark", "cert_recv", "cert_strg", "cert_class", "min_storage", "basis_adj",
)


def get_seam_tariffs(active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    where = " WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        f"SELECT id, {', '.join(_SEAM_COLS)}, is_active FROM seam_tariffs{where} ORDER BY "
        f"CAST(warehouse AS INTEGER), id"
    ).fetchall()
    return [dict(r) for r in rows]


def insert_seam_tariff(row: dict) -> None:
    conn = _get_conn()
    placeholders = ", ".join("?" for _ in _SEAM_COLS)
    conn.execute(
        f"INSERT INTO seam_tariffs ({', '.join(_SEAM_COLS)}) VALUES ({placeholders})",
        tuple(str(row.get(c, "")).strip() for c in _SEAM_COLS),
    )
    conn.commit()


def deactivate_seam_tariff(row_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE seam_tariffs SET is_active = 0 WHERE id = ?", (row_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# regions_and_ports
# ---------------------------------------------------------------------------

_RAP_COLS = (
    "warehouse", "name", "city", "state", "region", "export", "port",
    "eso", "flat_bed_fees", "late_fees", "transportation_adjust",
    "misc_fees", "consol_interest",
)


def get_regions_and_ports(active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    where = " WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        f"SELECT id, {', '.join(_RAP_COLS)}, is_active FROM regions_and_ports{where} ORDER BY "
        f"CAST(warehouse AS INTEGER), id"
    ).fetchall()
    return [dict(r) for r in rows]


def insert_regions_and_ports_row(row: dict) -> None:
    conn = _get_conn()
    placeholders = ", ".join("?" for _ in _RAP_COLS)
    conn.execute(
        f"INSERT INTO regions_and_ports ({', '.join(_RAP_COLS)}) VALUES ({placeholders})",
        tuple(str(row.get(c, "")).strip() for c in _RAP_COLS),
    )
    conn.commit()


def deactivate_regions_and_ports_row(row_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE regions_and_ports SET is_active = 0 WHERE id = ?", (row_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# portcode_portcity (ocean / unOrig -> city for Port column and drayage)
# ---------------------------------------------------------------------------


def _qident_sql(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def get_portcode_portcity_lookup(active_only: bool = True) -> dict[str, str]:
    """Uppercase UN/LOC port code -> city name (same shape as former portcode_portcity.csv)."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='portcode_portcity'"
    ).fetchone():
        return {}
    cols = {row[1] for row in conn.execute("PRAGMA table_info(portcode_portcity)").fetchall()}
    low = {str(c).lower(): c for c in cols}

    def pick(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in low:
                return low[c.lower()]
        return None

    c_code = pick("PortCode", "portcode", "port_code")
    c_city = pick("PortCity", "port_city")
    if not c_code or not c_city:
        return {}

    has_active = "is_active" in cols
    q = f"SELECT {_qident_sql(c_code)}, {_qident_sql(c_city)} FROM portcode_portcity"
    if active_only and has_active:
        q += " WHERE is_active = 1"

    out: dict[str, str] = {}
    for row in conn.execute(q):
        code = str(row[0] or "").strip().upper()
        if not code:
            continue
        out[code] = str(row[1] or "").strip()
    return out


def get_dischargeport_country_lookup(active_only: bool = True) -> dict[str, str]:
    """Uppercase destination UN/LOC (unDest) -> destination label (same as former dischargeport_country.csv)."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dischargeport_country'"
    ).fetchone():
        return {}
    cols = {row[1] for row in conn.execute("PRAGMA table_info(dischargeport_country)").fetchall()}
    low = {str(c).lower(): c for c in cols}

    def pick(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in low:
                return low[c.lower()]
        return None

    c_port = pick("discharge_port", "dischargePort")
    c_lbl = pick("country", "Country")
    if not c_port or not c_lbl:
        return {}

    has_active = "is_active" in cols
    q = f"SELECT {_qident_sql(c_port)}, {_qident_sql(c_lbl)} FROM dischargeport_country"
    if active_only and has_active:
        q += " WHERE is_active = 1"

    out: dict[str, str] = {}
    for row in conn.execute(q):
        code = str(row[0] or "").strip().upper()
        if not code:
            continue
        out[code] = str(row[1] or "").strip()
    return out


def get_countrycode_country_lookup(active_only: bool = True) -> dict[str, str]:
    """Uppercase ISO country code (first two chars of unDest) -> country name."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='countrycode_country'"
    ).fetchone():
        return {}
    cols = {row[1] for row in conn.execute("PRAGMA table_info(countrycode_country)").fetchall()}
    low = {str(c).lower(): c for c in cols}

    def pick(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in low:
                return low[c.lower()]
        return None

    c_code = pick("countrycode", "countryCode")
    c_name = pick("country", "Country")
    if not c_code or not c_name:
        return {}

    has_active = "is_active" in cols
    q = f"SELECT {_qident_sql(c_code)}, {_qident_sql(c_name)} FROM countrycode_country"
    if active_only and has_active:
        q += " WHERE is_active = 1"

    out: dict[str, str] = {}
    for row in conn.execute(q):
        code = str(row[0] or "").strip().upper()
        if not code:
            continue
        out[code] = str(row[1] or "").strip()
    return out


def get_ocean_rates_extract_row_dicts(active_only: bool = True) -> list[dict[str, object]]:
    """
    Ocean rate rows as dicts keyed like the former 470OceanRatesExtract.csv DictReader.
    Omits id and is_active from each dict.
    """
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ocean_rates_extract'"
    ).fetchone():
        return []
    col_rows = conn.execute("PRAGMA table_info(ocean_rates_extract)").fetchall()
    cols = [r[1] for r in col_rows]
    skip = {"id", "is_active"}
    data_cols = [c for c in cols if c not in skip]
    if not data_cols:
        return []
    has_active = "is_active" in cols
    sel = ", ".join(_qident_sql(c) for c in data_cols)
    q = f"SELECT {sel} FROM ocean_rates_extract"
    if active_only and has_active:
        q += " WHERE is_active = 1"

    out: list[dict[str, object]] = []
    for row in conn.execute(q):
        out.append({data_cols[i]: row[i] for i in range(len(data_cols))})
    return out


# ---------------------------------------------------------------------------
# ocean_costing_rules (versioned: save deactivates prior row with same city/desc/country)
# ---------------------------------------------------------------------------


def _norm_ocean_rule_key(value) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def get_ocean_costing_rules(active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    where = " WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        "SELECT id, city, description, country, logic, is_active "
        f"FROM ocean_costing_rules{where} ORDER BY id"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append(
            {
                "id": d["id"],
                "city": str(d.get("city") or ""),
                "desc": str(d.get("description") or ""),
                "country": str(d.get("country") or ""),
                "logic": str(d.get("logic") or ""),
                "is_active": int(d.get("is_active") or 0),
            }
        )
    return out


def insert_ocean_costing_rule(city: str, desc: str, country: str, logic: str) -> int:
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO ocean_costing_rules (city, description, country, logic, is_active) "
        "VALUES (?, ?, ?, ?, 1)",
        (city.strip(), desc.strip(), country.strip(), logic.strip()),
    )
    conn.commit()
    return int(cur.lastrowid)


def deactivate_ocean_costing_rules_matching(city: str, desc: str, country: str) -> int:
    """Deactivate active rows whose (city, desc, country) matches after normalization. Returns count."""
    conn = _get_conn()
    nc = _norm_ocean_rule_key(city)
    nd = _norm_ocean_rule_key(desc)
    nct = _norm_ocean_rule_key(country)
    rows = conn.execute(
        "SELECT id, city, description, country FROM ocean_costing_rules WHERE is_active = 1"
    ).fetchall()
    n = 0
    for r in rows:
        if (
            _norm_ocean_rule_key(r["city"]) == nc
            and _norm_ocean_rule_key(r["description"]) == nd
            and _norm_ocean_rule_key(r["country"]) == nct
        ):
            conn.execute("UPDATE ocean_costing_rules SET is_active = 0 WHERE id = ?", (r["id"],))
            n += 1
    conn.commit()
    return n


def deactivate_all_ocean_costing_rules() -> None:
    conn = _get_conn()
    conn.execute("UPDATE ocean_costing_rules SET is_active = 0 WHERE is_active = 1")
    conn.commit()


def update_regions_and_ports_row(row_id: int, updates: dict) -> None:
    conn = _get_conn()
    sets = []
    vals = []
    for col in _RAP_COLS:
        if col in updates:
            sets.append(f"{col} = ?")
            vals.append(str(updates[col]).strip())
    if not sets:
        return
    vals.append(row_id)
    conn.execute(f"UPDATE regions_and_ports SET {', '.join(sets)} WHERE id = ?", tuple(vals))
    conn.commit()


# ---------------------------------------------------------------------------
# Migration: seed DB from existing JSON + CSV files
# ---------------------------------------------------------------------------

def _migrate_otr_csv(data_dir: Path) -> None:
    import csv
    conn = _get_conn()
    if conn.execute("SELECT COUNT(*) FROM otr_rates").fetchone()[0] > 0:
        return
    otr_path = data_dir / "OTR_Rates.csv"
    if not otr_path.is_file():
        return
    with otr_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for raw in reader:
            oc_parts = str(raw.get("ORIGINCITY", "")).split(",", 1)
            oc = oc_parts[0].strip()
            os_ = oc_parts[1].strip() if len(oc_parts) > 1 else ""
            dc_parts = str(raw.get("DESTINATIONCITY", "")).split(",", 1)
            dc = dc_parts[0].strip()
            ds = dc_parts[1].strip() if len(dc_parts) > 1 else ""
            br = raw.get("BASE RATE", "0")
            pr = raw.get("PRIOR BASE RATE")
            try:
                br_f = float(br)
            except (TypeError, ValueError):
                br_f = 0.0
            try:
                pr_f = float(pr) if pr and str(pr).strip() else None
            except (TypeError, ValueError):
                pr_f = None
            conn.execute(
                "INSERT INTO otr_rates (origin_city, origin_state, dest_city, dest_state, "
                "cargo_type, base_rate, update_date, expiration_date, prior_base_rate) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (oc, os_, dc, ds,
                 str(raw.get("CARGOTYPE", "")).strip(),
                 br_f,
                 str(raw.get("UPDATEDATE", "")).strip(),
                 str(raw.get("EXPIRATIONDATE", "")).strip(),
                 pr_f),
            )
    conn.commit()


def _migrate_seam_csv(data_dir: Path) -> None:
    import csv
    conn = _get_conn()
    if conn.execute("SELECT COUNT(*) FROM seam_tariffs").fetchone()[0] > 0:
        return
    seam_path = data_dir / "SEAM_TARIFFS_CERT_TARIFFS.csv"
    if not seam_path.is_file():
        return
    csv_to_db = {
        "Warehouse": "warehouse", "Name": "name", "City": "city", "State": "state",
        "County": "county", "Terms": "terms", "Verified": "verified", "Points": "points",
        "Recv": "recv", "Strg": "strg", "Load": "load", "Compr": "compr",
        "Class": "class", "Mark": "mark", "EffDate": "eff_date", "Bales": "bales",
        "Rail": "rail", "ICE Ref": "ice_ref", "Capacity": "capacity",
        "CertLoad": "cert_load", "CertCompr": "cert_compr", "CertMark": "cert_mark",
        "CertRecv": "cert_recv", "CertStrg": "cert_strg", "CertClass": "cert_class",
        "Min Storage": "min_storage", "Basis Adj": "basis_adj",
    }
    with seam_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for raw in reader:
            row = {db_col: str(raw.get(csv_col, "")).strip() for csv_col, db_col in csv_to_db.items()}
            placeholders = ", ".join("?" for _ in _SEAM_COLS)
            conn.execute(
                f"INSERT INTO seam_tariffs ({', '.join(_SEAM_COLS)}) VALUES ({placeholders})",
                tuple(row.get(c, "") for c in _SEAM_COLS),
            )
    conn.commit()


def _migrate_rap_csv(data_dir: Path) -> None:
    import csv
    conn = _get_conn()
    if conn.execute("SELECT COUNT(*) FROM regions_and_ports").fetchone()[0] > 0:
        return
    rap_path = data_dir / "regions_and_ports.csv"
    if not rap_path.is_file():
        return
    csv_to_db = {
        "Warehouse": "warehouse", "Name": "name", "City": "city", "State": "state",
        "Region": "region", "Export": "export", "Port": "port", "ESO": "eso",
        "Flat Bed Fees": "flat_bed_fees", "Late Fees": "late_fees",
        "Transportation Adjust": "transportation_adjust",
        "Misc  Fees": "misc_fees", "Consol Interest": "consol_interest",
    }
    with rap_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for raw in reader:
            row = {}
            for csv_col, db_col in csv_to_db.items():
                row[db_col] = str(raw.get(csv_col, "")).strip()
            if not row.get("misc_fees"):
                row["misc_fees"] = str(raw.get("Misc Fees", "")).strip()
            placeholders = ", ".join("?" for _ in _RAP_COLS)
            conn.execute(
                f"INSERT INTO regions_and_ports ({', '.join(_RAP_COLS)}) VALUES ({placeholders})",
                tuple(row.get(c, "") for c in _RAP_COLS),
            )
    conn.commit()


def migrate_from_json(data_dir: Path) -> None:
    """One-time import: read JSON config files and CSV data files into SQLite."""

    cp_path = data_dir / "control_panel.json"
    if cp_path.exists():
        with cp_path.open("r", encoding="utf-8") as f:
            save_control_panel(json.load(f))

    cons_path = data_dir / "consolidation.json"
    if cons_path.exists():
        with cons_path.open("r", encoding="utf-8") as f:
            save_consolidation(json.load(f))

    cds_path = data_dir / "consolidation_days_storage.json"
    if cds_path.exists():
        with cds_path.open("r", encoding="utf-8") as f:
            save_consolidation_days_storage(json.load(f))

    dray_path = data_dir / "drayage.json"
    if dray_path.exists():
        with dray_path.open("r", encoding="utf-8") as f:
            save_drayage(json.load(f))

    doc_cif_path = data_dir / "document_cif.json"
    if doc_cif_path.exists():
        with doc_cif_path.open("r", encoding="utf-8") as f:
            save_document_cif(json.load(f))

    ufc_path = data_dir / "usa_forwarding_cost.json"
    if ufc_path.exists():
        with ufc_path.open("r", encoding="utf-8") as f:
            save_usa_forwarding_cost(json.load(f))

    _migrate_otr_csv(data_dir)
    _migrate_seam_csv(data_dir)
    _migrate_rap_csv(data_dir)

    print(f"Migration complete -> {DB_PATH}")


def ensure_csv_tables_populated(data_dir: Path) -> None:
    """Called on server startup: seed OTR/SEAM/R&P tables from CSV if they're empty."""
    _migrate_otr_csv(data_dir)
    _migrate_seam_csv(data_dir)
    _migrate_rap_csv(data_dir)
