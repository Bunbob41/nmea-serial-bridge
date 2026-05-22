# Feature Specification: Phase B Operator Dashboard

**Feature Branch**: `2033-phase-b-dashboard`

**Created**: 2026-05-22

**Status**: Draft

**Input**: Phase B operator dashboard — static HTML control page on localhost, live telemetry, start/stop, unlock ports, discovery refresh and device list. Builds on shipped Hybrid UI Web API ([`specs/005-hybrid-ui-webui/spec.md`](../005-hybrid-ui-webui/spec.md), v1.7.x).

**Governance**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — Principles I (bridge-core separation), II (operator trust), III (verifiable changes), V (resilience). Web UI MUST NOT parse NMEA or open sockets; it is a thin client over the existing control plane.

---

## Purpose

Field operators and bench testers need a **browser dashboard** on the bridge PC (or trusted LAN/Tailscale) so they can monitor Hz and drops and start/stop the bridge **without Swagger or curl**. The dashboard complements the desktop app; it does not replace Connect configuration for advanced survey setup.

This epic completes **Phase B** items deferred in 005 (`contracts/control-parity.md`): operator-facing HTML, unlock, and discovery exposure over REST.

---

## Clarifications

### Session 2026-05-22

- Q: Is COM/device selection on the dashboard in scope for v1.8.0 (US4 / FR-207)? → A: **Full US4** — discovery list, select device/COM on dashboard, apply via `PATCH /config` before Start.
- Q: How should the dashboard supply `X-Bridge-Token` when LAN bind + token are enabled? → A: **Dashboard settings** — token field on the page, persisted in `localStorage`, sent on all mutating requests when required.
- Q: How should dashboard styling work on offline field PCs? → A: **Vendored CSS only** — `web/static/` styles bundled in frozen build; no runtime CDN dependency.
- Q: How should `POST /discovery/refresh` behave? → A: **Async + poll** — POST returns immediately; UI polls `GET /discovery` until the list updates or **15s** timeout with a scanning state.
- Q: When should the dashboard show the token settings field? → A: **`GET /meta`** exposes `token_required` / `lan_bind`; show token settings when `token_required` is true.

---

## As-Built vs This Epic

| Capability | Today (v1.7.2) | This epic |
|------------|------------------|-----------|
| Web control | REST + OpenAPI at `/docs` | **Static dashboard** at `GET /` |
| Telemetry | `GET /status` (JSON) | Same data, **visible on dashboard** (~1 s refresh) |
| Start / Stop | `POST /bridge/start`, `/stop` | **Large buttons** on dashboard |
| Config read | `GET /config` (main-thread safe) | Shown on dashboard; **COM/device picker** applies `PATCH /config` |
| Unlock / discovery | Desktop + 501 on unsupported Web writes | **`POST /ports/unlock`**, **`POST /discovery/refresh`**, **`GET /discovery`** |
| Web meta | — | **`GET /meta`** (`token_required`, `lan_bind`, version) |
| Service index | JSON at `GET /` | Moved to **`GET /api`**; `/health` unchanged |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View real-time telemetry and status (Priority: P1)

As a field operator, I need to see data rates (Hz) and drop counts on one webpage so I can verify bridge health without Swagger or curl.

**Why this priority**: Visibility is the core B1 dashboard value.

**Independent Test**: Launch the app with Web enabled, open `http://127.0.0.1:8765/`, and observe Hz and drop counters update while NMEA traffic flows.

**Acceptance Scenarios**:

1. **Given** the bridge is passing data, **When** I open the dashboard, **Then** Hz and drop counts update automatically about every second.
2. **Given** the Web server stops or the app closes, **When** the dashboard polls, **Then** the UI shows a clear disconnected/offline state (not stale “healthy” numbers).

---

### User Story 2 - Remote start and stop (Priority: P1)

As a field operator, I need large, tap-friendly Start and Stop controls on the web page so I can run the bridge from a phone or second screen without using the PC mouse on the desktop UI.

**Why this priority**: Essential control parity with desktop Run panel.

