# Feature Specification: Pre-Release Full App Audit

**Feature Branch**: `2036-pre-release-audit`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Full app audit before the first (or next) **GitHub release**: identify features that still need work, UI/packaging polish gaps, and release blockers. Operator-reported **frozen EXE icon** shows an unintelligible blue square instead of recognizable Serial Link branding.

**Builds on**: UI Journey Modernization ([`specs/008-ui-journey-modernization/spec.md`](../008-ui-journey-modernization/spec.md)); Modern Control polish ([`specs/009-modern-control-polish/spec.md`](../009-modern-control-polish/spec.md)); constitution gates ([`.specify/memory/constitution.md`](../../.specify/memory/constitution.md)); Argo charter P0–P3 themes (`.cursor/rules/080-argo-serialtool-benchmark.mdc`).

**Baseline version at spec time**: v1.33.1 (`version.py`).

**Known release blocker (operator report)**: `dist\serial-link\serial-link.exe` and desktop shortcuts display a **featureless dark/blue square** in Windows Explorer, taskbar, and title bar—the RJ-45 / DB-9 connector glyph is not readable at shell sizes.

---

## Purpose

Serial Link is approaching a **public GitHub release** (tagged zip via `release.ps1`). Before publishing, the team needs a **structured audit** that:

1. Fixes **branding and packaging defects** that undermine first impressions (EXE icon).
2. Re-validates **Modern UI** and core bridge workflows at field-realistic window sizes.
3. Produces a **prioritized inventory** (P0 / P1 / P2) with explicit ship gates.
4. Confirms **automated verification** and **operator documentation** match the build being released.

This epic is **audit-first, fix-in-priority-order**—not a feature expansion. Items in [`docs/ROADMAP.md`](../../docs/ROADMAP.md) (e.g. MAVLink GPS injector) remain **out of scope** unless promoted to their own spec.

---

## Scope Boundaries

| In scope | Out of scope |
|----------|----------------|
| Frozen **EXE / shortcut / taskbar / title bar** icon readability | Code signing purchase or EV certificate procurement |
| Regenerating and validating icon assets; release build embeds correct icon | Kernel virtual COM / passive sniff drivers |
| Modern UI audit at **640×420** (min) and **1280×720** (default field) | Standard / Field / Minimal layout redesign |
| Extending or superseding [`docs/ui-audit-inventory.md`](../../docs/ui-audit-inventory.md) for **Modern** surfaces | MAVLink GPS injector (`docs/ROADMAP.md`) |
| Release gates: `verify_all`, unittest, `check_frozen_bundle`, version sync | New bridge protocols or multi-port N×M router |
| GitHub release checklist: CHANGELOG, README version line, zip naming | Full SerialTool terminal parity |
| P0–P2 fixes discovered during audit | P3+ sandbox expansion unless blocking release narrative |
| SmartScreen / unsigned-build **documentation** in OPERATOR_GUIDE | Marketing site or installer wizard |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognizable app icon everywhere Windows shows it (Priority: P1)

As an operator installing Serial Link from a GitHub release zip, I want the **EXE, shortcut, taskbar, and title bar** to show a **clear, readable logo** (connector glyph on branded tile—not a blank colored square), so I can find the app among other tools and trust the download.

**Why this priority**: Direct operator pain; damages credibility on first install. Reported as release blocker.

**Independent Test**: After a clean `release.ps1` build on a machine with cleared icon cache (or fresh VM), pin `serial-link.exe` to taskbar and create a desktop shortcut; at 16×16, 32×32, and 48×48 equivalent views, a reviewer identifies “serial / network bridge” branding without opening the app.

**Acceptance Scenarios**:

1. **Given** a fresh frozen build, **When** I view `serial-link.exe` in File Explorer (medium/large icons), **Then** the icon shows a **discernible connector glyph**, not a uniform blue/dark square.
2. **Given** the app is running, **When** I look at the taskbar button and window title bar, **Then** the same readable icon appears (not a generic placeholder).
3. **Given** I run `create_desktop_shortcut.ps1`, **When** I view the shortcut, **Then** it uses the same icon as the EXE.
4. **Given** dev mode (`python bridge_gui.py`), **When** the window opens, **Then** the title bar icon matches the frozen build family (PNG/ICO pipeline consistent).
5. **Given** icon assets are regenerated, **When** `build.ps1` runs, **Then** icon generation is part of the standard build path before PyInstaller (no stale ICO shipped).

---

### User Story 2 - Release audit inventory with ship gates (Priority: P1)

As a maintainer preparing `gh release`, I want a **single audit document** listing open issues by severity (P0 / P1 / P2), layout/area, and status, so we do not ship with unknown blockers.

