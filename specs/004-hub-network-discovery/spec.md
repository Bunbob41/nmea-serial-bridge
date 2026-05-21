# Feature Specification: Connection Hub Phase 2 — Responsive Layout & Network Discovery

**Feature Branch**: `2031-hub-network-discovery`

**Created**: 2026-05-20

**Status**: Draft

**Input**: Connection Hub Overhaul & Network Discovery Service — resizable card hub, active network discovery, smart port release, traffic quality in hub.

**Builds on**: [`specs/003-connection-hub-overhaul/spec.md`](../003-connection-hub-overhaul/spec.md) (shipped v1.5.0–1.5.1: passive discovery, card hub, manual override, TCP sink, last-known-good)

**Baseline**: [`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md)

**Governance**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Principles I (Bridge-Core Separation), II (Operator Trust), III (Verifiable Changes), V (Resilience & Bounded Resources).

---

## Purpose

Survey operators still fight **clipped, scroll-heavy** Connect layouts and **opaque port locks** after a failed start or crash. Phase 1 centralized setup in a Connection Hub with **passive** serial and UDP-context cards; Phase 2 makes the hub **responsive and resizable**, adds **active LAN discovery** for network endpoints, **one-click port recovery**, and **live traffic-quality signals** on cards—without moving bridge protocol logic into Qt widgets.

---

## As-Built vs This Epic

| Capability | Phase 1 (003 / v1.5.x) | Phase 2 (this spec) |
|------------|------------------------|---------------------|
| Serial GNSS cards | Passive USB scan + stability guard | Same + standardized controls on cards |
| Network cards | UDP listen template, port probe, peer count | **+ Active LAN discovery** (ARP/broadcast-derived devices) |
| Connect layout | Hub inside scrollable Connect panel | **Responsive hub layout**, reduced clipping |
| Port recovery | Manual Refresh + operator docs | **Smart Release** + single **Unlock / Refresh** action |
| Traffic quality | Status bar / HUD | **Quality chips on hub cards** |
| Discovery architecture | `discovery_service.py` (no Qt) | **+ Background network scanner service** |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resizable connection hub without clipping (Priority: P1)

An operator opens Connect on a laptop or secondary monitor. The Connection Hub shows serial and network cards in a **resizable grid**; port names and status chips remain readable without nested micro-scroll areas.

**Why this priority**: Directly addresses “tiny, clipped port lists” and daily setup friction.

**Independent Test**: Resize Connect panel and main window between 900×380 and 1400×900; cards reflow; no required horizontal scroll for primary card content; COM labels remain fully visible.

**Acceptance Scenarios**:

1. **Given** Standard Connect at minimum window size, **When** the connection panel is expanded, **Then** at least one serial and one network card are fully visible without opening Manual override.
2. **Given** the operator drags the Connect vertical splitter, **When** the connection section grows, **Then** the hub card area grows proportionally and cards use available width (multi-column when wide).
3. **Given** many detected endpoints, **When** the hub exceeds visible height, **Then** only the **card grid** scrolls—not the Run panel or Start/Stop row.

---

### User Story 2 - Unified serial + network cards with one refresh (Priority: P1)

An operator sees **Serial** and **Network** devices in one hub. A single **Refresh discovery** control re-runs serial enumeration and network scan; hung COM ports can be released without restarting the app.

**Why this priority**: Centralizes setup and recovery per user stories.

**Independent Test**: Click Refresh; serial list updates; network cards update within SLA; **Unlock ports** clears a stuck COM after simulated lock.

**Acceptance Scenarios**:

1. **Given** a GNSS device is connected, **When** Refresh runs, **Then** its serial card appears or updates within 5 seconds.
2. **Given** a device on the LAN emits survey traffic or answers discovery, **When** Refresh completes, **Then** a Network card appears with address, port hint, and reachability status.
3. **Given** COM open failed with “in use”, **When** the operator clicks **Unlock / Refresh ports**, **Then** the app attempts smart release and reports success or a clear next step within 3 seconds.

---

### User Story 3 - Active network discovery on the survey LAN (Priority: P2)

An operator on a boat or desk LAN wants the hub to **suggest** INS/GNSS UDP sources (e.g., Trimble, generic NMEA listeners) without hand-entering every IP.

**Why this priority**: Reduces mis-typed UDP targets; builds on passive cards from phase 1.

**Independent Test**: Bench LAN with two UDP senders; Refresh shows distinct network cards; selecting a card pre-fills listen/send fields.

**Acceptance Scenarios**:

1. **Given** hosts on the local subnet, **When** network scan runs, **Then** at least one Network card is produced from discovery data (not only the static UDP listen template).
2. **Given** a selected Network card, **When** applied to configuration, **Then** host/port/mode fields match the card metadata before Start.
3. **Given** scan finds no peers, **When** Refresh completes, **Then** the hub still shows the default UDP listen card and an empty-state hint.

---

### User Story 4 - Traffic quality visible on hub cards (Priority: P2)

While the bridge is Running, the operator glances at the hub and sees whether each path is **healthy** (Hz band, drops, stale NMEA) without opening the HUD.

**Why this priority**: Observability at the connection decision point.

**Independent Test**: Run bridge with `bench_udp_test.py`; selected serial/network cards show updating quality chips; after Stop, chips return to idle.

**Acceptance Scenarios**:

1. **Given** bridge Running with steady NMEA, **When** stats update, **Then** the active card shows a healthy indicator (e.g., green / “OK” / Hz in range).
2. **Given** backpressure or rejects, **When** counters increase, **Then** the card shows warning state within one stats refresh cycle (≤ 2 s).
3. **Given** strict mode rejects, **When** reject count rises, **Then** the card distinguishes **drops** vs **rejects** in tooltip or subtitle.

---

### User Story 5 - Standardized connection controls (Priority: P3)

Baud, port, and mode controls look and behave the same whether editing from a **card**, **Manual override**, or **Field** strip.

**Why this priority**: Reduces operator error; supports FR-403.

**Independent Test**: Change baud on card vs override; same validation rules; invalid baud blocks Start with same message.

**Acceptance Scenarios**:

1. **Given** any entry point for baud, **When** the operator enters an invalid value, **Then** Start is blocked with one consistent error message.
2. **Given** a serial card selection, **When** baud is changed on the card, **Then** Manual override and Field strip reflect the same value.

---

### Edge Cases

- USB enumeration churn: serial cards must not flicker off between polls; stability guard retained from phase 1.
- Multiple identical USB devices: cards distinguish by stable device id (HWID or port path).
- Network scan on VPN-only or offline PC: scan completes with serial + default UDP card only; no UI freeze.
- ARP table stale entries: cards show “stale” or last-seen age; operator can ignore or override.
- Bridge Running during Refresh: scan does not restart bridge; network scan does not bind exclusive UDP listen port.
- Smart Release while bridge Running: must not yank the active bridge COM without Stop confirmation.
- Field layout: hub may be summary-only, but Refresh/Unlock must remain reachable within two clicks.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-401**: Connect **connection** experience MUST use a responsive layout where the Connection Hub card grid receives primary vertical space and avoids nested clipping of COM/port labels at minimum supported window size.
- **FR-402**: The hub MUST present **card-based** connection objects for **Serial** and **Network** device types with selection, status chip, and consistent minimum card size.
- **FR-403**: Baud rate, port/host, and mode selectors MUST use **standardized validation and labeling** across hub cards, Manual override, and Field compact strip.
- **FR-404**: A **background network discovery** capability MUST identify candidate survey endpoints on the local LAN by combining **ARP / neighbor-table** host discovery with **bounded UDP broadcast probes** on default survey ports (e.g., 10110, 4001, 10111 sink), then emit Network cards without blocking the UI thread. Probes MUST time out per host and MUST NOT bind the bridge’s active UDP listen port while Running.
- **FR-405**: **Smart Release** MUST attempt safe teardown of stale COM (and documented UDP bind conflicts where applicable) when the operator invokes **Unlock / Refresh ports**, and MUST NOT release the active bridge COM while Running without explicit Stop.
- **FR-406**: **Traffic quality metrics** (Hz bands, drops, rejects, optional GNSS fix staleness) MUST flow from bridge stats into hub card subtitles or chips while Running.

### Architecture & Constitution (binding)

- **FR-407**: Discovery and network scanning logic MUST live outside QWidget-heavy mixins (dedicated service modules); UI only binds to snapshots and signals.
- **FR-408**: Serial and network scan work MUST run on **background threads** or async tasks; main-thread work per refresh MUST stay under interactive UI budgets (see SC-402).
- **FR-409**: Every layout, discovery, smart-release, and metrics binding change MUST include **automated unit tests**; bench procedures documented in quickstart.
- **FR-410**: Start/Stop MUST remain on the Connect **run** panel; required Connect sections `run` and `connection` unchanged.

### Key Entities

- **ConnectionCard**: Unified card model (serial | network) with `device_id`, title, subtitle, status, optional quality snapshot, last_seen.
- **DiscoverySnapshot**: Point-in-time serial + network card lists, scan errors, monotonic timestamp (extends phase 1).
- **NetworkScanResult**: Host address, discovery method, open/reachable port hints, label, confidence/stale flag.
- **PortLockState**: COM port, lock reason, whether smart release is safe, last attempt result.
- **TrafficQualitySnapshot**: Hz up/down, drops, rejects, optional fix age; mapped to active card(s).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-401**: On a 900×380 window, an operator can read full COM text on the selected serial card without horizontal scrolling in the hub.
- **SC-402**: During a full discovery refresh (serial + network), the Connect UI remains interactive (operator can click Stop or another tab) with no perceptible freeze exceeding 200 ms on the main thread.
- **SC-403**: After a simulated COM lock (external app holding port), **Unlock / Refresh ports** restores ability to Start on that COM in ≥ 80% of bench trials without app restart.
- **SC-404**: With two UDP senders on the LAN, Refresh produces distinguishable Network cards and Start routes traffic per selected card configuration.
- **SC-405**: While bridge Running at ≥ 1 Hz NMEA, the active hub card quality indicator updates within 2 s of a bench-induced drop burst.
- **SC-406**: `python verify_all.py` and full `unittest` suite pass after implementation; new tests cover FR-401–406 behaviors.

---

## Assumptions

- **Platform**: Windows 10+ primary; network discovery uses OS APIs (ARP/neighbor table, optional UDP broadcast) — no kernel driver or passive kernel sniff.
- **LAN scope**: Discovery targets the **local routed subnet** of the survey PC’s active NIC, not internet-wide scanning.
- **Network discovery (Q1: B)**: Use ARP/neighbor table for host inventory, then optional UDP broadcast probes on survey-default ports to detect INS/GNSS listeners; probe budget and timeouts are fixed in the plan (no unbounded scan).
- **Security**: Discovery is read-only/probe-only; no credential harvesting or port scanning beyond survey-relevant UDP/TCP hints (e.g., 10110, 4001, 10111 sink).
- **Phase 1 code** remains; this epic **extends** rather than rewrites `discovery_service.py` and `ui/connection_hub.py`.
- **60 fps** interpreted as: no main-thread blocking during enumeration; heavy work offloaded (constitution-aligned), not literal frame pacing measurement in CI.
- **Field layout** may show hub summary + link to Standard Connect unless full card grid is explicitly requested later.

---

## Out of Scope

- Kernel virtual COM, passive kernel sniff, arbitrary N×M serial routers.
- MAVLink planners, GNSS post-processing, cloud device inventory.
- Full SerialTool terminal parity or multi-pane charting IDE.
- Cross-platform mobile UI.

---

## Implementation Notes (for planning only)

*Non-normative hooks for `/speckit-plan` — not acceptance criteria.*

- Audit `ui/standard.py`, `ui/field.py`, `ui/connect_panels.py` for scroll vs splitter geometry.
- Extend `discovery_service.py` → `network_scanner.py` (or module) for ARP/broadcast; keep Qt in `ui/connection_hub.py` binding-only.
- Smart Release coordination with `bridge_core.py` / `com_free.py` patterns and `BridgeLogicMixin.start_bridge` / `stop_bridge`.
- Quality metrics: reuse `_stats_from_bridge` merged stats and navigation quality helpers.
