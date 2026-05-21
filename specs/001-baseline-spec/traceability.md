# Baseline Traceability Matrix

Maps [spec.md](./spec.md) functional requirements to verification paths.

**Version labels**: Behavior baseline **v1.4.9+** (auto-discovery); documentation release
**v1.4.10+**; `version.py` and synced `version_info.txt` are the release source of truth.

| FR | Requirement summary | Verification |
|----|---------------------|--------------|
| FR-001 | One COM ↔ one network config per session | `test_bridge_core.py`; OPERATOR_GUIDE §5–6 |
| FR-002 | Start/Stop visible Standard + Field | Manual UI; `ui/standard.py`, `ui/field.py` |
| FR-003 | UDP listen default pattern | OPERATOR_GUIDE §5–6; bench presets |
| FR-004 | Advanced UDP remote, TCP server/client | OPERATOR_GUIDE §6.3; Guide tab TCP sections |
| FR-005 | COM select, baud, refresh, auto-reconnect | OPERATOR_GUIDE §7; `test_bridge_core.py` |
| FR-006 | COM exclusivity not fake-healthy | `com_free.py`; preflight checklists |
| FR-007 | Passthrough / Strict / Raw modes | OPERATOR_GUIDE §7 NMEA; `test_nmea_codec.py` |
| FR-008 | Raw binary no NMEA assembly | `test_nmea_codec.py`; OPERATOR_GUIDE Raw warning |
| FR-009 | Bounded queues, drop/reject visible | Survey HUD + status bar; `bench_stress.py` |
| FR-010 | Presets persist fan-out + connection | OPERATOR_GUIDE §5.3; `path_presets.json` |
| FR-011 | Fan-out on → all session peers | `test_udp_fanout.py`; §5.5; `bench_fanout_probe.py` |
| FR-012 | Fan-out off → last sender only | `test_udp_fanout.py`; §5.5 step 7 |
| FR-013 | Stop clears peer set | `test_udp_fanout.py` abort tests |
| FR-014 | Standard, Field, Survey HUD | OPERATOR_GUIDE §3–4; `bench_gui_smoke.py` |
| FR-015 | Throttled live log, verbose | Connect/Log tabs; Field log-first |
| FR-016 | Send tab text inject | OPERATOR_GUIDE Send; not for binary |
| FR-017 | Operator documentation | `docs/OPERATOR_GUIDE.md`, README |
| FR-018 | Diagnostics entry points | Diagnostics tab; `verify_all.py` |
| FR-019 | Out of scope items listed | spec.md; constitution |
| FR-020 | One bridge, multiple UDP clients | OPERATOR_GUIDE §5.5; quickstart.md |
| FR-021 | Auto-discovery GNSS USB watcher | `auto_discovery.py`; Connect checkbox; `test_auto_discovery.py` |

## Success criteria

| SC | Summary | Verification |
|----|---------|--------------|
| SC-001 | Onboarding &lt; 3 min | Manual walkthrough; OPERATOR_GUIDE §4 |
| SC-002 | Bench happy-path &lt; 15 min | OPERATOR_GUIDE §5; quickstart.md |
| SC-003 | 30 min UI + 5 Hz ingress | **[sc003-hud-stress-validation.md](./sc003-hud-stress-validation.md)** — `bench_udp_test.py --hz 5`, HUD manual checks, optional `bench_gui_smoke.py` |
| SC-004 | Two-client fan-out | §5.5; `bench_fanout_probe.py`; `test_udp_fanout.py` |
| SC-005 | FR coverage | This matrix + spec.md |
| SC-006 | Future specs cite FR IDs | Spec Kit process |

## Automated regression

```powershell
python -m unittest test_udp_fanout.py test_baseline_docs.py test_version_sync.py -v
python verify_all.py
```

## Environmental waivers (`verify_all.py`)

Recorded so failures on developer PCs are not mistaken for product regressions.

| Step | Typical failure | Cause | Waiver / remediation |
|------|-----------------|-------|----------------------|
| `check_setup` / UDP probe | Port **10110 in use** | **OpenCPN** or another app bound to the bench UDP port | Quit OpenCPN (or change preset port); re-run. `verify_all` skips headless/stress when port busy — message: *hardware stress steps skipped*. |
| `bench_gui_smoke` | Exit `3221226505` (0xC0000409) after OK | PySide6 Windows teardown fast-fail | `bench_gui_smoke.py` uses `exit_after_qt_work`; `verify_all.py` treats post-OK fast-fail as pass. Re-run `python verify_all.py` if still flagged. |
| `bench_stress` | Skipped with port in use | Same as OpenCPN conflict | Free port or run `bench_stress.py` manually when COM+UDP exclusive. |

**Last documented verify run** (2026-05-20, branch `2028-baseline-version-sync`): unittest **218 OK**;
`verify_all.py` — **2 failures** (UDP 10110 held by `opencpn.exe`; `bench_gui_smoke` abnormal exit).
Waivers above apply; port conflict is environmental, not bridge defect.

**Remediation before release handoff**: stop conflicting apps → `python verify_all.py` → confirm green or update this table.
