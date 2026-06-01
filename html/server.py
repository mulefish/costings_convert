import copy
import csv
import math
import os
import sys
import traceback
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
os.environ.setdefault("COSTINGS_DB_PATH", str(DATABASE_DIR / "costings.db"))
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from api import ocean_api as cargo_ocean_api  # noqa: E402

from flask import Flask, current_app, jsonify, render_template, request
import database as db

app = Flask(__name__)
UPLOAD_DIR = BASE_DIR / "csv_to_upload"

CONTROL_PANEL_DEFAULTS = {
    "Fuel Surcharge": 1.47,
    "OTR GRI": 0.00,
    "Ocean GRI": 250.0,
    "Buffer": 0.00,
    "Avg Purchase Price": 0.70,
    "SOFR": 0.00,
    "EDF Rate": 0.00,
    "EDF Interest Rate": 0.00,
    "Cert Interest": 0.00,
    "Origin Commission": 0.00,
    "Avg Bale Weight": 500.00,
    "Daily Spot": 0.00,
    "Basis": 0.00,
    "OTR FSC Multiplier": 1.50,
    "OTR Buffer (USD)": 50.00,
    "InAndOut": 2.7,
    "TotalStorage": 1.68,
}

CONSOLIDATION_DEFAULTS: dict = {
    "Dallas": {"bale": 2.7, "storage": 0.12, "month": 1.68},
    "Houston": {"bale": 2.7, "storage": 0.12, "month": 1.68},
    "Savannah": {"bale": 2.6, "storage": 0.12, "month": 1.68},
    "Memphis": {"bale": 2.5, "storage": 0.08, "month": 1.12},
    "Shelby": {"bale": 2.2, "storage": 0.037, "month": 0.51},
    "CIL(MX)": {"bale": 2.6, "storage": 0.08, "month": 1.12},
}

CONSOLIDATION_DAYS_STORAGE_DEFAULTS: dict = {
    "Days Storage": 14.0,
}

DRAYAGE_DEFAULTS: dict = {
    "Memphis": {
        "GRI": 0.0,
        "LineHaul": 255.0,
        "ChasSplit": 210.0,
        "Contrainer": 593.0,
        "Bale": 6.733,
        "OceanBase": 100.0,
        "Updated": "24-Jun",
    },
    "Savannah": {
        "GRI": 0.0,
        "LineHaul": 0.0,
        "ChasSplit": 0.0,
        "Contrainer": 485.0,
        "Bale": 5.511,
        "OceanBase": 100.0,
        "Updated": "24-Jun",
    },
    "Dallas": {
        "GRI": 0.0,
        "LineHaul": 270.0,
        "ChasSplit": 260.0,
        "Contrainer": 665.0,
        "Bale": 7.557,
        "OceanBase": 100.0,
        "Updated": "24-Jun",
    },
    "Houston": {
        "GRI": 0.0,
        "LineHaul": 0.0,
        "ChasSplit": 0.0,
        "Contrainer": 585.0,
        "Bale": 6.648,
        "OceanBase": 100.0,
        "Updated": "24-Jun",
    },
}

DOCUMENT_CIF_NUMERIC_KEYS = frozenset({
    "GRI", "LC", "INS", "CONT", "COM", "COF", "CIQ_QC",
    "CAD_USA", "CAD_BRZ", "CAD_AUS",
    "LC_USA", "LC_BRZ", "LC_AUS",
    "COA_USA", "COA_BRZ", "COA_AUS",
    "USDA_USD_BALE", "USDA_PTS_LB",
})

CIF_REGIONS_DEFAULT: tuple[str, ...] = (
    "WTX",
    "WTXH",
    "STEX",
    "Memphis Rule 5",
    "GA 30 Day",
    "Eastern Rule 5",
    "WTEX Equity",
    "STEX Equity",
    "Memphis Equity",
    "Dallas",
    "Houston",
)
USA_FORWARDING_COST_POST_KEYS = ("COO", "FHTO", "AVG_Shipment")
USA_FORWARDING_COST_DEFAULTS: dict = {
    "COO": 10.0,
    "FHTO": 125.0,
    "AVG_Shipment": "1320",
    "TOTAL": 1.53,
    "cif_regions": list(CIF_REGIONS_DEFAULT),
}

# In-memory caches loaded from SQLite on each request that needs them.
control_panel: dict = {}
consolidation: dict = {}
consolidation_days_storage: dict = {}
drayage: dict = {}
document_cif: list = []
usa_forwarding_cost: dict = {}
lc_bank_cost: list = []

# Must match html/static/db.js (USD/CIF lists match html/static/usd.js / cif.js get*ViewConfig order).
OTR_COLUMNS = (
    "Row",
    "Origin City",
    "Origin State",
    "Dest City",
    "Dest State",
    "Cargo Type",
    "LH",
    "FSC",
    "GRI",
    "Final",
    "PTS",
    "Last Updated",
    "Expiration",
    "Previous",
    "Delta",
)
OCEAN_COLUMNS = (
    "Row",
    "Port",
    "Destination",
    "Country",
    "DTHC Prepaid",
    "Delivery Type",
    "Code",
    "SCAC",
    "Ocean Freight",
    "GRI",
    "Ocean Total",
    "Total pts",
    "Updated",
    "Expiration",
    "Previous",
    "Delta",
)
SEAM_COLUMNS = (
    "Row",
    "Warehouse",
    "Name",
    "City",
    "State",
    "County",
    "Terms",
    "Verified",
    "Points",
    "Recv",
    "Strg",
    "Load",
    "Compr",
    "Class",
    "Mark",
    "EffDate",
    "Rail",
    "ICE Ref",
    "Capacity",
    "CertLoad",
    "CertCompr",
    "CertMark",
    "CertRecv",
    "CertStrg",
    "CertClass",
    "Min Storage",
    "Basis Adj.",
)
CERT_COLUMNS = (
    "Row",
    "Warehouse",
    "Name",
    "City",
    "State",
    "County",
    "Terms",
    "Verified",
    "Points",
    "Recv",
    "Strg",
    "Load",
    "Compr",
    "Class",
    "Mark",
    "EffDate",
    "Rail",
    "ICE Ref",
    "Capacity",
    "CertLoad",
    "CertCompr",
    "CertMark",
    "CertRecv",
    "CertStrg",
    "CertClass",
)
REGIONS_AND_PORTS_COLUMNS = (
    "Row",
    "Warehouse",
    "Name",
    "City",
    "State",
    "Region",
    "Export",
    "Port",
    "ESO",
    "Flat Bed Fees",
    "Late Fees",
    "Transportation Adjust",
    "Misc  Fees",
    "Consol Interest",
)

USD_COLUMNS = (
    "Row",
    "Warehouse",
    "Name",
    "City",
    "State",
    "Region",
    "Export",
    "Port",
    "Terms",
    "Recv",
    "Load",
    "Compr",
    "Class",
    "Mark",
    "Strg",
    "ESO",
    "Interest",
    "Origin Comm",
    "Total Equity",
    "Total Origin",
    "Flatbed",
    "Late Fee",
    "Transit Truck",
    "Total Transit",
    "Consol_Block",
    "Consol_Strg",
    "Consol_Interest",
    "Total_Consol",
    "Dray",
    "Ocean",
    "Total_Out",
    "Sight_LC",
    "Forwarding",
    "Controlling",
    "Insurance",
    "Total_Doc",
    "Dest_Commission",
    "Cost_of_Funds",
    "Qclaim",
    "Total_CIF",
    "Weslaco_Transit",
    "Shelby_Transit",
)

USD_PTS_ID_KEYS = frozenset(
    {
        "Row",
        "Warehouse",
        "Name",
        "City",
        "State",
        "Region",
        "Export",
        "Port",
        "Terms",
    }
)

PTS_COLUMNS = USD_COLUMNS + ("Cash", "Equity")

# CIF view: PTS-style minus warehouse columns and Weslaco/Shelby transit. Values = PTS averages per Region;
# Cash/Equity = sums of those averaged subtotals (not averages of PTS Cash/Equity).
CIF_COLUMNS = (
    "Row",
    "Region",
) + tuple(
    k
    for k in USD_COLUMNS
    if k
    not in (
        "Row",
        "Warehouse",
        "Name",
        "City",
        "State",
        "Region",
        "Export",
        "Port",
        "Weslaco_Transit",
        "Shelby_Transit",
    )
) + ("Cash", "Equity")

# USD column keys for PTS Total Terms (same keys as GET /api/usd rows).
PTS_CASH_SUM_KEYS = (
    "Total Origin",
    "Total Transit",
    "Total_Consol",
    "Total_Out",
    "Total_Doc",
    "Total_CIF",
)
PTS_EQUITY_SUM_KEYS = (
    "Total Equity",
    "Total Transit",
    "Total_Consol",
    "Total_Out",
    "Total_Doc",
    "Total_CIF",
)


