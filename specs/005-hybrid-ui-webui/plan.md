# Implementation Plan: Hybrid UI — Qt Visual Layouts + WebUI Bridge

**Branch**: `2032-hybrid-ui-webui` | **Date**: 2026-05-21 | **Spec**: [spec.md](./spec.md)

**Input**: Layer 1 — `.ui` runtime load for Standard/Field shells; Layer 2 — background Web API (`/status`, `/config`, start/stop); WebUI as non-blocking Qt peer with phased full parity.

**Builds on**: v1.6.0 ([`specs/004-hub-network-discovery/`](../004-hub-network-discovery/)) — Connection Hub, discovery, QoS.

## Summary

Introduce two parallel UI layers without moving bridge I/O out of `bridge_core.py`:

1. **`ui/ui_loader.py` + `ui/resources/*.ui`** — `QUiLoader` loads Designer layouts for Standard Connect chrome and Field control strip; Python keeps signal wiring, hub embedding, and programmatic fallbacks.
2. **`app_facade.py` + `web_api.py` + `web_server.py`** — thread-safe façade over `BridgeLogicMixin` state; **FastAPI** on a **daemon thread** (uvicorn) exposes REST; writes marshal to Qt main via `QMetaObject.invokeMethod` / queued slots; reads use a coalesced snapshot dict (no Qt calls from HTTP thread).
3. **`contracts/control-parity.md`** — MVP vs Phase B matrix; NiceGUI dashboard deferred to Phase B (static `/` + OpenAPI for MVP).

Target version **1.7.0** (minor — new control plane + layout architecture).

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: PySide6 (existing); **new optional**: `fastapi>=0.110`, `uvicorn[standard]>=0.27` in `requirements-web.txt` (bundled when Web enabled in frozen build)  
**Storage**: Extend `ui_prefs.json` — `web_ui.enabled`, `web_ui.host`, `web_ui.port`, `web_ui.lan_bind`, `web_ui.token`  
**Testing**: `test_ui_loader.py`, `test_web_api.py` (FastAPI TestClient, no live port), `test_app_facade.py`; extend `bench_gui_smoke.py`; `tools/run_unittests.py`; `verify_all.py`  
**Target Platform**: Windows 10+ desktop + loopback HTTP (optional LAN bind)  
**Project Type**: Desktop bridge + embedded local control plane  
**Performance Goals**: Status GET p95 &lt; 50 ms from snapshot; Web poll 5 Hz must not raise Qt resize p95 above 100 ms (SC-203); config/start/stop round-trip &lt; 2 s to reflect on desktop  
**Constraints**: HTTP thread MUST NOT call Qt widgets; bridge asyncio loop unchanged; FR-302 Start/Stop on `run` panel preserved; Connect `run`/`connection` sections remain required  
**Scale/Scope**: ~8 new modules + 2–4 `.ui` files; refactor `ui/standard.py` / `ui/field.py` shells only (not Minimal/Log-first/HUD)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Web/facade in `app_facade.py` / `web_*.py`; no socket/NMEA in UI | ✅ | ✅ |
| II. Survey Operator Trust | Start/Stop stays on `run` panel; Web is additive peer | ✅ | ✅ |
| III. Verifiable Changes | API contract tests + loader tests + verify_all | ✅ | ✅ |
| IV. Version & Release | 1.7.0 + CHANGELOG + `sync_version_info` + spec `datas` for `.ui` | ✅ | ✅ |
| V. Resilience | Snapshot coalesce ≥ 500 ms; command queue serializes start/stop | ✅ | ✅ |

**Gate result**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/005-hybrid-ui-webui/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── web-api.md
│   ├── qt-ui-loader.md
│   └── control-parity.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
app_facade.py               # NEW — thread-safe status snapshot + command queue API (no Qt in HTTP handlers)
web_api.py                  # NEW — FastAPI routes (/status, /config, /bridge/start|stop)
web_server.py               # NEW — uvicorn thread lifecycle (start/stop/join on app exit)

ui/
├── ui_loader.py            # NEW — resolve .ui paths (dev + _MEIPASS), QUiLoader, fallback flag
├── resources/
│   ├── standard_connect_shell.ui
│   └── field_control_strip.ui
├── standard.py             # REFACTOR — load shell .ui, wire existing widgets into named slots
├── field.py                # REFACTOR — load strip .ui container
└── mixin.py                # EXTEND — register facade, publish snapshot on stats tick, apply web config

requirements-web.txt        # NEW — fastapi, uvicorn (optional install)
nmea_serial_bridge.spec     # EXTEND — datas: ui/resources/*.ui; hiddenimports for web stack if enabled

