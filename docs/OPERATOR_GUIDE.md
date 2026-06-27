# Serial Link — Operator Guide

Step-by-step guide for survey / bench use. Screenshots are optional; a **shot list** at the end lists exactly what to capture if you want illustrated docs.

**New to the app?** Start with **[GETTING_STARTED.md](GETTING_STARTED.md)** (install + 15-minute bench walkthrough).  
**Doc index:** [docs/README.md](README.md).

**Display comfort:** default theme is **Field Slate** (neutral gray, high-contrast text). Gold is used for accents and primary actions only, not for paragraph text on bright panels. Change theme via **View → Theme** if you prefer Maroon & Gold or others.

**What this app does:** forwards data between **UDP (or advanced TCP)** and a **COM port**. Default path is **NMEA 0183 text** (professional GPS unit, simulators, Hypack). Optional **Raw binary** mode forwards **RTCM**, **MAVLink**, and other non-NMEA bytes without parsing.

Typical use: INS or GNSS on Ethernet → bridge → designated device COM input.

**Cube / MAVLink / Mission Planner:** expose an autopilot COM port to ground-station software over the network — see **§5.6** and **§6.5** (multi-consumer survey stack).

**NORBIT DCT + GUI:** multibeam positioning over serial is the same pattern — see **[NORBIT_DCT.md](NORBIT_DCT.md)** and preset **NORBIT DCT** in the app.

**NTRIP:** not shown in the Connect UI (Applanix/internal RTK workflows). Legacy prefs keep corrections off.

**Baseline reference**: Spec Kit as-built spec and traceability live under
[`specs/001-baseline-spec/`](../specs/001-baseline-spec/) (fan-out FR-011–FR-013, FR-020).

---

## 1. Before you start


| You need                         | Notes                                                            |
| -------------------------------- | ---------------------------------------------------------------- |
| Windows PC                       | Primary target                                                   |
| COM port for the bridge          | Physical USB, or com0com pair on bench                           |
| UDP source (bench) or INS (boat) | Bridge **listens**; others **send to** the PC                    |
| This app installed               | Python dev tree **or** release zip with `serial-link.exe` |


**Do not** open Tera Term or another app on the **same** COM the bridge uses.

---

## 2. Install and first launch

### Option A — Release zip (field PCs, no Python)

1. Download `nmea-serial-bridge-v<version>-win64.zip` from GitHub Releases.
2. Unzip the whole folder; run `nmea-serial-bridge.exe`.
3. If SmartScreen warns: **More info** → **Run anyway** (unsigned build).
4. **Layout picker** appears once: choose **Standard** (recommended for first-time users).

### Option B — Developer / repo folder

```powershell
cd C:\path\to\udp-com-bridge
.\launch_bridge_gui.bat
```

Or `python launcher.py` and pick **1. Standard**.

The app remembers your layout under:

`%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json`

---

## 3. Pick a UI layout (one-time)


| Layout       | Best for                                                                 |
| ------------ | ------------------------------------------------------------------------ |
| **Standard** | **Connect** + **Log** + **Tools** (Presets, Phone, NMEA, Terminal, Diagnostics, Theme, Guide) |
| **Field**    | Large log, Start/Stop strip, COM/UDP row, Tools drawer, survey quick bar |


Older names **Minimal** / **Log-first** map to **Field** in the launcher (or still launch legacy layouts via CLI).

**Recommendation:** **Standard** for first setup and editing presets; **Field** for daily survey ops and presentations.

### Modern UI (default in recent builds)

The **Modern** layout uses a top **Control** tab with a page banner, **Serial link** and **Network path** cards side-by-side, a green **preset summary** strip when a named preset is loaded, and a collapsible **Position track**. Before **Start**, load a setup from **Presets** or pick a tile on **Hub** — the summary strip on Control confirms what is active.

**Tools navigation:** **View → Tools navigation → Sidebar** (left list) or **Top chips** (horizontal tabs). Same sections either way; pick whichever fits your monitor width.

---

## 4. Main window map

### Standard layout (current)

```
┌─ Survey bar: View · Presets · Recent · HUD · UI editor · … ─────────────┐
├─ Main tabs: Connect | Log | Tools ─────────────────────────────────────┤
│  Connect: Run, Serial & network (hub), hint, optional quick log/term   │
│  Tools sidebar: Presets | Phone | NMEA | Terminal | Diagnostics | Theme | Guide│
├─ Status bar: Serial | Network | NMEA | GNSS | Hz / session stats ──────┤
└────────────────────────────────────────────────────────────────────────┘
```

On launch, connection fields load your **last-used named preset** (or the first bench-style preset from `bench_defaults.json`). You can **Start** within about a minute without opening Tools first.

**Tray monitoring:** After **Start bridge**, closing the window (X) **minimizes to the system tray** and leaves the bridge running. Double-click the tray icon to reopen, or use the tray menu **Stop bridge** / **Exit**. Hover the tray icon for Serial | Network status. Theme and layout chrome are fixed for speed — personalization lives under **Tools → Theme** only if you need bench colors.

