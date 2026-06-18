# Feature Specification: Modern Control Tab Polish

**Feature Branch**: `2035-modern-control-polish`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Audit follow-ups from Modern Control tab redesign (v1.32.4–v1.32.7). Implement remaining polish items in priority order: preset status parity, advanced network styling, visual consistency, responsive-layout clarity, automated tests, stylesheet cleanup, and operator documentation.

**Builds on**: UI Journey Modernization ([`specs/008-ui-journey-modernization/spec.md`](../008-ui-journey-modernization/spec.md)); Phase B position map ([`specs/006-phase-b-dashboard/spec.md`](../006-phase-b-dashboard/spec.md)); Connection Hub ([`specs/004-hub-network-discovery/spec.md`](../004-hub-network-discovery/spec.md)).

**Shipped baseline (do not regress)**: Control page banner, card-style Serial/Network forms, preset summary strip, Hub page banner, side-by-side forms at 640×420 minimum, top-chips nav consistency.

---

## Purpose

The Modern **Control** tab received a structural redesign (page banner, form cards, preset strip, collapsible position track). Operators approved the layout at minimum window size. A post-ship audit identified **visual parity gaps**, **incomplete styling** for expanded advanced-network controls, **dead responsive code**, **missing automated coverage**, and **minor stylesheet duplication**.

This epic closes those gaps so Control feels as polished as Presets and Hub, without changing bridge behavior or non-Modern layouts.

---

## Scope Boundaries

| In scope | Out of scope |
|----------|----------------|
| Modern UI **Control** tab only (preset strip, Network card, Position track header, related QSS) | Field, Standard, Minimal, Log-first layout changes |
| Shared live-status visual language between Control preset strip and Presets “Loaded/Preview” strip | New bridge protocols, COM discovery algorithms |
| Styling for Advanced network panel when expanded inside Modern Network card | Rewriting `_modern_flat_page` or moving Control builder to `tool_tabs.py` |
| Clarifying or removing sub-minimum vertical stack behavior | Lowering window minimum below 640×420 |
| Unit tests for Control page chrome (banner, preset bar) | Visual screenshot/regression suite |
| Stylesheet deduplication for `modernControlTab` | Full Modern theme token refactor |
| Operator guide note for Control page layout and tools navigation modes | Marketing or installer copy |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preset status looks the same on Control and Presets (Priority: P1)

As an operator who loads a named preset, I want the **active configuration summary** on Control to use the same visual language as the Presets tab (color, weight, and “ready/loaded” meaning), so I instantly recognize that my saved setup is active before I press Start.

**Why this priority**: Highest visible inconsistency after the redesign; directly affects trust in connect-first workflow.

**Independent Test**: Load «Desk test» (or any preset); open Presets then Control; both surfaces communicate “active preset” with matching semantic styling (not conflicting blue vs green treatments for the same state).

**Acceptance Scenarios**:

1. **Given** a preset is loaded while stopped, **When** I view Control, **Then** the preset summary strip uses the same **ready/loaded** status styling family as Presets (not a one-off color scheme).
2. **Given** no preset is active and intent hint is empty, **When** I view Control, **Then** the preset strip is hidden (no empty chrome).
3. **Given** a long preset description, **When** the window is at minimum width, **Then** text elides with full text available on hover (existing compact hint behavior preserved).
4. **Given** I switch presets from the Presets tab, **When** I return to Control, **Then** the strip updates without requiring a bridge restart.

---

### User Story 2 - Advanced network controls match the Network card (Priority: P2)

As an operator enabling **Advanced network** on Control, I want TCP/UDP remote/server/client fields to look like part of the Network card—not a plain embedded panel—so expanded options feel intentional and readable.

**Why this priority**: Functional path used in bench and boat setups; currently visually weaker than the rest of the card.

**Independent Test**: On Control, check **Advanced network**; all radio rows, host/port fields, and labels match Network card typography, spacing, and focus states.

**Acceptance Scenarios**:

1. **Given** Advanced network is unchecked, **When** I view the Network card, **Then** no advanced panel chrome is visible (unchanged collapse behavior).
2. **Given** I enable Advanced network, **When** the panel expands, **Then** inputs and labels inherit Modern Control form styling (consistent borders, label color, checkbox spacing).
3. **Given** Advanced network is expanded at 640×420, **When** I read host/port fields, **Then** no control is clipped or overlaps adjacent checkboxes.
4. **Given** I toggle advanced modes (UDP remote, TCP server, TCP client), **When** mode-specific rows show/hide, **Then** layout reflow does not jump the Serial card or preset strip.

