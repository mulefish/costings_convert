import requests
import pandas as pd

api_key = r"fucE0PEHafFwh7UODPPKoelkuj0fXtxFXN4bwAFa"
url = (
    "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
    "?frequency=weekly"
    "&data[0]=value"
    "&sort[0][column]=period"
    "&sort[0][direction]=desc"
    "&offset=0&length=1"
    f"&api_key={api_key}"
)

response = requests.get(url)
data = response.json()
records = data['response']['data']

df = pd.DataFrame(records)
print(df)