**Recent sessions** (survey bar): last five COM + UDP + **NMEA mode** combos. Pick one while the bridge is **stopped**; if running, stop first then apply.

**Customize Connect:** survey bar or Connect toolbar **UI editor…** → drag sections (Run and Serial & network always stay on). Default order puts **Serial & network** directly under **Run** to reduce scrolling.

**Tools sidebar (Standard):** same **UI editor…** → **Tools tabs** page — reorder or hide Presets, Phone, NMEA, Terminal, Diagnostics, Inject, Theme, and Guide in the left list on the **Tools** main tab. At least one item must stay visible. Field layout uses the same page for drawer tabs instead of the sidebar.

**Connect layout:** use **UI editor…** on the Connect toolbar to show/hide and reorder sections. Panel heights follow the disclosure layout (no splitter **Reset sizes** control).

### Field layout

```
┌─ Survey bar (same quick actions as Standard) ──────────────────────────┐
├─ Start bridge | Stop bridge ─────────────────────────────────────────┤
├─ Live log (most of the window) ──────────────────────────────────────┤
├─ COM / Baud / UDP row · status · one-line intent hint · Tools ▾ ─────┤
│  Tools drawer: Presets | NMEA | Terminal | Diagnostics | Theme | Guide│
├─ Status bar ─────────────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────────────────────┘
```

**TCP / advanced UDP:** Field does not duplicate Advanced on the connect row — open **Tools → Presets** (advanced network section when shown).

---

## 5. Desk / bench workflow (one PC, com0com or simulator)

Use this when testing on your desk: virtual COM pair and UDP from `127.0.0.1`.

### 5.1 One-time setup

1. Install **com0com** (or know your real COM names).
2. In com0com Setup, note the **paired** ports (e.g. bridge = COM7, Tera Term = COM12).
3. Optional: edit `bench_defaults.json` in the app folder for default COM/port.

### 5.2 Each session


| Step | Action                                                   | Success check                                                      |
| ---- | -------------------------------------------------------- | ------------------------------------------------------------------ |
| 1    | Open the app (Standard layout)                           | Window title: `Serial Link v…`                            |
| 2    | **Presets** tab or survey bar **Presets** → load bench preset | COM, baud, UDP fill in; intent hint mentions 127.0.0.1      |
| 3    | Confirm **COM** = bridge port (not the paired echo port) |                                                                    |
| 4    | Confirm **Listen port** (e.g. 10110) on **Connect**    | **UDP listen** (Advanced off unless you know why)                  |
| 4b   | **Fan-out** checkbox (Connect → Run area)              | **Checked** = all UDP senders get serial→net (default); off = last sender only |
| 4c   | **Extra TCP output** (optional, port e.g. 10111)       | Off by default; when on, tools connect to this PC as TCP **clients** for a copy of COM→net |
| 5    | Click **Start bridge** on **Connect**                  | Banner → **Running**; log shows UDP listen + serial open           |
| 6    | Open Tera Term on the **paired** COM (not bridge COM)    | Bridge owns one leg; monitor the **paired** port only              |
| 7    | Send UDP NMEA to the bridge                              | Diagnostics → **UDP sample burst**, or `python nmea_static_sample.py` |
| 8    | Watch log + Tera Term                                    | Lines on serial; stats Hz > 0 in status bar                        |
| 9    | **Stop bridge** when done                                | Banner **Stopped**; COM released                                   |


### 5.3 Save your bench settings

After COM/baud/UDP are correct:

1. **Presets** tab → select a preset → **Save** (or **Save as…** for a new name).
2. Settings stored in `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json` (includes **fan-out** on/off per preset).
3. Next launch loads the last-used preset automatically.

### 5.4 Pre-flight checks (optional)

**Survey bar → Checklists**, or **Diagnostics** tab:


| Button               | Purpose                                                                  |
| -------------------- | ------------------------------------------------------------------------ |
| **Bench checklist**  | UDP port free/in use, COM list, send test (first bench-style preset)     |
| **UDP sample burst** | 2.5 s test traffic to bench UDP target (bridge must be **Running**)      |


Or from a terminal in the project folder:

```powershell
python check_setup.py
python com_free.py
```

### 5.5 Test UDP fan-out (one bridge, two UDP clients)

You do **not** need a second bridge app. Use **one** Running bridge and two UDP clients that both send at least one datagram to the listen port (this registers each peer).

| Step | Action | Check |
| ---- | ------ | ----- |
| 1 | Start bridge with **Fan-out** checked | Status can show `peer …` then `2 peers` after second sender |
| 2 | Terminal A: `python bench_udp_test.py --seconds 2` | Registers peer A; sends NMEA |
| 3 | Terminal B: `python bench_fanout_probe.py --seconds 20` | Registers peer B; listens for replies |
| 4 | Generate COM→net traffic | com0com echo on paired port, or live serial into bridge COM |
| 5 | Observe B (and A if still listening) | Both receive serial-originated UDP within a few seconds |
| 6 | Stop → Start with **Fan-out** unchecked | Repeat steps 2–5; only the **last** sender receives serial→net |
| 7 | **Automated** | `python bench_fanout_automation.py` — headless when UDP port free (both peers + last-peer-only); live registers two peers when the bridge is already Running. Also **Diagnostics → Fan-out bench (auto)** and `verify_all.py`. |

