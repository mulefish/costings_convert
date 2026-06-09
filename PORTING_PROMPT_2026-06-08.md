# Porting Prompt — 2026-06-08 Changes (Vanilla JS → React)

You are porting changes from the vanilla JS + Flask app (`costings_convert`) into the React + Redux + Mantine app (`costings_react`). Below is what was changed and the logic behind each piece. The React app uses Redux Toolkit (async thunks for fetch/save), Mantine v9 components, and Flask on port 5000 with SQLite.

---

## 1. Control Panel — New Keys

**What changed (server.py):**
- Added to `CONTROL_PANEL_DEFAULTS`:
  - `"Inflation": 0.05` (represents 5%)
  - `"Buffer": 0.0`
- Added `"Delivery Storage"` and `"Stopping Storage"` to `_CP_OBSOLETE_KEYS` so they get purged from the DB on load.
- The control panel PUT endpoint now handles `"Ocean Cost Method"` as a string (previously it fell through to `float()` and would error). Pattern: check `if key == "Ocean Cost Method"`, store as `str`, `continue`.

**What to do in React:**
- Update the API server's `CONTROL_PANEL_DEFAULTS` the same way.
- Add the `"Ocean Cost Method"` string handling to the PUT handler.
- Add `"Delivery Storage"` and `"Stopping Storage"` to `_CP_OBSOLETE_KEYS`.
- In the Jarvis Control Panel component, `Inflation` and `Buffer` should appear as editable number inputs. They are NOT readonly and NOT hidden.

---

## 2. New Endpoint: `GET /api/ocean-base-by-method?method=...`

**What it does:**
- Accepts `method` query param: `"Lowest"`, `"Avg Cheapest 2"`, or `"Avg Cheapest 3"`.
- Loads all ocean rates extract rows from SQLite.
- For each row, resolves the Port (drayage region) from `unOrig` via the port lookup.
- Computes `ocean_freight` using `db.ocean_freight_from_extract_row(raw, prepaid)`.
- Groups positive freight values by port.
- Per port, sorts ascending and applies the method:
  - Lowest: `freights[0]`
  - Avg Cheapest 2: average of first 2
  - Avg Cheapest 3: average of first 3
- Returns `{region: roundedValue}` e.g. `{"Memphis": 1450.00, "Houston": 1320.50, ...}`

**What to do in React:**
- Add this endpoint to the Flask API server (`api/server.py`). The logic is the same — it reuses existing `db.get_ocean_rates_extract_row_dicts()`, `_ocean_build_context()`, and `db.ocean_freight_from_extract_row()`.

---

## 3. Jarvis — Ocean Cost Method Dropdown Above Drayage

**What changed (script.js):**
- A `<select>` dropdown with options `["Lowest", "Avg Cheapest 2", "Avg Cheapest 3"]` is placed above the Drayage table, pre-selected from `controlPanel["Ocean Cost Method"]`.
- On change:
  1. Fetches `GET /api/ocean-base-by-method?method=<selected>`.
  2. For each drayage region in the response, updates the `OceanBase` input in the drayage table UI.
  3. Saves the method to the control panel via `PUT /api/control-panel` with `{"Ocean Cost Method": method}`.
- The user still needs to click "Save drayage" to persist the OceanBase values — the dropdown only updates the UI inputs.

**What to do in React:**
- In the Jarvis Drayage section, add a Mantine `Select` component above the table.
- On change, dispatch a thunk that:
  1. Fetches `/api/ocean-base-by-method?method=...`
  2. Updates the local drayage Redux state's `OceanBase` for each matching region.
  3. Saves the method to the control panel slice.
- The drayage save button persists everything as before.

---

## 4. Export View — Ocean Cost Method Also Updates Drayage

**What changed (script.js):**
- The Export view already had an Ocean Cost Method dropdown. Its change handler now additionally:
  1. Fetches `GET /api/ocean-base-by-method?method=...`
  2. Fetches current drayage from `GET /api/drayage`
  3. Merges the new OceanBase values into the drayage data
  4. Saves via `PUT /api/drayage`
- This means changing the method in Export immediately persists the new OceanBase to the DB (unlike Jarvis where you still click Save).

**What to do in React:**
- In the Export view's method dropdown handler, after saving to control panel, also fetch ocean bases and save updated drayage to the API.

---

## 5. CIF View — Cert Days Input

**What changed (script.js):**
- At the top of the CIF page controls row, added a labeled number input "Cert Days" populated from `GET /api/control-panel` → `"Cert Days"`.
- A "Save" button next to it sends `PUT /api/control-panel` with `{"Cert Days": value}`.
- Shows "Saved" briefly on success.
- `renderCifTable` became `async` to await the control panel fetch.

**What to do in React:**
- In the CIF view component, add a Mantine `NumberInput` + `Button` for Cert Days.
- On save, dispatch the control panel save thunk with `{"Cert Days": value}`.

---

## 6. CIF Stoppage Table (Bottom Table)

**What changed (script.js):**
- **Consolidation section**: Added `Total_Consol = Math.round((Consol_Strg + Consol_Interest) * 100) / 100`. Previously this was not calculated.
- **Cert Cost section**: `USDA`, `ICE`, and `Total Cert` are set to empty string `""` (blank cells). No calculation — TBD.
- **Total Terms Cash**: Now sums `["Total Origin", "Total Transit", "Total_Consol", "Total_Out", "Total_Doc", "Total_CIF"]`. Note: includes `Total_CIF`, excludes `Total Cert` (since it's blank).
- Cash rounds to 2 decimal places.
- **Derivation notes** (`_stopTableDerivation`):
  - Cert Cost columns return `"— not calculated for stoppage"`.
  - Cash formula lists the correct parts including Total CIF, displays with `.toFixed(2)`.

---

## 7. CIF Delivery Table (Middle Table)

**What changed (script.js):**
- `Total_Consol` now rounds to 2 decimal places: `Math.round((Consol_Block + Consol_Strg + Consol_Interest) * 100) / 100`.
- `Cash` now rounds to 2 decimal places: `Math.round(sum * 100) / 100`.

---

## 8. API Test View — Results Column

**What changed (script.js):**
- Both the External and Internal API tables have a new **"Results"** column.
- Each row gets a `<td class="api-result-cell">` with default background `#f5e642` (yellow).
- When the user clicks "Test" on a row, the corresponding result cell is tracked.
- After the test runs:
  - **Pass** (status 200 AND payload is non-null): background `#4caf50` (green), text "Pass".
  - **Fail** (any other status, null payload, or network error): background `#e53935` (red), text "Fail".

**What to do in React:**
- Add a `results` state object keyed by `${kind}-${idx}`.
- Default state: `"pending"` (yellow). After test: `"pass"` (green) or `"fail"` (red).
- Render the cell color based on state.

---

## File Reference

All vanilla JS changes are in `costings_convert/html/static/script.js`.
All server changes are in `costings_convert/html/server.py`.
Database layer is in `costings_convert/html/database.py` (no changes needed there beyond what the server does).
