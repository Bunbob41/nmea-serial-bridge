# Feature Specification: Baseline Cleanup and Version Sync

**Feature Branch**: `2028-baseline-version-sync`

**Created**: 2026-05-20

**Status**: Draft

**Input**: User description: "Baseline cleanup and version sync"

**Extends**: [`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md) (FR/SC traceability baseline)

## Purpose

Close gaps identified after baseline delivery and `/speckit-analyze`: align **release
metadata**, **baseline spec artifacts**, and **operator-facing version labels** so
`version.py`, Windows exe metadata, README, and `specs/001-baseline-spec/*` tell one
consistent story — without changing bridge protocol behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Release metadata matches app version (Priority: P1)

A release engineer packages a frozen build and expects the exe **FileVersion** /
**ProductVersion** to match `version.py` and the window title.

**Why this priority**: Constitution Principle IV; operators and IT use exe properties for support tickets.

**Independent Test**: After sync, `version_info.txt` strings equal `version.py`; smoke build or `tools/sync_version_info.py` dry-run passes.

**Acceptance Scenarios**:

1. **Given** `version.py` is 1.4.10, **When** version resource is synced, **Then** `version_info.txt` reports 1.4.10 for FileVersion and ProductVersion.
2. **Given** a frozen build is produced, **When** the operator inspects exe properties, **Then** version matches `__version__` within the same release.

---

### User Story 2 - Baseline spec artifacts are internally consistent (Priority: P1)

A developer opening `specs/001-baseline-spec/` understands which version is **documented
behavior** (v1.4.9 core + v1.4.9 auto-discovery) versus **doc-delivery patch** (v1.4.10).

**Why this priority**: Removes analyze finding I1/I3 confusion for future `/speckit-plan` deltas.

**Independent Test**: Read spec, plan, traceability, assumptions — no contradictory “no code” vs bench-helper wording; version footnotes present.

**Acceptance Scenarios**:

1. **Given** baseline spec Purpose section, **When** a reader checks version references, **Then** behavior baseline (1.4.9+) and doc release (1.4.10) are both labeled explicitly.
2. **Given** assumptions about delivery scope, **When** read alongside plan, **Then** text states **no bridge protocol changes** while allowing docs and bench helpers.

---

### User Story 3 - Baseline FR coverage includes auto-discovery (Priority: P2)

Integrators referencing the baseline FR list see **USB GNSS auto-connect** (shipped in
v1.4.9) documented or explicitly deferred with rationale.

**Why this priority**: Analyze finding U1 — live feature absent from FR-001–FR-020.

**Independent Test**: `traceability.md` contains FR-021 row OR assumptions document deferral with link to CHANGELOG v1.4.9.

**Acceptance Scenarios**:

1. **Given** auto-discovery is in the product, **When** baseline traceability is updated, **Then** FR-021 maps to `auto_discovery.py`, Connect checkbox, and `test_auto_discovery.py`.
2. **Given** Field layout operators, **When** they read baseline clarifications, **Then** fan-out control location (Standard Connect vs Field Tools path) is documented.

---

### User Story 4 - Verification status is honest (Priority: P2)

QA or Argo can see whether `verify_all.py` was green for this cleanup or which steps were waived and why.

**Why this priority**: Analyze finding C1 — T015 marked complete despite environmental failures.

**Independent Test**: `traceability.md` or `specs/002-*/quickstart.md` records verify outcome or waiver template.

**Acceptance Scenarios**:

1. **Given** a clean bench (UDP 10110 free), **When** `verify_all.py` runs, **Then** result is recorded in traceability notes with date.
2. **Given** `bench_gui_smoke` cannot run headless, **When** documented, **Then** waiver explains environment constraint without claiming full green.

---

### Edge Cases

- Version bump not required if only metadata sync (may stay 1.4.10 patch vs 1.4.11 — see plan).
- `sync_version_info.py` missing or broken → manual edit of `version_info.txt` with test guard.
- Editing `001-baseline-spec` must not rewrite approved history; prefer additive footnotes and FR-021.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-101**: `version_info.txt` MUST match `version.py` `__version__` for FileVersion and ProductVersion before any release handoff.
- **FR-102**: `specs/001-baseline-spec/spec.md`, `plan.md`, and `traceability.md` MUST state behavior baseline version (1.4.9+) and doc delivery version (1.4.10) without contradiction.
- **FR-103**: Baseline assumptions MUST clarify scope: no `bridge_core.py` / `nmea_codec.py` protocol changes; docs and bench helpers allowed.
- **FR-104**: Baseline traceability MUST add **FR-021** for auto-discovery or document explicit deferral in assumptions with CHANGELOG reference.
- **FR-105**: Operator-facing baseline notes MUST document where **fan-out** is configured in Field vs Standard layouts.
- **FR-106**: Traceability or this feature’s quickstart MUST record `verify_all.py` run outcome (pass, fail with reason, or waived steps) after cleanup.
- **FR-107**: A automated test MUST guard version alignment (extend `test_baseline_docs.py` or add `test_version_sync.py`).
- **FR-108**: `README.md` MUST remain aligned with fan-out default-on wording after cleanup (no regression to “last sender only” as sole description).

**Supersedes / modifies**: None of FR-001–FR-020 behavior; amends **documentation and metadata** only.

### Key Entities

- **Version triple**: `version.py`, `version_info.txt`, README/CHANGELOG headline version.
- **Baseline artifact set**: `specs/001-baseline-spec/*` reference documents.
- **Verification record**: Dated note of verify_all outcome tied to FR-106.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: `version_info.txt` and `version.py` show identical semver in 100% of automated checks (CI or `test_version_sync`).
- **SC-102**: Zero conflicting version strings across `001-baseline-spec` core trio (spec, plan, traceability) after edit.
- **SC-103**: FR-021 present in traceability with at least one automated and one manual verification path listed.
- **SC-104**: `python -m unittest discover` including version/baseline tests passes.
- **SC-105**: Analyze report items I1, I2, I3 marked resolved in CHANGELOG or `002` feature completion notes.

## Assumptions

- Current `version.py` remains **1.4.10** unless cleanup discovers other drift requiring **1.4.11** patch (plan will decide).
- `tools/sync_version_info.py` exists or equivalent manual sync is documented in plan.
- Bridge runtime behavior is frozen; this feature is **metadata + documentation** only.
- Extends baseline spec `001`; does not replace it.

## Dependencies

- Completed [`specs/001-baseline-spec`](../001-baseline-spec/) delivery.
- `/speckit-analyze` findings (I1, I2, I3, C1, U1, U2) as input checklist.