def _round_half_up_int(x: float) -> int:
    """Nearest integer; halves (.5) round away from zero (e.g. 0.5→1, 0.49→0)."""
    return int(Decimal(str(float(x))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _round_half_up_2(x: float) -> float:
    """Round to 2 decimal places, half-up."""
    y = float(x)
    if math.isnan(y) or math.isinf(y):
        return 0.0
    return float(Decimal(str(y)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _usd_pts_cash_terms_usd(usd_row: dict) -> float:
    return sum(_to_float(usd_row.get(k), 0.0) for k in PTS_CASH_SUM_KEYS)


def _usd_pts_equity_terms_usd(usd_row: dict) -> float:
    return sum(_to_float(usd_row.get(k), 0.0) for k in PTS_EQUITY_SUM_KEYS)


def _usd_row_to_pts(usd_row: dict) -> dict:
    """PTS: USD × 20, each cell rounded half-up to 2 decimal places; Cash/Equity per Total-Terms rules × 20."""
    out: dict = {}
    for key in USD_COLUMNS:
        if key in USD_PTS_ID_KEYS:
            out[key] = usd_row.get(key, "")
            continue
        v = usd_row.get(key)
        if v == "" or v is None:
            out[key] = ""
            continue
        try:
            out[key] = _round_half_up_2(float(v) * 20.0)
        except (TypeError, ValueError):
            out[key] = v
    out["Cash"] = _round_half_up_2(_usd_pts_cash_terms_usd(usd_row) * 20.0)
    out["Equity"] = _round_half_up_2(_usd_pts_equity_terms_usd(usd_row) * 20.0)
    return out


def _row_with_columns(row, column_keys, default=""):
    """Ensure every API column key exists; use default for missing or None."""
    out = {}
    for key in column_keys:
        if key not in row:
            out[key] = default
            continue
        val = row[key]
        out[key] = default if val is None else val
    return out


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value):
    """Return a float, or None if the cell is missing, blank, or not numeric."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _otr_prior_base_rate(raw):
    """Prior line-haul (LH) from OTR_Rates.csv; first non-empty recognized column wins."""
    for key in (
        "PRIOR BASE RATE",
        "PREVIOUS BASE RATE",
        "PREVIOUS RATE",
        "PRIOR RATE",
    ):
        if key not in raw:
            continue
        prior = _optional_float(raw.get(key))
        if prior is not None:
            return prior
    return None


def _split_city_state(value):
    pieces = str(value or "").split(",", 1)
    city = pieces[0].strip()
    state = pieces[1].strip() if len(pieces) > 1 else ""
    return city, state


def _round2(value):
    x = float(value)
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return round(x, 2)


def _persist_control_panel() -> None:
    db.save_control_panel(control_panel)


def _recompute_control_panel_derived() -> None:
    """Recompute derived control panel values.
    EDF Interest Rate = SOFR + EDF Rate
    Cert Interest = ((Daily Spot + Basis) / 12) * EDF Interest Rate
    """
    sofr = _to_float(control_panel.get("SOFR"), 0.0)
    edf_rate = _to_float(control_panel.get("EDF Rate"), 0.0)
    control_panel["EDF Interest Rate"] = sofr + edf_rate
    daily_spot = _to_float(control_panel.get("Daily Spot"), 0.0)
    basis = _to_float(control_panel.get("Basis"), 0.0)
    control_panel["Cert Interest"] = round(((daily_spot + basis) / 12.0) * control_panel["EDF Interest Rate"], 2)


def _reload_control_panel() -> None:
    global control_panel
    loaded = db.get_control_panel()
    if loaded:
        merged = {k: loaded.get(k, v) for k, v in CONTROL_PANEL_DEFAULTS.items()}
        for k, v in loaded.items():
            if k not in merged:
                merged[k] = v
        control_panel = merged
    else:
        control_panel = dict(CONTROL_PANEL_DEFAULTS)
    _recompute_control_panel_derived()


def _sync_control_panel_from_disk_if_needed() -> None:
    _reload_control_panel()


def _init_control_panel() -> None:
    global control_panel
    loaded = db.get_control_panel()
    if loaded:
        merged = {k: loaded.get(k, v) for k, v in CONTROL_PANEL_DEFAULTS.items()}
        for k, v in loaded.items():
            if k not in merged:
                merged[k] = v
        control_panel = merged
    else:
        control_panel = dict(CONTROL_PANEL_DEFAULTS)
        db.save_control_panel(control_panel)
    _recompute_control_panel_derived()


def _deep_copy_consolidation_defaults() -> dict:
    return copy.deepcopy(CONSOLIDATION_DEFAULTS)


def _days_storage_factor() -> float:
    """Days multiplier from consolidation_days_storage (key Days Storage)."""
    return float(
        consolidation_days_storage.get(
            "Days Storage",
            CONSOLIDATION_DAYS_STORAGE_DEFAULTS["Days Storage"],
        )
    )


def _usd_consolidation_interest(
    avg_purchase: float,
    edf_rate_pct: float,
    avg_bale_wt: float,
    days_storage: float,
) -> float:
    """USD Consolidation Interest (same every row).

    (Avg Purchase Price × EDF Interest Rate as percent × Avg Bale Weight) / 52
    × (Consolidation days storage "Days Storage" / 7).
    """
    if not avg_purchase or not edf_rate_pct or not avg_bale_wt:
        return 0.0
    ds = float(days_storage) if days_storage else 0.0
    return (
        (avg_purchase * (edf_rate_pct / 100.0) * avg_bale_wt)
        / 52.0
        * (ds / 7.0)
    )


def _consolidation_region_key_for_port(port: str) -> str | None:
    """Map USD export Port to a key in consolidation.json (Control Panel consolidation table)."""
    p = str(port or "").strip()
    if not p:
        return None
    by_upper = {str(k).upper(): k for k in consolidation}
    u = p.upper()
    if u in by_upper:
        return by_upper[u]
    # Ports not named as consolidation regions (see regions_and_ports.csv).
    if u == "WESLACO" and "Houston" in consolidation:
        return "Houston"
    return None


def _usd_consolidation_in_and_out_for_port(port: str) -> float:
    """InAndOut for USD Consolidation: consolidation region bale for Port, else Control Panel InAndOut."""
    region = _consolidation_region_key_for_port(port)
    if region:
        inner = consolidation.get(region)
        if isinstance(inner, dict):
            return _to_float(inner.get("bale"), 0.0)
    return _to_float(control_panel.get("InAndOut"), 0.0)


def _usd_consolidation_total_storage_for_port(port: str) -> float:
    """Consol_Strg (TotalStorage column): consolidation region month (Storage × Days Storage), else CP TotalStorage."""
    region = _consolidation_region_key_for_port(port)
    if region:
        inner = consolidation.get(region)
        if isinstance(inner, dict):
            return _to_float(inner.get("month"), 0.0)
    return _to_float(control_panel.get("TotalStorage"), 0.0)


def _drayage_field_for_port(port: str, field: str) -> float:
    """Lookup numeric field in the SQLite `drayage` table (in-memory `drayage` dict from db.get_drayage()) by export Port.

    Port maps to a drayage region the same way as consolidation (Weslaco → Houston, etc.). Field names match
    Jarvis / API keys: Bale, OceanBase, GRI, LineHaul, ChasSplit, Contrainer, Updated.
    """
    region = _consolidation_region_key_for_port(port)
    if region and region in drayage:
        inner = drayage.get(region)
        if isinstance(inner, dict):
            return _to_float(inner.get(field), 0.0)
    p = str(port or "").strip()
    if p:
        by_upper = {str(k).upper(): k for k in drayage}
        direct = by_upper.get(p.upper())
        if direct:
            inner = drayage.get(direct)
            if isinstance(inner, dict):
                return _to_float(inner.get(field), 0.0)
    return 0.0


def _document_cif_float_for_country(country: str, field: str) -> float:
    """Lookup a numeric field in document_cif list rows matched by country name (case-insensitive)."""
    tgt = _normalize_key(country)
    if not tgt:
        return 0.0
    for row in document_cif:
        if not isinstance(row, dict):
            continue
        if _normalize_key(row.get("country")) != tgt:
            continue
        return _to_float(row.get(field), 0.0)
    return 0.0


def _apply_consolidation_month_formula() -> None:
    """Month = storage * Days Storage (consolidation_days_storage)."""
    factor = _days_storage_factor()
    for inner in consolidation.values():
        if not isinstance(inner, dict):
            continue
        if "storage" not in inner:
            continue
        try:
            inner["month"] = float(inner["storage"]) * factor
        except (TypeError, ValueError):
            pass


def _merge_consolidation_loaded(loaded: dict) -> dict:
    out = _deep_copy_consolidation_defaults()
    if not isinstance(loaded, dict):
        return out
    for region, inner in loaded.items():
        region_key = str(region).strip()
        if not region_key or not isinstance(inner, dict):
            continue
        if region_key not in out:
            out[region_key] = {}
        for sk, sv in inner.items():
            sks = str(sk).strip()
            try:
                out[region_key][sks] = float(sv)
            except (TypeError, ValueError):
                pass
    return out


def _persist_consolidation() -> None:
    db.save_consolidation(consolidation)


def _reload_consolidation() -> None:
    global consolidation
    loaded = db.get_consolidation()
    if loaded:
        consolidation = _merge_consolidation_loaded(loaded)
    else:
        consolidation = _deep_copy_consolidation_defaults()
    _apply_consolidation_month_formula()


def _reload_consolidation_from_disk() -> None:
    _reload_consolidation()


def _init_consolidation() -> None:
    global consolidation
    loaded = db.get_consolidation()
    if loaded:
        consolidation = _merge_consolidation_loaded(loaded)
    else:
        consolidation = _deep_copy_consolidation_defaults()
    _apply_consolidation_month_formula()
    if not loaded:
        db.save_consolidation(consolidation)


def _persist_consolidation_days_storage() -> None:
    db.save_consolidation_days_storage(consolidation_days_storage)


def _reload_consolidation_days_storage() -> None:
    global consolidation_days_storage
    loaded = db.get_consolidation_days_storage()
    merged = dict(CONSOLIDATION_DAYS_STORAGE_DEFAULTS)
    merged.update(loaded)
    consolidation_days_storage = merged


def _reload_consolidation_days_storage_from_disk() -> None:
    _reload_consolidation_days_storage()


def _init_consolidation_days_storage() -> None:
    global consolidation_days_storage
    loaded = db.get_consolidation_days_storage()
    merged = dict(CONSOLIDATION_DAYS_STORAGE_DEFAULTS)
    merged.update(loaded)
    consolidation_days_storage = merged
    if not db.get_consolidation_days_storage().get("Days Storage"):
        db.save_consolidation_days_storage(consolidation_days_storage)


def _merge_drayage_loaded(loaded: dict) -> dict:
    out = copy.deepcopy(DRAYAGE_DEFAULTS)
    if not isinstance(loaded, dict):
        return out
    for region, inner in loaded.items():
        region_key = str(region).strip()
        if not region_key or not isinstance(inner, dict):
            continue
        if region_key not in out:
            out[region_key] = {}
        for sk, sv in inner.items():
            sks = str(sk).strip()
            if sks == "Updated":
                out[region_key][sks] = str(sv).strip() if sv is not None else ""
            else:
                try:
                    out[region_key][sks] = float(sv)
                except (TypeError, ValueError):
                    pass
    return out


def _persist_drayage() -> None:
    db.save_drayage(drayage)


def _reload_drayage() -> None:
    global drayage
    loaded = db.get_drayage()
    if loaded:
        drayage = _merge_drayage_loaded(loaded)
    else:
        drayage = copy.deepcopy(DRAYAGE_DEFAULTS)


def _reload_drayage_from_disk() -> None:
    _reload_drayage()


def _init_drayage() -> None:
    global drayage
    loaded = db.get_drayage()
    if loaded:
        drayage = _merge_drayage_loaded(loaded)
    else:
        drayage = copy.deepcopy(DRAYAGE_DEFAULTS)
        db.save_drayage(drayage)


def _document_cif_dthc_prepaid(row: dict) -> str:
    """Yes/No from dthc_prepaid by ISO code (preferred) or country name."""
    code = str(row.get("code", "")).strip().upper()
    if len(code) >= 2:
        return db.get_dthc_prepaid_by_country_code(code[:2], "Yes")
    return db.get_dthc_prepaid_for_country(str(row.get("country", "")).strip(), "Yes")


def _document_cif_with_prepaid(rows: list) -> list:
    edf = _to_float(control_panel.get("EDF Interest Rate"), 0.0)
    daily_spot = _to_float(control_panel.get("Daily Spot"), 0.0)
    basis = _to_float(control_panel.get("Basis"), 0.0)
    cof_factor = edf * daily_spot
    com_value = round(daily_spot + basis * 0.1)
    ins_value = round((daily_spot + basis) * 0.1)
    avg_by_cc = db.get_lc_bank_cost_avg_lowest_3()
    lc_multiplier = daily_spot + basis
    result = []
    for r in rows:
        row = {**r, "dthc_prepaid": _document_cif_dthc_prepaid(r)}
        cc = str(row.get("code", "")).strip().upper()
        avg_cost = avg_by_cc.get(cc, 0.0)
        row["LC"] = round((avg_cost * 0.01) * lc_multiplier)
        row["INS"] = ins_value
        lc_usa = _to_float(row.get("LC_USA"), 0.0)
        row["COF"] = round((lc_usa / 365.0) * cof_factor)
        row["COM"] = com_value
        result.append(row)
    return result


def _normalize_document_cif_row(raw: dict) -> dict:
    out: dict = {
        "country": str(raw.get("country", "")).strip(),
        "code": str(raw.get("code", "")).strip(),
    }
    for k in DOCUMENT_CIF_NUMERIC_KEYS:
        v = raw.get(k)
        default_zero = k == "GRI" or k.startswith(("CAD_", "LC_", "COA_", "USDA_"))
        if default_zero:
            if v is None:
                out[k] = 0.0
                continue
            if isinstance(v, str) and not str(v).strip():
                out[k] = 0.0
                continue
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = 0.0
            continue
        if v is None:
            out[k] = None
            continue
        if isinstance(v, str) and not str(v).strip():
            out[k] = None
            continue
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = None
    return out


def _merge_document_cif_loaded(loaded) -> list:
    if not isinstance(loaded, list):
        return []
    return [_normalize_document_cif_row(r) for r in loaded if isinstance(r, dict)]


def _ceil5(x: float) -> int:
    """Round up to the nearest multiple of 5."""
    import math
    return int(math.ceil(x / 5.0)) * 5


def _recompute_document_cif_computed() -> None:
    """Overwrite computed columns on every in-memory document_cif row.
    LC  = round((avg_lowest_3 * 0.01) * (Daily Spot + Basis))
    INS = round((Daily Spot + Basis) * 0.1)
    COF = round((LC_USA / 365) * (EDF Interest Rate * Daily Spot))
    COM = round(Daily Spot + Basis * 0.1)
    USDA_PTS_LB = ceil5(((USD/Bale * 90) / 20) / 22.046 * 100)
    """
    edf = _to_float(control_panel.get("EDF Interest Rate"), 0.0)
    daily_spot = _to_float(control_panel.get("Daily Spot"), 0.0)
    basis = _to_float(control_panel.get("Basis"), 0.0)
    cof_factor = edf * daily_spot
    com_value = round(daily_spot + basis * 0.1)
    ins_value = round((daily_spot + basis) * 0.1)
    avg_by_cc = db.get_lc_bank_cost_avg_lowest_3()
    lc_multiplier = daily_spot + basis
    for row in document_cif:
        cc = str(row.get("code", "")).strip().upper()
        avg_cost = avg_by_cc.get(cc, 0.0)
        row["LC"] = round((avg_cost * 0.01) * lc_multiplier)
        row["INS"] = ins_value
        lc_usa = _to_float(row.get("LC_USA"), 0.0)
        row["COF"] = round((lc_usa / 365.0) * cof_factor)
        row["COM"] = com_value
        usd_bale = _to_float(row.get("USDA_USD_BALE"), 0.0)
        if usd_bale:
            row["USDA_PTS_LB"] = _ceil5(((usd_bale * 90) / 20) / 22.046 * 100)
        else:
            row["USDA_PTS_LB"] = 0


def _persist_document_cif() -> None:
    _recompute_document_cif_computed()
    db.save_document_cif(document_cif)


def _reload_document_cif() -> None:
    global document_cif
    loaded = db.get_document_cif()
    document_cif = _merge_document_cif_loaded(loaded)
    _recompute_document_cif_computed()


def _reload_document_cif_from_disk() -> None:
    _reload_document_cif()


def _init_document_cif() -> None:
    global document_cif
    loaded = db.get_document_cif()
    if loaded:
        document_cif = _merge_document_cif_loaded(loaded)
    else:
        document_cif = []
        db.save_document_cif(document_cif)
    _recompute_document_cif_computed()


def _recompute_usa_forwarding_total() -> None:
    c = usa_forwarding_cost
    s = _to_float(c.get("COO"), 0.0) + _to_float(c.get("FHTO"), 0.0)
    divisor = _to_float(c.get("AVG_Shipment"), 88.0)
    if divisor == 0.0:
        divisor = 88.0
    c["TOTAL"] = _round2(s / divisor)


def _persist_usa_forwarding_cost() -> None:
    db.save_usa_forwarding_cost(usa_forwarding_cost)


def _reload_usa_forwarding_cost() -> None:
    global usa_forwarding_cost
    loaded = db.get_usa_forwarding_cost()
    if loaded:
        usa_forwarding_cost = loaded
    else:
        usa_forwarding_cost = dict(USA_FORWARDING_COST_DEFAULTS)
    _recompute_usa_forwarding_total()


def _reload_usa_forwarding_cost_from_disk() -> None:
    _reload_usa_forwarding_cost()


def _init_usa_forwarding_cost() -> None:
    global usa_forwarding_cost
    loaded = db.get_usa_forwarding_cost()
    if loaded and loaded.get("COO") is not None:
        usa_forwarding_cost = loaded
        _recompute_usa_forwarding_total()
    else:
        usa_forwarding_cost = dict(USA_FORWARDING_COST_DEFAULTS)
        _recompute_usa_forwarding_total()
        db.save_usa_forwarding_cost(usa_forwarding_cost)


def _reload_lc_bank_cost() -> None:
    global lc_bank_cost
    lc_bank_cost = db.get_lc_bank_cost()


def _init_lc_bank_cost() -> None:
    global lc_bank_cost
    lc_bank_cost = db.get_lc_bank_cost()


def _normalize_key(value):
    return " ".join(str(value or "").strip().split()).upper()


def _transit_lookup_dest_port_names() -> list[str]:
    """Distinct DEST_PORT labels from otr_transit_lookup, longest first for substring matching."""
    path = DATA_DIR / "excel_orig" / "otr_transit_lookup.csv"
    ports: set[str] = set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle, skipinitialspace=True):
                p = str(raw.get("DEST_PORT", "")).strip()
                if p:
                    ports.add(p)
    except OSError:
        pass
    return sorted(ports, key=len, reverse=True)


def _otr_destination_port_token(raw: dict, port_names_sorted: list[str]) -> str | None:
    """Map an OTR_Rates destination to a USD / transit_lookup-style port name."""
    dest_city, dest_state = _split_city_state(raw.get("DESTINATIONCITY"))
    dest_field = str(raw.get("DESTINATION", "") or "")
    state_u = (dest_state or "").upper()
    dc_norm = _normalize_key(dest_city)
    blob = _normalize_key(f"{dest_city} {dest_state} {dest_field}")

    if dc_norm == "GARDEN CITY" and "GA" in state_u:
        return "Savannah"
    if dc_norm == "GARDEN CITY" and "TX" in state_u:
        return "Houston"
    if "WESLACO" in blob:
        return "Weslaco"
    if "MEMPHIS" in blob:
        return "Memphis"
    if "HOUSTON" in blob or "PASADENA" in blob or "BAYTOWN" in blob:
        return "Houston"
    if "DALLAS" in blob:
        return "Dallas"
    if dc_norm == "SHELBY" and "NC" in state_u:
        return "Shelby"

    for p in port_names_sorted:
        pn = _normalize_key(p)
        if len(pn) >= 3 and pn in blob:
            return p
    return None


def _otr_final_lookup_from_db(fsc: float, otr_gri: float) -> dict:
    """Per (origin city, port): max OTR Final from otr_rates table."""
    out: dict = {}
    port_names = _transit_lookup_dest_port_names()
    db_rows = db.get_otr_rates(active_only=True)
    for r in db_rows:
        origin_city = r.get("origin_city", "")
        csv_compat = {
            "DESTINATIONCITY": f"{r.get('dest_city', '')}, {r.get('dest_state', '')}",
            "DESTINATION": "",
        }
        port_tok = _otr_destination_port_token(csv_compat, port_names)
        if not port_tok:
            continue
        lh = _to_float(r.get("base_rate"), 0.0)
        final = lh * fsc + otr_gri
        k = (_normalize_key(origin_city), _normalize_key(port_tok))
        out[k] = max(final, out.get(k, 0.0))
    return out


_init_control_panel()
_init_consolidation_days_storage()
_init_consolidation()
_init_drayage()
_init_document_cif()
_init_usa_forwarding_cost()
_init_lc_bank_cost()
if DATA_DIR.is_dir():
    db.ensure_csv_tables_populated(DATA_DIR)


@app.route("/api/usa-forwarding-cost", methods=["GET", "PUT", "POST"])
def usa_forwarding_cost_api():
    if request.method == "GET":
        _reload_usa_forwarding_cost()
        _recompute_usa_forwarding_total()
        return jsonify(usa_forwarding_cost)
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    clean: dict = {}
    for key in USA_FORWARDING_COST_POST_KEYS:
        if key not in payload:
            return jsonify({"error": f"Missing key {key!r}"}), 400
    try:
        clean["COO"] = float(payload["COO"])
        clean["FHTO"] = float(payload["FHTO"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid number for COO or FHTO"}), 400
    try:
        clean["AVG_Shipment"] = str(float(payload["AVG_Shipment"]))
    except (TypeError, ValueError):
        return jsonify({"error": "AVG_Shipment must be a number"}), 400
    preserved_cif_regions = usa_forwarding_cost.get("cif_regions")
    usa_forwarding_cost.clear()
    usa_forwarding_cost.update(clean)
    if isinstance(preserved_cif_regions, list):
        usa_forwarding_cost["cif_regions"] = preserved_cif_regions
    _recompute_usa_forwarding_total()
    _persist_usa_forwarding_cost()
    return jsonify(usa_forwarding_cost)


@app.route("/api/document-cif", methods=["GET", "PUT", "POST"])
def document_cif_api():
    if request.method == "GET":
        _reload_document_cif()
        return jsonify(_document_cif_with_prepaid(document_cif))
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "JSON array required"}), 400
    clean: list = []
    for i, raw in enumerate(payload):
        if not isinstance(raw, dict):
            return jsonify({"error": f"Row {i} must be an object"}), 400
        row = {
            "country": str(raw.get("country", "")).strip(),
            "code": str(raw.get("code", "")).strip(),
        }
        for k in DOCUMENT_CIF_NUMERIC_KEYS:
            v = raw.get(k)
            _default_zero = k == "GRI" or k.startswith(("CAD_", "LC_", "COA_", "USDA_"))
            if _default_zero:
                if v is None:
                    row[k] = 0.0
                elif isinstance(v, str) and not str(v).strip():
                    row[k] = 0.0
                else:
                    try:
                        row[k] = float(v)
                    except (TypeError, ValueError):
                        return (
                            jsonify(
                                {"error": f"Invalid number for row {i} field {k!r}"},
                            ),
                            400,
                        )
                continue
            if v is None:
                row[k] = None
            elif isinstance(v, str) and not str(v).strip():
                row[k] = None
            else:
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    return (
                        jsonify(
                            {"error": f"Invalid number for row {i} field {k!r}"},
                        ),
                        400,
                    )
        clean.append(row)
    document_cif.clear()
    document_cif.extend(clean)
    _persist_document_cif()
    return jsonify(_document_cif_with_prepaid(document_cif))


@app.route("/api/lc-bank-cost", methods=["GET", "POST"])
def lc_bank_cost_api():
    global lc_bank_cost
    if request.method == "GET":
        _reload_lc_bank_cost()
        return jsonify({"banks": db.LC_BANK_COST_BANKS, "rows": lc_bank_cost})
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "JSON array required"}), 400
    db.save_lc_bank_cost(payload)
    _reload_lc_bank_cost()
    return jsonify({"banks": db.LC_BANK_COST_BANKS, "rows": lc_bank_cost})


@app.route("/api/control-panel", methods=["GET", "PUT", "POST"])
def control_panel_api():
    if request.method == "GET":
        _reload_control_panel()
        return jsonify(control_panel)
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    for key in CONTROL_PANEL_DEFAULTS:
        if key not in payload:
            continue
        try:
            control_panel[key] = float(payload[key])
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid number for {key!r}"}), 400
    _recompute_control_panel_derived()
    _persist_control_panel()
    return jsonify(control_panel)


@app.route("/api/consolidation", methods=["GET", "PUT", "POST"])
def consolidation_api():
    if request.method == "GET":
        _reload_consolidation_days_storage()
        _reload_consolidation()
        return jsonify(consolidation)
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    clean: dict = {}
    for region, inner in payload.items():
        region_key = str(region).strip()
        if not region_key:
            continue
        if not isinstance(inner, dict):
            return jsonify({"error": f"Invalid value for region {region_key!r}"}), 400
        clean[region_key] = {}
        for sk, sv in inner.items():
            try:
                clean[region_key][str(sk).strip()] = float(sv)
            except (TypeError, ValueError):
                return jsonify({"error": f"Invalid number for {region_key}.{sk}"}), 400
    _reload_consolidation_days_storage()
    factor = _days_storage_factor()
    for inner in clean.values():
        if isinstance(inner, dict) and "storage" in inner:
            try:
                inner["month"] = float(inner["storage"]) * factor
            except (TypeError, ValueError):
                pass
    consolidation.clear()
    consolidation.update(clean)
    _persist_consolidation()
    return jsonify(consolidation)


@app.route("/api/consolidation-days-storage", methods=["GET", "PUT", "POST"])
def consolidation_days_storage_api():
    if request.method == "GET":
        _reload_consolidation_days_storage()
        return jsonify(consolidation_days_storage)
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    for key in CONSOLIDATION_DAYS_STORAGE_DEFAULTS:
        if key not in payload:
            continue
        try:
            consolidation_days_storage[key] = float(payload[key])
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid number for {key!r}"}), 400
    _persist_consolidation_days_storage()
    _apply_consolidation_month_formula()
    _persist_consolidation()
    return jsonify(consolidation_days_storage)


@app.route("/api/drayage", methods=["GET", "PUT", "POST"])
def drayage_api():
    if request.method == "GET":
        _reload_drayage()
        return jsonify(drayage)
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    clean: dict = {}
    for region, inner in payload.items():
        region_key = str(region).strip()
        if not region_key:
            continue
        if not isinstance(inner, dict):
            return jsonify({"error": f"Invalid value for region {region_key!r}"}), 400
        clean[region_key] = {}
        for sk, sv in inner.items():
            sks = str(sk).strip()
            if sks == "Updated":
                clean[region_key][sks] = str(sv).strip() if sv is not None else ""
            else:
                try:
                    clean[region_key][sks] = float(sv)
                except (TypeError, ValueError):
                    return (
                        jsonify({"error": f"Invalid number for {region_key}.{sk}"}),
                        400,
                    )
    drayage.clear()
    drayage.update(clean)
    _persist_drayage()
    return jsonify(drayage)


@app.route("/api/notes", methods=["GET", "POST"])
def notes_api():
    if request.method == "GET":
        return jsonify(db.get_notes())
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    title = str(payload.get("title", "")).strip()
    body = str(payload.get("body", "")).strip()
    note_id = payload.get("id")
    if note_id is not None:
        try:
            note_id = int(note_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid note id"}), 400
    saved = db.save_note(note_id, title, body)
    return jsonify(saved)


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def notes_delete_api(note_id):
    if db.delete_note(note_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Note not found"}), 404


@app.route("/api/db-tables")
def db_tables_api():
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return jsonify([r["name"] for r in rows])


@app.route("/api/db-active-counts")
def db_active_counts_api():
    """Per-table counts of is_active=1 and is_active=0 (Notes summary view)."""
    conn = db._get_conn()
    table_names = [
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    rows = []
    for tbl in table_names:
        table_cols = {row[1] for row in conn.execute(f"PRAGMA table_info([{tbl}])").fetchall()}
        if "is_active" not in table_cols:
            total = conn.execute(f"SELECT COUNT(*) AS n FROM [{tbl}]").fetchone()["n"]  # noqa: S608
            rows.append(
                {
                    "table": tbl,
                    "has_is_active": False,
                    "active": None,
                    "inactive": None,
                    "total": int(total or 0),
                }
            )
            continue
        agg = conn.execute(
            f"""
            SELECT
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_n,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive_n,
                COUNT(*) AS total_n
            FROM [{tbl}]
            """  # noqa: S608
        ).fetchone()
        rows.append(
            {
                "table": tbl,
                "has_is_active": True,
                "active": int(agg["active_n"] or 0),
                "inactive": int(agg["inactive_n"] or 0),
                "total": int(agg["total_n"] or 0),
            }
        )
    return jsonify({"rows": rows})


@app.route("/api/db-query")
def db_query_api():
    table = request.args.get("table", "").strip()
    active_filter = request.args.get("active_filter", "").strip().lower()
    if not active_filter:
        # Backward compat: active_only=1 → active; otherwise all rows.
        active_filter = "active" if request.args.get("active_only", "0") == "1" else "all"
    if active_filter not in ("active", "inactive", "all"):
        return jsonify({"error": f"Invalid active_filter: {active_filter}"}), 400
    conn = db._get_conn()
    valid = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if table not in valid:
        return jsonify({"error": f"Table not found: {table}"}), 400
    try:
        table_cols = {row[1] for row in conn.execute(f"PRAGMA table_info([{table}])").fetchall()}
        has_is_active = "is_active" in table_cols
        if has_is_active and active_filter == "active":
            cur = conn.execute(f"SELECT * FROM [{table}] WHERE is_active = 1")  # noqa: S608
        elif has_is_active and active_filter == "inactive":
            cur = conn.execute(f"SELECT * FROM [{table}] WHERE is_active = 0")  # noqa: S608
        else:
            cur = conn.execute(f"SELECT * FROM [{table}]")  # noqa: S608
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return jsonify({"columns": columns, "rows": rows, "has_is_active": has_is_active})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/db-search")
def db_search_api():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    conn = db._get_conn()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    pattern = f"%{q}%"
    results = []
    for tbl in tables:
        try:
            cols_info = conn.execute(f"PRAGMA table_info([{tbl}])").fetchall()
            text_cols = [row[1] for row in cols_info if row[2].upper() in ("TEXT", "VARCHAR", "BLOB", "")]
            if not text_cols:
                continue
            where = " OR ".join(f'CAST([{c}] AS TEXT) LIKE ?' for c in text_cols)
            cur = conn.execute(
                f"SELECT * FROM [{tbl}] WHERE {where}",  # noqa: S608
                [pattern] * len(text_cols),
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            if rows:
                results.append({"table": tbl, "columns": columns, "rows": rows})
        except Exception:
            continue
    return jsonify({"results": results, "query": q})


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/mermaid-demo")
def mermaid_demo():
    return render_template("mermaid-demo.html")


@app.route("/api/otr")
def otr_rows():
    try:
        _sync_control_panel_from_disk_if_needed()
        fsc = _to_float(control_panel.get("Fuel Surcharge"), 0.0)
        otr_gri = _to_float(control_panel.get("OTR GRI"), 0.0)
        rows = []
        db_rows = db.get_otr_rates(active_only=True)
        for idx, raw in enumerate(db_rows, start=1):
            lh = _to_float(raw.get("base_rate"), 0.0)
            prior_lh = raw.get("prior_base_rate")
            final = lh * fsc + otr_gri
            pts = (final / 88.0) * 20.0
            if prior_lh is None:
                previous_cell = ""
                delta_cell = ""
            else:
                previous_cell = _round2(prior_lh)
                delta_cell = _round2(lh - prior_lh)
            rows.append(
                {
                    "Row": idx,
                    "Origin City": raw.get("origin_city", ""),
                    "Origin State": raw.get("origin_state", ""),
                    "Dest City": raw.get("dest_city", ""),
                    "Dest State": raw.get("dest_state", ""),
                    "Cargo Type": raw.get("cargo_type", ""),
                    "LH": _round2(lh),
                    "FSC": _round2(fsc),
                    "GRI": _round2(otr_gri),
                    "Final": _round2(final),
                    "PTS": _round2(pts),
                    "Last Updated": raw.get("update_date", ""),
                    "Expiration": raw.get("expiration_date", ""),
                    "Previous": previous_cell,
                    "Delta": delta_cell,
                }
            )
        return jsonify({"rows": [_row_with_columns(r, OTR_COLUMNS) for r in rows]})
    except Exception as exc:
        if current_app.debug:
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500
        return jsonify({"error": "OTR request failed; enable Flask debug for details."}), 500


# --- OTR local file compare / apply ---

def _parse_otr_upload(filepath: Path) -> dict[str, float]:
    """Parse an OTR upload file (csv or xlsx) into {compound_key: LH}.
    Compound key = 'origcity|origstate|destcity|deststate' uppercased."""
    rows: dict[str, float] = {}
    ext = filepath.suffix.lower()
    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(str(filepath), read_only=True, data_only=True)
        ws = wb.active
        headers = None
        for row in ws.iter_rows(values_only=True):
            if headers is None:
                headers = [str(h or "").strip() for h in row]
                continue
            d = dict(zip(headers, row))
            oc = str(d.get("Origin City", "") or "").strip().upper()
            os_ = str(d.get("Origin State", "") or "").strip().upper()
            dc = str(d.get("Dest City", "") or "").strip().upper()
            ds = str(d.get("Dest State", "") or "").strip().upper()
            lh = _to_float(d.get("LH"), None)
            if oc and dc and lh is not None:
                key = f"{oc}|{os_}|{dc}|{ds}"
                rows[key] = lh
        wb.close()
    else:
        import io
        text = filepath.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
        for raw in reader:
            oc = str(raw.get("Origin City", "")).strip().upper()
            os_ = str(raw.get("Origin State", "")).strip().upper()
            dc = str(raw.get("Dest City", "")).strip().upper()
            ds = str(raw.get("Dest State", "")).strip().upper()
            lh = _to_float(raw.get("LH"), None)
            if oc and dc and lh is not None:
                key = f"{oc}|{os_}|{dc}|{ds}"
                rows[key] = lh
    return rows


@app.route("/api/otr/local-files")
def otr_local_files():
    files = []
    if UPLOAD_DIR.is_dir():
        for p in sorted(UPLOAD_DIR.glob("*.csv")):
            files.append(p.name)
    return jsonify({"files": sorted(files)})


def _resolve_otr_local_path(filename: str) -> Path | None:
    p = UPLOAD_DIR / filename
    if p.exists() and p.resolve().parent == UPLOAD_DIR.resolve():
        return p
    return None


@app.route("/api/otr/compare-local", methods=["POST"])
def otr_compare_local():
    """Compare a local OTR file against OTR_Rates.csv. Match on compound key,
    show updated LH values (bold), new rows (yellow), missing rows (red)."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = _resolve_otr_local_path(filename)
    if not local_path:
        return jsonify({"error": "File not found"}), 404

    uploaded = _parse_otr_upload(local_path)

    _sync_control_panel_from_disk_if_needed()
    fsc = _to_float(control_panel.get("Fuel Surcharge"), 0.0)
    otr_gri = _to_float(control_panel.get("OTR GRI"), 0.0)

    current_keys: dict[str, dict] = {}
    for r in db.get_otr_rates(active_only=True):
        key = db._otr_compound_key(r)
        lh = _to_float(r.get("base_rate"), 0.0)
        final = lh * fsc + otr_gri
        pts = (final / 88.0) * 20.0
        current_keys[key] = {
            "Origin City": r.get("origin_city", ""),
            "Origin State": r.get("origin_state", ""),
            "Dest City": r.get("dest_city", ""),
            "Dest State": r.get("dest_state", ""),
            "Cargo Type": r.get("cargo_type", ""),
            "LH": _round2(lh),
            "FSC": _round2(fsc),
            "GRI": _round2(otr_gri),
            "Final": _round2(final),
            "PTS": _round2(pts),
            "Last Updated": r.get("update_date", ""),
            "Expiration": r.get("expiration_date", ""),
        }

    all_keys = set(current_keys.keys()) | set(uploaded.keys())
    rows = []
    row_num = 0
    for key in sorted(all_keys):
        row_num += 1
        in_current = key in current_keys
        in_uploaded = key in uploaded

        if in_current and in_uploaded:
            row_data = dict(current_keys[key])
            new_lh = uploaded[key]
            old_lh = _to_float(row_data["LH"], 0.0)
            if abs(new_lh - old_lh) > 0.001:
                row_data["_status"] = "updated"
                row_data["_changed_fields"] = ["LH", "Final", "PTS"]
                row_data["LH"] = _round2(new_lh)
                new_final = new_lh * fsc + otr_gri
                row_data["Final"] = _round2(new_final)
                row_data["PTS"] = _round2((new_final / 88.0) * 20.0)
                row_data["Previous"] = _round2(old_lh)
                row_data["Delta"] = _round2(new_lh - old_lh)
            else:
                row_data["_status"] = "unchanged"
        elif in_current and not in_uploaded:
            row_data = dict(current_keys[key])
            row_data["_status"] = "removed"
        else:
            parts = key.split("|")
            new_lh = uploaded[key]
            new_final = new_lh * fsc + otr_gri
            row_data = {
                "Origin City": parts[0] if len(parts) > 0 else "",
                "Origin State": parts[1] if len(parts) > 1 else "",
                "Dest City": parts[2] if len(parts) > 2 else "",
                "Dest State": parts[3] if len(parts) > 3 else "",
                "Cargo Type": "",
                "LH": _round2(new_lh),
                "FSC": _round2(fsc),
                "GRI": _round2(otr_gri),
                "Final": _round2(new_final),
                "PTS": _round2((new_final / 88.0) * 20.0),
                "Last Updated": "",
                "Expiration": "",
                "_status": "new",
            }

        row_data.pop("_raw", None)
        row_data["Row"] = row_num
        row_data.setdefault("Previous", "")
        row_data.setdefault("Delta", "")
        rows.append(row_data)

    return jsonify({"rows": [_row_with_columns(r, OTR_COLUMNS + ("_status", "_changed_fields")) for r in rows]})


@app.route("/api/otr/apply-local", methods=["POST"])
def otr_apply_local():
    """Apply LH updates from local file to OTR_Rates.csv."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = _resolve_otr_local_path(filename)
    if not local_path:
        return jsonify({"error": "File not found"}), 404

    uploaded = _parse_otr_upload(local_path)

    current_rows = db.get_otr_rates(active_only=True)
    current_by_key: dict[str, dict] = {}
    for r in current_rows:
        key = db._otr_compound_key(r)
        current_by_key[key] = r

    updated_count = 0
    new_count = 0
    for key, new_lh in uploaded.items():
        if key in current_by_key:
            existing = current_by_key[key]
            old_lh = _to_float(existing.get("base_rate"), 0.0)
            if abs(new_lh - old_lh) > 0.001:
                db.deactivate_otr_rate(existing["id"])
                db.insert_otr_rate({
                    "origin_city": existing["origin_city"],
                    "origin_state": existing["origin_state"],
                    "dest_city": existing["dest_city"],
                    "dest_state": existing["dest_state"],
                    "cargo_type": existing.get("cargo_type", ""),
                    "base_rate": new_lh,
                    "update_date": existing.get("update_date", ""),
                    "expiration_date": existing.get("expiration_date", ""),
                    "prior_base_rate": old_lh,
                })
                updated_count += 1
        else:
            parts = key.split("|")
            db.insert_otr_rate({
                "origin_city": parts[0] if len(parts) > 0 else "",
                "origin_state": parts[1] if len(parts) > 1 else "",
                "dest_city": parts[2] if len(parts) > 2 else "",
                "dest_state": parts[3] if len(parts) > 3 else "",
                "cargo_type": "",
                "base_rate": new_lh,
            })
            new_count += 1

    return jsonify({"ok": True, "updated": updated_count, "new": new_count})


def _country_name_from_undest(undest: str, country_lookup: dict[str, str]) -> str:
    """Country name from unDest[:2] via countrycode_country."""
    cc = db.country_code_from_undest(undest)
    if not cc:
        return ""
    return str(country_lookup.get(cc, "") or "").strip()


def _ocean_destination_from_extract(
    raw: dict,
    destination_lookup: dict[str, str],
    undest: str,
) -> str:
    """dischargeport_country lookup, else city parsed from extract `dest` (e.g. Qingdao Pt, 32, CNQDG)."""
    destination = str(destination_lookup.get(undest, "") or "").strip()
    if destination:
        return destination
    dest_raw = str(raw.get("dest", "") or "").strip()
    if not dest_raw:
        return ""
    city = dest_raw.split(",")[0].strip()
    if city.lower().endswith(" pt"):
        city = city[:-3].strip()
    return city


def _ocean_build_context() -> dict:
    _sync_control_panel_from_disk_if_needed()
    _reload_document_cif()
    _reload_drayage()
    return {
        "now_text": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "port_lookup": db.get_portcode_portcity_lookup(),
        "destination_lookup": db.get_dischargeport_country_lookup(),
        "country_lookup": db.get_countrycode_country_lookup(),
    }


def _build_ocean_api_rows(
    raw_ocean: list[dict],
    *,
    ctx: dict | None = None,
) -> list[dict]:
    """Turn ocean_rates_extract dicts into OCEAN view rows."""
    if ctx is None:
        ctx = _ocean_build_context()
    now_text = ctx["now_text"]
    port_lookup = ctx["port_lookup"]
    destination_lookup = ctx["destination_lookup"]
    country_lookup = ctx["country_lookup"]

    rows: list[dict] = []
    for row_num, raw in enumerate(raw_ocean, start=1):
        unorig = str(raw.get("unOrig", "")).strip().upper()
        undest = str(raw.get("unDest", "")).strip().upper()
        country_code = db.country_code_from_undest(undest)

        port = port_lookup.get(unorig, "")
        destination = _ocean_destination_from_extract(raw, destination_lookup, undest)
        country = _country_name_from_undest(undest, country_lookup)

        prepaid = db.get_dthc_prepaid_by_country_code(country_code, "Yes")
        ocean_freight = db.ocean_freight_from_extract_row(raw, prepaid)
        doc_gri = _document_cif_float_for_country(country, "GRI")
        dray_gri = _drayage_field_for_port(port, "GRI")
        row_gri = doc_gri + dray_gri
        ocean_total = ocean_freight + row_gri
        total_pts = (ocean_total / 88.0) * 20.0

        row = {
            "Row": row_num,
            "Port": port,
            "Destination": destination,
            "Country": country,
            "DTHC Prepaid": prepaid,
            "Delivery Type": "EXPORT",
            "Code": undest,
            "SCAC": raw.get("scacCode", ""),
            "Ocean Freight": _round2(ocean_freight),
            "GRI": _round2(row_gri),
            "Ocean Total": _round2(ocean_total),
            "Total pts": _round2(total_pts),
            "Updated": now_text,
            "Expiration": raw.get("expirationDate", ""),
            "Previous": raw.get("Previous", ""),
            "Delta": raw.get("Delta", ""),
        }
        for meta_key in ("_status", "_changed_fields", "_extract_key"):
            if meta_key in raw:
                row[meta_key] = raw[meta_key]
        rows.append(row)
    return rows


@app.route("/api/ocean")
def ocean_rows():
    raw_ocean = db.get_ocean_rates_extract_row_dicts()
    rows = _build_ocean_api_rows(raw_ocean)
    return jsonify({"rows": [_row_with_columns(r, OCEAN_COLUMNS) for r in rows]})


# --- Ocean rates extract local CSV compare / apply (470OceanRatesExtract format) ---

_OCEAN_EXTRACT_CSV_COLS: tuple[str, ...] = (
    "unOrig",
    "unVia",
    "unDest",
    "orig",
    "via",
    "dest",
    "dischargePort",
    "scacCode",
    "carrierName",
    "contractNumber",
    "rateType",
    "amendmentNumber",
    "effectiveDate",
    "expirationDate",
    "updateTime",
    "40FT",
    "40HC",
    "DTHC40FT",
    "DTHC40HC",
    "ALLIN40FT",
    "ALLIN40HC",
)

_OCEAN_VIEW_COMPARE_FIELDS: tuple[str, ...] = (
    "Ocean Freight",
    "GRI",
    "Ocean Total",
    "Total pts",
    "DTHC Prepaid",
    "SCAC",
    "Expiration",
)


def _parse_ocean_extract_upload(filepath: Path) -> dict[str, dict]:
    """Parse 470OceanRatesExtract-style CSV into {compound_key: row_dict}."""
    import io

    text = filepath.read_text(encoding="utf-8-sig")
    rows_by_key: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    for raw in reader:
        row = {col: str(raw.get(col, "") or "").strip() for col in _OCEAN_EXTRACT_CSV_COLS}
        key = db.ocean_extract_compound_key(row)
        if not key.replace("|", "").strip():
            continue
        rows_by_key[key] = row
    return rows_by_key


def _extract_rows_to_uploaded(rows: list[dict]) -> dict[str, dict]:
    """Index extract-shaped row dicts by compound key."""
    rows_by_key: dict[str, dict] = {}
    for raw in rows:
        row = {col: str(raw.get(col, "") or "").strip() for col in _OCEAN_EXTRACT_CSV_COLS}
        key = db.ocean_extract_compound_key(row)
        if not key.replace("|", "").strip():
            continue
        rows_by_key[key] = row
    return rows_by_key


def _ocean_api_params_from_body(body: dict | None) -> dict:
    body = body or {}
    dest_port = str(body.get("dest_port") or "").strip().upper() or None
    all_adi = bool(body.get("all_adi_origins"))
    fetch_all = bool(body.get("fetch_all"))
    origins_raw = body.get("origins")
    origins = None
    if isinstance(origins_raw, list) and origins_raw:
        origins = [str(o).strip().upper() for o in origins_raw if str(o).strip()]
    return {
        "dest_port": dest_port,
        "all_adi_origins": all_adi,
        "fetch_all": fetch_all,
        "origins": origins,
    }


def _fetch_ocean_uploaded_from_cargo_api(body: dict | None) -> tuple[dict[str, dict], list[dict]]:
    """Call Cargo Savings oceanRatesAPI; return indexed extract rows + per-origin stats."""
    params = _ocean_api_params_from_body(body)
    rows, stats = cargo_ocean_api.collect_all_rates(
        params.get("origins"),
        dest_port=params.get("dest_port"),
        all_adi_origins=params.get("all_adi_origins", False),
        fetch_all=params.get("fetch_all", False),
    )
    return _extract_rows_to_uploaded(rows), stats


def _ocean_compare_uploaded(
    uploaded: dict[str, dict],
    *,
    current: dict[str, dict] | None = None,
) -> dict:
    """Compare uploaded extract rows to active DB; same payload as compare-local."""
    if current is None:
        current = db.get_ocean_rates_extract_indexed(active_only=True)
    ctx = _ocean_build_context()

    all_keys = set(current.keys()) | set(uploaded.keys())
    extract_rows: list[dict] = []
    for key in sorted(all_keys):
        in_current = key in current
        in_uploaded = key in uploaded
        if in_current and in_uploaded:
            cur = {k: v for k, v in current[key].items() if k not in ("id", "is_active")}
            up = uploaded[key]
            if db.ocean_extract_rows_differ(cur, up):
                changed = _ocean_view_changed_fields(cur, up, ctx)
                preview = dict(up)
                preview["_status"] = "updated"
                preview["_changed_fields"] = changed
                preview["_extract_key"] = key
                if "Ocean Freight" in changed:
                    old_view = _ocean_view_row_from_extract(cur, ctx)
                    new_view = _ocean_view_row_from_extract(up, ctx)
                    old_f = _to_float(old_view.get("Ocean Freight"), None)
                    new_f = _to_float(new_view.get("Ocean Freight"), None)
                    if old_f is not None and new_f is not None:
                        preview["Previous"] = _round2(old_f)
                        preview["Delta"] = _round2(new_f - old_f)
            else:
                preview = dict(cur)
                preview["_status"] = "unchanged"
                preview["_extract_key"] = key
        elif in_current and not in_uploaded:
            preview = {k: v for k, v in current[key].items() if k not in ("id", "is_active")}
            preview["_status"] = "removed"
            preview["_extract_key"] = key
        else:
            preview = dict(uploaded[key])
            preview["_status"] = "new"
            preview["_extract_key"] = key
        extract_rows.append(preview)

    rows = _build_ocean_api_rows(extract_rows, ctx=ctx)
    out_cols = OCEAN_COLUMNS + ("_status", "_changed_fields")

    port_lookup = ctx["port_lookup"]
    destination_lookup = ctx["destination_lookup"]
    country_lookup = ctx["country_lookup"]

    missing_ports: dict[str, int] = {}
    missing_dests: dict[str, dict] = {}
    missing_countries: dict[str, int] = {}
    for raw in extract_rows:
        status = raw.get("_status", "")
        if status in ("removed", "unchanged"):
            continue
        unorig = str(raw.get("unOrig", "")).strip().upper()
        undest = str(raw.get("unDest", "")).strip().upper()
        cc = db.country_code_from_undest(undest)
        if unorig and unorig not in port_lookup:
            missing_ports[unorig] = missing_ports.get(unorig, 0) + 1
        if undest and undest not in destination_lookup:
            entry = missing_dests.get(undest)
            if not entry:
                entry = {
                    "count": 0,
                    "country_code": cc,
                    "country": _country_name_from_undest(undest, country_lookup),
                }
                missing_dests[undest] = entry
            entry["count"] += 1
        if cc and cc not in country_lookup:
            missing_countries[cc] = missing_countries.get(cc, 0) + 1

    strict_overlap = len(set(current.keys()) & set(uploaded.keys()))
    current_lane = {db.ocean_extract_lane_key(v): k for k, v in current.items()}
    uploaded_lane = {db.ocean_extract_lane_key(v): k for k, v in uploaded.items()}
    lane_overlap = len(set(current_lane.keys()) & set(uploaded_lane.keys()))

    lookup_gaps: dict = {}
    if missing_ports:
        lookup_gaps["missing_ports"] = missing_ports
    if missing_dests:
        lookup_gaps["missing_destinations"] = missing_dests
    if missing_countries:
        lookup_gaps["missing_countries"] = missing_countries

    resp: dict = {
        "rows": [_row_with_columns(r, out_cols) for r in rows],
        "compare_stats": {
            "strict_key_overlap": strict_overlap,
            "lane_key_overlap": lane_overlap,
            "uploaded_rows": len(uploaded),
            "current_active_rows": len(current),
            "note": (
                "Row match uses full contract key (includes effective/expiration dates and "
                "amendment). Country in the table always uses unDest[:2] -> countrycode_country."
            ),
        },
    }
    if lookup_gaps:
        resp["lookup_gaps"] = lookup_gaps
    return resp


def _ocean_view_row_from_extract(raw: dict, ctx: dict) -> dict:
    """Single OCEAN view row (no Row number) for diffing."""
    built = _build_ocean_api_rows([raw], ctx=ctx)
    return built[0] if built else {}


def _ocean_view_changed_fields(old_raw: dict, new_raw: dict, ctx: dict) -> list[str]:
    old_view = _ocean_view_row_from_extract(old_raw, ctx)
    new_view = _ocean_view_row_from_extract(new_raw, ctx)
    return [
        f
        for f in _OCEAN_VIEW_COMPARE_FIELDS
        if str(old_view.get(f, "")).strip() != str(new_view.get(f, "")).strip()
    ]


def _resolve_ocean_local_path(filename: str) -> Path | None:
    p = UPLOAD_DIR / filename
    if p.exists() and p.resolve().parent == UPLOAD_DIR.resolve():
        return p
    return None


@app.route("/api/ocean/local-files")
def ocean_local_files():
    files: list[str] = []
    if UPLOAD_DIR.is_dir():
        for p in sorted(UPLOAD_DIR.glob("*.csv")):
            files.append(p.name)
    return jsonify({"files": sorted(files)})


@app.route("/api/ocean/compare-local", methods=["POST"])
def ocean_compare_local():
    """Compare local 470OceanRatesExtract CSV to SQLite ocean_rates_extract; return OCEAN view rows."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = _resolve_ocean_local_path(filename)
    if not local_path:
        return jsonify({"error": "File not found"}), 404

    uploaded = _parse_ocean_extract_upload(local_path)
    return jsonify(_ocean_compare_uploaded(uploaded))


@app.route("/api/ocean-api/compare", methods=["POST"])
def ocean_api_compare():
    """Fetch Cargo Savings oceanRatesAPI and compare to active ocean_rates_extract."""
    body = request.get_json(silent=True) or {}
    try:
        uploaded, fetch_stats = _fetch_ocean_uploaded_from_cargo_api(body)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    if not uploaded:
        errors = [s for s in fetch_stats if s.get("error")]
        detail = errors[0]["error"] if errors else "No rates returned from API."
        return jsonify({"error": detail, "fetch_stats": fetch_stats}), 502

    resp = _ocean_compare_uploaded(uploaded)
    resp["fetch_stats"] = fetch_stats
    resp["api_deduped_rows"] = len(uploaded)
    return jsonify(resp)


@app.route("/api/ocean-api/apply", methods=["POST"])
def ocean_api_apply():
    """Fetch from Cargo Savings API and apply into ocean_rates_extract."""
    body = request.get_json(silent=True) or {}
    try:
        uploaded, fetch_stats = _fetch_ocean_uploaded_from_cargo_api(body)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    if not uploaded:
        return jsonify({"error": "No rates returned from API.", "fetch_stats": fetch_stats}), 502

    counts = db.apply_ocean_rates_extract_upload(uploaded)
    return jsonify({"ok": True, "fetch_stats": fetch_stats, "api_deduped_rows": len(uploaded), **counts})


@app.route("/api/ocean/apply-local", methods=["POST"])
def ocean_apply_local():
    """Apply local 470OceanRatesExtract CSV into ocean_rates_extract."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = _resolve_ocean_local_path(filename)
    if not local_path:
        return jsonify({"error": "File not found"}), 404

    uploaded = _parse_ocean_extract_upload(local_path)
    counts = db.apply_ocean_rates_extract_upload(uploaded)
    return jsonify({"ok": True, **counts})


@app.route("/api/ocean-rates-extract", methods=["GET"])
def ocean_rates_extract_jarvis_get():
    return jsonify(db.list_ocean_rates_extract_for_jarvis())


@app.route("/api/ocean-rates-extract/<int:row_id>", methods=["DELETE"])
def ocean_rates_extract_jarvis_delete(row_id):
    if db.delete_ocean_rates_extract_row(row_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Row not found"}), 404


@app.route("/api/ocean-rates-extract/save", methods=["POST"])
def ocean_rates_extract_jarvis_save():
    payload = request.get_json(force=True, silent=True) or {}
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return jsonify({"error": "rows must be an array"}), 400
    try:
        counts = db.save_ocean_rates_extract_jarvis_rows(rows)
        return jsonify({"ok": True, **counts})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/ocean-costing-rules", methods=["GET"])
def ocean_costing_rules_list():
    rows = db.get_ocean_costing_rules(active_only=True)
    return jsonify({"rows": rows})


@app.route("/api/ocean-costing-rules/save", methods=["POST"])
def ocean_costing_rules_save():
    payload = request.get_json(force=True, silent=True) or {}
    city = str(payload.get("city", "")).strip()
    desc = str(payload.get("desc", "")).strip()
    country = str(payload.get("country", "")).strip()
    logic = str(payload.get("logic", "")).strip()
    if not city or not country:
        return jsonify({"error": "city and country are required"}), 400
    db.deactivate_ocean_costing_rules_matching(city, desc, country)
    new_id = db.insert_ocean_costing_rule(city, desc, country, logic)
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/ocean-costing-rules/save-all", methods=["POST"])
def ocean_costing_rules_save_all():
    payload = request.get_json(force=True, silent=True) or {}
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return jsonify({"error": "rows must be an array"}), 400
    merged: dict[tuple[str, str, str], tuple[str, str, str, str]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        city = str(item.get("city", "")).strip()
        desc = str(item.get("desc", "")).strip()
        country = str(item.get("country", "")).strip()
        logic = str(item.get("logic", "")).strip()
        if not city or not country:
            continue
        k = (
            db._norm_ocean_rule_key(city),
            db._norm_ocean_rule_key(desc),
            db._norm_ocean_rule_key(country),
        )
        merged[k] = (city, desc, country, logic)
    db.deactivate_all_ocean_costing_rules()
    saved = 0
    for city, desc, country, logic in merged.values():
        db.insert_ocean_costing_rule(city, desc, country, logic)
        saved += 1
    return jsonify({"ok": True, "saved": saved})


def _seam_db_to_api(raw: dict) -> dict:
    return {
        "Warehouse": raw.get("warehouse", ""),
        "Name": raw.get("name", ""),
        "City": raw.get("city", ""),
        "State": raw.get("state", ""),
        "County": raw.get("county", ""),
        "Terms": raw.get("terms", ""),
        "Verified": raw.get("verified", ""),
        "Points": raw.get("points", ""),
        "Recv": raw.get("recv", ""),
        "Strg": raw.get("strg", ""),
        "Load": raw.get("load", ""),
        "Compr": raw.get("compr", ""),
        "Class": raw.get("class", ""),
        "Mark": raw.get("mark", ""),
        "EffDate": raw.get("eff_date", ""),
        "Rail": raw.get("rail", ""),
        "ICE Ref": raw.get("ice_ref", ""),
        "Capacity": raw.get("capacity", ""),
        "CertLoad": raw.get("cert_load", ""),
        "CertCompr": raw.get("cert_compr", ""),
        "CertMark": raw.get("cert_mark", ""),
        "CertRecv": raw.get("cert_recv", ""),
        "CertStrg": raw.get("cert_strg", ""),
        "CertClass": raw.get("cert_class", ""),
        "Min Storage": raw.get("min_storage", ""),
        "Basis Adj.": raw.get("basis_adj", ""),
    }


def _seam_api_to_db(api_row: dict) -> dict:
    return {
        "warehouse": str(api_row.get("Warehouse", "")).strip(),
        "name": str(api_row.get("Name", "")).strip(),
        "city": str(api_row.get("City", "")).strip(),
        "state": str(api_row.get("State", "")).strip(),
        "county": str(api_row.get("County", "")).strip(),
        "terms": str(api_row.get("Terms", "")).strip(),
        "verified": str(api_row.get("Verified", "")).strip(),
        "points": str(api_row.get("Points", "")).strip(),
        "recv": str(api_row.get("Recv", "")).strip(),
        "strg": str(api_row.get("Strg", "")).strip(),
        "load": str(api_row.get("Load", "")).strip(),
        "compr": str(api_row.get("Compr", "")).strip(),
        "class": str(api_row.get("Class", "")).strip(),
        "mark": str(api_row.get("Mark", "")).strip(),
        "eff_date": str(api_row.get("EffDate", "")).strip(),
        "bales": str(api_row.get("Bales", "")).strip(),
        "rail": str(api_row.get("Rail", "")).strip(),
        "ice_ref": str(api_row.get("ICE Ref", "")).strip(),
        "capacity": str(api_row.get("Capacity", "")).strip(),
        "cert_load": str(api_row.get("CertLoad", "")).strip(),
        "cert_compr": str(api_row.get("CertCompr", "")).strip(),
        "cert_mark": str(api_row.get("CertMark", "")).strip(),
        "cert_recv": str(api_row.get("CertRecv", "")).strip(),
        "cert_strg": str(api_row.get("CertStrg", "")).strip(),
        "cert_class": str(api_row.get("CertClass", "")).strip(),
        "min_storage": str(api_row.get("Min Storage", "")).strip(),
        "basis_adj": str(api_row.get("Basis Adj.", api_row.get("Basis Adj", ""))).strip(),
    }


@app.route("/api/seam-tariffs")
def seam_tariff_rows():
    db_rows = db.get_seam_tariffs(active_only=True)
    rows = []
    for idx, raw in enumerate(db_rows, start=1):
        row = _seam_db_to_api(raw)
        row["Row"] = idx
        rows.append(row)
    return jsonify({"rows": [_row_with_columns(r, SEAM_COLUMNS) for r in rows]})


@app.route("/api/cert-tariffs")
def cert_tariff_rows():
    cert_warehouses = {
        "793961", "794505", "794540", "794550", "794553", "794555", "794560", "794598",
        "795007", "795026", "490150", "166150", "167003", "167025", "167035", "153505",
        "858053", "858054", "858055", "858056", "858065", "858063", "871048", "871049",
        "913054", "819202", "853007", "875260", "925011", "846847", "710530", "886623",
        "266861",
    }
    db_rows = db.get_seam_tariffs(active_only=True)
    rows = []
    row_num = 0
    for raw in db_rows:
        wh = raw.get("warehouse", "")
        if wh not in cert_warehouses:
            continue
        row_num += 1
        row = _seam_db_to_api(raw)
        row["Row"] = row_num
        rows.append(row)

    return jsonify({"rows": [_row_with_columns(r, CERT_COLUMNS) for r in rows]})


def _rap_db_to_api(raw: dict) -> dict:
    return {
        "Warehouse": raw.get("warehouse", ""),
        "Name": raw.get("name", ""),
        "City": raw.get("city", ""),
        "State": raw.get("state", ""),
        "Region": raw.get("region", ""),
        "Export": raw.get("export", ""),
        "Port": raw.get("port", ""),
        "ESO": raw.get("eso", ""),
        "Flat Bed Fees": raw.get("flat_bed_fees", ""),
        "Late Fees": raw.get("late_fees", ""),
        "Transportation Adjust": raw.get("transportation_adjust", ""),
        "Misc  Fees": raw.get("misc_fees", ""),
        "Consol Interest": raw.get("consol_interest", ""),
    }


def _rap_api_to_db(api_row: dict) -> dict:
    return {
        "warehouse": str(api_row.get("Warehouse", "")).strip(),
        "name": str(api_row.get("Name", "")).strip(),
        "city": str(api_row.get("City", "")).strip(),
        "state": str(api_row.get("State", "")).strip(),
        "region": str(api_row.get("Region", "")).strip(),
        "export": str(api_row.get("Export", "")).strip(),
        "port": str(api_row.get("Port", "")).strip(),
        "eso": str(api_row.get("ESO", "")).strip(),
        "flat_bed_fees": str(api_row.get("Flat Bed Fees", "")).strip(),
        "late_fees": str(api_row.get("Late Fees", "")).strip(),
        "transportation_adjust": str(api_row.get("Transportation Adjust", "")).strip(),
        "misc_fees": str(api_row.get("Misc  Fees", api_row.get("Misc Fees", ""))).strip(),
        "consol_interest": str(api_row.get("Consol Interest", "")).strip(),
    }


@app.route("/api/regions-and-ports")
def regions_and_ports_rows():
    db_rows = db.get_regions_and_ports(active_only=True)
    rows = []
    for idx, raw in enumerate(db_rows, start=1):
        row = _rap_db_to_api(raw)
        row["Row"] = idx
        rows.append(row)
    return jsonify({"rows": [_row_with_columns(r, REGIONS_AND_PORTS_COLUMNS) for r in rows]})


@app.route("/api/pts")
def pts_rows():
    built = _build_usd_rows()
    pts = [_usd_row_to_pts(r) for r in built]
    return jsonify({"rows": [_row_with_columns(r, PTS_COLUMNS) for r in pts]})


def _cif_regions_list() -> list[str]:
    raw = usa_forwarding_cost.get("cif_regions")
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        if out:
            return out
    return list(CIF_REGIONS_DEFAULT)


def _cif_pts_average_terms(matches: list[dict]) -> str:
    """Most common Terms among matching PTS rows (categorical; not a numeric average)."""
    if not matches:
        return ""
    vals = [str(m.get("Terms", "")).strip() for m in matches if str(m.get("Terms", "")).strip()]
    if not vals:
        return ""
    return Counter(vals).most_common(1)[0][0]


def _cif_pts_average_numeric(matches: list[dict], key: str, ignore_zeros: bool = True) -> float:
    """Arithmetic mean of numeric PTS cells; null/blank are always skipped.
    If ignore_zeros is True, zeros are also excluded from the average."""
    if not matches:
        return 0.0
    vals: list[float] = []
    for m in matches:
        v = m.get(key)
        if v == "" or v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        if ignore_zeros and x == 0.0:
            continue
        vals.append(x)
    if not vals:
        return 0.0
    return _round_half_up_2(sum(vals) / len(vals))


def _cif_cash_equity_from_row(row: dict, has_matches: bool) -> tuple[float, float]:
    """Cash / Equity from averaged subtotals (PTS points), not from averaging PTS Cash/Equity."""
    if not has_matches:
        return 0.0, 0.0
    cash = sum(_to_float(row.get(k), 0.0) for k in PTS_CASH_SUM_KEYS)
    equity = sum(_to_float(row.get(k), 0.0) for k in PTS_EQUITY_SUM_KEYS)
    return (_round_half_up_2(cash), _round_half_up_2(equity))


# Origin Warehouse columns in the CIF view — WTXH uses WTX warehouses for these.
_CIF_ORIGIN_KEYS = frozenset({
    "Terms", "Recv", "Load", "Compr", "Class", "Mark", "Strg", "ESO",
    "Interest", "Origin Comm", "Total Equity", "Total Origin",
})


def _build_cif_port_row(port_name: str, row_num: int) -> dict:
    """Build a CIF row for a port (Houston/Dallas) using port-level calculations, not PTS averages."""
    _reload_control_panel()
    _reload_consolidation()
    _reload_consolidation_days_storage()
    _reload_drayage()
    _reload_document_cif()
    _reload_usa_forwarding_cost()
    _recompute_usa_forwarding_total()

    avg_purchase = _to_float(control_panel.get("Avg Purchase Price"), 0.0)
    edf_rate = _to_float(control_panel.get("EDF Interest Rate"), 0.0)
    avg_bale_wt = _to_float(control_panel.get("Avg Bale Weight"), 0.0)
    usd_consol_interest = _usd_consolidation_interest(
        avg_purchase, edf_rate, avg_bale_wt, _days_storage_factor()
    )

    consol_block = _usd_consolidation_in_and_out_for_port(port_name)
    consol_strg = _usd_consolidation_total_storage_for_port(port_name)
    total_consol = consol_block + consol_strg + usd_consol_interest

    dray_bale = _drayage_field_for_port(port_name, "Bale")
    ocean_base_raw = _drayage_field_for_port(port_name, "OceanBase")
    ocean_base = ocean_base_raw / 88.0
    total_out = dray_bale + ocean_base

    china_lc = _document_cif_float_for_country("China", "LC")
    sight_lc = china_lc / 20.0
    china_cont = _document_cif_float_for_country("China", "CONT")
    controlling_usd = china_cont / 20.0
    china_ins = _document_cif_float_for_country("China", "INS")
    insurance_usd = china_ins / 20.0
    forwarding_usd = _to_float(usa_forwarding_cost.get("TOTAL"), 0.0)
    total_doc = sight_lc + forwarding_usd + controlling_usd + insurance_usd

    china_com = _document_cif_float_for_country("China", "COM")
    dest_commission_usd = china_com / 20.0
    china_cof = _document_cif_float_for_country("China", "COF")
    cost_of_funds_usd = china_cof / 20.0
    china_qc = _document_cif_float_for_country("China", "CIQ_QC")
    qclaim_usd = china_qc / 20.0
    total_cif = dest_commission_usd + cost_of_funds_usd + qclaim_usd

    cash = total_consol + total_out + total_doc + total_cif
    equity = cash

    # CIF view is in PTS (USD * 20), rounded to whole numbers
    pts = 20.0
    row: dict = {key: "" for key in CIF_COLUMNS}
    row["Row"] = row_num
    row["Region"] = port_name
    row["Consol_Block"] = round(consol_block * pts)
    row["Consol_Strg"] = round(consol_strg * pts)
    row["Consol_Interest"] = round(usd_consol_interest * pts)
    row["Total_Consol"] = round(total_consol * pts)
    row["Dray"] = round(dray_bale * pts)
    row["Ocean"] = round(ocean_base * pts)
    row["Total_Out"] = round(total_out * pts)
    row["Sight_LC"] = round(sight_lc * pts)
    row["Forwarding"] = round(forwarding_usd * pts)
    row["Controlling"] = round(controlling_usd * pts)
    row["Insurance"] = round(insurance_usd * pts)
    row["Total_Doc"] = round(total_doc * pts)
    row["Dest_Commission"] = round(dest_commission_usd * pts)
    row["Cost_of_Funds"] = round(cost_of_funds_usd * pts)
    row["Qclaim"] = round(qclaim_usd * pts)
    row["Total_CIF"] = round(total_cif * pts)
    row["Cash"] = round(cash * pts)
    row["Equity"] = round(equity * pts)
    return row


_CIF_PORT_REGIONS = {"Houston", "Dallas"}


def _build_cif_rows(ignore_zeros: bool = True, included: set | None = None) -> list[dict]:
    """Per CIF region label: average each PTS column over rows where PTS Region equals that label."""
    built_usd = _build_usd_rows()
    pts_rows_list = [_row_with_columns(_usd_row_to_pts(r), PTS_COLUMNS) for r in built_usd]
    regions = _cif_regions_list()

    matches_by_region: dict[str, list[dict]] = {}
    for r in pts_rows_list:
        wh = str(r.get("Warehouse", "")).strip()
        rk = str(r.get("Region", "")).strip()
        key = f"{wh}|{rk}"
        if included is not None and key not in included:
            continue
        matches_by_region.setdefault(rk, []).append(r)

    rows_out: list[dict] = []
    for i, region in enumerate(regions, start=1):
        region_key = str(region).strip()

        if region_key in _CIF_PORT_REGIONS:
            rows_out.append(_build_cif_port_row(region_key, i))
            continue

        matches = matches_by_region.get(region_key, [])

        origin_matches = matches
        if region_key == "WTXH":
            origin_matches = matches_by_region.get("WTX", [])

        row: dict = {}
        for key in CIF_COLUMNS:
            if key == "Row":
                row[key] = i
            elif key == "Region":
                row[key] = region
            elif key in ("Cash", "Equity"):
                continue
            elif key == "Terms":
                row[key] = _cif_pts_average_terms(origin_matches if key in _CIF_ORIGIN_KEYS else matches)
            elif key in _CIF_ORIGIN_KEYS:
                row[key] = round(_cif_pts_average_numeric(origin_matches, key, ignore_zeros))
            else:
                row[key] = round(_cif_pts_average_numeric(matches, key, ignore_zeros))
        cash_eq = _cif_cash_equity_from_row(row, bool(matches) or bool(origin_matches))
        row["Cash"], row["Equity"] = round(cash_eq[0]), round(cash_eq[1])
        rows_out.append(row)
    return rows_out


@app.route("/api/cif")
def cif_rows_api():
    ignore_zeros = request.args.get("ignore_zeros", "1") != "0"
    included_raw = request.args.get("included")
    included_set = set(included_raw.split(",")) if included_raw is not None and included_raw != "" else None
    built = _build_cif_rows(ignore_zeros=ignore_zeros, included=included_set)
    return jsonify({"rows": [_row_with_columns(r, CIF_COLUMNS) for r in built]})


@app.route("/api/export/documentation-totals")
def export_documentation_totals_api():
    """Per-country Total Doc in PTS for Export Documentation: (LC/20 + CONT/20 + INS/20 + USA forwarding TOTAL) × 20.

    Keys are normalized country names (uppercase, collapsed spaces) for Export view lookup.
    """
    _reload_document_cif()
    _reload_usa_forwarding_cost()
    _recompute_usa_forwarding_total()
    forwarding_usd = _to_float(usa_forwarding_cost.get("TOTAL"), 0.0)
    pts = 20.0
    totals: dict[str, int] = {}
    for row in document_cif:
        if not isinstance(row, dict):
            continue
        country = str(row.get("country", "")).strip()
        if not country:
            continue
        lc = _to_float(row.get("LC"), 0.0)
        ins = _to_float(row.get("INS"), 0.0)
        cont = _to_float(row.get("CONT"), 0.0)
        sight_usd = lc / 20.0
        insurance_usd = ins / 20.0
        controlling_usd = cont / 20.0
        total_usd = sight_usd + forwarding_usd + controlling_usd + insurance_usd
        k = _normalize_key(country)
        totals[k] = int(round(total_usd * pts))
    resp = jsonify(totals)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/export/cif-totals")
def export_cif_totals_api():
    """Per-country Total CIF in PTS for Export CIF section: (COM/20 + COF/20 + CIQ_QC/20) × 20.

    Keys are normalized country names (uppercase, collapsed spaces) for Export view lookup.
    USA forwarding TOTAL is not included here (it is part of Export Documentation only).
    """
    _reload_document_cif()
    pts = 20.0
    totals: dict[str, int] = {}
    for row in document_cif:
        if not isinstance(row, dict):
            continue
        country = str(row.get("country", "")).strip()
        if not country:
            continue
        com = _to_float(row.get("COM"), 0.0)
        cof = _to_float(row.get("COF"), 0.0)
        ciq = _to_float(row.get("CIQ_QC"), 0.0)
        dest_comm_usd = com / 20.0
        cof_usd = cof / 20.0
        qclaim_usd = ciq / 20.0
        total_usd = dest_comm_usd + cof_usd + qclaim_usd
        k = _normalize_key(country)
        totals[k] = int(round(total_usd * pts))
    resp = jsonify(totals)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/dthc-prepaid")
def dthc_prepaid_api():
    resp = jsonify(db.get_dthc_prepaid_rows(active_only=True))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/export-data")
def export_data_api():
    resp = jsonify(db.get_export_data(active_only=True))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/themes")
def themes_api():
    resp = jsonify(db.get_themes())
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/api/themes/save", methods=["POST"])
def themes_save_api():
    payload = request.get_json(force=True, silent=True) or {}
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return jsonify({"error": "rows must be an array"}), 400
    try:
        n = db.save_themes_rows(rows)
        return jsonify({"ok": True, "count": n})
    except Exception as exc:
        if current_app.debug:
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500
        return jsonify({"error": str(exc)}), 500


def _build_usd_rows():
    _reload_control_panel()
    _reload_consolidation_days_storage()
    _reload_consolidation()
    _reload_drayage()
    _reload_document_cif()
    _reload_usa_forwarding_cost()
    _recompute_usa_forwarding_total()
    seam_by_warehouse: dict[str, dict] = {}
    for sr in db.get_seam_tariffs(active_only=True):
        wh = sr.get("warehouse", "")
        if wh:
            seam_by_warehouse[wh] = sr

    flat_rows = []
    eso_by_warehouse: dict[str, float] = {}
    flatbed_by_warehouse: dict[str, float] = {}
    late_fee_by_warehouse: dict[str, float] = {}
    for rr in db.get_regions_and_ports(active_only=True):
        api_row = _rap_db_to_api(rr)
        flat_rows.append(api_row)
        wh_key = rr.get("warehouse", "")
        if wh_key:
            eso_by_warehouse[wh_key] = _to_float(rr.get("eso"), 0.0)
            flatbed_by_warehouse[wh_key] = _to_float(rr.get("flat_bed_fees"), 0.0)
            late_fee_by_warehouse[wh_key] = _to_float(rr.get("late_fees"), 0.0)

    edf_rate = _to_float(control_panel.get("EDF Interest Rate"), 0.0)
    avg_purchase = _to_float(control_panel.get("Avg Purchase Price"), 0.0)
    avg_bale_wt = _to_float(control_panel.get("Avg Bale Weight"), 0.0)
    origin_comm = _to_float(control_panel.get("Origin Commission"), 0.0)
    # OTR Final from OTR_Rates.csv (same as GET /api/otr), keyed by warehouse City + export Port.
    otr_fsc = _to_float(control_panel.get("Fuel Surcharge"), 0.0)
    otr_gri_lane = _to_float(control_panel.get("OTR GRI"), 0.0)
    otr_final_lookup = _otr_final_lookup_from_db(otr_fsc, otr_gri_lane)
    daily_spot = _to_float(control_panel.get("Daily Spot"), 0.0)
    interest = (edf_rate / 100.0 / 12.0) * ((daily_spot / 100.0) * avg_bale_wt) if edf_rate and daily_spot and avg_bale_wt else 0.0

    usd_consol_interest = _usd_consolidation_interest(
        avg_purchase,
        edf_rate,
        avg_bale_wt,
        _days_storage_factor(),
    )

    duplicated_warehouses = {
        "385000", "385001", "631020", "810001", "810002", "810003", "810535",
        "810537", "810538", "820010", "828031", "829537", "843000",
        "843002", "846847", "853005", "853007", "858078", "867017", "875260",
        "880533", "882008", "884033", "886506", "886509", "886512", "886517",
        "886520", "886533", "886570", "904033", "906015", "911510",
        "911520", "911525", "911533", "913030", "913055", "914510", "916501",
        "925011", "925012", "928532", "935002", "936006", "937530", "937534",
        "937535", "939033", "944344", "944708", "947505",
    }

    working_rows = []
    for f in flat_rows:
        wh = str(f.get("Warehouse", "")).strip()
        s = seam_by_warehouse.get(wh, {})
        row = {
            "Warehouse": wh,
            "Name": str(s.get("name", f.get("Name", ""))).strip(),
            "City": str(s.get("city", f.get("City", ""))).strip(),
            "State": str(s.get("state", f.get("State", ""))).strip(),
            "Region": str(f.get("Region", "")).strip(),
            "Export": str(f.get("Export", "")).strip(),
            "Port": str(f.get("Port", "")).strip(),
            "Terms": str(s.get("terms", "")).strip().lstrip("0"),
            "Recv": _to_float(s.get("recv"), 0.0),
            "Load": _to_float(s.get("load"), 0.0),
            "Compr": _to_float(s.get("compr"), 0.0),
            "Class": _to_float(s.get("class"), 0.0),
            "Mark": _to_float(s.get("mark"), 0.0),
            "Strg": _to_float(s.get("strg"), 0.0),
            "ESO": eso_by_warehouse.get(wh, 0.0),
            "Flatbed": flatbed_by_warehouse.get(wh, 0.0),
            "Late Fee": late_fee_by_warehouse.get(wh, 0.0),
        }
        if row["Strg"] < 1.0:
            row["Strg"] = row["Strg"] * 30.0
        working_rows.append(row)

    dup_rows = []
    for row in working_rows:
        if row["Warehouse"] not in duplicated_warehouses:
            continue
        dup = dict(row)
        dup["Region"] = "WTXH"
        dup["Port"] = "Houston"
        dup_rows.append(dup)
    working_rows.extend(dup_rows)

    def _total_origin(r):
        t = str(r.get("Terms", "")).strip()
        if t == "1":
            return r["Strg"] + interest + origin_comm
        if t == "2":
            return r["Compr"] + r["Strg"] + interest + origin_comm
        if t == "3":
            return r["Load"] + r["Compr"] + r["Strg"] + r["Class"] + interest + origin_comm
        if t == "4":
            return r["Class"] + interest + origin_comm
        return 0.0

    china_lc = _document_cif_float_for_country("China", "LC")
    sight_lc = china_lc / 20.0
    china_cont = _document_cif_float_for_country("China", "CONT")
    controlling_usd = china_cont / 20.0
    china_ins = _document_cif_float_for_country("China", "INS")
    insurance_usd = china_ins / 20.0
    china_com = _document_cif_float_for_country("China", "COM")
    dest_commission_usd = china_com / 20.0
    china_cof = _document_cif_float_for_country("China", "COF")
    cost_of_funds_usd = china_cof / 20.0
    china_qc = _document_cif_float_for_country("China", "CIQ_QC")
    qclaim_usd = china_qc / 20.0
    total_cif = dest_commission_usd + cost_of_funds_usd + qclaim_usd
    forwarding_usd = _to_float(usa_forwarding_cost.get("TOTAL"), 0.0)
    total_doc = sight_lc + forwarding_usd + controlling_usd + insurance_usd

    rows = []
    working_rows.sort(key=lambda r: (_to_float(r.get("Warehouse"), 0.0), r.get("Port", "")))
    for idx, r in enumerate(working_rows, start=1):
        otr_final = otr_final_lookup.get(
            (_normalize_key(r["City"]), _normalize_key(r["Port"])), 0.0
        )
        transit_truck = (otr_final / 88.0) if otr_final else 0.0
        total_equity = r["Recv"] + r["Load"] + r["Compr"] + r["Class"] + r["Mark"] + r["Strg"] + r["ESO"] + interest + origin_comm
        total_origin = _total_origin(r)
        total_transit = r["Flatbed"] + r["Late Fee"] + transit_truck
        consol_block = _usd_consolidation_in_and_out_for_port(r["Port"])
        consol_strg = _usd_consolidation_total_storage_for_port(r["Port"])
        row_total_consol = consol_block + consol_strg + usd_consol_interest
        dray_bale = _drayage_field_for_port(r["Port"], "Bale")
        ocean_base_raw = _drayage_field_for_port(r["Port"], "OceanBase")
        ocean_base = ocean_base_raw / 88.0
        total_out = dray_bale + ocean_base
        ph = ""
        rows.append(
            {
                "Row": idx,
                "Warehouse": r["Warehouse"],
                "Name": r["Name"],
                "City": r["City"],
                "State": r["State"],
                "Region": r["Region"],
                "Export": r["Export"],
                "Port": r["Port"],
                "Terms": r["Terms"],
                "Recv": _round2(r["Recv"]),
                "Load": _round2(r["Load"]),
                "Compr": _round2(r["Compr"]),
                "Class": _round2(r["Class"]),
                "Mark": _round2(r["Mark"]),
                "Strg": _round2(r["Strg"]),
                "ESO": _round2(r["ESO"]),
                "Interest": _round2(interest),
                "Origin Comm": _round2(origin_comm),
                "Total Equity": _round2(total_equity),
                "Total Origin": _round2(total_origin),
                "Flatbed": _round2(r["Flatbed"]),
                "Late Fee": _round2(r["Late Fee"]),
                "Transit Truck": _round2(transit_truck),
                "Total Transit": _round2(total_transit),
                "Consol_Block": _round2(consol_block),
                "Consol_Strg": _round2(consol_strg),
                "Consol_Interest": _round2(usd_consol_interest),
                "Total_Consol": _round2(row_total_consol),
                "Dray": _round2(dray_bale),
                "Ocean": _round2(ocean_base),
                "Total_Out": _round2(total_out),
                "Sight_LC": _round2(sight_lc),
                "Forwarding": _round2(forwarding_usd),
                "Controlling": _round2(controlling_usd),
                "Insurance": _round2(insurance_usd),
                "Total_Doc": _round2(total_doc),
                "Dest_Commission": _round2(dest_commission_usd),
                "Cost_of_Funds": _round2(cost_of_funds_usd),
                "Qclaim": _round2(qclaim_usd),
                "Total_CIF": _round2(total_cif),
                "Weslaco_Transit": ph,
                "Shelby_Transit": ph,
            }
        )

    return rows


@app.route("/api/usd")
def usd_rows():
    rows = _build_usd_rows()
    return jsonify({"rows": [_row_with_columns(r, USD_COLUMNS) for r in rows]})


# --- Seam Tariffs upload / compare / apply ---

# In-memory store for pending seam tariff changes (will become SQLite later)
_seam_pending: list[dict] = []


def _parse_seam_csv_rows(text: str) -> dict[str, dict]:
    """Parse CSV text into {warehouse: row_dict}."""
    import io
    rows_by_wh: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    for raw in reader:
        wh = str(raw.get("Warehouse", "")).strip()
        if not wh:
            continue
        rows_by_wh[wh] = {
            "Warehouse": wh,
            "Name": str(raw.get("Name", "")).strip(),
            "City": str(raw.get("City", "")).strip(),
            "State": str(raw.get("State", "")).strip(),
            "County": str(raw.get("County", "")).strip(),
            "Terms": str(raw.get("Terms", "")).strip(),
            "Verified": str(raw.get("Verified", "")).strip(),
            "Points": str(raw.get("Points", "")).strip(),
            "Recv": str(raw.get("Recv", "")).strip(),
            "Strg": str(raw.get("Strg", "")).strip(),
            "Load": str(raw.get("Load", "")).strip(),
            "Compr": str(raw.get("Compr", "")).strip(),
            "Class": str(raw.get("Class", "")).strip(),
            "Mark": str(raw.get("Mark", "")).strip(),
            "EffDate": str(raw.get("EffDate", "")).strip(),
            "Bales": str(raw.get("Bales", "")).strip(),
            "Rail": str(raw.get("Rail", "")).strip(),
            "ICE Ref": str(raw.get("ICE Ref", "")).strip(),
            "Capacity": str(raw.get("Capacity", "")).strip(),
            "CertLoad": str(raw.get("CertLoad", "")).strip(),
            "CertCompr": str(raw.get("CertCompr", "")).strip(),
            "CertMark": str(raw.get("CertMark", "")).strip(),
            "CertRecv": str(raw.get("CertRecv", "")).strip(),
            "CertStrg": str(raw.get("CertStrg", "")).strip(),
            "CertClass": str(raw.get("CertClass", "")).strip(),
            "Min Storage": str(raw.get("Min Storage", "")).strip(),
            "Basis Adj.": str(raw.get("Basis Adj.", raw.get("Basis Adj", ""))).strip(),
        }
    return rows_by_wh


def _load_current_seam_by_warehouse() -> dict[str, dict]:
    """Load current SEAM tariffs from SQLite into {warehouse: api_dict}."""
    result: dict[str, dict] = {}
    for r in db.get_seam_tariffs(active_only=True):
        wh = r.get("warehouse", "")
        if not wh:
            continue
        row = _seam_db_to_api(r)
        row["Bales"] = r.get("bales", "")
        result[wh] = row
    return result


_SEAM_COMPARE_FIELDS = (
    "Name", "City", "State", "County", "Terms", "Verified", "Points",
    "Recv", "Strg", "Load", "Compr", "Class", "Mark", "EffDate",
    "Bales", "Rail", "ICE Ref", "Capacity", "CertLoad", "CertCompr", "CertMark",
    "CertRecv", "CertStrg", "CertClass", "Min Storage", "Basis Adj.",
)


def _rows_differ(a: dict, b: dict) -> bool:
    for f in _SEAM_COMPARE_FIELDS:
        if str(a.get(f, "")).strip() != str(b.get(f, "")).strip():
            return True
    return False


def _changed_fields(a: dict, b: dict) -> list[str]:
    """Return list of field names that differ between two rows."""
    return [f for f in _SEAM_COMPARE_FIELDS
            if str(a.get(f, "")).strip() != str(b.get(f, "")).strip()]


@app.route("/api/seam-tariffs/upload", methods=["POST"])
def seam_tariff_upload():
    """Accept uploaded CSV, compare with current data, return color-coded rows."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    text = f.read().decode("utf-8-sig")

    uploaded = _parse_seam_csv_rows(text)
    current = _load_current_seam_by_warehouse()

    all_warehouses = set(current.keys()) | set(uploaded.keys())
    rows = []
    row_num = 0
    for wh in sorted(all_warehouses, key=lambda w: int(w) if w.isdigit() else 0):
        row_num += 1
        in_current = wh in current
        in_uploaded = wh in uploaded

        if in_current and in_uploaded:
            row_data = dict(uploaded[wh])
            if _rows_differ(current[wh], uploaded[wh]):
                row_data["_status"] = "updated"  # green
            else:
                row_data["_status"] = "unchanged"  # blue
        elif in_current and not in_uploaded:
            row_data = dict(current[wh])
            row_data["_status"] = "removed"  # red
        else:
            row_data = dict(uploaded[wh])
            row_data["_status"] = "new"  # tan

        row_data["Row"] = row_num
        rows.append(row_data)

    return jsonify({"rows": [_row_with_columns(r, SEAM_COLUMNS + ("_status",)) for r in rows]})


@app.route("/api/seam-tariffs/apply", methods=["POST"])
def seam_tariff_apply():
    """Apply uploaded CSV: version changed rows (deactivate old, insert new)."""
    global _seam_pending
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    text = f.read().decode("utf-8-sig")

    uploaded = _parse_seam_csv_rows(text)
    current_db = db.get_seam_tariffs(active_only=True)
    current_by_wh: dict[str, dict] = {}
    for r in current_db:
        current_by_wh[r["warehouse"]] = r

    rap_by_wh = {r["warehouse"]: r for r in db.get_regions_and_ports(active_only=True)}

    updated_count = 0
    new_count = 0
    for wh, up_row in uploaded.items():
        db_row = _seam_api_to_db(up_row)
        if wh in current_by_wh:
            existing = current_by_wh[wh]
            changed = any(
                str(db_row.get(c, "")).strip() != str(existing.get(c, "")).strip()
                for c in db._SEAM_COLS if c != "warehouse"
            )
            if changed:
                db.deactivate_seam_tariff(existing["id"])
                db.insert_seam_tariff(db_row)
                updated_count += 1
        else:
            db.insert_seam_tariff(db_row)
            new_count += 1
            if wh not in rap_by_wh:
                db.insert_regions_and_ports_row({
                    "warehouse": wh,
                    "name": db_row.get("name", ""),
                    "city": db_row.get("city", ""),
                    "state": db_row.get("state", ""),
                    "region": "", "export": "", "port": "", "eso": "",
                    "flat_bed_fees": "", "late_fees": "",
                    "transportation_adjust": "", "misc_fees": "",
                    "consol_interest": "",
                })

    return jsonify({"ok": True, "updated": updated_count, "new": new_count})


@app.route("/api/seam-tariffs/local-files")
def seam_tariff_local_files():
    files = []
    if UPLOAD_DIR.is_dir():
        for p in sorted(UPLOAD_DIR.glob("*.csv")):
            files.append(p.name)
    return jsonify({"files": sorted(files)})


@app.route("/api/seam-tariffs/compare-local", methods=["POST"])
def seam_tariff_compare_local():
    """Compare a local file (by name) against current SEAM_TARIFFS data."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = UPLOAD_DIR / filename
    if not local_path.exists() or local_path.resolve().parent != UPLOAD_DIR.resolve():
        return jsonify({"error": "File not found"}), 404

    text = local_path.read_text(encoding="utf-8-sig")
    uploaded = _parse_seam_csv_rows(text)
    current = _load_current_seam_by_warehouse()

    all_warehouses = set(current.keys()) | set(uploaded.keys())
    rows = []
    row_num = 0
    for wh in sorted(all_warehouses, key=lambda w: int(w) if w.isdigit() else 0):
        row_num += 1
        in_current = wh in current
        in_uploaded = wh in uploaded

        if in_current and in_uploaded:
            row_data = dict(uploaded[wh])
            changed = _changed_fields(current[wh], uploaded[wh])
            if changed:
                row_data["_status"] = "updated"
                row_data["_changed_fields"] = changed
            else:
                row_data["_status"] = "unchanged"
        elif in_current and not in_uploaded:
            row_data = dict(current[wh])
            row_data["_status"] = "removed"
        else:
            row_data = dict(uploaded[wh])
            row_data["_status"] = "new"

        row_data["Row"] = row_num
        rows.append(row_data)

    return jsonify({"rows": [_row_with_columns(r, SEAM_COLUMNS + ("_status", "_changed_fields")) for r in rows]})


@app.route("/api/seam-tariffs/apply-local", methods=["POST"])
def seam_tariff_apply_local():
    """Apply a local file: version changed rows (deactivate old, insert new)."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = UPLOAD_DIR / filename
    if not local_path.exists() or local_path.resolve().parent != UPLOAD_DIR.resolve():
        return jsonify({"error": "File not found"}), 404

    text = local_path.read_text(encoding="utf-8-sig")
    uploaded = _parse_seam_csv_rows(text)

    current_db = db.get_seam_tariffs(active_only=True)
    current_by_wh: dict[str, dict] = {}
    for r in current_db:
        current_by_wh[r["warehouse"]] = r

    rap_by_wh = {r["warehouse"]: r for r in db.get_regions_and_ports(active_only=True)}

    updated_count = 0
    new_count = 0
    for wh, up_row in uploaded.items():
        db_row = _seam_api_to_db(up_row)
        if wh in current_by_wh:
            existing = current_by_wh[wh]
            changed = any(
                str(db_row.get(c, "")).strip() != str(existing.get(c, "")).strip()
                for c in db._SEAM_COLS if c != "warehouse"
            )
            if changed:
                db.deactivate_seam_tariff(existing["id"])
                db.insert_seam_tariff(db_row)
                updated_count += 1
        else:
            db.insert_seam_tariff(db_row)
            new_count += 1
            if wh not in rap_by_wh:
                db.insert_regions_and_ports_row({
                    "warehouse": wh,
                    "name": db_row.get("name", ""),
                    "city": db_row.get("city", ""),
                    "state": db_row.get("state", ""),
                    "region": "", "export": "", "port": "", "eso": "",
                    "flat_bed_fees": "", "late_fees": "",
                    "transportation_adjust": "", "misc_fees": "",
                    "consol_interest": "",
                })

    return jsonify({"ok": True, "updated": updated_count, "new": new_count})


# --- Regions and Ports upload / compare / apply ---

_RAP_FIELDS = (
    "Name", "City", "State", "Region", "Export", "Port",
    "ESO", "Flat Bed Fees", "Late Fees", "Transportation Adjust",
    "Misc  Fees", "Consol Interest",
)


def _parse_rap_csv_rows(text: str) -> dict[str, dict]:
    """Parse CSV text into {warehouse: row_dict}."""
    import io
    rows_by_wh: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    for raw in reader:
        wh = str(raw.get("Warehouse", "")).strip()
        if not wh:
            continue
        misc_key = "Misc  Fees"
        rows_by_wh[wh] = {
            "Warehouse": wh,
            "Name": str(raw.get("Name", "")).strip(),
            "City": str(raw.get("City", "")).strip(),
            "State": str(raw.get("State", "")).strip(),
            "Region": str(raw.get("Region", "")).strip(),
            "Export": str(raw.get("Export", "")).strip(),
            "Port": str(raw.get("Port", "")).strip(),
            "ESO": str(raw.get("ESO", "")).strip(),
            "Flat Bed Fees": str(raw.get("Flat Bed Fees", "")).strip(),
            "Late Fees": str(raw.get("Late Fees", "")).strip(),
            "Transportation Adjust": str(raw.get("Transportation Adjust", "")).strip(),
            "Misc  Fees": str(raw.get(misc_key, raw.get("Misc Fees", ""))).strip(),
            "Consol Interest": str(raw.get("Consol Interest", "")).strip(),
        }
    return rows_by_wh


def _load_current_rap_by_warehouse() -> dict[str, dict]:
    """Load current regions_and_ports from SQLite into {warehouse: api_dict}."""
    result: dict[str, dict] = {}
    for r in db.get_regions_and_ports(active_only=True):
        wh = r.get("warehouse", "")
        if not wh:
            continue
        result[wh] = _rap_db_to_api(r)
    return result


def _rap_changed_fields(a: dict, b: dict) -> list[str]:
    return [f for f in _RAP_FIELDS
            if str(a.get(f, "")).strip() != str(b.get(f, "")).strip()]


@app.route("/api/regions-and-ports/local-files")
def rap_local_files():
    files = []
    if UPLOAD_DIR.is_dir():
        for p in sorted(UPLOAD_DIR.glob("*.csv")):
            files.append(p.name)
    return jsonify({"files": sorted(files)})


def _extract_warehouse_rows_from_csv(text: str) -> dict[str, dict]:
    """Extract Warehouse + shared columns (Name, City, State) from any CSV."""
    import io
    rows: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
    for raw in reader:
        wh = str(raw.get("Warehouse", "")).strip()
        if wh:
            rows[wh] = {
                "Warehouse": wh,
                "Name": str(raw.get("Name", "")).strip(),
                "City": str(raw.get("City", "")).strip(),
                "State": str(raw.get("State", "")).strip(),
            }
    return rows


@app.route("/api/regions-and-ports/compare-local", methods=["POST"])
def rap_compare_local():
    """Warehouse-level comparison: show which warehouses are in the uploaded
    file but missing from regions_and_ports (new/yellow) and which are in
    regions_and_ports but not the uploaded file (removed/red).
    Current data is NEVER overwritten."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = UPLOAD_DIR / filename
    if not local_path.exists() or local_path.resolve().parent != UPLOAD_DIR.resolve():
        return jsonify({"error": "File not found"}), 404

    text = local_path.read_text(encoding="utf-8-sig")
    uploaded = _extract_warehouse_rows_from_csv(text)
    current = _load_current_rap_by_warehouse()

    all_warehouses = set(current.keys()) | set(uploaded.keys())
    rows = []
    row_num = 0
    for wh in sorted(all_warehouses, key=lambda w: int(w) if w.isdigit() else 0):
        row_num += 1
        in_current = wh in current
        in_uploaded = wh in uploaded

        if in_current and in_uploaded:
            row_data = dict(current[wh])
            row_data["_status"] = "unchanged"
        elif in_current and not in_uploaded:
            row_data = dict(current[wh])
            row_data["_status"] = "removed"
        else:
            # New warehouse — pull Name, City, State from uploaded CSV
            row_data = dict(uploaded[wh])
            row_data["_status"] = "new"

        row_data["Row"] = row_num
        rows.append(row_data)

    return jsonify({"rows": [_row_with_columns(r, REGIONS_AND_PORTS_COLUMNS + ("_status",)) for r in rows]})


@app.route("/api/regions-and-ports/apply-local", methods=["POST"])
def rap_apply_local():
    """Apply a local file: version changed rows (deactivate old, insert new)."""
    filename = request.json.get("filename", "") if request.is_json else ""
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    local_path = UPLOAD_DIR / filename
    if not local_path.exists() or local_path.resolve().parent != UPLOAD_DIR.resolve():
        return jsonify({"error": "File not found"}), 404

    text = local_path.read_text(encoding="utf-8-sig")
    uploaded = _parse_rap_csv_rows(text)

    current_db = db.get_regions_and_ports(active_only=True)
    current_by_wh: dict[str, dict] = {}
    for r in current_db:
        current_by_wh[r["warehouse"]] = r

    updated_count = 0
    new_count = 0
    for wh, up_row in uploaded.items():
        db_row = _rap_api_to_db(up_row)
        if wh in current_by_wh:
            existing = current_by_wh[wh]
            changed = any(
                str(db_row.get(c, "")).strip() != str(existing.get(c, "")).strip()
                for c in db._RAP_COLS if c != "warehouse"
            )
            if changed:
                db.deactivate_regions_and_ports_row(existing["id"])
                db.insert_regions_and_ports_row(db_row)
                updated_count += 1
        else:
            db.insert_regions_and_ports_row(db_row)
            new_count += 1

    return jsonify({"ok": True, "updated": updated_count, "new": new_count})


_RAP_API_TO_DB_COL = {
    "Warehouse": "warehouse", "Name": "name", "City": "city", "State": "state",
    "Region": "region", "Export": "export", "Port": "port", "ESO": "eso",
    "Flat Bed Fees": "flat_bed_fees", "Late Fees": "late_fees",
    "Transportation Adjust": "transportation_adjust",
    "Misc  Fees": "misc_fees", "Consol Interest": "consol_interest",
}


@app.route("/api/regions-and-ports/edit-cell", methods=["POST"])
def rap_edit_cell():
    """Edit a single cell: deactivate existing row, insert new version."""
    data = request.json or {}
    warehouse = str(data.get("warehouse", "")).strip()
    column = str(data.get("column", "")).strip()
    value = str(data.get("value", "")).strip()
    if not warehouse or not column:
        return jsonify({"error": "warehouse and column required"}), 400

    db_col = _RAP_API_TO_DB_COL.get(column)
    if not db_col:
        return jsonify({"error": f"Invalid column: {column}"}), 400

    current_db = db.get_regions_and_ports(active_only=True)
    existing = next((r for r in current_db if r["warehouse"] == warehouse), None)
    if not existing:
        return jsonify({"error": f"Warehouse {warehouse} not found"}), 404

    db.deactivate_regions_and_ports_row(existing["id"])
    new_row = {c: existing.get(c, "") for c in db._RAP_COLS}
    new_row[db_col] = value
    db.insert_regions_and_ports_row(new_row)

    return jsonify({"ok": True, "warehouse": warehouse, "column": column, "value": value})


@app.route("/api/regions-and-ports/save-edits", methods=["POST"])
def rap_save_edits():
    """Bulk-save Region, Export, Port edits with versioning."""
    data = request.json or {}
    edits = data.get("edits", [])
    if not edits:
        return jsonify({"error": "No edits provided"}), 400

    current_db = db.get_regions_and_ports(active_only=True)
    current_by_wh = {r["warehouse"]: r for r in current_db}
    updated = 0

    for edit in edits:
        wh = str(edit.get("warehouse", "")).strip()
        if not wh or wh not in current_by_wh:
            continue
        existing = current_by_wh[wh]
        new_row = {c: existing.get(c, "") for c in db._RAP_COLS}
        changed = False
        for api_col in ("Region", "Export", "Port"):
            if api_col in edit:
                db_col = _RAP_API_TO_DB_COL[api_col]
                new_val = str(edit[api_col]).strip()
                if new_val != str(existing.get(db_col, "")).strip():
                    new_row[db_col] = new_val
                    changed = True
        if changed:
            db.deactivate_regions_and_ports_row(existing["id"])
            db.insert_regions_and_ports_row(new_row)
            updated += 1

    return jsonify({"ok": True, "count": updated})


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8501)