See also [`specs/001-baseline-spec/quickstart.md`](../specs/001-baseline-spec/quickstart.md).

### 5.6 Cube Orange / MAVLink + Mission Planner (UDP Client)

Use this when a **Cube** (or other ArduPilot autopilot) is on USB serial and you want **Mission Planner**, **QGroundControl**, or another MAVLink GCS on the **same PC or LAN** — with **full COM-level access** (parameters, missions, calibration) through the bridge.

Serial Link is a **transparent byte pipe** in **Raw binary** mode: MAVLink frames pass unchanged in both directions.

#### Roles (who listens vs who connects)

| Program | Role | Port |
| ------- | ---- | ---- |
| **Serial Link** | **UDP listen** on this PC (owns the COM port) | e.g. **14550** |
| **Mission Planner** | **UDP Client** → sends to Serial Link | Remote **127.0.0.1:14550** (do **not** bind 14550 locally) |
| **Cube** | USB serial telemetry | COMx @ **115200** (match `SERIAL0_BAUD` / TELEM port) |

Only **one** program may **listen** on a given UDP port. If both Serial Link and Mission Planner try to bind **14550**, one of them fails with *address already in use*.

#### One-time setup

1. Identify the **MAVLink COM port** in Device Manager (Cube USB often exposes **multiple** COM ports — pick the one that streams telemetry when the autopilot is powered; not the bootloader/SLCAN port unless you intend that).
2. In Serial Link **Control**: **COM**, **115200**, **NMEA → Raw binary**, **Listen port 14550**, **Fan-out** on (recommended if you may add a logger or second GCS later).
3. **Tools → Presets → Save as…** → e.g. `Cube MAVLink` (stored in `path_presets.json`). Edit **COM** to match Device Manager (your Cube UART — often not the default COM9).

Shipped built-in **Cube MAVLink** is a starting point — click **Load** (single-click in the list only fills survey notes, not COM/baud).

#### Each session (order matters)

| Step | Action | Success check |
| ---- | ------ | --------------- |
| 1 | Quit Mission Planner (or any app using **14550**) | `Get-NetUDPEndpoint -LocalPort 14550` shows nothing, or only Serial Link after Start |
| 2 | Serial Link → load **Cube MAVLink** preset → **Start** | Banner **Running**; log `UDP listen on ('0.0.0.0', 14550)` + serial open |
| 3 | **Activity** tab | **COM→NET [RAW …]** with `fd` bytes (MAVLink) when Cube is powered |
| 4 | Mission Planner → **right-click Connect** → **UDP Client** (`udpcl://…`) | Remote host **127.0.0.1**, remote port **14550** |
| 5 | Connect | HUD shows voltage, GPS, modes; parameters download without *disposed object* errors |
| 6 | **Do not** open the same COM in MP | Serial Link owns COM — MP uses **network only** |

**Do not** use the top-right plain **UDP** button in Mission Planner for this workflow — that **listens** on 14550 and conflicts with Serial Link. Use **UDP Client** only.

#### TCP note (Mission Planner)

Some MP builds also offer **TCP** to the bridge. Serial Link **Advanced → TCP server** can mirror the COM stream, but **UDP Client to the listen port** is the tested path for full bidirectional MAVLink. TCP may show telemetry without completing parameter download if the client mode is receive-only — prefer **UDP Client** for full GCS access.

#### Troubleshooting (MAVLink)

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| UDP *already in use* on Start | Mission Planner (or another tool) bound **14550** | Quit MP; Start Serial Link first |
| MP *already in use* / bind error | Serial Link already on **14550**; MP used plain **UDP** | Use **UDP Client** to `127.0.0.1:14550` |
| MP *Cannot access disposed object* | Link dropped during parameter fetch (no stable MAVLink) | Fix COM/baud/Raw mode; confirm **COM→NET** in Activity before connecting MP |
| Activity shows **NET→COM** only | Cube not replying on serial | Wrong COM, wrong baud, or autopilot not powered |
| Activity shows **COM→NET** only | MP not registered as UDP peer | Connect MP **after** Serial Link is Running; use UDP Client |
| Garbled / no lock in MP | NMEA Passthrough or Strict on binary MAVLink | **NMEA → Raw binary** |

#### What you get

With a stable link you have **the same class of access as a direct USB cable** to the autopilot: parameters, firmware tools, mission upload, sensors — because the bridge does not interpret MAVLink, it only moves bytes between COM and UDP.

---

## 6. Boat / field workflow (INS on Ethernet → device COM)

Use when the INS sends NMEA UDP to the survey PC and the bridge drives the target serial input.

### 6.1 One-time / per-vessel setup

