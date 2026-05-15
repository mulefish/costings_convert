"""
Data for Export outbound hubs (WTX, WTXH, STX, MR5, ER5, HOU, DAL → Dallas / Houston /
Memphis / Savannah ocean ports): add dischargeport_country labels + ocean_rates_extract rows
on all four origins (USDAL, USHOU, USMEM, USSAV) for:

  Guatemala: Amatitlan, Palin
  Honduras: Naco
  Spain: Santa Barbara
  Italy: Bergamo, Salerno
  Other: Batumi (synthetic OTBTM + countrycode OT→"Other" so Ocean Country matches Export Base)

Templates clone existing contract rates (same numbers as source row). Cross-hub clones copy
rates from another US origin when this hub has no lane for that country (review with pricing).

Re-run safe: NOT EXISTS on (unOrig, unVia, unDest, scacCode, contractNumber) active.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "costings.db"

HUBS = ("USDAL", "USHOU", "USMEM", "USSAV")
# Prefer these donors when borrowing a row from another hub for the same template unDest.
DONOR_HUB_ORDER = ("USDAL", "USMEM", "USHOU", "USSAV", "USCHS", "USORF")

HUB_ORIG_FALLBACK = {
    "USDAL": "Dallas, TX, USDAL",
    "USHOU": "Houston, TX, USHOU",
    "USMEM": "Memphis, TN, USMEM",
    "USSAV": "Savannah, GA, USSAV",
}

# (new_unDest, discharge label for lookup / Notes, template unDests in order, optional country prefix for any-port fallback)
INLAND_SPECS: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("GTAMT", "Amatitlan, GT", ("GTPRQ", "GTGUA", "GTPBR"), "GT"),
    ("GTPAL", "Palin, GT", ("GTPRQ", "GTGUA", "GTPBR"), "GT"),
    ("HNNAC", "Naco, HN", ("HNPCR",), "HN"),
    ("ESSBT", "Santa Barbara, ES", ("ESALG", "ESVLC", "ESBCN"), "ES"),
    ("ITBGM", "Bergamo, IT", ("ITSPE",), "IT"),
    ("ITSAL", "Salerno, IT", ("ITSPE",), "IT"),
    ("OTBTM", "Batumi, OT", ("TRMER",), None),
)


def _hub_orig(conn: sqlite3.Connection, hub: str) -> str:
    row = conn.execute(
        """
        SELECT orig FROM ocean_rates_extract
        WHERE upper(trim(unOrig)) = ? AND orig IS NOT NULL AND trim(orig) != ''
        LIMIT 1
        """,
        (hub,),
    ).fetchone()
    if row and row[0]:
        return str(row[0]).strip()
    return HUB_ORIG_FALLBACK.get(hub, hub)


def _fetch_rows_same_hub_template(
    conn: sqlite3.Connection, hub: str, template: str
) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(
        conn.execute(
            """
            SELECT * FROM ocean_rates_extract
            WHERE upper(trim(unOrig)) = ? AND upper(trim(unDest)) = ? AND is_active = 1
            """,
            (hub, template.upper()),
        )
    )


def _fetch_rows_same_hub_country(conn: sqlite3.Connection, hub: str, prefix: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(
        conn.execute(
            """
            SELECT * FROM ocean_rates_extract
            WHERE upper(trim(unOrig)) = ? AND upper(trim(unDest)) LIKE ? AND is_active = 1
            """,
            (hub, prefix.upper() + "%"),
        )
    )


def _fetch_rows_template_any_hub(conn: sqlite3.Connection, template: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    for h in DONOR_HUB_ORDER:
        rows = _fetch_rows_same_hub_template(conn, h, template)
        if rows:
            return rows
    return []


def _resolve_sources(
    conn: sqlite3.Connection, hub: str, templates: tuple[str, ...], country_prefix: str | None
) -> tuple[list[sqlite3.Row], str]:
    for t in templates:
        rows = _fetch_rows_same_hub_template(conn, hub, t)
        if rows:
            return rows, t
    if country_prefix:
        rows = _fetch_rows_same_hub_country(conn, hub, country_prefix)
        if rows:
            return rows, str(rows[0]["unDest"] or "").strip().upper()
    for t in templates:
        rows = _fetch_rows_template_any_hub(conn, t)
        if rows:
            return rows, t
    return [], ""


def _dest_line(label: str, template_used: str) -> str:
    city = label.split(",")[0].strip()
    cc = label.split(",")[-1].strip() if "," in label else ""
    return f"{city}, {cc} (same ocean freight as {template_used})"


def _insert_clone_if_absent(conn: sqlite3.Connection, src: sqlite3.Row, hub: str, hub_orig: str, new_dest: str, dest_line: str) -> int:
    before = conn.total_changes
    conn.execute(
        """
        INSERT INTO ocean_rates_extract (
            unOrig, unVia, unDest, orig, via, dest, dischargePort, scacCode, carrierName,
            contractNumber, rateType, amendmentNumber, effectiveDate, expirationDate, updateTime,
            "40FT", "40HC", "DTHC40FT", "DTHC40HC", "ALLIN40FT", "ALLIN40HC", is_active
        )
        SELECT
            ? AS unOrig,
            src.unVia,
            ? AS unDest,
            ? AS orig,
            src.via,
            ? AS dest,
            ? AS dischargePort,
            src.scacCode,
            src.carrierName,
            src.contractNumber,
            src.rateType,
            src.amendmentNumber,
            src.effectiveDate,
            src.expirationDate,
            src.updateTime,
            src."40FT",
            src."40HC",
            src."DTHC40FT",
            src."DTHC40HC",
            src."ALLIN40FT",
            src."ALLIN40HC",
            src.is_active
        FROM ocean_rates_extract AS src
        WHERE src.id = ?
          AND NOT EXISTS (
              SELECT 1 FROM ocean_rates_extract AS x
              WHERE upper(trim(x.unOrig)) = ?
                AND ifnull(upper(trim(x.unVia)), '') = ifnull(upper(trim(src.unVia)), '')
                AND upper(trim(x.unDest)) = ?
                AND ifnull(x.scacCode, '') = ifnull(src.scacCode, '')
                AND ifnull(x.contractNumber, '') = ifnull(src.contractNumber, '')
                AND x.is_active = 1
          )
        """,
        (
            hub,
            new_dest,
            hub_orig,
            dest_line,
            new_dest,
            src["id"],
            hub,
            new_dest.upper(),
        ),
    )
    return conn.total_changes - before


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO countrycode_country (countrycode, country, is_active)
        VALUES ('OT', 'Other', 1)
        """
    )

    for code, label, _, _ in INLAND_SPECS:
        cur.execute(
            """
            INSERT OR IGNORE INTO dischargeport_country (discharge_port, country, is_active)
            VALUES (?, ?, 1)
            """,
            (code, label),
        )
    conn.commit()
    print("Ensured countrycode OT->Other and discharge rows for", len(INLAND_SPECS), "ports")

    hub_orig = {h: _hub_orig(conn, h) for h in HUBS}
    total_ins = 0

    for new_dest, label, templates, country_prefix in INLAND_SPECS:
        per_port = 0
        for hub in HUBS:
            rows, tmpl_used = _resolve_sources(conn, hub, templates, country_prefix)
            if not rows or not tmpl_used:
                print(f"  SKIP {new_dest} @ {hub}: no template source ({templates})")
                continue
            dest_line = _dest_line(label, tmpl_used)
            for src in rows:
                n = _insert_clone_if_absent(conn, src, hub, hub_orig[hub], new_dest, dest_line)
                per_port += n
        conn.commit()
        print(f"{new_dest}: inserted {per_port} row(s)")
        total_ins += per_port

    conn.close()
    print(f"Done. Total new ocean rows: {total_ins} in {DB}")


if __name__ == "__main__":
    main()
