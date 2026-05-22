# Control Parity Matrix (MVP baseline)

**Feature**: `specs/005-hybrid-ui-webui`  
**Purpose**: FR-207 — every desktop control mapped to Web phase; gaps explicit.

Legend: **MVP** = this epic | **B** = Phase B | **RO** = read-only via API | **—** = out of scope

## Connect — Run panel

| control_id | Desktop | Web | API / notes |
|------------|---------|-----|-------------|
| `bridge.start` | Start bridge button | MVP | `POST /bridge/start` |
| `bridge.stop` | Stop bridge button | MVP | `POST /bridge/stop` |
| `bridge.status_banner` | Status banner | MVP | `GET /status` |
| `fanout.enable` | Fan-out checkbox | B | read in config; write deferred |
| `run.panel_layout` | UI editor order | — | desktop only |

## Connect — Connection / Hub

| control_id | Desktop | Web | API / notes |
|------------|---------|-----|-------------|
| `hub.select_device` | Card selection | MVP | `PATCH /config` `hub_device_id` |
| `hub.refresh_discovery` | Refresh discovery | **B ✅** | `POST /discovery/refresh`; polls `GET /discovery` |
| `hub.unlock_ports` | Unlock ports | **B ✅** | `POST /ports/unlock`; `smart_release_com` on main thread |
| `hub.qos_display` | QoS on card | RO | `GET /status` aggregates Hz/drops |
| `serial.com` | COM combo | MVP | `config.com_port`; dashboard form (007 ✅) |
| `serial.baud` | Baud field | MVP | `config.baud`; dashboard form (007 ✅) |
| `serial.refresh_ports` | Refresh COM | B | |
| `serial.auto_reconnect` | Auto-reconnect | B | |
| `serial.auto_discover` | Auto-discover GNSS | B | |
| `net.listen_host` | UDP listen host | MVP | `config.udp_listen_host` |
| `net.listen_port` | UDP listen port | MVP | `config.udp_listen_port` |
| `nmea.mode` | NMEA mode | MVP | `config.nmea_mode` |
| `manual.override` | Manual override toggle | RO | `config.manual_override` read; partial write |
| `net.advanced_tcp` | Advanced TCP/UDP | **007 ✅** | `config.network_mode` + host/port on dashboard |
| `net.tcp_sink` | TCP sink mirror | B | |
| `ntrip.panel` | NTRIP section | — | desktop only |

## Field strip

| control_id | Desktop | Web | API / notes |
|------------|---------|-----|-------------|
| `field.com_udp` | Compact COM/UDP | MVP | same as `config.*` |
| `field.refresh` | Refresh | **B ✅** | `POST /discovery/refresh` |
| `field.unlock` | Unlock | **B ✅** | `POST /ports/unlock` |
| `field.tools_drawer` | Tools drawer | — | |

## Global / other modes

| control_id | Desktop | Web | API / notes |
|------------|---------|-----|-------------|
| `hud.open` | Survey HUD | — | |
| `theme.select` | Theme | — | |
| `ui.editor` | UI editor | — | |
| `presets.load_save` | Presets tab | B | optional `GET/PUT /presets/{name}` |
| `diag.scripts` | Diagnostic scripts | — | |
| `web.settings` | Web enable/port | MVP | `ui_prefs` + `GET /meta` (Phase B ✅) |

## MVP coverage summary

- **In scope (MVP / Phase B)**: start, stop, status, core config (COM, baud, UDP listen, NMEA mode, hub id), discovery refresh, unlock ports.
- **Phase B shipped (v1.8.0)**: `GET /`, `GET /meta`, `GET /discovery`, `POST /discovery/refresh`, `POST /ports/unlock`, `GET /api`; static HTML dashboard at `GET /`.
- **Explicitly deferred**: fan-out, NTRIP, TCP advanced, presets write.
- **Implement**: return `501 unsupported` for deferred **write** attempts if exposed accidentally.