---

### User Story 3 - Visual hierarchy and icon clarity (Priority: P2)

As an operator moving between Control, Activity, and Presets, I want section icons and headings to be distinct and hierarchically consistent, so I never confuse “preset summary” with “Activity log” or undervalue the position track section.

**Why this priority**: Low effort, high scannability; fixes 📋 icon reuse called out in audit.

**Independent Test**: Scan Control and Activity banners and section headers at default size; no duplicate icon semantics; Position track title weight/size aligns with Serial/Network section titles.

**Acceptance Scenarios**:

1. **Given** Control preset strip and Activity page banner, **When** I compare icons, **Then** they are not identical for unrelated meanings (preset config vs wire-tap activity).
2. **Given** Position track header on Control, **When** I compare to Serial/Network section titles, **Then** typography follows one hierarchy (section title size/weight within one step, not mismatched by >1 level).
3. **Given** top-chips navigation, **When** I view Control page banner icon, **Then** it remains consistent with the Control nav chip icon (🎛).

---

### User Story 4 - Responsive layout behavior is honest at minimum size (Priority: P3)

As a maintainer and operator, I want the app’s **minimum-size Control layout** to stay side-by-side (Serial | Network) and any unused vertical-stack code path to be either removed or clearly documented as test-only, so future changes do not reintroduce the stacked minimum layout regression.

**Why this priority**: Prevents recurrence of v1.32.6→1.32.7 bug; reduces dead code confusion.

**Independent Test**: At 640×420 with sidebar and with top-chips nav, Serial and Network remain side-by-side; codebase/doc comment states when vertical stack applies (if retained).

**Acceptance Scenarios**:

1. **Given** window at 640×420, **When** Control is visible, **Then** Serial and Network cards are **horizontal** (regression guard).
2. **Given** sidebar navigation at minimum width, **When** Control is visible, **Then** forms remain usable (no critical clipping of COM row or fan-out checkbox).
3. **Given** the responsive stack threshold, **When** a developer reads the constant and tests, **Then** intent is documented (either “below allowed min width, test-only” or stack code removed).

---

### User Story 5 - Automated coverage for Control page chrome (Priority: P3)

As a developer shipping Modern UI changes, I want unit tests that assert Control uses the shared page banner and preset strip widgets, so refactors cannot silently drop the redesign.

**Why this priority**: Cheap guardrail; audit found zero tests for banner/preset bar.

**Independent Test**: `test_ui_tabs` (or sibling) asserts `modernToolsPageHeader`, `modernControlPresetBar`, and Hub banner presence without starting the bridge.

**Acceptance Scenarios**:

1. **Given** Modern window construction in tests, **When** Control tab content is built, **Then** `modernToolsPageHeader` and `modernControlPresetBar` exist.
2. **Given** Modern Hub page construction, **When** inspected, **Then** page banner exists and duplicate hub title is suppressed (`show_page_header=False` behavior).

---

### User Story 6 - Stylesheet hygiene (Priority: P3)

As a maintainer editing Modern styles, I want a single authoritative rule block per Control surface object name, so QSS changes do not drift across duplicates.

**Why this priority**: Prevents subtle theme bugs; zero operator-visible risk if done correctly.

**Independent Test**: `modern_styles.py` contains one `QWidget#modernControlTab` background declaration; Modern Control appearance unchanged in manual smoke.

**Acceptance Scenarios**:

1. **Given** the Modern stylesheet source, **When** searched for `modernControlTab`, **Then** duplicate background blocks are merged without changing rendered colors.
2. **Given** a manual launch, **When** I view Control, Hub, and Presets, **Then** page backgrounds match pre-cleanup appearance.

---

### User Story 7 - Operator guide reflects Modern Control workflow (Priority: P3)

As a new operator reading `docs/OPERATOR_GUIDE.md`, I want a short description of the Modern Control page (banner, preset strip, Hub handoff, top-chips vs sidebar), so field setup docs match what they see on screen.

**Why this priority**: Documentation lag after UI redesign; low risk additive doc.

**Independent Test**: Guide mentions Modern Control sections and tools navigation toggle; no stale references to pre-v1.32.6 Control-only layout.

**Acceptance Scenarios**:

1. **Given** OPERATOR_GUIDE Connect/Control section, **When** I read setup steps, **Then** they reference Presets or Hub before Start and mention the preset summary strip on Control.
2. **Given** tools navigation, **When** I read the guide, **Then** View → Tools navigation (Sidebar / Top chips) is documented in one paragraph.

