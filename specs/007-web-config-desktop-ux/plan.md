# Implementation Plan: Web Config Editor & Desktop UX Fixes

**Branch**: `007-web-config-desktop-ux` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Editable web dashboard config (COM, network mode, host/port); QR token for remote devices; Field Guide clipping fix; Standard COM dropdown + Connect splitter resize.

**Builds on**: [006-phase-b-dashboard](../006-phase-b-dashboard/) (v1.8.4 dashboard); [005-hybrid-ui-webui](../005-hybrid-ui-webui/) (`PATCH /config`, façade).

## Summary

Extend **`web/static/`** with an editable configuration form (replaces read-only summary) wired to existing **`PATCH /config`**, extend **`app_facade._apply_config_on_main`** for **`network_mode`** (+ remote host/port fields), add **`GET /token-qr`** (SVG, offline-safe pure-Python) for token handoff, fix **Field Guide** layout (scroll + form row heights), harden **`refresh_ports`** COM selection, and verify **Standard Connect** vertical splitter (`connect_panels.py`) remains draggable with persisted sizes.

Target **1.9.0**.

## Technical Context

**Language/Version**: Python 3.10+; vanilla ES6 in `dashboard.js`  
**Primary Dependencies**: Existing `fastapi`, `uvicorn`, PySide6; **no new mandatory pip packages** (QR via inline SVG generator in `web/qr_svg.py`)  
**Storage**: `web/static/*`; `ui_prefs.json` (`web_ui.token`); `connect_panel` prefs for splitter sizes  
**Testing**: `test_web_api.py`, `test_app_facade.py` (network_mode patch), `test_ui_prefs.py` if touched; manual Field/Standard visual checks  
**Target Platform**: Windows 10+; browser + Qt desktop  
**Performance Goals**: Config save &lt; 2 s; QR render &lt; 200 ms; no extra status-poll load  
**Constraints**: Constitution I/II/V; running_guard on config writes; vendored/offline QR (no CDN); no `bridge_core.py` changes  
**Scale/Scope**: ~8 modules; 1 small new helper `web/qr_svg.py`; façade network_mode; dashboard form; 3 desktop UX fixes

## Constitution Check

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Web + façade only; no protocol in JS | ✅ | ✅ |
| II. Survey Operator Trust | Running guard; desktop Start/Stop unchanged | ✅ | ✅ |
| III. Verifiable Changes | API + façade tests; verify_all | ✅ | ✅ |
| IV. Version & Release | 1.9.0 + CHANGELOG + sync_version_info | ✅ | ✅ |
| V. Resilience | Form disable while running; command-in-flight unchanged | ✅ | ✅ |

**Gate result**: ✅ PASS

## Project Structure

### Documentation

```text
specs/007-web-config-desktop-ux/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── dashboard-config-ui.md
│   └── desktop-ux-fixes.md
└── tasks.md
```

### Source Code

```text
web/static/index.html, dashboard.css, dashboard.js   # Editable config + QR checkbox
web/qr_svg.py                                        # Pure-Python QR → SVG (token payload)
web_api.py                                           # GET /token-qr; optional meta hints
app_facade.py                                        # network_mode + remote host/port in apply_config
ui/tool_tabs.py                                      # Guide scroll area; form layout fix
ui/mixin.py                                          # refresh_ports preserve selection
ui/connect_panels.py                                 # Splitter handle / resize verify (if bug found)
ui/standard.py                                       # COM row min heights (if needed)
test_web_api.py, test_app_facade.py
docs/OPERATOR_GUIDE.md
specs/005-hybrid-ui-webui/contracts/control-parity.md
```

## Implementation Phases

### Phase A — Façade network_mode (blocking for US1)

- Implement `network_mode` in `_apply_config_on_main`: toggle advanced net + radio buttons (`udp_listen`, `udp_remote`, `tcp_client`, `tcp_server`).
- Map `remote_host` / `remote_port` via existing widgets when mode requires.

### Phase B — Dashboard editable config (US1)

- Replace read-only config card with form: COM `<select>`, baud, mode, conditional host/port fields.
- Load from `GET /config` + `GET /discovery` for COM options; disable when `status.running`.
- Save button → `PATCH /config`; inline errors.

### Phase C — Token QR (US2)

- `web/qr_svg.py` + `GET /token-qr` (SVG, token from `load_web_ui_prefs`, 404 if no token).
- Dashboard checkbox shows `<img src="/token-qr">` + plain text from localStorage sync.

### Phase D — Desktop UX (US3–US5)

- **US3**: Wrap `build_guide_tab` body in `QScrollArea`; `QFormLayout` vertical spacing; `web_box` minimum height.
- **US4**: `refresh_ports` preserve current selection; `setInsertPolicy(NoInsert)`; ensure post-refresh reselect.
- **US5**: Audit `_connect_panel_splitter` — ensure handles visible, `setChildrenCollapsible(False)`, `reset_sizes` wired.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
