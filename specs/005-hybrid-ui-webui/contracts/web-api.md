# Contract: Web Control API

**Modules**: `web_api.py`, `web_server.py`, `app_facade.py`  
**Transport**: HTTP/JSON on loopback (optional LAN)  
**Default base**: `http://127.0.0.1:8765`

## Authentication

| Mode | Rule |
|------|------|
| Localhost only | No header required |
| LAN bind + token configured | `X-Bridge-Token: <token>` required on `PATCH`, `POST` |

`GET` may remain unauthenticated on localhost; when LAN + token, require token on all routes.

## Endpoints (MVP)

### `GET /health`

Response `200` — `HealthResponse`: `{ "ok": true, "version": "<app>" }`.

### `GET /status`

Response `200` — `StatusResponse` / `WebSessionState` (see `data-model.md`). OpenAPI schema exposed in `/docs`.

### `GET /config`

Response `200` — `WebConfigPayload`.

### `PATCH /config`

Request body: partial `WebConfigPayload` fields.

| Result | Body |
|--------|------|
| 200 | `{ "ok": true, "message": "...", "config": { ... } }` |
| 400 | `{ "ok": false, "error_code": "validation", "message": "..." }` |
| 409 | `{ "ok": false, "error_code": "running_guard", "message": "Stop bridge first" }` |
| 501 | `{ "ok": false, "error_code": "unsupported", "message": "..." }` |

### `POST /bridge/start`

| Result | Body |
|--------|------|
| 200 | `{ "ok": true, "state": "running", "message": "..." }` |
| 400 | validation (same text class as desktop `_validate_before_start`) |
| 409 | `busy` or already running |

Delegates to mixin `start_bridge()` on Qt main thread.

### `POST /bridge/stop`

| Result | Body |
|--------|------|
| 200 | `{ "ok": true, "state": "stopped", "message": "..." }` |

Delegates to mixin `stop_bridge()` on Qt main thread.

## Invariants

- Handlers MUST NOT import `PySide6` widgets or call `bridge_core` directly.
- At most one bridge session; start/stop serialized with desktop UI.
- Snapshot age for status fields ≤ 2 s under normal stats traffic (SC-201).
- Unsupported Phase B fields return `501` with `error_code=unsupported`, never silent success.

## Tests

- `test_web_api.py` — `httpx`/`TestClient` against `create_app(mock_facade)`.
- `bench_web_api.py` — optional live server loop (com0com bench).
