# Feature Specification: Web Config Editor & Desktop UX Fixes

**Feature Branch**: `007-web-config-desktop-ux`

**Created**: 2026-05-22

**Status**: Draft

**Input**: Extend the operator web dashboard so configuration is editable (COM port, network mode, destination, port)—not read-only. Add optional QR code generation for the API token so remote devices without clipboard can obtain the token as plain text. Fix Standard layout: broken COM dropdown and non-resizable Connect tab. Fix Field layout: clipped text in Guide → Web control section on launch (violates no-clipping UI rule). Discovery improvements remain out of scope (backseat).

**Governance**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Principles I (bridge-core separation), II (operator trust), III (verifiable changes), V (resilience). Web UI remains a thin REST client; no NMEA/socket logic in `web/static/`.

**Builds on**: Phase B dashboard ([`specs/006-phase-b-dashboard/spec.md`](../006-phase-b-dashboard/spec.md), v1.8.x); Hybrid Web API ([`specs/005-hybrid-ui-webui/spec.md`](../005-hybrid-ui-webui/spec.md)).

---

## Purpose

Operators can now **control** the bridge from the phone dashboard (v1.8.4), but they still cannot **reconfigure** COM or network bind without returning to the desktop app. Remote crews on tablets often lack reliable copy/paste for LAN tokens. Separately, two desktop regressions undermine daily survey use: Standard Connect ergonomics (COM picker, panel resize) and Field Guide layout clipping on first open.

This epic closes the **configuration parity** gap on the web dashboard, improves **token handoff** for remote devices, and restores **desktop layout quality** per project UI polish rules (no clipping, resizable Connect, working COM dropdown).

---

## Scope Boundaries

| In scope | Out of scope |
|----------|----------------|
| Editable web config: COM, network mode, host/port fields | Full discovery UX overhaul (deferred; backseat) |
| QR display for API token (opt-in checkbox) | NTRIP, fan-out, TCP sink, presets write via web |
| Field Guide Web control clipping fix | HUD, theme editor, UI editor dialog |
| Standard COM dropdown repair | Kernel virtual COM, new network discovery algorithms |
| Standard Connect tab resize (splitters / min heights) | Log-first / minimal layout parity unless same root cause |

---

## Clarifications

### Defaults (no blocking questions)

- **QR payload**: Encodes the **raw API token string** only (not a URL), so any camera-based QR app can paste into the dashboard token field or a notes app. Optional caption shows the token in plain text beside the QR for manual entry.
- **Network modes on web**: **udp_listen**, **udp_remote**, **tcp_client**, **tcp_server**—matching desktop advanced network modes exposed in `PATCH /config` / desktop parity matrix.
- **Running guard**: Same as 005—COM, baud, and network bind fields are **read-only while bridge is running**; UI explains “Stop bridge first” with the same message class as desktop.
- **Baud on web**: Included in editable config (paired with COM); validation matches desktop.

---

## As-Built vs This Epic

| Capability | Today (v1.8.4) | This epic |
|------------|----------------|-----------|
| Web config panel | Read-only summary from `GET /config` | **Editable** form; saves via `PATCH /config` |
| COM change from web | Discovery row select only | **Dropdown or text** + discovery list |
| Network mode / host / port | Display only | **Mode selector** + conditional host/port fields |
| API token handoff | Copy button on desktop; paste on phone | **Optional QR** on dashboard (+ desktop Guide optional) |
| Field Guide Web box | Clipped labels/rows at default window size | **Fully readable** at launch sizes |
| Standard COM combo | Reported broken (empty/wrong/stuck) | **Lists ports, selection sticks, applies to bridge** |
| Standard Connect tab | Not resizable per user | **User-resizable** sections with persisted sizes |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Edit bridge configuration from the web dashboard (Priority: P1)

As a field operator on a phone or second screen, I need to change the COM port and network mode (UDP/TCP, host, port) from the dashboard so I do not have to walk back to the survey PC for every cable swap or IP change.

**Why this priority**: Configuration parity is the main gap after working Start/Stop; without it the dashboard is monitor-only.

**Independent Test**: With bridge **stopped**, open dashboard, change COM to an available port and UDP port, save, confirm `GET /config` and desktop Connect fields match; Start bridge and verify traffic uses new settings.

**Acceptance Scenarios**:

1. **Given** the bridge is stopped, **When** I change COM port on the dashboard and save, **Then** the new port appears in config readback and desktop COM field without restart.
2. **Given** the bridge is stopped, **When** I switch network mode to TCP client and enter host/port, **Then** saved config matches desktop advanced network selection.
3. **Given** the bridge is **running**, **When** I attempt to change COM or network bind, **Then** the UI blocks the save and shows a clear “stop bridge first” message (409 / running_guard parity).
4. **Given** invalid baud or port, **When** I save, **Then** validation errors appear inline (same operator-facing class as desktop).

