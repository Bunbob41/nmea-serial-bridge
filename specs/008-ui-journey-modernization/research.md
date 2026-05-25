# Research: UI & Workflow Journey Modernization

**Feature**: `008-ui-journey-modernization` | **Date**: 2026-05-24

## R1 — Product Demo state isolation strategy

**Decision**: **Snapshot + restore** on the live host window, with a **demo-active guard** on persistence hooks (presets, recent sessions, connect prefs), not a second invisible main window.

**Rationale**:

- Today `ui/demo.py` calls `step.action(host)` directly on the real `BridgeWindow*`; `closeEvent` only resets `DemoRunner` and stops diagnostics—no rollback (see `ProductDemoDialog.closeEvent`, lines ~937–940).
- A full duplicate Qt window would duplicate `BridgeLogicMixin` wiring and drift from production parity.
- Snapshot aligns with spec FR-301/304 and is testable without browser automation.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Separate `DemoBridgeWindow` instance | High wiring cost; parity drift; two event loops risk |
| Immutable demo-only mock host (no real bridge) | Breaks FR-305 parity for Start/HUD/diagnostics steps |
| Document “presenter must reload preset after demo” | Fails SC-201/203; operator-trust violation |

---

## R2 — What the snapshot must capture

**Decision**: Capture an **Operator Session Snapshot** (connection + NMEA + active preset name + bridge run/stop + minimal UI navigation), not a full `ui_prefs.json` clone.

**Rationale**: Restore must put the operator back exactly where they were; persisting demo-driven changes to `path_presets.json` is explicitly forbidden (SC-202).

**Fields** (minimum viable):

- COM, baud, network mode radios, UDP/TCP host/port fields, fanout/sink toggles
- NMEA mode + strict sentence checkboxes
- `_active_preset_name` / `last_preset` reference (name only—do not rewrite preset file bodies)
- `bridge is not None`, `_starting` flag
- Optional: main tab index, Field drawer open, Tools nav row (best-effort)

**Alternatives considered**:

- Deep-copy all widgets via Qt serialization — fragile, untested on PySide6
- Snapshot only preset name — insufficient when demo changes TCP mode inline

---

## R3 — Demo presenter state vs host state

**Decision**: Keep **presenter state** entirely inside `ProductDemoDialog` / `DemoRunner` (step index, phase, auto-play timers). **Host mutations** go only through `DemoHostGateway` while `_demo_session_active` is true.

**Rationale**: Spec FR-302 requires demo UI state independent of Connect disclosure collapse; already true for dialog, but host was shared.

---

## R4 — Mock / demonstration labeling

**Decision**: Reuse **`[Demo]` log prefix** (existing `_log` in `demo.py`); add optional **HUD subtitle / status banner** “Demonstration” chip during demo only; do **not** inject fake NMEA into `bridge_core` queues.

**Rationale**: Constitution V—no fake traffic that pollutes counters; presenters need visual cue without corrupting drop/reject stats.

---

## R5 — Validation approach (local-only)

**Decision**: **No agent-browser / Playwright** for this epic. Validation = **unittest + QTest where cheap** + **manual quickstart checklist** + `verify_all.py`.

**Rationale**: User explicitly requested local-only validation; demo isolation is desktop Qt; web dashboard is audit-copy only (US2/US4).

**Test matrix**:

| Layer | Tool | Covers |
|-------|------|--------|
| Snapshot serialize/restore | `test_demo_snapshot.py` | FR-301/304 logic |
| Preset file untouched | `test_demo_snapshot.py` + temp `path_presets.json` mock | SC-202 |
| Demo runner stop/reset | extend `test_ui_tabs.py` or new `test_demo_runner.py` | Regression |
| Manual | `quickstart.md` | SC-203 presenter script |
| Gate | `verify_all.py` | Constitution III |

---

## R6 — UI audit execution

**Decision**: Maintain **`docs/ui-audit-inventory.md`** (or `specs/008-.../contracts/ui-audit-matrix.md`) as a living checklist; fix P0 in same epic, batch P1.

**Rationale**: Spec FR-101/102 require inventory; spreadsheet in-repo travels with PRs.

---

## R7 — Returning-user flow

**Decision**: Consolidate launch restore in **`_finalize_ui` / `_init_web_and_facade` / `_activate_preset_by_name`** audit—no new persistence file; migrate invalid toolbar keys (`reset_sizes`) and junk connect heights (already partially done in 007).

**Rationale**: Data already in `ui_prefs.json`, `path_presets.json`, `bench_config`; friction is ordering and messaging not storage.
