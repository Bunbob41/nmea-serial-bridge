# Contract: Dashboard Editable Configuration

**Assets**: `web/static/index.html`, `dashboard.css`, `dashboard.js`  
**API**: `GET /config`, `GET /status`, `GET /discovery`, `PATCH /config`

## Config form regions

| Control | Type | Visible when |
|---------|------|--------------|
| COM port | `<select>` + optional manual | Always; disabled if running |
| Baud | number input | Stopped only |
| Network mode | `<select>` 4 modes | Stopped only |
| UDP listen host/port | text/number | mode = udp_listen |
| Remote host/port | text/number | mode = udp_remote or tcp_client |
| TCP server port | number | mode = tcp_server |
| Save configuration | primary button | Stopped only |
| Lock banner | text | running |

## Save behavior

- `PATCH /config` JSON body with changed fields only
- `X-Bridge-Token` when `meta.token_required`
- On 409 `running_guard`: show message, do not clear form
- On success: refresh config readback + status poll

## QR token (Tools section)

| Control | Behavior |
|---------|----------|
| Show QR for API token | checkbox, `localStorage` `nmea-bridge-show-qr` |
| QR image | `<img src="/token-qr" alt="API token QR">` when checked |
| Token caption | monospace, user-select all |

## Responsive

- Form single column &lt; 768px; two-column optional for host/port on wide screens
- No horizontal scroll at 360px

## Out of scope

- NTRIP, fan-out, nmea_mode edit (read-only display OK)
