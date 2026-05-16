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
- **Survey / Hypack workflow** — **View → Full screen** (F11) for large displays; **View → Pop out survey stats** (Ctrl+Shift+S) for a second monitor with large Hz / transport / session totals (Hypack on one screen, bridge on another). MAVLink / Mission Planner stays on its own COM; this app is the NMEA ↔ bridge path.

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

**Desktop shortcut:** run `.\create_desktop_shortcut.bat` from the repo folder. It writes **NMEA Serial Bridge.lnk** (points at `launch_bridge_gui.bat`, silent `pythonw` + layout picker / saved UI) and **NMEA Serial Bridge (console menu).lnk** (numbered menu in a console). After **moving or renaming the project folder**, run it again so **Start in** and targets stay correct.

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

Includes: unit tests, `check_setup`, GUI smoke (all three UIs), and bench steps (`com_free`, headless bridge, stress). If the bench UDP port is already bound (bridge **Running**), exclusive COM/UDP steps are skipped unless you set `VERIFY_ALL_NO_SKIP=1`.

## Tests

```powershell
python -m unittest discover -s . -p "test_*.py" -v
```

## Install on many PCs (frozen build)

Same build on every machine: use **GitHub Releases** (or copy the zip on a USB stick).

1. On each PC: open the repo **Releases** page, download **`nmea-serial-bridge-v<version>-win64.zip`** (the asset, not “Source code”).
2. Unzip anywhere you like; keep the whole **`nmea-serial-bridge`** folder.
3. Run **`nmea-serial-bridge.exe`**. First launch: **layout picker** (Standard / Minimal / Log-first). Optional: put `bench_defaults.json` next to the exe for Desk/Boat presets.
4. Windows **SmartScreen** may warn (unsigned app) — “More info” → run anyway if you trust the build.

Repeat whenever you publish a newer **v…** zip; no Python install required on those PCs.

## Build & release (authoring the zip)

**One command** — build, zip, optional GitHub publish (version comes from `version.py`; zip name matches):

```powershell
.\release.ps1                 # dist\nmea-serial-bridge-v<version>-win64.zip
.\release.ps1 -Publish        # + git tag v<version> + gh release (needs GitHub CLI + `gh auth login`)
.\release.ps1 -PublishOnly   # upload existing zip only (no PyInstaller rebuild — e.g. after login failed mid-publish)
.\release.ps1 -SkipTests      # faster rebuild while iterating (skips unittest in build.ps1)
```

**Manual steps:**

```powershell
.\build.ps1
cd dist
Compress-Archive -Path nmea-serial-bridge -DestinationPath nmea-serial-bridge-v<version>-win64.zip
```

Then [create a release](https://github.com/Bunbob41/nmea-serial-bridge/releases/new): tag **`v<version>`** (same string as `version.py`), attach the zip.

**Cadence (personal / small fleet):** bump `version.py` when you want a new drop → commit → `.\release.ps1` → `gh auth login` once per machine → `.\release.ps1 -Publish` (or `-PublishOnly` if the zip is already built). Human-readable notes live in **`CHANGELOG.md`**.

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
