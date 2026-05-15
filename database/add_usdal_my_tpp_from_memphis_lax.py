"""
Idempotent data fix: ocean_rates_extract had no USDAL (Dallas) rows for unDest MYTPP
(Tanjung Pelepas), so Export WTX/DAL Outbound could not match GET /api/ocean.

Clones all active USMEM + USLAX + MYTPP rows to USDAL + same via/dest/rates, with Dallas orig.
Review rates with your pricing team -- numbers match the Memphis LAX lane until true Dallas
contracts are loaded.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "costings.db"


def main() -> None:
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    n_existing = cur.execute(
        """
        SELECT COUNT(*) FROM ocean_rates_extract
        WHERE upper(trim(unOrig)) = 'USDAL'
          AND upper(trim(unDest)) = 'MYTPP'
          AND is_active = 1
        """
    ).fetchone()[0]
    if n_existing > 0:
        print(f"Skip: already {n_existing} active USDAL->MYTPP row(s) in {DB}")
        conn.close()
        return

    cur.execute(
        """
        INSERT INTO ocean_rates_extract (
            unOrig, unVia, unDest, orig, via, dest, dischargePort, scacCode, carrierName,
            contractNumber, rateType, amendmentNumber, effectiveDate, expirationDate, updateTime,
            "40FT", "40HC", "DTHC40FT", "DTHC40HC", "ALLIN40FT", "ALLIN40HC", is_active
        )
        SELECT
            'USDAL' AS unOrig,
            unVia,
            unDest,
            'Dallas, TX, USDAL' AS orig,
            via,
            dest,
            dischargePort,
            scacCode,
            carrierName,
            contractNumber,
            rateType,
            amendmentNumber,
            effectiveDate,
            expirationDate,
            updateTime,
            "40FT",
            "40HC",
            "DTHC40FT",
            "DTHC40HC",
            "ALLIN40FT",
            "ALLIN40HC",
            is_active
        FROM ocean_rates_extract
        WHERE upper(trim(unOrig)) = 'USMEM'
          AND upper(trim(unVia)) = 'USLAX'
          AND upper(trim(unDest)) = 'MYTPP'
          AND is_active = 1
        """
    )
    inserted = conn.total_changes
    conn.commit()
    print(f"Inserted {inserted} USDAL->MYTPP row(s) (cloned from USMEM+USLAX+MYTPP) into {DB}")
    conn.close()


if __name__ == "__main__":
    main()