1. Set survey PC Ethernet static IP (your `pc_ip` — placeholder in defaults is `192.168.1.10`).
2. Configure INS to **send** NMEA UDP to `pc_ip:udp_port` (not “listen” on that port).
3. Note target device COM name in Device Manager (placeholder default: COM3).

### 6.2 Each session


| Step | Action                                           | Success check                                       |
| ---- | ------------------------------------------------ | --------------------------------------------------- |
| 1    | **Presets** → load boat-style preset             | COM + UDP filled; optional LAN notes in preset      |
| 2    | Adjust COM/baud/UDP if this PC differs           |                                                     |
| 3    | **Save** after first good config on this PC      | Updates `path_presets.json`                         |
| 4    | **Auto-reconnect COM** (default on)              | Connect tab (Standard) or Presets → Advanced (Field)  |
| 5    | **NMEA** → **Passthrough** for professional GPS unit NMEA | Use **Raw** only for binary RTCM / other (rare)     |
| 6    | **Start bridge**                                 | Running; bridge COM is dedicated                     |
| 7    | Confirm INS stream                               | Log shows UDP traffic; Hz in status bar / HUD         |
| 7b   | Multiple UDP consumers (rare)                    | Leave **Fan-out** on so each sender that contacted the bridge receives serial→net |
| 8    | Verify data at downstream device/app             | Not laptop COM GPS                                  |
| 9    | **Stop bridge** when done                        |                                                     |


**Checklists → Boat checklist** or **Diagnostics → Boat checklist** runs `check_setup --production` with your first boat-style preset.

### 6.3 Network links (MikroTik, Tailscale, LAN)

| Environment | What to verify |
| ----------- | -------------- |
| **MikroTik PTP / survey LAN** | INS configured to **send** UDP to survey PC IP:port. Bridge **listens** on that port. No NAT in the middle for UDP unicast. |
| **Tailscale (R&D)** | Sender must use this PC’s **Tailscale IP** and the same UDP port. Allow UDP in Windows firewall. Expect slightly higher jitter — watch Survey HUD **Into COM** Hz. |
| **TCP to bridge** | Use Advanced → **TCP server**; clients connect to PC IP:4001 (or your port). External TCP demo/stress tools must **read** TCP replies on long runs so queues do not fill. |

The bridge does not configure routers or VPN — only opens sockets on the Windows machine.

### 6.4 Network reliability checklist (P0)

Use this when traffic is flaky, Hz drops, or the status bar / HUD shows **transport** warnings (drops, rejects, queue backlog).

| Check | What to verify |
| ----- | ---------------- |
| **INS → PC direction** | The INS must **send** UDP to this PC’s IP and the **same listen port** the bridge shows on **Connect**. The bridge **listens**; it does not dial the INS. |
| **Listen host** | `0.0.0.0` accepts datagrams on all interfaces; a specific IP binds only that address. Mismatch = no packets. |
| **Windows firewall** | Allow **inbound UDP** on your listen port (and TCP if you use Advanced TCP server/client). |
| **Fan-out** | **On (default):** every UDP peer that has sent to this session gets **COM→UDP** replies. **Off:** only the **most recent** sender receives serial→net — fine for one simulator; wrong if you expect multiple listeners. |
| **Extra TCP output** | Optional second listener for **COM→network** bytes only; unrelated to fan-out. Turn off if nothing is connected (avoids idle TCP queue pressure). |
| **TCP client (Advanced)** | Bridge reconnects automatically; tune **reconnect delay** on Connect if the peer is slow to come up. If a consumer never reads TCP replies, queues can fill — keep the client reading or stop the bridge. |
| **Tailscale / VPN** | Sender must target this PC’s **VPN IP**, not only LAN. Expect extra jitter; use Survey HUD **Into COM** Hz as a sanity check. |
| **When things go wrong** | Status bar **session stats** turn red on drops/rejects/backlog; Survey HUD **Transport** tile shows Warn/OK. **Stop** → fix bind/port/firewall → **Start** again. |
| **Automated bench** | `python bench_network_automation.py` — **headless** when the bench UDP port is free (zero net→serial drops + TCP reconnect on :41099); **live** burst when the bridge is already listening. Fan-out: `python bench_fanout_automation.py`. **Diagnostics → Network bench (auto)** / **Fan-out bench (auto)**; `verify_all.py`. |

For in-app wording aligned with Connect, use **Connect → ?** (network guide popout) and **Tools → Guide**.

### 6.5 Survey stack: Hypack, sonar, autopilot, mesh (theory)

Serial Link is one **COM ↔ IP** bridge session. It does not replace survey software, autopilot firmware, or mesh radios — it **joins** them. Below is what becomes possible once COM-level MAVLink (§5.6) or NMEA (§6) is on the network.

#### Architecture pattern

```
[ Sensor / autopilot / INS ] ──serial──► [ Serial Link COM ]
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              UDP listen :14550         UDP fan-out peers          Extra TCP :10111
              (Mission Planner          (logger, QGC, custom       (optional mirror
               UDP Client)                script on same PC)         for TCP-only tools)
                    │
                    └── over LAN / Wi‑Fi / Tailscale / mesh VPN IP ──► remote laptop
```

