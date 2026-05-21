# Data Model: Product Baseline (Conceptual)

Entities from [spec.md](./spec.md) — logical model for traceability, not a new database schema.

## Bridge session

| Field | Description |
|-------|-------------|
| state | Stopped \| Running |
| com | COM port name |
| baud | Integer baud rate |
| network_mode | UDP listen \| UDP remote \| TCP server \| TCP client |
| nmea_mode | Passthrough \| Strict \| Raw binary |
| udp_fanout | Boolean (UDP listen only) |
| drops_net_to_serial | Counter |
| drops_serial_to_net | Counter |
| rejected_* | Counters |

**Lifecycle**: Start → Running → Stop clears UDP peer set (FR-013).

## Preset

| Field | Description |
|-------|-------------|
| name | Unique label |
| com, baud | Serial settings |
| network fields | Mode, host, ports |
| nmea_mode | Session default |
| udp_fanout | Persisted checkbox (FR-010) |

**Storage**: `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json`

## UDP peer

| Field | Description |
|-------|-------------|
| address | (host, port) tuple |
| registered_at | First datagram in session |

**Relationships**: Many peers belong to one Bridge session (listen mode). Serial→net fan-out iterates this set when `udp_fanout` is true.

## Survey quality snapshot

| Field | Description |
|-------|-------------|
| fix_quality | From latest GGA |
| satellites, hdop | From latest GGA |
| stale | Derived for HUD display |

**Source**: Parsed NMEA on bridged stream; not persisted across sessions.

## Drop / reject counters

Ephemeral session metrics surfaced in status bar and Survey HUD; evidence of backpressure (FR-009) or Strict rejects.
