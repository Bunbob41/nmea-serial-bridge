# SC-003 Validation: HUD Stress Under Sustained Ingress

**Criterion** (from [spec.md](./spec.md)): Under sustained 5 Hz NMEA ingress in Passthrough
mode, the UI remains interactive (resize, Stop, HUD open/close) for a 30-minute observation
window without deadlock.

**Type**: Manual validation with existing bench scripts (no new bridge logic).

## Prerequisites

- Bench PC with display (GUI required — not headless-only)
- UDP listen port **free** (stop OpenCPN or other apps on that port — see traceability waivers)
- com0com pair or physical COM per OPERATOR_GUIDE §5
- Bridge **Standard** layout, **Passthrough** NMEA mode

## Procedure

| Step | Action | Script / check |
|------|--------|----------------|
| 1 | Load bench preset; confirm fan-out as needed | Presets tab |
| 2 | **Start bridge** | Status → Running |
| 3 | Open **Survey HUD** | Survey bar → HUD |
| 4 | Start sustained **5 Hz** UDP ingress | `python bench_udp_test.py --hz 5 --seconds 1800` (30 min) or `--seconds 300` for abbreviated smoke |
| 5 | During ingress, every ~5 min | Resize main window; drag HUD edge; open/close HUD; click **Stop** then **Start** once mid-run |
| 6 | Observe | Hz/drops update in HUD; no frozen cursor; Stop always ends session |
| 7 | Optional parallel soak | When COM/UDP exclusive: `python bench_stress.py --cycles 6` in a separate maintenance window (headless; does not replace GUI SC-003) |
| 8 | Launch smoke (short) | `python bench_gui_smoke.py` before/after long run — confirms UI modes still open |

## Pass / fail

| Result | Evidence |
|--------|----------|
| **PASS** | Full 30 min (or agreed abbreviated ≥15 min) with HUD interactions responsive |
| **FAIL** | Qt freeze, Stop ignored, HUD resize lockup, or status stops updating while ingress continues |
| **WAIVED** | Document reason (remote desktop disabled, single-monitor policy, etc.) in traceability |

## Relation to `verify_all.py`

`verify_all.py` runs short automated steps only; it does **not** substitute for this
30-minute SC-003 procedure. See traceability **Environmental waivers**.
