"""API inventory for the API Test view (internal Flask routes + external services)."""

from __future__ import annotations

from typing import Any

EXTERNAL_APIS: list[dict[str, Any]] = [
    {
        "id": "cargo-ocean",
        "name": "Cargo Savings Ocean Rates",
        "url": "https://api.cargosavings.com/oceanRatesAPI",
        "method": "GET",
        "description": (
            "Contract ocean rates by US origin (origLocation) and optional destPort. "
            "Returns JSON array of rate objects (40FT, 40HC, DTHC, SCAC, dates, etc.)."
        ),
        "used_by": ["Ocean API view", "api/ocean_api.py", "generate_ocean_rates_extract.py"],
        "test_endpoint": "/api/test/cargo-ocean",
        "test_method": "POST",
        "test_body_hint": '{"origin":"USDAL","dest_port":""}',
    },
    {
        "id": "hartree-sofr",
        "name": "Hartree SOFR fixing rates",
        "url": "https://settles-api.mosaic.hartreepartners.com/settles/api/v1/getIRFixingRateTS/SOFR/{start}/{end}",
        "method": "GET",
        "description": "Daily SOFR time series. Latest value feeds control panel SOFR and EDF Interest Rate.",
        "used_by": ["Jarvis control panel", "database/SOFR.py", "POST /api/sofr-refresh"],
        "test_endpoint": "/api/test/sofr",
        "test_method": "GET",
    },
]

