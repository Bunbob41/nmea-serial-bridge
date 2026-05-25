# Implementation Plan: UI & Workflow Journey Modernization

**Branch**: `2034-ui-journey-modernization` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)

**Input**: Comprehensive UI/workflow modernization—audit copy/layout, returning-user restore, **Product Demo state isolation** with local-only validation (no agent-browser).

**Builds on**: [001-baseline-spec](../001-baseline-spec/spec.md), [007-web-config-desktop-ux](../007-web-config-desktop-ux/spec.md), [006-phase-b-dashboard](../006-phase-b-dashboard/spec.md).

## Summary

Ship three tracks in one minor release (**1.10.0** target):

1. **UI audit** — inventory + P0 fixes across layouts (copy, placeholders, dead controls, clip at 1280×720).
2. **Returning user** — single launch-restore path for last preset + recent sessions + prefs migration (toolbar keys, panel heights).
3. **Product Demo isolation** — new `OperatorSessionSnapshot` + `DemoHostGateway`: capture on open, block preset/recent writes during demo, restore on close; presenter state stays in `ProductDemoDialog` / `DemoRunner`.

Validation is **unittest + manual quickstart + `verify_all.py`** only—no agent-browser.

## Technical Context

**Language/Version**: Python 3.10+; PySide6; existing asyncio bridge unchanged  
**Primary Dependencies**: Existing Qt widgets, `bench_config`, `ui/ui_prefs.py`; **no new mandatory pip packages**  
**Storage**: `ui_prefs.json`, `path_presets.json` (must not mutate during demo); no new snapshot-on-disk file  
**Testing**: New `test_demo_snapshot.py`; extend `test_ui_prefs.py`; manual `quickstart.md`; `verify_all.py`  
**Target Platform**: Windows 10+ desktop; web dashboard audit is copy-only  
**Performance Goals**: Demo restore &lt; 5 s; no extra bridge thread load from demo labeling  
**Constraints**: Constitution I–V; bridge_core untouched; demo steps keep production parity via same mixin entry points  
**Scale/Scope**: ~6–10 Python modules; 4 contract docs; 1 audit inventory markdown

## Constitution Check

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Demo does not add protocol logic; snapshot in `ui/` only | ✅ | ✅ |
| II. Survey Operator Trust | Restore preserves run/stop; Start/Stop visible; no fake stats in bridge | ✅ | ✅ |
| III. Verifiable Changes | `test_demo_snapshot.py` + verify_all called out | ✅ | ✅ |
| IV. Version & Release | 1.10.0 + CHANGELOG + `sync_version_info` | ✅ | ✅ |
| V. Resilience | No synthetic traffic; gateway blocks unbounded prefs spam during demo | ✅ | ✅ |

**Gate result**: ✅ PASS

## Product Demo State Isolation Architecture

### Problem (as-built)

```text
ProductDemoDialog
  └─ DemoRunner / manual advance
        └─ DemoStep.action(host)  ──►  mutates live BridgeWindow widgets
                                      (presets, network mode, start_bridge, …)
closeEvent  ──►  runner.reset() + stop diag ONLY  (no restore)
```

Presenter state (step index, auto timer) is already isolated in the dialog; **host session state is not**.

### Target architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ ProductDemoDialog (presenter state only)                     │
│  • presenter_index, phase, progress, narration UI            │
│  • DemoRunner (auto-play timers — unchanged ownership)       │
│  • DemoHostGateway                                           │
│       enter()  → capture OperatorSessionSnapshot             │
│       run_action(fn) → fn(host) under _demo_session_active   │
│       exit()   → restore_operator_snapshot()                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ owns lifecycle
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ BridgeWindow* (host)                                         │
│  _demo_session_active: bool                                  │
│  mixin: start/stop, presets, COM/net widgets                 │
│  bridge: optional running session (snapshot records flag)    │
└─────────────────────────────────────────────────────────────┘

Persistence layer (guarded while demo active):
  bench_config.save_preset      → NO-OP
  push_recent_session           → NO-OP
  (optional) connect size save  → NO-OP
