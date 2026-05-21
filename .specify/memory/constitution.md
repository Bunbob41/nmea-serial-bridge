<!--
Sync Impact Report
Version change: (template) → 1.0.0
Modified principles: N/A (initial ratification from placeholder template)
Added sections: Core Principles (5), Technical Constraints, Development Workflow & Quality Gates, Governance
Removed sections: None
Templates: plan-template.md ✅ updated | spec-template.md ✅ (no change required) | tasks-template.md ✅ updated
Follow-up TODOs: None
-->

# NMEA Serial Bridge Constitution

## Core Principles

### I. Bridge-Core Separation

All bidirectional serial ↔ network I/O MUST live in `bridge_core.py` and `nmea_codec.py`.
The GUI layer (`bridge_gui.py`, `ui/`) MUST NOT embed bridge protocol logic.
Rationale: keeps asyncio bridge testable, reusable, and free of Qt thread hazards.

### II. Survey Operator Trust (NON-NEGOTIABLE)

Features MUST serve INS/GNSS UDP or TCP → serial COM for survey targets, or bench
com0com testing. Operator-visible behavior MUST prioritize clarity over raw protocol
noise: connect → run → monitor status/drops/HUD. Start/Stop and connection health MUST
remain discoverable at launch in every UI mode (Standard, Field, HUD).
Rationale: field operators lose trust when controls hide or status lies under load.

### III. Verifiable Changes

Substantive bridge or codec changes MUST include or update automated coverage in
`test_*.py` and pass `python verify_all.py` plus `python -m unittest discover -s . -p "test_*.py"`
before merge. Bench scripts (`bench_udp_test.py`, com0com pair) SHOULD be cited in the
plan when behavior is network- or serial-timing sensitive.
Rationale: regressions in NMEA assembly, backpressure, or reconnect are costly in the field.

### IV. Version & Release Discipline

User-facing or behavioral changes MUST bump `version.py` (`__version__`) and add a
`## vX.Y.Z` section to `CHANGELOG.md` per semver (patch/minor/major). Frozen builds MUST
keep `version_info.txt` aligned with `version.py` when packaging metadata changes.
Rationale: operators and support need a single source of truth across exe, window title, and zip.

### V. Resilience & Bounded Resources

Bridge queues MUST stay bounded; drop/reject counters MUST remain accurate. UI updates
from the bridge thread MUST be rate-limited or coalesced so disconnect storms and HUD
resize do not freeze Qt. Raw binary (RTCM) passthrough MUST NOT corrupt bytes via NMEA
assembly. Prefer graceful degradation over lockups.
Rationale: survey links run for hours under bursty INS output and flaky USB serial.

## Technical Constraints

- **Stack**: Python 3.10+, PySide6, pyserial-asyncio; Windows is the primary target.
- **Threading**: asyncio on a background thread; Qt on the main thread only.
- **Scope**: Focused survey Ethernet ↔ COM bridge; NOT a general serial router, MAVLink
  planner, GNSS post-processor, or kernel virtual-COM/sniffer unless explicitly requested.
- **Dependencies**: No new mandatory packages without justification in the feature plan.
- **Multi-endpoint**: Software fan-out (UDP listen peers, optional future taps/sinks) is
  in scope; arbitrary N×M serial hubs and kernel drivers are out of scope by default.
- **UI layout**: Connect section order via UI editor; do not re-add inline layout editors
  unless the user asks. Required Connect sections: `run`, `connection`.

## Development Workflow & Quality Gates

- Spec Kit features live under `specs/[###-feature-name]/` with `spec.md`, `plan.md`,
  `tasks.md` produced by `/speckit-specify` → `/speckit-plan` → `/speckit-tasks`.
- `/speckit-implement` MUST satisfy tasks and re-run constitution gates before claiming done.
- Operator-visible changes SHOULD update `docs/OPERATOR_GUIDE.md`.
- Cursor rules under `.cursor/rules/` (Argo charter, bridge resilience, HUD stability, UI
  polish, version-on-change) complement this constitution; conflicts resolve in favor of
  this file for Spec Kit planning gates.
- Release handoff: compile edited modules, verification suite when feasible, no debug
  leftovers, primary workflow visible in all UI modes.

## Governance

This constitution supersedes ad-hoc feature scope during Spec Kit `/speckit-plan` and
`/speckit-analyze` gates. Amendments require updating this file, bumping
**CONSTITUTION_VERSION** (semver), setting **Last Amended** to the change date, and
propagating impacts to `.specify/templates/*` and operator docs when principles change.

All feature plans MUST include a **Constitution Check** with explicit pass/fail per
principle; unjustified violations require an entry in **Complexity Tracking**.

Compliance review expectations:

- Specs: user stories independently testable; acceptance scenarios for P1 paths.
- Plans: Technical Context filled for this repo (not generic placeholders).
- Tasks: file paths named; bridge tests when Principles III or V apply.
- Implementation: version bump + CHANGELOG when shipping substantive work.

**Version**: 1.0.0 | **Ratified**: 2026-05-20 | **Last Amended**: 2026-05-20