**Why this priority**: Without inventory, polish work is ad hoc; 008 inventory is **Standard/Field-centric** and stale for Modern v1.33.x.

**Independent Test**: `docs/pre-release-audit-inventory.md` exists; P0 count is zero before tag; every open P1 is either fixed or listed in CHANGELOG deferred section with one-line operator note (same contract as 008).

**Acceptance Scenarios**:

1. **Given** audit start, **When** inventory is created, **Then** each row has ID, surface (Modern tab / packaging / bridge / web), type, severity, status, notes.
2. **Given** audit complete, **When** I filter P0 rows, **Then** count is **zero** or release is explicitly held.
3. **Given** an unfixed P1, **When** we ship anyway, **Then** CHANGELOG **Deferred** section documents it in ≤1 line each.
4. **Given** 008 inventory, **When** Modern-only findings are added, **Then** they use a distinct ID prefix (e.g. `MOD-CONTROL-01`) without duplicating already-fixed STD/FIELD rows.

---

### User Story 3 - Modern UI polish pass at minimum and default sizes (Priority: P1)

As an operator using the **Modern** layout on a laptop, I want every primary tab (Control, Hub, Presets, Phone, NMEA, Activity, Guide, Diagnostics) to remain **readable and actionable** at **640×420** and **1280×720**, so I can connect and start without maximizing the window.

**Why this priority**: Recent fixes (Control side-by-side, Phone stack) show min-width regressions are likely elsewhere; release should not reintroduce clipping or dead controls.

**Independent Test**: Manual checklist at both resolutions with sidebar and top-chips navigation; automated tests where they exist (`test_ui_tabs`, layout constants) pass.

**Acceptance Scenarios**:

1. **Given** window at **640×420**, **When** I visit each Modern tools page, **Then** Start/Stop (or equivalent run control) and connection health remain reachable without horizontal scroll on primary actions.
2. **Given** Phone tab at minimum width, **When** cards stack, **Then** QR, port spinbox, and Open dashboard remain usable (regression guard for v1.33.1).
3. **Given** Control at minimum width, **When** Advanced network is expanded, **Then** no P0 clipping on host/port rows (extends 009 SC-202).
4. **Given** top-chips navigation, **When** I switch tabs at 1280×720, **Then** active chip styling matches content (no stale highlight).
5. **Given** audit finds a P0 layout defect, **When** fixed, **Then** inventory row moves to **fixed** with version note.

---

### User Story 4 - Packaging and version integrity (Priority: P2)

As a maintainer running `release.ps1`, I want **version.py**, **version_info.txt**, window title, and zip filename to agree, and frozen bundle checks to pass, so support can correlate operator reports to an exact build.

**Why this priority**: Constitution principle IV; prevents “wrong version in Properties” support churn.

**Independent Test**: After build, exe Properties version matches `version.py`; `tools/check_frozen_bundle.py` passes; zip name is `serial-link-vX.Y.Z-win64.zip`.

**Acceptance Scenarios**:

1. **Given** `version.py` bump, **When** `build.ps1` runs, **Then** `sync_version_info.py` updates `version_info.txt` before PyInstaller.
2. **Given** successful build, **When** I inspect `dist\serial-link\`, **Then** `assets\app-icon.ico`, `docs\`, and web static files required by phone dashboard are present (`check_frozen_bundle`).
3. **Given** `-SkipTests` release iteration, **When** publishing, **Then** maintainer acknowledges skipped unittest gate in release notes (not default for public release).

---

### User Story 5 - Core bridge reliability spot-check (Priority: P2)

As a survey operator, I need confidence that **connect → run → monitor drops** still works for the primary NMEA UDP→COM path after UI polish, so the release is not “pretty but broken.”

**Why this priority**: Argo P0 themes—backpressure visibility, COM exclusivity messaging, raw mode byte integrity.

**Independent Test**: Existing automated suite passes; manual or bench script spot-check documented in audit verification log (com0com + UDP burst optional).

**Acceptance Scenarios**:

1. **Given** `python verify_all.py` and unittest discover, **When** run on release branch, **Then** both exit zero.
2. **Given** raw binary mode, **When** RTCM-like bytes traverse bridge in tests, **Then** no NMEA assembly corruption (`test_nmea_codec`, bridge tests).
3. **Given** COM port in use, **When** operator starts bridge, **Then** blocking message is clear (no silent failure)—verified manually once per release.
4. **Given** running bridge with consumer disconnect, **When** UDP peer drops, **Then** UI remains responsive and drop counters update (manual smoke note in audit log).

---

### User Story 6 - GitHub release narrative ready (Priority: P2)

As a new GitHub visitor, I want **README**, **CHANGELOG**, and release notes to describe what Serial Link does, how to install the zip, and what changed in this version, so I can deploy without reading the whole repo.

**Why this priority**: First public release sets expectations; unsigned SmartScreen warning must be documented.

**Independent Test**: README install section matches actual zip layout; CHANGELOG has `## vX.Y.Z` for release tag; OPERATOR_GUIDE mentions SmartScreen / unsigned exe if still applicable.

