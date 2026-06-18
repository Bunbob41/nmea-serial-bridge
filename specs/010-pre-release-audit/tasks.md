---
description: "Task list for Pre-Release Full App Audit (010)"
---

# Tasks: Pre-Release Full App Audit

**Input**: Design documents from `/specs/010-pre-release-audit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Constitution Principle III — extend `test_app_icon.py`, wire into `verify_all.py`; full unittest discover + frozen bundle gates per quickstart.md.

**Organization**: Tasks grouped by user story (US1–US7); **MVP = Phase 3 (US1 — EXE icon fix)**.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to spec user stories US1–US7
- Include exact file paths in descriptions

## Path Conventions

- Assets: `assets/` at repository root
- Tools/scripts: `tools/`, `build.ps1`, `release.ps1`, `verify_all.py`
- Tests: `test_*.py` at repository root
- Docs: `docs/pre-release-audit-inventory.md`, `CHANGELOG.md`, `README.md`
- Spec: `specs/010-pre-release-audit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch context, contracts, and icon baseline before edits

- [x] T001 Verify branch `2036-pre-release-audit` and read contracts in `specs/010-pre-release-audit/contracts/app-icon-acceptance.md`, `specs/010-pre-release-audit/contracts/release-readiness-gate.md`, and `specs/010-pre-release-audit/contracts/modern-ui-audit-matrix.md`
- [x] T002 [P] Run `python -m unittest test_app_icon.py -v` and note whether `assets/app-icon-source.png` exists (baseline for PKG-ICON-01)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Audit inventory skeleton required before tracking fixes across user stories

**⚠️ CRITICAL**: No user story work can begin until T003 completes

- [x] T003 Create `docs/pre-release-audit-inventory.md` with seed rows from `specs/010-pre-release-audit/spec.md`, verification log table, and ship-gate header per `specs/010-pre-release-audit/contracts/modern-ui-audit-matrix.md`

**Checkpoint**: Foundation ready — user story phases may begin

---

## Phase 3: User Story 1 — Recognizable app icon (Priority: P1) 🎯 MVP

**Goal**: Frozen EXE, taskbar, title bar, and shortcuts show readable connector branding—not a blue square (FR-401–403, SC-401)

**Independent Test**: `python tools/make_app_icon.py` logs `from app-icon-source.png`; `test_app_icon.py` passes; manual checklist in `specs/010-pre-release-audit/contracts/app-icon-acceptance.md` signed off

### Tests for User Story 1

- [x] T004 [P] [US1] Add `test_16px_shell_layer_has_bright_glyph` and require `(16, 16)` in `test_ico_includes_windows_dpi_sizes` in `test_app_icon.py`

### Implementation for User Story 1

- [x] T005 [US1] Add or restore `assets/app-icon-source.png` with bold RJ-45/DB-9 connector on white/transparent matte per `assets/README.md`
- [x] T006 [US1] Tune shell-tier contrast in `tools/make_app_icon.py` (e.g. `SHELL_INK_FILL`, `SHELL_DILATE_PX`, brighten glyph for ≤48px layers) per `specs/010-pre-release-audit/research.md` R1
- [x] T007 [US1] Regenerate `assets/app-icon.png` and `assets/app-icon.ico` via `python tools/make_app_icon.py`; confirm console logs `from app-icon-source.png`
- [x] T008 [US1] Add `test_app_icon.py` as a step in `verify_all.py` per `specs/010-pre-release-audit/contracts/app-icon-acceptance.md`
- [x] T009 [P] [US1] Add `assets/app-icon.ico` and `assets/app-icon.png` to `tools/frozen_bundle_manifest.py` `FROZEN_STATIC_FILES`
- [x] T010 [US1] Invoke `python tools/make_app_icon.py` before PyInstaller in `release.ps1` `-SkipTests` path (mirror `build.ps1`)
- [x] T011 [US1] Run full `build.ps1` or `release.ps1` (no `-SkipTests`); complete manual icon checklist in `specs/010-pre-release-audit/contracts/app-icon-acceptance.md` on `dist/serial-link/serial-link.exe`
- [x] T012 [US1] Mark `PKG-ICON-01` **fixed** with version note in `docs/pre-release-audit-inventory.md`

**Checkpoint**: US1 complete — icon shippable as MVP; SC-401 satisfied

---

## Phase 4: User Story 2 — Release audit inventory (Priority: P1)

**Goal**: Single audit document with P0/P1/P2 rows, ship gates, and link to 008 history (FR-404–406)

