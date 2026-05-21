# Tasks: Connection Hub Overhaul

**Input**: `specs/003-connection-hub-overhaul/plan.md`, `spec.md`, `contracts/`, `data-model.md`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

## Format: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

**Purpose**: Scaffolding and shared types

- [ ] T001 Create `discovery_service.py` with dataclasses `SerialDeviceInfo`, `NetworkCardInfo`, `DiscoverySnapshot` per `data-model.md`
- [ ] T002 [P] Add `test_discovery_service.py` skeleton importing `DEFAULT_KEYWORDS` from `discovery_service.py`
- [ ] T003 [P] Create `ui/connection_hub.py` with stub `ConnectionHubWidget` and `EndpointCardWidget` per `contracts/connection-hub-ui.md`

---

## Phase 2: Foundational (Blocking)

**Purpose**: Discovery service + persistence — required before hub renders real data

**⚠️ CRITICAL**: No user story UI work until this phase completes

- [ ] T004 Port serial scan + stability guard from `auto_discovery.py` into `discovery_service.py` `scan_serial_ports()`
- [ ] T005 Implement `probe_udp_port_available()` in `discovery_service.py`
- [ ] T006 Implement `build_network_cards()` and `build_snapshot()` in `discovery_service.py` (passive/network contextual)
- [ ] T007 Migrate `test_auto_discovery.py` cases to `test_discovery_service.py`; keep `auto_discovery.py` as thin delegate to service
- [ ] T008 Add `load_last_known_good()` / `save_last_known_good()` in `ui/ui_prefs.py` keyed by `device_id`
- [ ] T009 Add discovery poll timer + `_on_discovery_snapshot()` wiring stub in `ui/mixin.py` (2 s coalesced)

**Checkpoint**: `python -m unittest test_discovery_service.py -v` passes

---

## Phase 3: User Story 1 — Pick detected GNSS serial card (P1) 🎯 MVP

**Goal**: Serial endpoint cards visible; selection drives COM/baud for Start

**Independent Test**: Plug GNSS USB → card appears → click → Start opens correct COM (see `quickstart.md` Phase B)

- [ ] T010 [US1] Implement `EndpointCardWidget` serial layout + status chip in `ui/connection_hub.py`
- [ ] T011 [US1] Implement `ConnectionHubWidget.set_snapshot()` rendering serial cards in `ui/connection_hub.py`
- [ ] T012 [US1] Wire `selection_changed` signal to `BridgeLogicMixin._on_hub_selection()` in `ui/mixin.py`
- [ ] T013 [US1] On hub selection load `LastKnownGood` into `com_cb` / `baud_edit` in `ui/mixin.py`
- [ ] T014 [US1] Embed `ConnectionHubWidget` in Connect `connection` panel via `ui/connect_panels.py`
- [ ] T015 [US1] Move legacy `create_connection_controls` into collapsible Manual override below hub in `ui/standard.py` / `connect_panels.py`
- [ ] T016 [US1] Update `_collect_bridge_config()` / `_start_bridge()` to prefer hub selection unless override dirty in `ui/mixin.py`
- [ ] T017 [US1] Save `LastKnownGood` on successful Start in `ui/mixin.py`
- [ ] T018 [P] [US1] Add `test_connection_hub.py` — render snapshot with 2 serial cards, click emits `device_id`
- [ ] T019 [US1] Mark stale card when selected COM missing from latest snapshot in `ui/connection_hub.py`

**Checkpoint**: Bench plug/unplug USB; card select → Start → NMEA on COM

---

## Phase 4: User Story 2 — Network listen context (P1)

**Goal**: Network cards show UDP listen template, port availability, live peer count when Running

**Independent Test**: UDP listen Running + sender → card shows peer count; fan-out unchanged (`test_udp_fanout.py`)

- [ ] T020 [US2] Render `NetworkCardInfo` cards in `ConnectionHubWidget` in `ui/connection_hub.py`
- [ ] T021 [US2] Feed `bridge_stats` from `_tick_stats` / `stats_cb` into `build_snapshot()` in `ui/mixin.py`
- [ ] T022 [US2] Hub selection for network card applies UDP host/port/mode widgets in `ui/mixin.py`
- [ ] T023 [US2] Show `port_busy` status when `probe_udp_port_available` false in `ui/connection_hub.py`
- [ ] T024 [P] [US2] Extend `test_discovery_service.py` for `build_network_cards` with mock stats and busy port

**Checkpoint**: Network card reflects `N peers` during session

---

## Phase 5: User Story 3 — Manual override (P2)

