"""
Data-centric Mexico inland Export ports (Yecapixtla, Parras, CD Victoria):

1) dischargeport_country — synthetic 5-letter codes (MX*** ) so Destination on GET /api/ocean
   contains the inland city name (Notes search finds them).

2) ocean_rates_extract — clone every active MXZLO (Manzanillo) row to MXYEC / MXPAR / MXCDV with
   same rates/origins; dest/dischargePort set for readability.

Re-run safe: skips discharge rows that exist; skips ocean (unOrig, unVia, unDest, scacCode, contractNumber) dupes.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "costings.db"

# unDest codes (MX prefix → country MX in server.py); labels must contain Export CIF FE substring.
INLAND_PORTS = (
    ("MXYEC", "Yecapixtla, MX"),
    ("MXPAR", "Parras, MX"),
    ("MXCDV", "CD Victoria, MX"),
)


def main() -> None:
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    for code, label in INLAND_PORTS:
        cur.execute(
            """
            INSERT OR IGNORE INTO dischargeport_country (discharge_port, country, is_active)
            VALUES (?, ?, 1)
            """,
            (code, label),
        )
    conn.commit()
    print("dischargeport_country: ensured rows for MXYEC, MXPAR, MXCDV")

    total_ins = 0
    for new_dest, _lbl in INLAND_PORTS:
        before = conn.total_changes
        cur.execute(
            """
            INSERT INTO ocean_rates_extract (
                unOrig, unVia, unDest, orig, via, dest, dischargePort, scacCode, carrierName,
                contractNumber, rateType, amendmentNumber, effectiveDate, expirationDate, updateTime,
                "40FT", "40HC", "DTHC40FT", "DTHC40HC", "ALLIN40FT", "ALLIN40HC", is_active
            )
            SELECT
                src.unOrig,
                src.unVia,
                ? AS unDest,
                src.orig,
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
            WHERE upper(trim(src.unDest)) = 'MXZLO'
              AND src.is_active = 1
              AND NOT EXISTS (
                  SELECT 1 FROM ocean_rates_extract AS x
                  WHERE upper(trim(x.unOrig)) = upper(trim(src.unOrig))
                    AND ifnull(upper(trim(x.unVia)), '') = ifnull(upper(trim(src.unVia)), '')
                    AND upper(trim(x.unDest)) = ?
                    AND ifnull(x.scacCode, '') = ifnull(src.scacCode, '')
                    AND ifnull(x.contractNumber, '') = ifnull(src.contractNumber, '')
                    AND x.is_active = 1
              )
            """,
            (
                new_dest,
                f"{_lbl.split(',')[0]}, MX (same ocean freight as Manzanillo MXZLO)",
                new_dest,
                new_dest,
            ),
        )
        n = conn.total_changes - before
        total_ins += n
        print(f"{new_dest}: inserted {n} row(s) from MXZLO")
    conn.commit()
    conn.close()
    print(f"ocean_rates_extract: total new inland clone row(s): {total_ins} in {DB}")


if __name__ == "__main__":
    main()
