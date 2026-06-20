# Data Model: Fleet Multi-Stream

**Feature**: [`spec.md`](spec.md)

---

## FleetConfig

Top-level persisted document.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | int | yes | Start at `1` |
| `auto_start_on_launch` | bool | yes | Default `false` |
| `streams` | `StreamDefinition[]` | yes | Max length 8 |

**Storage**: `%USERPROFILE%\.cursor-udp-com-bridge\fleet_config.json` (exact path finalized in plan).

**Import/export**: Same JSON file; optional fleet name in export metadata only.

---

## StreamDefinition

Static configuration for one lock on the river.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string (uuid) | yes | Stable across edits |
| `label` | string | yes | Operator name, e.g. `TSS1`, `SVP` |
| `enabled` | bool | yes | Excluded from Start all when false |
| `primary` | bool | yes | Default false; at most one true in fleet |
| `com` | string | yes | e.g. `COM9` |
| `baud` | int | yes | |
| `nmea_mode` | enum | yes | `passthrough`, `strict`, `raw` — same as bridge |
| `net_mode` | enum | yes | Maps to `NetMode` |
| `udp_host` | string | if listen | Bind address |
| `udp_port` | int | if listen | **Unique** across fleet when listening |
| `udp_remote_host` | string | if remote | |
| `udp_remote_port` | int | if remote | |
| `tcp_host` | string | if tcp | |
| `tcp_port` | int | if tcp | |
| `udp_fanout` | bool | if udp listen | Default true |
| `local_backup` | bool | no | Per-stream rotating raw log |

### Validation rules

1. `len(streams) <= 8`
2. Unique `com` among **enabled** streams
3. Unique `udp_port` among streams where `net_mode` is UDP listen on same bind host
4. `sum(primary) <= 1`
5. `label` non-empty, max 32 chars (UI)

---

## StreamRuntimeState

Ephemeral; not persisted.

| Field | Type | Notes |
|-------|------|-------|
| `stream_id` | string | FK to `StreamDefinition.id` |
| `worker_state` | enum | `idle`, `starting`, `running`, `stopping`, `error` |
| `error_message` | string? | COM busy, bind failed, etc. |
| `last_rx_monotonic` | float? | For silence detection |
| `bytes_rx` | int | Rolling / cumulative per session |
| `bytes_tx` | int | |
| `drops` | int | From bridge stats |
| `rate_hint` | float? | Hz or B/s — UI formatted |
| `started_at` | datetime? | |

---

## FleetSupervisor (runtime)

| Responsibility | Notes |
|----------------|-------|
| Load/save `FleetConfig` | Via prefs module |
| `validate()` | FR-503 |
| `start_all()` / `stop_all()` | Skips disabled; continues on per-row error |
| `start_stream(id)` / `stop_stream(id)` | |
| `restart_stream(id)` | Stop + start |
| `primary_stream_id()` | Derived from config |
| `worker_for_primary()` | For HUD binding |
| `subscribe_stats(callback)` | Coalesced, max 2 Hz to UI |

---

## StreamWorker (interface)

See [`contracts/stream-worker.md`](contracts/stream-worker.md).

| Implementation | v1 | v2 |
|----------------|----|----|
| `ThreadStreamWorker` | yes | — |
| `ProcessStreamWorker` | — | planned |

---

## State transitions (worker)

```text
idle → starting → running → stopping → idle
starting → error → idle (operator restart)
running → error (fatal COM loss — policy in plan)
```

---

## Relationship to existing prefs

| Existing | Fleet interaction |
|----------|-------------------|
| `path_presets.json` | Optional “Load preset into stream row” — copies fields into `StreamDefinition` |
| Modern Control single bridge | Coexists: if fleet inactive, Control behaves as today |
| Primary + fleet | HUD reads Primary worker stats when fleet has running primary |

---

## Schema example (illustrative)

```json
{
  "schema_version": 1,
  "auto_start_on_launch": false,
  "streams": [
    {
      "id": "a1b2c3",
      "label": "Applanix",
      "enabled": true,
      "primary": true,
      "com": "COM9",
      "baud": 115200,
      "nmea_mode": "passthrough",
      "net_mode": "udp_listen",
      "udp_host": "0.0.0.0",
      "udp_port": 10110,
      "udp_fanout": true,
      "local_backup": false
    },
    {
      "id": "d4e5f6",
      "label": "SVP",
      "enabled": true,
      "primary": false,
      "com": "COM6",
      "baud": 9600,
      "nmea_mode": "raw",
      "net_mode": "udp_remote",
      "udp_remote_host": "192.168.1.50",
      "udp_remote_port": 10112,
      "local_backup": true
    }
  ]
}
```
