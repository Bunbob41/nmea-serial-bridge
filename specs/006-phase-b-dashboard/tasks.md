# Tasks: Phase B Operator Dashboard

**Input**: `specs/006-phase-b-dashboard/plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts ✅, 005 Web API shipped (v1.7.2+)

**Tests**: FR-301 + constitution Principle III — `test_web_api.py`, `test_app_facade.py`, `verify_all.py` in polish phase.

## Format: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

**Purpose**: Static asset directory and test scaffolding

- [X] T001 Create `web/static/` directory per `specs/006-phase-b-dashboard/plan.md`
- [X] T002 [P] Add placeholder `web/static/index.html`, `web/static/dashboard.css`, `web/static/dashboard.js` shells
- [X] T003 [P] Extend `test_web_api.py` with skipped/placeholder tests for `GET /` HTML and new routes (imports only until implemented)

---

## Phase 2: Foundational (Blocking)

**Purpose**: API extensions + façade discovery cache — MUST complete before dashboard user stories

**⚠️ CRITICAL**: No US1–US4 dashboard work until T004–T015 pass

- [X] T004 Add `WebMeta`, `WebDiscoveryPayload`, DTO helpers in `app_facade.py` per `data-model.md`
- [X] T005 Implement thread-safe discovery cache `update_discovery_snapshot()` / `get_discovery()` in `app_facade.py`
- [X] T006 Wire `ui/mixin.py` to call `facade.update_discovery_snapshot()` after hub `set_snapshot()` and discovery worker completion
- [X] T007 Implement `request_refresh_discovery()` via `_invoke_on_main` calling `mixin._on_hub_refresh_discovery()` in `app_facade.py`
- [X] T008 Implement `request_unlock_ports()` via `_invoke_on_main` using `smart_release_com` + `hint_udp_listen_busy` (no `QMessageBox` on API path) in `app_facade.py`
- [X] T009 Add `GET /meta` in `web_api.py` per `contracts/web-api-extensions.md`
- [X] T010 Add `GET /discovery` in `web_api.py` returning façade discovery payload
- [X] T011 Add `POST /discovery/refresh` in `web_api.py` with `WebCommandResult` / busy handling
- [X] T012 Add `POST /ports/unlock` in `web_api.py` with `WebCommandResult`
- [X] T013 Move JSON service index from `GET /` to `GET /api` in `web_api.py` (preserve response shape)
- [X] T014 [P] Add Pydantic models for `MetaResponse`, `DiscoveryResponse`, unlock/refresh in `web_api.py`
- [X] T015 Complete `test_web_api.py` for `/meta`, `/discovery`, `/ports/unlock`, `/discovery/refresh`, `/api`
- [X] T016 [P] Complete `test_app_facade.py` for discovery cache, `request_unlock_ports`, `request_refresh_discovery` with Qt event loop harness

**Checkpoint**: `python -m unittest test_web_api test_app_facade -v` passes for new API surface

---

## Phase 3: User Story 1 — View real-time telemetry & status (P1) 🎯 MVP

**Goal**: Dashboard at `GET /` shows live Hz/drops and offline state without Swagger

**Independent Test**: Open `http://127.0.0.1:8765/`, bridge running — Hz/drops update ~1/s; stop app — offline banner (`quickstart.md` Phase A)

- [X] T017 [US1] Implement `web/static/index.html` layout regions per `contracts/dashboard-ui.md` (header, status card, placeholders for run/discovery)
- [X] T018 [P] [US1] Implement vendored `web/static/dashboard.css` responsive rules (360px–1920px, touch targets) per `contracts/dashboard-ui.md`
- [X] T019 [US1] Mount static files and serve `GET /` → `index.html` in `web_api.py` (StaticFiles or FileResponse)
- [X] T020 [US1] Implement status polling loop (1000 ms) and render `GET /status` fields in `web/static/dashboard.js`
- [X] T021 [US1] Implement offline/backend-down UI state on fetch failure in `web/static/dashboard.js`
- [X] T022 [US1] Load `GET /meta` on init and show version in header in `web/static/dashboard.js`
- [X] T023 [US1] Display `GET /config` summary strip in `web/static/dashboard.js`
- [X] T024 [US1] Show token settings field when `meta.token_required`; persist `localStorage` key `nmea-bridge-web-token` in `web/static/dashboard.js`
- [X] T025 [P] [US1] Add `test_web_api.py` assertion `GET /` returns `text/html` with dashboard marker

**Checkpoint**: Dashboard shows live telemetry; offline state works; SC-101 manual check

---

## Phase 4: User Story 2 — Remote start and stop (P1)

**Goal**: Large Start/Stop on dashboard map to existing bridge endpoints

**Independent Test**: Start/stop from dashboard matches desktop (`quickstart.md` Phase A; SC-102 bench script)

- [X] T026 [US2] Add Start/Stop buttons to `web/static/index.html` per `contracts/dashboard-ui.md`
- [X] T027 [US2] Style primary/secondary run controls in `web/static/dashboard.css`
- [X] T028 [US2] Implement `POST /bridge/start` and `POST /bridge/stop` with token header and command-in-flight disable in `web/static/dashboard.js`
- [X] T029 [US2] Surface API error bodies (400 validation, 409 busy) inline in `web/static/dashboard.js`
- [X] T030 [US2] Sync running indicator with status poll after start/stop in `web/static/dashboard.js`
- [X] T031 [P] [US2] Document 10× start/stop dashboard loop in `bench_web_api.py` or `quickstart.md` for SC-102

**Checkpoint**: US2 independent — start/stop works without opening `/docs`

---

## Phase 5: User Story 3 — Soft reset / unlock ports (P2)

**Goal**: Unlock ports from dashboard with desktop-parity messaging

