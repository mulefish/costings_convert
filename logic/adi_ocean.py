import requests
import urllib3
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
US_ORIGINS = [
    "USCHI", "USLAX", "USNYC", "USSAV", "USHOU",
    "USBAL", "USNOR", "USOAK", "USSEA", "USORF",
    "USMOB", "USNEW", "USCHA", "USDET", "USMEM",
    "USSTL", "USATL", "USDAL", "USDEN", "USPHX",
]
 
params_base = {
    "clientID": "470",
    "clientSecret": "26337353b7962f533d78c762373b3318",
    "destPort": "VNSGN",
}
 
all_rates = []
 
for origin in US_ORIGINS:
    response = requests.get(
        "https://api.cargosavings.com/oceanRatesAPI",
        params={**params_base, "origLocation": origin},
        verify=False
    )
    if response.status_code == 200:
        rates = response.json()
        if isinstance(rates, list):
            all_rates.extend(rates)
            print(f"{origin}: {len(rates)} rates found")
        else:
            print(f"{origin}: unexpected response - {rates}")
    else:
        print(f"{origin}: HTTP {response.status_code}")
 
print(f"\nTotal rates: {len(all_rates)}")
 
# Show summary sorted by 40HC price
all_rates.sort(key=lambda r: float(r.get("40HC") or 0))
for rate in all_rates:
    print(f"{rate['orig']:<30} {rate['carrierName']:<8} 20FT: ${rate['20FT']}  40FT: ${rate['40FT']}  40HC: ${rate['40HC']}  Expires: {rate['expirationDate']}")
 
