# Tasks: Hybrid UI — Qt Visual Layouts + WebUI Bridge

**Input**: `specs/005-hybrid-ui-webui/plan.md`, `spec.md`, `contracts/`, `data-model.md`, `research.md`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, v1.6.0 shipped (004)

**Tests**: Constitution Principle III — `test_*.py` + `verify_all.py` in polish phase.

## Format: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

**Purpose**: Optional Web deps, resource dirs, test fixtures, skeleton modules

- [x] T001 Create `requirements-web.txt` with `fastapi>=0.110` and `uvicorn[standard]>=0.27` per `research.md`
- [x] T002 [P] Create `ui/resources/` directory and document Designer workflow in `specs/005-hybrid-ui-webui/quickstart.md` (Phase A note if missing)
- [x] T003 [P] Add `tests/fixtures/minimal_shell.ui` with `connectPanelHost` object name for loader tests
- [x] T004 [P] Add `test_ui_loader.py`, `test_app_facade.py`, and `test_web_api.py` import skeletons
- [x] T005 [P] Add `app_facade.py`, `web_api.py`, and `web_server.py` module stubs (docstrings + `LayoutLoadError` placeholder only in `ui/ui_loader.py`)

---

## Phase 2: Foundational (Blocking)

**Purpose**: UI loader + thread-safe façade + prefs — required before Web user stories; loader required before US1

**⚠️ CRITICAL**: Complete T006–T012 before User Story 2+; complete T006–T007 before User Story 1 implementation

- [x] T006 Implement `ui/ui_loader.py` (`resource_dir`, `load_widget`, `LayoutLoadError`) per `contracts/qt-ui-loader.md`
- [x] T007 [P] Implement `WebSessionState`, `WebConfigPayload`, `WebCommandResult` dataclasses in `app_facade.py` per `data-model.md`
- [x] T008 Implement `BridgeAppFacade` snapshot lock, `get_status()`, `get_config()`, and command enqueue stubs in `app_facade.py`
- [x] T009 Add `load_web_ui_prefs()` / `save_web_ui_prefs()` for `WebUiPrefs` in `ui/ui_prefs.py`
- [x] T010 Wire mixin stats path to `facade.update_snapshot()` with 500 ms coalesce in `ui/mixin.py`
- [x] T011 Register `BridgeAppFacade` on window init in `bridge_gui.py` or `ui/mixin.py` `_init_bridge_state()`
- [x] T012 [P] Complete `test_app_facade.py` — snapshot read/write thread safety and empty defaults

**Checkpoint**: `python -m unittest test_app_facade test_ui_loader -v` passes (loader tests may use fixture only until US1 `.ui` land)

---

## Phase 3: User Story 1 — Visual layout edit without code rebuild (P1) 🎯 MVP

**Goal**: Standard and Field shells load from `.ui` at runtime; programmatic fallback on failure

**Independent Test**: Edit label in `standard_connect_shell.ui`, restart app — change visible; Start/Stop work (`quickstart.md` Phase A, SC-101)

- [x] T013 [P] [US1] Author `ui/resources/standard_connect_shell.ui` with `connectPanelHost`, `statusBannerHost`, `appSubtitle` per `contracts/qt-ui-loader.md`
- [x] T014 [P] [US1] Author `ui/resources/field_control_strip.ui` with `fieldStripHost`, `fieldStatusHost` per `contracts/qt-ui-loader.md`
- [x] T015 [US1] Refactor `BridgeWindowStandard` in `ui/standard.py` to load shell via `load_standard_connect_shell()` and embed existing controls
- [x] T016 [US1] Add `_build_standard_shell_programmatic()` fallback in `ui/standard.py` on `LayoutLoadError` (FR-104)
- [x] T017 [US1] Refactor `BridgeWindowField` in `ui/field.py` to load strip via `load_field_control_strip()` with programmatic fallback
- [x] T018 [US1] Preserve `embed_connection_hub_on_connect_body()` and `setup_connect_tab_panels()` wiring unchanged in `ui/standard.py`
- [x] T019 [P] [US1] Complete `test_ui_loader.py` — fixture load, missing file raises `LayoutLoadError`, required object names validated
- [x] T020 [US1] Visual checklist SC-102 — Start/Stop visible at 900×380 Standard and 720×480 Field (document pass in `quickstart.md` or task note)

**Checkpoint**: Standard + Field launch; layout edit visible after restart without Python layout edits

---

## Phase 4: User Story 2 — Web dashboard reads live bridge status (P1)

**Goal**: `GET /status` and `GET /health` reflect bridge state within 2 s; HTTP thread does not block Qt

**Independent Test**: `curl /status` matches desktop while Running/Stopped (`quickstart.md` Phase B, SC-201)

