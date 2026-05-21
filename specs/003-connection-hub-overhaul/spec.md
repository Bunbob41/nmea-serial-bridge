# Feature Specification: Connection Hub Overhaul

**Feature Branch**: `2030-connection-hub-overhaul`

**Created**: 2026-05-20

**Status**: Draft

**Input**: Unified UI and architecture overhaul — Connection Hub, discovery service, TCP sink.

**Extends**: [`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md) (FR-001–FR-021, SC-003/004)

**Governance**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Principles I (Bridge-Core Separation), II (Operator Trust), III (Verifiable Changes), V (Resilience).

---

## Current Architecture Audit (integration hooks)

*Read-only survey of today’s code — informs plan/tasks; not implementation.*

### Bridge engine (`bridge_core.py`)

| Area | Today | Hook for overhaul |
|------|--------|-------------------|
| **Net egress** | `_send_net()` — UDP fan-out via `_udp_peers` or single `last_udp_addr`; TCP via one `tcp_writer` | Add **parallel TCP sink** path (separate listener/writers), invoked from same `_pump_serial_to_net_queue` after primary send; must not block primary path |
| **Net ingress** | `on_udp_datagram()` registers peers; TCP accept/client tasks | Unchanged primary mode; sink is outbound mirror only |
| **Session** | `SerialNetBridge.start()` / `abort_now()`; bounded queues | Sink lifecycle tied to Running; teardown clears sink clients |
| **Qt leakage** | Imports `PySide6.QtCore` (existing) | New discovery logic MUST NOT add QWidget; prefer pure-Python service module |

### Auto-discovery (`auto_discovery.py` + `ui/mixin.py`)

| Area | Today | Hook for overhaul |
|------|--------|-------------------|
| **Scanner** | `AutoDiscoveryThread(QThread)` — 2 s poll, GNSS keyword match, `device_detected(str)` | **Promote** to first-class **DiscoveryService** (serial scan API + network snapshot API) |
| **UI coupling** | Mixin starts/stops thread in `_finalize_ui` / `closeEvent`; checkbox `chk_auto_discover` in `controls.py` | Hub consumes **discovery state** (list of device cards); auto-start remains opt-in |
| **Persistence** | `ui_prefs.json` auto-discover flag only | Extend with **per-device last-known-good** (baud, mode, port) keyed by stable device id |

### Connect UI (`ui/connect_panels.py`, `ui/controls.py`, `ui/standard.py`)

| Area | Today | Hook for overhaul |
|------|--------|-------------------|
| **Layout** | Scrollable collapsible panels: `run`, `connection` (required), `hint`, `quick_log`, `terminal`, `ntrip` | Replace **connection** panel body with **Connection Hub** card grid; keep `run` (Start/Stop) visible per constitution |
| **Widgets** | `com_cb`, `baud_edit`, `udp_host/port`, mode radio group, `chk_udp_fanout`, advanced TCP fields in `controls.py` | Cards select endpoints; **Manual override** reveals today’s fields |
| **Config build** | `BridgeLogicMixin._start_bridge()` (~L3555) reads widgets → `SerialNetBridge(...)` | Hub selection → same config dict; presets gain device-id keys |
| **Field layout** | `ui/field.py` — strip + Tools drawer | Hub must expose equivalent selection or deep-link to Connect hub |

### Presets & paths (`ui/mixin.py`, `path_presets.json`)

| Area | Today | Hook |
|------|--------|------|
| **Load/save** | `_apply_preset_data` sets COM, baud, network, fan-out | Map preset ↔ selected card; store last-good per `device_id` |

### Legacy stability constraints

- Do **not** remove UDP fan-out or single-link toggle (FR-011/012).
- Keep asyncio on **background thread**, Qt on **main thread** (constitution).
- Start/Stop remain on Connect **run** panel (not buried in hub).
- Standard + Field layouts must remain launchable without fullscreen.

---

## Purpose

Modernize survey **setup** into a **Connection Hub**: auto-detected Serial and Network endpoints as cards, cached per-device defaults, manual override for edge cases, and a formal **discovery service** feeding the Qt UI. Add an optional **TCP sink** mirroring serial→network traffic concurrently with existing UDP fan-out (separate stream, not a replacement).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick a detected GNSS serial card (Priority: P1)

An operator plugs in a Trimble USB adapter; the Connection Hub shows a **Serial** card with port name and last-known baud. One click selects it; Start uses that COM without scrolling dropdowns.

**Why this priority**: Replaces highest-friction desk setup step.

**Independent Test**: Plug/unplug USB device; card appears/disappears; selecting card sets COM; bridge starts with cached baud.

**Acceptance Scenarios**:

1. **Given** a matching GNSS USB device, **When** the hub refreshes, **Then** a Serial card appears with port label and suggested baud.
2. **Given** a selected Serial card, **When** the operator clicks Start, **Then** bridge opens that COM at cached or default 115200 baud.
3. **Given** manual override toggled, **When** the operator edits baud/COM, **Then** override values win over card defaults.

---

### User Story 2 - Pick network listen from discovered context (Priority: P1)

An operator sees **Network** cards for UDP listen (bind address/port status, recent peer count) and can select primary bridge mode without expanding advanced TCP unless needed.

**Why this priority**: Boat/bench workflows center on UDP listen + fan-out (baseline FR-003, FR-011).

**Independent Test**: Start bridge UDP listen; send datagram; card shows peer count; fan-out behavior unchanged.

**Acceptance Scenarios**:

1. **Given** UDP listen mode, **When** a sender registers, **Then** the network card reflects peer count or “listening on port N”.
2. **Given** a saved preset with host/port, **When** no active session, **Then** card shows preset endpoint as selectable template.
3. **Given** primary mode UDP listen, **When** serial→net traffic flows, **Then** existing fan-out rules apply unchanged.

---

### User Story 3 - Manual override for edge cases (Priority: P2)

An integrator uses com0com, non-GNSS USB, or custom TCP client — they open **Manual override** to access full legacy fields (mode picker, TCP advanced, fan-out checkbox).

**Why this priority**: Survey reality requires escape hatch without blocking happy path.

**Independent Test**: Toggle override → all current `controls.py` fields available; preset save/load still works.

**Acceptance Scenarios**:

1. **Given** override collapsed, **When** operator has unusual COM, **Then** they can expand override and set COM/baud/mode explicitly.
2. **Given** override settings, **When** saved as preset, **Then** reload restores override state.

---

### User Story 4 - TCP sink mirror alongside UDP fan-out (Priority: P2)

An operator enables **TCP sink** on a secondary port; serial→network bytes are mirrored to connected TCP clients while primary UDP listen fan-out continues independently.

**Why this priority**: Software tap for loggers/analyzers without second bridge (Argo sandbox theme).

**Independent Test**: Bridge Running UDP fan-out + TCP sink enabled; UDP peers and TCP client both receive same serial-originated burst.

**Acceptance Scenarios**:

1. **Given** TCP sink enabled on port P, **When** a client connects, **Then** it receives serial→net mirror traffic.
2. **Given** UDP fan-out with two peers, **When** TCP sink active, **Then** UDP peers still receive traffic (no regression).
3. **Given** TCP sink disabled, **When** session runs, **Then** behavior matches baseline (no extra listeners).

---

### User Story 5 - Field layout and HUD still operable (Priority: P2)

A field operator using **Field** layout can reach connection intent (via hub or compact strip), Start/Stop, and HUD without regression.

**Why this priority**: Constitution II — all modes must stay trustworthy.

**Independent Test**: Launch Field → select connection → Start → open HUD → resize 5 min with traffic.

**Acceptance Scenarios**:

1. **Given** Field layout, **When** launched at 1280×720, **Then** Start/Stop visible without opening Tools drawer.
2. **Given** Running session, **When** HUD opened, **Then** rates/drops update under load.

---

### Edge Cases

- Device unplugged while selected → hub marks card stale; Start blocks with clear message.
- USB enumeration churn → stability guard (≥2 consecutive polls) before card appears (extends FR-021).
- TCP sink port in use → Start blocked or sink disabled with explicit error (like COM exclusivity FR-006).
- OpenCPN or other app holding UDP port → network card shows “port in use” (align traceability waivers).
- Override + card selection conflict → override wins when expanded and dirty.
- Stop/abort → discovery continues; peer registry and sink clients cleared per session.

## Requirements *(mandatory)*

### Functional Requirements

**Discovery service (backend)**

- **FR-301**: A **DiscoveryService** (non-UI module) MUST expose serial device snapshots (port, description, stable id, match reason) on a poll interval.
- **FR-302**: DiscoveryService MUST expose network snapshots: primary mode hint, bind host/port, listen availability, active UDP peer count when bridge Running.
- **FR-303**: DiscoveryService MUST apply stability guards before promoting serial devices (compatible with FR-021).
- **FR-304**: UI MUST consume discovery state via thread-safe signals or polled snapshots — no serial protocol logic in `ui/` widgets.

**Connection Hub (UI)**

- **FR-305**: Standard Connect MUST present a **Connection Hub** card layout replacing scroll-heavy serial/network form as the default path.
- **FR-306**: Each card MUST represent one selectable endpoint (Serial or Network) with status chip (ready / stale / in use).
- **FR-307**: **Manual override** MUST provide access to all legacy connection fields without removing them.
- **FR-308**: Last-known-good baud, network mode, host, and port MUST persist per `device_id` and restore when the card is re-selected.
- **FR-309**: Start/Stop MUST remain on the **run** panel, visible at launch (extends FR-002).

**TCP sink**

- **FR-310**: Operator MUST be able to enable an optional **TCP sink** that mirrors serial→network bytes to accepted TCP clients on a configured port.
- **FR-311**: TCP sink MUST operate **concurrently** with primary network mode; UDP fan-out (FR-011) MUST NOT be degraded when sink is on.
- **FR-312**: TCP sink MUST use bounded resources; failed sink clients MUST be pruned without stopping the bridge.

**Constitution & baseline**

- **FR-313**: Bridge protocol changes MUST live in `bridge_core.py` / `nmea_codec.py`; hub is presentation and config only (Principle I).
- **FR-314**: Feature MUST ship automated tests and pass project verification (Principle III).
- **FR-315**: Version and CHANGELOG MUST be updated on release (Principle IV).

**Modifies baseline**: FR-021 (elevated to service); adds FR-310–312. Does not remove FR-011–013.

### Key Entities

- **DiscoverySnapshot**: Timestamped serial[] + network[] + errors[] for UI render.
- **EndpointCard**: UI model: type (serial|network), device_id, display_name, status, selected flag.
- **LastKnownGood**: Per device_id: baud, net mode, hosts/ports, fan-out, tcp_sink_enabled.
- **TcpSinkSession**: Optional parallel listener + set of client writers; mirror of serial→net egress.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-301**: Operator selects a detected GNSS serial card and starts bridge in **under 60 seconds** on first bench visit (vs baseline SC-001 3 min for locating controls).
- **SC-302**: With TCP sink + UDP fan-out enabled, **two UDP peers and one TCP client** all receive serial-originated data within **5 seconds** of serial activity (extends SC-004).
- **SC-303**: Field layout Start/Stop + HUD path completes without UI deadlock in **15-minute** smoke (abbreviated SC-003).
- **SC-304**: **100%** of new FR-301–315 covered by unit tests or documented manual procedure in plan quickstart.
- **SC-305**: `verify_all.py` and full unittest suite pass on clean bench (or documented waivers updated).

## Assumptions

- **Network discovery v1** is **passive/contextual**: preset templates, bind-port availability, running-session peer counts — not full LAN scanning or mDNS (deferred).
- **TCP sink v1** is **TCP server mirror** (clients connect to bridge PC); bridge does not open multiple outbound TCP clients unless later specified.
- **One primary NetMode** per session remains (baseline FR-001); sink is additive.
- Phased delivery: P1 = hub + serial discovery; P2 = network cards + TCP sink; Field parity in P2.
- Existing presets remain importable; migration adds `device_id` optionally.

## Out of Scope

- Kernel virtual COM, passive kernel sniff, arbitrary N×M routers (FR-019).
- Replacing Survey HUD, NMEA tab, or Diagnostics tab layout.
- Removing collapsible Connect panels entirely (run/hint/ntrip may remain).

## Dependencies

- Baseline spec and traceability (`001-baseline-spec`).
- Existing `auto_discovery.py` behavior and `test_auto_discovery.py` as regression anchor until migrated.
