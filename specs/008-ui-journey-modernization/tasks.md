# Tasks: UI & Workflow Journey Modernization

**Input**: Design documents from `/specs/008-ui-journey-modernization/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Per constitution Principle III — `test_demo_snapshot.py`, `test_ui_prefs.py`, and `verify_all.py` required for this epic (local-only; no agent-browser).

**Organization**: Tasks grouped by user story (spec priority). **Plan note**: implementation may tackle **US3 (Demo isolation)** early as architectural spine even though spec labels it P2; US1 remains the operator MVP for release validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same phase)
- **[Story]**: US1–US4 per [spec.md](./spec.md)

## Path Conventions

- Repo root: `ui/`, `docs/`, `test_*.py`, `bench_config.py`, `web/static/` (audit copy only)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Read design artifacts and prepare audit tracking

- [x] T001 Review [contracts/demo-state-isolation.md](./contracts/demo-state-isolation.md), [contracts/ui-audit-matrix.md](./contracts/ui-audit-matrix.md), and [contracts/returning-user-flow.md](./contracts/returning-user-flow.md)
- [x] T002 Create `docs/ui-audit-inventory.md` header and severity columns per [contracts/ui-audit-matrix.md](./contracts/ui-audit-matrix.md)
- [x] T003 [P] Confirm feature pointer in `.specify/feature.json` is `specs/008-ui-journey-modernization`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Layout/prefs migration shared by US1, US2, and US4 — MUST complete before layout-dependent story work

**⚠️ CRITICAL**: US3 demo modules do not block US1/US2, but prefs migration blocks reliable Connect launch geometry

- [x] T004 Verify `reset_sizes` removed from `CONNECT_TOOLBAR_KEYS` in `ui/connect_panels.py` and toolbar prefs strip in `ui/ui_prefs.py`
- [x] T005 [P] Extend `test_ui_prefs.py` to assert `reset_sizes` stripped from loaded `toolbar_order`
- [x] T006 [P] Verify `_MIN_VALID_SAVED_HEIGHT` applied on Connect rebuild in `ui/connect_panels.py` (no zero-height connection panel)

**Checkpoint**: Prefs/layout migration stable — US1, US2, US4 can proceed; US3 can start in parallel from Phase 5

---

## Phase 3: User Story 1 — Returning operator resumes last setup (Priority: P1) 🎯 MVP

**Goal**: Cold launch restores last preset + connection fields; recent sessions scannable and apply cleanly when stopped

**Independent Test**: Save distinct preset, relaunch stopped app — Connect shows same COM/UDP/NMEA/preset without opening Tools; Start uses restored settings (see [quickstart.md](./quickstart.md) §3, SC-102)

### Tests for User Story 1

- [x] T007 [P] [US1] Add launch-restore test for `last_preset` in `test_path_presets.py` or `test_ui_prefs.py`
- [x] T008 [P] [US1] Add recent-session apply sets `nmea_mode` test in `test_ui_prefs.py` or new `test_recent_sessions.py`

### Implementation for User Story 1

- [x] T009 [US1] Audit single launch-restore path in `ui/mixin.py` (`_finalize_ui` / `_init_web_and_facade` / preset activation)
- [x] T010 [US1] Ensure all layout entry points call unified restore in `bridge_gui.py` and `ui/registry.py` window factories
- [x] T011 [P] [US1] Verify `_rebuild_recent_sessions_menu` label format in `ui/mixin.py` includes `nmea_mode`
- [x] T012 [US1] Confirm stop-first messaging when applying preset/recent while running in `ui/mixin.py` `_activate_preset_by_name` / `_apply_recent_session`
- [x] T013 [P] [US1] Verify Field strip summary reflects active preset in `ui/field.py` `_update_field_connect_summary`

**Checkpoint**: US1 independently testable — operator can resume and start within 60 s (manual SC-102)

---

## Phase 4: User Story 2 — Global UI & information consistency (Priority: P1)

**Goal**: Zero P0 copy/layout defects; terminology aligned with operator guide; no dead controls

**Independent Test**: Walk `docs/ui-audit-inventory.md` at 1280×720 on Standard, Field, Minimal, Log-first — all P0 closed (SC-101, SC-103)

### Implementation for User Story 2

- [x] T014 [US2] Populate audit rows for Connect + status bar in `docs/ui-audit-inventory.md` (STD/FIELD/MIN/LOG)
- [x] T015 [P] [US2] Populate Tools subtabs rows (Presets, Phone, NMEA, Guide, Diagnostics) in `docs/ui-audit-inventory.md`
- [x] T016 [P] [US2] Fix P0 placeholder: Phone QR when token present in `ui/mixin.py` `_refresh_phone_tab_qr` and `ui/connect_qr_overlay.py`
- [x] T017 [P] [US2] Fix P0 clip: Start/Stop and status chips at 1280×720 in `ui/standard.py` `ui/field.py` `ui/styles.py`
- [x] T018 [P] [US2] Fix P0 dead-control/docs: remove **Reset sizes** / splitter references in `docs/OPERATOR_GUIDE.md` and `docs/GETTING_STARTED.md`
- [x] T019 [P] [US2] Align Tools hints with operator guide in `ui/presets_panel.py` `ui/tool_tabs.py` `ui/controls.py`
- [x] T020 [P] [US2] Fix P0 `webPortSpin` step button visibility in `ui/styles.py` if still open in inventory
- [x] T021 [US2] Mark all P0 items **fixed** or **deferred** with release-note line in `docs/ui-audit-inventory.md`

**Checkpoint**: US2 ship gate — zero open P0 (SC-101)

---

## Phase 5: User Story 3 — Product Demo without polluting live session (Priority: P2)

**Goal**: Snapshot on demo open, persistence guards during demo, full restore on close; presenter state isolated in dialog

**Independent Test**: [quickstart.md](./quickstart.md) §2 — pre/post COM/preset/bridge match; `path_presets.json` unchanged (SC-201, SC-202, SC-203)

### Tests for User Story 3

> Write tests first; they should fail until T025–T027 complete.

- [x] T022 [P] [US3] Add `test_capture_restore_roundtrip` in `test_demo_snapshot.py`
- [x] T023 [P] [US3] Add `test_demo_preserves_path_presets` in `test_demo_snapshot.py` (temp `USER_PRESETS_PATH` mock)
- [x] T024 [P] [US3] Add `test_restore_bridge_running_flag` in `test_demo_snapshot.py`

### Implementation for User Story 3

- [x] T025 [P] [US3] Create `OperatorSessionSnapshot` dataclass in `ui/demo_snapshot.py` per [data-model.md](./data-model.md)
- [x] T026 [US3] Implement `capture_operator_snapshot` in `ui/demo_snapshot.py`
- [x] T027 [US3] Implement `restore_operator_snapshot` in `ui/demo_snapshot.py` using `ui/mixin.py` helpers
- [x] T028 [US3] Create `DemoHostGateway` (`enter`/`exit`/`run_action`) in `ui/demo_gateway.py`
- [x] T029 [US3] Set `host._demo_session_active` in gateway; call `enter` from `open_product_demo` in `ui/demo.py`
- [x] T030 [US3] Route `DemoRunner`, `_manual_advance`, `_run_selected` actions through `gateway.run_action` in `ui/demo.py`
- [x] T031 [US3] Implement `closeEvent`/`reject` restore via `gateway.exit` in `ui/demo.py` `ProductDemoDialog`
- [x] T032 [US3] Add persistence guards in `ui/mixin.py` (`_preset_save_*`, `push_recent_session`, related save paths)
- [x] T033 [P] [US3] Track `demo_started_bridge` for restore policy in `ui/demo_gateway.py` or `ui/demo.py`
- [x] T034 [P] [US3] Add optional “Demonstration” status chip while demo open in `ui/mixin.py` or status banner widget
- [x] T035 [US3] Add **Reset demo script** control (rewind presenter index only) in `ui/demo.py` per FR-306
- [x] T036 [US3] Ensure second demo open reuses single dialog path in `ui/mixin.py` `_open_product_demo` without double snapshot

**Checkpoint**: US3 independently testable — automated tests green + manual §2 pass

---

## Phase 6: User Story 4 — Web dashboard handoff copy (Priority: P3)

**Goal**: Phone/dashboard strings reflect saved token and current port (no stale placeholders)

**Independent Test**: Desktop token + phone URL saved → Phone tab and setup link work without redundant missing-token UI (SC-301 partial, FR-401)

### Implementation for User Story 4

- [ ] T037 [P] [US4] Verify `_restore_web_ui_prefs` calls `_refresh_phone_tab_qr` in `ui/mixin.py`
- [ ] T038 [P] [US4] Verify `_phone_tools_tab_active` hides floating QR in `ui/connect_qr_overlay.py`
- [ ] T039 [US4] Audit token/URL empty-state strings in `web/static/dashboard.js` vs desktop state (read-only copy fixes)
- [ ] T040 [P] [US4] Add audit row for web dashboard handoff in `docs/ui-audit-inventory.md` and close P0/P1

**Checkpoint**: US4 complete — hybrid handoff copy consistent with desktop

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Release gates and documentation

- [ ] T041 Bump `version.py` to **1.10.0** and add `## v1.10.0` section in `CHANGELOG.md`
- [ ] T042 [P] Run `python tools/sync_version_info.py` for `version_info.txt`
- [ ] T043 Update Product demo + returning-user sections in `docs/OPERATOR_GUIDE.md`
- [ ] T044 [P] Update `.cursor/rules/specify-rules.mdc` if feature ships (optional post-merge)
- [ ] T045 Run `python -m unittest test_demo_snapshot.py test_ui_prefs.py test_path_presets.py -v`
- [ ] T046 Run `python verify_all.py` and `python -m unittest discover -s . -p "test_*.py"`
- [ ] T047 Execute manual checklist in `specs/008-ui-journey-modernization/quickstart.md` (all §§)

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends on | Blocks |
|-------|------------|--------|
| 1 Setup | — | 2 |
| 2 Foundational | 1 | 3, 4, 6 (layout prefs) |
| 3 US1 (P1) | 2 | — |
| 4 US2 (P1) | 2 | Polish (P0 gate) |
| 5 US3 (P2) | 1 (contracts) | Polish |
| 6 US4 (P3) | 2, 4 partial | Polish |
| 7 Polish | 3–6 desired scope | — |