**Acceptance Scenarios**:

1. **Given** release tag vX.Y.Z, **When** I read CHANGELOG top section, **Then** it summarizes audit fixes (icon, P0/P1 closures) in operator language.
2. **Given** README **Frozen build** section, **When** I follow steps, **Then** they match `release.ps1` output path and exe name `serial-link.exe`.
3. **Given** unsigned build, **When** I read OPERATOR_GUIDE install/security section, **Then** SmartScreen “More info → Run anyway” or equivalent is documented.

---

### User Story 7 - Explicit deferrals for post-release work (Priority: P3)

As a maintainer, I want **deferred** items (P2 audit findings, ROADMAP epics, 009 manual smoke T021) listed in one place, so the release scope is honest and follow-up specs are obvious.

**Why this priority**: Prevents scope creep while preserving backlog visibility.

**Independent Test**: Audit inventory **deferred** section + CHANGELOG deferred bullets; no hidden “known broken” items.

**Acceptance Scenarios**:

1. **Given** P2 UI nit found during audit, **When** not fixed pre-release, **Then** it appears in inventory as **deferred** with target spec or version hint.
2. **Given** ROADMAP epics, **When** release notes are drafted, **Then** they are not implied as shipped features.

---

### Edge Cases

- **Windows icon cache** shows old icon after rebuild—audit procedure must include cache-bust or VM note so false passes are not reported.
- **Missing `app-icon-source.png`**: pipeline falls back to `app-icon.png`; audit must confirm source art exists or document approved fallback.
- **High-DPI display**: icon readability at 125%/150% scaling on taskbar.
- **009 T021 manual smoke** not completed—either complete before release or defer with explicit P1 note if non-blocking.
- **PublishOnly** release path skips tests—must not be used for first public release without maintainer sign-off.
- **Multiple UI modes**: Modern is primary; Standard/Field regressions are P1 if they break connect-first workflow, P2 if cosmetic only.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Branding & packaging

- **FR-401**: Frozen `serial-link.exe` MUST display a **readable application icon** at Windows shell sizes (16–48px equivalent)—not a featureless solid color square—in Explorer, taskbar, title bar, and shortcuts.
- **FR-402**: Icon asset pipeline MUST produce consistent branding for dev (`bridge_gui.py`) and frozen builds before each release build.
- **FR-403**: Release build MUST embed the same validated ICO used by `create_desktop_shortcut.ps1`.

#### Audit inventory & gates

- **FR-404**: A **pre-release audit inventory** MUST be maintained at `docs/pre-release-audit-inventory.md` following the severity matrix in [`specs/008-ui-journey-modernization/contracts/ui-audit-matrix.md`](../008-ui-journey-modernization/contracts/ui-audit-matrix.md) (extended for Modern + packaging rows).
- **FR-405**: **Zero open P0** rows MUST be the default ship gate; exceptions require explicit maintainer waiver documented in CHANGELOG.
- **FR-406**: Open **P1** at ship MUST be fixed OR listed in CHANGELOG **Deferred** with one-line operator impact each.

#### Modern UI validation

- **FR-407**: Manual audit MUST cover Modern tools pages at **640×420** and **1280×720** with both **sidebar** and **top-chips** navigation modes where applicable.
- **FR-408**: Any new P0/P1 Modern layout defect found MUST receive a regression test or documented manual check in the audit verification log when automation is impractical.

#### Release integrity

- **FR-409**: `version.py`, `version_info.txt`, window title, and release zip name MUST report the same semver for the tagged release.
- **FR-410**: `verify_all.py` and full unittest discover MUST pass on the release branch before `-Publish` (constitution gate).
- **FR-411**: `check_frozen_bundle.py` MUST pass on `dist\serial-link` before zipping.

#### Documentation

- **FR-412**: CHANGELOG MUST include a release section summarizing audit-driven fixes (minimum: icon + closed P0/P1 items).
- **FR-413**: OPERATOR_GUIDE MUST document unsigned/SmartScreen expectations if builds remain unsigned.
- **FR-414**: README frozen-build instructions MUST match actual artifact names and folder layout.

#### Bridge trust (spot-check)

- **FR-415**: Raw binary passthrough MUST remain byte-safe (no regression in existing codec/bridge tests).
- **FR-416**: Drop/reject counters and connection health MUST remain visible in Modern UI during normal run (manual smoke once per release).