# path -> metadata for Flask /api/* routes
ROUTE_META: dict[str, dict[str, Any]] = {
    "/api/control-panel": {
        "group": "Jarvis",
        "description": "Global control panel values (fuel, GRI, SOFR, etc.).",
        "used_by": ["Jarvis"],
    },
    "/api/sofr-refresh": {
        "group": "Jarvis",
        "description": "Fetch latest SOFR from Hartree API and update control panel.",
        "used_by": ["Jarvis"],
        "writes_data": True,
    },
    "/api/consolidation": {
        "group": "Jarvis",
        "description": "Consolidation bale / wrap / total by region.",
        "used_by": ["Jarvis", "USD", "PTS", "Export"],
    },
    "/api/consolidation-days-storage": {
        "group": "Jarvis",
        "description": "Consolidation days storage parameters.",
        "used_by": ["Jarvis"],
    },
    "/api/drayage": {
        "group": "Jarvis",
        "description": "Drayage and ocean base by region.",
        "used_by": ["Jarvis", "USD", "CIF", "Export"],
    },
    "/api/document-cif": {
        "group": "Jarvis",
        "description": "Document CIF fees by country (doc, GRI, etc.).",
        "used_by": ["Jarvis", "Documentation", "Export", "Ocean"],
    },
    "/api/usa-forwarding-cost": {
        "group": "Jarvis",
        "description": "USA forwarding cost table.",
        "used_by": ["Jarvis", "Documentation", "Export"],
    },
    "/api/dthc-prepaid": {
        "group": "Jarvis",
        "description": "DTHC prepaid Yes/No by country code.",
        "used_by": ["Jarvis", "Ocean API", "Ocean Costing"],
    },
    "/api/themes": {
        "group": "Jarvis",
        "description": "Country theme colors for Export row shading.",
        "used_by": ["Jarvis", "Export"],
    },
    "/api/themes/save": {
        "group": "Jarvis",
        "description": "Save theme rows.",
        "used_by": ["Jarvis"],
        "writes_data": True,
    },
    "/api/lc-bank-cost": {
        "group": "Jarvis",
        "description": "LC bank cost parameters.",
        "used_by": ["LC_Bank_Cost", "Documentation"],
    },
    "/api/export-data": {
        "group": "Export",
        "description": "Export master list (countries and CIF FE ports).",
        "used_by": ["Export"],
    },
    "/api/export/documentation-totals": {
        "group": "Export",
        "description": "Documentation section totals by country key.",
        "used_by": ["Export"],
    },
    "/api/export/cif-totals": {
        "group": "Export",
        "description": "CIF section totals by country key.",
        "used_by": ["Export"],
    },
    "/api/otr": {
        "group": "OTR",
        "description": "OTR rates with FSC/GRI from control panel.",
        "used_by": ["OTR", "USD"],
    },
    "/api/otr/local-files": {
        "group": "OTR upload",
        "description": "List CSV files in csv_to_upload for OTR compare.",
        "used_by": ["OTR"],
    },
    "/api/otr/compare-local": {
        "group": "OTR upload",
        "description": "Compare local OTR CSV to database.",
        "used_by": ["OTR"],
    },
    "/api/otr/apply-local": {
        "group": "OTR upload",
        "description": "Apply local OTR CSV to database.",
        "used_by": ["OTR"],
        "writes_data": True,
    },
    "/api/ocean": {
        "group": "Ocean",
        "description": "Ocean rates rows (from ocean_rates_extract).",
        "used_by": ["Ocean API", "Ocean Costing", "Export"],
    },
    "/api/ocean/local-files": {
        "group": "Ocean upload (legacy)",
        "description": "List 470OceanRatesExtract CSV files in csv_to_upload.",
        "used_by": [],
    },
    "/api/ocean/compare-local": {
        "group": "Ocean upload (legacy)",
        "description": "Compare local ocean CSV to active DB rows.",
        "used_by": [],
    },
    "/api/ocean/apply-local": {
        "group": "Ocean upload (legacy)",
        "description": "Apply local ocean CSV to ocean_rates_extract.",
        "used_by": [],
        "writes_data": True,
    },
    "/api/ocean-api/compare": {
        "group": "Ocean API",
        "description": "Fetch Cargo Savings API and compare to DB.",
        "used_by": ["Ocean API"],
    },
    "/api/ocean-api/apply": {
        "group": "Ocean API",
        "description": "Fetch Cargo Savings API and apply to DB.",
        "used_by": ["Ocean API"],
        "writes_data": True,
    },
    "/api/ocean-rates-extract": {
        "group": "Ocean",
        "description": "Raw ocean_rates_extract rows for Notes grid.",
        "used_by": ["Notes"],
    },
    "/api/ocean-rates-extract/save": {
        "group": "Ocean",
        "description": "Save edited ocean_rates_extract rows from Notes.",
        "used_by": ["Notes"],
        "writes_data": True,
    },
    "/api/ocean-costing-rules": {
        "group": "Ocean Costing",
        "description": "Country freight aggregation rules.",
        "used_by": ["Ocean Costing"],
    },
    "/api/seam-tariffs": {
        "group": "Tariffs",
        "description": "SEAM tariff rows.",
        "used_by": ["Seam Tariffs", "USD", "PTS"],
    },
    "/api/cert-tariffs": {
        "group": "Tariffs",
        "description": "Cert tariff rows.",
        "used_by": ["Cert Tariffs"],
    },
    "/api/usd": {
        "group": "Costing views",
        "description": "USD costing table rows.",
        "used_by": ["USD"],
    },
    "/api/pts": {
        "group": "Costing views",
        "description": "PTS costing table rows.",
        "used_by": ["PTS"],
    },
    "/api/cif": {
        "group": "Costing views",
        "description": "CIF region rows.",
        "used_by": ["CIF", "Export"],
    },
    "/api/regions-and-ports": {
        "group": "Regions",
        "description": "Regions and ports reference data.",
        "used_by": ["Regions and Ports"],
    },
    "/api/notes": {
        "group": "Notes",
        "description": "User notes CRUD.",
        "used_by": ["Jarvis notes modal"],
    },
    "/api/db-tables": {
        "group": "Database",
        "description": "SQLite table names.",
        "used_by": ["Notes"],
    },
    "/api/db-active-counts": {
        "group": "Database",
        "description": "Per-table active/inactive row counts.",
        "used_by": ["Notes"],
    },
    "/api/db-query": {
        "group": "Database",
        "description": "Query one table with optional is_active filter.",
        "used_by": ["Notes"],
    },
    "/api/db-search": {
        "group": "Database",
        "description": "Search all tables for a string.",
        "used_by": ["Notes"],
    },
}


def build_internal_catalog(app) -> list[dict[str, Any]]:
    """Enumerate Flask /api routes with metadata."""
    skip_prefixes = ("/api/catalog", "/api/test/")
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        path = rule.rule
        if not path.startswith("/api/"):
            continue
        if any(path.startswith(p) for p in skip_prefixes):
            continue
        if path in seen:
            continue
        seen.add(path)

        methods = sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))
        meta = ROUTE_META.get(path, {})
        routes.append(
            {
                "path": path,
                "methods": methods,
                "group": meta.get("group", "Other"),
                "description": meta.get("description", ""),
                "used_by": meta.get("used_by", []),
                "writes_data": bool(meta.get("writes_data")),
            }
        )

    return routes


def build_api_catalog(app) -> dict[str, Any]:
    internal = build_internal_catalog(app)
    groups: dict[str, list] = {}
    for row in internal:
        g = row["group"]
        groups.setdefault(g, []).append(row)

    return {
        "external": EXTERNAL_APIS,
        "internal": internal,
        "internal_by_group": [
            {"group": g, "apis": groups[g]} for g in sorted(groups.keys())
        ],
    }