**Fan-out (default on):** every UDP sender that has contacted the bridge this session receives **COM→network** copies. **NET→COM** still merges all inbound UDP into one serial stream (fine for one autopilot; avoid two unrelated senders unless you know they share the link).

#### What this unlocks

| Scenario | How Serial Link fits | Notes |
| -------- | -------------------- | ----- |
| **Mission Planner / QGC on laptop** | Cube on vessel PC COM → bridge → MP **UDP Client** on survey laptop via LAN or **Tailscale** | Target the **survey PC’s IP:14550**, not `127.0.0.1`, from remote machines. Open Windows firewall for inbound UDP on that port. |
| **Hypack / acquisition PC** | INS **NMEA** UDP → bridge → **COM** into Hypack or acquisition card | Classic survey path (§6). Passthrough NMEA; match baud and sentence rate. |
| **Sonar / depth (NMEA)** | SonarMite / SDDPT / ASCII on **secondary COM** (optional) | Enable **Depth sonar on secondary COM** on Control; GNSS on UDP or primary COM. Serial Link **muxes** depth to latest fix for Survey Map + export. |
| **Budget survey stack** | Cheap GNSS + single-beam without Applanix/DCT | See [`docs/BUDGET_SURVEY_STACK.md`](BUDGET_SURVEY_STACK.md): UDP GNSS + COM sonar, Survey Map tab, CSV/KML with depth. |
| **One COM, many listeners** | **Fan-out** + optional **Extra TCP output** | e.g. MP + Python logger + web dashboard tap on same Cube stream without a second USB cable. |
| **Mesh / PTP / MikroTik / Starlink + Tailscale** | Mesh provides **IP reachability**; bridge still **listens** on the survey PC | No special mesh mode — configure senders to the PC’s **mesh/VPN IP** and the same listen port. Watch jitter on HUD **Into COM** Hz. |
| **Bench com0com** | Prove fan-out and MAVLink before the boat | com0com pair + MP UDP Client to localhost (§5.6). |
| **Second serial device** | One GUI instance = **one** bridge session | For a second COM (e.g. GNSS + Cube simultaneously), use a **second PC**, **`bridge_headless.py`**, or run one stream at a time. |

#### Combined field picture (example)

On a **single survey PC** you might run:

1. **Bridge A (NMEA):** Professional GPS / INS UDP → COM → Hypack positioning input.  
2. **Bridge B (MAVLink):** Cube COM → UDP **14550** → Mission Planner for USV autopilot monitoring.

That requires **two COM ports and two bridge processes** (GUI + headless, or two machines). One Serial Link session cannot split two COM devices.

On **one autopilot COM** with fan-out, you can simultaneously:

- Mission Planner (UDP Client) for control/monitoring  
- A custom Python script logging MAVLink  
- Optional TCP mirror for a tool that only speaks TCP  

#### Limits (important)

- **Not a MAVLink router** — no multi-vehicle routing, no command filtering, no mission planner logic.  
- **Not kernel virtual COM** — physical USB or com0com only.  
- **One primary network mode per session** (UDP listen + optional TCP sink mirror).  
- **NET→COM aggregation** — multiple UDP talkers on one bridge can collide on serial; typical ops use **one GCS** or disciplined senders.  
- **Latency** — adds a small hop vs direct USB; fine for monitoring and mission ops; validate if your autopilot loop is timing-critical.

#### Next steps for your fleet

1. Save working **Cube MAVLink** and boat NMEA presets (§5.3).  
2. Document **mesh/VPN IP + port** on the vessel checklist.  
3. Use **Survey HUD** and Activity **COM→NET / NET→COM** to prove each link before leaving the dock.  
4. See **§5.5** for fan-out proof with two UDP clients on the bench.

---

## 7. Tab reference

### Connect (Standard only)

- **Connection hub** — card grid at the top of **Serial & network**: pick a detected GNSS COM port, UDP listen context, or a **LAN-discovered** host (after **Refresh discovery**). Selection fills COM/baud or listen host/port for **Start**. The active card shows **QoS** (Hz / drops) while the bridge is running. Successful starts save **last-known-good** per device.
- **Refresh discovery** — scans the local ARP table and sends short UDP probes on survey ports (10110, 4001, 10111) to find peers; completes in a few seconds. Does not replace your INS configuration — it surfaces likely targets on the LAN.
- **Unlock ports** — tries to release a stuck COM (e.g. PuTTY left open) without restarting the app. Blocked while the bridge is **Running** on that COM; stop the bridge first.
- **Manual override** — expand the checkbox group below the hub for full COM, **Fan-out**, **Extra TCP output**, and **Advanced network** (TCP/UDP remote). When override is on and you edit fields, hub card defaults are ignored until you collapse override or pick a card again.
- **Extra TCP output** — optional TCP server on this PC (default port **10111**). Other programs connect as clients to receive the same **COM→network** bytes as your main UDP path. Independent of **Fan-out**; leave off unless you need a second listener (logger, test tool, etc.).
- **Network guide (?)** — beside **Fan-out** on Standard **Connect** → opens a popout explaining Listen host/port, Fan-out, Extra TCP output, and Advanced network.
- **Bench walkthrough** — see `specs/004-hub-network-discovery/quickstart.md` for resize, refresh, unlock, QoS, and two-sender LAN checks.