**Goal**: Full legacy connection fields available for edge cases; presets still work

**Independent Test**: Override expanded → edit TCP client mode → Save preset → reload

- [ ] T025 [US3] Add `ManualOverridePanel` `QGroupBox` toggled by checkbox in `ui/connection_hub.py`
- [ ] T026 [US3] When override dirty, `_collect_bridge_config()` ignores hub card defaults in `ui/mixin.py`
- [ ] T027 [US3] Include override fields in preset serialize/deserialize in `ui/mixin.py` (`_apply_preset_data` / save preset)
- [ ] T028 [P] [US3] Document override path in `docs/OPERATOR_GUIDE.md` Connect section

---

## Phase 6: User Story 4 — TCP sink mirror (P2)

**Goal**: Optional TCP sink mirrors serial→net concurrently with UDP fan-out

**Independent Test**: SC-302 in `quickstart.md` — 2 UDP clients + 1 TCP client receive data

- [ ] T029 [US4] Add `TcpSinkConfig` dataclass and fields on `SerialNetBridge` in `bridge_core.py`
- [ ] T030 [US4] Implement sink `asyncio` server start/stop in `SerialNetBridge.start()` / `abort_now()` in `bridge_core.py`
- [ ] T031 [US4] Implement `_mirror_to_tcp_sink()` called from `_send_net()` after primary path in `bridge_core.py`
- [ ] T032 [US4] Expose `tcp_sink_clients` / `tcp_sink_drops` in stats dict in `bridge_core.py`
- [ ] T033 [P] [US4] Add `test_tcp_sink.py` — fan-out UDP peers + sink client both receive bytes
- [ ] T034 [US4] Add TCP sink enable + port controls in Manual override or hub network area in `ui/connection_hub.py` / `controls.py`
- [ ] T035 [US4] Pass `TcpSinkConfig` from mixin `_start_bridge()` in `ui/mixin.py`
- [ ] T036 [US4] Include `tcp_sink_*` in `LastKnownGood` persistence in `ui/ui_prefs.py`

**Checkpoint**: `test_tcp_sink.py` + `test_udp_fanout.py` green

---

## Phase 7: User Story 5 — Field layout parity (P2)

**Goal**: Field operators retain Start/Stop + connection access

**Independent Test**: `python bridge_gui.py --ui field` — SC-303 abbreviated smoke

- [ ] T037 [US5] Add compact connection summary + link to Connect hub in `ui/field.py`
- [ ] T038 [US5] Ensure Field strip Start/Stop uses hub-derived config when selection set in `ui/mixin.py`
- [ ] T039 [P] [US5] Verify `bench_gui_smoke.py` passes Field + Standard with hub present

---

## Phase 8: Polish & Cross-Cutting

- [ ] T040 Deprecate direct `AutoDiscoveryThread` usage; document migration in `auto_discovery.py` module docstring
- [ ] T041 [P] Update `docs/OPERATOR_GUIDE.md` with Connection Hub workflow and TCP sink section
- [ ] T042 [P] Update `README.md` feature list for Connection Hub + TCP sink
- [ ] T043 Bump `version.py` to **1.5.0**, `CHANGELOG.md`, run `python tools/sync_version_info.py`
- [ ] T044 Run `python -m unittest discover -s . -p "test_*.py"` and `python verify_all.py`; update `specs/001-baseline-spec/traceability.md` waivers if needed
- [ ] T045 [P] Add operator quickstart cross-link from `specs/003-connection-hub-overhaul/quickstart.md` to OPERATOR_GUIDE

---

## Dependencies & Execution Order

```text
T001–T003 → T004–T009 → T010–T019 (US1 MVP) → T020–T024 (US2)
          → T025–T028 (US3) → T029–T036 (US4) → T037–T039 (US5) → T040–T045
```

### Parallel opportunities

- T002 + T003 after T001
- T018 + T024 after hub exists
- T033 parallel with T034 once bridge_core sink API exists
- T041 + T042 + T045 in polish

### MVP scope (User Story 1 only)

**T001–T019** — discovery service + serial cards + hub embedded in Connect + Start uses selection

---

## Implementation Strategy

1. Land **Foundational** discovery service with migrated tests (no UI regressions).
2. Ship **US1** serial cards as first operator-visible win.
3. Add **US2** network context cards without changing bridge modes.
4. **US3** override ensures escape hatch before **US4** TCP sink.
5. **US5** Field parity; polish with docs + 1.5.0 release.

**Constitution**: No protocol logic in `ui/connection_hub.py` widgets — binding only.
