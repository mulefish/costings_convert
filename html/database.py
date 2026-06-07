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
    _ensure_additional_theme_countries(conn)
    _ensure_export_data_seeded(conn)
    _ensure_dthc_prepaid_country_code_column(conn)
    _ensure_dthc_prepaid_seeded(conn)
    _ensure_document_cif_gri_column(conn)
    _ensure_document_cif_cad_lc_coa_columns(conn)
    _ensure_document_cif_usda_columns(conn)
    _ensure_consolidation_otr_gri_column(conn)
    _ensure_consolidation_storage_days_column(conn)
    _ensure_consolidation_breaks_column(conn)
    _ensure_drayage_gri_column(conn)
    _ensure_cif_regions_drop_brz_aus(conn)
    _ensure_lc_bank_cost_seeded(conn)
    _ensure_fsc_fuel_columns(conn)
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
    otr_gri       REAL NOT NULL DEFAULT 0,
    storage_days  REAL NOT NULL DEFAULT 0,
        breaks        REAL NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS lc_bank_cost (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    bank         TEXT NOT NULL,
    value        REAL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    UNIQUE(country_code, bank)
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

CREATE TABLE IF NOT EXISTS export_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    base        TEXT NOT NULL,
    code        TEXT NOT NULL,
    c           TEXT NOT NULL DEFAULT '',
    d           TEXT NOT NULL DEFAULT '',
    ports_json  TEXT NOT NULL DEFAULT '[]',
    extra_json  TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dthc_prepaid (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL DEFAULT '',
    location     TEXT NOT NULL,
    prepaid      TEXT NOT NULL CHECK (prepaid IN ('Yes', 'No')),
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS fsc_fuel (
    fuel_price   REAL PRIMARY KEY,
    fsc_percent  REAL NOT NULL DEFAULT 0,
    total_percent    REAL NOT NULL DEFAULT 0
);
"""


_ALL_TABLES = (
    "control_panel", "consolidation",
    "drayage", "document_cif", "usa_forwarding_cost", "cif_regions", "notes",
    "otr_rates", "seam_tariffs", "regions_and_ports", "ocean_costing_rules",
    "portcode_portcity", "dischargeport_country", "countrycode_country", "ocean_rates_extract", "otr_transit_lookup",
    "export_data",
    "dthc_prepaid",
    "lc_bank_cost",
    "fsc_fuel",
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


def _ensure_document_cif_cad_lc_coa_columns(conn: sqlite3.Connection) -> None:
    """Add CAD_USA/BRZ/AUS, LC_USA/BRZ/AUS, COA_USA/BRZ/AUS columns."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_cif'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(document_cif)").fetchall()}
    new_cols = {
        "cad_usa": 14, "cad_brz": 18, "cad_aus": 14,
        "lc_usa": 21, "lc_brz": 65, "lc_aus": 14,
        "coa_usa": 30, "coa_brz": 14, "coa_aus": 40,
    }
    changed = False
    for col, default in new_cols.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE document_cif ADD COLUMN {col} REAL NOT NULL DEFAULT {default}")
            changed = True
    if changed:
        conn.commit()


def _ensure_document_cif_usda_columns(conn: sqlite3.Connection) -> None:
    """Add USDA USD/Bale and Pts/lb columns to document_cif."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_cif'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(document_cif)").fetchall()}
    changed = False
    for col in ("usda_usd_bale", "usda_pts_lb"):
        if col not in cols:
            conn.execute(f"ALTER TABLE document_cif ADD COLUMN {col} REAL NOT NULL DEFAULT 0")
            changed = True
    if changed:
        import math
        def _ceil5(x):
            return int(math.ceil(x / 5.0)) * 5
        # Pre-populate with known USDA USD/Bale values by country code;
        # Pts/lb is computed: ceil5(((USD/Bale * 90) / 20) / 22.046 * 100)
        usda_by_code = {
            "CN": 0.617, "VN": 0.567, "KO": 0.633,
            "JP": 1.200, "MA": 0.793, "TW": 0.600,
            "ID": 0.690, "TH": 0.533, "BD": 0.343,
            "PK": 0.473, "IN": 0.430, "TR": 0.567,
            "MX": 0.757, "PE": 1.007, "CO": 0.833,
            "EC": 1.423, "GU": 0.923, "HO": 0.0,
            "ES": 0.0, "IT": 0.0,
        }
        for code, usd in usda_by_code.items():
            pts = _ceil5(((usd * 90) / 20) / 22.046 * 100) if usd else 0
            conn.execute(
                "UPDATE document_cif SET usda_usd_bale=?, usda_pts_lb=? WHERE UPPER(code)=?",
                (usd, pts, code),
            )
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


def _ensure_consolidation_otr_gri_column(conn: sqlite3.Connection) -> None:
    """Add consolidation.otr_gri for DBs created before that column existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='consolidation'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(consolidation)").fetchall()}
    if "otr_gri" not in cols:
        conn.execute("ALTER TABLE consolidation ADD COLUMN otr_gri REAL NOT NULL DEFAULT 0")
        conn.commit()


def _ensure_consolidation_storage_days_column(conn: sqlite3.Connection) -> None:
    """Add consolidation.storage_days for DBs created before that column existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='consolidation'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(consolidation)").fetchall()}
    if "storage_days" not in cols:
        conn.execute("ALTER TABLE consolidation ADD COLUMN storage_days REAL NOT NULL DEFAULT 0")
        conn.commit()


def _ensure_consolidation_breaks_column(conn: sqlite3.Connection) -> None:
    """Add consolidation.breaks for DBs created before that column existed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='consolidation'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(consolidation)").fetchall()}
    if "breaks" not in cols:
        conn.execute("ALTER TABLE consolidation ADD COLUMN breaks REAL NOT NULL DEFAULT 0")
        conn.commit()


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


