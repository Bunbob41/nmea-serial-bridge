# nmea-serial-bridge

**Current release: v1.3.6** — Windows desktop app that **bidirectionally bridges** traffic between **UDP/TCP** and a **serial COM port**. Primary use: **NMEA 0183 text** for survey / USV workflows — Ethernet GNSS or INS (e.g. Trimble R10) → bridge → physical COM destination.

**Stack:** Python 3.10+, [PySide6](https://doc.qt.io/qtforpython/), [pyserial-asyncio](https://pyserial-asyncio.readthedocs.io/). Bridge I/O runs on a **background asyncio thread**; the GUI stays on the Qt main thread.

**Operator manual:** [`docs/OPERATOR_GUIDE.md`](docs/OPERATOR_GUIDE.md)

**Frozen build:** `.\release.ps1` (or `.\build.ps1` then zip under `dist\`)

## Features

- **Network modes (one per session)**  
  - **UDP listen** — bind on this PC; replies toward serial go to the **last UDP sender** (typical for bench + boat INS).  
  - **UDP remote** — fixed peer (advanced).  
  - **TCP server** / **TCP client** — under *Advanced* network; TCP client auto-reconnects with configurable delay.

- **Serial** — COM list, baud, refresh; **auto-reconnect COM** (optional, on by default) if the port drops while the bridge stays Running.  
- **Named presets** — **Presets** tab (or survey bar **Presets** menu): load, save, save as, delete; stored in `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json`. Shipped defaults in `bench_defaults.json` (or beside the `.exe`).

- **Queues & backpressure** — bounded queues; drop / reject counters in the status bar and Survey HUD.

- **Live log** — throttled; optional **verbose** per-sentence view (NMEA text modes).

- **NMEA tab** — **Passthrough** (recommended for Trimble NMEA), **Strict** (+ checksum + sentence filter), or **Raw binary** (RTCM / other binary passthrough).

- **Send tab** — inject NMEA text (`\r\n` normalized); **not** for binary streams.

- **Diagnostics** — file log, checklists, UDP burst, TCP stress/demo, verify suite.

- **UI layouts** — **Standard** (Connect + Presets + tool tabs + log) and **Field** (log-first, survey bar, tools drawer). Launcher remembers choice.

- **Survey workflow** — Survey HUD popout, **GNSS** status (GGA fix / sats / HDOP), product demo teleprompter, preflight menus, themes.
- **Connect tab (Standard)** — collapsible panels, NTRIP corrections (phase 1), quick log/terminal.
- **Log tab** — full live log (replaces side-only log in Standard).

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
python bridge_gui.py --ui field --demo
```

| UI | Use |
|----|-----|
| **Standard** | Connect, NMEA, Send, Diagnostics + log |
| **Field** | Large log, COM/UDP strip, Tools drawer, survey bar (**Presets**, **Recent**, **Checklists**, **HUD**, **Demo**) |

Saved layout: `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json`

**Desktop shortcut:** `.\create_desktop_shortcut.bat` (re-run after moving the project folder).

### Typical workflow

1. **Presets** — load bench or boat preset → confirm COM + UDP on **Connect** (Standard) or the strip (Field) → **Start** → **Running**.  
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
python -m unittest discover -s . -p "test_*.py" -v
```

## Frozen build (field PCs)

1. Download `nmea-serial-bridge-v<version>-win64.zip` from GitHub Releases.  
2. Unzip; run `nmea-serial-bridge.exe`.  
3. Optional `bench_defaults.json` beside exe for fleet defaults.

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
| `ui/` | Standard, Field, demo, HUD, diagnostics |
| `docs/OPERATOR_GUIDE.md` | Step-by-step operator manual |
| `bench_defaults.json` | Shipped Desk + production defaults |

## What this app is not

- Not a GNSS post-processor or vehicle configuration tool.  
- Not a binary protocol encoder — **Raw** mode only forwards bytes unchanged.  
- Forwards **bytes** — validate on bench before operational use.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

## Disclaimer

Use at your own risk on operational hardware. Validate on a bench before depending on it for navigation or survey positioning.