```

### Module boundaries

| Module | Responsibility |
|--------|----------------|
| `ui/demo_snapshot.py` | `OperatorSessionSnapshot` dataclass; `capture_operator_snapshot`; `restore_operator_snapshot` |
| `ui/demo_gateway.py` | `DemoHostGateway` enter/exit/run_action; sets `host._demo_session_active` |
| `ui/demo.py` | Wire gateway in `ProductDemoDialog.__init__`, `closeEvent`, all step execution paths |
| `ui/mixin.py` | Early-return guards in `_preset_save_*`, `_record_recent_session`, etc. when demo active |
| `test_demo_snapshot.py` | Round-trip + preset file unchanged tests |

### Capture / restore flow

**Enter (dialog show)**:

1. `snap = capture_operator_snapshot(host)` — read widgets + `bridge`/`_starting` + `active_preset_name`.
2. `host._demo_session_active = True`.
3. Presenter bootstraps at step 0 (unchanged UX).

**During demo**:

- Every `step.action`, `_manual_advance`, `_run_selected` calls `gateway.run_action(host, fn)` instead of `fn(host)` directly.
- Track `demo_started_bridge` if action invokes `start_bridge` while snapshot had no bridge.
- Optional UI: status banner property `demonstration=true` for chip text.

**Exit (`closeEvent`, End demo button)**:

1. `runner.reset()`; `_stop_diag(host)`.
2. `restore_operator_snapshot(host, snap)`:
   - Stop bridge if demo started it and operator was stopped before.
   - `_apply_preset_data` / NMEA restore from snap fields (bridge stopped).
   - Restart bridge only if `snap.bridge_was_running`.
3. Clear banner; `host._demo_session_active = False`.
4. Log `[Demo] Restored your session before the presentation.`

**Reset demo script** (new button, optional): rewind `presenter_index` to 0 **without** host restore until exit—satisfies FR-306.

### Why not agent-browser

Demo isolation is **Qt desktop** logic; verification uses:

- Unit tests on snapshot serialization
- Hash/mtime guard on temp preset file
- Manual presenter checklist in `quickstart.md`

Web dashboard items in this epic remain **copy/placeholder audit** only (no Playwright).

See [contracts/demo-state-isolation.md](./contracts/demo-state-isolation.md) for full contract.

## Project Structure

### Documentation

```text
specs/008-ui-journey-modernization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── demo-state-isolation.md
│   ├── ui-audit-matrix.md
│   └── returning-user-flow.md
└── tasks.md                    # /speckit-tasks
```

### Source Code (implementation)

```text
ui/demo_snapshot.py          # NEW — capture/restore
ui/demo_gateway.py           # NEW — enter/exit/guards orchestration
ui/demo.py                   # Wire gateway; End demo; reset script
ui/mixin.py                  # Persistence guards; launch restore audit
ui/connect_panels.py         # (done) reset_sizes removed
ui/ui_prefs.py               # Toolbar key migration
docs/ui-audit-inventory.md   # NEW — living checklist
docs/OPERATOR_GUIDE.md       # Demo restore + audit notes
test_demo_snapshot.py        # NEW — local validation core
test_ui_prefs.py             # Toolbar migration tests
```

## Implementation Phases

### Phase A — Product Demo isolation (architectural spine)

1. Implement `OperatorSessionSnapshot` + capture/restore (`demo_snapshot.py`).
2. Implement `DemoHostGateway` + `_demo_session_active` flag.
3. Refactor `demo.py` execution paths to use `gateway.run_action`.
4. Add mixin persistence guards.
5. Add `test_demo_snapshot.py` (round-trip, preset file untouched, running flag).
6. Manual quickstart § Demo.

**Exit criteria**: SC-201/202/203 manual script passes; tests green.

### Phase B — Returning user (P1)

1. Audit `_finalize_ui` / preset restore ordering.
2. Verify recent session menu on all layouts.
3. Toolbar/panel prefs migration (extend 007 patterns).

**Exit criteria**: SC-102 manual timing; automated prefs tests pass.

### Phase C — UI audit (P1)

1. Seed `docs/ui-audit-inventory.md` from matrix contract.
2. Close P0 items (Phone QR, clip, dead controls).
3. Batch P1 copy alignment with operator guide.

**Exit criteria**: SC-101/103; zero P0 open.

### Phase D — Polish & release

1. `version.py` → 1.10.0; CHANGELOG; `sync_version_info`.
2. `verify_all.py` + full unittest discover.
3. Operator guide § Product demo restore.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