### User Story Dependencies

| Story | Depends on | Independent? |
|-------|------------|--------------|
| **US1** | Foundational T004–T006 | ✅ Yes — MVP |
| **US2** | Foundational; inventory T002 | ✅ Yes — parallel with US1 |
| **US3** | Tests after T025–T027 | ✅ Yes — does not require US1/US2 complete |
| **US4** | US2 Phone P0 fixes (T016) recommended | ✅ Mostly independent |

### Within User Story 3 (critical path)

```text
T025 → T026 → T027 → T028 → T029 → T030 → T031
              ↘ T032 (guards) ↗
T022–T024 (tests) after T026–T027 stubs exist
```

### Parallel Opportunities

- **Phase 2**: T005 ∥ T006  
- **Phase 3**: T007 ∥ T008; T011 ∥ T013  
- **Phase 4**: T014–T021 largely different files — mark [P] batches  
- **Phase 5**: T022–T024 ∥ after snapshot stubs; T025 ∥ T028 design; T034 ∥ T035  
- **Phase 6**: T037 ∥ T038 ∥ T039  
- **Cross-story**: US1 ∥ US2 after Phase 2; US3 ∥ US2 after T002 inventory exists  

---

## Parallel Example: User Story 3

```bash
# Tests in parallel (after snapshot module stubbed):
T022 test_capture_restore_roundtrip
T023 test_demo_preserves_path_presets
T024 test_restore_bridge_running_flag

# Then implementation chain:
T025 OperatorSessionSnapshot → T026 capture → T027 restore
T028 DemoHostGateway → T029 wire open → T030 route actions → T031 close restore
```

