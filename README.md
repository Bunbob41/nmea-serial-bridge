# Serial Link

[![Release](https://img.shields.io/github/v/release/Bunbob41/nmea-serial-bridge?label=download&sort=semver)](https://github.com/Bunbob41/nmea-serial-bridge/releases/latest)
[![License](https://img.shields.io/github/license/Bunbob41/nmea-serial-bridge)](LICENSE)
[![CI](https://github.com/Bunbob41/nmea-serial-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/Bunbob41/nmea-serial-bridge/actions/workflows/ci.yml)

**Serial Link** (`serial-link.exe`) is a Windows desktop app that **bidirectionally bridges** traffic between **UDP/TCP** and a **serial COM port**. Built for survey / USV workflows — NMEA 0183, raw binary (RTCM / MAVLink), **Fleet** multi-stream, and **Modern** or **Field** layouts.

| | |
| --- | --- |
| **Download** | [Latest release](https://github.com/Bunbob41/nmea-serial-bridge/releases/latest) — unzip and run `serial-link.exe` |
| **Version** | [`version.py`](version.py) |
| **Repo name** | `nmea-serial-bridge` (product: **Serial Link**) |

**Spec Kit baseline**: [`specs/001-baseline-spec/spec.md`](specs/001-baseline-spec/spec.md) (as-built FR traceability).

**Stack:** Python 3.10+, [PySide6](https://doc.qt.io/qtforpython/), [pyserial-asyncio](https://pyserial-asyncio.readthedocs.io/). Bridge I/O runs on a **background asyncio thread**; the GUI stays on the Qt main thread.

**Documentation**

| Doc | Audience |
| --- | -------- |
| [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) | First install + 15-minute bench walkthrough |
| [`docs/OPERATOR_GUIDE.md`](docs/OPERATOR_GUIDE.md) | Full operator manual |
| [`docs/NORBIT_DCT.md`](docs/NORBIT_DCT.md) | NORBIT DCT + Applanix workflow |
| [`docs/README.md`](docs/README.md) | Doc index |

**Frozen build:** `.\release.ps1` (or `.\build.ps1` then zip under `dist\`)

## Features

- **Network modes (one per session)**  
  - **UDP listen** — bind on this PC; remote devices send in. **Fan-out** (default on): serial→network goes to **every UDP sender** registered this session. Uncheck *Fan-out* on Connect for legacy **single-link** (most recent sender only).  
  - **UDP remote** — fixed peer (advanced).  
  - **TCP server** / **TCP client** — under *Advanced* network; TCP client auto-reconnects with configurable delay.

- **Serial** — COM list, baud, refresh; **auto-reconnect COM** (optional, on by default) if the port drops while the bridge stays Running.  
- **Named presets** — **Presets** tab (or survey bar **Presets** menu): load, save, save as, delete; stored in `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json`. Shipped built-ins come from neutral `bench_defaults.json` beside the `.exe`; optional `bench_defaults.local.json` overrides for your fleet (not in release zips).

- **Queues & backpressure** — bounded queues; drop / reject counters in the status bar and Survey HUD.

- **Live log** — throttled; optional **verbose** per-sentence view (NMEA text modes).

- **NMEA tab** — **Passthrough** (recommended for Trimble NMEA), **Strict** (+ checksum + sentence filter), or **Raw binary** (RTCM / **MAVLink** / other binary passthrough).

- **Cube / MAVLink + Mission Planner** — Raw binary + UDP listen; GCS uses **UDP Client** to the bridge (see `docs/OPERATOR_GUIDE.md` §5.6). Shipped **Cube MAVLink** preset.

- **Send tab** — inject NMEA text (`\r\n` normalized); **not** for binary streams.

- **Diagnostics** (Tools) — collapsible cards: automated checks (`verify_all`, checklists, UDP/TCP bench tools), rotating file log, on-screen log clear, traffic legend; **Reorder cards…**

- **UI layouts** — **Modern** (header chips + tool pages) and **Field** (log-first, survey bar, tools drawer). Launcher remembers choice. **UI editor** reorders Connect sections and panel visibility.

- **Survey workflow** — Survey HUD popout, **GNSS** status (GGA fix / sats / HDOP), in-app **Guide** (Bench Tools), preflight menus, themes, recent sessions.
- **Connection Hub (Modern Connect)** — card grid for GNSS COM + UDP listen + **LAN-discovered** hosts (Refresh discovery); **Unlock ports** for bench COM conflicts; live **QoS** on the active card; **Manual override** for TCP/advanced; optional **TCP sink mirror** (parallel egress with fan-out). Field strip adds Refresh/Unlock.
- **Hybrid UI (v1.7+)** — Qt Designer shells; optional **Web API** + browser **operator dashboard** (`requirements-web.txt`) — status, config, discovery, start/stop, log, map, Survey monitor; optional **GridStack beta** layout — see `specs/005-hybrid-ui-webui/quickstart.md` and `specs/006-phase-b-dashboard/quickstart.md`.
- **Connect** — collapsible panels (Serial & network defaults under Run), quick log/terminal, intent hint.
- **Log** — full live log with presets, pause, save.
- **Phone** (Bench Tools) — Web API, token, QR, phone dashboard setup.
- **Guide** (Bench Tools) — UDP/TCP connection workflows, links to operator docs.

## Requirements

- **Windows** (primary target).  
- **Python 3.10+** for dev; frozen **`.exe`** for field PCs.  
- COM drivers for your hardware (USB serial, com0com on bench).

## Install (development)

```powershell
cd nmea-serial-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

### Launcher

```powershell
.\launch_bridge_gui.bat
# or
python launcher.py
python launcher.py --ui field
python launcher.py --ui modern
```

| UI | Use |
|----|-----|
| **Modern** | Header chips (Connect, Log, Bench Tools, Fleet, …), card-based Connect hub |
| **Field** | Large log, COM/UDP strip, Tools drawer, survey bar (**Presets**, **Recent**, **Checklists**, **HUD**) |

Saved layout: `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json`

**Desktop shortcut:** `.\create_desktop_shortcut.bat` (re-run after moving the project folder).

### Typical workflow

1. **Presets** — load bench or boat preset → confirm COM + UDP on **Connect** (Modern) or the strip (Field) → **Start** → **Running**.  
2. **NMEA** — **Passthrough** for Trimble/R10 NMEA; **Raw** only for binary RTCM or other non-NMEA streams.  
3. **Send** — manual inject on bench (watch **paired** com0com port, not bridge COM).  
4. **Stop** when finished.

### Bench (com0com)

Bridge owns e.g. **COM7**; Tera Term on **paired** port (e.g. **COM12**). Simulator **sends to** `127.0.0.1:10110` — bridge **listens**.

```powershell
python com_free.py
python check_setup.py
python bridge_gui.py
python nmea_static_sample.py
```

### Boat (INS on Ethernet)

INS **sends** UDP to survey PC `pc_ip:port`. Bridge **listens**; does not dial the INS. Static IP on survey Ethernet recommended; **Tailscale** is fine for R&D if INS/simulator targets the Tailscale IP and firewall allows UDP.

```powershell
python check_setup.py --production
```

### Network notes (MikroTik / Tailscale)

| Link | Guidance |
|------|----------|
| **MikroTik point-to-point** | Low jitter; treat like LAN. INS unicast to survey PC IP:port. |
| **Tailscale** | Works for lab/R&D when the sender uses the PC’s **Tailscale IP** and UDP/TCP is allowed. Extra latency — validate Hz on Survey HUD. |
| **TCP client mode** | Bridge reconnects to server automatically; tune delay under Advanced. |

This app does **not** configure routers or VPN — only binds/ connects on the Windows PC.

## Verify

```powershell
python verify_all.py
```

From project folder (not `System32`). Skips exclusive COM/UDP steps if bridge already Running unless `VERIFY_ALL_NO_SKIP=1`.

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Frozen build (field PCs)

1. Download `serial-link-v<version>-win64.zip` from GitHub Releases.  
2. Unzip; run `serial-link.exe`.  
3. Optional `bench_defaults.local.json` beside exe for fleet LAN/COM overrides (copy from `bench_defaults.local.json.example`; not shipped publicly).

```powershell
.\release.ps1
.\release.ps1 -Publish
```

Version: `version.py` + `CHANGELOG.md`.

## Project layout

| Path | Role |
|------|------|
| `bridge_core.py` | Async engine (serial, UDP/TCP, queues, reconnect) |
| `nmea_codec.py` | Line assembly, strict checksum, filters |
| `bridge_gui.py` | GUI entry |
| `tests/` | Unit tests (`test_*.py`) + fixtures |
| `ui/` | Modern, Field, demo, HUD, diagnostics, Fleet |
| `docs/GETTING_STARTED.md` | First install and walkthrough |
| `docs/OPERATOR_GUIDE.md` | Step-by-step operator manual |
| `docs/NORBIT_DCT.md` | NORBIT DCT operator notes |
| `bench_defaults.json` | Shipped neutral Desk / Boat / NORBIT built-ins |
| `bench_defaults.local.json` | Optional local override (gitignored; not in public zip) |

## What this app is not

- Not a GNSS post-processor or vehicle configuration tool.  
- Not a binary protocol encoder — **Raw** mode only forwards bytes unchanged.  
- Forwards **bytes** — validate on bench before operational use.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

## Disclaimer

Use at your own risk on operational hardware. Validate on a bench before depending on it for navigation or survey positioning.
