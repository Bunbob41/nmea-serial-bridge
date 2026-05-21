# Tasks: Connection Hub Phase 2 — Network Discovery

**Input**: `specs/004-hub-network-discovery/plan.md`, `spec.md`, `contracts/`, `data-model.md`, `research.md`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, phase 1 shipped (v1.5.x)

**Tests**: Constitution Principle III — include `test_*.py` and `verify_all.py` in polish phase.

## Format: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

**Purpose**: Scaffolding for scanner, release helpers, and test fixtures

- [x] T001 Create `network_scanner.py` with `NetworkScanResult` dataclass per `data-model.md` and `contracts/network-scanner.md`
- [x] T002 [P] Create `port_release.py` with `PortLockState` dataclass per `contracts/smart-release.md`
- [x] T003 [P] Add `tests/fixtures/arp_sample_windows.txt` for mocked ARP output in unit tests
- [x] T004 [P] Add `test_network_scanner.py` and `test_port_release.py` skeletons with imports

---

## Phase 2: Foundational (Blocking)

**Purpose**: Active scan + snapshot merge + background worker — required before hub refresh shows LAN devices

**⚠️ CRITICAL**: No user story UI work until this phase completes

- [x] T005 Implement `list_lan_hosts()` parsing `arp -a` in `network_scanner.py`
- [x] T006 Implement `probe_host_udp()` and `scan_network()` with host/port budget in `network_scanner.py`
- [x] T007 Implement `probe_com_lock()` and `smart_release_com()` in `port_release.py` (reuse `com_free` open pattern)
- [x] T008 Extend `NetworkCardInfo` / `build_snapshot()` in `discovery_service.py` to merge `network_scan_results` per `data-model.md`
- [x] T009 Add `ui/discovery_worker.py` with `DiscoveryScanWorker(QThread)` emitting `DiscoverySnapshot`
- [x] T010 Wire worker cancel + `skip_bind_port` when bridge UDP listen Running in `ui/mixin.py`
- [x] T011 [P] Complete `test_network_scanner.py` — mocked ARP, UDP probe, deadline budget
- [x] T012 [P] Complete `test_port_release.py` — blocked when bridge running, success on mock serial

**Checkpoint**: `python -m unittest test_network_scanner test_port_release test_discovery_service -v` passes

---

## Phase 3: User Story 1 — Resizable hub without clipping (P1) 🎯 MVP

**Goal**: Connection Hub card grid gets primary space; scroll only on cards; readable COM labels at 900×380

**Independent Test**: Resize window/panel per `quickstart.md` Phase C (SC-401)

- [x] T013 [US1] Refactor `ConnectionHubWidget` toolbar + card-only `QScrollArea` per `contracts/hub-layout-v2.md` in `ui/connection_hub.py`
- [x] T014 [US1] Implement responsive `QGridLayout` column count from hub width in `ui/connection_hub.py`
- [x] T015 [US1] Set `EndpointCardWidget` min width 220px and title elide in `ui/connection_hub.py`
- [x] T016 [US1] Adjust `embed_connection_hub_on_connect_body()` / splitter stretch in `ui/connect_panels.py`
- [x] T017 [US1] Remove double-scroll on Connect `connection` body in `ui/standard.py` (hub scroll only)
- [x] T018 [P] [US1] Update `test_connect_panel_sizes.py` for connection panel min height / hub stretch
- [x] T019 [P] [US1] Extend `test_connection_hub.py` for grid columns at width and toolbar object names

**Checkpoint**: SC-401 manual — no horizontal clip on COM at min window size

---

## Phase 4: User Story 2 — Unified refresh and unlock (P1)

**Goal**: One Refresh discovery + Unlock ports; smart release without app restart

**Independent Test**: `quickstart.md` Phase B — Refresh ≤ 8 s; Unlock after PuTTY on COM (SC-403)

- [x] T020 [US2] Add `refresh_requested` / `unlock_requested` signals and buttons in `ui/connection_hub.py`
- [x] T021 [US2] Implement `_on_hub_refresh_discovery()` starting `DiscoveryScanWorker` in `ui/mixin.py`
- [x] T022 [US2] Implement `_on_hub_unlock_ports()` calling `port_release.smart_release_com()` in `ui/mixin.py`
- [x] T023 [US2] Show scan busy state on hub during worker run in `ui/connection_hub.py` + `ui/mixin.py`
- [x] T024 [US2] Block unlock with dialog when bridge Running on selected COM in `ui/mixin.py`
- [x] T025 [US2] Add Field strip **Refresh** / **Unlock** buttons in `ui/field.py` wired to same mixin handlers
- [x] T026 [P] [US2] Add `hint_udp_listen_busy()` usage in unlock flow in `ui/mixin.py`

**Checkpoint**: Refresh updates cards; Unlock frees bench COM without restart

---

## Phase 5: User Story 3 — Active LAN network discovery (P2)