---

## Parallel Example: User Story 1 + US2

```bash
# After Phase 2 complete, two developers:
Dev A: T009–T013 (US1 launch restore)
Dev B: T014–T021 (US2 audit inventory + P0 fixes)
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1–2  
2. Complete Phase 3 (US1)  
3. **STOP** — validate [quickstart.md](./quickstart.md) §3 and SC-102  
4. Ship patch release if needed before demo work  

### Recommended full epic order (per [plan.md](./plan.md))

1. Phase 1–2  
2. **Phase 5 (US3)** — demo isolation spine (prevents presenter regressions)  
3. Phase 3 (US1) + Phase 4 (US2) in parallel  
4. Phase 6 (US4)  
5. Phase 7 polish → **v1.10.0**  

### Incremental delivery

| Increment | Stories | Version hint |
|-----------|---------|--------------|
| v1.10.0-alpha | US3 demo restore | internal |
| v1.10.0-beta | + US1 returning | bench |
| v1.10.0 | + US2 audit P0 + US4 + polish | release |

---

## Notes

- **No agent-browser** — validation per [research.md](./research.md) R5 and [quickstart.md](./quickstart.md)  
- `[P]` = different files; avoid two agents editing `ui/mixin.py` simultaneously  
- US3 tasks touch `ui/demo.py` + `ui/mixin.py` — sequence T030 before T032 or coordinate  
- Commit after each checkpoint; do not amend constitution-required version bump across partial releases without CHANGELOG entry  

---

## Task Summary

| Metric | Count |
|--------|------:|
| **Total tasks** | 47 |
| Phase 1 Setup | 3 |
| Phase 2 Foundational | 3 |
| US1 | 7 |
| US2 | 8 |
| US3 | 15 |
| US4 | 4 |
| Polish | 7 |

**Suggested MVP scope**: Phase 1–2 + Phase 3 (US1) — 13 tasks (T001–T013)

**Demo isolation slice**: T022–T036 (15 tasks)

**Format validation**: All tasks use `- [ ] T###` with story labels on US phases and file paths in descriptions ✅
