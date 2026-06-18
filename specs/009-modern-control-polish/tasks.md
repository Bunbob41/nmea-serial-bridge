---
description: "Task list for Modern Control Tab Polish (009)"
---

# Tasks: Modern Control Tab Polish

**Input**: Design documents from `/specs/009-modern-control-polish/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Constitution Principle III — `test_ui_tabs.py` chrome tests + `verify_all.py` gates per quickstart.md.

**Organization**: Tasks grouped by user story (US1–US7) for independent delivery; **MVP = Phase 3 (US1)**.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to spec user stories US1–US7
- Include exact file paths in descriptions

## Path Conventions

- UI: `ui/` at repository root
- Tests: `test_*.py` at repository root
- Docs: `docs/OPERATOR_GUIDE.md`
- Spec: `specs/009-modern-control-polish/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch context and baseline before edits

- [x] T001 Verify branch `2035-modern-control-polish` and read contracts in `specs/009-modern-control-polish/contracts/control-preset-status-parity.md` and `specs/009-modern-control-polish/contracts/advanced-network-modern-styling.md`
- [x] T002 [P] Run `python -m py_compile ui/modern.py ui/modern_styles.py ui/mixin.py ui/tool_tabs.py` to confirm baseline compiles

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared live-status helper required by US1 and mixin Presets refresh

**⚠️ CRITICAL**: No user story implementation until T003 completes

- [x] T003 Create `ui/modern_live_status.py` with `apply_modern_live_status()`, `summary_kind_to_status_kind()`, and `create_modern_live_status_label()` per `specs/009-modern-control-polish/contracts/control-preset-status-parity.md`

**Checkpoint**: Foundation ready — user story phases may begin

---

## Phase 3: User Story 1 — Preset status parity (Priority: P1) 🎯 MVP

**Goal**: Control preset strip uses same `modernToolsLiveStatus` / `statusKind=ready` family as Presets loaded state (FR-201/202)

**Independent Test**: Load a preset; Presets green “Loaded:” and Control strip match; strip hidden when empty (quickstart §2)

### Tests for User Story 1

- [x] T004 [P] [US1] Add `test_summary_kind_to_status_kind` in `test_modern_live_status.py` covering `ok→ready`, `idle→idle`

### Implementation for User Story 1

- [x] T005 [US1] Change Control `intent_hint` to `objectName="modernToolsLiveStatus"` inside preset strip in `ui/modern.py` `_build_control_tab()`
- [x] T006 [US1] Update `_apply_intent_hint_display()` in `ui/modern.py` to call `apply_modern_live_status()` with `statusKind="ready"` when hint text is non-empty
- [x] T007 [US1] Refactor `_apply_live_chip()` in `ui/mixin.py` to delegate to `apply_modern_live_status()` from `ui/modern_live_status.py`
- [x] T008 [US1] Remove bespoke blue `QFrame#modernControlPresetBar` QSS; use transparent/minimal frame styling in `ui/modern_styles.py`
- [x] T009 [P] [US1] Replace `_modern_live_status_label()` in `ui/tool_tabs.py` with import from `ui/modern_live_status.py`

**Checkpoint**: US1 complete — preset visual parity shippable as MVP patch

---

## Phase 4: User Story 2 — Advanced network styling (Priority: P2)

**Goal**: Expanded `advancedNetPanel` matches Network card field styling at 640×420 (FR-203)

**Independent Test**: Enable Advanced network at minimum window; host/port fields readable (quickstart §3)

### Implementation for User Story 2

- [x] T010 [US2] Add `QFrame#modernControlFormCard QWidget#advancedNetPanel` descendant QSS (GroupBox, QLineEdit, QRadioButton, QLabel) in `ui/modern_styles.py` per `specs/009-modern-control-polish/contracts/advanced-network-modern-styling.md`

**Checkpoint**: US2 complete — advanced net visually integrated in Network card

---

## Phase 5: User Story 3 — Visual hierarchy and icon clarity (Priority: P2)

**Goal**: Distinct preset icon; Position track title aligned with section titles (FR-204/205)

**Independent Test**: Control preset uses 📌 not 📋; map title matches Serial/Network hierarchy (quickstart §4)

### Implementation for User Story 3

- [x] T011 [P] [US3] Change preset strip icon from 📋 to 📌 in `ui/modern.py` `_build_control_tab()`
- [x] T012 [P] [US3] Update `QLabel#modernControlMapTitle` to 11pt / font-weight 700 in `ui/modern_styles.py` to match `modernControlSectionTitle`

**Checkpoint**: US3 complete — no icon collision with Activity banner

---

## Phase 6: User Story 4 — Responsive layout clarity (Priority: P3)

**Goal**: Side-by-side at 640×420 preserved; stack threshold documented as sub-minimum test-only (FR-206/207)

**Independent Test**: `test_modern_control_forms_stack_narrow` passes; 640px asserts horizontal layout

### Implementation for User Story 4

- [x] T013 [US4] Expand `CONTROL_FORMS_STACK_BELOW_W` comment in `ui/modern.py` documenting sub-minimum (520px) test-only intent per `specs/009-modern-control-polish/research.md` R4

**Checkpoint**: US4 complete — responsive behavior documented and regression-tested