**Goal**: Network cards from ARP + UDP probe (Q1: B), not only passive UDP template

**Independent Test**: `quickstart.md` Phase E — two UDP senders → distinguishable cards (SC-404)

- [x] T027 [US3] Map `NetworkScanResult` → `NetworkCardInfo` with `discovery_source` in `discovery_service.py`
- [x] T028 [US3] Dedupe discovered cards vs preset/listen cards in `discovery_service.py`
- [x] T029 [US3] Pass `network_scan_results` from worker into `build_snapshot()` in `ui/discovery_worker.py`
- [x] T030 [US3] Hub selection for `net:discovered:*` applies host/port in `ui/mixin.py` `_on_hub_selection()`
- [x] T031 [US3] Empty-state hint when scan finds no extra hosts in `ui/connection_hub.py`
- [x] T032 [P] [US3] Extend `test_discovery_service.py` for discovered network card merge
- [x] T033 [P] [US3] Integration test: mocked `scan_network` returns two hosts → two cards in snapshot

**Checkpoint**: LAN bench shows discovered network cards after Refresh

---

## Phase 6: User Story 4 — Traffic quality on cards (P2)

**Goal**: Running bridge shows Hz / drops / warn on active hub card

**Independent Test**: `quickstart.md` Phase D (SC-405)

- [x] T034 [US4] Add `TrafficQualitySnapshot` and `quality_from_bridge_stats()` in `ui/hub_quality.py` per `contracts/traffic-quality.md`
- [x] T035 [US4] Implement `ConnectionHubWidget.set_quality()` chip/subtitle update in `ui/connection_hub.py`
- [x] T036 [US4] Bind `_stats_from_bridge` to `set_quality()` with 2 s coalesce in `ui/mixin.py`
- [x] T037 [US4] Reset quality to idle on `stop_bridge` in `ui/mixin.py`
- [x] T038 [P] [US4] Add `test_hub_quality.py` for idle/ok/warn thresholds

**Checkpoint**: Card warn within 2 s of bench drop burst

---

## Phase 7: User Story 5 — Standardized connection controls (P3)

**Goal**: Same baud/port validation on hub card, Manual override, and Field strip

**Independent Test**: Invalid baud blocked with one message from any entry point

- [x] T039 [US5] Create `ui/connection_fields.py` with `parse_baud()`, `validate_udp_port()`, shared baud presets
- [x] T040 [US5] Refactor `_validate_before_start()` to use `connection_fields` in `ui/mixin.py`
- [x] T041 [US5] Add optional inline baud on serial card using shared helpers in `ui/connection_hub.py`
- [x] T042 [P] [US5] Add `test_connection_fields.py` for validation parity

**Checkpoint**: Hub baud change syncs to `com_cb` / `baud_edit`

---

## Phase 8: Polish & Cross-Cutting

- [x] T043 [P] Add `load_discovery_scan_prefs()` / `save_discovery_scan_prefs()` in `ui/ui_prefs.py`
- [x] T044 [P] Update `docs/OPERATOR_GUIDE.md` — Refresh discovery, Unlock ports, LAN cards
- [x] T045 [P] Update `README.md` for phase 2 hub features
- [x] T046 Bump `version.py` to **1.6.0**, `CHANGELOG.md`, run `python tools/sync_version_info.py`
- [x] T047 Run `python tools/run_unittests.py` and `python verify_all.py`; fix regressions
- [x] T048 [P] Validate `bench_gui_smoke.py` after hub layout v2 changes
- [x] T049 [P] Cross-link `specs/004-hub-network-discovery/quickstart.md` from `docs/OPERATOR_GUIDE.md`

---

## Dependencies & Execution Order

```text
T001–T004 → T005–T012 → T013–T019 (US1 MVP layout)
          → T020–T026 (US2 refresh/unlock) → T027–T033 (US3 LAN scan)
          → T034–T038 (US4 quality) → T039–T042 (US5 fields) → T043–T049
```

### Parallel opportunities

- T002 + T003 + T004 after T001
- T011 + T012 after T005–T007
- T018 + T019 after T013–T015
- T032 + T033 after T027–T029
- T038 parallel with T034 once `hub_quality.py` exists
- T043–T045 + T049 in polish

### MVP scope (User Story 1 + minimal refresh)

**T001–T026** — foundation + responsive layout + Refresh/Unlock (operator can discover serial and recover COM without layout pain)

Full LAN cards require **T027–T033** (US3).

---

## Implementation Strategy

1. Land **Foundational** scanner + worker (mocked tests green).
2. Ship **US1** layout — immediate clipping fix.
3. Add **US2** Refresh/Unlock on toolbar and Field strip.
4. **US3** active LAN cards (Q1 B).
5. **US4** quality chips; **US5** shared validators.
6. Polish **1.6.0** + verify_all.

**Constitution**: No protocol logic in `ui/connection_hub.py` — binding and layout only; scan in `network_scanner.py` / worker.
