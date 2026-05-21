# Implementation Plan: Connection Hub Phase 2 — Network Discovery

**Branch**: `2031-hub-network-discovery` | **Date**: 2026-05-20 | **Spec**: [spec.md](./spec.md)

**Input**: Responsive hub layout, ARP + UDP broadcast discovery (Q1: B), Smart Release, traffic quality on cards, standardized controls.

**Builds on**: Phase 1 ([`specs/003-connection-hub-overhaul/`](../003-connection-hub-overhaul/)) — `discovery_service.py`, `ui/connection_hub.py`, v1.5.x.

## Summary

Extend the shipped Connection Hub with: (1) **responsive Connect layout** so the card grid gets splitter space and scrolls independently of Run/Start; (2) **`network_scanner.py`** — Windows ARP/neighbor inventory plus bounded UDP broadcast probes on survey ports; (3) **`DiscoveryScanWorker`** (QThread) merging serial + network results into `DiscoverySnapshot`; (4) **Smart Release** in mixin (`port_release.py`) coordinating `com_free` probes and bridge Stop guards; (5) **traffic quality chips** on cards from coalesced bridge stats; (6) **`ui/connection_fields.py`** shared baud/port validators for hub, override, and Field. Target version **1.6.0**.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: PySide6, pyserial, pyserial-asyncio (unchanged); stdlib `socket`, `subprocess`, `ipaddress` for LAN scan  
**Storage**: Extend `ui_prefs.json` (`last_known_good`, optional `discovery_scan` prefs)  
**Testing**: `test_network_scanner.py`, `test_port_release.py`, extend `test_discovery_service.py`, `test_connection_hub.py`, `tools/run_unittests.py`; `verify_all.py`  
**Target Platform**: Windows 10+ (ARP via `arp -a` / `Get-NetNeighbor` fallback documented in research)  
**Project Type**: Desktop bridge — `bridge_core.py` + `ui/` + new `network_scanner.py`, `port_release.py`  
**Performance Goals**: Full refresh ≤ 8 s wall clock; main-thread work per poll ≤ 50 ms (snapshot apply only); scan worker cancellable; card quality refresh ≤ 2 s lag vs stats  
**Constraints**: FR-404 probes must not bind bridge UDP listen port while Running; max 32 LAN hosts per scan; Principle I — scan logic not in widgets  
**Scale/Scope**: ~6 new/modified Python modules + Connect layout touch; no new pip dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Scan/release in `network_scanner.py` / `port_release.py`; UI binds snapshots | ✅ | ✅ |
| II. Survey Operator Trust | Start/Stop stays on `run` panel; Refresh/Unlock visible on hub | ✅ | ✅ |
| III. Verifiable Changes | New tests + quickstart bench paths + verify_all | ✅ | ✅ |
| IV. Version & Release | 1.6.0 + CHANGELOG + `sync_version_info` | ✅ | ✅ |
| V. Resilience | Bounded scan budget; coalesced hub updates; no blocking `_send_net` | ✅ | ✅ |

**Gate result**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/004-hub-network-discovery/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── network-scanner.md
│   ├── hub-layout-v2.md
│   ├── smart-release.md
│   └── traffic-quality.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
network_scanner.py          # NEW — ARP/neighbor + UDP probe (no Qt)
port_release.py             # NEW — Smart Release COM/UDP helpers (no Qt)
discovery_service.py        # EXTEND — merge scanner results into build_snapshot

ui/
├── connection_hub.py       # EXTEND — toolbar Refresh/Unlock, quality chips, card baud row
├── connection_fields.py    # NEW — shared validators + baud combo factory
├── connect_panels.py       # EXTEND — hub stretch priority, scroll only on card area
├── mixin.py                # EXTEND — DiscoveryScanWorker, smart release, quality bind
├── standard.py             # MINOR — layout hook for hub stretch
└── field.py                # EXTEND — Refresh/Unlock on strip

test_network_scanner.py
test_port_release.py
test_connection_hub.py      # extend
test_discovery_service.py   # extend with scanner mocks
```

**Structure Decision**: Keep phase-1 `discovery_service.py` as snapshot composer; add `network_scanner.py` for active LAN work so constitution separation stays clear and tests stay mock-friendly.

## Implementation Phases

### Phase A — Network scanner (P1 backend)

- `list_lan_hosts()` — parse `arp -a` on Windows; dedupe IPv4 on local /24 (or interface prefix).
- `probe_survey_ports(host, ports, timeout_ms)` — UDP send minimal NMEA ping datagram; optional single-byte recv; no listen bind on bridge port.
- `scan_network(max_hosts=32, ports=(10110, 4001, 10111), deadline_s=6)` → `list[NetworkScanResult]`.
- Unit tests with mocked subprocess and socket.

### Phase B — Discovery worker + snapshot merge (P1)

- `DiscoveryScanWorker(QThread)` runs serial scan + `scan_network`; emits `DiscoverySnapshot`.
- `build_snapshot(..., network_scan_results=...)` merges discovered hosts into `NetworkCardInfo` cards.
- Replace mixin timer-only poll with worker on Refresh + optional 30 s background (configurable off).
- Cancel in-flight scan on Stop / second Refresh.

### Phase C — Responsive hub layout (P1 UI)

- `ConnectionHubWidget`: toolbar **Refresh discovery** + **Unlock ports**; card area in dedicated `QScrollArea` with `QSizePolicy` expanding.
- `connect_panels.py`: connection panel min height; splitter stretch favors hub; remove double-scroll (hub scroll only, not whole connection body).
- `EndpointCardWidget`: min width 220 px; grid reflow 1–3 columns from width.

### Phase D — Smart Release (P1)

- `port_release.smart_release_com(port, baud)` — probe open/close like `com_free.py`; never touch port if bridge Running on that COM without `force=False`.
- `port_release.hint_udp_port_busy(port)` — reuse `probe_udp_port_available`.
- Mixin `_on_unlock_refresh_ports()` — Stop not required if different COM; message on failure.

### Phase E — Traffic quality on cards (P2)

- `TrafficQualitySnapshot` from merged stats (`hz_up`, `drops_s2n`, `rej_s2n`, nav quality stale).
- `ConnectionHubWidget.apply_quality(active_device_id, snapshot)` updates chip color/subtitle.
- Throttle: same 2 s coalesce as discovery poll when Running.

### Phase F — Standardized fields (P3)

- `connection_fields.py`: `parse_baud()`, `validate_udp_port()`, shared `BaudCombo` preset list.
- Wire hub serial card inline baud + override/Field to same helpers.

## Complexity Tracking

> No constitution violations requiring justification.

## Risk Register

| Risk | Mitigation |
|------|------------|
| ARP table empty (VPN) | Fall back to default UDP listen card + hint |
| UDP probe firewall | Mark host “unreachable”; do not block scan |
| Scan blocks UI | Strict worker thread; main thread only applies snapshot |
| Smart Release opens bridge COM | Guard on `bridge.running` + same COM check |
| Layout regression | `test_connect_panel_sizes.py` update + bench_gui_smoke |
