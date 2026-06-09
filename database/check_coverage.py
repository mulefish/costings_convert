import sqlite3, json
from pathlib import Path

conn = sqlite3.connect(str(Path(__file__).parent / "costings.db"))
conn.row_factory = sqlite3.Row

ocean = conn.execute('''
    SELECT DISTINCT
        lower(trim(p.PortCity)) as hub,
        cc.country as country,
        lower(trim(d.country)) as dest
    FROM ocean_rates_extract o
    JOIN dischargeport_country d ON upper(d.discharge_port) = upper(o.unDest)
    JOIN countrycode_country cc ON upper(cc.countrycode) = upper(substr(o.unDest, 1, 2))
    JOIN portcode_portcity p ON upper(p.PortCode) = upper(o.unOrig)
    WHERE o.is_active = 1
''').fetchall()

ALIASES = {'korea, republic of': 'korea'}
def nc(s):
    s2 = s.strip().lower()
    return ALIASES.get(s2, s2)

def nd(s):
    return s.strip().lower().replace('kwangyang','gwangyang').replace('tao yuan','taoyuan')

by_hub = {}
for row in ocean:
    h = row["hub"]
    by_hub.setdefault(h, set()).add((nc(row["country"]), nd(row["dest"])))

print("Hubs in ocean data:", sorted(by_hub.keys()))
for h in sorted(by_hub.keys()):
    print(f"  {h}: {len(by_hub[h])} country+dest combos")

hubs_map = {
    'WTX': ['dallas'],
    'WTXH': ['houston','dallas'],
    'STX': ['houston','dallas'],
    'MR5': ['memphis'],
    'ER5': ['savannah'],
}

export_rows = conn.execute(
    'SELECT base, ports_json FROM export_data WHERE is_active=1 ORDER BY sort_order'
).fetchall()

print()
for abbr in ['WTX','WTXH','STX','MR5','ER5']:
    try_hubs = hubs_map[abbr]
    missing = []
    ok = []
    for row in export_rows:
        base = row["base"]
        ports = json.loads(row["ports_json"] or "[]")
        for port in ports:
            nb = nc(base)
            np_ = nd(port)
            found = False
            for th in try_hubs:
                for (c, d) in by_hub.get(th, set()):
                    if c == nb and (d == np_ or d in np_ or np_ in d):
                        found = True
                        break
                if found:
                    break
            if found:
                ok.append((base, port))
            else:
                missing.append((base, port))

    total = len(ok) + len(missing)
    print(f"{abbr} ({', '.join(try_hubs)}): {len(ok)}/{total} OK, {len(missing)} MISSING")
    for b, p in missing:
        print(f"  MISS  {b:<15} {p}")

conn.close()
