# Baseline Traceability Matrix

Maps [spec.md](./spec.md) functional requirements to verification paths (v1.4.9+ baseline).

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
| FR-009 | Bounded queues, drop/reject visible | Survey HUD + status bar; stress benches |
| FR-010 | Presets persist fan-out + connection | OPERATOR_GUIDE §5.3; `path_presets.json` |
| FR-011 | Fan-out on → all session peers | `test_udp_fanout.py`; §5.5; `bench_fanout_probe.py` |
| FR-012 | Fan-out off → last sender only | `test_udp_fanout.py`; §5.5 step 7 |
| FR-013 | Stop clears peer set | `test_udp_fanout.py` abort tests |
| FR-014 | Standard, Field, Survey HUD | OPERATOR_GUIDE §3–4; launcher |
| FR-015 | Throttled live log, verbose | Connect/Log tabs; Field log-first |
| FR-016 | Send tab text inject | OPERATOR_GUIDE Send; not for binary |
| FR-017 | Operator documentation | `docs/OPERATOR_GUIDE.md`, README |
| FR-018 | Diagnostics entry points | Diagnostics tab; `verify_all.py` |
| FR-019 | Out of scope items listed | spec.md; constitution |
| FR-020 | One bridge, multiple UDP clients | OPERATOR_GUIDE §5.5; quickstart.md |

**Automated regression**: `python -m unittest test_udp_fanout.py` + `python verify_all.py`
