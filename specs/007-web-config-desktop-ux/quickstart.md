# Quickstart: 007 Web Config & Desktop UX

## Prerequisites

- v1.8.4+ with Web API enabled
- `pip install -r requirements-web.txt`
- Bench: com0com pair or USB serial

## Phase A — Editable web config (US1)

1. Start app, enable Web API, open `http://127.0.0.1:8765/`
2. Stop bridge if running
3. Change COM, baud, UDP port in **Configuration** form → **Save**
4. Confirm desktop Connect matches; Start bridge; verify UDP/COM in status

## Phase B — QR token (US2)

1. Tools → Guide: Generate token, enable LAN if needed
2. On PC browser dashboard: check **Show QR for API token**
3. Scan with phone camera; paste into phone dashboard token field
4. Start bridge from phone with token

## Phase C — Field clipping (US3)

1. Field layout, default window size
2. Tools ▾ → Guide tab
3. Verify Web control rows not clipped; resize window short — scroll appears

## Phase D — Standard COM + resize (US4–US5)

1. Standard layout → Connect
2. COM dropdown lists ports; selection sticks
3. Drag vertical splitter between Run and Connection panels
4. Restart app — sizes restored; **Reset sizes** on Connect toolbar

## Automated

```powershell
python -m unittest test_web_api test_app_facade -v
python verify_all.py
```
