# Research: Connection Hub Phase 2

**Feature**: `004-hub-network-discovery` | **Date**: 2026-05-20

## R1 — Network discovery method (Q1: B)

**Decision**: Combine **ARP/neighbor-table host list** with **bounded UDP datagram probes** on survey-default ports `{10110, 4001, 10111}`.

**Rationale**: Spec Q1 B; ARP is fast and needs no extra dependencies on Windows; UDP probes detect INS/GNSS senders that may not appear as named ARP entries but respond on the survey port.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| ARP only | Misses configured senders not in cache |
| Full port scan | Out of scope; security/noise |
| mDNS/Bonjour | Not standard on survey GNSS gear |
| Scapy raw ARP | New dependency; constitution prefers stdlib |

**Probe behavior**:

- Send `$PING\r\n` or minimal `$GPGGA` stub to `host:port` (UDP).
- `socket.settimeout(0.25)`; success = any recv OR ICMP unreachable absent (best-effort).
- **Never** `bind()` to the bridge listen port while `bridge.running` and mode is UDP_LISTEN on that port.
- Cap **32 hosts** × **3 ports** with overall **6 s** worker deadline.

## R2 — Windows ARP host enumeration

**Decision**: Primary: parse `arp -a` via `subprocess` (UTF-8, 3 s timeout). Secondary: if empty, include `127.0.0.1` and gateway from `ipconfig` regex (bench loopback path).

**Rationale**: Works on survey laptops without PowerShell 5.1+ modules; testable via mocked stdout.

**Alternatives considered**: `Get-NetNeighbor` (PowerShell) — optional future enhancement; ctypes `SendARP` — more code, marginal gain.

## R3 — Connect layout / scroll clipping

**Decision**: One **vertical scroll** inside `ConnectionHubWidget` for the card grid only; Connect panel `connection` section uses existing splitter with **increased default fraction** for connection (e.g. 45% of splitter when expanded). Remove outer `connect_body` stretch eating hub space.

**Rationale**: FR-401/402; operators reported clipped COM labels inside nested `QScrollArea` on `connect_scroll` wrapping entire body.

**Reference**: `ui/connect_panels.py` `_flush_connect_scroll_geometry`, `ui/standard.py` `connect_scroll` wrapper.

## R4 — Smart Release semantics

**Decision**:

1. If bridge **Running** on COM *X* → Unlock shows dialog “Stop bridge first” (no forced release).
2. Else → run `port_release.smart_release_com`: timed open/close probe (reuse `com_free` 5 s pattern).
3. UDP: only **hint** if listen port busy — suggest Stop or change port; no kill other process.

**Rationale**: FR-405; avoids yanking active session; aligns with `com_free.py` operator workflow.

## R5 — Traffic quality mapping

**Decision**: Map stats to three hub states: **idle** (Stopped), **ok** (Hz ≥ 0.5 and drops/rejects zero in window), **warn** (drops/rejects > 0 or nav stale > 5 s). Show `↑Hz` and `drops/rej` in card subtitle when Running.

**Rationale**: FR-406 / SC-405; reuses `_merge_bridge_stats` and `navigation_quality_stats()` without new bridge counters.

## R6 — Background threading model

**Decision**: `DiscoveryScanWorker(QThread)` with signals `snapshot_ready(DiscoverySnapshot)` and `scan_failed(str)`. Mixin owns worker lifecycle; 2 s timer only applies **quality** updates when not scanning.

**Rationale**: FR-408 / SC-402; serial `list_ports` and ARP/subprocess safe off main thread.

## R7 — Version bump

**Decision**: **1.6.0** minor — new operator-visible discovery, layout, unlock, quality chips.

**Rationale**: Constitution IV; extends 1.5.x hub without breaking preset schema.
