# Dashboard Layout 1.0 (frozen backup)

**Date:** 2026-05-24 (refreshed **2026-05-24** for v1.10.0)  
**App version at snapshot:** 1.10.0

These files are a **read-only reference** of the operator web dashboard **before** the GridStack beta experiment. The live UI continues to load from:

- `web/static/index.html`
- `web/static/dashboard.css`
- `web/static/dashboard.js`

Do not import this folder from the app. To restore 1.0 manually, copy these three files back to `web/static/`.

## What 1.0 includes

- Collapsible panels with ▲▼ reorder (`localStorage` `nmea-dashboard-order`)
- Panels: COM & ports, Survey monitor, Position map, Configuration, Tools (token/QR), Live log, Discovery
- Responsive CSS grid (1/2/3 columns by width)
- Header: Start/Stop, status chip, connection dot

## GridStack beta

Drag-and-resize trial lives at `web/static/layouts/gridstack/` — same API, separate layout storage.
