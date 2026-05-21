# Data Model: Hybrid UI — Qt Visual + WebUI Bridge

**Feature**: `specs/005-hybrid-ui-webui`

## LayoutResource

| Field | Type | Notes |
|-------|------|-------|
| `name` | str | e.g. `standard_connect_shell`, `field_control_strip` |
| `relative_path` | str | `ui/resources/{name}.ui` |
| `ui_mode` | enum | `standard` \| `field` |
| `version` | str | App version when file last validated (informational) |
| `load_state` | enum | `ok` \| `fallback_programmatic` \| `error` |

**Validation**: File exists and parses under `QUiLoader`; required object names documented in `contracts/qt-ui-loader.md`.

---

## WebUiPrefs (persisted in `ui_prefs.json`)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` | bool | `false` | Operator opt-in for field laptops |
| `host` | str | `127.0.0.1` | `0.0.0.0` only when `lan_bind` true |
| `port` | int | `8765` | 1024–65535 |
| `lan_bind` | bool | `false` | Requires operator guide acknowledgment |
| `token` | str \| null | null | Required on write when LAN + token set |

---

## WebSessionState (GET `/status`)

| Field | Type | Source |
|-------|------|--------|
| `running` | bool | `bridge.running` |
| `com_port` | str | `com_cb` / active session |
| `baud` | int | `baud_edit` |
| `udp_listen_host` | str | listen host field |
| `udp_listen_port` | int | listen port field |
| `nmea_mode` | str | passthrough \| strict \| raw |
| `hz_net_to_com` | float \| null | stats coalesced |
| `hz_com_to_net` | float \| null | stats coalesced |
| `drops` | int | stats |
| `rejects` | int | stats |
| `last_error` | str \| null | last start/validation error |
| `updated_mono` | float | snapshot write time |

---

## WebConfigPayload (GET/PATCH `/config`)

| Field | Type | Writable when stopped | Writable when running |
|-------|------|----------------------|------------------------|
| `com_port` | str | yes | no (stop-first) |
| `baud` | int | yes | no |
| `udp_listen_host` | str | yes | no |
| `udp_listen_port` | int | yes | no |
| `nmea_mode` | str | yes | no |
| `hub_device_id` | str \| null | yes | yes (selection only) |
| `manual_override` | bool | yes | yes |
| `network_mode` | str | yes | no | `udp_listen` \| `tcp_server` \| … (read reflects desktop) |

**Validation**: Reuse `ui/connection_fields.py` (`validate_baud`, `validate_udp_port`) inside façade before applying.

---

## WebCommandResult

| Field | Type | Notes |
|-------|------|-------|
| `ok` | bool | |
| `message` | str | Operator-readable |
| `error_code` | str \| null | `validation` \| `busy` \| `running_guard` \| `unsupported` |
| `state` | str | `stopped` \| `starting` \| `running` \| `stopping` |

---

## ControlParityEntry

| Field | Type | Notes |
|-------|------|-------|
| `control_id` | str | Stable slug |
| `desktop_location` | str | e.g. `Connect/run/Start bridge` |
| `web_phase` | enum | `mvp` \| `phase_b` \| `read_only` \| `out_of_scope` |
| `api_surface` | str \| null | e.g. `POST /bridge/start` |
| `notes` | str | |

---

## State transitions (bridge command)

```text
stopped --[POST /bridge/start valid]--> starting --[bridge ok]--> running
running --[POST /bridge/stop]--> stopping --[teardown ok]--> stopped
any --[invalid config]--> stopped (message set on WebCommandResult)
```

Concurrent desktop + Web commands: single-flight lock; second request returns `error_code=busy`.

---

## Relationships

```text
BridgeWindow (Qt) ──owns──> BridgeLogicMixin
        │
        ├── publishes ──> BridgeAppFacade.snapshot (WebSessionState)
        ├── applies <── WebConfigPayload (via queued slots)
        └── loads ──> LayoutResource (.ui)

WebServerThread ──serves──> FastAPI ──calls──> BridgeAppFacade (reads lock / enqueue writes)
```
