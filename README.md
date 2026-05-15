# nmea-serial-bridge

Windows desktop app that **bidirectionally bridges** NMEA-style (text) traffic between **UDP/TCP** and a **serial COM port**. Built for survey / USV-style workflows: Ethernet NMEA (Trimble/INS or simulator) → bridge → physical COM → autopilot GPS UART (e.g. Cube Orange), with Mission Planner on a separate path.

**Stack:** Python 3.10+, [PySide6](https://doc.qt.io/qtforpython/), [pyserial-asyncio](https://pyserial-asyncio.readthedocs.io/). Bridge I/O runs on a **background asyncio thread** so the GUI stays responsive.

## Features

- **Network modes (one per session)**  
  - **UDP listen** — bind on this PC; replies to serial go to the **last UDP sender** (standard for bench + boat INS).  
  - **UDP remote** — fixed peer (advanced; blocked at start for Desk/Boat presets).  
  - **TCP server** / **TCP client** — optional under *Advanced* network modes.

- **Desk / Boat presets** — **Connect** tab: pick **Desk test** (com0com + `127.0.0.1`) or **Boat / INS** (`production` block in `bench_defaults.json`). Start validation requires a path and UDP listen.

- **Serial** — COM list, baud, refresh; friendly errors for port-in-use and timeouts.

- **Queues & backpressure** — bounded queues; **drop / reject / queue depth** in the status bar.

- **Live log** — throttled updates; optional **verbose** per-sentence view.

- **Send tab** — inject NMEA (`\r\n` normalized); **Send → serial**, **network**, or **both** while running.

- **NMEA tab** — **Passthrough** or **Strict** (+ sentence-type filter).

- **Diagnostics tab** — optional rotating file log (PC time | GPS UTC | direction | payload); clear on-screen log; quick bench commands.

- **Three UI layouts** — choose at launch (see [Run](#run)).

## Requirements

- **Windows** (primary target).  
- **Python 3.10+**  
- COM drivers as usual for your hardware.

## Install

```powershell
cd nmea-serial-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

### Launcher (pick a UI)

```powershell
.\launch_bridge_gui.bat
```

Or:

```powershell
python launcher.py
```

| UI | Description |
|----|-------------|
| **Standard** | Tabs: Connect, NMEA, Send, Diagnostics + live log panel |
| **Minimal** | Light theme, compact controls, log on top |
| **Log-first** | Dark theme, log dominates; tools in a drawer |

The launcher can **remember** your last choice (`%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json`).

### Direct launch (skip menu)

```powershell
python bridge_gui.py
python bridge_gui.py --ui minimal
python bridge_gui.py --ui logfirst
python bridge_gui.py --ui standard
```

### Typical workflow

1. **Connect** — **Desk test** or **Boat / INS**, confirm COM + UDP port, **Start**. Wait for **Running** in the log.  
2. **NMEA** — Passthrough for first tests; Strict if you need filtering.  
3. **Send** — manual inject (bench: **Send → serial**, watch the **paired** com0com port, not the bridge COM).  
4. **Diagnostics** — optional file log path.  
5. **Stop** when finished.

### Bench (com0com on one PC)

Edit `bench_defaults.json` if needed. Bridge owns e.g. **COM7**; watch the **paired** port (e.g. **COM12**) in Tera Term.

```powershell
python com_free.py
python check_setup.py
python bridge_gui.py
# Start bridge (Desk preset) then:
python nmea_static_edh.py
```

### Boat (INS on Ethernet)

Set `production` in `bench_defaults.json` (COM, `pc_ip`, `ins_ip`, UDP port). Static IP on survey Ethernet recommended.

```powershell
python check_setup.py --production
```

## Verify

```powershell
python verify_all.py
```

Or `.\verify_all.bat` from the project folder (not from `System32`).

Includes: unit tests, `com_free`, `check_setup`, GUI smoke (all three UIs), headless bridge, stress cycles.

## Tests

```powershell
python -m unittest discover -s . -p "test_*.py" -v
```

## Build & release (Windows `.exe` for another PC)

**One command** — build, zip, optional GitHub publish:

```powershell
.\release.ps1              # creates dist\nmea-serial-bridge-v0.5.2-win64.zip
.\release.ps1 -Publish     # also tags v0.5.2 and uploads to GitHub Releases (needs `gh` CLI)
.\release.ps1 -SkipTests   # faster rebuild while iterating
```

**Manual steps:**

```powershell
.\build.ps1
cd dist
Compress-Archive -Path nmea-serial-bridge -DestinationPath nmea-serial-bridge-v0.5.2-win64.zip
```

Then [create a release](https://github.com/Bunbob41/nmea-serial-bridge/releases/new): tag `v0.5.2`, attach the zip.

**On the other PC:** download the zip from **Releases** (not “Source code”), unzip, run `nmea-serial-bridge.exe`. First run shows a **layout picker**; copy the whole folder (not just the `.exe`). Windows SmartScreen may warn on unsigned apps.

## Project layout

| Path | Role |
|------|------|
| `bridge_core.py` | Async bridge engine + worker thread |
| `bridge_gui.py` | GUI entry (`--ui`) |
| `launcher.py` | Interactive UI picker |
| `ui/` | Standard, minimal, log-first layouts + shared logic |
| `bridge_headless.py` | UDP→COM test without GUI |
| `bench_defaults.json` | Desk + `production` presets |
| `check_setup.py` | Pre-flight (`--production` for boat) |

## Notes

- **Virtual COM** (com0com): confirm which two ports are **paired**; do not open Tera Term on the same COM the bridge uses.  
- For UDP bench tests, the **bridge listens**; simulators must **send to** `127.0.0.1:10110`, not listen on that port.  
- Forwards **bytes** only — not a substitute for autopilot failsafes, level shifting, or mission QA.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

## Disclaimer

Use at your own risk on operational hardware. Validate on a bench before depending on it for navigation or survey positioning.
