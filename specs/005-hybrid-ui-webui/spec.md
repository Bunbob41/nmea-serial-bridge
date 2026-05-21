# Feature Specification: Hybrid UI Architecture — Qt Visual Layouts + WebUI Bridge

**Feature Branch**: `2032-hybrid-ui-webui`

**Created**: 2026-05-21

**Status**: Draft

**Input**: Hybrid UI Architecture Migration (Qt Visual + WebUI Bridge) — Layer 1: Qt Designer `.ui` files for Standard/Field; Layer 2: background WebUI with status/config and start/stop; Constitution: WebUI as non-blocking peer with full control parity over time.

**Builds on**: [`specs/004-hub-network-discovery/spec.md`](../004-hub-network-discovery/spec.md) (shipped v1.6.0: Connection Hub, discovery, QoS)

**Baseline**: [`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md)

**Governance**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Principles I (Bridge-Core Separation), II (Operator Trust), III (Verifiable Changes), V (Resilience & Bounded Resources); Technical Constraints (Qt main thread, asyncio bridge thread, no new mandatory deps without plan justification).

---

## Purpose

Survey operators and maintainers need two improvements without sacrificing field reliability:

1. **Visual layout maintenance** — Standard and Field Connect layouts should be editable in a visual designer and loaded at runtime so UI polish does not require recompiling Python layout code for every spacing tweak.
2. **Remote headless control** — A browser-accessible control plane on the same machine (or trusted LAN) should read bridge/connection status and issue the same start/stop and configuration actions as the desktop app, for bench automation, second-monitor dashboards, and future mobile-friendly ops.

The WebUI MUST remain a **peer** to the Qt desktop UI: it reads state and sends commands through a shared application core, never owning bridge protocol logic and never blocking the Qt event loop.

---

## As-Built vs This Epic

| Capability | Today (v1.6.0) | This epic |
|------------|----------------|-----------|
| Standard / Field layout | Programmatic Qt widgets in Python modules | **Runtime-loaded visual layout files** for primary Connect shells |
| Secondary UIs | Minimal, Log-first, HUD unchanged initially | Out of scope unless explicitly added in plan |
| External control | None (desktop only) | **Web control plane** with status + config read/write + start/stop |
| Bridge logic location | `bridge_core.py` / `nmea_codec.py` | Unchanged — WebUI and Qt bind to same session API |
| Threading model | asyncio bridge thread + Qt main | **+ Web server on dedicated background thread** |
| Control parity | Desktop only | **Documented parity matrix**; MVP endpoints first, phased full parity |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual layout edit without code rebuild (Priority: P1)

A maintainer adjusts Connect panel spacing, labels, or widget order in a visual designer, saves layout files, and relaunches the app to see changes without editing Python layout code.

**Why this priority**: Unblocks faster UI iteration called out in Layer 1.

**Independent Test**: Change a visible label or margin in the layout file; relaunch Standard and Field; change appears; Start/Stop and Connection hub still function.

**Acceptance Scenarios**:

1. **Given** Standard Connect is shown, **When** the app starts, **Then** the Connect shell is assembled from external layout resources, not solely from inline widget construction in the layout module.
2. **Given** a layout file is updated on disk, **When** the operator restarts the app, **Then** the new layout is reflected without rebuilding the frozen executable (dev mode); frozen builds ship updated `.ui` assets in the bundle.
3. **Given** a layout file is missing or invalid, **When** the app starts, **Then** the operator sees a clear error and a safe fallback (last-known-good programmatic layout or blocking message with log path)—not a silent blank Connect tab.

---

### User Story 2 - Web dashboard reads live bridge status (Priority: P1)

An operator or test script opens a browser page on the bridge PC and sees whether the bridge is running, COM/UDP settings in effect, and high-level health (Hz band, drops/rejects summary) matching the desktop status within one refresh interval.

**Why this priority**: Layer 2 foundation; enables bench automation and second-screen monitoring.

**Independent Test**: Start bridge from desktop; open Web status view; fields match desktop within 2 s; after Stop, status shows stopped.

**Acceptance Scenarios**:

1. **Given** the bridge is stopped, **When** the client requests status, **Then** the response indicates stopped state and current configured COM/UDP (not stale “running”).
2. **Given** the bridge is running with traffic, **When** status is polled, **Then** throughput and drop/reject summaries update within 2 s of desktop stats.
3. **Given** the Web server is running, **When** the Qt window is resized or HUD is opened, **Then** the desktop UI remains responsive (no multi-second freezes attributable to Web traffic).

---

### User Story 3 - Web client starts and stops the bridge (Priority: P1)

An operator uses the Web UI (or `curl`/bench script) to start and stop the bridge with the same validation rules as the desktop **Start bridge** / **Stop bridge** controls.

**Why this priority**: Core Layer 2 command path; constitution requires peer behavior.

**Independent Test**: Configure COM/UDP via desktop or Web; POST start; bridge runs; POST stop; COM released; invalid config returns same error class as desktop.

**Acceptance Scenarios**:

1. **Given** valid connection settings, **When** the Web client requests start, **Then** the bridge enters Running and desktop Start/Stop reflects running state within 2 s.
2. **Given** invalid baud or port, **When** the Web client requests start, **Then** start is rejected with an operator-readable message consistent with desktop validation.
3. **Given** bridge Running, **When** the Web client requests stop, **Then** the session ends, COM is released, and status shows stopped within 3 s.
4. **Given** bridge Running from desktop, **When** the Web client requests stop, **Then** stop succeeds (either entry point may stop the session).

---

### User Story 4 - Web client reads and updates configuration (Priority: P2)

An operator adjusts connection configuration (COM, baud, UDP listen host/port, NMEA mode, and hub-selected device context) through the Web API and sees those values applied before the next start.

**Why this priority**: Completes `/config` contract; enables headless bench presets.

**Independent Test**: GET config; PATCH/POST config with new UDP port; desktop fields and next start use new values.

**Acceptance Scenarios**:

1. **Given** a hub-selected serial device, **When** config is read, **Then** the response includes COM, baud, and device identity sufficient to reproduce desktop selection.
2. **Given** the bridge is stopped, **When** config is updated via Web, **Then** desktop Manual override / hub fields reflect the change without requiring a restart of the Web server.
3. **Given** the bridge is running, **When** a change would alter active COM or bind port, **Then** the API rejects or requires stop-first with a clear message (same policy as desktop).

---

### User Story 5 - Documented control parity matrix (Priority: P2)

A maintainer consults a parity document listing every operator-facing control in Standard, Field, and HUD, marking whether it is available via Web in MVP vs later phases.

**Why this priority**: Constitution gate “full parity” is a program, not a single sprint; matrix prevents silent gaps.

**Independent Test**: Parity artifact exists in spec folder; each MVP Web endpoint maps to at least one desktop control; gaps are labeled Phase B/C.

**Acceptance Scenarios**:

1. **Given** the parity matrix, **When** reviewing MVP scope, **Then** Start, Stop, status, and core connection fields are marked **in scope**.
2. **Given** advanced controls (NTRIP, fan-out, TCP sink, UI editor, themes), **When** reviewing MVP, **Then** they are explicitly **deferred** or **read-only** with rationale.
3. **Given** a deferred control, **When** the Web client attempts unsupported action, **Then** the API returns a structured “not supported” response—not a silent no-op.

---

### User Story 6 - Safe Web exposure on survey PCs (Priority: P3)

An operator enables or disables browser access; by default only local machine clients can reach the Web UI; optional LAN bind is documented with firewall guidance.

**Why this priority**: Security/trust on field laptops.

**Independent Test**: Default bind rejects remote host; with LAN mode enabled, second PC on subnet can reach status; with disabled, server does not listen.

**Acceptance Scenarios**:

1. **Given** default settings, **When** a remote machine attempts access, **Then** connection is refused unless LAN exposure is explicitly enabled.
2. **Given** Web server enabled, **When** the operator disables it in settings, **Then** the port closes within 2 s and no background thread leak remains after app exit.

---

### Edge Cases

- Layout file version mismatch after app upgrade → detect and fall back with logged warning.
- Web start requested while COM is locked by another app → same error path as desktop preflight.
- Concurrent Web and desktop start/stop within 500 ms → serialized; final state is consistent; no double bridge instance.
- High-frequency Web status polling (≥ 5 Hz) → server throttles or coalesces; desktop UI frame time unaffected (p95 interaction latency under 100 ms during 5 Hz poll).
- Frozen `.exe` missing `.ui` assets → startup diagnostic names expected bundle path.
- Bridge thread disconnect storm while Web polls status → status remains available; no deadlock on Qt main thread.
- Operator closes laptop lid / sleep → Web server resumes or clean-stops per app lifecycle policy documented in operator guide.

---

## Requirements *(mandatory)*

### Functional Requirements

**Layer 1 — Qt visual layouts**

- **FR-101**: Standard Connect chrome MUST load primary structure from external Qt Designer layout resources at runtime; widget signal/slot wiring MAY remain in Python.
- **FR-102**: Field layout primary survey strip / connection summary MUST load from external layout resources at runtime using the same loading mechanism as Standard.
- **FR-103**: Layout resources MUST ship inside frozen builds beside the executable; dev mode MUST load from the project resource path without recompilation.
- **FR-104**: Missing or corrupt layout resources MUST produce operator-visible failure guidance and MUST NOT leave Connect in a broken silent state.
- **FR-105**: Programmatic layout code for Standard/Field MUST be reduced to wiring, business logic, and fallbacks—not duplicate static widget trees.

**Layer 2 — WebUI bridge**

- **FR-201**: The application MUST expose a machine-readable **status** surface reporting at minimum: bridge running/stopped, active COM, baud, UDP/TCP listen context, NMEA mode, and summarized stats (Hz, drops, rejects).
- **FR-202**: The application MUST expose a machine-readable **config** surface for read and write of core connection fields (COM, baud, listen host/port, NMEA mode, selected hub device id) while stopped or under the same stop-first rules as desktop.
- **FR-203**: The application MUST accept **start** and **stop** commands via the Web API with validation parity to desktop Start/Stop.
- **FR-204**: Web command and query handlers MUST delegate to the same bridge session / mixin configuration layer used by Qt—no duplicate bridge instances.
- **FR-205**: The Web server MUST run on a **background thread** (or equivalent non-Qt-main executor) and MUST NOT block the Qt main event loop during normal polling and command traffic.
- **FR-206**: Web-driven state changes MUST propagate to Qt widgets within 2 s so desktop and browser stay consistent.
- **FR-207**: A **control parity matrix** artifact MUST list desktop controls vs Web availability (MVP / Phase B / out of scope).
- **FR-208**: Unsupported Web actions MUST return explicit errors; silent ignoring of write requests is forbidden.

**Constitution & quality gates**

- **FR-301**: Bridge protocol logic MUST remain in `bridge_core.py` and `nmea_codec.py`; Web and Qt layers MUST NOT embed NMEA assembly or socket I/O.
- **FR-302**: Start/Stop MUST remain discoverable on desktop at launch in Standard and Field after layout migration (Principle II).
- **FR-303**: Substantive changes MUST include automated tests for layout loading, Web API contracts, and thread-safety smoke; `verify_all.py` MUST pass before release.
- **FR-304**: New runtime dependencies for the Web stack MUST be justified in the plan with size and security notes; default install remains bridge-focused.
- **FR-305**: Web status/config polling from the UI layer MUST be rate-limited or coalesced to satisfy Principle V (no stats-event flooding across threads).

**Out of scope (default)**

- Replacing Minimal, Log-first, or HUD layouts with `.ui` files (unless added in plan).
- Kernel drivers, MAVLink planner, GNSS post-processing.
- Public internet exposure, OAuth identity provider, or multi-tenant admin.
- Full SerialTool-grade terminal in the browser (future epic).

### Key Entities

- **LayoutResource**: Identifies a `.ui` (or equivalent) file, version, target mode (standard/field), validation state.
- **WebSessionState**: Snapshot of bridge running, stats summary, last error, last update time (for status endpoint).
- **WebConfigPayload**: COM, baud, network bind, NMEA mode, hub selection, manual-override flag, read-only advanced flags.
- **ControlParityEntry**: Control id, desktop location, Web MVP/phase, notes.
- **WebCommandResult**: ok/error, message, applied state id (for start/stop/config writes).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: A maintainer can change a visible Connect label or spacing via layout files and see the result after app restart in under 3 minutes (no Python rebuild in dev workflow).
- **SC-102**: Standard and Field Start/Stop remain visible at default window size without regression vs v1.6.0 baselines (visual checklist).
- **SC-201**: Web status JSON reflects desktop running/stopped state within **2 s** under normal load.
- **SC-202**: Web start/stop succeeds for valid bench config with **100%** agreement with desktop outcome on a 10-iteration automated bench script.
- **SC-203**: During 5 Hz Web status polling for 60 s while resizing the main window, **p95** UI interaction latency stays under **100 ms** (no stuck resize or frozen Start button).
- **SC-204**: Control parity matrix covers **100%** of Connect **run** and **connection** panel controls with explicit MVP/defer labels.
- **SC-205**: Invalid Web start attempts show the same validation failure class as desktop in **100%** of documented negative test cases.
- **SC-301**: `verify_all.py` and unit tests pass on CI/dev machine after migration (Principle III).

---

## Assumptions

- **Stack proposal for planning** (not binding in this spec): Qt `QUiLoader` (or equivalent) for `.ui`; lightweight HTTP service (e.g., FastAPI) for `/status`, `/config`, start/stop; optional NiceGUI or static HTML dashboard as a thin client over those endpoints—final choice in `plan.md` with dependency justification per FR-304.
- **MVP Web surface**: `/status` (GET), `/config` (GET + PATCH/POST), `/bridge/start` and `/bridge/stop` (POST) or equivalent REST mapping documented in contracts.
- **Binding**: Loopback-only by default; LAN bind opt-in via settings + operator guide firewall note.
- **Authentication MVP**: None on localhost; optional shared token when LAN mode enabled (plan detail).
- **Parity phasing**: MVP covers run + core connection + hub selection; NTRIP, fan-out, TCP sink, themes, UI editor remain desktop-only until Phase B unless plan narrows further.
- **Existing v1.6.0 Connection Hub** behavior is preserved; layout migration refactors container shells, not hub business logic in `discovery_service.py`.
- **Frozen release** ships new layout assets and documents Web port in `docs/OPERATOR_GUIDE.md`.

---

## Dependencies

- Shipped Connection Hub and discovery (004 / v1.6.0).
- Constitution threading rules (asyncio bridge + Qt main).
- Operator guide update for Web port, LAN exposure, and security expectations.
