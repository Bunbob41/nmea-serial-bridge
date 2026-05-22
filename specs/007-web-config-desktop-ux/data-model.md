# Data Model: Web Config Editor & Desktop UX Fixes

**Feature**: `specs/007-web-config-desktop-ux`

## EditableWebConfig (dashboard form state)

| Field | Type | Maps to PATCH |
|-------|------|----------------|
| `com_port` | string | `com_port` |
| `baud` | int | `baud` |
| `network_mode` | enum | `network_mode` |
| `udp_listen_host` | string | `udp_listen_host` |
| `udp_listen_port` | int | `udp_listen_port` |
| `remote_host` | string | *(via façade → `remote_host` widget when mode tcp/udp remote)* |
| `remote_port` | int | *(via façade → `remote_port` widget)* |

### network_mode enum

`udp_listen` | `udp_remote` | `tcp_client` | `tcp_server`

## TokenQrDisplay (browser)

| Field | Storage | Notes |
|-------|---------|-------|
| `show_qr` | `localStorage` key `nmea-bridge-show-qr` | Opt-in checkbox |
| `token` | `localStorage` `nmea-bridge-web-token` | Existing 006 |

## ConnectLayoutPrefs (existing)

Reuses `ui_prefs` `connect_panel` heights + `splitter_sizes` for Standard mode.

## GET /token-qr (new read-only asset)

| Response | Condition |
|----------|-----------|
| `image/svg+xml` body | `web_ui.token` non-empty |
| 404 | No token configured |

No secret in JSON responses beyond existing meta.

## State transitions

```text
stopped + edit form → PATCH /config → idle (config updated)
running + edit form → Save blocked (UI) or 409 (API)
show_qr checked → GET /token-qr → display SVG
```
