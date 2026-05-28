# Getting started — Serial Link

**For:** survey operators setting up a field or bench PC.  
**Version:** read the window title (`Serial Link v…`).  
**Full manual:** [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) · **NORBIT DCT:** [NORBIT_DCT.md](NORBIT_DCT.md)

> **Developers / repo checkout?** Skip to [Appendix — developers](#appendix--developers) at the bottom.  
> **In the app:** **Tools → Guide** → **Getting started…** / **Operator guide…** opens this manual inside Serial Link (offline, formatted).

---

## What this app does (30 seconds)

The bridge moves bytes between **Ethernet (UDP or TCP)** and a **Windows COM port**. Typical survey path:

**INS / GNSS on the LAN → UDP to this PC → bridge → COM → downstream device** (DCT, sonar, display, or a bench serial pair).

It does **not** replace Applanix positioning, NORBIT acquisition, or Hypack — it only forwards the stream you configure.

---

## Install on a field PC (release zip)

| Step | What to do |
| ---- | ---------- |
| 1 | Download the latest **`serial-link-v…-win64.zip`** from GitHub Releases. |
| 2 | Unzip the **whole folder** to a permanent place (e.g. `C:\Tools\serial-link\`). Keep **everything** in that folder together. |
| 3 | Double-click **`serial-link.exe`**. |
| 4 | If Windows SmartScreen appears: **More info** → **Run anyway**. (See [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) if the app is blocked.) |
| 5 | **Layout picker** (first run only) → choose **Standard** for first-time setup. |

**Your settings** (presets, layout, phone dashboard options) are saved automatically for your Windows user — you do not edit files by hand for normal use.

Optional: copy `bench_defaults.local.json.example` to `bench_defaults.local.json` **beside** `serial-link.exe` only if your team ships a site-specific default COM/UDP (see Appendix).

---

## First 15 minutes — bench walkthrough (Standard layout)

Goal: prove UDP → COM on your desk with com0com or a USB serial adapter.

| # | Where | Do this | You should see |
| - | ----- | ------- | ---------------- |
| 1 | **Connect** tab | Load preset **Desk test** (survey bar **Presets** or **Tools → Presets → Load**) | COM, baud, UDP port filled; hint mentions `127.0.0.1` |
| 2 | **Connect → Serial & network** | Confirm **COM** is the bridge leg (e.g. COM7), not the paired monitor port | Your ports shown in the connection hub |
| 3 | **Connect → Run bridge** | Click **Start bridge** | Banner **Running**; log lines for UDP listen + serial open |
| 4 | External | Open Tera Term (or similar) on the **paired** com0com port (e.g. COM12) | Do **not** open the bridge COM in another app |
| 5 | **Tools → Diagnostics** | **Automated checks** → **UDP sample burst (2.5 s)** | Log + Tera Term show NMEA; status bar Hz > 0 |
| 6 | **Log** tab | Skim traffic; try log preset **Survey ops** | Readable sentences, not a flood |
| 7 | **Tools → NMEA** | Leave **Passthrough** for Trimble-style NMEA | Use **Strict** only when you need QA |
| 8 | **Connect** | **Stop bridge** | COM released; banner **Stopped** |

**Stuck?** **Tools → Diagnostics → Bench checklist** or survey bar **Checklists → Bench checklist**.

---

## Main window map (Standard)

```
Survey bar: View · Presets · Recent · HUD · UI editor · …
Main tabs:  Connect | Log | Tools
Tools sidebar: Presets | Phone | NMEA | Terminal | Diagnostics | Theme | Guide
Status bar: Serial | Network | NMEA | GNSS | session stats
```

### Connect tab (daily driver)

| Section | Purpose |
| ------- | ------- |
| **Run bridge** | Start / Stop |
| **Serial & network** | COM, baud, UDP listen, discovery, unlock |
| **Status hint** | Preset / workflow guidance |
| **Quick log** | Small live log on Connect (optional) |
| **Quick terminal** | Bench output (optional) |

Reorder or hide sections: survey bar **UI editor…** → **Connect** tab.

### Tools → Diagnostics

| Card | When to use |
| ---- | ----------- |
| **Automated checks** | Bench/boat checklist, UDP burst, network demos |
| **Rotating file log** | Optional survey archive on disk while Running |
| **On-screen log** | Clear the main **Log** tab |
| **Traffic & data quality** | Explains status-bar Hz / GNSS (not live data) |

Use **Reorder cards…** to stack cards your way.

### Tools → Phone

Web dashboard on this PC (`http://127.0.0.1:8765/` on the bridge PC). Enable **Web API**, then **Copy phone setup link** for Tailscale/LAN phones (not `127.0.0.1` on the phone). Start/Stop and COM discovery mirror the desktop.

### Tools → Guide

**Start here**, UDP, TCP, and checklist tabs — same wording as **Connect**. Use these tabs on a phone or second monitor instead of opening markdown files in a browser.

---

## Field layout (after you know Standard)

Switch via the launcher, **Diagnostics → Quick UI switch**, or the survey bar layout control.

- Large **Log** and **Start / Stop** strip.  
- COM/UDP at the bottom; **Tools** drawer for Presets, NMEA, Terminal, Diagnostics, Theme, Guide.  
- Same bridge — only the shell changes.

---

## Boat / production (outline)

1. Static IP on survey Ethernet; INS sends UDP **to** `pc_ip:port` (bridge **listens**).  
2. Load boat-style preset → set real COM/baud → **Save**.  
3. **NMEA → Passthrough** for text NMEA; **Raw binary** only for RTCM/binary.  
4. **Start bridge** → confirm Hz on the status bar or **HUD**.  
5. **Stop** when done.  
6. **Checklists → Boat checklist** or Diagnostics → **Boat checklist**.

See [NORBIT_DCT.md](NORBIT_DCT.md) for Applanix + iWBMSe UDP ports and DCT targets.

**Network reliability (firewall, fan-out, TCP):** [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) section **6.4 Network reliability checklist**.

---

## Customize the UI (no code)

| Goal | How |
| ---- | --- |
| Hide unused Connect sections | **UI editor…** → **Connect** → uncheck optional panels → **OK** |
| Move Serial & network up | **UI editor…** → **Connect** → drag **Serial & network** under **Run** → **OK** |
| Reorder survey bar chips | **UI editor…** → **Top bar** |
| Reorder Diagnostics cards | **Tools → Diagnostics → Reorder cards…** |
| Reorder main tabs | **UI editor…** → **Main tabs** |

---

## Next documents

| Doc | Use when |
| --- | -------- |
| [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) | Full bench/boat workflows, troubleshooting |
| [NORBIT_DCT.md](NORBIT_DCT.md) | NORBIT DCT + Applanix + INS UDP → COM |
| [README.md](../README.md) | Features, building from source, tests |
| `CHANGELOG.md` | What changed each release |

---

## Appendix — developers

### Saved settings (JSON paths)

Support / migration only — operators do not need these paths for daily use.

| File | Purpose |
| ---- | ------- |
| `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json` | Last UI layout (Standard / Field) |
| `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json` | Named COM + UDP/TCP presets |
| `%USERPROFILE%\.cursor-udp-com-bridge\ui_prefs.json` | Tabs, Connect panel order, web API, diagnostics cards |

### Run from the git repo

```powershell
cd C:\path\to\udp-com-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\launch_bridge_gui.bat
# or: python launcher.py
```

Pick **1. Standard** in the launcher.

### Desktop shortcut (repo / dev tree)

```powershell
.\create_desktop_shortcut.bat
```

Re-run if you move the project directory.

### Terminal checks (repo folder, bridge stopped)

```powershell
python check_setup.py
python com_free.py
python verify_all.py
```

### Web UI specs (contributors)

- `specs/005-hybrid-ui-webui/quickstart.md`
- `specs/006-phase-b-dashboard/quickstart.md`