---

### Edge Cases

- Preset loaded but intent hint suppressed by empty preset name edge case: strip stays hidden, no orphan icon.
- Advanced network expanded while map expanded: both sections scroll/reflow without overlapping footer version line.
- Theme slate remains the only Modern theme; polish must not assume light mode.
- Standard/Field `connectGroupBox` styling unchanged—operators on legacy layouts see no delta.
- Hub page with `show_page_header=False` must not regress Refresh/Unlock toolbar placement.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-201**: Control preset summary MUST use the shared **live status** visual system (`statusKind` semantics: idle / ready / recording / error) aligned with Presets tab loaded/preview states—not a bespoke color scheme for the same meaning.
- **FR-202**: A single reusable helper or component pattern SHOULD back Presets live status and Control preset strip styling to avoid future drift (implementation detail deferred to plan).
- **FR-203**: Advanced network panel (`advancedNetPanel`) MUST inherit Modern Control form field, label, checkbox, and radio styling when visible inside the Network card.
- **FR-204**: Control preset strip icon MUST differ semantically from Activity page banner icon.
- **FR-205**: Position track section title MUST align with Serial/Network section title hierarchy (within one typographic step).
- **FR-206**: At window minimum **640×420**, Serial and Network form cards MUST remain side-by-side (regression requirement).
- **FR-207**: Vertical stack responsive behavior MUST be either removed or documented as test-only/sub-minimum with constant comment and test alignment.
- **FR-208**: Unit tests MUST verify Control page banner and preset bar widgets exist on Modern window init.
- **FR-209**: Unit tests MUST verify Hub page uses flat page banner without duplicate Connection hub title.
- **FR-210**: `modernControlTab` stylesheet rules MUST not be duplicated in `modern_styles.py`.
- **FR-211**: `docs/OPERATOR_GUIDE.md` MUST document Modern Control layout (banner, cards, preset strip) and tools navigation modes in ≤2 short subsections.

### Key Entities

- **Preset summary state**: idle (hidden), ready (loaded preset name + path summary), preview (selected but not loaded—Presets only; Control shows loaded/active only).
- **Control page chrome**: page header, form cards, preset strip, position track card—each independently styled but one hierarchy.
- **Responsive threshold**: window width constant governing side-by-side vs stacked forms; must not break minimum-size layout.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-201**: In a three-person visual review (or single operator checklist), **100%** identify loaded preset status on Control and Presets as the same class of information without hesitation.
- **SC-202**: With Advanced network expanded, **zero** P0/P1 clipping defects at 640×420 in manual smoke (COM, fan-out, and TCP client host rows readable).
- **SC-203**: Automated suite adds **≥2** new Modern Control/Hub chrome tests; all existing `test_ui_tabs` Modern tests pass.
- **SC-204**: Stylesheet search shows **one** `modernControlTab` background block; manual theme spot-check shows no visible delta on Control/Hub/Presets.
- **SC-205**: OPERATOR_GUIDE updated sections are ≤150 words combined and mention Hub + Presets handoff before Start.

---

## Assumptions

- Operators primarily use **Modern** UI; Field/Standard polish is out of scope.
- **Slate** theme remains default; no new theme work required.
- Preset “preview” (selected-not-loaded) stays Presets-tab-only; Control strip reflects **loaded/active** preset via existing intent hint text.
- Side-by-side forms at minimum width remain acceptable density (operator approved v1.32.7).
- Version bump **patch** per shipped story group; minor if a shared status component is extracted.

---

## Implementation Priority (ordered backlog)

| Order | ID | Story | Audit source |
|-------|-----|-------|----------------|
| 1 | US1 | Preset status parity | P2 — unify preset strip with Presets |
| 2 | US2 | Advanced network styling | P2 — `advancedNetPanel` in Network card |
| 3 | US3 | Icons + typography | P2 — 📋 collision, map title hierarchy |
| 4 | US4 | Responsive clarity | P3 — stack path / min-width guard |
| 5 | US5 | Layout tests | P3 — banner + preset bar + Hub |
| 6 | US6 | QSS dedupe | P3 — `modernControlTab` duplicate |
| 7 | US7 | Operator guide | P3 — doc pass |

---

## Dependencies

- Existing `_modern_flat_page`, `modernToolsLiveStatus`, `modernControlPresetBar`, `apply_compact_intent_hint`.
- v1.32.7 Control layout must remain stable while polish lands incrementally.