### Key Entities

- **Audit row**: `{ID, Surface, Type, Severity, Status, Notes}` — surfaces include `packaging`, `modern-control`, `modern-hub`, `modern-phone`, `bridge`, `web`, `docs`.
- **Ship gate**: `{P0 open = 0, verify_all pass, unittest pass, frozen bundle pass, version sync}`.
- **Icon acceptance**: subjective **recognizable glyph** test at small sizes; documented reviewer checklist in plan contract.
- **Release artifact**: `dist\serial-link-vX.Y.Z-win64.zip` containing one-folder `serial-link\` with `serial-link.exe`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-401**: **3/3** reviewers (or one maintainer + checklist) identify the EXE icon as Serial Link / serial-network bridge branding at taskbar size—not a blank colored square.
- **SC-402**: Pre-release inventory shows **0 open P0** at tag time; **≤3 open P1** only if each has CHANGELOG deferred entry.
- **SC-403**: Modern UI manual pass at 640×420 and 1280×720 completes with **zero new P0** findings; any P1 found are fixed or deferred with ID reference.
- **SC-404**: `verify_all.py` + unittest discover + `check_frozen_bundle.py` all **exit 0** on release commit.
- **SC-405**: Version string identical in `version.py`, exe Properties, and window title bar for the release build.
- **SC-406**: GitHub release zip downloads and launches on a clean Windows profile with documented SmartScreen steps; primary connect workflow completable in **≤15 minutes** per GETTING_STARTED.

---

## Assumptions

- **Modern UI** is the primary operator surface for this release; Standard/Field receive regression-only attention unless P0.
- Builds remain **unsigned**; documentation compensates until signing is a separate epic.
- Icon source art (`assets/app-icon-source.png` or approved PNG) can be edited or replaced if current glyph fails small-size readability.
- Audit is performed on **Windows 10/11 x64** matching primary target.
- v1.33.x Control and Phone min-width fixes remain baseline; audit searches for similar gaps on other tabs.
- Public release uses full `build.ps1` gate, not `-SkipTests`, unless explicitly waived.

---

## Seed Findings (initial audit backlog)

These rows **seed** `docs/pre-release-audit-inventory.md` during implement; status is **open** until closed.

| ID | Surface | Type | Severity | Status | Notes |
|----|---------|------|----------|--------|-------|
| PKG-ICON-01 | packaging | branding | **P0** | open | EXE/shortcut shows unintelligible blue square; shell sizes lack readable glyph |
| AUDIT-INV-01 | docs | process | P1 | open | `ui-audit-inventory.md` is 008-era Standard/Field; Modern v1.33.x not covered |
| MOD-SMOKE-01 | modern-all | process | P1 | open | 009 T021 manual smoke at 640×420 / 1280×720 not recorded in verification log |
| PKG-VERSION-01 | packaging | copy | P2 | open | Confirm `version_info.txt` sync on every release build (automated in build.ps1; verify on tag) |
| DOC-SMART-01 | docs | copy | P2 | open | Confirm OPERATOR_GUIDE SmartScreen / unsigned exe guidance is current |
| ROADMAP-SCOPE-01 | docs | scope | P3 | deferred | MAVLink injector and kernel COM remain ROADMAP-only |

---

## Implementation Priority (ordered backlog)

| Order | Story | Focus |
|-------|-------|-------|
| 1 | US1 | EXE icon fix + validation checklist |
| 2 | US2 | Audit inventory + P0/P1 gates |
| 3 | US3 | Modern UI min/default pass + fixes |
| 4 | US4 | Version sync + frozen bundle gates |
| 5 | US5 | Bridge spot-check + test suite green |
| 6 | US6 | README / CHANGELOG / release notes |
| 7 | US7 | Deferrals documented |

---

## Dependencies

- Existing icon tooling (`tools/make_app_icon.py`, `assets/*`, `nmea_serial_bridge.spec` icon=, `ui/app_icon.py`).
- Release scripts (`build.ps1`, `release.ps1`, `tools/sync_version_info.py`, `tools/check_frozen_bundle.py`).
- 009 Modern Control polish (v1.33.0–1.33.1) as UI baseline.
- 008 audit matrix contract for severity definitions.

---

## Next Steps

1. `/speckit-plan` — research icon root cause, define contracts (`app-icon-acceptance`, `release-readiness-gate`, `modern-ui-audit-matrix`).
2. `/speckit-tasks` — ordered tasks: icon fix → inventory → UI pass → release dry-run.
3. `/speckit-implement` — execute fixes; bump version; run full build; manual icon + Modern smoke.