### Web control plane (optional, v1.7+)

- **Enable** — Tools → **Phone** → **Enable Web API on this PC** (default port **8765**, localhost only).
- **Open dashboard** — Same tab → **Open dashboard in browser**, or `http://127.0.0.1:8765/` (token query param if configured). **`GET /` opens the customizable grid layout**; classic single-column layout: `http://127.0.0.1:8765/static/index.html`.
- **Operator dashboard (v1.8+)** — Start/stop bridge, unlock COM, discovery refresh, config patch, live log, position map, Survey monitor. Section **⋯** (or long-press on phone) opens layout options: hide header, terminal-only log, prioritize map, Survey monitor **Rows / Columns / Simple**.
- **Grid layout (default at `/`, v1.11+)** — Drag/resize tiles; **Lock layout** freezes positions; **Reset layout** clears saved layout. **Classic layout (backup)** — `http://127.0.0.1:8765/static/index.html` (footer on grid links there too).
- **Endpoints** — `GET /status`, `GET /config`, `PATCH /config`, `POST /bridge/start`, `POST /bridge/stop` (see `specs/005-hybrid-ui-webui/quickstart.md`).
- **LAN access** — Off by default. Enabling **Allow LAN access** binds all interfaces; use Windows firewall and optional `token` in `%USERPROFILE%\.cursor-udp-com-bridge\ui_prefs.json` under `web_ui`.
- **Dev install** — `python -m pip install -r requirements-web.txt` when running from source.
- **Frozen build** — `web/static` ships inside the PyInstaller folder; restart the app after upgrading the zip so the embedded server picks up new assets.
- **Run** — **Start bridge** / **Stop bridge** (always visible at top of tab).
- **Intent hint** — one-line guidance for preset, UDP listen, or TCP mode (full text on hover).
- **COM / Baud / Refresh** — serial toward target device or com0com (under Manual override when hub is shown).
- **Auto-reconnect COM** — while Running, retry opening COM every 2 s after a disconnect.
- **Listen host / port** — UDP listen bind on this PC (default path).
- **Advanced network** — TCP server/client or UDP remote (Standard Connect tab only).
- Field layout: same COM/UDP fields on the bottom strip; TCP lives under **Tools → Presets**.

### Presets

| Control | Action |
| ------- | ------ |
| **List** | Saved named presets on this PC |
| **Load** | Fill COM, UDP, and optional survey LAN notes |
| **Save** | Overwrite selected preset with current connection fields |
| **Save as…** / **New…** | Create a named preset |
| **Delete** | Remove selected preset |
| **Survey network** | Optional PC IP, subnet, INS IP, notes (reference only) |
| **Advanced network** | Shown here in Field/Minimal drawer; on Standard, use **Connect** tab |

### NMEA

| Mode | Use when |
| ---- | -------- |
| **Passthrough** | Professional GPS unit NMEA, simulators, Hypack path (default) |
| **Strict** | You need checksum + sentence-type filter (bench QA) |
| **Raw binary** | Receiver outputs **RTCM** or other binary — bytes forwarded unchanged |

Strict does **not** apply to Raw mode.

### Terminal (Tools → Terminal)

While **Running** (NMEA text modes):

- Type or paste NMEA lines.
- **Insert sample GGA** — generic bench fix (38°N, 122°W, 10 m).
- **Send → serial** / **network** / **both** — manual inject.

Does **not** inject binary streams — NMEA text only.

### Phone (Tools → Phone)

- Enable localhost Web API, LAN/Tailscale bind, API token, **Show QR**, setup link copy/paste, **Detect Tailscale IP**, **Open dashboard in browser**.
- In-tab **API token** blurb explains when the token is required, and **Generate** vs paste-your-own / setup link.

### Guide (Tools → Guide)

