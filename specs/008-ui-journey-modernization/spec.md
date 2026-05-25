# Feature Specification: UI & Workflow Journey Modernization

**Feature Branch**: `2034-ui-journey-modernization`

**Created**: 2026-05-24

**Status**: Draft

**Input**: Define a comprehensive UI and workflow modernization specification for existing user journeys. Scope: (1) UI & information audit across global layouts, (2) returning-user flow optimization with cached session handling, (3) Product Demo tab overhaul with isolated state, clean mock data, and non-polluting exit.

**Builds on**: Baseline operator journeys ([`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md)); desktop UX fixes ([`specs/007-web-config-desktop-ux/spec.md`](../007-web-config-desktop-ux/spec.md)); Phase B web dashboard ([`specs/006-phase-b-dashboard/spec.md`](../006-phase-b-dashboard/spec.md)).

---

## Purpose

Survey operators and bench presenters use the NMEA serial bridge across multiple layouts (Standard, Field, Minimal, Log-first), persisted preferences, and a presenter **Product demo** mode. Over time, copy, placeholders, and layout density have diverged; returning users hit friction restoring COM/network/NMEA context; and the demo walkthrough can alter live bridge settings without a guaranteed rollback.

This epic modernizes **existing** journeys—no new bridge protocols—so operators trust what they read on screen, resume work in one predictable path, and presenters can run demos without contaminating production sessions.

---

## Scope Boundaries

| In scope | Out of scope |
|----------|----------------|
| Copy, labels, tooltips, placeholder text, and layout consistency audit across all primary layouts | New network discovery algorithms, kernel drivers, NTRIP redesign |
| Returning-user flows: presets, recent sessions, layout prefs, web token handoff, last-used COM/network | New authentication system or multi-user accounts |
| Product Demo (View menu / survey bar): isolated demo state, mock data, clean exit, production parity for demonstrated capabilities | Full rewrite of bridge core or web dashboard Phase C |
| Measurable acceptance criteria and operator-facing verification | Marketing site or installer branding outside the app |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Returning operator resumes the last survey setup (Priority: P1)

As a field operator who used the bridge yesterday on this PC, I want the app to restore my last meaningful connection context (COM, baud, network bind, NMEA mode, active preset name) without hunting through tabs or re-entering values, so I can start the bridge within one minute of opening the app.

**Why this priority**: Daily survey work depends on fast resume; friction here is the highest-frequency pain across layouts.

**Independent Test**: Save a distinct preset and recent-session fingerprint, close the app, relaunch, confirm Connect (or field strip) shows the same values and preset label without starting the bridge; start bridge and confirm traffic uses restored settings.

**Acceptance Scenarios**:

1. **Given** a stopped bridge and a saved preset was last active, **When** I launch the app, **Then** the active preset name and its COM/UDP/NMEA fields are visible without opening Tools first.
2. **Given** recent sessions exist, **When** I open the Recent menu, **Then** each entry shows COM, baud, host:port, and NMEA mode in one scannable line.
3. **Given** I load a recent session while stopped, **When** apply completes, **Then** COM, network, and NMEA controls match that session before Start.
4. **Given** the bridge is running, **When** I attempt to load a different preset’s COM/UDP, **Then** the app blocks destructive apply and explains stop-first (survey fields may still preview).
5. **Given** persisted layout preferences (Connect section order, toolbar, theme), **When** I relaunch, **Then** sections appear in saved order without clipped primary controls at default window size.

---

### User Story 2 - Global UI & information consistency pass (Priority: P1)

As an operator or trainer, I want every screen to use current product language (no stale placeholders, no “generate token first” when a token exists, no contradictory hints), and layouts to follow one visual hierarchy, so I am not misled during connect → run → monitor flows.

**Why this priority**: Incorrect or legacy copy erodes trust and drives support churn equal to functional bugs.

**Independent Test**: Walk a written audit checklist across Standard, Field, Minimal, and Log-first at default launch size; zero P0 copy/layout defects remain for Connect, Tools (Presets, Phone, NMEA, Guide), status bar, and web dashboard entry points.

**Acceptance Scenarios**:

1. **Given** any primary layout at first launch (1280×720 minimum), **When** I view Connect and status chips, **Then** no label or helper text is clipped or overlaps controls.
2. **Given** Web API is enabled with a valid token, **When** I open Tools → Phone, **Then** QR and helper text reflect “ready to scan” state—not placeholder “generate token” messaging.
3. **Given** I open Tools → Presets, NMEA, Phone, and Guide, **When** I read hints and tooltips, **Then** terminology matches the operator guide (COM, UDP listen, NMEA passthrough/strict/raw, Tailscale/LAN).
4. **Given** obsolete UI chrome (e.g., controls that no longer affect layout), **When** I search the Connect toolbar and Tools areas, **Then** removed or relabeled items do not appear as dead controls.
5. **Given** the UI audit inventory, **When** modernization ships, **Then** every P0/P1 audit item is closed or explicitly deferred with operator-visible rationale in release notes.

---

### User Story 3 - Presenter runs Product Demo without polluting live session (Priority: P2)

As a presenter demonstrating the bridge to stakeholders, I want the Product Demo view (View → Product demo / survey bar Demo) to use self-contained mock or sandboxed data, manage its own step state, and fully restore my pre-demo bridge and UI settings when I close the demo, so my live survey session is unchanged.

**Why this priority**: Demo pollution causes real COM ports, presets, and network modes to change silently—high severity but lower frequency than daily resume.

**Independent Test**: Record pre-demo COM, preset, bridge running state, and log line count; run demo through at least three steps including one that today changes presets/network; close demo; assert all recorded values match pre-demo snapshot.

**Acceptance Scenarios**:

1. **Given** a running or stopped production bridge configuration, **When** I open Product Demo, **Then** the demo captures a restorable snapshot before any demo step mutates the host window.
2. **Given** demo is open, **When** I advance steps (manual or auto-play), **Then** demo UI state (current step, phase, progress) is independent of Connect tab collapse state and does not require the Connect tab to be visible.
3. **Given** demo steps need sample traffic or stats, **When** mock data is shown, **Then** labels clearly indicate demonstration content and do not write mock values into persisted presets or `path_presets.json`.
4. **Given** I close or dismiss Product Demo (including force-close window), **When** exit completes, **Then** COM, network, NMEA mode, active preset, bridge run/stop state, and open panels match the pre-demo snapshot within operator-visible tolerance (stopped/started as before).
5. **Given** production modules demonstrated in demo (presets, HUD, TCP mode, diagnostics triggers), **When** I compare demo step capabilities to live modules, **Then** demonstrated actions remain available in production without demo-only stubs that misrepresent behavior.

---

### User Story 4 - First-time and returning web-dashboard handoff (Priority: P3)

As an operator using phone dashboard after a prior desktop session, I want token and URL guidance to reflect actual state (token present, LAN URL set), so I do not repeat setup steps that already succeeded.

**Why this priority**: Extends returning-user optimization to hybrid UI; lower priority than desktop Connect but included in global audit.

**Independent Test**: With token and phone URL saved in desktop prefs, open dashboard from setup link; confirm no redundant “missing token” banners when token is valid.

**Acceptance Scenarios**:

1. **Given** desktop has saved API token and phone base URL, **When** I open the dashboard via setup link on another device, **Then** token is consumed and controls are usable without re-pasting unless token was revoked.
2. **Given** desktop Web API port changed since last phone visit, **When** I read Phone tab URL labels, **Then** copy reflects the current port and distinguishes live vs pending restart when applicable.

---

### Edge Cases

- App crash or kill during Product Demo: on next launch, no partial demo snapshot leaves bridge in half-applied demo state.
- Demo opened while bridge is running: exit restores run/stop state; operator is warned if demo steps require stop-first.
- Multiple rapid preset/recent loads while stopped: last intentional selection wins; UI does not flash intermediate values.
- Corrupted or legacy prefs (invalid panel heights, removed toolbar keys): app migrates or ignores safely with defaults, no zero-height Connect sections.
- Presenter runs demo twice in one session: second open starts from clean demo state, not mid-script residue.
- Returning user with empty COM list (no USB serial): copy explains refresh path without implying a fault in saved prefs.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-101**: The product MUST maintain a documented UI & information audit inventory covering Standard, Field, Minimal, Log-first, Tools subtabs (Presets, Phone, NMEA, Terminal, Diagnostics, Theme, Guide), Connect status bar, and Product Demo entry points.
- **FR-102**: The audit MUST classify findings as P0 (misleading/broken), P1 (clutter/inconsistent), P2 (polish); shipping gate requires zero open P0 and agreed disposition on P1.
- **FR-103**: All operator-visible strings in scope MUST use consistent terminology per the operator guide (COM, UDP listen, NMEA modes, Tailscale/LAN, stop-before-change).
- **FR-104**: Placeholder and empty-state messages MUST reflect actual system state (e.g., token present, ports list empty, bridge running).
- **FR-105**: Primary workflows (Connect visible, Start/Stop reachable, status chips readable) MUST not require fullscreen at 1280×720 for any in-scope layout.
- **FR-201**: On launch, the app MUST restore last active preset name and connection fields when the bridge is stopped, without silent overwrite from builtins.
- **FR-202**: Recent sessions MUST display COM, baud, host:port, and NMEA mode; applying a session MUST set matching controls when stopped.
- **FR-203**: Loading presets or recent sessions while the bridge is running MUST follow existing stop-first rules with visible operator messaging.
- **FR-204**: Persisted layout preferences (Connect section order/visibility, toolbar order, theme, QR position) MUST load without trapping users in unusable geometry (migrated or reset safely).
- **FR-205**: State transitions between Connect, Log, Tools, and HUD MUST preserve operator context (no unexpected tab switches except where demo or explicit navigation requires).
- **FR-301**: Product Demo MUST capture a restorable snapshot of host bridge/UI configuration before the first demo mutation.
- **FR-302**: Product Demo MUST keep presenter UI state (step index, phase, auto-play timer) inside the demo module, not dependent on Connect panel expansion.
- **FR-303**: Demo initialization MUST start from defined mock/safe defaults for presentation (bench-style COM/UDP labels acceptable) without persisting demo values into user preset files.
- **FR-304**: Closing Product Demo MUST restore the snapshot within 5 seconds and log a single confirmation line in the live log.
- **FR-305**: Demo steps that invoke production actions (presets, network mode, HUD, diagnostics) MUST remain functionally available in production after demo exit with parity to pre-demo behavior.
- **FR-306**: Product Demo MUST offer explicit “Reset demo” or equivalent that rewinds demo script state without touching production snapshot until exit.
- **FR-401**: Phone/Web handoff copy MUST align with desktop token and URL state per returning-user rules (no stale placeholders when configured).

### Key Entities

- **UI Audit Item**: Screen area, issue type (copy/layout/placeholder), severity, resolution status, verifier.
- **Operator Session Snapshot**: COM, baud, network mode/bind, NMEA mode, preset name, bridge running flag, optional log pause state—used for demo restore and returning-user validation.
- **Recent Session Entry**: COM, baud, net target, NMEA mode, pin flag, sort order.
- **Demo Run State**: Current step id, phase, auto-play flag, presenter index, isolated from Connect disclosure state.
- **Layout Preference Bundle**: Connect panel order/visibility/collapsed, toolbar order, theme id, QR overlay position—migrated as needed.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: 100% of P0 audit items are closed before release; P1 items are closed or documented as deferred with operator-facing release note entry.
- **SC-102**: In moderated usability checks, returning operators (n≥5) restore last preset and start bridge in under 60 seconds without opening more than two tabs.
- **SC-103**: Zero instances of clipped Start/Stop or status chips at 1280×720 across four layouts in QA matrix (4 layouts × 3 window sizes).
- **SC-201**: Product Demo exit restores pre-demo COM, network mode, NMEA mode, preset name, and bridge run/stop state in 100% of scripted test runs (n≥10).
- **SC-202**: After demo, zero unintended writes to user preset files (hash/compare `path_presets.json` before/after).
- **SC-203**: Presenters complete a 5-step manual demo script without reporting “my live COM changed” in post-run survey (target 0/5 failures).
- **SC-301**: Recent session menu apply sets all four displayed fields correctly in 100% of bench-automated UI tests for stored fixtures.

---

## Assumptions

- Target users remain Windows survey operators and bench presenters; mobile web dashboard is a companion surface, not the primary audit surface except Phone/Guide handoff strings.
- “Product Demo” refers to the presenter dialog opened from View → Product demo (and Field survey bar Demo), not a separate unreleased module.
- Returning-user data continues to live in existing local preference stores; no cloud account sync is required.
- Demo mock data may use com0com-style bench labeling but must be clearly marked as demonstration when shown in stats/HUD.
- Bridge running guardrails (stop before COM/network change) remain non-negotiable; modernization does not relax them.
- Feature parity for demo means demonstrated controls exist and behave as in production, not that every production feature appears in the demo script.