# New theme rows use mauve until colors are set in Jarvis → Themes.
_THEME_NEW_COUNTRY_MAUVE = "#E0B0FF"

# DTHC / ocean prepaid countries missing from original chart seed.
_ADDITIONAL_THEME_COUNTRIES: tuple[tuple[str, str], ...] = (
    ("Algeria", "DZ"),
    ("Bahrain", "BH"),
    ("Egypt", "EG"),
    ("Greece", "GR"),
    ("Hong Kong", "HK"),
    ("Morocco", "MO"),  # ISO MA; themes already uses MA for Malaysia
    ("Philippines", "PH"),
    ("Portugal", "PT"),
    ("Qatar", "QA"),
    ("Saudi Arabia", "SA"),
    ("Singapore", "SG"),
    ("Sri Lanka", "LK"),
    ("Tunisia", "TN"),
    ("UAE", "AE"),
)


def _ensure_additional_theme_countries(conn: sqlite3.Connection) -> None:
    """Insert theme rows for prepaid/chart countries not in the original seed."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='themes'"
    ).fetchone():
        return
    for country, abbr in _ADDITIONAL_THEME_COUNTRIES:
        abbr_u = abbr.upper()
        hit = conn.execute(
            """
            SELECT CountryAbbr FROM themes
            WHERE upper(trim(CountryAbbr)) = ? OR lower(trim(Country)) = lower(?)
            LIMIT 1
            """,
            (abbr_u, country),
        ).fetchone()
        if hit:
            conn.execute(
                """
                UPDATE themes SET "type" = ?
                WHERE upper(trim(CountryAbbr)) = ? OR lower(trim(Country)) = lower(?)
                """,
                ("country", abbr_u, country),
            )
            continue
        conn.execute(
            'INSERT INTO themes (Country, CountryAbbr, Color, "type") VALUES (?, ?, ?, ?)',
            (country, abbr_u, _THEME_NEW_COUNTRY_MAUVE, "country"),
        )
    conn.execute(
        "UPDATE themes SET \"type\" = 'country' WHERE lower(trim(Country)) = 'ecuador'"
    )
    conn.execute(
        """
        UPDATE themes SET "type" = 'country'
        WHERE lower(trim(Country)) IN ('uae', 'united arab emirates')
        """
    )
    conn.commit()


# Export view countries / CIF FE ports (was EXPORT_DATA in script.js).
_EXPORT_DATA_MAUVE = _THEME_NEW_COUNTRY_MAUVE

_EXPORT_DATA_SEED: tuple[dict[str, object], ...] = (
    {"base": "China", "code": "CN", "c": "38", "d": "18", "ports": ["Qingdao", "Xiamen", "Nantong"]},
    {"base": "Vietnam", "code": "VN", "c": "50", "d": "14", "ports": ["Ho Chi Minh", "Da Nang", "Haiphong"]},
    {"base": "Korea", "code": "KO", "c": "46", "d": "18", "ports": ["Busan", "Kwangyang"]},
    {"base": "Japan", "code": "JP", "c": "43", "d": "14", "ports": ["Osaka", "Kobe", "Nagoya"]},
    {"base": "Malaysia", "code": "MA", "c": "40", "d": "14", "ports": ["Tanjung Pelepas", "Penang", "Port Klang"]},
    {"base": "Taiwan", "code": "TW", "c": "45", "d": "21", "ports": ["Keelung", "Taichung", "Kaohsiung", "Tao Yuan"]},
    {"base": "Indonesia", "code": "ID", "c": "38", "d": "14", "ports": ["Jakarta", "Semarang", "Cikarang", "Surabaya"]},
    {"base": "Thailand", "code": "TH", "c": "45", "d": "14", "ports": ["Bangkok", "Lat Krabang", "Laem Chabang"]},
    {"base": "Bangladesh", "code": "BD", "c": "52", "d": "14", "ports": ["Chittagong"]},
    {"base": "Pakistan", "code": "PK", "c": "45", "d": "14", "ports": ["Port Qasim/Karachi"]},
    {"base": "India", "code": "IN", "c": "50", "d": "14", "ports": ["Mundra", "Tuticorin", "Chennai"]},
    {"base": "Turkey", "code": "TR", "c": "37", "d": "14", "ports": ["Iskenderun", "Mersin", "Izmir"]},
    {
        "base": "Mexico",
        "code": "MX",
        "c": "",
        "d": "N/A",
        "ports": ["Yecapixtla", "Parras", "CD Victoria"],
        "extra": {"secondCode": "Weslaco"},
    },
    {"base": "Peru", "code": "PE", "c": "11", "d": "18", "ports": ["Callao"]},
    {"base": "Guatemala", "code": "GU", "c": "8", "d": "21", "ports": ["Amatitlan", "Palin"]},
    {"base": "Honduras", "code": "HO", "c": "11", "d": "18", "ports": ["Naco"]},
    {"base": "Spain", "code": "ES", "c": "", "d": "14", "ports": ["Santa Barbara"]},
    {"base": "Italy", "code": "IT", "c": "", "d": "14", "ports": ["Bergamo", "Salerno"]},
    {"base": "Other", "code": "OT", "c": "-", "d": "-", "ports": ["Batumi"]},
)


def _export_data_row_to_api(row: sqlite3.Row | dict) -> dict[str, object]:
    d = dict(row)
    ports_raw = d.get("ports_json") or "[]"
    try:
        ports = json.loads(ports_raw) if isinstance(ports_raw, str) else list(ports_raw or [])
    except json.JSONDecodeError:
        ports = []
    extra = None
    extra_raw = d.get("extra_json")
    if extra_raw:
        try:
            extra = json.loads(extra_raw) if isinstance(extra_raw, str) else extra_raw
        except json.JSONDecodeError:
            extra = None
    return {
        "base": str(d.get("base") or "").strip(),
        "code": str(d.get("code") or "").strip(),
        "c": str(d.get("c") if d.get("c") is not None else ""),
        "d": str(d.get("d") if d.get("d") is not None else ""),
        "ports": [str(p) for p in ports],
        "extra": extra,
    }


def _ensure_export_data_seeded(conn: sqlite3.Connection) -> None:
    """Ensure export_data rows exist for each built-in country; sync themes for export countries."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='export_data'"
    ).fetchone():
        return
    for i, item in enumerate(_EXPORT_DATA_SEED):
        code = str(item["code"]).upper()
        exists = conn.execute(
            "SELECT 1 FROM export_data WHERE upper(trim(code)) = ? AND is_active = 1 LIMIT 1",
            (code,),
        ).fetchone()
        if exists:
            continue
        ports = item.get("ports") or []
        extra = item.get("extra")
        conn.execute(
            """
            INSERT INTO export_data (base, code, c, d, ports_json, extra_json, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                str(item["base"]),
                code,
                str(item.get("c", "")),
                str(item.get("d", "")),
                json.dumps(list(ports)),
                json.dumps(extra) if extra is not None else None,
                i,
            ),
        )
    _sync_themes_for_export_data(conn)
    conn.commit()


def _sync_themes_for_export_data(conn: sqlite3.Connection) -> None:
    """Themes: existing export countries → type country; missing → insert with mauve."""
    rows = conn.execute(
        "SELECT base, code FROM export_data WHERE is_active = 1 ORDER BY sort_order, id"
    ).fetchall()
    theme_rows = conn.execute(
        'SELECT Country, CountryAbbr, Color, "type" FROM themes'
    ).fetchall()
    by_abbr = {str(r["CountryAbbr"] or "").strip().upper(): dict(r) for r in theme_rows}
    by_country = {str(r["Country"] or "").strip().lower(): dict(r) for r in theme_rows}

    for er in rows:
        base = str(er["base"] or "").strip()
        code = str(er["code"] or "").strip().upper()
        if not base or not code:
            continue
        hit = by_country.get(base.lower()) or by_abbr.get(code)
        if hit:
            abbr = str(hit["CountryAbbr"] or "").strip().upper()
            conn.execute(
                'UPDATE themes SET "type" = ? WHERE CountryAbbr = ?',
                ("country", abbr),
            )
            by_abbr[abbr] = {**hit, "type": "country"}
            continue
        conn.execute(
            'INSERT INTO themes (Country, CountryAbbr, Color, "type") VALUES (?, ?, ?, ?)',
            (base, code, _EXPORT_DATA_MAUVE, "country"),
        )
        by_abbr[code] = {"Country": base, "CountryAbbr": code, "Color": _EXPORT_DATA_MAUVE, "type": "country"}
        by_country[base.lower()] = by_abbr[code]


def get_export_data(active_only: bool = True) -> list[dict[str, object]]:
    conn = _get_conn()
    q = "SELECT base, code, c, d, ports_json, extra_json FROM export_data"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY sort_order, id"
    return [_export_data_row_to_api(r) for r in conn.execute(q)]


# DTHC prepaid: ISO 3166-1 alpha-2 (matches unDest[:2] / countrycode_country) -> Yes/No.
# Ocean extract columns: Yes = ALLIN40HC (U) then ALLIN40FT (T); No = 40HC (Q) then 40FT (P).
_DTHC_PREPAID_ALIASES: dict[str, str] = {
    "korea, republic of": "KR",
    "south korea": "KR",
    "republic of korea": "KR",
    "united arab emirates": "AE",
}

_DTHC_PREPAID_SEED: tuple[tuple[str, str, str], ...] = (
    ("DZ", "Algeria", "Yes"),
    ("BH", "Bahrain", "Yes"),
    ("BD", "Bangladesh", "Yes"),
    ("CN", "China", "Yes"),
    ("CO", "Colombia", "Yes"),
    ("EG", "Egypt", "Yes"),
    ("EC", "Ecuador", "Yes"),
    ("GR", "Greece", "Yes"),
    ("GT", "Guatemala", "Yes"),
    ("HK", "Hong Kong", "No"),
    ("IN", "India", "No"),
    ("ID", "Indonesia", "Yes"),
    ("IT", "Italy", "Yes"),
    ("JP", "Japan", "No"),
    ("KR", "Korea", "No"),
    ("MY", "Malaysia", "No"),
    ("MA", "Morocco", "Yes"),
    ("PK", "Pakistan", "Yes"),
    ("PE", "Peru", "Yes"),
    ("PH", "Philippines", "Yes"),
    ("PT", "Portugal", "Yes"),
    ("QA", "Qatar", "Yes"),
    ("SA", "Saudi Arabia", "Yes"),
    ("SG", "Singapore", "No"),
    ("LK", "Sri Lanka", "No"),
    ("TW", "Taiwan", "No"),
    ("TH", "Thailand", "No"),
    ("TN", "Tunisia", "Yes"),
    ("TR", "Turkey", "Yes"),
    ("AE", "UAE", "Yes"),
    ("VN", "Vietnam", "Yes"),
)

_DTHC_LOCATION_TO_CODE: dict[str, str] = {
    str(loc).strip().lower(): str(code).strip().upper()
    for code, loc, _pre in _DTHC_PREPAID_SEED
}


def _ensure_dthc_prepaid_country_code_column(conn: sqlite3.Connection) -> None:
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dthc_prepaid'"
    ).fetchone():
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(dthc_prepaid)").fetchall()}
    if "country_code" not in cols:
        conn.execute("ALTER TABLE dthc_prepaid ADD COLUMN country_code TEXT NOT NULL DEFAULT ''")
    for row in conn.execute("SELECT id, location FROM dthc_prepaid WHERE trim(country_code) = ''").fetchall():
        loc = str(row["location"] or "").strip().lower()
        code = _DTHC_LOCATION_TO_CODE.get(loc, "")
        if not code:
            hit = conn.execute(
                "SELECT countrycode FROM countrycode_country WHERE lower(country) = ?",
                (loc,),
            ).fetchone()
            if hit:
                code = str(hit["countrycode"] or "").strip().upper()
        if code:
            conn.execute("UPDATE dthc_prepaid SET country_code = ? WHERE id = ?", (code, row["id"]))
    conn.commit()


def _ensure_dthc_prepaid_seeded(conn: sqlite3.Connection) -> None:
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dthc_prepaid'"
    ).fetchone():
        return
    for i, (code, location, prepaid) in enumerate(_DTHC_PREPAID_SEED):
        cc = str(code).strip().upper()
        loc = str(location).strip()
        pre = str(prepaid).strip()
        if not cc or not loc or pre not in ("Yes", "No"):
            continue
        exists = conn.execute(
            """
            SELECT 1 FROM dthc_prepaid
            WHERE is_active = 1
              AND (upper(trim(country_code)) = ? OR lower(trim(location)) = lower(?))
            LIMIT 1
            """,
            (cc, loc),
        ).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE dthc_prepaid
                SET country_code = ?, location = ?, prepaid = ?, sort_order = ?
                WHERE is_active = 1
                  AND (upper(trim(country_code)) = ? OR lower(trim(location)) = lower(?))
                """,
                (cc, loc, pre, i, cc, loc),
            )
            continue
        conn.execute(
            """
            INSERT INTO dthc_prepaid (country_code, location, prepaid, sort_order, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (cc, loc, pre, i),
        )
    conn.commit()


def get_dthc_prepaid_lookup_by_code(active_only: bool = True) -> dict[str, str]:
    """Uppercase ISO country code -> 'Yes' or 'No'."""
    conn = _get_conn()
    q = "SELECT country_code, prepaid FROM dthc_prepaid"
    if active_only:
        q += " WHERE is_active = 1"
    out: dict[str, str] = {}
    for row in conn.execute(q):
        code = str(row["country_code"] or "").strip().upper()
        pre = str(row["prepaid"] or "Yes").strip()
        if code:
            out[code] = pre if pre in ("Yes", "No") else "Yes"
    return out


def get_dthc_prepaid_lookup(active_only: bool = True) -> dict[str, str]:
    """Lowercase location label -> 'Yes' or 'No' (Notes / legacy)."""
    conn = _get_conn()
    q = "SELECT location, prepaid FROM dthc_prepaid"
    if active_only:
        q += " WHERE is_active = 1"
    out: dict[str, str] = {}
    for row in conn.execute(q):
        loc = str(row["location"] or "").strip().lower()
        pre = str(row["prepaid"] or "Yes").strip()
        if loc:
            out[loc] = pre if pre in ("Yes", "No") else "Yes"
    return out


def get_dthc_prepaid_by_country_code(country_code: str, default: str = "Yes") -> str:
    """Primary lookup: 2-letter code from unDest (same as countrycode_country.countrycode)."""
    code = str(country_code or "").strip().upper()[:2]
    if not code:
        return default
    lookup = get_dthc_prepaid_lookup_by_code()
    if code in lookup:
        return lookup[code]
    return default


def get_dthc_prepaid_for_country(country_name: str, default: str = "Yes") -> str:
    """Resolve prepaid from full country name (countrycode_country) or dthc location label."""
    key = str(country_name or "").strip().lower()
    if not key:
        return default
    alias_code = _DTHC_PREPAID_ALIASES.get(key)
    if alias_code:
        return get_dthc_prepaid_by_country_code(alias_code, default)
    conn = _get_conn()
    hit = conn.execute(
        "SELECT countrycode FROM countrycode_country WHERE lower(country) = ?",
        (key,),
    ).fetchone()
    if hit:
        return get_dthc_prepaid_by_country_code(str(hit["countrycode"]), default)
    lookup = get_dthc_prepaid_lookup()
    if key in lookup:
        return lookup[key]
    return default


def _ocean_extract_rate_value(raw: dict, field: str) -> float | None:
    """Return numeric rate if field is present and non-zero; else None."""
    v = raw.get(field)
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        n = float(s.replace(",", ""))
    except ValueError:
        return None
    if not (n == n):  # NaN
        return None
    if n == 0.0:
        return None
    return n


def ocean_freight_from_extract_row(raw: dict, prepaid: str) -> float:
    """
  470OceanRatesExtract / ocean_rates_extract:
    Prepaid Yes → ALLIN40HC (col U), else ALLIN40FT (col T).
    Prepaid No  → 40HC (col Q), else 40FT (col P).
    """
    pre = str(prepaid or "Yes").strip()
    if pre.lower() == "no":
        keys = ("40HC", "40FT")
    else:
        keys = ("ALLIN40HC", "ALLIN40FT")
    for k in keys:
        val = _ocean_extract_rate_value(raw, k)
        if val is not None:
            return val
    return 0.0


def get_dthc_prepaid_rows(active_only: bool = True) -> list[dict[str, str]]:
    conn = _get_conn()
    q = "SELECT country_code, location, prepaid FROM dthc_prepaid"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY sort_order, id"
    return [
        {
            "country_code": str(r["country_code"] or "").strip().upper(),
            "location": str(r["location"]),
            "prepaid": str(r["prepaid"]),
        }
        for r in conn.execute(q)
    ]


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
    CP_STRING_KEYS = {"Daily Spot Month", "Ocean Cost Method"}
    out: dict = {}
    for r in cur:
        k = r["cp_k"]
        if k is None or str(k).strip() == "":
            continue
        k = str(k).strip()
        v = r["cp_v"]
        if k in CP_STRING_KEYS:
            out[k] = str(v) if v is not None else ""
        else:
            try:
                out[k] = float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                out[k] = 0.0
    return out


def save_control_panel(data: dict) -> None:
    CP_STRING_KEYS = {"Daily Spot Month", "Ocean Cost Method"}
    conn = _get_conn()
    rows = []
    for k, v in data.items():
        if k in CP_STRING_KEYS:
            rows.append((k, str(v)))
        else:
            rows.append((k, float(v)))
    conn.executemany(
        "INSERT OR REPLACE INTO control_panel (key, value) VALUES (?, ?)",
        rows,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# consolidation
# ---------------------------------------------------------------------------

def get_consolidation() -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT region, bale, storage, month, otr_gri, storage_days, breaks FROM consolidation").fetchall()
    return {r["region"]: {"bale": r["bale"], "storage": r["storage"], "month": r["month"], "otr_gri": r["otr_gri"], "storage_days": r["storage_days"], "breaks": r["breaks"]} for r in rows}


def save_consolidation(data: dict) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM consolidation")
    conn.executemany(
        "INSERT INTO consolidation (region, bale, storage, month, otr_gri, storage_days, breaks) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (region, inner.get("bale", 0), inner.get("storage", 0), inner.get("month", 0), inner.get("otr_gri", 0), inner.get("storage_days", 0), inner.get("breaks", 0))
            for region, inner in data.items()
            if isinstance(inner, dict)
        ],
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
            "Container": r["contrainer"],
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
                inner.get("Container", 0),
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
        "SELECT country, code, lc, ins, cont, com, cof, ciq_qc, gri, "
        "cad_usa, cad_brz, cad_aus, lc_usa, lc_brz, lc_aus, coa_usa, coa_brz, coa_aus, "
        "usda_usd_bale, usda_pts_lb "
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
            "CAD_USA": r["cad_usa"],
            "CAD_BRZ": r["cad_brz"],
            "CAD_AUS": r["cad_aus"],
            "LC_USA": r["lc_usa"],
            "LC_BRZ": r["lc_brz"],
            "LC_AUS": r["lc_aus"],
            "COA_USA": r["coa_usa"],
            "COA_BRZ": r["coa_brz"],
            "COA_AUS": r["coa_aus"],
            "USDA_USD_BALE": r["usda_usd_bale"],
            "USDA_PTS_LB": r["usda_pts_lb"],
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
                float(row.get("CAD_USA") or 0),
                float(row.get("CAD_BRZ") or 0),
                float(row.get("CAD_AUS") or 0),
                float(row.get("LC_USA") or 0),
                float(row.get("LC_BRZ") or 0),
                float(row.get("LC_AUS") or 0),
                float(row.get("COA_USA") or 0),
                float(row.get("COA_BRZ") or 0),
                float(row.get("COA_AUS") or 0),
                float(row.get("USDA_USD_BALE") or 0),
                float(row.get("USDA_PTS_LB") or 0),
            )
        )
    conn.executemany(
        "INSERT INTO document_cif (country, code, lc, ins, cont, com, cof, ciq_qc, gri, "
        "cad_usa, cad_brz, cad_aus, lc_usa, lc_brz, lc_aus, coa_usa, coa_brz, coa_aus, "
        "usda_usd_bale, usda_pts_lb) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        params,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# lc_bank_cost
# ---------------------------------------------------------------------------

LC_BANK_COST_BANKS = [
    "FAB", "Rabo", "Societe Generale", "Credit Agricole", "Citibank",
    "Natixis", "Lloyds", "CBD", "Mashreq", "Erste", "ING", "Raiffeisen",
    "UBS", "MUFG", "UniCredit", "Granti", "Arab Bank", "KBC",
    "Commerzbank", "Intesa", "BCP", "Nexentbank", "BBVA", "Standard Chartered",
]

LC_BANK_COST_COUNTRY_CODES = [
    "CN", "VN", "KO", "JP", "MA", "TW", "ID", "TH",
    "BD", "PK", "IN", "TR", "MX", "PE", "CO", "EC", "GU", "HO", "ES", "OT",
]

_LC_BANK_COST_SEED: dict[str, dict[str, float | None]] = {
    "CN": {"FAB": 40, "Rabo": 16, "Societe Generale": 60, "Credit Agricole": 35, "Citibank": 30, "Natixis": 40, "Lloyds": 15, "CBD": 55, "Mashreq": 25, "Erste": 35, "ING": 35, "Raiffeisen": 30, "UBS": 50, "MUFG": 20, "UniCredit": 50, "Granti": 30, "Arab Bank": 55, "KBC": 25, "Commerzbank": 65, "Intesa": 30, "BCP": 45, "Nexentbank": 60, "BBVA": 80, "Standard Chartered": 50},
    "VN": {"FAB": 60, "Rabo": 65, "Societe Generale": 150, "Credit Agricole": 80, "Citibank": 155, "Natixis": 55, "CBD": 100, "Mashreq": 70, "ING": 60, "Raiffeisen": 60, "UBS": 45, "MUFG": 90, "UniCredit": 70, "Granti": 90, "KBC": 120, "Commerzbank": 70, "Intesa": 85, "BCP": 70, "Nexentbank": 115, "Standard Chartered": 100},
    "KO": {"FAB": 30, "Rabo": 50, "Societe Generale": 70, "Credit Agricole": 30, "Citibank": 15, "Natixis": 40, "Lloyds": 5, "CBD": 55, "Mashreq": 20, "Erste": 28, "ING": 40, "Raiffeisen": 20, "UBS": 50, "MUFG": 20, "UniCredit": 25, "Granti": 30, "Arab Bank": 55, "KBC": 25, "Commerzbank": 25, "Intesa": 35, "BBVA": 20, "Standard Chartered": 50},
    "TW": {"FAB": 20, "Rabo": 45, "Societe Generale": 90, "Credit Agricole": 35, "Citibank": 20, "Natixis": 40, "Lloyds": 15, "CBD": 55, "Mashreq": 20, "Erste": 35, "ING": 40, "Raiffeisen": 30, "UBS": 50, "MUFG": 40, "UniCredit": 50, "Granti": 30, "Arab Bank": 55, "KBC": 25, "Commerzbank": 80, "Intesa": 35, "BBVA": 55, "Standard Chartered": 250},
    "ID": {"FAB": 30, "Rabo": 50, "Societe Generale": 80, "Credit Agricole": 40, "Citibank": 40, "Natixis": 45, "Lloyds": 25, "CBD": 55, "Mashreq": 25, "Erste": 40, "ING": 40, "Raiffeisen": 35, "UBS": 60, "MUFG": 40, "UniCredit": 55, "Granti": 30, "Arab Bank": 80, "KBC": 60, "Commerzbank": 85, "Intesa": 40, "Standard Chartered": 150},
    "TH": {"FAB": 40, "Rabo": 55, "Societe Generale": 80, "Credit Agricole": 40, "Citibank": 50, "Natixis": 50, "Lloyds": 25, "CBD": 55, "Mashreq": 30, "Erste": 40, "ING": 40, "Raiffeisen": 40, "UBS": 60, "MUFG": 30, "UniCredit": 55, "Arab Bank": 80, "KBC": 30, "Commerzbank": 60, "Intesa": 40, "Standard Chartered": 50},
    "BD": {"FAB": 250, "Rabo": 250, "Citibank": 100, "Mashreq": 400, "ING": 100, "MUFG": 300, "Granti": 250, "Commerzbank": 300, "Intesa": 200, "Standard Chartered": 400},
    "PK": {"Citibank": 350, "CBD": 160, "Mashreq": 250, "UBS": 350, "UniCredit": 325, "Commerzbank": 300, "Intesa": 280, "Standard Chartered": 450},
    "IN": {"FAB": 40, "Rabo": 20, "Societe Generale": 80, "Credit Agricole": 65, "Citibank": 35, "Natixis": 45, "Lloyds": 34, "CBD": 55, "Mashreq": 25, "Erste": 50, "ING": 40, "Raiffeisen": 35, "UBS": 60, "MUFG": 30, "UniCredit": 70, "Granti": 40, "Arab Bank": 60, "KBC": 50, "Commerzbank": 55, "Intesa": 40, "Nexentbank": 100, "BBVA": 80, "Standard Chartered": 50},
    "TR": {"FAB": 130, "Rabo": 90, "Societe Generale": 160, "Credit Agricole": 130, "Citibank": 80, "Natixis": 100, "Lloyds": 90, "CBD": 160, "Mashreq": 95, "Erste": 150, "ING": 150, "Raiffeisen": 200, "UBS": 110, "MUFG": 100, "UniCredit": 75, "Granti": 100, "Arab Bank": 100, "KBC": 175, "Commerzbank": 250, "Intesa": 120, "BCP": 85, "BBVA": 170, "Standard Chartered": 250},
}


def get_lc_bank_cost() -> list[dict]:
    """Return LC bank cost data as a list of dicts, one per country_code, with bank names as keys."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT country_code, bank, value FROM lc_bank_cost ORDER BY id"
    ).fetchall()
    by_country: dict[str, dict] = {}
    for r in rows:
        cc = r["country_code"]
        if cc not in by_country:
            by_country[cc] = {"country_code": cc}
        by_country[cc][r["bank"]] = r["value"]
    # Ensure all country codes appear in order
    result = []
    for cc in LC_BANK_COST_COUNTRY_CODES:
        result.append(by_country.get(cc, {"country_code": cc}))
    # Include any extra country codes from DB not in the default list
    for cc, row in by_country.items():
        if cc not in LC_BANK_COST_COUNTRY_CODES:
            result.append(row)
    return result


