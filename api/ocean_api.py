"""
Cargo Savings oceanRatesAPI client.

Used by csv_to_upload/generate_ocean_rates_extract.py and the Jarvis Ocean API view.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://api.cargosavings.com/oceanRatesAPI"

# Full origin list from original script (optional --all-adi-origins)
US_ORIGINS = [
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

# Hubs used in costings (portcode_portcity / populate_all_combos)
DEFAULT_ORIGINS = [
    "USCHS",
    "USDAL",
    "USHOU",
    "USMEM",
    "USORF",
    "USSAV",
]

EXTRACT_COLUMNS = [
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
    "40HC", # if null in 71 use 70 
    "DTHC40FT",
    "DTHC40HC",
    "ALLIN40FT", # if null in 74 use 75 
    "ALLIN40HC",
]


def _client_id() -> str:
    return os.environ.get("CARGO_CLIENT_ID", "470").strip()


def _client_secret() -> str:
    secret = os.environ.get("CARGO_CLIENT_SECRET", "").strip()
    if secret:
        return secret
    return "26337353b7962f533d78c762373b3318"


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
    if n != n:
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


def api_rate_to_extract_row(rate: dict[str, Any]) -> dict[str, str]:
    """Map one oceanRatesAPI object to ocean_rates_extract / CSV row fields."""
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


def fetch_rates(
    session: requests.Session,
    origin: str | None = None,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    dest_port: str | None = None,
    timeout: float = 90.0,
) -> list[dict[str, Any]]:
    """Fetch rates. If origin is None, fetches all rates in a single call."""
    params: dict[str, str] = {
        "clientID": client_id or _client_id(),
        "clientSecret": client_secret or _client_secret(),
    }
    if origin:
        params["origLocation"] = origin
    if dest_port:
        params["destPort"] = dest_port

    label = origin or "ALL"
    response = session.get(API_URL, params=params, timeout=timeout, verify=False)
    if response.status_code != 200:
        raise RuntimeError(f"{label}: HTTP {response.status_code} - {response.text[:200]}")

    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"{label}: expected JSON array, got {type(data).__name__}")

    return data


def fetch_rates_for_origin(
    session: requests.Session,
    origin: str,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    dest_port: str | None = None,
    timeout: float = 90.0,
) -> list[dict[str, Any]]:
    return fetch_rates(
        session, origin,
        client_id=client_id, client_secret=client_secret,
        dest_port=dest_port, timeout=timeout,
    )


def _dedup_rates(
    raw_rates: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], int]:
    """Convert API rate dicts to extract rows, dedup, return (rows, added_count)."""
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for rate in raw_rates:
        if not isinstance(rate, dict):
            continue
        row = api_rate_to_extract_row(rate)
        if not row["unOrig"] or not row["unDest"]:
            continue
        key = tuple(row[c] for c in EXTRACT_COLUMNS)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows, len(rows)


def collect_all_rates(
    origins: list[str] | None = None,
    *,
    dest_port: str | None = None,
    all_adi_origins: bool = False,
    fetch_all: bool = False,
    timeout: float = 90.0,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """
    Fetch rates and return (extract_rows, per_origin_stats).
    fetch_all=True does a single API call without origLocation (all origins at once).
    """
    session = requests.Session()
    cid = client_id or _client_id()
    csec = client_secret or _client_secret()

    if fetch_all:
        try:
            rates = fetch_rates(
                session,
                origin=None,
                client_id=cid,
                client_secret=csec,
                dest_port=dest_port,
                timeout=timeout,
            )
            rows, added = _dedup_rates(rates)
            stats = [{"origin": "ALL", "count": len(rates), "deduped_added": added}]
        except Exception as exc:
            rows = []
            stats = [{"origin": "ALL", "count": 0, "error": str(exc)}]
        return rows, stats

    if origins:
        origin_list = [str(o).strip().upper() for o in origins if str(o).strip()]
    elif all_adi_origins:
        origin_list = list(US_ORIGINS)
    else:
        origin_list = list(DEFAULT_ORIGINS)

    all_rows: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    stats: list[dict[str, Any]] = []

    for origin in origin_list:
        try:
            rates = fetch_rates_for_origin(
                session,
                origin,
                client_id=cid,
                client_secret=csec,
                dest_port=dest_port,
                timeout=timeout,
            )
            added = 0
            for rate in rates:
                if not isinstance(rate, dict):
                    continue
                row = api_rate_to_extract_row(rate)
                if not row["unOrig"] or not row["unDest"]:
                    continue
                key = tuple(row[c] for c in EXTRACT_COLUMNS)
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append(row)
                added += 1
            stats.append({"origin": origin, "count": len(rates), "deduped_added": added})
        except Exception as exc:
            stats.append({"origin": origin, "count": 0, "error": str(exc)})

    return all_rows, stats


def collect_all_rates_indexed(
    origins: list[str] | None = None,
    **kwargs: Any,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    """Like collect_all_rates but keyed by compound key (caller supplies key fn)."""
    rows, stats = collect_all_rates(origins, **kwargs)
    return rows, stats


if __name__ == "__main__":
    params_base = {
        "clientID": _client_id(),
        "clientSecret": _client_secret(),
        "destPort": "VNSGN",
    }
    all_rates: list[dict[str, Any]] = []
    for origin in US_ORIGINS:
        response = requests.get(
            API_URL,
            params={**params_base, "origLocation": origin},
            verify=False,
        )
        if response.status_code == 200:
            rates = response.json()
            if isinstance(rates, list):
                all_rates.extend(rates)
                print(f"{origin}: {len(rates)} rates found")
            else:
                print(f"{origin}: unexpected response - {rates}")
        else:
            print(f"{origin}: HTTP {response.status_code}")

    print(f"\nTotal rates: {len(all_rates)}")
    all_rates.sort(key=lambda r: float(r.get("40HC") or 0))
    for rate in all_rates:
        print(
            f"{rate['orig']:<30} {rate['carrierName']:<8} "
            f"20FT: ${rate.get('20FT')}  40FT: ${rate.get('40FT')}  "
            f"40HC: ${rate.get('40HC')}  Expires: {rate.get('expirationDate')}"
        )
