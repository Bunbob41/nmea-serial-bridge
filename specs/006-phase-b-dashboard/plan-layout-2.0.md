# Plan: Web dashboard Layout 2.0 (PC-first)

**Status:** Phase A shipped (v1.9.64); Phase B optional  
**Baseline:** `web/static/layouts/1.0/` (frozen 2026-05-24)  
**Scope:** HTML/CSS/JS only — no API or bridge changes required for phase A.

---

## Screenshot review (what you showed)

| Observation | Severity | Notes |
|-------------|----------|--------|
| Large empty regions on wide PC | High | 3-column grid + mostly **collapsed** panels → accordion strip + dead space (v1.9.53-style). |
| Map floating / overlapping | High | Map in small column cell without `grid-row` span; Leaflet init before panel sized → overlap (v1.9.62). |
| **COM list twice** | Medium | **COM & ports** + **Discovery → Serial ports** duplicate; Discovery already hints “use COM & ports on phone.” |
| **“Bridge stopped”** under **Running** | Medium | `run-alert` keeps last stop message; header chip shows Running — confusing. |
| QR / token block dominates when Tools open | Medium | Setup-time UI competes with run-time monitor on PC. |
| Survey monitor buried | Medium | GNSS/backpressure inside nested accordions; red GNSS tone only on header strip. |
| Reorder ▲▼ on every panel | Low | Useful on phone; noisy on PC — consider hide on `min-width: 1200px` or “Edit layout” mode. |
| Good parts to keep | — | Header chip, panel summaries, GNSS color on Survey monitor, log expand mode, map toggle + coords. |

**Data note (not layout):** “Simulation · 0 sats · HDOP 328” is a **GGA/simulator** issue, not a UI bug — still worth a **compact alert** in the ops row so it’s visible without opening Session transport.

---

## Layout 2.0 goals

1. **PC (≥1200px):** One glance — run state, Hz, GNSS health, position (map or coords), COM — without opening five accordions.
2. **Phone:** Keep single column, large taps, COM + Start/Stop first (unchanged priority).
3. **No regression:** Vendored CSS, no CDN, `/status` polling, panel order persistence (upgrade schema).
4. **HUD later:** Ops row fields mirror future `navigation_position()` / GNSS chip — no Qt embed in 2.0.

---

## Proposed information architecture

### Tier A — Always visible (desktop)

Fixed **operations band** below header (not collapsible):

| Zone | Content |
|------|---------|
| Run | Start / Stop (smaller than today on PC) |
| Link | COM, baud, UDP bind, NMEA mode, transport OK/warn |
| Rates | Hz net→COM, COM→net, inject |
| GNSS | Fix summary, sats, HDOP — **single** strip (POSPac-style), color-coded |
| Position | Lat/lon mono + optional mini “map on” indicator |

### Tier B — Two-column workspace (desktop)

```text
┌─────────────────────────────────────────────────────────────┐
│ Header + run-alert (ephemeral toasts, not persistent “stopped”)│
├──────────────────────────────┬──────────────────────────────┤
│  LEFT (~58%)                 │  RIGHT (~42%)                │
│  Position map (when enabled) │  Survey monitor (flat grid)  │
│  or Live log (tab)           │  Backpressure + line counts  │
├──────────────────────────────┴──────────────────────────────┤
│  Setup row (collapsed by default): COM | Config | Tools | Discovery │
└─────────────────────────────────────────────────────────────┘
```

- **Map + log:** Tab or toggle — “Map | Log” — not both fighting for height.
- **Survey monitor:** Drop inner accordions on desktop; show 2×3 stat grid always.
- **Setup row:** Accordion **“Setup & discovery”** containing COM, Configuration, Tools (QR collapsed by default), Discovery (serial list **hidden on desktop** — network adapters only).

### Tier C — Mobile

Keep current panel order defaults; open COM + Survey monitor only; map optional; log collapsed.

---

## Concrete changes (phased)

### Phase A — Quick wins (S, no speckit blockers)