**Independent Test**: Tap Start with valid COM/network configured; bridge runs and telemetry moves; tap Stop; bridge stops and status shows stopped.

**Acceptance Scenarios**:

1. **Given** the bridge is stopped and configuration is valid, **When** I tap Start, **Then** the UI shows running state and telemetry begins updating within a few seconds.
2. **Given** the bridge is running, **When** I tap Stop, **Then** the UI shows stopped state and throughput indicators idle.
3. **Given** invalid configuration (e.g. no COM), **When** I tap Start, **Then** the UI shows the same class of error message the desktop app would show.

---

### User Story 3 - Soft reset / unlock ports (Priority: P2)

As a field or bench operator, I need to release hung COM ports from the dashboard without restarting the desktop application.

**Why this priority**: Solves stale COM locks; secondary to start/stop/status.

**Independent Test**: With a known port lock scenario, tap Unlock; API returns success or a clear failure; desktop Unlock behavior matches.

**Acceptance Scenarios**:

1. **Given** a COM port may be locked, **When** I tap Unlock ports, **Then** the system invokes the same smart-release path as the desktop hub and displays the result message in the UI.

---

### User Story 4 - Refresh discovery and see devices (Priority: P3)

As an operator plugging in new survey equipment, I need to refresh discovery and see available serial/network endpoints on the dashboard.

**Why this priority**: Useful for dynamic USB serial; often equipment is connected before start.

**Independent Test**: Plug in a USB serial adapter, tap Refresh discovery, see the new port in the list, select it, and confirm **`GET /config`** shows the chosen COM before Start.

**Acceptance Scenarios**:

1. **Given** the app is running, **When** I trigger discovery refresh, **Then** **`POST /discovery/refresh`** returns promptly, the UI shows a scanning state, and **`GET /discovery`** reflects an updated device list within **15 seconds** or a clear timeout message.
2. **Given** a new serial device appears in the list, **When** I select it on the dashboard, **Then** **`PATCH /config`** applies hub/COM selection and **`GET /config`** matches before the next start.
3. **Given** the bridge is running, **When** I attempt to change COM via the dashboard picker, **Then** the UI shows the same stop-first policy as desktop (409 / clear message).

---

### Edge Cases

- Browser loses connection to localhost or LAN → fetch error → **Backend offline** state; no silent success.
- Rapid Start/Stop clicks → buttons disabled while a command is in flight; backend rejects duplicate commands cleanly.
- Unlock fails on a deeply hung Windows port → error message from API shown in the UI (toast or inline alert).
- LAN bind with token enabled → operator enters token once in dashboard settings; value stored in **`localStorage`** and sent as **`X-Bridge-Token`** on all mutating requests.
- Tailscale/LAN access → same dashboard URL on PC IP; firewall and token rules documented.
- Bridge running while editing COM via web → stop-first rules unchanged from 005.

---

## Requirements *(mandatory)*

### Functional Requirements

**Dashboard (presentation)**

- **FR-101**: The system MUST serve a static operator dashboard at **`GET /`** (HTML).
- **FR-102**: The previous JSON service index at **`GET /`** MUST move to **`GET /api`** without changing **`GET /health`** liveness semantics.
- **FR-103**: The dashboard MUST use responsive layout suitable for phone and desktop widths via **vendored CSS** in `web/static/` (bundled in frozen builds); external CSS/CDN MUST NOT be required at runtime.
- **FR-104**: The dashboard MUST poll **`GET /status`** about every **1 second** and render running state, COM, Hz, and drops.
- **FR-105**: The dashboard MUST provide Start and Stop actions mapped to existing **`POST /bridge/start`** and **`POST /bridge/stop`**.
- **FR-106**: The dashboard MUST NOT implement NMEA parsing, socket I/O, or bridge protocol logic (constitution).

**New API surface (control plane)**