- **UDP / TCP Client / TCP Server / Checklist** — short HTML workflows (connection methods).
- Buttons at the top open **GETTING_STARTED.md**, this guide, and **NORBIT_DCT.md** inside Serial Link (offline viewer; same bundled `docs\` files in release zips).

### Diagnostics (Tools → Diagnostics)

Four **collapsible cards** in a vertical stack (default order: **Automated checks** first). Use **Reorder cards…** (top right) to drag cards into your preferred order; **Apply** saves per layout mode. Drag the splitter between cards to set height — sizes persist.

| Card | Purpose |
| ---- | ------- |
| **Automated checks** | Same scripts as the command line: **Bench pair setup…** (opens this guide §5 + runs checks), **Full verify** (`verify_all.py`), **Bench/Boat checklist** (`check_setup.py`), **UDP sample burst**, TCP stress/demo, **capacity probe**, **Stop** / **Clear output**. Mirror checkbox sends lines to the main **Log** tab. |
| **Rotating file log** | Optional `bridge_survey.log` on disk while Running (size/backups). |
| **On-screen log** | **Clear live log panel** — does not delete the rotating file above. |
| **Traffic & data quality** | **Legend only** for status-bar Hz, transport OK/warn, session totals, GNSS chip — expand when you need a reminder; live values stay in the status bar and Survey HUD. |

**Quick UI switch** (when present) jumps between Standard and Field layout.

**Presenter tip:** collapse **Traffic & data quality** and **On-screen log**; keep **Automated checks** expanded for bench demos.

### Survey bar (all layouts)

| Control | Action |
| ------- | ------ |
| **View** | Full screen, Survey HUD, Theme, UI editor |
| **Presets** | Quick-load menu of saved presets |
| **Recent** | Last five COM + network + NMEA sessions |
| **Checklists** | Bench or Boat check_setup (same as Diagnostics) |
| **HUD** | Survey stats popout |
| **Tools** | Toggle Field/Minimal tools drawer |
| **Pause log** / **Clear log** / **Copy stats** | Log control and clipboard export |

### Connection help (Tools → Guide)

Use **Tools → Guide** for in-app UDP/TCP steps that match the Connect tab (Start here, UDP, TCP client/server, checklist). Doc buttons open **GETTING_STARTED.md** and this guide. Phone/Web API setup is on **Tools → Phone**, not Guide.

---

## 8. View menu (survey displays)


| Item                     | Shortcut     | Use                                                            |
| ------------------------ | ------------ | -------------------------------------------------------------- |
| **Full screen**          | F11          | More room for Connect + log on one monitor                     |
| **Pop out survey stats** | Ctrl+Shift+S | Large Hz/transport window for second monitor (Hypack + bridge) |
| **Theme**                | —            | Appearance only                                                |


HUD is for **monitoring** while surveying; it does not replace Connect for start/stop.

---

## 9. Status bar (when Running)

Read left to right:

- **Serial** — COM open, errors, timeouts.
- **Network** — UDP/TCP mode and endpoint.
- **Stats** — rolling Hz, inject rate, session line counts, drops/rejects (hover for detail).

If **drops** or **rejects** climb under load, serial consumer may be slow or filter too strict.

### Transport truth (v1.41+)

Three clocks — do not confuse them:

| Clock | Meaning | Where to look |
| ----- | ------- | ------------- |
| **Running** | Time since **Start** until **Stop** | Activity **Session** pill; web **Running**; Mission Review duration |
| **COM data active** | Time with serial bytes actually moving **COM→network** (gaps >2 s pause the timer) | Activity **Session** tooltip; web **COM data active**; Stop log `[Transport] Session summary`; Mission Review when active ≪ running |
| **UDP peer last seen** | Age of the **newest inbound** datagram from a registered tablet/app (listen mode) | Activity **UDP** pill (click for peer list); Modern header chip **UDP …** suffix; web **UDP peer** |

**Activity strip** (Modern → Activity): **Serial ● …** shows last COM→net byte age; **UDP ● …** shows peer address or count; **Session …** shows Running time with COM-active detail on hover. Amber **⚠** means stale COM data (>60 s) or stale UDP peers (>60 s since inbound).

**After Stop:** the log prints a `[Transport] Session summary` block (Running, COM active, last COM→net byte, line counts, UDP peers).

**Mission Review:** duration label tooltip compares Running vs COM data active; summary text notes when COM was idle for much of the session.

**Web dashboard** (Survey monitor): **Running**, **COM data active**, **Last COM→net**, and **UDP peer** mirror the same fields from `GET /status`.

---

## 10. Troubleshooting


| Symptom                        | Likely cause                            | Fix                                                        |
| ------------------------------ | --------------------------------------- | ---------------------------------------------------------- |
| Start fails: COM in use        | Tera Term, another serial app, old bridge | Close other app; **Stop**; run **Bench checklist**       |
| BT sonar LED flashing, no data | Opened **incoming** COM only; outgoing leg not dialed | See **`docs/BLUETOOTH_SPP_WINDOWS.md`** — may need outgoing “SPP Dev” port to establish link |
| Start fails: UDP in use        | NMEA Simulator “listening” on same port | Quit simulator; bridge must **listen** first               |
| No UDP in log                  | Nothing sending to PC:port              | Point simulator/INS to correct IP:port; **Bench checklist** |
| No serial in Tera Term         | Wrong COM (opened bridge port)          | Use **paired** com0com port                                |
| Strict mode rejects everything | Bad checksums from source               | Switch NMEA to **Passthrough** for test                    |
| Serial: reconnecting…          | COM dropped; auto-reconnect on          | Replug USB; or disable auto-reconnect and **Stop**/**Start** |
| Binary stream garbled on COM   | Used Passthrough on binary stream       | **NMEA → Raw binary**; enable binary output on receiver    |
| MAVLink / MP bind error        | Both MP and Serial Link on **14550**    | Start Serial Link first; MP **UDP Client** → `127.0.0.1:14550` |
| MP *disposed object* on connect | MAVLink link dropped mid-param-fetch   | Confirm Activity **COM→NET**; Raw mode; correct Cube COM |
| TCP Transport Warn on long run | Client not reading TCP replies          | Use stress tool with RX drain or stop client                |
| Checklist shows old port       | Rare if preset not saved                | **Presets → Save** again; rerun checklist                  |


---

## 11. File locations (for support)


| File                                                     | Purpose                      |
| -------------------------------------------------------- | ---------------------------- |
| `%USERPROFILE%\.cursor-udp-com-bridge\path_presets.json` | Named presets (bench, boat, custom) |
| `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json`    | Last UI layout               |
| `bench_defaults.json` (beside exe or repo)               | Neutral shipped Desk / Boat / NORBIT built-ins |
| `bench_defaults.local.json` (optional, not in public zip) | Your LAN/COM overrides; copy from `.example` |
| Optional file log path                                   | Set on Diagnostics tab       |


---

## 12. Screenshot shot list (for your manual)

Capture at **1920×1080** or **1280×720**, PNG, window fully visible. Save under `docs/images/`.  
Use **Field Slate** theme unless noted. Hide unrelated windows; status bar and survey bar fully visible.

### Standard layout (setup & tabs)

| ID  | Filename | What to capture | Setup before capture |
| --- | -------- | --------------- | -------------------- |
| S01 | `01-layout-picker.png` | Launcher layout picker | Delete `%USERPROFILE%\.cursor-udp-com-bridge\ui_choice.json` or first run |
| S02 | `02-standard-stopped.png` | Full window, **Connect** tab, **Stopped** | Fresh launch; intent hint visible |
| S03 | `03-presets-bench.png` | **Tools → Presets**: list + **Load** / **Save** | Select **Desk test** (or your bench preset); fields filled after Load |
| S04 | `04-connect-running.png` | **Connect**: Run box **Running**, **Log** tab with traffic | Load bench preset → **Start** → **UDP sample burst** once |
| S05 | `05-status-bar-hz.png` | Crop status bar (Serial, Network, NMEA, Hz line) | Same session as S04 |
| S06 | `06-nmea-passthrough.png` | **NMEA** tab; **Passthrough** selected; strict grid grayed out | |
| S07 | `07-terminal-tab.png` | **Tools → Terminal** with sample GGA | **Insert sample GGA** |
| S08 | `08-diagnostics-checklist.png` | **Tools → Diagnostics** → **Automated checks** expanded; bench checklist output | **Bench checklist**; show `diag_output` pane |
| S09 | `09-presets-boat-notes.png` | **Tools → Presets**: boat preset selected; **Survey network** fields visible | Load **Boat / INS** (or boat preset) |

### Field layout (daily ops)

| ID  | Filename | What to capture | Setup before capture |
| --- | -------- | --------------- | -------------------- |
| S10 | `10-field-stopped.png` | Field UI: Start/Stop strip, log, COM row, intent hint | Switch layout via Diagnostics or launcher |
| S11 | `11-field-tools-drawer.png` | **Tools ▴** open on **Presets** or **NMEA** | Expand drawer |
| S12 | `12-survey-bar.png` | Survey bar: **Presets**, **Recent**, **Checklists**, **HUD** | Crop top bar if needed |
| S13 | `13-field-running-log.png` | Field **Running**; log preset **survey ops** or **full detail** | Start bridge + short UDP burst |

### HUD & presenter

| ID  | Filename | What to capture | Setup before capture |
| --- | -------- | --------------- | -------------------- |
| S14 | `14-hud-popout.png` | Survey HUD (6 columns, 100% scale) | **View → Survey HUD** or survey bar **HUD** |
| S15 | (optional) | Tools → Guide — Start here tab | **Tools → Guide** |

### Optional (outside the app)

| ID  | Filename | What |
| --- | -------- | ---- |
| S16 | `16-com0com-pair.png` | com0com paired ports |
| S17 | `17-tera-term-paired-com.png` | Tera Term on **paired** COM (not bridge COM) |

After capture, drop PNGs in `docs/images/` — a follow-up pass can embed `![S04](images/04-connect-running.png)` into this guide.

---

## 13. Quick command reference (terminal)

From the project folder (Python install):

```powershell
python check_setup.py              # Desk preflight
python check_setup.py --production # Boat preflight
python com_free.py                 # COM available?
python nmea_static_sample.py       # UDP test feed (bridge must be Running)
python verify_all.py               # Automated regression (dev)
```

---

## 14. What we defer until field numbers are known

COM names, survey IP, and INS IP will be wrong on the repo defaults until you configure the boat. That is expected:

1. Set real values on **Connect**.
2. **Save** Desk or Boat.
3. Use checklists and Start — no code changes required.

When you have final field values, copy `path_presets.json` to other PCs, or add `bench_defaults.local.json` next to the exe for fleet overrides (keeps public `bench_defaults.json` generic).