def save_lc_bank_cost(data: list[dict]) -> None:
    """Save LC bank cost data. Each dict has country_code + bank name keys with numeric values."""
    conn = _get_conn()
    conn.execute("DELETE FROM lc_bank_cost")
    params: list[tuple] = []
    for row in data:
        cc = str(row.get("country_code", "")).strip()
        if not cc:
            continue
        for bank in LC_BANK_COST_BANKS:
            v = row.get(bank)
            if v is None or (isinstance(v, str) and not v.strip()):
                val = None
            else:
                try:
                    val = float(v)
                except (TypeError, ValueError):
                    val = None
            params.append((cc, bank, val))
    conn.executemany(
        "INSERT INTO lc_bank_cost (country_code, bank, value) VALUES (?, ?, ?)",
        params,
    )
    conn.commit()


_LC_BANK_COST_CN_BANKS = ("Rabo", "Credit Agricole", "Intesa")


def get_lc_bank_cost_avg_lowest_3() -> dict[str, float]:
    """Return {country_code: avg_of_lowest_3_values} from lc_bank_cost.
    Exception: CN uses the average of Rabo, Credit Agricole, and Intesa instead.
    """
    conn = _get_conn()
    # General: lowest 3 for all non-CN countries
    rows = conn.execute("""
        WITH ranked AS (
            SELECT country_code, value,
                   ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY value ASC) AS rn
            FROM lc_bank_cost
            WHERE value IS NOT NULL AND country_code != 'CN'
        )
        SELECT country_code, AVG(value) AS avg_lowest_3
        FROM ranked
        WHERE rn <= 3
        GROUP BY country_code
    """).fetchall()
    result = {r["country_code"]: r["avg_lowest_3"] for r in rows}
    # CN exception: average of specific banks
    cn_row = conn.execute(
        "SELECT AVG(value) AS avg_val FROM lc_bank_cost "
        "WHERE country_code = 'CN' AND bank IN (?, ?, ?) AND value IS NOT NULL",
        _LC_BANK_COST_CN_BANKS,
    ).fetchone()
    if cn_row and cn_row["avg_val"] is not None:
        result["CN"] = cn_row["avg_val"]
    return result