- **FR-201**: The system MUST add **`POST /ports/unlock`** that delegates to the desktop smart-release path on the Qt main thread.
- **FR-202**: The system MUST add **`POST /discovery/refresh`** that triggers the same discovery rescan as the desktop Refresh control on the Qt main thread and returns immediately with an acknowledgment (does not block until scan completion).
- **FR-203**: The system MUST add **`GET /discovery`** returning the latest discovery snapshot (serial and network endpoints); the dashboard MUST poll it after refresh until the list updates or a **15s** timeout.
- **FR-204**: All new mutating endpoints MUST use the same thread-safe façade pattern as 005 (no Qt widget access from the HTTP thread).
- **FR-205**: When LAN exposure and token are configured, mutating routes MUST require the same token header behavior as 005; the dashboard MUST provide a settings control to enter and persist the token (browser `localStorage`) and attach it to every mutating `fetch`.
- **FR-208**: The system MUST expose **`GET /meta`** with at least `token_required`, `lan_bind`, and `version`; the dashboard MUST show the token settings field only when `token_required` is true.

**Configuration on dashboard (phased within epic)**

- **FR-206**: The dashboard MUST display current settings from **`GET /config`** alongside status.
- **FR-207**: The dashboard MUST allow selecting a discovered serial device or network card and applying it via **`PATCH /config`** (`com_port`, `hub_device_id` as applicable) before start; running-state changes MUST follow 005 stop-first rules.

**Quality**

- **FR-301**: Substantive changes MUST include tests for new routes, static root, and façade delegation; `verify_all.py` MUST pass before release.
- **FR-302**: Frozen builds MUST bundle static assets beside the executable.
- **FR-303**: Operator guide MUST document dashboard URL, LAN/Tailscale, and token usage.

### Key Entities

- **DashboardSession**: Browser-side state (connected, last status payload, in-flight command, discovery scanning).
- **WebMeta**: `token_required`, `lan_bind`, `version` for dashboard gating of token UI.
- **DiscoverySnapshot** (API view): Serial devices and network cards exposed to the web client after refresh.
- **UnlockResult**: ok/message from smart COM release (aligned with desktop).
- **WebCommandResult** (existing): ok, message, error_code, state for start/stop/config/unlock/refresh commands.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: An operator can open the dashboard and see live Hz/drops within **3 seconds** of the bridge running (after first poll).
- **SC-102**: An operator can start and stop the bridge from the dashboard without opening `/docs` in **100%** of valid bench scenarios (10-iteration script).
- **SC-103**: Dashboard layout remains usable on a **360px-wide** phone viewport and on **1920px** desktop without horizontal clipping of primary controls, with **vendored CSS only** (verify on a machine with no internet).
- **SC-104**: Unlock and discovery refresh return operator-readable success or failure messages in the UI in **100%** of scripted positive/negative cases; discovery refresh completes or times out within **15 seconds** in bench scripts.
- **SC-105**: `verify_all.py` and unit tests pass after release (Principle III).

---

## Assumptions

- **Builds on** 005 Web API: `GET /status`, `GET/PATCH /config`, `POST /bridge/start`, `POST /bridge/stop`, optional LAN bind and `X-Bridge-Token` (v1.7.2+).
- **Default access** is loopback; LAN/Tailscale is opt-in via existing Web settings; when token is required, operators configure it in the dashboard settings UI (persisted in `localStorage`, not embedded in the server).
- **No NiceGUI** or other heavy embedded Python UI framework; static HTML + existing FastAPI static mount.
- **Styling** uses vendored CSS only (`web/static/`), included in PyInstaller `datas`; dashboard MUST remain usable with no internet access.
- **NTRIP, fan-out, TCP advanced, presets, HUD** remain desktop-only (005 parity matrix).
- **Target version** after implement: **1.8.0** (minor — new operator surface + API routes).

---

## Dependencies

- Shipped [`specs/005-hybrid-ui-webui`](../005-hybrid-ui-webui/) (Web server, façade, OpenAPI).
- Connection Hub discovery worker and `port_release.smart_release_com` (v1.6.0+).
- `docs/OPERATOR_GUIDE.md` update for dashboard workflow.