---

## Phase 7: User Story 5 — Automated chrome coverage (Priority: P3)

**Goal**: Unit tests guard Control banner/preset bar and Hub banner (FR-208/209, SC-203)

**Independent Test**: New tests pass without starting bridge

### Tests for User Story 5

- [x] T014 [P] [US5] Add `test_modern_control_page_chrome` in `test_ui_tabs.py` asserting `modernToolsPageHeader`, `modernControlPresetBar`, and `modernToolsLiveStatus` on intent hint
- [x] T015 [P] [US5] Add `test_modern_hub_page_banner` in `test_ui_tabs.py` asserting Hub page header exists and `connectionHubTitle` is absent on Modern Hub page

**Checkpoint**: US5 complete — chrome regressions caught in CI/local unittest

---

## Phase 8: User Story 6 — Stylesheet hygiene (Priority: P3)

**Goal**: Single authoritative `modernControlTab` background rule (FR-210, SC-204)

**Independent Test**: `rg modernControlTab ui/modern_styles.py` shows one background block; manual theme spot-check unchanged

### Implementation for User Story 6

- [x] T016 [US6] Merge duplicate `QWidget#modernControlTab` background declarations into one block in `ui/modern_styles.py`

**Checkpoint**: US6 complete — no QSS duplication for Control tab root

---

## Phase 9: User Story 7 — Operator guide (Priority: P3)

**Goal**: Document Modern Control layout and tools navigation toggle (FR-211, SC-205)

**Independent Test**: Guide mentions banner, cards, preset strip, Hub/Presets handoff, View → Tools navigation in ≤150 words combined

### Implementation for User Story 7

- [x] T017 [US7] Add Modern Control layout and View → Tools navigation (Sidebar / Top chips) subsections to `docs/OPERATOR_GUIDE.md`

**Checkpoint**: US7 complete — operator docs match v1.33.0 UI

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Release gates and verification

- [x] T018 Bump `version.py` to `1.33.0` and add `## v1.33.0` section to `CHANGELOG.md` summarizing US1–US7
- [x] T019 [P] Align `version_info.txt` with `version.py` if release packaging metadata changed
- [x] T020 Run automated gates from `specs/009-modern-control-polish/quickstart.md` (`test_ui_tabs`, `test_modern_live_status`, `verify_all.py`, full unittest discover)
- [ ] T021 Manual smoke at 640×420: preset parity, advanced net expanded, Hub banner, sidebar + top-chips nav per quickstart §2–6

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on T003 — **MVP**
- **US2 (Phase 4)**: Depends on T003; independent of US1 (different QSS region)
- **US3 (Phase 5)**: Independent of US2; can run parallel after US1 if desired
- **US4 (Phase 6)**: Independent comment/test doc task
- **US5 (Phase 7)**: Tests best after US1 (T005–T008) for chrome assertions
- **US6 (Phase 8)**: Can run after US1/US2 QSS edits to avoid merge conflicts
- **US7 (Phase 9)**: Independent doc task
- **Polish (Phase 10)**: Depends on all desired story phases complete

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | T003 | Load preset → Control/Presets same status family |
| US2 | T003 | Advanced net expanded at min width |
| US3 | — | Icon + typography scan |
| US4 | — | unittest 640px horizontal |
| US5 | US1 layout (T005) for chrome test | unittest chrome tests |
| US6 | US1/US2 QSS land | grep + visual spot-check |
| US7 | — | OPERATOR_GUIDE word count |

### Parallel Opportunities

- **T002** ∥ **T001**
- **T009** ∥ **T008** (after T006–T007)
- **T011** ∥ **T012** (US3)
- **T014** ∥ **T015** (US5)
- **T010** can start after T003 in parallel with US1 implementation (different QSS section)
- **T017** can run anytime after plan read

### Parallel Example: User Story 1

```bash
# After T003, in parallel:
# T004 test_modern_live_status.py (kind mapping tests)
# T009 ui/tool_tabs.py (factory import)

# Then sequential on ui/modern.py:
# T005 → T006, plus T007 ui/mixin.py, T008 ui/modern_styles.py
```

### Parallel Example: Post-MVP (US2 + US3)

```bash
# After US1 checkpoint:
# T010 ui/modern_styles.py (advancedNetPanel)
# T011 ui/modern.py + T012 ui/modern_styles.py (icons/typography)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1–2 (T001–T003)
2. Complete Phase 3 US1 (T004–T009)
3. **STOP and VALIDATE**: quickstart §2 preset parity
4. Optional patch release if stopping early

### Incremental Delivery

1. US1 → preset parity (highest operator value)
2. US2 + US3 → network styling + visual hierarchy (parallel-friendly)
3. US4–US6 → maintainability + tests
4. US7 + Polish → docs and v1.33.0 release

### Suggested `/speckit-implement` order

`T001→T003→T004–T009→T010→T011–T012→T013→T014–T015→T016→T017→T018–T021`

---

## Notes

- Do **not** modify `bridge_core.py`, `nmea_codec.py`, or Field/Standard `connectGroupBox` paths
- Preserve v1.32.7 side-by-side layout at 640×420 (regression)
- Commit after each user story checkpoint or when user requests git commit