**Independent Test**: `docs/pre-release-audit-inventory.md` exists; P0 filter documented; cross-ref to 008 inventory without duplicate STD/FIELD rows

### Implementation for User Story 2

- [x] T013 [US2] Add header cross-links to `docs/ui-audit-inventory.md` and `specs/010-pre-release-audit/contracts/modern-ui-audit-matrix.md` in `docs/pre-release-audit-inventory.md`
- [x] T014 [US2] Add ship-gate summary (P0=0, P1 deferred rules) to `docs/pre-release-audit-inventory.md` per `specs/010-pre-release-audit/contracts/release-readiness-gate.md`
- [x] T015 [US2] Mark `AUDIT-INV-01` **fixed** in `docs/pre-release-audit-inventory.md`

**Checkpoint**: US2 complete — inventory process active for remaining stories

---

## Phase 5: User Story 3 — Modern UI polish pass (Priority: P1)

**Goal**: All Modern tools pages readable at 640×420 and 1280×720; zero open P0 from UI pass (FR-407–408, SC-403)

**Independent Test**: Quickstart §3 checklist logged in verification table; any P0 fixed or release held

### Implementation for User Story 3

- [x] T016 [US3] Run Modern UI checklist at **640×420** with **sidebar** nav (Control, Hub, Presets, Phone minimum) per `specs/010-pre-release-audit/quickstart.md` §3; append row to verification log in `docs/pre-release-audit-inventory.md`
- [x] T017 [US3] Repeat checklist at **640×420** with **top-chips** nav; log in `docs/pre-release-audit-inventory.md`
- [x] T018 [US3] Run full **1280×720** pass on all 11 Modern nav pages; add `MOD-*` rows for findings in `docs/pre-release-audit-inventory.md`
- [x] T019 [P] [US3] Fix any **P0** Modern layout defects in `ui/modern.py`, `ui/tool_tabs.py`, and/or `ui/modern_styles.py` as identified in T016–T018
- [x] T020 [P] [US3] Add regression tests in `test_ui_tabs.py` for any P1 layout fixes that warrant automation
- [x] T021 [US3] Record 009 manual smoke outcome as `MOD-SMOKE-01` in `docs/pre-release-audit-inventory.md` verification log

**Checkpoint**: US3 complete — zero open P0 from Modern UI pass

---

## Phase 6: User Story 4 — Packaging and version integrity (Priority: P2)

**Goal**: version.py, version_info.txt, exe Properties, and zip name agree; frozen bundle passes (FR-409–411, SC-404–SC-405)

**Independent Test**: `sync_version_info.py` + `check_frozen_bundle.py dist/serial-link` exit 0; exe Details version matches `version.py`

### Implementation for User Story 4

- [x] T022 [US4] Run `python tools/sync_version_info.py` and confirm `version_info.txt` matches `version.py`
- [x] T023 [US4] Run `python tools/check_frozen_bundle.py dist/serial-link` after build; confirm `assets/app-icon.ico` present
- [x] T024 [US4] Verify exe **Properties → Details** version and window title match `version.py` (SC-405)
- [x] T025 [US4] Mark `PKG-VERSION-01` **fixed** in `docs/pre-release-audit-inventory.md`

**Checkpoint**: US4 complete — packaging metadata verified

---

## Phase 7: User Story 5 — Core bridge reliability spot-check (Priority: P2)

**Goal**: Automated suite green; bridge trust documented (FR-415–416)

**Independent Test**: `verify_all.py` and full unittest discover exit 0; spot-check noted in verification log

### Implementation for User Story 5

- [x] T026 [US5] Run `python verify_all.py` and `python -m unittest discover -s . -p "test_*.py"`; fix any failures on release branch
- [x] T027 [US5] Document bridge spot-check (automated-only or com0com bench) in `docs/pre-release-audit-inventory.md` verification log

**Checkpoint**: US5 complete — constitution Principle III satisfied

---

## Phase 8: User Story 6 — GitHub release narrative (Priority: P2)

**Goal**: CHANGELOG, README, OPERATOR_GUIDE ready for public release (FR-412–414, SC-406)

**Independent Test**: README zip path matches `release.ps1` output; CHANGELOG top section covers icon + audit fixes

### Implementation for User Story 6

