import sys
import pandas as pd

if len(sys.argv) < 2:
    print("Usage: python find_dupes.py <csv_file> [key_col1,key_col2,...]")
    print("  If no key columns given, checks for fully identical rows.")
    print("  Example: python find_dupes.py OTR_Rates.csv ORIGINCITY,DESTINATIONCITY,CARGOTYPE")
    sys.exit(1)

csv_path = sys.argv[1]
df = pd.read_csv(csv_path)
df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

if len(sys.argv) >= 3:
    keys = [k.strip().upper() for k in sys.argv[2].split(",")]
    missing = [k for k in keys if k not in df.columns]
    if missing:
        print(f"ERROR: columns not found: {missing}")
        print(f"Available: {list(df.columns)}")
        sys.exit(1)
else:
    keys = list(df.columns)

dupes = df[df.duplicated(subset=keys, keep=False)].sort_values(keys)

if dupes.empty:
    print(f"No duplicates found on {keys}")
else:
    print(f"{len(dupes)} rows involved in duplicates on {keys}:\n")
    print(dupes.to_string(index=False))