- [x] T021 [US2] Implement `create_app(facade)` with `GET /health` and `GET /status` in `web_api.py` per `contracts/web-api.md`
- [x] T022 [US2] Implement `web_server.py` — daemon thread, uvicorn start/stop, default `127.0.0.1:8765` from prefs
- [x] T023 [US2] Start web server from mixin after UI ready when `web_ui.enabled` in `ui/mixin.py`; stop in `closeEvent`
- [x] T024 [US2] Populate facade snapshot fields (running, COM, baud, UDP, Hz, drops, rejects) from mixin bridge stats in `ui/mixin.py`
- [x] T025 [P] [US2] Complete `test_web_api.py` — TestClient `GET /health` and `GET /status` against mock facade
- [x] T026 [US2] Add optional `GET /` minimal JSON or OpenAPI redirect in `web_api.py` (NiceGUI deferred)

**Checkpoint**: `curl http://127.0.0.1:8765/status` matches desktop within 2 s

---

## Phase 5: User Story 3 — Web client starts and stops the bridge (P1)

**Goal**: `POST /bridge/start` and `POST /bridge/stop` with desktop validation parity

**Independent Test**: 10-iteration start/stop via API matches desktop (`quickstart.md` Phase B/E, SC-202)

- [x] T027 [US3] Implement `request_start()` / `request_stop()` queued to Qt main in `app_facade.py` calling mixin `start_bridge` / `stop_bridge`
- [x] T028 [US3] Add command single-flight lock and `error_code=busy` in `app_facade.py`
- [x] T029 [US3] Implement `POST /bridge/start` and `POST /bridge/stop` in `web_api.py` returning `WebCommandResult`
- [x] T030 [US3] Reuse `_validate_before_start()` for Web start path in `app_facade.py` (same messages as desktop)
- [x] T031 [P] [US3] Extend `test_web_api.py` — start/stop ok, validation 400, busy 409 with mock facade
- [x] T032 [P] [US3] Add `bench_web_api.py` — 10× start/stop loop script for SC-202 (optional `verify_all` waiver)

**Checkpoint**: Web start/stop agrees with desktop; invalid baud blocked consistently (SC-205 sample cases)

---

## Phase 6: User Story 4 — Web client reads and updates configuration (P2)

**Goal**: `GET /config` and `PATCH /config` sync core fields to Qt when stopped; stop-first when running

**Independent Test**: PATCH UDP port via curl; desktop fields match before next start (`quickstart.md` Phase B)

- [x] T033 [US4] Implement `get_config()` / `apply_config(patch)` in `app_facade.py` using `ui/connection_fields.py` validators
- [x] T034 [US4] Implement `GET /config` and `PATCH /config` in `web_api.py` with 409 `running_guard` per `contracts/web-api.md`
- [x] T035 [US4] Queue config apply to Qt widgets (com, baud, listen host/port, nmea mode, hub id) in `ui/mixin.py`
- [x] T036 [US4] Reflect Web-driven config changes on hub selection and Manual override within 2 s (FR-206)
- [x] T037 [P] [US4] Extend `test_web_api.py` — PATCH while stopped ok; PATCH COM while running returns 409
- [x] T038 [P] [US4] Extend `test_app_facade.py` — `apply_config` rejects invalid baud via `validate_baud()`

**Checkpoint**: Config round-trip matches desktop; running guard enforced

---

## Phase 7: User Story 5 — Documented control parity matrix (P2)

**Goal**: Parity artifact complete; unsupported writes return 501

**Independent Test**: Review `contracts/control-parity.md`; deferred write returns 501 (`quickstart.md` Phase D)

- [x] T039 [US5] Audit Standard/Field/HUD controls and finalize `specs/005-hybrid-ui-webui/contracts/control-parity.md` (100% run + connection rows)
- [x] T040 [US5] Return `501` + `error_code=unsupported` for Phase B write fields in `web_api.py` (NTRIP, fan-out, discovery refresh, unlock)
- [x] T041 [P] [US5] Add `test_web_api.py` cases for unsupported PATCH fields → 501
- [x] T042 [US5] Add traceability note in `specs/001-baseline-spec/traceability.md` or feature README line pointing to parity matrix

**Checkpoint**: SC-204 — matrix covers all Connect run + connection controls with MVP/B labels

---

## Phase 8: User Story 6 — Safe Web exposure on survey PCs (P3)

**Goal**: Localhost default; optional LAN bind + token; clean shutdown

**Independent Test**: Remote blocked by default; LAN + token works (`quickstart.md` security notes)

