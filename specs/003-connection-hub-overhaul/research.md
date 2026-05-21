# Research: Connection Hub Overhaul

## R1 — Where discovery logic lives

**Decision**: New module `discovery_service.py` (stdlib + pyserial only). `ui/mixin.py` runs a `QTimer` (2 s) calling `DiscoveryService.build_snapshot()` on a worker thread via `QtConcurrent` or dedicated `QThread` that returns a dataclass — **no** `QObject` in discovery_service.

**Rationale**: Constitution Principle I; `auto_discovery.py` already couples `QThread` + scan — split scan from thread.

**Alternatives considered**:
- Keep logic only in `AutoDiscoveryThread` — rejected (not first-class service).
- Put discovery in `bridge_core.py` — rejected (polls serial ports while bridge not running; wrong layer).

## R2 — Network discovery scope (v1)

**Decision**: **Passive/contextual** snapshots only:
- UDP port bind probe (`socket` try-bind)
- Preset-derived template cards (Desk/Boat)
- When bridge Running: `udp_peer_count`, mode, listen host:port from stats callback

**Rationale**: Spec assumption; avoids firewall/Nmap complexity on survey PCs.

**Alternatives considered**:
- Bonjour/mDNS INS discovery — deferred.
- Active subnet scan — deferred (IT policy risk).

## R3 — TCP sink architecture

**Decision**: Secondary **`asyncio.Server`** on bridge event loop; `_send_net` calls `_mirror_to_tcp_sink(data)` after primary path (try/except per client, prune dead writers). Independent of `NetMode` primary socket.

**Rationale**: FR-311 concurrent mirror; mirrors UDP fan-out pattern (iterate clients).

**Alternatives considered**:
- Second `SerialNetBridge` instance — rejected (port/COM conflict, operator confusion).
- Multicast duplicate datagram — rejected (not TCP sink semantics).

## R4 — Connection Hub widget pattern

**Decision**: `QFrame` cards in `QGridLayout` inside scroll area; selected state via stylesheet + `property selected`. Manual override = `DisclosureRow` or `QGroupBox` below grid reusing existing widgets from `controls.py`.

**Rationale**: Matches spec cards; reuses battle-tested fields for override (FR-307).

**Alternatives considered**:
- Replace entire Connect tab — rejected (breaks panel order prefs, NTRIP, run panel).
- Wizard dialog — rejected (extra click, violates operator trust).

## R5 — Device ID stability

**Decision**: Prefer `hwid` from `list_ports.comports()` when present: `f"serial:{hwid}"`; fallback `f"serial:{port_name}"`. Network template cards: `f"net:preset:{name}"` or `f"net:udp_listen:{host}:{port}"`.

**Rationale**: USB re-enumeration may change COM number; hwid more stable on Trimble cables.

**Alternatives considered**:
- COM-only key — kept as fallback only.

## R6 — Version bump

**Decision**: **Minor 1.5.0** — new UI surface + TCP sink feature + discovery service.

**Rationale**: Constitution IV; user-visible workflow change beyond patch.
