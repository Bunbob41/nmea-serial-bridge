# Implementation Plan: Phase B Operator Dashboard

**Branch**: `2033-phase-b-dashboard` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Static HTML dashboard at `GET /`, vendored CSS, poll `/status`, Start/Stop, unlock, async discovery + COM picker; new routes `/meta`, `/discovery`, `/ports/unlock`, `/discovery/refresh`; service index → `/api`.

**Builds on**: [`specs/005-hybrid-ui-webui/`](../005-hybrid-ui-webui/) (v1.7.2+ REST + `BridgeAppFacade` + uvicorn thread).

## Summary

Ship an **operator dashboard** (`web/static/`) served by FastAPI at **`GET /`**, using existing 005 endpoints for status/config/start/stop and **four new API routes** wired through `BridgeAppFacade` to Qt main-thread hub/discovery/unlock handlers. No new Python UI framework; no bridge protocol in the browser. Target **1.8.0**.

## Technical Context

**Language/Version**: Python 3.10+ (existing); vanilla ES6 in `dashboard.js`  
**Primary Dependencies**: Existing `fastapi`, `uvicorn` (`requirements-web.txt`); PySide6 unchanged; **no new mandatory pip packages**  
**Storage**: `web/static/*`; PyInstaller `datas` for `web/static`; browser `localStorage` for token only  
**Testing**: `test_web_api.py`, `test_app_facade.py`, static route smoke; extend `bench_web_api.py`; `verify_all.py`  
**Target Platform**: Windows 10+ desktop host; dashboard in browser (loopback, LAN, Tailscale)  
**Project Type**: Desktop bridge + embedded HTTP control plane + static web client  
**Performance Goals**: Status poll 1 Hz; discovery poll ≤ 2 Hz during 15 s scan window; dashboard first paint &lt; 500 ms on localhost (SC-101/SC-103)  
**Constraints**: HTTP thread MUST NOT touch Qt; vendored CSS only (no CDN); desktop Start/Stop unchanged (FR-302 constitution); 005 stop-first / token rules preserved  
**Scale/Scope**: ~6 touched modules + 3 static files; 4 new REST routes; façade methods; no `bridge_core.py` changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Dashboard/JS + `web_api` only; unlock/discovery delegate to mixin | ✅ | ✅ |
| II. Survey Operator Trust | Desktop Start/Stop primary; dashboard additive; clear offline/errors | ✅ | ✅ |
| III. Verifiable Changes | API + static + façade tests; verify_all | ✅ | ✅ |
| IV. Version & Release | 1.8.0 + CHANGELOG + sync_version_info + static datas | ✅ | ✅ |
| V. Resilience | 1 s status poll; command disable during fetch; no unbounded discovery poll (15 s cap) | ✅ | ✅ |

**Gate result**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/006-phase-b-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── web-api-extensions.md
│   └── dashboard-ui.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
web/
└── static/
    ├── index.html       # Dashboard shell
    ├── dashboard.css    # Vendored responsive styles (offline-safe)
    └── dashboard.js     # Poll status, commands, discovery, token/meta

web_api.py               # EXTEND — StaticFiles, /, /api, /meta, /discovery, unlock, refresh
app_facade.py            # EXTEND — discovery cache, request_unlock, request_refresh, get_discovery
ui/mixin.py              # EXTEND — publish discovery snapshot to façade (optional hook)

nmea_serial_bridge.spec  # EXTEND — datas: web/static
docs/OPERATOR_GUIDE.md   # Dashboard, LAN, token, Tailscale

test_web_api.py          # New routes + GET / HTML
test_app_facade.py       # Unlock/refresh/discovery delegation
bench_web_api.py         # Optional dashboard smoke notes
```

**Structure Decision**: Single-repo; static assets colocated under `web/static/`; reuse 005 `WebServerThread` and `create_app()` factory pattern.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |

## Implementation Phases

### Phase A — API extensions + façade (blocking)

- Add `GET /meta` from `load_web_ui_prefs()` + version (no Qt).
- Add `GET /discovery` reading thread-safe cached `DiscoverySnapshot` JSON (updated on main thread when hub snapshot changes).
- Add `POST /discovery/refresh` → `facade.request_refresh_discovery()` → `mixin._on_hub_refresh_discovery()`.
- Add `POST /ports/unlock` → `facade.request_unlock_ports()` → extract unlock result from `smart_release_com` + hints (return `WebCommandResult`, avoid blocking QMessageBox on API path).
- Move service index from `GET /` to `GET /api`.
- Extend OpenAPI models in `web_api.py` for new responses.

### Phase B — Static dashboard P1 (US1 + US2)

- `web/static/index.html` + `dashboard.css` + `dashboard.js`.
- Mount `StaticFiles` at `/` or explicit `GET /` → `index.html`.
- Poll `GET /status` 1000 ms; offline banner on fetch failure.
- Start/Stop buttons; disable during command; show API error body.
- Load `GET /meta` on init; token field + `localStorage` when `token_required`.
- Display `GET /config` summary strip.

### Phase C — Discovery + COM picker (US4)

- Refresh button → `POST /discovery/refresh` then poll `GET /discovery` every 500 ms up to 15 s.
- Render serial + network lists; select → `PATCH /config` with `com_port` / `hub_device_id`.
- Handle 409 running_guard when bridge running.

### Phase D — Unlock UI (US3)

- Unlock button → `POST /ports/unlock`; inline alert with message.

### Phase E — Docs, packaging, release

- PyInstaller `datas` for `web/static`.
- `OPERATOR_GUIDE.md` § dashboard, LAN, Tailscale, token.
- Bump **1.8.0**; `verify_all.py`; update `specs/005-hybrid-ui-webui/contracts/control-parity.md` Phase B rows to MVP for implemented controls.

## Test Plan

| Area | Command / artifact |
|------|-------------------|
| API | `python -m unittest test_web_api test_app_facade -v` |
| Static | TestClient `GET /` returns `text/html` |
| Bench | `bench_web_api.py` + manual dashboard SC-102 (10× start/stop) |
| Full gate | `python verify_all.py` |
| Offline CSS | Open dashboard with network disabled; layout usable (SC-103) |

## Post-Design Constitution Re-check

All principles satisfied: no bridge I/O in web layer; desktop remains authoritative; tests and version bump planned; polling bounded.