- [x] T043 [US6] Enforce default bind `127.0.0.1` and reject `0.0.0.0` unless `lan_bind` true in `web_server.py`
- [x] T044 [US6] Validate `X-Bridge-Token` on mutating routes when LAN + token configured in `web_api.py`
- [x] T045 [US6] Add Tools or prefs UI toggle for Web enable, port, LAN bind in `ui/mixin.py` (or compact Tools tab control)
- [x] T046 [US6] Ensure `stop_web_server()` joins thread within 2 s on `closeEvent` in `ui/mixin.py`
- [x] T047 [P] [US6] Extend `test_web_api.py` — 401/403 without token when LAN+token mode mocked

**Checkpoint**: Default install not LAN-exposed; operator can enable LAN deliberately

---

## Phase 9: Polish & Cross-Cutting

- [x] T048 [P] Add `ui/resources` to PyInstaller `datas` in `nmea_serial_bridge.spec`; hiddenimports for fastapi/uvicorn when bundled
- [x] T049 [P] Update `docs/OPERATOR_GUIDE.md` — Web control plane, port 8765, LAN/firewall, token
- [x] T050 [P] Update `README.md` — optional `requirements-web.txt` and hybrid UI note
- [x] T051 Bump `version.py` to **1.7.0**, `CHANGELOG.md`, run `python tools/sync_version_info.py`
- [x] T052 Run `python tools/run_unittests.py` and `python verify_all.py`; fix regressions
- [x] T053 [P] Run `bench_gui_smoke.py` after `.ui` migration; confirm Qt teardown still clean
- [x] T054 [P] SC-203 manual or scripted 5 Hz `/status` poll during resize (document result in `quickstart.md`)

---

## Dependencies & Execution Order

```text
T001–T005 → T006–T012 (Foundational)
          → T013–T020 (US1 Layer 1 MVP)
          → T021–T026 (US2 status) → T027–T032 (US3 start/stop)
          → T033–T038 (US4 config) → T039–T042 (US5 parity)
          → T043–T047 (US6 security) → T048–T054 (Polish)
```

### User Story Dependencies

| Story | Depends on | Can parallelize after |
|-------|------------|------------------------|
| US1 | T006–T007 (loader) | Foundational loader only — may start T013–T014 with T008–T012 if loader done |
| US2 | Foundational + US1 recommended (same mixin touches) | T021–T025 after T012 |
| US3 | US2 (web_api app exists) | T027–T032 after T021 |
| US4 | US3 (command path proven) | T033–T038 after T027 |
| US5 | US4 (API surface stable) | T039–T042 anytime after T029 |
| US6 | US2 (server running) | T043–T047 after T022 |

### Parallel Opportunities

- T002 + T003 + T004 + T005 after T001
- T007 + T012 after T006
- T013 + T014 (different `.ui` files)
- T019 + T020 after T015–T017
- T025 + T026 after T021
- T031 + T032 after T029
- T037 + T038 after T033
- T048–T054 mostly parallel except T051–T052 sequential

### Parallel Example: User Story 1

```bash
# Design both shells in parallel:
# T013 ui/resources/standard_connect_shell.ui
# T014 ui/resources/field_control_strip.ui
# Then wire sequentially: T015 → T017 → T018
```

### Parallel Example: User Story 2 + 3 (same files — sequential)

```text
web_api.py: T021 (GET) before T029 (POST) before T034 (PATCH)
```

---

## Implementation Strategy

### MVP (Layer 1 + minimal Web read)

1. Phase 1–2 Setup + Foundational  
2. Phase 3 **US1** — `.ui` shells (SC-101, SC-102)  
3. Phase 4 **US2** — status API only (SC-201)  
4. **STOP** — demo visual edit + browser status monitor  

### Field-ready control plane

5. Phase 5 **US3** — start/stop (SC-202, SC-205)  
6. Phase 6 **US4** — config PATCH  
7. Phase 7–8 **US5–US6** — parity + security  
8. Phase 9 — **1.7.0** release  

### Constitution reminders

- No bridge protocol in `web_api.py` / `ui_loader.py` — only `app_facade` → mixin  
- Start/Stop remain on Connect `run` panel after US1  
- HTTP thread never calls Qt widgets directly  

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T005 (5) | — |
| Foundational | T006–T012 (7) | — |
| US1 | T013–T020 (8) | P1 MVP layout |
| US2 | T021–T026 (6) | P1 status |
| US3 | T027–T032 (6) | P1 start/stop |
| US4 | T033–T038 (6) | P2 config |
| US5 | T039–T042 (4) | P2 parity |
| US6 | T043–T047 (5) | P3 security |
| Polish | T048–T054 (7) | — |
| **Total** | **54** | |

**Suggested MVP scope**: T001–T026 (Setup + Foundational + US1 + US2) — visual `.ui` shells and live Web status on localhost.
