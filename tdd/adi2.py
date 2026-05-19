import requests
import urllib3
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

response = requests.get(
    "https://api.cargosavings.com/oceanRatesAPI",
    params={
        "clientID": "470",
        "clientSecret": "26337353b7962f533d78c762373b3318",
    },
    verify=False,
    timeout=60  # give it time, could be a large response
)

rates = response.json()
print(f"Total rates: {len(rates)}")

# Save everything to CSV
df = pd.DataFrame(rates)
df.to_csv("all_ocean_rates.csv", index=False)
print(df[["orig", "dest", "carrierName", "20FT", "40FT", "40HC", "effectiveDate", "expirationDate"]].head(20))
 
