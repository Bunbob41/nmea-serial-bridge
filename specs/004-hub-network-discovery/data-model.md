# Data Model: Connection Hub Phase 2

**Feature**: `004-hub-network-discovery` | **Date**: 2026-05-20

## Entity relationship

```text
DiscoverySnapshot
├── serial_devices: SerialDeviceInfo[]     (phase 1)
├── network_cards: NetworkCardInfo[]       (phase 1 + scanner merge)
├── discovered_hosts: NetworkScanResult[]  (NEW — raw scan)
├── errors: str[]
└── mono_ts: float

NetworkScanResult (NEW)
├── host: str              # IPv4
├── mac: str | ""          # from ARP if known
├── open_ports: int[]      # ports that responded to probe
├── method: str            # arp | udp_probe
├── label: str             # display e.g. "192.168.1.50 (UDP 10110)"
├── stale: bool            # ARP age > threshold
└── last_seen_mono: float

NetworkCardInfo (extended)
├── device_id: str         # net:discovered:{host}:{port} | net:udp_listen:...
├── discovery_source: str  # passive | arp | udp_probe
└── (existing fields)

TrafficQualitySnapshot (NEW)
├── state: str             # idle | ok | warn
├── hz_up: float
├── hz_down: float
├── drops_s2n: int
├── drops_n2s: int
├── rej_s2n: int
├── rej_n2s: int
├── nav_stale: bool
└── summary: str           # one-line for card subtitle

PortLockState (NEW)
├── port: str
├── locked: bool
├── reason: str
├── safe_to_release: bool
└── last_attempt_ok: bool | None
```

## State transitions

### Discovery scan

```text
idle → scanning (worker started)
scanning → idle (snapshot_ready | scan_failed | cancelled)
```

### Smart Release

```text
probe → released (open+close OK)
probe → blocked (bridge running on COM)
probe → failed (permission / timeout) → operator message
```

### Card quality (while Running)

```text
idle → ok (traffic present, no drops)
ok → warn (drops/rejects/stale nav)
warn → ok (counters cleared)
* → idle (bridge stopped)
```

## Validation rules

| Field | Rule |
|-------|------|
| `baud` | Positive int; shared `connection_fields.parse_baud` |
| `udp_port` | 1–65535 |
| `host` | Valid IPv4 or `0.0.0.0` for listen |
| `device_id` | Stable string; discovered network `net:discovered:{ip}:{port}` |
| Scan budget | ≤ 32 hosts, ≤ 6 s total worker time |

## Persistence (`ui_prefs.json`)

```json
{
  "discovery_scan": {
    "background_interval_s": 30,
    "background_enabled": false
  },
  "last_known_good": { "...": "unchanged from phase 1" }
}
```

## Merge rules (`build_snapshot`)

1. Always include default **UDP listen** card from UI fields + `probe_udp_port_available`.
2. Append **preset** cards (phase 1).
3. Append **discovered** cards from `NetworkScanResult` (dedupe by host+port).
4. If bridge Running, overlay `peer_count` / `running` on matching listen card.
