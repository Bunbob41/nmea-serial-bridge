# Feature Specification: Product Baseline (As-Built)

**Feature Branch**: `2027-baseline-spec`

**Created**: 2026-05-20

**Status**: Approved (baseline reference — documentation delivery complete)

**Input**: User description: "baseline spec"

## Purpose

Capture the **current** NMEA Serial Bridge product behavior as the Spec Kit baseline.
Future features MUST declare what they add, change, or deprecate relative to this document.
This spec describes **what operators can do today**, not a net-new implementation backlog.

**Baseline release referenced**: **Behavior** v1.4.9+ (includes auto-discovery); **doc delivery**
v1.4.10+ (see `version.py`). Frozen exe metadata must match `version.py` via `version_info.txt`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bench bridge session (Priority: P1)

A survey technician on a bench PC connects a com0com pair, loads a desk preset,
starts the bridge, and verifies NMEA flows from a UDP simulator to the paired COM port
while reading the live log and status bar.

**Why this priority**: Bench validation is the gate before any boat or production COM use.

**Independent Test**: With com0com (bridge on one leg, terminal on the paired leg) and a
UDP sender to the listen port, operator completes Start → sees Running → receives NMEA on
the monitor leg within one minute without exclusive-COM errors.

**Acceptance Scenarios**:

1. **Given** a free bridge COM and UDP listen port from a saved preset, **When** the
   operator clicks Start, **Then** status shows serial open and network listening, and
   the session remains interactive under continuous UDP input.
2. **Given** the bridge is Running, **When** the operator clicks Stop, **Then** the
   session ends, COM is released, and a new session can start without restarting the app.
3. **Given** Passthrough NMEA mode, **When** valid sentences arrive from UDP, **Then**
   equivalent line traffic appears toward serial without checksum stripping unless Strict
   mode is explicitly selected.

---

### User Story 2 - Boat / INS UDP listen (Priority: P1)

A field operator connects survey Ethernet (or VPN lab link), loads a boat/production
preset, starts UDP listen on the survey PC, and feeds the vessel INS output into the
designated downstream COM for acquisition software.

**Why this priority**: Primary production value — GNSS/INS on the network to serial target.

**Independent Test**: INS or lab simulator sends UDP to the PC listen address; downstream
COM receives sustained stream; Survey HUD or status bar shows non-zero ingress rate.

**Acceptance Scenarios**:

1. **Given** UDP listen mode and correct bind port, **When** the INS sends datagrams to
   the survey PC, **Then** data is accepted without the bridge dialing outbound to the INS.
2. **Given** a running session, **When** serial output toward the network is produced,
   **Then** registered UDP peers receive it according to fan-out setting (see FR-011).
3. **Given** sustained ingress, **When** downstream consumer slows or disconnects,
   **Then** drop/reject counters increase and remain visible without freezing the UI.

---

### User Story 3 - Survey monitoring and presets (Priority: P2)

An operator loads named presets, switches Standard vs Field layout, opens the Survey HUD,
and uses GNSS quality indicators (fix, satellites, HDOP) to confirm the link is healthy
during a run.

**Why this priority**: Operational confidence during long runs; reduces silent failure risk.

**Independent Test**: Load preset → Start → open HUD → observe GGA-derived quality updating
at least once per minute under live GGA input.

**Acceptance Scenarios**:

1. **Given** saved presets on disk, **When** the operator loads a preset, **Then** COM,
   baud, network mode, ports, NMEA mode, and fan-out preference restore from that preset.
2. **Given** GGA sentences in the stream, **When** the HUD is open, **Then** fix quality
   and related survey fields update without blocking window resize or drag operations.
3. **Given** the operator saves a new preset, **When** they reload it later, **Then** the
   same connection intent is restored across app restarts.

---

### User Story 4 - Multi-client UDP fan-out (Priority: P2)

A bench engineer or integrator runs **one** bridge instance and attaches **multiple** UDP
clients (e.g., simulator + logger). Each client that has sent at least one datagram during
the session may receive serial→network traffic when fan-out is enabled.

