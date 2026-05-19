#!/usr/bin/env python3
"""
Fetch ocean rates from Cargo Savings (same API as adi.py) and write
470OceanRatesExtract.csv for Jarvis / ocean_rates_extract import.

Output columns match html/server.py _OCEAN_EXTRACT_CSV_COLS and
html/database.py ocean_rates_extract.

Usage:
  python generate_ocean_rates_extract.py
  python generate_ocean_rates_extract.py -o 470OceanRatesExtract.csv
  python generate_ocean_rates_extract.py --origins USCHS,USDAL,USHOU
  CARGO_CLIENT_ID=470 CARGO_CLIENT_SECRET=... python generate_ocean_rates_extract.py

Compare in the app (OCEAN view) before Apply — Apply deactivates DB rows
not present in the CSV.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://api.cargosavings.com/oceanRatesAPI"

# Origins used by costings (portcode_portcity / populate_all_combos.py)
DEFAULT_ORIGINS = [
    "USCHS",
    "USDAL",
    "USHOU",
    "USMEM",
    "USORF",
    "USSAV",
]

# Broader list from adi.py (optional --all-adi-origins)
ADI_ORIGINS = [
    "USCHI",
    "USLAX",
    "USNYC",
    "USSAV",
    "USHOU",
    "USBAL",
    "USNOR",
    "USOAK",
    "USSEA",
    "USORF",
    "USMOB",
    "USNEW",
    "USCHA",
    "USDET",
    "USMEM",
    "USSTL",
    "USATL",
    "USDAL",
    "USDEN",
    "USPHX",
]

CSV_COLUMNS = [
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
]


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    if not (n == n):  # NaN
        return None
    return n


def _fmt_num(value: Any) -> str:
    n = _parse_float(value)
    if n is None:
        return ""
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def _fmt_date(value: Any) -> str:
    """API ISO date (2026-04-01) -> M/D/YYYY like existing extract CSV."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s[:19], fmt)
            return f"{dt.month}/{dt.day}/{dt.year}"
        except ValueError:
            continue
    return s


def _fmt_update_time(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:19].replace("T", " "), fmt)
            if dt.hour or dt.minute:
                h = dt.hour % 12 or 12
                ampm = "AM" if dt.hour < 12 else "PM"
                return f"{dt.month}/{dt.day}/{dt.year} {h}:{dt.minute:02d} {ampm}"
            return f"{dt.month}/{dt.day}/{dt.year}"
        except ValueError:
            continue
    return _fmt_date(value)


def _allin(base: Any, dthc: Any) -> str:
    b = _parse_float(base)
    d = _parse_float(dthc)
    if b is None and d is None:
        return ""
    return _fmt_num((b or 0.0) + (d or 0.0))


def api_rate_to_csv_row(rate: dict[str, Any]) -> dict[str, str]:
    """Map one oceanRatesAPI object to a CSV row dict."""
    ft40 = rate.get("40FT")
    hc40 = rate.get("40HC")
    dthc_ft = rate.get("DTHC40FT")
    dthc_hc = rate.get("DTHC40HC")

    return {
        "unOrig": str(rate.get("unOrig") or "").strip(),
        "unVia": str(rate.get("unVia") or rate.get("unOrig") or "").strip(),
        "unDest": str(rate.get("unDest") or "").strip(),
        "orig": str(rate.get("orig") or "").strip(),
        "via": str(rate.get("via") or rate.get("orig") or "").strip(),
        "dest": str(rate.get("dest") or "").strip(),
        "dischargePort": str(rate.get("dischargePort") or "").strip(),
        "scacCode": str(rate.get("scacCode") or "").strip(),
        "carrierName": str(rate.get("carrierName") or "").strip(),
        "contractNumber": str(rate.get("contractNumber") or "").strip(),
        "rateType": str(rate.get("rateType") or "").strip(),
        "amendmentNumber": str(rate.get("amendmentNumber") or "").strip(),
        "effectiveDate": _fmt_date(rate.get("effectiveDate")),
        "expirationDate": _fmt_date(rate.get("expirationDate")),
        "updateTime": _fmt_update_time(rate.get("updateTime")),
        "40FT": _fmt_num(ft40),
        "40HC": _fmt_num(hc40),
        "DTHC40FT": _fmt_num(dthc_ft),
        "DTHC40HC": _fmt_num(dthc_hc),
        "ALLIN40FT": _allin(ft40, dthc_ft),
        "ALLIN40HC": _allin(hc40, dthc_hc),
    }


