# Getting started — NMEA Serial Bridge

**Audience:** first-time operators and survey leads onboarding a new PC.  
**Version:** read the window title (`Network ↔ COM Bridge v…`) or `version.py`.  
**Full manual:** [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) · **NORBIT DCT:** [NORBIT_DCT.md](NORBIT_DCT.md)

---

## What this app does (30 seconds)

The bridge moves bytes between **Ethernet (UDP or TCP)** and a **Windows COM port**. Typical survey path:

**INS / GNSS on the LAN → UDP to this PC → bridge → COM → downstream device** (DCT, sonar, display, com0com bench pair).

It does **not** replace Applanix positioning, NORBIT acquisition, or Hypack — it only forwards the stream you configure.

---

## Install (pick one path)

### A — Release zip (recommended for field PCs)

| Step | Action |
| ---- | ------ |
| 1 | Download `nmea-serial-bridge-v<version>-win64.zip` from GitHub Releases. |
| 2 | Unzip the **entire folder** (do not run only the `.exe` without its `_internal` tree). |
| 3 | Double-click `nmea-serial-bridge.exe`. |
| 4 | If Windows SmartScreen warns: **More info** → **Run anyway** (unsigned build until code signing). |
| 5 | **Layout picker** appears once → choose **Standard** (best for first setup). |

Optional: copy `bench_defaults.json` beside the `.exe` so Desk/Boat/NORBIT presets ship with the build.

### B — Developer / repo folder

```powershell
cd C:\path\to\udp-com-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\launch_bridge_gui.bat
# or: python launcher.py
```

Pick **1. Standard** in the launcher.

### C — Desktop shortcut

From the repo folder (after install):

```powershell
.\create_desktop_shortcut.bat
```

Re-run if you move the project directory.

### Saved settings location

| File | Purpose |
| ---- | ------- |
| `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json` | Last UI layout (Standard / Field) |
| `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json` | Named COM + UDP/TCP presets |
| `%USERPROFILE%\.cursor-udp-com-bridge\ui_prefs.json` | Tabs, Connect panel order, web API, diagnostics cards |

---

## First 15 minutes — bench walkthrough (Standard layout)

Goal: prove UDP → COM on your desk with com0com or a USB serial adapter.

| # | Where | Do this | You should see |
| - | ----- | ------- | ---------------- |
| 1 | **Connect** tab | Load preset **Desk test** (survey bar **Presets** or **Tools → Presets → Load**) | COM, baud, UDP port filled; intent hint mentions `127.0.0.1` |
| 2 | **Connect → Serial & network** | Confirm **COM** is the bridge leg (e.g. COM7), not the paired monitor port | Connection hub or manual fields show your ports |
| 3 | **Connect → Run bridge** | Click **Start bridge** | Banner **Running**; log lines for UDP listen + serial open |
| 4 | External | Open Tera Term (or similar) on the **paired** com0com port (e.g. COM12) | Do **not** open the bridge COM in another app |
| 5 | **Tools → Diagnostics** | Expand **Automated checks** → **UDP sample burst (2.5 s)** | Log + Tera Term show NMEA; status bar Hz > 0 |
| 6 | **Log** tab | Skim traffic; try log preset **Survey ops** | Readable sentences, not flood |
| 7 | **Tools → NMEA** | Leave **Passthrough** for Trimble-style NMEA | Strict only when you need QA |
| 8 | **Connect** | **Stop bridge** | COM released; banner **Stopped** |

**Stuck?** **Tools → Diagnostics → Bench checklist** or survey bar **Checklists → Bench checklist**.

---

## Main window map (Standard, current)

```
Survey bar: View · Presets · Recent · HUD · UI editor · …
Main tabs:  Connect | Log | Tools
Tools sidebar: Presets | Phone | NMEA | Terminal | Diagnostics | Theme | Guide
Status bar: Serial | Network | NMEA | GNSS | session stats
```

### Connect tab (daily driver)

Collapsible sections (reorder/hide via **UI editor…** on the survey bar or Connect toolbar):

