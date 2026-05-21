# Implementation Plan: Product Baseline (As-Built)

**Branch**: `2027-baseline-spec` | **Date**: 2026-05-20 | **Spec**: [spec.md](./spec.md)

**Input**: Baseline spec ratifying v1.4.9 behavior for Spec Kit traceability.

## Summary

Deliver **documentation and traceability artifacts** that align operator-facing docs with
as-built behavior (especially UDP fan-out), map FR-001–FR-020 to verification paths, and
add a reproducible two-client bench procedure — **without** changing bridge protocol logic.

## Technical Context

**Language/Version**: Python 3.10+ (existing repo); documentation in Markdown  
**Primary Dependencies**: None new — uses existing `bench_udp_test.py`, `verify_all.py`  
**Storage**: User presets (`path_presets.json`); spec artifacts under `specs/001-baseline-spec/`  
**Testing**: `python verify_all.py`; `python -m unittest discover`; manual bench fan-out steps  
**Target Platform**: Windows desktop (primary)  
**Project Type**: Desktop bridge app + operator docs  
**Performance Goals**: N/A (docs-only delta)  
**Constraints**: No `bridge_core.py` behavior changes; constitution Principles I & V unchanged  
**Scale/Scope**: README, OPERATOR_GUIDE, traceability matrix, quickstart, one optional bench helper script

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|-----------|------|--------|
| I. Bridge-Core Separation | Docs only; no protocol logic in UI | ✅ PASS |
| II. Survey Operator Trust | Fan-out testing clarified; Start/Stop unchanged | ✅ PASS |
| III. Verifiable Changes | Traceability doc + verify_all run | ✅ PASS |
| IV. Version & Release | Patch bump + CHANGELOG for doc alignment | ✅ PASS |
| V. Resilience & Bounded Resources | No queue/engine changes | ✅ PASS |

**Gate result**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-baseline-spec/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── traceability.md
├── contracts/
│   ├── bridge-session.md
│   └── udp-fanout.md
├── tasks.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
bridge_core.py          # reference only (no edits planned)
nmea_codec.py
bridge_gui.py
ui/
docs/
├── OPERATOR_GUIDE.md   # update: fan-out bench procedure
README.md               # update: fan-out default, version line
bench_fanout_probe.py   # optional: two-client UDP probe (new)
test_udp_fanout.py      # existing — cited in traceability
```

**Structure Decision**: Single-repo desktop app; baseline work touches `docs/`, `README.md`,
and `specs/001-baseline-spec/` only.

## Complexity Tracking

> No violations — documentation-only delivery.
