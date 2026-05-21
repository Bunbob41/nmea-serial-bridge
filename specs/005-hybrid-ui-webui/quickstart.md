# Quickstart: Hybrid UI — Qt `.ui` + Web API

**Branch**: `2032-hybrid-ui-webui`  
**Target version**: 1.7.0 (after `/speckit-implement`)

## Prerequisites

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python -m pip install -r requirements.txt
python -m pip install -r requirements-web.txt   # fastapi, uvicorn
```

Bench: com0com pair or real COM; UDP sender optional.

## Phase A — Layout loader

1. Open `ui/resources/standard_connect_shell.ui` in **Qt Designer** (ships with PySide6).
2. Change a visible label margin; save.
3. Launch Standard UI:

```powershell
python bridge_gui.py --ui standard
```

4. Confirm layout change without editing `standard.py` logic.
5. Run `python -m unittest test_ui_loader -v`.

## Phase B — Web API (localhost)

1. Enable Web in app (Tools or prefs) or set `ui_prefs.json`:

```json
"web_ui": { "enabled": true, "host": "127.0.0.1", "port": 8765 }
```

2. Restart app; verify listener:

```powershell
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/status | python -m json.tool
```

3. Configure COM (desktop or API):

```powershell
curl -s -X PATCH http://127.0.0.1:8765/config `
  -H "Content-Type: application/json" `
  -d '{"com_port":"COM7","baud":115200,"udp_listen_port":10110}'
```

4. Start / stop from Web:

```powershell
curl -s -X POST http://127.0.0.1:8765/bridge/start
curl -s http://127.0.0.1:8765/status
curl -s -X POST http://127.0.0.1:8765/bridge/stop
```

5. Desktop Start/Stop and status banner should match within **2 s** (SC-201).

## Phase C — Responsiveness (SC-203)

While bridge running:

```powershell
# PowerShell loop ~5 Hz for 60 s
1..300 | ForEach-Object {
  Invoke-RestMethod http://127.0.0.1:8765/status | Out-Null
  Start-Sleep -Milliseconds 200
}
```

During loop: resize main window and drag Connect splitter — UI must stay responsive (p95 &lt; 100 ms subjective; no stuck resize).

## Phase D — Negative tests (SC-205)

- `POST /bridge/start` with baud `999999` → 400 validation, same message class as desktop.
- `PATCH /config` com change while running → 409 `running_guard`.
- `PATCH /config` NTRIP fields (if exposed) → 501 `unsupported`.

## Phase E — Automated gate

```powershell
python verify_all.py
python tools/run_unittests.py
```

Optional: `python bench_web_api.py` (10× start/stop agreement SC-202).

## Frozen build

```powershell
.\release.ps1
# Confirm ui/resources/*.ui inside zip; Web port documented in OPERATOR_GUIDE
```