**Independent Test**: Tap Unlock — message matches API; desktop unlock path invoked (`quickstart.md` Phase C)

- [X] T032 [US3] Add Unlock button to `web/static/index.html` tools region
- [X] T033 [US3] Wire `POST /ports/unlock` with token header and inline alert in `web/static/dashboard.js`
- [X] T034 [US3] Disable Unlock during command-in-flight in `web/static/dashboard.js`

**Checkpoint**: US3 independent — unlock message visible in UI

---

## Phase 6: User Story 4 — Refresh discovery and select COM (P3)

**Goal**: Full US4 — refresh, poll discovery 15s, select device, PATCH config

**Independent Test**: USB adapter appears after refresh; select updates `GET /config`; 409 when running (`quickstart.md` Phase B)

- [X] T035 [US4] Add discovery panel (Refresh button, serial/network lists) to `web/static/index.html`
- [X] T036 [P] [US4] Style discovery list and scanning state in `web/static/dashboard.css`
- [X] T037 [US4] Implement `POST /discovery/refresh` + poll `GET /discovery` every 500 ms up to 15 s in `web/static/dashboard.js`
- [X] T038 [US4] Render `serial_devices` and `network_cards` from discovery payload in `web/static/dashboard.js`
- [X] T039 [US4] On row select, `PATCH /config` with `com_port` and/or `hub_device_id` in `web/static/dashboard.js`
- [X] T040 [US4] Handle 409 `running_guard` on PATCH with clear message in `web/static/dashboard.js`
- [X] T041 [US4] Refresh config summary after successful PATCH in `web/static/dashboard.js`

**Checkpoint**: US4 independent — discovery refresh + COM picker end-to-end

---

## Phase 7: Polish & Cross-Cutting

- [X] T042 [P] Add `web/static` to PyInstaller `datas` in `nmea_serial_bridge.spec`
- [X] T043 [P] Update `docs/OPERATOR_GUIDE.md` — dashboard at `/`, LAN/Tailscale, token, offline CSS
- [X] T044 [P] Update `specs/005-hybrid-ui-webui/contracts/control-parity.md` — mark implemented Phase B controls (unlock, refresh, dashboard)
- [X] T045 Bump `version.py` to **1.8.0**, `CHANGELOG.md`, run `python tools/sync_version_info.py`
- [X] T046 Run `python -m unittest test_web_api test_app_facade -v` and `python verify_all.py`
- [X] T047 [P] Manual SC-103 checklist — dashboard usable at 360px and 1920px, vendored CSS only, no internet
- [X] T048 [P] Manual SC-104 — unlock and discovery timeout/success paths documented in `quickstart.md` notes

---

## Phase 8: Bug Fixes (post-ship)

**Root causes identified from live screenshot:**

- `[hidden]` attribute overridden by CSS `display` rules → banner/spinner/token-section always visible
- Stale "Application window not available" inline alerts not cleared on reconnect
- `body.detail` API error parser breaks on plain-string details (401 responses)

- [X] T049 Add `[hidden] { display: none !important; }` reset to `web/static/dashboard.css` (fixes offline-banner, scan-spinner, token-section, status-grid always showing)
- [X] T050 In `dashboard.js` `setOnline()`: clear stale window-unavailable alerts from run-card and discovery-card on first successful reconnect
- [X] T051 Extract `extractApiError(body, fallback)` helper in `dashboard.js`; replace all inline `body.detail.message || JSON.stringify(body.detail)` patterns to handle string and object detail equally

---

## Dependencies & Execution Order

```text
T001–T003 → T004–T016 (Foundational API)
          → T017–T025 (US1 telemetry) → T026–T031 (US2 start/stop)
          → T032–T034 (US3 unlock)
          → T035–T041 (US4 discovery)
          → T042–T048 (Polish)
```

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US1 | Foundational (T016) | Needs `/meta`; `GET /` HTML; static mount |
| US2 | US1 shell (T017–T019) | Same `dashboard.js`; can follow immediately after US1 |
| US3 | Foundational unlock route (T012) | UI only after US1 layout |
| US4 | Foundational discovery routes (T010–T011) | UI after US1; PATCH uses 005 config API |

### Parallel Opportunities

- T002 + T003 after T001
- T014 + T015 + T016 after T009–T013
- T018 parallel with T017 after T019 route exists
- T025 after T019
- T031, T036, T042–T044, T047–T048 mostly parallel in polish

### Parallel Example: Foundational

```text
# After T008:
T009–T013 (web_api.py) sequential
T014 + T015 parallel
T016 (test_app_facade.py) parallel with T015
```

---

## Implementation Strategy

### MVP (operator can monitor without Swagger)

1. Phase 1–2 Setup + Foundational  
2. Phase 3 **US1** — dashboard + live status (SC-101)  
3. **STOP** — demo telemetry page  

### Field-ready control

4. Phase 4 **US2** — start/stop (SC-102)  
5. Phase 5 **US3** — unlock  
6. Phase 6 **US4** — discovery + COM picker  
7. Phase 7 — **1.8.0** release  

### Constitution reminders

- No NMEA/socket logic in `web/static/dashboard.js` beyond REST calls  
- No Qt access from HTTP handlers — façade only  
- Desktop Start/Stop remains on Connect `run` panel  

---

## Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T003 (3) | — |
| Foundational | T004–T016 (13) | — |
| US1 | T017–T025 (9) | P1 MVP telemetry |
| US2 | T026–T031 (6) | P1 start/stop |
| US3 | T032–T034 (3) | P2 unlock |
| US4 | T035–T041 (7) | P3 discovery |
| Polish | T042–T048 (7) | — |
| **Total** | **48** | |

**Suggested MVP scope**: T001–T025 (Setup + Foundational + US1) — live dashboard telemetry at `GET /`.
