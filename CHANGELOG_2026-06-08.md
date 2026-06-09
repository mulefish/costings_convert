# Changelog — 2026-06-08

## CIF View

- **Cert Days input** — Added a "Cert Days" input box at the top of the CIF page, populated from the control panel. Includes a Save button that persists the value to the database via the control panel API.

- **Delivery table (middle table)**
  - `Total_Consol` in the Consolidation section now rounds to 2 decimal places.
  - `Cash` in the Total Terms section now rounds to 2 decimal places.

- **Stoppage table (bottom table)**
  - Added `Total_Consol` calculation in the Consolidation section: `Consol_Strg + Consol_Interest`.
  - Cert Cost section (`USDA`, `ICE`, `Total Cert`) left blank — calculations TBD.
  - `Total_CIF` from the CIF section now flows into the `Cash` sum in Total Terms.
  - `Cash` rounds to 2 decimal places.
  - Updated derivation notes to reflect all changes: Cash formula now includes Total CIF instead of Total Cert, and Cert Cost columns show "not calculated for stoppage".

## API Test View

- Added a **Results** column to both the External and Internal API tables.
- Defaults to **yellow** background.
- When a test is run: turns **green** with "Pass" if status is 200 and a payload is received; turns **red** with "Fail" otherwise (error status, no payload, or network failure).

## Control Panel / Jarvis

- Added `Delivery Storage` and `Stopping Storage` to the control panel (default 0.5) — then **removed** them after deciding to revisit the CIF calculations. Added to `_CP_OBSOLETE_KEYS` to purge from the DB.
- Added `Inflation` (default 0.05) and `Buffer` (default 0.0) to the control panel, both visible and editable in Jarvis.
- Added **Ocean Cost Method** dropdown above the Drayage table in Jarvis. On change, fetches computed ocean freight per drayage region using the selected method (Lowest / Avg Cheapest 2 / Avg Cheapest 3) and updates the OceanBase inputs. The Export view's dropdown also updates drayage OceanBase in the DB.
- New server endpoint `GET /api/ocean-base-by-method?method=...` computes OceanBase per port from ocean rates data.
- Fixed control panel API to properly handle `Ocean Cost Method` as a string value.
