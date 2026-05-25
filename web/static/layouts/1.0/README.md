# Dashboard Layout 1.0 (frozen backup)

**Date:** 2026-05-24  
**App version at snapshot:** 1.9.63 (map panel present; panel order key may omit `map` in JS default list)

These files are a **read-only reference** of the operator web dashboard before Layout 2.0 work. The live UI continues to load from:

- `web/static/index.html`
- `web/static/dashboard.css`
- `web/static/dashboard.js`

Do not import this folder from the app. To restore 1.0 manually, copy these three files back to `web/static/` (and revert any Layout 2.0-only assets).

**Live restore:** v1.9.71 copied this snapshot back to `web/static/` (2026-05-25).

## What 1.0 includes

- Collapsible panels with ▲▼ reorder (`localStorage` `nmea-dashboard-order`)
- Panels: COM & ports, Survey monitor, Position map, Configuration, Tools (token/QR), Live log, Discovery
- 1-col mobile / 2-col tablet / 3-col desktop CSS grid
- Header: Start/Stop, status chip, connection dot

## Known issues (motivation for 2.0)

See `specs/006-phase-b-dashboard/plan-layout-2.0.md`.
