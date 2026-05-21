# Tasks: Product Baseline (As-Built)

**Input**: `specs/001-baseline-spec/plan.md`, `spec.md`, `research.md`, `contracts/`

**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Traceability and spec status

- [ ] T001 Create FR traceability matrix in `specs/001-baseline-spec/traceability.md`
- [ ] T002 [P] Set spec status to Approved in `specs/001-baseline-spec/spec.md`

---

## Phase 2: Foundational (Blocking)

**Purpose**: Operator doc authority aligned with baseline

- [ ] T003 Update UDP listen and fan-out description in `README.md`
- [ ] T004 [P] Add baseline cross-link in `docs/OPERATOR_GUIDE.md` introduction

**Checkpoint**: README and operator guide reference fan-out default-on behavior

---

## Phase 3: User Story 1 — Bench bridge session (P1) 🎯 MVP

**Goal**: Bench operators can run happy-path without doc contradictions

**Independent Test**: Follow OPERATOR_GUIDE §5 with fan-out checkbox visible; Start/Stop unchanged

- [ ] T005 [US1] Expand bench workflow table for fan-out checkbox in `docs/OPERATOR_GUIDE.md` §5.2
- [ ] T006 [US1] Add com0com monitor-leg reminder to `docs/OPERATOR_GUIDE.md` §5.2

---

## Phase 4: User Story 2 — Boat / INS UDP listen (P1)

**Goal**: Boat workflow notes when multiple UDP consumers exist

**Independent Test**: Boat checklist path unchanged; §6 mentions multi-sender fan-out option

- [ ] T007 [US2] Add multi-consumer UDP note in `docs/OPERATOR_GUIDE.md` §6.2

---

## Phase 5: User Story 3 — Survey monitoring and presets (P2)

**Goal**: Presets restore fan-out per FR-010 in docs

**Independent Test**: Presets section mentions fan-out persistence

- [ ] T008 [US3] Document fan-out in preset save/load in `docs/OPERATOR_GUIDE.md` §5.3

---

## Phase 6: User Story 4 — Multi-client UDP fan-out (P2)

**Goal**: Reproducible two-client bench procedure (FR-020)

**Independent Test**: `bench_fanout_probe.py` + quickstart steps; no second bridge

- [ ] T009 [US4] Add `bench_fanout_probe.py` UDP register/listen helper at repo root
- [ ] T010 [US4] Add §5.5 two-client fan-out bench procedure in `docs/OPERATOR_GUIDE.md`
- [ ] T011 [P] [US4] Link quickstart from `specs/001-baseline-spec/quickstart.md` to new §5.5

---

## Phase 7: User Story 5 — Diagnostics and safety modes (P3)

**Goal**: Traceability covers diagnostics FR-018

**Independent Test**: traceability.md maps FR-018 to Diagnostics tab + verify_all

- [ ] T012 [US5] Complete FR-015–FR-018 rows in `specs/001-baseline-spec/traceability.md`

---

## Phase 8: Polish & Cross-Cutting

- [ ] T013 Bump `version.py` to 1.4.10 and add `CHANGELOG.md` entry for baseline docs
- [ ] T014 [P] Add `test_baseline_docs.py` asserting README fan-out keywords
- [ ] T015 Run `python verify_all.py` and `python -m unittest discover -s . -p "test_*.py"`

---

## Dependencies & Execution Order

```text
T001 → T003,T004 → T005–T012 (docs, parallel per file) → T013 → T014,T015
```

### Parallel opportunities

- T002 + T004 after T001
- T009 + T010 after T003
- T014 parallel with T013

### MVP scope

**T001 + T003 + T005 + T009 + T010** — traceability, README, bench fan-out procedure

---

## Implementation Strategy

1. Traceability matrix first (anchors FR verification).
2. README / OPERATOR_GUIDE alignment (operator trust).
3. `bench_fanout_probe.py` for SC-004 manual check.
4. Version + tests + verify suite.
