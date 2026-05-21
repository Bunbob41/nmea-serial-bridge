# Implementation Plan: Connection Hub Overhaul

**Branch**: `2030-connection-hub-overhaul` | **Date**: 2026-05-20 | **Spec**: [spec.md](./spec.md)

**Input**: Connection Hub UI, DiscoveryService, TCP sink mirror (extends baseline FR-001–FR-021).

## Summary

Deliver a **phased** overhaul: (1) extract **`discovery_service.py`** from `auto_discovery.py` with serial + passive network snapshots; (2) **`ui/connection_hub.py`** card grid inside Connect `connection` panel with manual override hosting legacy `controls.py` fields; (3) extend **`bridge_core.py`** with optional **TCP sink** server fan-out parallel to `_send_net`; (4) **`last_known_good.json`** (or `ui_prefs` section) for per-device defaults; (5) tests + minor version bump **1.5.0**.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: PySide6, pyserial, pyserial-asyncio (unchanged)  
**Storage**: `%USERPROFILE%\.cursor-udp-com-bridge\` — extend `ui_prefs.json` + optional `last_known_good.json`  
**Testing**: `test_discovery_service.py`, `test_tcp_sink.py`, `test_connection_hub.py` (widget smoke), migrate `test_auto_discovery.py`; `verify_all.py`  
**Target Platform**: Windows desktop (primary)  
**Project Type**: Desktop bridge — single repo, `bridge_core.py` + `ui/`  
**Performance Goals**: Discovery poll ≤2 s; hub refresh coalesced 500 ms; TCP sink mirror must not add >1 ms p95 blocking on `_send_net` hot path (async fire-and-forget write)  
**Constraints**: Principle I — no protocol in widgets; Principle V — bounded sink client set (max 8), prune on write failure  
**Scale/Scope**: ~8–12 new/modified modules; Standard Connect primary; Field strip parity in Phase 2

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Protocol in `bridge_core` / `discovery_service`; UI binds snapshots only | ✅ | ✅ |
| II. Survey Operator Trust | Start/Stop on `run` panel; cards reduce scroll, not hide run | ✅ | ✅ |
| III. Verifiable Changes | New tests + verify_all cited in quickstart | ✅ | ✅ |
| IV. Version & Release | 1.5.0 + CHANGELOG + `sync_version_info` | ✅ | ✅ |
| V. Resilience | Bounded queues unchanged; sink prune; UI poll coalescing | ✅ | ✅ |

**Gate result**: ✅ PASS

## Project Structure

### Documentation (this feature)

```text
specs/003-connection-hub-overhaul/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── discovery-service.md
│   ├── tcp-sink.md
│   └── connection-hub-ui.md
└── tasks.md                    # /speckit-tasks
```

### Source Code (repository root)

```text
discovery_service.py          # NEW — serial scan + network snapshot (no Qt)
auto_discovery.py             # DEPRECATE → thin wrapper or remove after migration

bridge_core.py                  # TcpSinkListener, _send_net mirror hook
nmea_codec.py                   # unchanged unless filter hooks needed

ui/
├── connection_hub.py         # NEW — card grid widget + model binding
├── connect_panels.py         # wire hub into "connection" panel body
├── controls.py               # legacy fields → override panel child
├── mixin.py                  # Discovery poll timer, hub→_start_bridge config
├── ui_prefs.py               # last_known_good load/save
├── standard.py               # embed hub
└── field.py                  # Phase 2: compact hub strip or link

test_discovery_service.py
test_tcp_sink.py
test_connection_hub.py
test_auto_discovery.py        # update imports / compat
```

**Structure Decision**: New top-level `discovery_service.py` keeps constitution separation; Qt thread in `ui/mixin` only polls service and emits snapshots to hub.

## Implementation Phases

### Phase A — Discovery service (P1 backend)

- Extract scan logic from `AutoDiscoveryThread` into `DiscoveryService.scan_serial()`.
- Add `build_network_snapshot(bridge_stats, preset, port_probe)` — passive only.
- `DiscoveryPollWorker(QThread)` or `QTimer` on main thread calling service every 2 s.
- Migrate `test_auto_discovery.py` → `test_discovery_service.py`.

### Phase B — Connection Hub UI (P1)

- `ConnectionHubWidget`: `QScrollArea` + horizontal/vertical flow of `EndpointCardWidget`.
- Card click → `selected_device_id` on window; populate override fields from `LastKnownGood`.
- Manual override: existing `create_connection_controls` subtree inside `QGroupBox`.
- Replace `connection` panel content in `connect_panels.py` (keep panel key + height prefs).

### Phase C — Last-known-good persistence (P1)

- `device_id` = `serial:COM7` or `serial:USB\\VID_xxxx+PID_yyyy` when available else COM name.
- Save on successful Start and on preset Save.

### Phase D — TCP sink (P2 backend)

- `TcpSinkConfig(enabled, bind_host, bind_port, max_clients=8)`.
- `asyncio.start_server` on bridge loop; `_mirror_to_sink(data)` after primary `_send_net`.
- UI: checkbox + port in hub network section or override (default off).

### Phase E — Network cards + Field (P2)

- Network template cards from preset + live peer count via `stats_cb`.
- Field layout: mini hub or “Edit connection…” opens Standard Connect tab.

## Complexity Tracking

> No constitution violations requiring justification.

## Risk Register

| Risk | Mitigation |
|------|------------|
| Connect panel scroll regression | Keep `connect_panels` splitter; cap hub height; user-resizable |
| TCP sink port conflict | Pre-flight bind probe in discovery snapshot |
| Regression on fan-out | `test_udp_fanout.py` unchanged; add `test_tcp_sink.py` dual-path |
| `bridge_core` Qt import | Do not worsen — discovery stays out of bridge_core |