**Why this priority**: Documents a common integration pattern; avoids mistaken expectation
of needing a second bridge application.

**Independent Test**: Two UDP clients send to the listen port; with fan-out enabled, both
receive serial-originated datagrams; with fan-out disabled, only the most recent sender does.

**Acceptance Scenarios**:

1. **Given** fan-out enabled and two distinct senders registered, **When** serial produces
   network-bound data, **Then** both sender addresses receive copies for that session.
2. **Given** fan-out disabled, **When** serial produces network-bound data, **Then** only
   the most recent sender receives it.
3. **Given** a peer becomes unreachable, **When** send fails for that peer, **Then** that
   peer is removed from the active set and remaining peers continue receiving.

---

### User Story 5 - Diagnostics and safety modes (Priority: P3)

An operator selects NMEA handling mode, runs packaged diagnostics from the UI, and uses
Raw binary mode only when RTCM or non-NMEA byte streams are required.

**Why this priority**: Prevents misconfiguration that corrupts binary correction data.

**Independent Test**: Switch to Raw → confirm binary path; run verify/checklist from
Diagnostics without losing bridge responsiveness.

**Acceptance Scenarios**:

1. **Given** RTCM or binary input, **When** Raw binary mode is selected, **Then** bytes
   pass through without line assembly or checksum validation.
2. **Given** Strict mode, **When** malformed or filtered sentences arrive, **Then** rejects
   are counted and optionally visible in verbose logging without stopping the bridge.
3. **Given** diagnostics scripts available in the install, **When** the operator launches
   them from the Diagnostics tab, **Then** they receive clear success/failure feedback.

---

### Edge Cases

- COM port already in use by another application → Start blocked or failed with clear
  operator messaging; no silent partial bridge.
- USB serial unplug mid-run → optional auto-reconnect attempts while bridge remains Running;
  operator sees serial status change.
- No UDP sender yet in listen mode → bridge listens; serial→network may send to zero peers
  until first datagram registers a peer.
- TCP client mode peer drops → bridge reconnects with configurable delay (advanced network).
- Queue saturation under burst → drops counted; UI remains responsive.
- Send tab inject → intended for text NMEA only; not a substitute for binary inject paths.
- Frozen portable build → full verify suite may require source tree; operator sees explicit
  message rather than opaque failure.

## Requirements *(mandatory)*

### Functional Requirements

**Bridge session**

- **FR-001**: The product MUST provide bidirectional forwarding between exactly one serial
  COM port and one network endpoint configuration per running session.
- **FR-002**: The product MUST expose Start and Stop controls visible at launch in Standard
  and Field layouts without requiring fullscreen.
- **FR-003**: The product MUST support UDP listen as the default network pattern (bind on
  survey PC; remote devices send in).
- **FR-004**: The product MUST support advanced network modes: UDP remote, TCP server, and
  TCP client (single peer per session for remote/TCP paths).

**Serial**

- **FR-005**: The product MUST let the operator select COM port and baud rate, refresh the
  port list, and optionally enable automatic serial reconnect while the bridge stays Running.
- **FR-006**: The product MUST prevent exclusive COM conflicts from presenting as a healthy
  running bridge when the port cannot be opened.

**NMEA and data integrity**

- **FR-007**: The product MUST offer NMEA Passthrough, Strict (checksum + filter), and Raw
  binary modes selectable per session.
- **FR-008**: In Raw binary mode, the product MUST forward bytes unchanged without NMEA line
  assembly on the bridged paths.
- **FR-009**: The product MUST maintain bounded queues with visible drop and reject counters.

**Presets and persistence**

- **FR-010**: The product MUST support named presets that persist COM, network, NMEA mode,
  and fan-out preference across sessions.

**UDP fan-out (listen mode)**

- **FR-011**: In UDP listen mode with fan-out enabled (default), the product MUST deliver
  serial→network data to every UDP sender that has contacted the bridge during the current
  session.
- **FR-012**: In UDP listen mode with fan-out disabled, the product MUST deliver
  serial→network data only to the most recent UDP sender.
