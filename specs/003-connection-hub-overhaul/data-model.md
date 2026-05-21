# Data Model: Connection Hub Overhaul

## DiscoverySnapshot

| Field | Type | Notes |
|-------|------|-------|
| mono_ts | float | `time.monotonic()` at build |
| serial_devices | list[SerialDeviceInfo] | After stability filter |
| network_cards | list[NetworkCardInfo] | Templates + live |
| errors | list[str] | Probe failures (port in use, etc.) |

## SerialDeviceInfo

| Field | Type | Notes |
|-------|------|-------|
| device_id | str | `serial:{hwid}` or `serial:{port}` |
| port | str | COM name |
| description | str | list_ports description |
| manufacturer | str | optional |
| match_keyword | str | Which keyword matched |
| stable | bool | Passed consecutive poll guard |
| status | enum | `available` \| `stale` \| `in_use` |

## NetworkCardInfo

| Field | Type | Notes |
|-------|------|-------|
| device_id | str | `net:...` |
| label | str | e.g. "UDP listen :10110" |
| mode_hint | str | `udp_listen` \| `tcp_server` \| template |
| host | str | Bind or target |
| port | int | |
| port_available | bool | Probe result |
| peer_count | int | 0 when bridge stopped |
| status | enum | `ready` \| `port_busy` \| `running` |

## LastKnownGood (persisted)

| Field | Type | Notes |
|-------|------|-------|
| device_id | str | Key |
| com | str | |
| baud | int | |
| net_mode | str | Maps to NetMode |
| udp_host | str | |
| udp_port | int | |
| udp_fanout | bool | |
| tcp_sink_enabled | bool | |
| tcp_sink_port | int | |
| updated_at | str | ISO timestamp |

**Storage**: `ui_prefs.json` key `last_known_good: { device_id: { ... } }`

## HubSelection (runtime, window state)

| Field | Type | Notes |
|-------|------|-------|
| selected_device_id | str \| None | |
| manual_override_active | bool | |
| manual_override_dirty | bool | Override wins when true |

## TcpSinkSession (bridge_core runtime)

| Field | Type | Notes |
|-------|------|-------|
| enabled | bool | |
| bind_host | str | default `0.0.0.0` |
| bind_port | int | |
| server | asyncio.Server \| None | |
| clients | set[StreamWriter] | Max 8 |
| drops | int | Mirror backpressure counter |

## State transitions

```text
Hub: idle → card_selected → (optional) override_edit → Start → Running
Discovery: poll → stability_counter → emit snapshot → UI render
TcpSink: disabled → listen → clients_connect → mirror_writes → Stop → clear
```
