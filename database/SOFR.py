import requests
import pandas as pd
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://settles-api.mosaic.hartreepartners.com"

def get_sofr_rates(start_date: str, end_date: str) -> pd.DataFrame:

    url = f"{BASE_URL}/settles/api/v1/getIRFixingRateTS/SOFR/{start_date}/{end_date}"

    response = requests.get(url, verify=False, timeout=30)
    response.raise_for_status()

    df = pd.DataFrame(response.json())

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["sofr_pct"] = df["value"] * 100

    return df


def update_sofr_in_db():
    """Fetch latest SOFR rate and update the control_panel table in the database."""
    import sqlite3
    from datetime import datetime, timedelta
    from pathlib import Path

    db_path = Path(__file__).resolve().parent / "costings.db"

    end = datetime.now()
    start = end - timedelta(days=30)
    df = get_sofr_rates(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df is None or df.empty:
        print("[SOFR] No data returned from API")
        return

    latest_rate = float(df.iloc[-1]["sofr_pct"])
    latest_date = df.iloc[-1]["date"]
    print(f"[SOFR] Latest rate: {latest_rate}% ({latest_date:%Y-%m-%d})")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Load current control panel
    cp = {}
    for row in conn.execute("SELECT [key], [value] FROM control_panel"):
        cp[row["key"]] = float(row["value"]) if row["value"] is not None else 0.0

    cp["SOFR"] = latest_rate

    # Recompute derived: EDF Interest Rate = SOFR + EDF Rate
    edf_rate = cp.get("EDF Rate", 0.0)
    cp["EDF Interest Rate"] = latest_rate + edf_rate

    # Cert Interest = ((Daily Spot + Basis) / 12) * EDF Interest Rate
    daily_spot = cp.get("Daily Spot", 0.0)
    basis = cp.get("Basis", 0.0)
    cp["Cert Interest"] = round(((daily_spot + basis) / 12.0) * cp["EDF Interest Rate"], 2)

    conn.executemany(
        "INSERT OR REPLACE INTO control_panel (key, value) VALUES (?, ?)",
        [(k, v) for k, v in cp.items()],
    )
    conn.commit()
    conn.close()
    print(f"[SOFR] Database updated — SOFR={latest_rate}%, EDF Interest Rate={cp['EDF Interest Rate']}%, Cert Interest={cp['Cert Interest']}")


if __name__ == "__main__":
    update_sofr_in_db()
