# Data Model: Phase B Operator Dashboard

**Feature**: `specs/006-phase-b-dashboard`

## WebMeta (GET `/meta`)

| Field | Type | Source |
|-------|------|--------|
| `version` | str | `version.__version__` |
| `lan_bind` | bool | `web_ui.lan_bind` |
| `token_required` | bool | `lan_bind && token` non-empty |

No secrets exposed.

---

## WebDiscoveryPayload (GET `/discovery`)

| Field | Type | Notes |
|-------|------|-------|
| `updated_mono` | float | Snapshot write time |
| `scan_note` | str | Hub footer note / scan status |
| `scan_busy` | bool | True while `DiscoveryScanWorker` running |
| `serial_devices` | list[SerialDeviceDto] | |
| `network_cards` | list[NetworkCardDto] | |
| `errors` | list[str] | Non-fatal scan errors |

### SerialDeviceDto

| Field | Type |
|-------|------|
| `device_id` | str |
| `port` | str |
| `description` | str |
| `manufacturer` | str |
| `match_keyword` | str |
| `status` | str |

### NetworkCardDto

| Field | Type |
|-------|------|
| `device_id` | str |
| `label` | str |
| `mode_hint` | str |
| `host` | str |
| `port` | int |
| `port_available` | bool |
| `peer_count` | int |
| `status` | str |
| `discovery_source` | str |

Mapped from `discovery_service.DiscoverySnapshot` / hub cache.

---

## UnlockCommandResult (POST `/ports/unlock`)

Uses existing **`WebCommandResult`**:

| Field | Notes |
|-------|-------|
| `ok` | True if release attempt completed (may still warn) |
| `message` | `smart_release_com` reason + optional UDP hint |
| `error_code` | `validation` if no COM; null on success |

---

## DiscoveryRefreshResult (POST `/discovery/refresh`)

| Field | Type | Notes |
|-------|------|-------|
| `ok` | bool | Acknowledgment (scan started or already running) |
| `message` | str | e.g. "Discovery scan started" |
| `state` | str | `scanning` \| `idle` |

Does not embed full device list (client polls GET `/discovery`).

---

## DashboardSession (browser, informal)

| State | Notes |
|-------|-------|
| `connected` | Last status fetch ok |
| `commandInFlight` | Disables Start/Stop/Unlock/Refresh |
| `discoveryScanning` | Poll loop active (≤ 15 s) |
| `token` | From `localStorage` when `token_required` |

---

## Existing entities (reuse from 005)

- **WebSessionState** — `GET /status`
- **WebConfigPayload** — `GET/PATCH /config`
- **WebCommandResult** — start/stop/config/errors

---

## State transitions

```text
idle --[POST /discovery/refresh]--> scanning --[GET /discovery updated | 15s timeout]--> idle

stopped --[POST /bridge/start]--> starting --> running
running --[POST /bridge/stop]--> stopping --> stopped

running --[PATCH /config com change]--> 409 running_guard (unchanged from 005)
```

---

## Relationships

```text
dashboard.js --fetch--> FastAPI (web_api.py)
                          ├── read: /meta, /status, /config, /discovery
                          └── write: /bridge/*, /config, /ports/unlock, /discovery/refresh
                                    └── BridgeAppFacade
                                            ├── snapshot (status)
                                            ├── discovery cache
                                            └── Qt main: mixin hub/unlock/discovery
```
