# Contract: Operator Dashboard UI

**Assets**: `web/static/index.html`, `dashboard.css`, `dashboard.js`  
**Consumers**: Field operators, bench testers (browser)

## Layout regions (minimum)

| Region | Content |
|--------|---------|
| Header | App title, connection indicator (online/offline), version from `/meta` |
| Status card | `running`, COM, baud, UDP, NMEA mode; Hz net→COM, Hz COM→net; drops, rejects |
| Run controls | **Start** (primary), **Stop** (secondary), disabled while command in flight |
| Config summary | From `/config` (read-only display) |
| Discovery | **Refresh** button; device list (serial + network); **select** row → PATCH |
| Tools | **Unlock ports**; token field (visible only if `/meta.token_required`) |

## Visual states

| State | Behavior |
|-------|----------|
| Online | Green/neutral indicator; status numbers live |
| Offline | Banner "Backend offline"; no fake zeros |
| Scanning | Spinner or "Scanning…" on discovery panel; list may be stale until update |
| Error | Inline alert with API `message` (start validation, 409, unlock fail) |

## Responsive rules (SC-103)

- **360px** min width: single column; buttons full-width; tap targets ≥ 44px height
- **≥ 768px**: status + run controls side-by-side where space allows
- No horizontal scroll for primary controls at 360px and 1920px

## CSS contract

- All rules in **`dashboard.css`** (vendored)
- No `@import` from external URLs
- Contrast: status text readable on dark/light (match survey bridge dark theme preference)

## JS contract

- No frameworks (vanilla ES6)
- `fetch` + `JSON`; `Content-Type: application/json` on PATCH/POST bodies
- `localStorage` key: `nmea-bridge-web-token` (document in OPERATOR_GUIDE)
- On load: read token from storage if `token_required`

## Layout 2.0 Phase A (v1.9.64+)

- Default panel order includes **map** after Survey monitor.
- Desktop: COM + Survey monitor + map open by default; Configuration, Tools, Discovery, Log collapsed.
- Map panel: `grid-column: span 2` when open (≥992px); Leaflet `invalidateSize` on open/resize.
- `run-alert`: auto-hide ~6s; cleared when `/status.running` conflicts with message text.
- Discovery **Serial ports** section hidden ≥992px (COM & ports is canonical).

See `plan-layout-2.0.md` for optional Phase B (ops band + two-column shell).

## Out of scope (UI)

- NTRIP, fan-out, TCP advanced editors
- HUD, themes, UI editor
- NMEA sentence display or hex tap