---

### User Story 2 - Scan API token via QR on remote devices (Priority: P2)

As an operator on a tablet that cannot easily copy from the PC, I need to scan a QR code to obtain the API token as plain text so I can paste or type it into the dashboard without using the desktop clipboard.

**Why this priority**: LAN/Tailscale workflows already require a token; QR removes friction for rugged tablets and remote viewers.

**Independent Test**: Enable LAN + token on PC, open dashboard, check “Show QR for token”, scan with phone camera or QR app, confirm decoded text matches token; paste into token field and successfully Start bridge.

**Acceptance Scenarios**:

1. **Given** LAN mode requires a token, **When** I enable “Show QR for API token” on the dashboard, **Then** a scannable QR and human-readable token copy are visible.
2. **Given** QR is shown, **When** a standard QR scanner reads it, **Then** the decoded content is **exactly** the API token string (no extra URL wrapper required).
3. **Given** QR is hidden (checkbox off), **When** I view Tools, **Then** no QR is rendered (token field may still be used for manual paste).
4. **Given** no token is configured on the server, **When** I open QR option, **Then** the UI explains to generate a token on the desktop Guide first.

---

### User Story 3 - Field layout: no clipped Guide Web control text (Priority: P1)

As a Field-layout operator, when I open Tools → Guide, the Web control section (Enable Web API, port, LAN, API token) must be fully readable without vertical clipping of labels or inputs.

**Why this priority**: Violates explicit project UI rule (“no clipping”); visible in v1.8.4 screenshot at default launch size.

**Independent Test**: Launch Field layout at default window size (~1024×768 or common laptop), open Guide, verify every row in Web control group box shows full text and controls (no cut-off ascenders/descenders).

**Acceptance Scenarios**:

1. **Given** Field layout at default restored size, **When** Guide tab is selected, **Then** all Web control rows (checkboxes, port spin, token field, buttons, hint) are fully visible without overlap or clip.
2. **Given** window height is reduced to minimum usable Field size, **When** Guide is open, **Then** the Web control area scrolls or expands rather than clipping text.
3. **Given** DPI scaling 125–150%, **When** Guide is opened, **Then** text remains readable and unclipped.

---

### User Story 4 - Standard layout: working COM dropdown (Priority: P2)

As a Standard-layout operator, I need the COM port dropdown on the Connect tab to list available ports, accept selection, and reflect the chosen port in bridge configuration—not appear empty, stuck, or non-functional.

**Why this priority**: COM selection is P0 survey workflow; broken dropdown blocks connect-first flow.

**Independent Test**: Launch Standard layout, Connect tab, click COM dropdown—ports appear after refresh; select COM7 (or bench pair); selection persists; Start uses selected port.

**Acceptance Scenarios**:

1. **Given** USB serial devices are connected, **When** I open the COM dropdown, **Then** at least one port name is listed (or a clear “no ports” state).
2. **Given** I select a port, **When** I click away or reopen the dropdown, **Then** the same port remains selected.
3. **Given** I click Refresh ports, **When** a new adapter appears, **Then** the list updates without freezing the UI.
4. **Given** web dashboard sets COM via `PATCH /config`, **When** I return to Standard Connect, **Then** the dropdown shows the same port.

---

### User Story 5 - Standard layout: resizable Connect tab (Priority: P2)

As a Standard-layout operator, I need to resize Connect sections (e.g. hub vs connection vs run panel) using splitters or equivalent handles so I can see hub cards and COM row on one screen without clipping.

**Why this priority**: Connect tab resize was requested alongside COM fix; aligns with layout-canvas rule (panel heights via splitters, reset sizes).

**Independent Test**: Standard layout, Connect tab—drag splitter handles; sizes persist after restart; Reset sizes restores defaults.

**Acceptance Scenarios**:

1. **Given** Standard Connect tab, **When** I drag a splitter between major sections, **Then** adjacent panels resize smoothly without layout lockup.
2. **Given** I resized panels, **When** I restart the app, **Then** sizes restore from preferences within sane bounds.
3. **Given** crowded content, **When** I use Reset sizes (toolbar or equivalent), **Then** Connect returns to documented default proportions.
4. **Given** resize during bridge running, **When** I drag splitters, **Then** UI remains responsive (no bridge stall).

---

### Edge Cases