| Section | Purpose |
| ------- | ------- |
| **Run bridge** | Start / Stop |
| **Serial & network** | Connection hub, COM, baud, UDP listen, discovery, unlock |
| **Status hint** | One-line preset / workflow guidance |
| **Quick log** | Small live log on Connect (optional) |
| **Quick terminal** | Bench script output (optional) |

**Tip:** Put **Serial & network** directly under **Run** (default since v1.9.27). Use **UI editor…** on the Connect toolbar to reorder or hide optional sections.

### Tools → Diagnostics

| Card | When to use |
| ---- | ----------- |
| **Automated checks** | `verify_all`, bench/boat checklist, UDP burst, TCP demos, capacity probe |
| **Rotating file log** | Optional survey archive on disk while Running |
| **On-screen log** | Clear the main **Log** tab panel |
| **Traffic & data quality** | Legend for status-bar Hz / transport / GNSS (not live data) |

Use **Reorder cards…** to stack cards your way; drag splitter lines between cards for height.

### Tools → Phone

Web API, Tailscale/LAN URL, API token, QR code, and setup link for the operator dashboard (`http://<PC>:8765/`).

### Tools → Guide

UDP/TCP connection workflows and links to **GETTING_STARTED.md** / **OPERATOR_GUIDE.md** (no web controls here).

### Optional — phone / second monitor dashboard

1. **Tools → Phone** → enable **Web API** (port **8765**) and **Allow LAN / Tailscale** — a floating setup QR appears on **Connect** (drag to move; right-click to hide; toggle Web API off/on to show again).  
2. For iPhone/Tailscale: **Detect Tailscale IP**, **Generate token**, **Copy phone setup link** (not `127.0.0.1`).  
3. Open the dashboard in the phone browser; Start/Stop and discovery mirror desktop.  
4. Details: `specs/005-hybrid-ui-webui/quickstart.md` and `specs/006-phase-b-dashboard/quickstart.md`.

---

## Field layout (after you know Standard)

Switch via launcher, **Diagnostics → Quick UI switch**, or survey bar layout control.

- Large **Log** and **Start / Stop** strip.  
- COM/UDP row at the bottom; **Tools** drawer holds Presets, NMEA, Terminal, Diagnostics, Theme, Guide.  
- Same bridge engine — only the shell changes.

---

## Boat / production (outline)

1. Static IP on survey Ethernet; INS sends UDP **to** `pc_ip:port` (bridge **listens**).  
2. Load boat-style preset → set real COM/baud → **Save**.  
3. **NMEA → Passthrough** for text NMEA; **Raw binary** only for RTCM/binary.  
4. **Start bridge** → confirm Hz on status bar or **HUD**.  
5. **Stop** when done.  
6. **Checklists → Boat checklist** or Diagnostics → **Boat checklist**.

See [NORBIT_DCT.md](NORBIT_DCT.md) for Applanix + iWBMSe: **40810** on the boat PC; DCT target is **127.0.0.1** (DCT on boat), **192.168.1.8** (DCT on operator laptop / MikroTik wireless), or **VPN StaticIp** (Tailscale/ZeroTier).

---

## Customize the UI (without editing code)

| Goal | How |
| ---- | --- |
| Hide unused Connect sections | **UI editor…** → **Connect** tab → uncheck optional panels → **OK** |
| Move Serial & network up | **UI editor…** → **Connect** → drag **Serial & network** under **Run** → **OK** |
| Reorder survey bar chips | **UI editor…** → **Top bar** |
| Reorder Diagnostics cards | **Tools → Diagnostics → Reorder cards…** |
| Reorder main tabs | **UI editor…** → **Main tabs** |

---

## Next documents

| Doc | Use when |
| --- | -------- |
| [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) | Full bench/boat workflows, troubleshooting, screenshot list |
| [NORBIT_DCT.md](NORBIT_DCT.md) | NORBIT DCT + Applanix + INS UDP → COM |
| [README.md](../README.md) | Features, dev install, verify commands |
| `CHANGELOG.md` | What changed each release |

---

## Quick terminal checks (from repo folder)

```powershell
python check_setup.py
python com_free.py
python verify_all.py
```

Run these with the bridge **Stopped** unless the checklist says otherwise.