def fetch_rates_for_origin(
    session: requests.Session,
    client_id: str,
    client_secret: str,
    origin: str,
    dest_port: str | None,
    timeout: float,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "clientID": client_id,
        "clientSecret": client_secret,
        "origLocation": origin,
    }
    if dest_port:
        params["destPort"] = dest_port

    response = session.get(API_URL, params=params, timeout=timeout, verify=False)
    if response.status_code != 200:
        raise RuntimeError(f"{origin}: HTTP {response.status_code} — {response.text[:200]}")

    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"{origin}: expected JSON array, got {type(data).__name__}")

    return data


def collect_all_rates(
    origins: list[str],
    client_id: str,
    client_secret: str,
    dest_port: str | None,
    timeout: float,
) -> list[dict[str, str]]:
    session = requests.Session()
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    for origin in origins:
        rates = fetch_rates_for_origin(
            session, client_id, client_secret, origin, dest_port, timeout
        )
        print(f"{origin}: {len(rates)} rates")
        for rate in rates:
            if not isinstance(rate, dict):
                continue
            row = api_rate_to_csv_row(rate)
            if not row["unOrig"] or not row["unDest"]:
                continue
            # Dedupe identical API rows (same lane + contract + dates + SCAC)
            key = tuple(row[c] for c in CSV_COLUMNS)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    default_secret = os.environ.get("CARGO_CLIENT_SECRET", "")
    if not default_secret:
        # Same default as adi.py for local use; prefer env in shared environments.
        default_secret = "26337353b7962f533d78c762373b3318"

    parser = argparse.ArgumentParser(
        description="Generate 470OceanRatesExtract.csv from Cargo Savings oceanRatesAPI.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "470OceanRatesExtract.csv",
        help="Output CSV path (default: csv_to_upload/470OceanRatesExtract.csv)",
    )
    parser.add_argument(
        "--origins",
        type=str,
        default="",
        help="Comma-separated UN/LOC origin codes (default: US hub list)",
    )
    parser.add_argument(
        "--all-adi-origins",
        action="store_true",
        help=f"Use all {len(ADI_ORIGINS)} origins from adi.py instead of default hubs",
    )
    parser.add_argument(
        "--dest-port",
        type=str,
        default="",
        help="Optional destPort filter (e.g. VNSGN). Omit for all destinations per origin.",
    )
    parser.add_argument("--client-id", default=os.environ.get("CARGO_CLIENT_ID", "470"))
    parser.add_argument("--client-secret", default=default_secret)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    if args.origins.strip():
        origins = [x.strip().upper() for x in args.origins.split(",") if x.strip()]
    elif args.all_adi_origins:
        origins = list(ADI_ORIGINS)
    else:
        origins = list(DEFAULT_ORIGINS)

    dest_port = args.dest_port.strip().upper() or None

    print(f"Fetching from {API_URL}")
    print(f"Origins ({len(origins)}): {', '.join(origins)}")
    if dest_port:
        print(f"destPort filter: {dest_port}")
    else:
        print("destPort: (none - all destinations per origin)")

    try:
        rows = collect_all_rates(
            origins,
            args.client_id,
            args.client_secret,
            dest_port,
            args.timeout,
        )
    except (requests.RequestException, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    write_csv(args.output, rows)
    print(f"\nWrote {len(rows)} rows -> {args.output}")
    print("Next: OCEAN view -> Compare Local -> review -> Apply only if intended.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