test_ui_loader.py
test_web_api.py
test_app_facade.py
bench_web_api.py            # NEW — curl-friendly smoke script (optional in verify_all waiver)
```

**Structure Decision**: Single-repo desktop app; Web stack is optional pip extra but first-class in plan. No separate `backend/` tree — keeps PyInstaller and `bridge_gui.py` entry simple.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New mandatory-class deps (FastAPI/uvicorn) when Web enabled | REST + OpenAPI + TestClient for FR-203/303 | `http.server` lacks typed contracts, harder to test; raw sockets unmaintainable |
| Second long-lived thread (HTTP) besides bridge asyncio | FR-205 non-blocking peer | Running uvicorn on Qt main thread would freeze UI during requests |

## Implementation Phases

### Phase A — UI loader + Standard shell migration (P1 Layer 1)

- Add `ui/ui_loader.py`: `load_ui(name) -> QWidget`, paths `ui/resources/{name}.ui`, frozen via `sys._MEIPASS/ui/resources`.
- Author `standard_connect_shell.ui` in Qt Designer: top-level `QWidget` with named children: `connectPanelHost`, `statusBannerHost`, `subtitleLabel` (or promote widgets).
- Refactor `BridgeWindowStandard.__init__`: load shell; `create_connection_controls` unchanged; embed hub into `connectPanelHost`; map `status_banner` to host or keep programmatic banner with object name match.
- Fallback: on load failure, log + call legacy `_build_standard_shell_programmatic()` kept in `standard.py` for one release.
- `test_ui_loader.py`: valid fixture .ui loads; missing file raises `LayoutLoadError`.

### Phase B — Field strip migration (P1 Layer 1)

- `field_control_strip.ui` for bottom strip layout (COM row, Refresh/Unlock, status).
- Wire Field widgets into loaded layout; preserve splitter prefs.
- Visual regression checklist SC-102 (900×380 Standard, 720×480 Field).

### Phase C — App façade + snapshot (P1 Layer 2 core)

- `BridgeAppFacade` holds `weakref` to window/mixin; `update_snapshot(**fields)` called from mixin stats timer (coalesced 500 ms).
- `get_status() -> WebSessionState`, `get_config() -> WebConfigPayload` read snapshot under `threading.Lock`.
- `request_start()` / `request_stop()` / `apply_config(patch)` enqueue to Qt main (`QTimer.singleShot(0, ...)` → `_validate_before_start`, `start_bridge`, `stop_bridge`).
- Serialize concurrent commands with `threading.Lock` + “busy” response if start already in flight.

### Phase D — Web server + API (P1 Layer 2 surface)

- `web_api.py`: FastAPI app factory `create_app(facade)`.
  - `GET /status` → JSON status
  - `GET /config` / `PATCH /config` → read/write core fields
  - `POST /bridge/start` / `POST /bridge/stop` → command results
  - `GET /health` → `{"ok": true}`
- Optional `X-Bridge-Token` when `lan_bind` + token set.
- `web_server.py`: start uvicorn on `127.0.0.1:8765` default; daemon thread; `stop_web_server()` in `closeEvent`.
- Tools → **Web control** checkbox + port (or Advanced in connect manual override) persisting `ui_prefs`.
- `test_web_api.py`: TestClient against facade mock (no Qt event loop required for read paths).

### Phase E — Parity matrix + docs + polish (P2/P3)

- Fill `contracts/control-parity.md` with all Connect controls (MVP / Phase B / N/A).
- `docs/OPERATOR_GUIDE.md` § Web control plane (localhost default, LAN + firewall, token).
- `quickstart.md` curl recipes; `bench_web_api.py` for 10-iteration start/stop loop (SC-202).
- Phase B (deferred in tasks): NiceGUI single-page dashboard importing same REST; NTRIP/fan-out read-only in API.

### Phase F — Packaging (release)

- `nmea_serial_bridge.spec`: add `ui/resources` to `datas`; conditional collect for fastapi/uvicorn.
- Bump **1.7.0**; run `release.ps1` after implement.

## Test Plan

| Area | Command / artifact |
|------|-------------------|
| Loader | `python -m unittest test_ui_loader -v` |
| Web API | `python -m unittest test_web_api test_app_facade -v` |
| Regression | `python tools/run_unittests.py` |
| Full gate | `python verify_all.py` |
| Thread smoke | 60 s × 5 Hz `GET /status` while manually resizing (SC-203 checklist) |
| Parity | Review `contracts/control-parity.md` vs UI |

## Post-Design Constitution Re-check

All principles remain satisfied: bridge I/O untouched; Web commands are thin delegates; version/docs called out; snapshot coalescing satisfies Principle V.