def _ensure_lc_bank_cost_seeded(conn: sqlite3.Connection) -> None:
    """Seed lc_bank_cost if the table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM lc_bank_cost").fetchone()[0]
    if count > 0:
        return
    params: list[tuple] = []
    for cc in LC_BANK_COST_COUNTRY_CODES:
        seed = _LC_BANK_COST_SEED.get(cc, {})
        for bank in LC_BANK_COST_BANKS:
            params.append((cc, bank, seed.get(bank)))
    conn.executemany(
        "INSERT INTO lc_bank_cost (country_code, bank, value) VALUES (?, ?, ?)",
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


_OCEAN_EXTRACT_KEY_FIELDS: tuple[str, ...] = (
    "unOrig",
    "unVia",
    "unDest",
    "dischargePort",
    "scacCode",
    "contractNumber",
    "rateType",
    "amendmentNumber",
    "effectiveDate",
    "expirationDate",
)

_OCEAN_EXTRACT_DATA_FIELDS: tuple[str, ...] = (
    "orig",
    "via",
    "dest",
    "carrierName",
    "updateTime",
    "40FT",
    "40HC",
    "DTHC40FT",
    "DTHC40HC",
    "ALLIN40FT",
    "ALLIN40HC",
)


def ocean_extract_compound_key(row: dict) -> str:
    """Unique lane/rate identity for 470OceanRatesExtract rows."""
    parts = [str(row.get(f, "") or "").strip().upper() for f in _OCEAN_EXTRACT_KEY_FIELDS]
    return "|".join(parts)


_OCEAN_EXTRACT_LANE_KEY_FIELDS: tuple[str, ...] = (
    "unOrig",
    "unVia",
    "unDest",
    "dischargePort",
    "scacCode",
    "contractNumber",
    "rateType",
)


def ocean_extract_lane_key(row: dict) -> str:
    """Lane identity without contract dates/amendment (for compare diagnostics)."""
    parts = [str(row.get(f, "") or "").strip().upper() for f in _OCEAN_EXTRACT_LANE_KEY_FIELDS]
    return "|".join(parts)


def country_code_from_undest(undest: str) -> str:
    """ISO country code from unDest (first two characters, e.g. CNQDG -> CN)."""
    return str(undest or "").strip().upper()[:2]


def ocean_extract_rows_differ(a: dict, b: dict) -> bool:
    for f in _OCEAN_EXTRACT_DATA_FIELDS:
        if str(a.get(f, "") or "").strip() != str(b.get(f, "") or "").strip():
            return True
    return False


def get_ocean_rates_extract_indexed(active_only: bool = True) -> dict[str, dict]:
    """compound_key -> {id, is_active?, ...extract columns}."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ocean_rates_extract'"
    ).fetchone():
        return {}
    col_rows = conn.execute("PRAGMA table_info(ocean_rates_extract)").fetchall()
    cols = [r[1] for r in col_rows]
    sel_cols = [c for c in cols if c != "id"]
    if not sel_cols:
        return {}
    has_active = "is_active" in cols
    sel = "id, " + ", ".join(_qident_sql(c) for c in sel_cols)
    q = f"SELECT {sel} FROM ocean_rates_extract"
    if active_only and has_active:
        q += " WHERE is_active = 1"
    out: dict[str, dict] = {}
    for row in conn.execute(q):
        rid = int(row[0])
        d = {sel_cols[i]: row[i + 1] for i in range(len(sel_cols))}
        is_act = int(d.get("is_active", 1) or 0) if has_active else 1
        data_only = {k: v for k, v in d.items() if k != "is_active"}
        key = ocean_extract_compound_key(
            {k: str(v or "").strip() if v is not None else "" for k, v in data_only.items()}
        )
        if not key.replace("|", "").strip():
            continue
        row_out = {
            "id": rid,
            **{k: str(v or "").strip() if v is not None else "" for k, v in data_only.items()},
        }
        if has_active:
            row_out["is_active"] = is_act
        out[key] = row_out
    return out