| # | Change | Files |
|---|--------|-------|
| A1 | Add `map` to `DASHBOARD_PANEL_DEFAULT_ORDER`; desktop default open map when coords valid | `dashboard.js` |
| A2 | **Auto-hide** `run-alert` after N s when state matches (running + “stopped” msg) | `dashboard.js` |
| A3 | Map: `invalidateSize()` on panel open + `ResizeObserver` on `#map-frame` | `dashboard.js` |
| A4 | CSS: `.map-card.dashboard-panel-open .bridge-map { min-height: 360px }`; `grid-column: span 2` on wide | `dashboard.css` |
| A5 | Hide Discovery serial list on `@media (min-width: 992px)` | `index.html` / CSS |
| A6 | Desktop: default **collapsed** Tools + Discovery; expanded Survey + COM | `dashboard.js` defaults |

### Phase B — Layout 2.0 shell (M)

| # | Change | Files |
|---|--------|-------|
| B1 | New wrapper `#dashboard-ops` band in HTML | `index.html` |
| B2 | CSS grid `dashboard--layout-2` with areas | `dashboard.css` |
| B3 | Mirror `/status` into ops band (duplicate ids or `data-bind` helpers) | `dashboard.js` |
| B4 | Map \| Log segmented control | `index.html`, `dashboard.js` |
| B5 | Flatten monitor sections on desktop (class `monitor-wrap--flat`) | CSS + JS |
| B6 | QR: collapsed `<details>` “Phone setup (QR)” inside Tools | `index.html` |

### Phase C — Polish (S, optional)

| # | Change |
|---|--------|
| C1 | Preset layouts: **Field**, **Bench**, **Phone** buttons (overwrite order + collapse in localStorage) |
| C2 | “Reset layout to default” |
| C3 | Screenshot / visual regression checklist in quickstart |

---

## localStorage migration

| Key | 2.0 behavior |
|-----|----------------|
| `nmea-dashboard-order` | Bump to v2 default: `com-setup`, `status`, `map`, `log`, `configuration`, `tools`, `discovery` |
| `nmea-dashboard-panels` | New desktop collapse defaults |
| `nmea-bridge-map-enabled` | Unchanged |
| New: `nmea-dashboard-layout` | `"1"` \| `"2"` — optional feature flag to A/B |

On first load with layout=2, merge old order arrays to include `map`.

---

## Speckit: do we need it?

| Work | Speckit? |
|------|----------|
| Phase A quick wins | **No** — extend `contracts/dashboard-ui.md` + CHANGELOG |
| Phase B Layout 2.0 shell | **Light** — add `contracts/dashboard-layout-2.0.md` (regions, breakpoints, states); optional `tasks-layout-2.0.md` |
| Preset layouts + role modes + HUD embed | **Yes** — new spec slice `007-dashboard-layout-presets` or US in 006 |

**Recommendation:** Proceed with **Phase A without speckit**; run **speckit clarify** only if you want signed-off desktop wireframe (ops band + 2-column) before Phase B.

---

## Success criteria (acceptance)

1. At 1920×1080, operator sees Running, Hz, GNSS, COM **without scrolling** and without opening panels.
2. Map open does not overlap other cards; resize stable after toggle.
3. No contradictory “Bridge stopped” while Running (unless stop just failed).
4. COM port list appears **once** on desktop.
5. Phone 360px: still usable, no horizontal scroll on Start/Stop.
6. Layout 1.0 restorable from `web/static/layouts/1.0/`.

---

## Out of scope (2.0)

- Qt Survey HUD map (reserved API already exists).
- Changing `/status` fields.
- OpenFreeMap vector tiles (OSM raster is fine for v1).
- NMEA parsing in browser.

---

## Suggested order of work

1. Freeze 1.0 ✅ (`web/static/layouts/1.0/`)  
2. Phase A (1–2 sessions)  
3. Review with your screenshots again  
4. Phase B if approved  
5. Update `docs/OPERATOR_GUIDE.md` with “PC dashboard layout” screenshot
