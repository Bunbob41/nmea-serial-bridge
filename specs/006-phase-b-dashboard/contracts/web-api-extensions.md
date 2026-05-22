# Contract: Web API Extensions (Phase B Dashboard)

**Modules**: `web_api.py`, `app_facade.py`, `web/static/*`  
**Base contract**: [`specs/005-hybrid-ui-webui/contracts/web-api.md`](../../005-hybrid-ui-webui/contracts/web-api.md)  
**Default base**: `http://127.0.0.1:8765`

## Route changes

| Before (005) | After (006) |
|--------------|-------------|
| `GET /` → JSON service index | `GET /` → HTML dashboard (`text/html`) |
| — | `GET /api` → JSON service index (same body as old `GET /`) |
| `GET /health` | Unchanged |

All 005 routes remain: `/status`, `/config`, `/bridge/start`, `/bridge/stop`, `/docs`.

## New endpoints

### `GET /meta`

Response `200`:

```json
{
  "version": "1.8.0",
  "lan_bind": false,
  "token_required": false
}
```

`token_required` = `lan_bind && token` configured in prefs. No token value returned.

---

### `GET /discovery`

Response `200` — `WebDiscoveryPayload` (see `data-model.md`).

Read from façade cache (main-thread updates only). Safe at 2 Hz during scan.

---

### `POST /discovery/refresh`

| Result | Body |
|--------|------|
| 200 | `{ "ok": true, "message": "Discovery scan started", "state": "scanning" }` |
| 409 | `{ "ok": false, "error_code": "busy", "message": "..." }` if scan already running |

Does **not** wait for scan completion. Client polls `GET /discovery`.

Auth: same as 005 mutating routes when LAN + token.

---

### `POST /ports/unlock`

| Result | Body |
|--------|------|
| 200 | `{ "ok": true, "message": "<smart_release reason>", "state": "stopped" }` |
| 400 | validation (e.g. empty COM) |
| 503 | window unavailable |

Delegates to `smart_release_com` on Qt main thread. No `QMessageBox` on API path.

Auth: same as 005 mutating routes when LAN + token.

---

## Static assets

| Path | File |
|------|------|
| `GET /` | `web/static/index.html` |
| `GET /dashboard.css` | `web/static/dashboard.css` (or relative paths via static mount) |
| `GET /dashboard.js` | `web/static/dashboard.js` |

## Dashboard client behavior (contract)

| Action | HTTP |
|--------|------|
| Init | `GET /meta`, `GET /config` |
| Telemetry loop | `GET /status` every **1000 ms** |
| Start / Stop | `POST /bridge/start`, `/bridge/stop` |
| Unlock | `POST /ports/unlock` |
| Refresh discovery | `POST /discovery/refresh` then `GET /discovery` every **500 ms** max **15 s** |
| Select device | `PATCH /config` `{ "com_port", "hub_device_id" }` |
| Token | Header `X-Bridge-Token` on mutating calls when `token_required` |

## Invariants

- Handlers MUST NOT import bridge protocol or touch Qt from HTTP thread.
- `GET /health` body unchanged (`{ "ok", "version" }`).
- OpenAPI documents all new response models (no `additionalProp1` placeholders).

## Tests

- `test_web_api.py` — `/meta`, `/discovery`, unlock/refresh, `GET /` content-type
- `test_app_facade.py` — discovery cache, unlock/refresh delegation
