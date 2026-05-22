# Tasks: Web Config Editor & Desktop UX Fixes

**Input**: `specs/007-web-config-desktop-ux/plan.md`, `spec.md`, contracts/, `research.md`

**Prerequisites**: plan.md ✅, spec.md ✅, v1.8.4+ dashboard shipped

## Format: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

- [X] T001 Add `qrcode>=7.4` to `requirements-web.txt` for SVG token QR (optional web dep)
- [X] T002 [P] Create `web/qr_svg.py` text fallback when qrcode missing

---

## Phase 2: Foundational (Blocking)

- [X] T003 Extend `ConfigPatch` with `remote_host`, `remote_port` in `web_api.py`
- [X] T004 Implement `network_mode` + remote host/port in `app_facade._apply_config_on_main`
- [X] T005 Add `GET /token-qr` SVG route in `web_api.py`
- [X] T006 [P] Add `test_app_facade.py` tests for `network_mode` patch mapping
- [X] T007 [P] Add `test_web_api.py` tests for `/token-qr` and config patch fields

**Checkpoint**: façade + API tests pass

---

## Phase 3: User Story 1 — Editable web config (P1)

- [X] T008 [US1] Replace read-only config card with editable form in `web/static/index.html`
- [X] T009 [P] [US1] Style config form, lock state, mode-conditional fields in `web/static/dashboard.css`
- [X] T010 [US1] Implement config load/save, running lock, mode fields in `web/static/dashboard.js`
- [X] T011 [US1] Populate COM `<select>` from `GET /discovery` serial list in `web/static/dashboard.js`

**Checkpoint**: US1 — save COM/mode/port from dashboard when stopped

---

## Phase 4: User Story 2 — QR token (P2)

- [X] T012 [US2] Add "Show QR for API token" checkbox + img region in `web/static/index.html`
- [X] T013 [US2] Wire QR checkbox + `/token-qr` display in `web/static/dashboard.js`
- [X] T014 [P] [US2] Style QR block in `web/static/dashboard.css`

**Checkpoint**: US2 — QR scannable on PC browser

---

## Phase 5: User Story 3 — Field Guide clipping (P1)

- [X] T015 [US3] Wrap Guide tab in `QScrollArea` + form spacing in `ui/tool_tabs.py` `build_guide_tab`
- [X] T016 [US3] Set `web_box` minimum height and field growth policy in `ui/tool_tabs.py`

**Checkpoint**: US3 — no clipped Web control rows at launch

---

## Phase 6: User Story 4 — Standard COM dropdown (P2)

- [X] T017 [US4] Preserve COM selection in `refresh_ports()` in `ui/mixin.py`
- [X] T018 [US4] Empty-list placeholder and `NoInsert` policy in `ui/mixin.py`

**Checkpoint**: US4 — COM dropdown lists and retains selection

---

## Phase 7: User Story 5 — Standard Connect resize (P2)

- [X] T019 [US5] Verify/fix splitter handle visibility in `ui/connect_panels.py` / `ui/styles.py`
- [X] T020 [US5] Ensure `reset_sizes` restores splitter in `ui/connect_panels.py`

**Checkpoint**: US5 — Connect panels draggable + persist

---

## Phase 8: Polish

- [X] T021 [P] Update `docs/OPERATOR_GUIDE.md` — editable web config, QR, desktop fixes
- [X] T022 [P] Update `specs/005-hybrid-ui-webui/contracts/control-parity.md` web config write
- [X] T023 Bump `version.py` to **1.9.0**, `CHANGELOG.md`, `python tools/sync_version_info.py`
- [X] T024 Run `python -m unittest test_web_api test_app_facade -v` and `python verify_all.py`
- [X] T025 Mark all tasks [X] in this file

---

## Dependencies

```text
T001–T007 → T008–T011 (US1) → T012–T014 (US2)
         → T015–T016 (US3) ∥ T017–T018 (US4) ∥ T019–T020 (US5) → T021–T025
```

**MVP**: T001–T011 (US1 editable config)

**Suggested release**: 1.9.0 full epic
