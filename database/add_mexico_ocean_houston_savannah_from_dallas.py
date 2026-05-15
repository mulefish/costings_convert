"""
Idempotent: clone Dallas (USDAL) Mexico seaport lanes to Houston (USHOU) and Savannah (USSAV).

ocean_rates_extract only had USDAL + USMEM for MXZLO / MXLZC / PAMIT, so Export Outbound
columns WTXH, STX, HOU (Houston hub) and ER5 (Savannah) could not match. Same rates as Dallas
until real Houston/Savannah contracts exist -- review with pricing.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "costings.db"

CLONE_TARGETS = (
    ("USHOU", "Houston, TX, USHOU"),
    ("USSAV", "Savannah, GA, USSAV"),
)


def main() -> None:
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    total_ins = 0
    for un_orig, orig_label in CLONE_TARGETS:
        before = conn.total_changes
        cur.execute(
            """
            INSERT INTO ocean_rates_extract (
                unOrig, unVia, unDest, orig, via, dest, dischargePort, scacCode, carrierName,
                contractNumber, rateType, amendmentNumber, effectiveDate, expirationDate, updateTime,
                "40FT", "40HC", "DTHC40FT", "DTHC40HC", "ALLIN40FT", "ALLIN40HC", is_active
            )
            SELECT
                ? AS unOrig,
                src.unVia,
                src.unDest,
                ? AS orig,
                src.via,
                src.dest,
                src.dischargePort,
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
            WHERE upper(trim(src.unOrig)) = 'USDAL'
              AND upper(trim(src.unDest)) IN ('MXZLO', 'MXLZC', 'PAMIT')
              AND src.is_active = 1
              AND NOT EXISTS (
                  SELECT 1 FROM ocean_rates_extract AS x
                  WHERE upper(trim(x.unOrig)) = ?
                    AND upper(trim(x.unDest)) = upper(trim(src.unDest))
                    AND ifnull(upper(trim(x.unVia)), '') = ifnull(upper(trim(src.unVia)), '')
                    AND ifnull(x.scacCode, '') = ifnull(src.scacCode, '')
                    AND ifnull(x.contractNumber, '') = ifnull(src.contractNumber, '')
                    AND x.is_active = 1
              )
            """,
            (un_orig, orig_label, un_orig),
        )
        n = conn.total_changes - before
        total_ins += n
        print(f"{un_orig}: inserted {n} row(s)")
    conn.commit()
    conn.close()
    print(f"Done. Total new rows: {total_ins} in {DB}")


if __name__ == "__main__":
    main()