- [x] T028 [P] [US6] Add `## v1.34.0` section to `CHANGELOG.md` summarizing icon fix and closed audit IDs
- [x] T029 [P] [US6] Verify `README.md` frozen-build instructions match `dist/serial-link/serial-link.exe` and `serial-link-vX.Y.Z-win64.zip` naming
- [x] T030 [US6] Confirm `docs/OPERATOR_GUIDE.md` SmartScreen install line; mark `DOC-SMART-01` **fixed** in `docs/pre-release-audit-inventory.md`

**Checkpoint**: US6 complete — release notes ready for `gh release`

---

## Phase 9: User Story 7 — Explicit deferrals (Priority: P3)

**Goal**: Honest scope—ROADMAP and unfixed P2 listed (FR-406 deferred path)

**Independent Test**: Inventory deferred section + CHANGELOG Deferred bullets; no hidden known-broken items

### Implementation for User Story 7

- [x] T031 [US7] Add deferred section in `docs/pre-release-audit-inventory.md` for `ROADMAP-SCOPE-01` and any open P2 rows
- [x] T032 [US7] Add **Deferred** subsection to `CHANGELOG.md` for any open P1 with one-line operator impact each

**Checkpoint**: US7 complete — post-release backlog visible

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Version bump, full gate run, release artifact

- [x] T033 Bump `version.py` to **1.34.0** and run `python tools/sync_version_info.py` for `version_info.txt`
- [x] T034 Run full gate sequence from `specs/010-pre-release-audit/quickstart.md` §1 (`verify_all.py`, unittest discover, `check_frozen_bundle.py`)
- [x] T035 [P] Produce `dist/serial-link-v1.34.0-win64.zip` via `.\release.ps1` (no `-Publish` until maintainer sign-off)
- [ ] T036 Complete manual sign-off for gates G1–G10 in `specs/010-pre-release-audit/contracts/release-readiness-gate.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: After Phase 2 — **MVP / release blocker** (icon)
- **US2 (Phase 4)**: After Phase 2 — can overlap US1 tail (inventory doc exists from T003)
- **US3 (Phase 5)**: After US1 recommended (icon fixed before full UI smoke on frozen build); after T003
- **US4 (Phase 6)**: After US1 (needs fresh build with icon assets)
- **US5 (Phase 7)**: After US1 T008 (verify_all includes icon tests)
- **US6 (Phase 8)**: After US1–US3 fixes known (CHANGELOG content)
- **US7 (Phase 9)**: After US3–US6 (deferrals list final open items)
- **Polish (Phase 10)**: After US1–US7 desired scope complete

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | Phase 2 | Icon tests + manual acceptance |
| US2 | Phase 2 | Inventory doc + gates documented |
| US3 | Phase 2; US1 for frozen smoke | Quickstart §3 verification log |
| US4 | US1 build | version + frozen bundle |
| US5 | US1 T008 | verify_all + unittest |
| US6 | US1–US3 content | README/CHANGELOG/OPERATOR_GUIDE |
| US7 | US3–US6 | Deferred sections populated |

### Parallel Opportunities

- **Phase 1**: T002 ∥ T001 (after T001 contracts read)
- **US1**: T004 ∥ T005 after T003; T009 ∥ T008 after T007
- **US3**: T019 ∥ T020 after T018 findings known
- **US6**: T028 ∥ T029
- **Polish**: T035 after T034

### Parallel Example: User Story 1

```text
After T003 and T004:
  T005 → T006 → T007 (sequential icon pipeline)

After T007:
  T004 (tests)  ∥  T009 (manifest)

After T008 + T010:
  T011 (manual) → T012 (inventory row)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1–2 (Setup + inventory skeleton)
2. Complete Phase 3 (US1 — icon fix + gates)
3. **STOP and VALIDATE**: Manual icon acceptance + `verify_all.py`
4. Ship patch **v1.34.0** icon fix before full audit if needed

### Incremental Delivery

1. US1 → icon fixed (release blocker cleared)
2. US2 → inventory process live
3. US3 → Modern UI pass + fixes
4. US4–US5 → packaging + bridge gates green
5. US6–US7 → docs + deferrals
6. Phase 10 → tag + zip

### Suggested `/speckit-implement` order

```text
T001–T003 → T004–T012 (US1 MVP) → T013–T015 → T016–T021 → T022–T027 → T028–T032 → T033–T036
```

---

## Notes

- Do **not** use `release.ps1 -SkipTests` for first public GitHub release
- Icon cache: if manual acceptance fails after rebuild, follow acceptance contract §F before re-tuning art
- `bridge_core.py` unchanged unless US5 discovers P0 protocol regression
- Commit regenerated `assets/app-icon.*` with source PNG when US1 completes