- **FR-013**: The product MUST clear the registered peer set when the session stops.

**Operator surfaces**

- **FR-014**: The product MUST provide Standard and Field UI layouts plus an optional Survey
  HUD popout for live rates and GNSS quality.
- **FR-015**: The product MUST provide a throttled live log with optional verbose sentence view
  for text modes.
- **FR-016**: The product MUST provide a Send path for operator text inject with normalized
  line endings (not for arbitrary binary injection).
- **FR-017**: The product MUST ship operator documentation suitable for bench and boat setup.

**Diagnostics**

- **FR-018**: The product MUST expose diagnostics entry points (checklists, burst/stress
  helpers, verification guidance) from the UI where the install supports them.

**Auto-discovery (v1.4.9+)**

- **FR-021**: The product MUST optionally watch USB-serial ports for survey GNSS adapters and,
  when enabled by the operator, auto-select the detected COM port and auto-start the bridge
  when configuration validates. Detection MUST use a stability guard (consecutive polls) to
  avoid false triggers during USB enumeration churn, and MUST reset after device absence so
  reconnecting the same cable can trigger again.

**Out of scope (baseline)**

- **FR-019**: The baseline product does NOT provide kernel virtual COM, passive kernel sniff,
  arbitrary N×M serial routing, GNSS post-processing, or vehicle mission planning.
- **FR-020**: The baseline product does NOT require a second bridge instance to test UDP
  fan-out; multiple UDP clients to one listen port are sufficient.

### Key Entities

- **Bridge session**: One Running interval binding one COM configuration to one network
  mode; owns queue counters and UDP peer registry for that interval.
- **Preset**: Named saved operator intent (COM, baud, network, NMEA mode, fan-out flag).
- **UDP peer**: Distinct sender address (host and port) registered during a listen-mode session.
- **Drop / reject counters**: Evidence of backpressure or strict-mode filtering; shown in status
  and HUD.
- **Survey quality snapshot**: Latest GGA-derived fix/sat/HDOP state for operator assurance.
- **Auto-discovery watcher**: Background poll of serial port list; optional auto-connect policy
  driven by operator checkbox and `ui_prefs.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new team member can locate Start/Stop, COM, UDP port, and preset load in
  under 3 minutes on first launch using Standard layout without external coaching.
- **SC-002**: Bench operators can complete a com0com + UDP simulator happy-path test in under
  15 minutes using only the operator guide and in-app Diagnostics hints.
- **SC-003**: Under sustained 5 Hz NMEA ingress in Passthrough mode, the UI remains interactive
  (resize, Stop, HUD open/close) for a 30-minute observation window without deadlock.
  Validated per [sc003-hud-stress-validation.md](./sc003-hud-stress-validation.md).
- **SC-004**: With two UDP clients registered and fan-out enabled, both clients receive
  serial-originated traffic within 5 seconds of serial activity starting.
- **SC-005**: 100% of baseline functional requirements (FR-001 through FR-021) map to at
  least one acceptance scenario, edge case, or traceability row for future plans.
- **SC-006**: Future feature specs explicitly state which FR IDs they extend, modify, or
  supersede when opened against this baseline.

## Assumptions

- Primary users are survey technicians and integrators on Windows 10+ field or bench PCs.
- Downstream acquisition software consumes the bridged COM port; the bridge does not replace
  that software.
- Bench testing uses com0com or physical serial; boat testing uses INS/GNSS sending UDP to
  the survey PC listen address.
- Network configuration (MikroTik, Tailscale, firewall) is operator responsibility outside
  the app.
- Baseline documentation may lag README marketing copy; CHANGELOG and operator guide take
  precedence for fan-out and v1.4.x behavior when they differ from older README bullets.
- This baseline spec ratifies as-built behavior; it does not require **bridge protocol**
  changes. Documentation, metadata sync, and bench validation procedures are in scope for
  cleanup features (see `specs/002-baseline-version-sync/`).
- **Fan-out UI**: checkbox on Standard **Connect → Run**; Field layout uses **Tools → Presets**
  (Advanced) for the same settings.
