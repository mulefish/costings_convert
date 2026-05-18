"""Populate ocean_rates_extract with all origin x destination combinations.

For missing combos, copies rates from the best available donor hub.
Priority: Houston > Dallas > Memphis > Charleston > Savannah > Norfolk.
"""
import sqlite3
from pathlib import Path
from collections import Counter

DB_PATH = Path(__file__).parent / "costings.db"
conn = sqlite3.connect(str(DB_PATH), timeout=10)

COLS = [
    "unOrig", "unDest", "scacCode", "carrierName", "contractNumber", "rateType",
    "amendmentNumber", "effectiveDate", "expirationDate", "updateTime",
    "orig", "via", "dest", "dischargePort", "unVia",
    "40FT", "40HC", "DTHC40FT", "DTHC40HC", "ALLIN40FT", "ALLIN40HC",
]

select_cols = ", ".join(
    f'"{c}"' if c[0].isdigit() else c for c in COLS
)
rows = conn.execute(
    f"SELECT {select_cols} FROM ocean_rates_extract WHERE is_active = 1"
).fetchall()

by_key: dict[tuple, list[dict]] = {}
for r in rows:
    d = dict(zip(COLS, r))
    key = (d["unOrig"], d["unDest"])
    by_key.setdefault(key, []).append(d)

all_origs = sorted(set(k[0] for k in by_key))
all_dests = sorted(set(k[1] for k in by_key))

DONOR_PRIORITY = ["USHOU", "USDAL", "USMEM", "USCHS", "USSAV", "USORF"]
ORIG_LABELS = {
    "USCHS": "Charleston, SC, USCHS",
    "USDAL": "Dallas, TX, USDAL",
    "USHOU": "Houston, TX, USHOU",
    "USMEM": "Memphis, TN, USMEM",
    "USORF": "Norfolk, VA, USORF",
    "USSAV": "Savannah, GA, USSAV",
}

to_insert: list[dict] = []
for orig in all_origs:
    for dest in all_dests:
        if (orig, dest) in by_key:
            continue
        donor_orig = None
        for dp in DONOR_PRIORITY:
            if dp != orig and (dp, dest) in by_key:
                donor_orig = dp
                break
        if not donor_orig:
            continue
        for donor_row in by_key[(donor_orig, dest)]:
            new_row = dict(donor_row)
            new_row["unOrig"] = orig
            new_row["unVia"] = orig
            new_row["orig"] = ORIG_LABELS.get(orig, orig)
            new_row["via"] = ORIG_LABELS.get(orig, orig)
            to_insert.append(new_row)

print(f"Existing active rows: {len(rows)}")
print(f"New rows to insert:   {len(to_insert)}")
c = Counter(r["unOrig"] for r in to_insert)
for o in sorted(c):
    print(f"  {o}: +{c[o]} new rows")

# Insert
insert_cols = COLS + ["is_active"]
col_sql = ", ".join(f'"{c}"' if c[0].isdigit() else c for c in insert_cols)
placeholders = ", ".join(["?"] * len(insert_cols))
insert_sql = f"INSERT INTO ocean_rates_extract ({col_sql}) VALUES ({placeholders})"

for new_row in to_insert:
    vals = [new_row.get(c, "") for c in COLS] + [1]
    conn.execute(insert_sql, vals)

conn.commit()

new_count = conn.execute(
    "SELECT count(*) FROM ocean_rates_extract WHERE is_active = 1"
).fetchone()[0]
print(f"\nDone. Total active rows now: {new_count}")

by_orig2: dict[str, set] = {}
for r in conn.execute(
    "SELECT unOrig, unDest FROM ocean_rates_extract WHERE is_active = 1"
):
    by_orig2.setdefault(r[0], set()).add(r[1])
for o in sorted(by_orig2):
    print(f"  {o}: {len(by_orig2[o])} unique dests")

conn.close()
