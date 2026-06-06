import requests
import pandas as pd

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

# Example
sofr = get_sofr_rates("2026-01-01", "2026-12-01")
sofr.tail()
