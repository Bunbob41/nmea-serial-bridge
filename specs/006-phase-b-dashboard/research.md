# Research: Phase B Operator Dashboard

**Feature**: `specs/006-phase-b-dashboard`  
**Date**: 2026-05-22

## R1 — Static dashboard delivery

**Decision**: `web/static/` with `index.html`, `dashboard.css`, `dashboard.js`; FastAPI `StaticFiles` + explicit `GET /` for `index.html`; service index at `GET /api`.

**Rationale**:
- Matches clarifications: no NiceGUI, no runtime CDN.
- Smallest diff on 005 stack; OpenAPI remains at `/docs`.
- PyInstaller `datas` pattern same as `ui/resources/`.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| NiceGUI | Blocks Qt risk; heavy deps (005 R5) |
| Jinja2 server-rendered | Extra template layer; static is enough |
| Keep JSON at `/` | Blocks operator dashboard at root (FR-101) |

---

## R2 — Styling (vendored CSS)

**Decision**: Hand-authored **`dashboard.css`** — flex/grid, touch targets ≥ 44px, status dot, card layout for telemetry; no Tailwind CDN.

**Rationale**: Clarification **B** — field PCs offline; frozen bundle must work air-gapped.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| Tailwind CDN only | Offline broken |
| CDN + fallback | Clarification chose vendored-only path |

---

## R3 — Discovery refresh (async + poll)

**Decision**: `POST /discovery/refresh` returns immediately after queueing `mixin._on_hub_refresh_discovery()`; dashboard polls `GET /discovery` every **500 ms** for up to **15 s**; UI shows `scanning` while `scan_busy` or snapshot `mono_ts` unchanged.

**Rationale**:
- Desktop already uses `DiscoveryScanWorker` async (mixin).
- Avoids HTTP blocking on ARP/UDP probe budget.
- Clarification **A**.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| Synchronous POST until scan done | Risk 20 s HTTP timeout; blocks worker thread perception |
| GET-only discovery | No forced rescan (US4) |

---

## R4 — Discovery snapshot on API

**Decision**: `BridgeAppFacade` holds a lock-protected **`WebDiscoveryPayload`** copy updated whenever hub `set_snapshot()` runs (hook from mixin after `_poll_discovery_snapshot` / worker completion).

**Rationale**:
- `GET /discovery` must not read Qt from HTTP thread.
- Reuses `discovery_service.DiscoverySnapshot` → JSON DTO.

**Alternatives considered**:
| Alternative | Rejected because |
|-------------|------------------|
| `_invoke_read_on_main` per GET | Extra main-thread latency at 2 Hz poll |
| Re-run `build_snapshot()` on HTTP thread | Duplicates work; may touch serial APIs off main inconsistently |

---

## R5 — Unlock via API

**Decision**: `request_unlock_ports()` on main thread calls same logic as `_on_hub_unlock_ports` but returns **`WebCommandResult`** with `smart_release_com` message; skip `QMessageBox` for API; still `refresh_ports()` + optional discovery refresh.

**Rationale**: Parity with desktop; API needs machine-readable message for dashboard alert.

---

## R6 — Token and meta

**Decision**: `GET /meta` → `{ version, lan_bind, token_required }` from prefs (no secret); dashboard shows token input when `token_required`; `localStorage` key `nmea-bridge-token`.

**Rationale**: Clarifications **A** + **D**; localhost users not prompted unnecessarily.

---

## R7 — COM / device selection

**Decision**: Dashboard lists `serial_devices` and `network_cards` from discovery; on select, `PATCH /config` with `com_port` and/or `hub_device_id` (mirror desktop hub card selection).

**Rationale**: Clarification **full US4**; reuses 005 `apply_config` hub path.

---

## R8 — Threading (005 carry-forward)

**Decision**: Continue **`_dispatch_command`** signal for mutating façade methods; **`_dispatch_read`** for `get_config`; discovery cache written only on Qt main thread.

**Rationale**: 1.7.1 fix proved `QTimer.singleShot` from uvicorn is unsafe; 1.7.2 fixed config read.
