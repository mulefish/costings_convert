# NOTE TO SELF: This API looks FUN! Graph IT! Get all the dates!
# This file will get only the most recent close.


import requests
import urllib3
import pandas as pd
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://settles-api.mosaic.hartreepartners.com"

YEAR = pd.Timestamp.today().year
MONTHS = [7, 12]  # months in first year
NEXT_YEAR_MONTHS = [3, 5, 7, 12]  # months in following year

TARGET_MONTHS = [f"{YEAR}-{m:02d}" for m in MONTHS] + [f"{YEAR+1}-{m:02d}" for m in NEXT_YEAR_MONTHS]

# Try the last few business days to find the most recent settle
for dt in reversed(list(pd.bdate_range(end=pd.Timestamp.today(), periods=5))):
    as_of_date = dt.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/settles/api/v1/getFutureCurveSettlement/CT/ICE/{as_of_date}"

    print(f"Trying {as_of_date}...", end=" ", flush=True)

    response = requests.get(url, params={"allow_indicative": True}, verify=False, timeout=30)

    if response.status_code != 200:
        print("no data")
        continue

    curve = response.json()
    if not curve:
        print("empty")
        continue

    print("OK")
    print(f"\nSettlements as of {as_of_date}:")
    print(f"{'Contract':<20} {'Settlement':>10}")
    print("-" * 32)

    for contract in curve:
        exp = contract.get("expiration_date", "")
        if exp[:7] in TARGET_MONTHS:
            print(f"{contract.get('instrument_key', ''):<20} {contract.get('value', ''):>10}")

    break
