import requests

API_KEY = "hsYsfvOXeyRVTWfrisWcfrud6XK8VMtZcrV1m4on"

url = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
params = {
"api_key": API_KEY,
"frequency": "weekly",
"data[]": "value",
"facets[product][]": "EPD2D",   # No. 2 Diesel
"facets[duoarea][]": "NUS",     # National U.S.
"sort[0][column]": "period",
"sort[0][direction]": "desc",
"length": 52,  # last 52 weeks
}

response = requests.get(url, params=params)
response.raise_for_status()
data = response.json()

for row in data["response"]["data"]:
    print(f"{row['period']}  ${row['value']}/gal")
