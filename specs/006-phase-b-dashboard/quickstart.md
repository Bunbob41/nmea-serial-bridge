# Quickstart: Phase B Operator Dashboard

**Branch**: `2033-phase-b-dashboard`  
**Target version**: 1.8.0 (after `/speckit-implement`)  
**Prerequisite**: 005 Web API (v1.7.2+), `requirements-web.txt`

## Prerequisites

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python -m pip install -r requirements.txt
python -m pip install -r requirements-web.txt
```

## Enable Web control plane

1. Launch `python bridge_gui.py`
2. **Tools → Guide** → enable **Web API**, port **8765**
3. Optional: **LAN bind** + set token for phone/Tailscale

## Phase A — Dashboard (P1)

1. Open **`http://127.0.0.1:8765/`** (not `/docs`)
2. Confirm status card updates ~1/s when bridge running
3. Tap **Start** / **Stop** — desktop banner should match within ~2 s
4. Stop app — dashboard shows **offline**

## Phase B — Discovery + COM (P3)

1. Plug USB serial (or use com0com bench)
2. Tap **Refresh discovery** — list updates within **15 s**
3. Select a device — **GET /config** shows chosen COM
4. **Start** bridge from dashboard

## Phase C — Unlock (P2)

1. With port lock scenario, tap **Unlock ports**
2. Confirm message in UI matches desktop unlock log class

## Phase D — LAN / token

1. Enable LAN bind + token in Guide
2. Reload dashboard — token field visible (`GET /meta` → `token_required: true`)
3. Enter token, save (localStorage), **Start** succeeds from phone at `http://<PC-IP>:8765/`

## Phase E — API smoke (curl)

```powershell
curl -s http://127.0.0.1:8765/meta
curl -s http://127.0.0.1:8765/discovery
curl -s -X POST http://127.0.0.1:8765/discovery/refresh
curl -s -X POST http://127.0.0.1:8765/ports/unlock
curl -s http://127.0.0.1:8765/api
```

## Phase F — Automated gate

```powershell
python -m unittest test_web_api test_app_facade -v
python verify_all.py
```

## Offline CSS check (SC-103)

1. Disconnect internet (or block CDN — should not matter)
2. Reload `http://127.0.0.1:8765/` — layout and buttons still usable

## Frozen build

```powershell
.\release.ps1
# Confirm web/static in bundle; OPERATOR_GUIDE documents dashboard URL
```