def apply_ocean_rates_extract_upload(uploaded_by_key: dict[str, dict]) -> dict[str, int]:
    """Merge uploaded extract rows: update/insert active rows; deactivate missing keys."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ocean_rates_extract'"
    ).fetchone():
        raise ValueError("ocean_rates_extract table does not exist")
    current_all = get_ocean_rates_extract_indexed(active_only=False)
    current_active = {k: v for k, v in current_all.items() if int(v.get("is_active", 1) or 0) == 1}
    cols_ordered = _ocean_rates_extract_ordered_columns(conn)
    insert_cols = [c for c in cols_ordered if c != "id"]
    if not insert_cols:
        raise ValueError("ocean_rates_extract has no data columns")

    upd_set = ", ".join(f"{_qident_sql(c)} = ?" for c in insert_cols)
    upd_sql = f"UPDATE ocean_rates_extract SET {upd_set} WHERE id = ?"
    ins_names = ", ".join(_qident_sql(c) for c in insert_cols)
    ins_ph = ", ".join("?" for _ in insert_cols)
    ins_sql = f"INSERT INTO ocean_rates_extract ({ins_names}) VALUES ({ins_ph})"

    updated = 0
    new = 0
    deactivated = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        for key, up_row in uploaded_by_key.items():
            payload = {c: _ocean_rates_extract_coerce_cell(c, up_row) for c in insert_cols}
            if "is_active" in insert_cols:
                payload["is_active"] = 1
            if key in current_all:
                ex = current_all[key]
                if ocean_extract_rows_differ(ex, up_row) or int(ex.get("is_active", 1) or 0) != 1:
                    vals = [payload[c] for c in insert_cols]
                    conn.execute(upd_sql, (*vals, ex["id"]))
                    updated += 1
            else:
                vals = [payload[c] for c in insert_cols]
                conn.execute(ins_sql, vals)
                new += 1
        if "is_active" in insert_cols:
            deact_sql = "UPDATE ocean_rates_extract SET is_active = 0 WHERE id = ?"
            for key, ex in current_active.items():
                if key not in uploaded_by_key:
                    conn.execute(deact_sql, (ex["id"],))
                    deactivated += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"updated": updated, "new": new, "deactivated": deactivated}


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


def _ocean_rates_extract_ordered_columns(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("PRAGMA table_info(ocean_rates_extract)").fetchall()
    return [r[1] for r in sorted(rows, key=lambda x: int(x[0]))]


def _ocean_rates_extract_coerce_cell(col: str, raw: dict) -> object:
    if col == "is_active":
        try:
            v = int(raw.get("is_active", 1))
            return 1 if v not in (0, 1) else v
        except (TypeError, ValueError):
            return 1
    v = raw.get(col)
    if v is None:
        return ""
    return str(v)


def list_ocean_rates_extract_for_jarvis() -> dict[str, object]:
    """Full table for Jarvis editor: column order + one dict per row (includes id, is_active)."""
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ocean_rates_extract'"
    ).fetchone():
        return {"columns": [], "rows": []}
    cols = _ocean_rates_extract_ordered_columns(conn)
    if not cols:
        return {"columns": [], "rows": []}
    sel = ", ".join(_qident_sql(c) for c in cols)
    out_rows: list[dict[str, object]] = []
    for row in conn.execute(f"SELECT {sel} FROM ocean_rates_extract ORDER BY id"):
        d = {cols[i]: row[i] for i in range(len(cols))}
        if "id" in d and d["id"] is not None:
            d["id"] = int(d["id"])
        if "is_active" in d and d["is_active"] is not None:
            d["is_active"] = int(d["is_active"])
        out_rows.append(d)
    return {"columns": cols, "rows": out_rows}


def delete_ocean_rates_extract_row(row_id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM ocean_rates_extract WHERE id = ?", (int(row_id),))
    conn.commit()
    return cur.rowcount > 0


def save_ocean_rates_extract_jarvis_rows(rows: list) -> dict[str, int]:
    """
    Upsert rows from Jarvis: positive integer id → UPDATE all non-id columns; else INSERT.
    """
    conn = _get_conn()
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ocean_rates_extract'"
    ).fetchone():
        raise ValueError("ocean_rates_extract table does not exist")
    cols_ordered = _ocean_rates_extract_ordered_columns(conn)
    if "id" not in cols_ordered:
        raise ValueError("ocean_rates_extract has no id column")
    insert_cols = [c for c in cols_ordered if c != "id"]
    if not insert_cols:
        raise ValueError("ocean_rates_extract has no data columns")

    upd_set = ", ".join(f"{_qident_sql(c)} = ?" for c in insert_cols)
    upd_sql = f"UPDATE ocean_rates_extract SET {upd_set} WHERE id = ?"
    ins_names = ", ".join(_qident_sql(c) for c in insert_cols)
    ins_ph = ", ".join("?" for _ in insert_cols)
    ins_sql = f"INSERT INTO ocean_rates_extract ({ins_names}) VALUES ({ins_ph})"

    n_ins = 0
    n_upd = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            vals = [_ocean_rates_extract_coerce_cell(c, raw) for c in insert_cols]
            rid = raw.get("id")
            try:
                rid_int = int(rid) if rid is not None and str(rid).strip() != "" else 0
            except (TypeError, ValueError):
                rid_int = 0
            if rid_int > 0:
                conn.execute(upd_sql, (*vals, rid_int))
                n_upd += 1
            else:
                conn.execute(ins_sql, vals)
                n_ins += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"inserted": n_ins, "updated": n_upd}


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


def _ensure_fsc_fuel_columns(conn: sqlite3.Connection) -> None:
    """Drop and recreate fsc_fuel if it has the old column names."""
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(fsc_fuel)").fetchall()}
    if cols and "fsc_percent" not in cols:
        conn.execute("DROP TABLE IF EXISTS fsc_fuel")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fsc_fuel (
                fuel_price   REAL PRIMARY KEY,
                fsc_percent  REAL NOT NULL DEFAULT 0,
                total_percent REAL NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


# ---------------------------------------------------------------------------
# fsc_fuel
# ---------------------------------------------------------------------------

def get_fsc_fuel() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT fuel_price, fsc_percent, total_percent FROM fsc_fuel ORDER BY fuel_price"
    ).fetchall()
    return [dict(r) for r in rows]


def save_fsc_fuel(rows: list[dict]) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM fsc_fuel")
    conn.executemany(
        "INSERT INTO fsc_fuel (fuel_price, fsc_percent, total_percent) VALUES (?, ?, ?)",
        [(float(r["fuel_price"]), float(r["fsc_percent"]), float(r["total_percent"])) for r in rows],
    )
    conn.commit()


def ensure_csv_tables_populated(data_dir: Path) -> None:
    """Called on server startup: seed OTR/SEAM/R&P tables from CSV if they're empty."""
    _migrate_otr_csv(data_dir)
    _migrate_seam_csv(data_dir)
    _migrate_rap_csv(data_dir)