- Operator edits config on web and desktop simultaneously—last save wins; dashboard refresh after save shows desktop truth.
- QR shown while token rotates (Generate on desktop)—dashboard QR updates on next meta/config poll or explicit refresh.
- COM port in use by another app—Start fails with same operator message as desktop, not silent failure.
- Field drawer height smaller than Web control minimum—vertical scroll inside Guide or Web group, not clip.
- Standard hub hidden via UI editor—COM row still functional when connection section visible.

---

## Requirements *(mandatory)*

### Functional Requirements

**Web dashboard — editable configuration**

- **FR-101**: Dashboard MUST replace read-only config summary with an **editable configuration** section when the bridge is stopped (or show read-only with clear lock when running).
- **FR-102**: Operator MUST be able to change **COM port** from the dashboard (dropdown fed by discovery list and/or manual entry consistent with desktop).
- **FR-103**: Operator MUST be able to change **network mode** among at least UDP listen, UDP remote, TCP client, and TCP server.
- **FR-104**: Operator MUST be able to edit **host and port** fields appropriate to the selected network mode (listen host/port, remote host/port, etc.).
- **FR-105**: Saving configuration MUST use the existing config mutation contract (`PATCH /config`) with token header when required; MUST surface validation and running_guard errors inline.
- **FR-106**: After successful save, dashboard and `GET /config` readback MUST match desktop Connect fields within one refresh cycle.

**Web dashboard — QR token**

- **FR-201**: Dashboard MUST provide a checkbox (or equivalent opt-in control) **“Show QR for API token”** in the Tools/token area.
- **FR-202**: When enabled and a token exists, the UI MUST render a **QR code** encoding the token as plain text and display the same token as selectable/copyable text beside it.
- **FR-203**: QR generation MUST work **offline** (vendored script or build-time asset in `web/static/`—no CDN).
- **FR-204**: When `token_required` is false, QR control MAY be hidden or disabled with helper text.

**Desktop — Field layout clipping**

- **FR-301**: Field layout Guide tab Web control group MUST NOT clip labels, checkboxes, or inputs at default launch window sizes (minimum target: 1024×768 effective content area).
- **FR-302**: If vertical space is insufficient, Guide content MUST scroll or expand rather than truncate text (project rule: no clipping).

**Desktop — Standard layout**

- **FR-401**: Standard Connect COM dropdown MUST list serial ports, allow selection, and persist selection across tab switches within a session.
- **FR-402**: Standard Connect MUST expose **resizable** major sections via splitter handles (or documented equivalent) consistent with Connect layout rules; sizes MUST persist across restarts.
- **FR-403**: Standard Connect MUST provide **Reset sizes** for Connect splitters where other layouts do.

### Key Entities

- **EditableWebConfig**: Operator-facing subset of bridge config (com_port, baud, network_mode, hosts, ports) bound to dashboard form state.
- **TokenQrDisplay**: Opt-in UI state (show_qr boolean, token string source from meta/desktop prefs).
- **ConnectLayoutPrefs**: Persisted splitter sizes and section order for Standard Connect.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: Operator can change COM and UDP/TCP bind from the dashboard alone (bridge stopped) and start successfully without opening desktop UI—verified on bench com0com + UDP test in under 3 minutes.
- **SC-102**: On a tablet without clipboard from PC, operator can enable QR, scan token, and complete one successful authenticated Start within 2 minutes.
- **SC-103**: Field Guide Web control passes visual check at 1024×768 and 125% DPI—zero clipped rows in three consecutive launches.
- **SC-104**: Standard COM dropdown lists ports and retains selection in 10 open/close cycles without UI freeze.
- **SC-105**: Standard Connect splitter drag + restart restores saved sizes within ±10% of saved values.
- **SC-106**: PyInstaller build size increase from QR library/assets remains under 5% of v1.8.4 dist (no heavy new Python UI stack).

---

## Assumptions

- `PATCH /config` and desktop façade already support the network fields; this epic is primarily **dashboard UI + desktop layout fixes**, not new bridge protocol.
- Discovery list (`GET /discovery`) remains the preferred source for COM dropdown options on web; full discovery UX polish is out of scope.
- QR is for **token handoff**, not for encoding full dashboard URLs (unless later clarified).
- Standard COM “broken” will be reproduced on Windows with at least one COM port present during acceptance testing.
- Field clipping fix may require Guide tab scroll area or increased minimum height for Web group box—implementation choice deferred to `/speckit-plan`.

---

## Dependencies

- Shipped: v1.8.4 dashboard, `GET /meta`, `PATCH /config`, Guide token field, LAN bind.
- Docs: update `docs/OPERATOR_GUIDE.md` and `control-parity.md` when web config write ships.
