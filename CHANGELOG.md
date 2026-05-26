# Changelog (personal progress)

High-level notes for **this fork / branch** (`2034-ui-journey-modernization` and descendants).  
 Version = `version.py` / Git tag when you run `.\release.ps1` or tag manually.

## v1.14.5

- **Web position map — Satellite layer** — **Street** (OpenStreetMap) or **Satellite** (Esri imagery + place labels) via the map’s layer control (top-right); choice persists in the browser. Right-click **Position map** for the same shortcuts.

## v1.14.4

- **Web Survey monitor — Rows vs Columns** — **Rows** uses bordered metric tiles inside collapsible sections; **Columns** uses a true aligned grid table (header row + value row, column borders) per section so the two modes read clearly different.

## v1.14.3

- **Web Survey monitor — Simple layout** — Flattens nested section grids (fixes vertical letter-stacking and cramped tiles); clean 3×2 stat grid + GNSS strip; UDP shows port only (`10110`); nowrap values and tighter labels.

## v1.14.2

- **Tools → Terminal (typing)** — Backspace sends Windows BS (`0x08`) instead of DEL; PTY writes run on a background I/O thread so keys do not block the UI; small shell echo is painted immediately (bulk output still batched).

## v1.14.1

- **Tools → Terminal (smoothness)** — Batched PTY output (~28 ms) so the UI does not repaint on every byte; larger reads; debounced window resize; no outer scroll wrapper (terminal fills the pane); PowerShell starts with `-NoProfile` for less startup noise. Click **New session** to start (no auto-spawn on tab open).

## v1.14.0

- **Tools → Terminal** — Embedded local shell (PowerShell / cmd via optional **pywinpty** on Windows); **Open external…** when pywinpty is missing. Use for bench scripts and COM tools, not bridge traffic.
- **Tools → Inject** — Former “Terminal” NMEA inject tab moved here; saved tab order migrates `Send` / old `Terminal` → **Inject**. Product demo and Connect quick **Send→COM** unchanged.

## v1.13.14

- **PassThru label** — NMEA passthrough shows as **PassThru** on status chips and web Survey monitor (internal mode unchanged).
- **Survey monitor Simple** — Flat 2-column stat cards (state, transport, COM, UDP port, NMEA, Hz, GNSS) matching Rows styling; hides backpressure/extra Hz/line counters for narrow tiles.

## v1.13.13

- **Tools → Phone port/status** — Wider port spin box (left-aligned value, no `max-width` squeeze); **This PC** URL on two lines with full-width wrap; both cards min-width 320px.

## v1.13.12

- **Tools → Phone** — Extra spacing and top alignment for the **This PC** dashboard URL row so it no longer crowds the port spin box.

## v1.13.11

- **Phone port spin box** — Removed custom QSS “triangle” arrows on `webPortSpin`; uses standard Qt up/down step buttons (still gated by unlock).

## v1.13.10

- **Tools → Phone — Server card alignment** — Every row uses a real label (`Web API`, `Port`, `This PC`, …); field hosts span the column so checkboxes and buttons stay left-aligned with the port spin (fixes centered Enable/Open). Local dashboard URL on its own labeled row below port.

## v1.13.9

- **Tools → Phone — Server card** — Same `QFormLayout` rows as Phone Pairing: port controls on their own row, dashboard URL/status on the next row (no overlap), checkboxes aligned in the field column. Inline actions use `QStyle` icons (`SP_BrowserReload`, `SP_FileIcon`, etc.) with `webIconRole` for optional custom SVG.

## v1.13.8

- **Tools → Phone panel alignment** — Strict `QFormLayout` columns (right-aligned labels, left-aligned fields), left-aligned checkboxes, text-only inline action buttons (no broken theme icons), listen URL under port with dimmed `webListenStatus` styling.

## v1.13.7

- **Tools → Phone panel UX** — Two cards (**Server & Network** / **Phone Pairing**), inline icon actions beside URL and token fields, lock/unlock port control with status text, subtle dark styling (no yellow port highlight), tooltips and **?** help on labels instead of paragraph copy.

## v1.13.6

- **Web default = grid layout** — `GET /` serves the GridStack dashboard; classic accordion UI remains at `/static/index.html` (linked from grid banner/footer). Fixed `build_gridstack_index.py` script injection when `dashboard.js` uses `?v=` query (grid page was missing GridStack JS).

## v1.13.5

- **Grid map ⋯ menu (stale script fix)** — `gridstack-layout.js` patches the menu when an old cached `dashboard.js` is loaded (typical with frozen v1.13.0 zip). Map actions: center on fix, clear/fit track, etc. Web API serves `.js` with `Cache-Control: no-store`.

## v1.13.4

- **Web map context menu** — Map right-click / ⋯ now lists center on fix, track, and related actions first; clicks on the Leaflet map resolve to the map panel. `dashboard.js?v=` cache bust so browsers load the latest script.

## v1.13.3

- **Web dashboard ⋯ chrome menus** — Panel-specific actions: **Map** — center on fix, fit/clear track, show/hide track, toggle map, refresh size; **Log** — pause, auto-scroll, clear, expand; **Survey monitor** — expand all sections; **COM / Discovery / Tools** — refresh, unlock, copy setup link.

## v1.13.2

- **Removed Layout 2.0 beta** — Dropped `/static/layouts/v2/` trial; **GridStack** remains the customizable web layout (`/static/layouts/gridstack/`). Focus next: tile resize–aware panels and map/tools enhancements on the grid.

## v1.13.1

- **Fix: frozen build console storms** — Diagnostics and verify scripts no longer spawn system `python.exe` windows (use bundled `nmea-serial-bridge.exe --run-helper …`). `arp`/`ipconfig`/`netstat`/`bench_stress` subprocesses use `CREATE_NO_WINDOW` on Windows. **Do not use v1.13.0** if you see flashing blank terminals.

## v1.13.0

**Release build** — Web operator dashboard + GridStack beta (v1.11–1.12) packaged in frozen `web/static` (standard UI at `GET /`, grid trial at `/static/layouts/gridstack/`). Field strip layout tests aligned with current compact strip sizes. Use `.\release.ps1` for zip + optional `gh release`.

**Known issue:** v1.13.0 may flash many console windows when Diagnostics or LAN discovery runs — replaced by v1.13.1.

- **Web dashboard** — Status, config, discovery, start/stop, live log, position map, Survey monitor (Rows / Columns / Simple), section chrome menus (hide headers, terminal-only log, prioritize map), context menu stability.
- **GridStack beta** — Drag/resize tiles, ▲▼ reorder, collapse shrink, Lock layout, touch **⋯** / long-press, iPhone resize bars, left-edge width bar, optional hide resize bars.
- **Static routing** — Directory `index.html` served for layout folders (`html=True`).
- **Qt** — UI journey modernization (008), returning-user launch restore, Product Demo snapshot (v1.10).
- **Release tooling** — `build.ps1` uses `tools/run_unittests.py`; `verify_all` tolerates expected bridge test log tracebacks; `docs/RELEASE_CHECKLIST.md` added.

## v1.12.8

- **Survey monitor Columns** — True two-row table per section (all labels on one line, all values on the next); no stretched mini-columns. GNSS spans full width. Switching back to Rows restores normal stat cards.

## v1.12.7

- **Grid layout lock** — **Lock layout** checkbox in the header (grid beta page) saves tile positions/sizes/order; disables drag, resize, ▲▼ reorder, and resize bars until unchecked.

## v1.12.6

- **Survey monitor Columns layout** — Fixed Columns mode on grid/standard dashboard: true table per section (label row, value row) instead of looking identical to Rows.

## v1.12.5

- **Web dashboard context menu** — Options menu no longer closes every ~1–2 s from log autoscroll; removed global scroll-dismiss, added brief open guard, outside-tap/click to close.

## v1.12.4

- **GridStack resize bars** — Left-edge width bar added (mirrors right). **Hide resize bars** in ⋯ / long-press menu restores corner resize on desktop when hidden.

## v1.12.3

- **GridStack touch resize** — Full-width blue **bottom resize bar** on each tile (and right edge on phone) for reliable iPhone resize; disables tiny corner handles on coarse pointers. Live height/width updates while dragging.

## v1.12.2

- **Touch layout options** — **⋯** on each section header opens the same menu as right-click (hide header, terminal-only log, prioritize map, Survey monitor layouts). Long-press (~½ s) on a section also opens it on phone. When the header is hidden, a floating **⋯** appears on the tile.

## v1.12.1

- **GridStack iPhone resize** — Resize handles always visible with larger touch targets; fixes tile resize on iPhone after autohide/hover-only handles.

## v1.12.0

- **GridStack + standard controls** — Grid layout beta now has ▲▼ section reorder (swaps tile positions), plus existing drag/resize, collapse shrink, and right-click chrome (hide headers, terminal-only log, prioritize map, Survey monitor layouts). ▲▼ no longer starts a drag on grid tiles.

## v1.11.8

- **Survey monitor columns layout** — Fixed crushed vertical text; columns mode now shows labels on top and values below, left-to-right (e.g. State / Running · COM port / COM3 · Baud / 115200).

## v1.11.7

- **Survey monitor layouts** — Right-click Survey monitor (header or inside): **Rows** (default sections), **Columns** (table-style headers over values), **Simple** (state, transport, GNSS badge, sats, HDOP only; keeps green/red/blue GNSS and transport alerts).

## v1.11.6

- **GridStack collapse** — Collapsing a section (▶) now shrinks the tile to header height; expanding restores the previous tile size. Saved layout keeps expanded heights, not collapsed stubs.

## v1.11.5

- **Web dashboard chrome menus** — Right-click any section header (▼ label bar) to hide that header or all headers; right-click **Live log** for **Terminal only**; right-click **Position map** for **Prioritize map**. Choices persist in the browser. Works on standard and GridStack layouts.

## v1.11.4

- **GridStack beta** — Removed per-tile viewport fullscreen (⛶ / right-click restore); drag-resize grid only.

## v1.11.3

- **GridStack tile fullscreen** (reverted in v1.11.4) — Experimental overlay fullscreen per panel.

## v1.11.2

- **GridStack beta polish** — Default 12-column tile positions (COM + Survey top row, map/config second, tools/discovery, full-width log); disable CSS grid conflict on beta page; **Reset layout** button; layout storage key `v2` (clears old left-stacked saves).

## v1.11.1

- **Web static — directory index** — `StaticFiles` now uses `html=True` so `/static/layouts/gridstack/` (and other folders with `index.html`) return the page instead of FastAPI `{"detail":"Not Found"}`.

## v1.11.0

- **Web dashboard — GridStack beta** — Standard layout unchanged at `GET /`; optional trial at `/static/layouts/gridstack/` with vendored GridStack 10.3.1 (drag/resize tiles, layout in `localStorage`). Baseline snapshotted in `web/static/layouts/1.0/`. Footer link **Grid layout (beta)** on the standard page.

## v1.10.0

- **UI journey modernization (008)** — Returning-user launch restore, UI audit inventory (zero P0), Product Demo session snapshot/restore, web dashboard handoff copy aligned with **Tools → Phone**, and `test_web_handoff.py` / `test_demo_snapshot.py` gates.

## v1.9.86

- **Returning user (008 US1)** — Launch restores `last_preset` through one path in `_finalize_ui`; Field strip shows active preset and NMEA mode; tests for `last_preset` and recent-session apply.
- **UI audit (008 US2)** — `docs/ui-audit-inventory.md` with all P0 closed; operator docs no longer mention removed **Reset sizes**; Phone tab auto-enables **Show QR** when a saved token exists; Standard default window 1200×720.

## v1.9.85

- **Product Demo — session restore** — Opening **View → Product demo** snapshots your COM, network, NMEA, preset, and bridge run/stop state; closing the presenter restores it within a few seconds. Demo steps no longer write presets or recent sessions while presenting. Status banner shows **Demonstration** while the dialog is open. **Reset demo script** rewinds the presenter to Welcome without touching Connect.

## v1.9.84

- **Tools → Phone — port ▲▼** — Web API port step buttons use a visible button strip and triangle arrows (dark/light themes); no more invisible controls on the right.
- **Connect toolbar** — Removed **Reset sizes** (disclosure layout no longer uses splitters; button had no effect). Saved toolbar prefs drop `reset_sizes` automatically.

## v1.9.83

- **Tools → Phone — QR panel** — Embedded Phone-tab QR refreshes when prefs load (no stale “Generate a token first” while a token exists). Floating Connect QR hides on **Tools → Phone** so it does not stack on the built-in QR; it returns on Connect/Log.

## v1.9.82

- **Tools → Phone — Web API port spin** — Port field is compact with ▲▼ pinned on the right edge (no wide empty gap). Unlock uses read-only lock instead of disabling the whole control so both step buttons work. Port prefs save immediately when you change the value.

## v1.9.81

- **Standard Connect — Serial & network side-by-side** — **Serial** and **Network (UDP listen)** sit in one row (like your layout mockup) so both are visible without scrolling the connection section. Default panel height targets updated for the shorter block.

## v1.9.80

- **Tools → Phone — Web API port lock** — Dashboard port spin box ignores the mouse wheel (scroll moves the page, not the port). Port is locked by default; check **Unlock port (10 s)** to edit, then it auto-locks again.

## v1.9.79

- **Presets + NMEA mode** — Tools → Presets **Save** / **Save as…** now stores the current **Passthrough / Strict / Raw** choice from Tools → NMEA (and strict sentence-type checkboxes). Loading a preset restores those radios; log line includes the mode. Existing presets without `nmea_mode` default to passthrough on load.

## v1.9.78

- **Web COM & ports + Discovery Select** — Fixed the same silent click block on COM rows while Running (`pointer-events: none`). Row/Select taps always reach the handler: network updates live, COM shows **Stop first** with a visible warning. One click delegate on the dashboard panel root; token errors show in the relevant section.

## v1.9.77

- **Web Discovery Select** — Network adapter rows and **Select** work again (including while the bridge is running). COM rows still require **Stop** first. Clicks use delegated handlers so row taps register reliably on phone layout.

## v1.9.76

- **Web dashboard (phone)** — Discovery adapter rows use a 3-line grid (name, host:port, mode tag) so preset labels no longer overlap IP text. **Expand log** pins the log panel under the Start/Stop header for most of the screen (Ctrl+F5 to pick up CSS).

## v1.9.75

- **Phone QR — all layouts** — Floating setup QR matches Field behavior everywhere (Standard, Minimal, Log-first): always visible when Web API + LAN bind are on, centered in the log area on startup, stays put across layout switches. Position is saved once in **global** prefs (normalized) so drag-to-move applies to every layout.

## v1.9.74

- **Field layout — phone QR** — Floating setup QR defaults to the **center of the live log** on startup (not the bottom-right). Stays centered when you resize until you drag it; your position is still saved per layout.

## v1.9.73

- **Web API port bind (WinError 10048)** — Restarts are serialized: wait for the old listener to release the port before starting again, skip duplicate overlapping restarts, and show a clear **Port N is already in use** message in Tools → Phone instead of repeated uvicorn errors.

## v1.9.72

- **Tools → Phone — Web API port** — Port spin arrows restart the API immediately (no need to press Enter). A live line shows **This PC dashboard: http://127.0.0.1:PORT/**; Phone dashboard URL port stays in sync. **Open dashboard** uses localhost when LAN bind is off.

## v1.9.71

- **Web dashboard rolled back to Layout 1.0** — Live `web/static/` restored from `web/static/layouts/1.0/` (pre–Layout 2.0). Offline UI no longer shows the false “Bridge is running” banner when the API is down.

## v1.9.70

- **Web dashboard offline state** — When the API is unreachable, the UI no longer shows the misleading “Bridge is running” lock on Configuration; forms stay disabled with the correct **Backend offline** message and recovery hint.

## v1.9.69

- **Web COM picker** — Selecting COM7 no longer snaps back to COM1: hub “last known good” is applied before explicit `com_port` in `PATCH /config`, and the dashboard uses **configured** vs **runtime** COM (`configured_com_port` vs open serial while Running).

## v1.9.68

- **Tools → Presets** — **Save as…** works while the bridge is running (writes a new named preset only). **Delete** stays blocked until Stop, with a clear message and Yes/No confirm. Preset name dialog uses a raised modal so it is not hidden behind the main window.

## v1.9.67

- **Connect status banner** — “Stopped / Load a preset…” text bumped +3 pt (title 9 pt, detail 8.5 pt) so it stays compact but easier to read than v1.9.65–66.

## v1.9.66

- **Web dashboard — Select + layout** — COM & ports and Discovery **Select** / row tap use delegated clicks (fixes no-op on some browsers). Network select sends `udp_listen_host`/`port` plus `hub_device_id` so presets and NIC rows apply when stopped. **Tailscale** appears from `Unknown adapter Tailscale` in ipconfig and from `tailscale ip -4` when missing. **Panel ▲▼ order** follows saved DOM order on desktop grid. **layout-desktop** / **layout-mobile** body classes tighten spacing on PC vs phone.

## v1.9.65

- **Connect status banner (Standard UI)** — “Stopped / Load a preset…” box is ~40% smaller: tighter padding, smaller type, and vertical size capped so it takes less room above the green panel headers.

## v1.9.64

- **Web dashboard Layout 2.0 Phase A (PC polish)** — Map in default panel order; desktop opens COM + Survey monitor + map (setup panels collapsed). Map spans two columns when open; Leaflet resizes on panel open/resize. Run-alert auto-hides and clears when status disagrees (no more “Bridge stopped” under Running). Discovery serial list hidden on wide screens (use COM & ports).

## v1.9.63

- **Web dashboard: position map (GGA/RMC)** — Collapsible **Position map** panel with **Show map** toggle. Live lat/lon from `/status` (`position_lat`, `position_lon`, `position_source`, `position_stale`); vendored Leaflet + OpenStreetMap tiles when online. `bridge.navigation_position()` reserved for a future Survey HUD map (no Qt map in this release).

## v1.9.62

- **Fix: bridge thread crash after UDP/GGA** — Bridge thread errors now log a full traceback (not only `repr`). Stats/status Qt callbacks and the UDP datagram handler are wrapped so a bad UI callback cannot tear down the asyncio loop after NMEA is received.

## v1.9.61

- **Fix: Connect section styles (Pill / Seamless / Outline / Accent)** — Section style from Tools → Theme now visibly updates Run and Serial & network headers. Fixed early no-op apply before the panel host existed, disabled AutoRaise on disclosure buttons (stylesheet backgrounds were ignored), repolish the full panel tree on change, and re-apply after theme swaps.

## v1.9.60

- **Fix: COM/Baud scroll wheel (complete block)** — Wheel input is fully disabled on COM, Baud, and TCP reconnect controls (not only when unfocused). Focus policy is ClickFocus so hover-scroll no longer changes values under Qt StrongFocus.
- **Fix: COM/Baud dropdown arrow clipping** — Connect serial combos get min height, drop-down subcontrol padding, and form row spacing so the arrow is not cut off by rounded styling.

## v1.9.59

- **Fix: scroll wheel on COM/Baud** — COM and Baud dropdowns (and TCP reconnect delay) ignore the mouse wheel unless you click into them first, so scrolling the Connect tab no longer changes values accidentally.

## v1.9.58

- **Connection hub → Diagnostics** — Card grid moved to **Tools → Diagnostics** (two visible rows + scroll). **Connect → Serial & network** is COM/UDP settings only — no hub splitter fighting your layout.
- **Hub pick vs manual COM** — Editing Connect fields still overrides a hub card pick on Start (same as before, without Manual override checkbox).

## v1.9.57

- **Fix: Connect empty gap / clipped hub** — Stopped stretching the panel stack to fill the viewport (that left a tall dead zone above the COM cards). Connection hub keeps ~280px+ for the card grid when Manual override is off; scroll the Connect tab for more sections.

## v1.9.56

- **Fix: Connection hub narrow column** — Removed the extra scroll wrapper around Serial/network (one Connect tab scroll only). Hub card grid now measures the real tab width so COM cards use the full row instead of a thin strip on the left.

## v1.9.55

- **Fix: Connect layout on startup** — Ignores junk saved panel heights from the old splitter (e.g. 26–48px) that squashed **Serial & network**; multi-open sections size naturally with full-width scroll. Click **Reset sizes** once if prefs were already corrupted.

## v1.9.54

- **Fix: Connect narrow column** — Expanding sections (or startup with Run + Serial open) no longer leaves the scroll page stuck at a tiny fixed width from a prior **Collapse all**; viewport resize clears the width lock so Connect uses the full tab again.

## v1.9.53

- **Fix: Connect startup / Expand all** — Default **Run** + **Serial & network** layout no longer caps section height or pins the outer scroll page; the connection hub sizes from content so cards are not trapped in a tiny inner scrollbar. One deferred relayout pass after first paint.

## v1.9.52

- **Fix: Expand all** — Multiple open Connect sections stack at their natural heights (no bottom stretch or vertical `Expanding` fight), so **Run** and **Serial & network** no longer overlap or clip the connection hub. Scroll area uses a fixed content height when two or more sections are open.

## v1.9.51

- **Fix: Collapse all (layout)** — Connect sections use a vertical stack instead of a `QSplitter` inside a resizable scroll area, so **Collapse all** keeps normal header strips without squashing into one line or leaving a tall empty gap. Scroll area turns off `widgetResizable` when every section is collapsed so height matches content.

## v1.9.50

- **Fix: Collapse all (again)** — Scroll-area geometry no longer clears the compact height lock, so sections stack as normal strips instead of a thin red stack with a huge empty void below.

## v1.9.49

- **Fix: Connect Collapse all** — Splitter height is pinned before `setSizes` so collapsed strips stack compactly (no tall dead gap). Thinner handles when all collapsed.
- **Fix: QR flicker** — Debounced refresh; skips redundant hide/show during layout reflow.
- **Fix: Web API restart** — Debounced server stop/start (port spinner no longer kills the server on every click); clearer log lines for browser URL and LAN token.

## v1.9.48

- **Fix: UI editor / restore defaults crash** — Rebuilding Connect panels no longer deletes `intent_hint` and other shared widgets (`libshiboken … already deleted`).

## v1.9.47

- **Fix: Connect collapse spacing** — Collapsed sections no longer leave a tall empty gap with a floating splitter handle; **Collapse all** stacks compact strips. Expanded sections still absorb slack; multi-open layouts keep draggable handles.

## v1.9.46

- **Fix: UI editor desync** — Apply no longer rebuilds Connect panels unless section order/visibility actually changed (top bar / main tab edits stay isolated). Splitter heights clamp to the visible area so green rows are not squashed flat.

## v1.9.45

- **Connect QR** — Floating draggable chip on the window (no right-hand column). **Right-click → Hide**; toggle **Web API** off and on to show again. Position saved in prefs.
- **Fix: UI editor tab reorder** — After changing main/Connect layout, panel splitters and row styles resync so **Serial & network** no longer clips.
- **Connection hub** — Taller minimum height so hub header/cards stay below the section title.

## v1.9.44

- **Fix: UI editor** — Typo (`sub_l_lbl`) crashed dialog open; **UI editor** and **UI editor…** work again.
- **Fix: Connect splitters** — Tab focus no longer resets section heights; drag handles keep your sizes (persisted on release).

## v1.9.43

- **Connection hub resize** — Vertical splitter between discovery cards and **Manual override** (drag the handle); sizes saved in prefs. Taller default **Serial & network** panel. Card grid scrolls horizontally when needed.

## v1.9.42

- **UI editor** — Wider default window (760×540) so labels are not cut off; **↑ ↓** buttons replace broken drag-reorder; clearer instructions per tab. Tab renamed **Toolbar** (was Connect toolbar).

## v1.9.41

- **Connect launch layout** — Version line and status banner stay **above** the collapsible sections (not buried inside **Serial & network**). That section is now COM/UDP + Connection hub only.

## v1.9.40

- **Fix: Connect QR crash / layout thrash** — Restored missing `recommended_qr_lane_width`; debounced QR splitter updates so enabling API + LAN no longer hides the code or bounces the Connect panels.

## v1.9.39

- **Connect QR default width** — Lane opens wide enough to show the full code (saved width bumped if too narrow).
- **Connect section styles** — **Tools → Theme → Connect sections**: Pill, Seamless, Outline, Accent bar (persisted).
- **New color themes** — **Midnight Teal** and **Arctic Day** in the theme picker.

## v1.9.38

- **Connect seamless layout** — Flat disclosure rows (no pill cards); QR sidebar uses a **horizontal splitter** (drag to resize, width saved). QR matches app background with white quiet zone only on the code; scales with lane width.

## v1.9.37

- **Connect tab QR layout** — QR uses a dedicated right column so green disclosure rows end cleanly (no overlap under the code). Subtle lane divider when API + LAN are on.

## v1.9.36

- **Connect tab QR (Standard)** — When **Enable Web API** and **Allow LAN / Tailscale** are both on, a compact setup QR floats top-right on **Connect** (over Run / Serial & network panels). Stays visible while sections expand/collapse; **Tools → Phone** unchanged.

## v1.9.35

- **Phone tab** — Web API, Tailscale/LAN URL, token, QR, and setup-link actions moved from Guide to **Tools → Phone** (2nd after Presets) in Standard, Field, and drawer layouts. Guide keeps connection workflows only. **Show QR** on by default on the Phone page; **Open dashboard in browser** button added.

## v1.9.34

- **Field layout** — Preset/intent hint wraps (no single-line elision); taller default control strip; wider UDP host/port fields; status bar stats use remaining width with shorter stopped text; top bar **Shortcuts** tile reads **Keys** when narrow.

## v1.9.33

- **Bridge thread** — Suppress benign `ConnectionResetError` (WinError 10054) asyncio callback spam on Windows/Python 3.14 when UDP/TCP peers drop.
- **Diagnostics** — Catch spawn-setup errors in the panel instead of only printing a traceback to the terminal.

## v1.9.32

- **Diagnostics** — Automated checks work on PySide6 builds without `setCreateProcessArgumentsModifier` (Python 3.14 / current wheels); no-console spawn falls back to `pythonw.exe`.
- **Connect** — Fix `QBoxLayout::insert: index 2 out of range` when embedding Connection Hub on an empty connect body layout.

## v1.9.31

- **Docs** — NORBIT DCT wording neutralized (no personal names in preset notes or operator doc).

## v1.9.30

- **NORBIT DCT** — [docs/NORBIT_DCT.md](docs/NORBIT_DCT.md) and preset notes: DCT target **depends where DCT runs** — **127.0.0.1:40810** on boat PC; **192.168.1.8:40810** from operator laptop (MikroTik PTP boat IP); **Tailscale/ZeroTier StaticIp:40810** over VPN. Bridge still listens **40810** on the boat PC.

## v1.9.29

- **NORBIT DCT** — Preset and [docs/NORBIT_DCT.md](docs/NORBIT_DCT.md): boat PC **UDP port 40810**; DCT and Applanix use the PC’s **local IPv4** (e.g. 192.168.1.4) or **Tailscale IP** on that port (not 10110 for this stack).

## v1.9.28

- **Documentation** — New [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) (install + 15-minute walkthrough), [docs/README.md](docs/README.md) index; [OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) and [README.md](README.md) updated for Standard `Connect | Log | Tools`, UI editor, web dashboard, Diagnostics cards, and NORBIT/NTRIP notes.
- **Guide tab** — Buttons open Getting started / Operator guide / NORBIT DCT; in-app UDP/TCP steps match current Presets UI.
- **Diagnostics** — Default card order puts **Automated checks** first; traffic legend card uses a compact width; **Reorder cards…** dialog enlarged with reliable drag flags.

## v1.9.27

- **UI editor** — Connect and Connect toolbar lists use drag-and-drop reorder (`InternalMove`); dialog opens larger and stays resizable. **Serial & network** defaults directly under **Run bridge** (legacy factory order migrates on load). Use **Restore defaults** in the Connect tab to reset section order and splitter sizes.

## v1.9.26

- **NTRIP hidden** — Connect tab NTRIP panel removed from Standard layout and UI editor; saved `enabled` is forced off (Applanix/iWBMSe workflows use internal RTK). `ntrip_client` remains in tree for possible future use.

## v1.9.25

- **NORBIT DCT preset** — Defaults for Applanix+iWBMSe stack: survey PC **192.168.1.4**, Applanix **192.168.1.150**, UDP **10110**; docs clarify Trimble **192.168.142.1** → Applanix, Bluetooth **$SDDBT** → separate DCT COM (not the bridge).

## v1.9.24

- **NORBIT DCT** — Built-in preset **NORBIT DCT** (boat-style LAN notes) and operator doc `docs/NORBIT_DCT.md` for INS UDP → COM → DCT positioning workflow.

## v1.9.23

- **Web dashboard header** — Removed empty Control panel; Start/Stop alerts show in a strip under the top bar. Live **status chip** (`COM · UDP port · Running/Stopped · Hz`) between the run buttons and connection indicator.

## v1.9.22

- **Web dashboard** — **Start/Stop** moved to the top bar beside the version tag; Control panel keeps status messages.
- **Web live log NMEA filter** — Dropdown replaced with picker + **Custom…** dialog (checkbox grid like desktop). Click one type; **Shift+click** in the list to combine (e.g. GGA+RMC). Presets: All types, Survey (GGA+RMC), Clear.

## v1.9.21

- **Web dashboard reorder (localhost + phone)** — Same **▲▼** controls on every screen size; removed unreliable drag handles. Wide layouts no longer pin sections to fixed grid cells, so saved order applies on desktop too.

## v1.9.20

- **Fix — web dashboard ▲▼ reorder on portrait phone** — Removed fixed CSS `order` on sections (it ignored DOM moves in vertical layout); order now follows saved layout on all orientations. Larger ▲▼ touch targets on narrow screens.

## v1.9.19

- **Web live log — expand** — **Expand log** checkbox fills the dashboard (hides Control/COM/Config/etc.) for a near full-screen terminal; uncheck or tap the Live Log header to minimize and configure again. Preference saved in the browser.

## v1.9.18

- **Web discovery — host NICs** — Network adapters list now includes this PC’s Ethernet/Wi‑Fi/Tailscale IPv4 addresses (from `ipconfig`), not only UDP listen/presets/LAN scan.
- **Web live log** — Filter by NMEA sentence (GGA, RMC, …) or custom substring; kind filter unchanged; filters are view-only in the browser.
- **Web COM Select** — Tap/Select applies COM with visible confirmation, updates Active COM immediately; works without desktop Connection Hub; network select requires bridge stopped.
- **Unlock ports copy** — COM & ports hint explains unlock probes/releases stuck COM and checks UDP listen port busy state.

## v1.9.17

- **COM port scan (web)** — Discovery lists **all** PC COM ports (pyserial), not only GNSS-keyword matches; **Refresh ports** calls fast `/ports/refresh` (no separate scanner app).
- **Dashboard reorder** — Drag **⋮⋮** handles (desktop) or **▲▼** (phone) to reorder sections; order saved in the browser.

## v1.9.16

- **Web discovery fix (Field UI)** — COM/LAN discovery now runs without the desktop Connection Hub widget; phone Refresh ports / Discovery scan populate serial + network lists (fixes stuck 15 s timeout and empty COM dropdown).
- **Web GNSS colors** — Survey monitor GNSS tile uses RTK/GPS/no-fix badge colors; card header strip reflects fix quality while running.

## v1.9.15

- **Fix** — Baud `QComboBox` startup crash (`AttributeError: text`) — all desktop paths use `read_baud_widget()` / `currentText()`.

## v1.9.14

- **Standard baud dropdown** — Desktop Connect and web Configuration use a fixed list (4800–460800 survey/GNSS rates); legacy custom baud values snap to the nearest preset on load.

## v1.9.13

- **Phone COM workflow** — New collapsible **COM & ports** section under Control (tap-to-select, Apply COM, Refresh/Unlock); all dashboard cards collapse like Survey monitor (state saved); phone order Control → COM → monitor; Live Log/Discovery collapsed by default on mobile.

## v1.9.12

- **GNSS status badges** — Status bar and Survey HUD GNSS fix tile use color-coded badges (green RTK 4/5, blue GPS/DGPS 1/2, red no-fix/idle) with padding and rounded corners; idle stream shows soft red with “No Data Stream”.

## v1.9.11

- **GNSS stale reset** — When NMEA traffic hits 0 Hz or no GGA/NMEA is parsed for 2 s, HUD/status/web GNSS fields clear (0 sats, fix quality 0, “No Data Stream”) instead of holding the last simulator values.

## v1.9.10

- **Web Survey monitor UX** — 2-column stat grid (larger type, like v1.8); collapsible HUD sections (Connection, Sentence rates, Session, Backpressure) with one-line summaries when collapsed; mobile defaults hide Session/Backpressure until expanded.

## v1.9.9

- **Web Survey monitor** — `/status` exposes HUD metrics (inject Hz, session line totals, per-direction drops/rejects/queues, GNSS, transport OK). Dashboard uses a full-width monitor strip and denser layout (less empty space in status/control/discovery cards).

## v1.9.8

- **Web Live Log** — removed **Cards** layout trial; **Terminal** and **Table** only.

## v1.9.7

- **Phone setup link / QR use Tailscale IP, not 127.0.0.1** — LAN mode blocks localhost in QR and Copy phone setup link; **Detect Tailscale IP** button; Phone dashboard URL field strips pasted `#bridge-token` fragments. Renamed visible **Remote control token** label.

## v1.9.6

- **iPhone web UX** — clearer token onboarding copy; Copy failures on HTTP show a helpful message; Share link fallback when copy is blocked.

## v1.9.5

- **Fix: phone web UI token handoff** — setup links (`#bridge-token=…`) apply again (JavaScript `split` limit bug broke hash parsing). Token Tools panel shows whenever LAN bind is enabled, not only after a token exists in prefs.
- **Fix: PC Guide Web controls** — **Web & phone** is the first Guide tab with API token, setup links, and QR (no longer buried above long workflow docs).

## v1.9.4

- **Web dashboard — Live Log** — `GET /logs` mirrors the desktop live log; new **Live Log** card with three trial layouts (**Terminal**, **Cards**, **Table**), filter, auto-scroll, pause view, and clear. Layout choice persists in browser localStorage.
- **Release gate** — `verify_all` / `run_unittests` treat Windows Qt `0xC0000409` shutdown and uvicorn bind noise correctly after tests pass.

## v1.9.3

- **Symmetric token handoff (all devices)** — **Paste setup link** on web dashboard and PC Tools → Guide imports a link/token from clipboard (phone → PC without typing). **Share link** on phones (system share sheet). Bidirectional hints on dashboard and Guide.

## v1.9.2

- **Phone token onboarding (no self-scan QR)** — Setup links use `#bridge-token=…` so opening the link on the phone saves the token automatically. Mobile dashboard hides the QR block, adds **Copy token** / **Copy setup link** / **Show** token, and shows PC-first instructions. Desktop Guide: **Phone dashboard URL** (Tailscale/LAN), **Copy phone setup link**, QR encodes the setup URL (scan from PC screen with phone camera).
- **`GET /token-qr?setup=1&base_url=…`** — QR payload is a one-tap dashboard URL, not raw token text.

## v1.9.1

- **Guide tab — desktop QR for API token** — **Show QR** checkbox beside Generate token; scannable QR appears on the right side of Web control (uses `qrcode` package). Fixes gap where QR existed only on the browser dashboard, not on Tools → Guide.

## v1.9.0

- **Web dashboard — editable configuration** — COM, baud, network mode (UDP listen/remote, TCP client/server), listen/remote host/port; Save via `PATCH /config`; locked while bridge is running.
- **API token QR** — `GET /token-qr` (SVG); dashboard checkbox **Show QR for API token** for phone scan from PC screen (`qrcode` in `requirements-web.txt`).
- **Façade** — `network_mode`, `remote_host`, `remote_port` applied on main thread; config readback includes remote fields.
- **Field layout** — Guide tab in scroll area; Web control group minimum height; drawer min height 320px (fixes clipped token/port rows).
- **Standard Connect** — COM `refresh_ports` preserves selection + empty-state placeholder; Connect splitter handle 10px + minimum height.

## v1.8.4

- **Guide → Web control: API token field** — LAN checkbox no longer says "token in ui_prefs" with no UI. Added **API token** line edit, **Generate token**, and **Copy** on Tools → Guide. Token is saved to `ui_prefs.json` and used for `X-Bridge-Token`. Enabling LAN auto-generates a token if missing. Phone dashboard: paste the same token in Tools → API token field.

## v1.8.3

- **Fix: commands still fail with "Application window not available"** — `_window()` only consulted a weakref set by `attach_window()`, which never ran on Standard/Field/Minimal layouts. The façade is always constructed as `BridgeAppFacade(main_window)`, so `_window()` now falls back to `self.parent()`. `publish_from_window()` also re-attaches if the ref was missing. `GET /meta` adds `commands_ready` for dashboard diagnostics.
- **Dashboard (LAN / phone)** — clear message when `token_required` but no token in `localStorage` (POST needs `X-Bridge-Token` over Tailscale/cellular).

## v1.8.2

- **Fix: Start/Stop/Unlock/Discovery commands never worked** — `BridgeAppFacade.attach_window()` was placed in `mixin._on_ui_ready()`, but every UI subclass (`standard.py`, `field.py`, `minimal.py`) overrides `_on_ui_ready` without calling `super()`, so that method never ran. `_window_ref` stayed `None` and every command returned "Application window not available". Also: `_maybe_start_web_server` suffered the same bypass, meaning the web server only started if the user manually toggled the web settings after launch. Fix: extracted both into a new `_init_web_and_facade()` method called unconditionally from `_finalize_ui()` after `_on_ui_ready()`, bypassing the override gap entirely.

## v1.8.1

- **Dashboard CSS `[hidden]` fix** — CSS `display: flex/inline-block/grid` rules were overriding the HTML `hidden` attribute. Added `[hidden] { display: none !important; }` reset at top of `dashboard.css`. Fixes: offline banner always showing alongside live data; "⟳ Scanning…" spinner always animating; token field always visible even when not required; status grid not hiding on backend-offline.
- **Clear stale window-error alerts on reconnect** — "Application window not available" alerts left over from early startup clicks are automatically dismissed the first time the status poll comes back online.
- **`extractApiError()` helper** — API error detail can be a plain string (401) or an object with `.message` (our command results). Centralised parsing replaces all inline patterns so error messages display cleanly in all cases.

## v1.8.0

- **Phase B Operator Dashboard** — static HTML/CSS/JS dashboard served at `GET /` by the FastAPI web server (no CDN, fully offline-capable).
  - **US1 Telemetry**: live Hz, drops/rejects, bridge state refreshed every second; offline banner on backend loss.
  - **US2 Start/Stop**: large tap-friendly buttons map to `POST /bridge/start` and `POST /bridge/stop` with in-flight disable and inline error messages.
  - **US3 Unlock Ports**: Unlock button → `POST /ports/unlock`; `smart_release_com` result shown inline (no QMessageBox on API path).
  - **US4 Discovery + COM picker**: Refresh Scan → `POST /discovery/refresh`; polls `GET /discovery` every 500 ms (≤ 15 s); click any serial/network row → `PATCH /config` with 409 running-guard message.
- **New API routes**: `GET /meta` (version, lan_bind, token_required), `GET /discovery`, `POST /discovery/refresh`, `POST /ports/unlock`, `GET /api` (JSON index, old `GET /`).
- **`BridgeAppFacade` extensions**: `SerialDeviceDto`, `NetworkCardDto`, `WebDiscoveryPayload`, `WebMeta` dataclasses; thread-safe discovery cache; `request_refresh_discovery()` and `request_unlock_ports()` via Qt signal dispatch.
- **`ui/mixin.py`**: wires `facade.update_discovery_snapshot(snap)` after hub `set_snapshot()` (both worker and fallback paths).
- **Token support**: token field appears only when `meta.token_required`; persisted in `localStorage` (`nmea-bridge-web-token`).
- **PyInstaller**: `web/static` folder added to `datas` in `nmea_serial_bridge.spec`.
- **Tests**: expanded `test_web_api.py` (10+ new cases) and `test_app_facade.py` (discovery cache, unlock, refresh with Qt event-loop harness).

## v1.7.2

- **Web API config + OpenAPI** — `GET /config` reads Qt fields on the main thread (fixes empty/wrong `com_port` vs `/status`); Swagger shows real response schemas (`StatusResponse`, `ConfigResponse`, `CommandResponse`) instead of generic placeholders.

## v1.7.1

- **Web API start/stop** — Commands from the HTTP thread now queue to the Qt main thread via a signal; `QTimer.singleShot` from uvicorn never ran, so Swagger/curl start/stop could time out or appear dead.

## v1.7.0

- **Hybrid UI Layer 1** — Standard Connect and Field control strip load from Qt Designer `.ui` files at runtime (`ui/ui_loader.py`, `ui/resources/`); programmatic fallback if assets are missing.
- **Hybrid UI Layer 2** — Optional **Web control plane** on `127.0.0.1:8765` (FastAPI): `GET /status`, `GET/PATCH /config`, `POST /bridge/start`, `POST /bridge/stop`; background uvicorn thread; `BridgeAppFacade` delegates to the same mixin as the desktop UI.
- **Tools → Guide** — Enable Web API, port, and LAN bind checkbox; prefs in `ui_prefs.json`.
- **Tests** — `test_ui_loader.py`, `test_app_facade.py`, `test_web_api.py`; optional `requirements-web.txt` and `bench_web_api.py`.

## v1.6.0

- **Connection Hub Phase 2** — responsive card grid (1–3 columns, card-only scroll), **Refresh discovery** (ARP + bounded UDP probes on survey ports), **Unlock ports** (Smart Release COM without restart), traffic **QoS** chips on the active card from bridge stats.
- **`network_scanner.py`** — LAN host list from `arp -a`, `scan_network()` with host/port budget; **`port_release.py`** — COM lock probe and smart release; **`ui/discovery_worker.py`**, **`ui/hub_quality.py`**, **`ui/connection_fields.py`**.
- **Field layout** — **Refresh** / **Unlock** on the bottom strip wired to the same handlers as Standard.
- **Tests** — `test_network_scanner.py`, `test_port_release.py`, `test_hub_quality.py`, `test_connection_fields.py`; extended discovery/hub/connect-panel tests.

## v1.5.1

- **verify_all / Qt teardown** — `ui/qt_test_harness.py`, `tools/run_unittests.py`, and `verify_all.py` treat Windows `0xC0000409` fast-fail as pass when unittest/GUI smoke output already shows OK. `bench_gui_smoke.py` closes windows and exits cleanly.

## v1.5.0

- **Connection Hub (Connect tab)** — card grid for detected GNSS serial ports and UDP listen context; selection drives COM/UDP for Start with per-device **last-known-good** in `ui_prefs.json`. Legacy serial/network fields live under collapsible **Manual override**.
- **`discovery_service.py`** — Qt-free discovery snapshots (serial stability, UDP port probe, live peer counts); `auto_discovery.py` delegates serial scan to the service.
- **TCP sink mirror** — optional `TcpSinkConfig` on `SerialNetBridge` mirrors serial→net bytes to a parallel TCP server (independent of UDP fan-out).
- **Field layout** — compact connection summary line under COM/UDP strip.
- **Tests** — `test_discovery_service.py`, `test_connection_hub.py`, `test_tcp_sink.py`.

## v1.4.10

- **Spec Kit baseline delivery** — `specs/001-baseline-spec/`: as-built spec (FR-001–FR-020), plan, tasks, traceability matrix, contracts, quickstart. No bridge logic changes.
- **Operator docs aligned with fan-out** — `README.md` and `docs/OPERATOR_GUIDE.md` document default-on fan-out vs single-link; new §5.5 two-client bench procedure (one bridge, not two apps).
- **`bench_fanout_probe.py`** — registers a UDP peer and listens for serial→net replies during fan-out bench tests.
- **`test_baseline_docs.py`** — guards README/operator-guide/traceability keywords.
- **Baseline cleanup** — `version_info.txt` synced to `version.py` (1.4.10) via `tools/sync_version_info.py`; **FR-021** auto-discovery formalized in baseline spec; **SC-003** HUD stress validation doc (`sc003-hud-stress-validation.md`); traceability waivers for OpenCPN UDP port conflict and `bench_gui_smoke` environment failures; `test_version_sync.py` added.

## v1.4.9

### Auto-Discovery — headless GNSS device watcher

- **`auto_discovery.py`** (new) — `AutoDiscoveryThread(QThread)` polls USB-serial ports every 2 s. Emits `device_detected(port_name: str)` once a matching device has been seen for 2 consecutive polls (stability guard prevents false fires during Windows USB enumeration churn). Resets after absence so reconnecting the same cable triggers again. Default keyword list covers Trimble, U-blox, NovAtel, Septentrio, Leica, Topcon, Hemisphere, SiRF, Garmin — intentionally excludes generic "FTDI" / "Serial" to avoid matching printers and Arduinos.
- **"Auto-connect on GNSS device detected" checkbox** — added to the serial connection section (below Auto-reconnect). Off by default; state is persisted to `ui_prefs.json`. When checked: COM port is updated automatically on device appearance; bridge auto-starts if the bridge is stopped and configuration passes `_validate_start()`.
- **Thread lifecycle** — started at `_finalize_ui()` close, stopped cleanly in `closeEvent()` (waits up to 2.5 s). Safe to run alongside all layouts (Standard / Field / Minimal / Log-first).
- **Tests** — `test_auto_discovery.py`: 13 new cases covering default keywords, `_scan()` matching (description / manufacturer / case-insensitive / custom keywords), stable-poll guard, no-re-emit guard, device-absence reset, `stop()` flag, and a live `run()` smoke test.

## v1.4.8

- **Diagnostic scripts work in the portable `.exe` build** — three-part fix:
  1. `nmea_serial_bridge.spec`: added `HELPER_MODULES` list (`bench_config.py`, `bench_udp_test.py`, `nmea_codec.py`, `bridge_core.py`, `py_interpreter.py`) to `datas` alongside the existing helper scripts so a fresh Python subprocess can import project modules from `_MEIPASS`.
  2. `ui/mixin.py` `_diag_start_script`: now injects `PYTHONPATH=_REPO_ROOT` into the `QProcess` environment, guaranteeing imports resolve even if the working-directory rule doesn't fire.
  3. `_diag_run_verify_all`: in a frozen build, checks for `test_bridge_core.py` and shows a clear "not available in portable build / clone and run from source" message instead of silently failing.
- Scripts that work in the portable build after this fix: `com_free`, `check_setup`, `nmea_static_sample`, `bench_tcp_stress`, `bench_capacity_probe`. `verify_all` requires the source tree.

## v1.4.7

- **Diagnostics scripts found in frozen `.exe` build** — `_REPO_ROOT` in `ui/mixin.py` was resolved using `Path(__file__).parent.parent` which points inside PyInstaller's bootstrap tree, not the exe directory. Replaced with `_resolve_repo_root()`: when `sys.frozen` is set, uses `sys._MEIPASS` (the one-folder dist directory where the spec bundles `verify_all.py`, `com_free.py`, etc. via `helper_datas`). Source runs unchanged. Added top-level `import sys` to `mixin.py`.

## v1.4.6

- **Guide tab rewritten** — replaced the old three-line disclaimer with a full structured workflow guide. Four tabs: UDP Flow, TCP Client, TCP Server, and Checklist. Each method has numbered setup steps with inline code spans for IPs/ports. Rendered via `QTextBrowser` with per-theme QSS (dark and light). The old static `QLabel` body is gone.

## v1.4.5

### Part A — "Run bridge" panel cleanup
- **Ghost text removed** — `CONNECT_PANEL_COLLAPSED_HINTS["run"]` trimmed to `"Start/Stop"` (dropped stale "bench setup" copy). Same fix in `CONNECT_PANEL_HINTS` in `ui_editor.py`.
- **Button row breathing room** — `al.setContentsMargins` changed from `(0,4,0,4)` to `(5,5,5,5)` and spacing from `6` to `10` px, eliminating the Start/Stop button overhang.

### Part B — HUD `KeyError` killed permanently
- **`default_layout()` fixed** (`ui/survey_hud_layout.py`) — `gnss_hdop` is now included in the metrics dict with value `False` (off by default) instead of absent. Old configs that exclude it are no longer broken at the source.
- **`_migrate_hud_metrics()` added** (`ui/stats_popout.py`) — migration helper called at the top of `_HudLayoutDialog.__init__` before `deepcopy`. Any metric ID missing from the saved config is back-filled with `True` before checkboxes are built, making future metric additions safe without a version bump.

## v1.4.4

- **Splitter state save/restore fixed** — reverted the 1.3.8 over-fix that always wiped panel sizes on every rebuild. `_rebuild_connect_panels` now passes the normalized `saved_sizes` dict back to `save_connect_panel_prefs` (corruption guard already cleaned it to `{}` when needed) and uses the `use_default_sizes` flag from `_normalize_connect_launch_prefs`. Result: drag-to-resize heights are restored on every normal relaunch; corrupted states still boot from defaults.
- **"Run bridge" panel cap raised** — `_PANEL_EXPANDED_CAP["run"]` raised from 72 → 120 px so the Start/Stop buttons + Fan-out checkbox aren't cramped on first-launch defaults.
- **Status bar anchored** — `self.statusBar` now has `Expanding × Fixed` size policy and explicit `stretch=0` in the outer VBox, ensuring it is always pinned to the bottom of the window regardless of splitter sizing.

## v1.4.3

- **UDP Mode toggle UI** — "Fan-out — send serial data to all UDP peers" checkbox added to the Network (UDP listen) section of the Connect tab. Checked = fan-out to all registered peers (new default); unchecked = single-link, replies only to the most recent sender (legacy behaviour). Setting is saved per-preset and restored when a preset is loaded.
- **`bridge_core.SerialNetBridge`** — new `udp_fanout: bool = True` constructor parameter; `_send_net` branches on `self._udp_fanout` to select fan-out vs single-link path.
- **Tests** — 3 new cases in `test_udp_fanout.py`: single-link sends only to `last_udp_addr`, single-link with no addr sends nothing, default constructor has fan-out enabled.

## v1.4.2

- **UDP fan-out (one COM → many network clients)** — in `UDP_LISTEN` mode the bridge now tracks every UDP sender that contacts it during a session (`_udp_peers: set`) and forwards the serial→net stream to all of them simultaneously. Previously only the most-recent sender received serial data. Key behaviour:
  - First new peer shows `peer <addr>` in the network status label; additional peers show `N peers`.
  - If `sendto` fails for a peer (e.g. ICMP unreachable), that peer is silently pruned from the fan-out set; remaining peers continue receiving.
  - `abort_now` / Stop clears the peer set so the next session starts fresh.
  - `UDP_REMOTE` and TCP modes are unchanged (single-endpoint, no fan-out).
  - New `udp_peer_count` property; `udp_peers` key added to stats dict.
- **Tests** — `test_udp_fanout.py`: 12 new tests covering peer registration, multi-peer send, dead-peer pruning, remote-mode isolation, abort cleanup, and stats emission.

## v1.4.1

- **Native scrolling restored** — nuked the entire manual geometry-toggle system in `connect_panels.py` that was the root cause of clipping and scrollbar breakage:
  - `_sync_connect_panel_scroll_geometry` now only **releases** previously-applied Fixed height locks (scroll, page, tab) and re-applies `Expanding × Expanding` on the scroll area — it never pins anything to a content height.
  - `_reflow_connect_panel_host` replaced: all `sole_expanded` / `in_scroll` / `setFixedHeight` branching removed; host and splitter are always set to `Preferred × Minimum` and released from any prior lock.
  - `_set_connect_tab_stretch` always uses stretch=1 — the old `compact→0` path was zeroing the scroll area out of the layout entirely.
  - `panel_scroll` construction now explicitly sets `Expanding × Expanding` policy so no subsequent call can accidentally override it.
- **Top-alignment preserved** — `page_lay.setAlignment(AlignTop)` and `addStretch(1)` already ensured panels stack from the top; the cleanup ensures this is always restored after any geometry flush.
- **Test updated** — `test_sync_scroll_compact_height` and `test_sync_scroll_geometry_reapplies_when_signature_same` reflect the new lock-release contract.

## v1.4.0

- **Panel expand clipping fix** — `DisclosureRow._set_expanded(True)` now releases the row's own `maximumHeight` cap (`setMaximumHeight(WIDGET_SIZE_MAX)`) before making the body visible. Previously the row stayed clamped at 44 px while the body tried to render, causing content to paint underneath the splitter handle until the deferred reflow timer fired.
- **"Tools" chip removed from ribbon** — the top utility ribbon no longer creates or registers a "Tools" chip for Standard layout (it has a dedicated Tools tab instead). Field layout is unaffected — the chip is still created and wired to `_drawer_btn` there. Drawer-sync code now uses `getattr(self, "_survey_btn_tools", None)` so it is safe on any layout.
- **Reverted `load_top_bar_prefs` default-hidden approach** — prefs loading is back to the original clean implementation; ribbon visibility is now controlled structurally (chip not created) rather than via a hidden pref.

## v1.3.9

- **Collapse-all 0 px fix** — `_apply_connect_splitter_sizes` now clamps every slot to `_COLLAPSED_STRIP_HEIGHT` before calling `splitter.setSizes()`, preventing Qt from distributing below widget minimums when available height is tight. "Collapse all" also flushes the QScrollArea geometry via timer so the area compacts immediately.
- **Full header bubble clickable** — `DisclosureRow` button now uses `Expanding × Fixed` size policy so it fills the entire header strip width; `PointingHandCursor` is set on hover. Clicking anywhere on the panel header title bar now toggles it.
- **Toolbar buttons right-aligned** — Connect toolbar `addStretch(1)` moved to the front of the layout, pushing UI editor / Expand all / Collapse all / Reset sizes flush against the right edge.
- **Run bridge panel cleanup** — removed the "Bench pair setup…" button; Start bridge and Stop bridge are now capped to 200 px wide with a trailing stretch so they stay left-aligned and compact at any window width.
- **Standard layout chip bar defaults** — "Tools" and "UI editor" chips are hidden by default on first launch (Standard mode) since the Tools tab and Connect toolbar already cover both functions. Users can restore them via the UI editor.
- **Window freely resizable** — confirmed no `setFixedSize` anywhere on `BridgeWindowStandard`.

## v1.3.8

- **Ghost-state splitter fix** — Connect tab panels no longer crush to 0 px on boot from a corrupted saved layout. `_rebuild_connect_panels` now always boots with default geometry (`use_defaults=True`) and clears the prefs sizes dict on every rebuild, so stale values can never override `setMinimumHeight` constraints. Drag-to-resize still persists new sizes for "Reset sizes" baseline; they are simply not re-applied on next launch.
- **`_normalize_connect_launch_prefs` hardened** — added an explicit any-zero/any-negative guard in addition to the existing all-at-strip-height check; either condition now wipes the saved sizes dict before it can reach `splitter.setSizes()`.

## v1.3.7

- **3-tab Standard layout** — reduced top-level tabs from 8 down to 3 (Connect, Log, Tools); Presets, NMEA, Terminal, Diagnostics, Theme, and Guide now live inside a clean sidebar-nav + stacked-page Tools drawer, eliminating tab overload.
- **Greedy button fix** — Start bridge / Stop bridge / Bench pair setup buttons now use `Expanding × Fixed` size policy with enforced minimum heights so they resize horizontally but never stretch vertically inside the Run bridge panel.
- **Connect tab scroll & anti-squish** — every splitter panel gets a hard minimum height floor (preventing 0-pixel collapse), and the scroll area is stretch-weighted so it grows to fill available space on large monitors.
- **DPI scaling cleanup** — removed conflicting `ctypes.SetProcessDpiAwareness` call; Qt6-native env vars (`QT_AUTO_SCREEN_SCALE_FACTOR`, `QT_ENABLE_HIGHDPI_SCALING`) are now set before `QApplication` construction, fixing Windows taskbar shrink on launch.
- **Top-bar box model** — replaced CSS `margin` on clickable buttons with `padding` (larger hitboxes); removed rigid `max-height` constraints; layout now uses `setSpacing` / `setContentsMargins` for breathing room.
- **UI editor resilience** — `_apply_tab_visibility` and `_apply` wrap rebuild calls in `hasattr` + `try/except`; `ordered_checked()` strict-None guards prevent crashes on dynamic drag.
- **Tools sidebar styling** — `QListWidget#toolsNavList` gets themed background, border-right separator, and hover/selected states in both dark and light themes.
- **Test update** — `test_standard_has_theme_tab` updated to assert Theme lives inside the Tools sidebar nav rather than as a top-level tab.

## v1.3.6

- **UI review polish** — product demo steps open the **Terminal** tab reliably (`send`/`terminal` aliases); Field **Ctrl+L** focuses the live log when the log panel is always visible; UI editor copy and tooltips are layout-aware (Standard vs Field Tools tabs).
- **Field UI editor** — **Tools tabs** page for hiding/reordering drawer tabs (Presets, NMEA, Terminal, …); tab visibility apply uses `_drawer_tabs` for Field instead of main window tabs.
- **Top-bar migration** — `migrate_topbar_order()` now delegates to `normalize_topbar_order()` so legacy chip cleanup stays in one place.
- **Tests** — demo tab aliases, tools_tabs hidden-tab prefs roundtrip, migration parity.

## v1.3.5

- **Removed Hidden top-bar chip** — the dedicated **Hidden** tile is gone from the survey bar; tab hide/restore now lives on the tab strip (right-click a tab to hide, right-click empty tab-bar space to restore hidden tabs, or use **UI editor → Main tabs**).
- **Top-bar migration** — saved layouts that still reference the old `hidden_tabs` chip are cleaned up automatically on load.

## v1.3.4

- **Connect Serial section no longer falls back to white on some PCs** — Standard layout Connect panels (`Serial & network`, inner Serial/Network group boxes, and scroll viewport) now force styled backgrounds on Windows so green/dark surfaces render consistently in packaged builds, not just on dev machines.

## v1.3.3

- **High-contrast dialog guardrail** — added an app-wide contrast stylesheet for `QMessageBox` and tooltips so startup/bridge-failure dialogs no longer show low-contrast text on light backgrounds.
- **Theme-safe application of contrast rules** — contrast guard is now re-applied on theme changes from shared UI logic, keeping warnings/errors readable across Standard/Field/Minimal/Log-first and random theme variants.
- **Regression coverage added** — new tests lock in global contrast guard injection and idempotent re-application behavior.

## v1.3.2

- **Frozen Diagnostics scripts restored** — PyInstaller spec now bundles Diagnostics helper scripts (`check_setup.py`, `com_free.py`, `verify_all.py`, TCP/UDP bench helpers, and related runtime tools) so Bench/Boat checklist and Automated checks run from the downloaded zip build.
- **Frozen guide availability fixed** — `docs/` is now included in one-folder releases so Bench setup guidance and in-app operator guide links resolve in packaged deployments.

## v1.3.1

- **UI workflow polish shipped** — Connect panel stability improvements and UI editor/log-view/top-bar tooling are now committed together with targeted regression tests for collapsibles, field strip sizing, top-bar chips, log filtering, and editor behavior.
- **Launcher reliability pass** — launcher and Windows launch scripts now run with safer cwd/interpreter handling and no-console subprocess helpers for smoother GUI startup and diagnostics scripts.
- **NTRIP mux hardening** — serial correction injection now uses a write lock to avoid write interleaving under concurrent bridge/NTRIP traffic, with benchmark helper and parser-tail test coverage.

## v1.3.0

- **Backend runtime invariants hardened** — UI timer/chip code now uses object-safe bridge-running checks, eliminating `bridge.running` attribute tracebacks during mixed test/mocked UI states.
- **Startup self-check line added** — app logs a single startup line with version, active UI mode, and effective prefs/config paths for faster field diagnostics.
- **Prefs schema/versioning introduced** — `ui_prefs.json` now tracks `schema_version` with migration hooks (including Connect toolbar order backfill) and recovers cleanly from malformed JSON.
- **Release gates tightened** — `verify_all.py` now fails the run when traceback markers appear in subprocess output even if return codes are zero; `build.ps1` enforces `verify_all` before packaging.
- **Packaging reproducibility artifacts** — `release.ps1` now emits a build environment lock snapshot (`pip freeze` + tool versions), plus a release manifest with SHA-256 checksums/sizes for exe+zip and includes both files in GitHub releases.
- **New consistency tests** — added deterministic bridge mode start/stop cycle tests, queue-pressure counter invariants, traceback-gate tests, and prefs schema recovery migration tests.

## v1.2.50

- **Collapsed Connect labels visible again** — increased collapsed strip height to match rounded header padding so section text/arrows remain readable when rows are collapsed.

## v1.2.49

- **Collapsed Connect reassurance text** — each collapsed Connect section title now includes a short purpose hint so operators can identify sections without expanding all.
- **Bench setup hide now hides buttons** — checking “Hide this setup window next time” now hides Bench pair setup buttons in Standard and Diagnostics after close/startup instead of leaving a no-op button.
- **Hidden tabs menu: Show all** — added a one-click “Show all hidden tabs” action.
- **Guide tab + Demo sync** — added a transparent Guide tab (main tab in Standard; drawer tab in Field/log-first/minimal), shortened Traffic/quality legend toward quick health read, and updated Product Demo to point at Guide for truthful strengths/limits/current focus.
- **Connect toolbar button order** — `UI editor… / Expand all / Collapse all / Reset sizes` can be reordered in `UI editor → Connect toolbar` and persisted.

## v1.2.48

- **Bench setup dialog hide toggle** — added a bottom checkbox to hide the Bench pair setup window on future runs while still running preflight scripts.
- **Reorder Connect toolbar buttons** — `UI editor… / Expand all / Collapse all / Reset sizes` order is now configurable via **UI editor → Connect toolbar** and persisted per workspace.

## v1.2.47

- **Connect iOS-card polish** — increased per-row card separation, rounded corners, and soft gradient fills for Connect disclosure headers so each section reads as a distinct card block without visual merging.

## v1.2.46

- **Connect section cards + rounded UI pass** — collapsed Connect rows now render as individual bordered cards (not a continuous strip), and core controls/chips/tabs use stronger rounded corners for a cleaner Apple-style look.

## v1.2.45

- **Top-bar chip readability** — compact chips now try readable words with smaller font before abbreviations (e.g. `Random` / `Standard` before `Rand` / `Strd`), reducing unnecessary shorthand while still preventing clipping.

## v1.2.44

- **Standard first-paint Connect fix** — added activation/show/resize/layout-request reflow hooks for the Connect tab so launch-time geometry settles automatically without requiring a manual click.

## v1.2.43

- **Connect tab auto-reflow on activation** — Standard now forces a Connect splitter/scroll geometry sync when Connect becomes active (plus startup deferred passes), removing the “clips until I click” behavior after tab navigation.

## v1.2.42

- **Standard Connect stability after tab navigation** — hardened Connect scroll/page reflow to always re-apply geometry locks and keep panel content top-aligned, preventing intermittent “floating”/clipped Connect blocks after moving around tabs.

## v1.2.41

- **Connect expand/collapse no-clip pass** — expanded rows now always honor their natural content height (saved size caps no longer force clipping), and Run/Status defaults are taller so first-open state stays readable.

## v1.2.40

- **Layout chip** — survey bar shows one **Layout** tile (not separate Standard / Field buttons). **Double-click** toggles to the other workspace; label stays «Layout» on both layouts. Stop the bridge before switching.

## v1.2.39

- **Removed inline Edit layout** — dropped the buggy live Connect canvas editor. Connect sections are back in the **UI editor…** checkbox dialog (with Top bar and Main tabs). Use **Expand all / Collapse all** and drag splitter handles on Connect for sizes.

## v1.2.38

- **Field control strip** — COM / Stopped / preset banner sit tight on launch (layout stretch at bottom, smaller default splitter pane, strip min 92px when Tools closed). Drag the bar between the log and the strip to resize; saved layouts that gave the strip >34% height reset once to the compact default.

## v1.2.37

- **Diagnostics cards** — vertical splitter between cards (drag handles like Connect): expanded sections size to content (On-screen log no longer fills the drawer), heights persist per layout, sole-open card does not absorb all slack.

## v1.2.36

- **Field layout launch fix** — restored missing `load_field_prefs` / `save_field_prefs` imports in `ui/mixin.py` so **Field** (and saved layout via `launch_bridge_gui.bat`) opens instead of exiting silently under `pythonw`.

## v1.2.35

- **Connect Edit layout** — iOS-style inline editor on the live Connect tab: per-tile Up/Down/Hide, green edit bar with Done/Cancel/Restore defaults, highlighted splitter handles. **Workspace…** opens top bar + main tabs dialog (Connect checklist tab removed). Cursor rule `100-layout-canvas-editor` tracks phased layout work; NTRIP stays on backburner.

## v1.2.34

- **UI editor Restore defaults** — no longer hides **Serial & network** and other required Connect sections (non-checkable rows were saved as hidden). Restore resets collapse/sizes and shows all sections except NTRIP by default.

## v1.2.33

- **UI editor polish** — **Main tabs** list shows tab names and short descriptions (fixed blank checkbox rows caused by empty tooltips at catalog build). All three tabs have clearer legends, styled lists, and main-tab reorder persists on OK.

## v1.2.32

- **Top bar Presets** — choosing a preset loads COM/UDP/survey fields and **starts** (or restarts) the bridge only — no automatic bench checklist. Checklists remain on **Diagnostics** (Bench / Boat checklist buttons).

## v1.2.31

- **Diagnostics cards after Presets quick-load** — collapsed cards no longer render as clipped ~0px strips (minimum header height + layout refresh on tab show). **Automated checks** expands automatically when a diagnostic script starts so output is visible.

## v1.2.30

- **Connect Run bridge layout** — after **Collapse all**, expanding **Run bridge** (or any single section) again shows full Start/Stop/Bench controls instead of crushed 26px strips; splitter heights now follow each row’s real size hint, and sole-expanded mode no longer locks the splitter with `setFixedHeight`.

## v1.2.29

- **Connect panels after Collapse all** — reopening one section (e.g. Run bridge) no longer stretches it through the whole tab with a huge empty gap; extra height is only shared when two or more sections are expanded.

## v1.2.28

- **Top bar overlap fix** — **Std** and **Layout** no longer stack on each other: the layout chip clips to its tile and switches to the single **Layout** menu when too narrow for Standard | Field buttons.

## v1.2.27

- **UI editor** — removed **Demo** from the top bar; new **UI** tile and **View → UI editor** open a workspace editor to show/hide and reorder top bar chips, Connect sections (hide NTRIP, Quick log, etc.), and main tabs. Connect tab **UI editor…** button opens the same dialog. **Restore defaults** applies a recommended survey layout.

## v1.2.26

- **Live log view** — replaced the narrow “Sentences: all / GGA only” dropdown with **log presets** (Ops, Survey GGA+RMC, Wire tap, Problems only, Debug) plus a **View…** dialog to toggle RX/TX/warnings/UI messages, every-NMEA verbosity, sentence types, and hex preview. Display-only — bridge NMEA mode stays on the NMEA tab.

## v1.2.25

- **Diagnostics cards** — expand/collapse no longer caps the whole card to a thin strip; only the body hides, with `set_expanded()` for reliable open state (same class of fix as Connect panels).

## v1.2.24

- **Send tab → Terminal** — main and drawer tabs renamed; saved tab order migrates `Send` → `Terminal`.
- **Top bar stability** — Layout chip uses a stacked Standard|Field vs Layout menu (never both); bar-wide compact hysteresis stops jitter; Shortcuts tile keeps full **Shortcuts** label in compact mode (not **Keys**).

## v1.2.23

- **Memory / freeze fix** — stopped top-bar resize layout storms and debounced Connect panel geometry updates; launch window widening runs once. Fixes runaway RAM use introduced around v1.2.17–1.2.22.

## v1.2.22

- **Top bar first impression** — on launch the window widens when needed for full tile titles; otherwise every tile uses short readable labels (**Presets**, **Hidden**, **Stats**) with no `Pr…` ellipsis clipping.

## v1.2.21

- **Field layout launch** — wider default window, balanced log/control splitter (not a huge empty log band), readable top-bar shorts instead of `Pr…` ellipses, preset hint wraps, duplicate log toolbar hidden (controls live in the bottom strip).

## v1.2.20

- **Bench pair setup** — opens a stay-open setup window with guide section 5 (no flash/auto-close from external viewers). Expands **Quick terminal**, runs preflight there, and suppresses console popups on Windows.

## v1.2.19

- **Expand all / Collapse all** — section bodies now open and close with the headers (bulk actions no longer leave panels at zero height while chevrons show expanded).

## v1.2.18

- **Connect tab dead space** — tool buttons stay fixed at the top; only the panel stack scrolls. When all sections are collapsed, the scroll region matches panel height (no huge empty band you cannot shrink).

## v1.2.17

- **Connect panel toggles** — expanding/collapsing sections no longer shrinks the main window or traps you in a short, hard-to-resize frame. Connect tab scrolls when content is taller than the viewport.
- **Window height** — if a prior build left the window very short, opening any Connect panel restores a comfortable default height.

## v1.2.16

- **Top bar labels** — no more mystery **N** / **O** tiles; narrow tiles use readable shorts (**Rand**, **Std**, **Hidden**, **Stats**, …). Full titles when space allows. Bar fills edge-to-edge.
- **Connect panel drag** — pink splitter bars between sections are easier to grab; dragging no longer gets reset by layout. Sections keep sensible heights instead of stretching Run into a giant band.
- **Main tabs** — drag tabs on the tab strip to reorder (tooltip reminder); movable flag re-applied after layout rebuilds.

## v1.2.15

- **Top bar resize** — drag the right edge of any tile (↔ cursor) to change widths; sizes persist. ⋮⋮ grip still reorders. Letter tiles (N, O, …) show full name on hover.
- **Main tabs** — more gap between Connect / Diagnostics / Log tabs.
- **Diagnostics tab** — removed bottom stretch that left a huge empty void when cards are collapsed.

## v1.2.14

- **Top bar equal-width tiles** — each chip gets an explicit computed width so the row always spans the full bar (fixes trailing empty gutter and uneven tile sizes). Full label only when it fits inside the tile; otherwise a single letter (no `Sho…` ellipsis).

## v1.2.13

- **Top bar spring fill (always)** — visible chips share the full bar width at every window size; no empty track between tiles. Full labels when each chip's share fits; centered single letter when narrow. `TOPBAR_ALWAYS_FILL_TRACK` invariant in `ui/survey_top_bar.py`.

## v1.2.12

- **Connect tab fits content** — collapsed panels stack at the top without a huge empty gap; window height shrinks on launch when everything is collapsed. Bottom filler no longer steals vertical space.
- **Connect splitter drag** — splitter grows inside the host when expanded; drag handles work (no fixed-height lock while resizing). Run/Status panels cap height so Start is not a giant band.
- **Top bar labels on wide launch** — letter tiles only when the window is actually too narrow; launch keeps full chip titles on a normal/wide desktop width.

## v1.2.11

- **Standard launch readability** — top bar no longer defaults to unreadable one-letter tiles on first paint; window opens wide enough for full labels and waits for real layout width before choosing letter mode.

## v1.2.10

- **Top bar: no clipped labels** — full-text tiles only when they fully fit; otherwise letter tiles (no overlapping/bunched chips). Hysteresis applies when growing out of letter mode only. Launch width includes a small margin.

## v1.2.9

- **Top bar resize hysteresis** — slight window shrink no longer snaps every chip to one-letter mode; full labels stay until clearly too narrow, and letter mode needs extra width before expanding back. Field/Standard open wide enough for full labels when possible (comfort width like your mid-size screenshot).

## v1.2.8

- **Fix hide top-bar chip** — hiding a chip (e.g. Copy stats) no longer leaves a ghost tile overlapping neighbors; hidden chips are removed from layout and not painted.

## v1.2.7

- **Top bar content-sized tiles** — each chip is only as wide as its label (character width + minimal border); spare space stays on the right. Fixes oversized “View” and truncated “Standard” on wide windows. Layout/Field buttons size to their text.

## v1.2.6

- **Top bar spring layout** — chips share bar width equally (expand to the right); adding/hiding chips redistributes space. Letter tiles stay centered inside each expanded chip; full titles when wide enough.

## v1.2.5

- **Top bar letter tiles** — narrow window collapses chips to v1.2.3-sized boxes with a **single letter** (View→V, Presets→P, …) instead of abbreviations or forced wide window. Wide window shows full titles. Drag grip on the right with hand cursor unchanged. Layout chip compact letter **L** opens Standard/Field menu.

## v1.2.4

- **Top bar readability** — chip text comes first; **⋮⋮** drag grip on the **right** with open/closed **hand** cursor (not resize arrows). Buttons keep full titles at normal width; abbreviate only when squeezed (tooltip keeps full name). Window minimum width grows to fit all chips; Field opens at the same readable width as Standard.

## v1.2.3

- **Draggable top bar chips** — each survey bar action is a bordered box with consistent padding; drag the **⋮⋮** grip to reorder and snap on the bar (no separate rearrange dialog). Right-click a chip to hide it; **View → Show all top bar chips** to restore.
- **Layout switch on top bar** — **Standard** / **Field** moved from Diagnostics to the far-right top bar chip (replaces Quick UI switch card).

## v1.2.2

- **Connect expand/collapse polish** — releasing fixed height when any panel expands; splitter target height uses the Connect tab (not a shrunken post-collapse splitter). Tab stretch keeps collapsed stacks at the top; expanding a section grows the host again. Disclosure toggles reflow the splitter immediately.
- **Diagnostics cards** — all sections default collapsed (including Quick UI switch and file log); closed cards use a compact strip; spare space packs below the card stack.

## v1.2.1

- **Connect tab compact collapse** — collapsed panels stack at the top with no dead space inside the splitter; **Collapse all** shrinks the panel host to strip height only. Stretch goes below the stack (not between headers). Default: only **Run** and **Serial & network** expanded; optional sections start collapsed. Removed launch logic that forced all panels open when prefs were collapsed.

## v1.2.0 — survey bridge release

**Operator-facing**

- **Standard + Field layouts** — Connect tab (collapsible/resizable panels, quick log/terminal, NTRIP phase 1), dedicated **Log** tab, survey bar (Presets, Recent, HUD, checklists).
- **Live GNSS quality** — GGA fix, satellites, HDOP on status bar and Survey HUD (POSPac Ch.16-style hints); stale detection; raw mode shows `n/a`.
- **Survey HUD** — Hz, transport/backpressure, session totals, GNSS tiles; layout persists (including box scale).
- **Operator guide** — `docs/OPERATOR_GUIDE.md` for bench/boat workflows.

**Reliability**

- Bridge asyncio thread, bounded queues, coalesced stats/logs, serial auto-reconnect, TCP client reconnect.
- Copy stats clipboard fixed; frozen EXE `version_info.txt` synced via `tools/sync_version_info.py`.
- `verify_all.py` compile excludes `dist/`; 100+ unit tests.

**Packaging**

- `.\build.ps1` / `.\release.ps1` — PyInstaller one-folder; zip `nmea-serial-bridge-v1.2.0-win64.zip`.

## v1.1.57

- **Audit fixes** — **Copy stats** uses correct bridge counters (was always zero); Windows `version_info.txt` syncs from `version.py` at build; Survey HUD **box scale** persists; **GNSS** chip shows **n/a (raw)** in raw binary mode; `verify_all` compile skips `dist/`; removed unused `qasync` dependency; NTRIP password field warns about plain-text local storage.

## v1.1.56

- **GNSS survey quality (live)** — parses GGA fix, satellite count, and HDOP using POSPac MMS Ch.16-style thresholds; shows on the **GNSS** status chip, stats bar, and Survey HUD (GNSS / Sats / HDOP tiles). Stale if no GGA for ~3 s. New module `survey_quality.py`.

## v1.1.55

- **Connect tab opens expanded** — all Connect sections start expanded by default (NTRIP and Quick terminal no longer start collapsed). Saved “collapse all” / strip-only sizes are reset on launch so the splitter fills the tab sensibly.

## v1.1.54

- **Connect panel sizes** — collapsed sections snap to a minimal strip height; expanded heights are remembered separately so reopening a panel restores your last size (drag-resize and collapse no longer overwrite saved heights with the strip size).

## v1.1.53

- **Connect collapse/expand fix** — panel toggles no longer call `adjustSize()` on the whole window (that was breaking the vertical splitter layout).
- **Bench pair setup fix** — stays on **Connect**, expands **Quick terminal**, opens the operator guide via desktop/`startfile` fallback, and runs preflight without clearing terminal output or forcing a jump to Diagnostics.

## v1.1.52

- **Resizable Connect panels** — Connect sections now sit in a vertical splitter: drag the handles between Run, Quick log, Quick terminal, Serial & network, NTRIP, etc. Sizes persist across restarts; **Reset sizes** restores defaults.

## v1.1.51

- **Connect tab panels** — Quick log, new **Quick terminal** (preflight output + one-line Send→COM), serial/network, NTRIP, and Run are collapsible with **Expand all / Collapse all** and **Arrange panels…** (drag reorder + default collapsed state, persisted).

## v1.1.50

- **Bench pair setup** — **View → Bench pair setup…**, **Connect** tab, and **Diagnostics** run the operator guide (bench/com0com §5) plus automated **com_free → check_setup** preflight (no kernel driver; install com0com per guide).

## v1.1.49

- **Connect tab defaults** — Standard layout opens on **Connect** with a compact **Quick log** strip for bench testing.
- **Auto Log tab** — after the bridge has been **Running** for 20 seconds, the UI switches to the full **Log** tab.
- **File log retention choices** — Diagnostics file log now offers **10 / 25 / 50 / 100 MB** per file and **3 / 5 / 10** backups, with an on-screen duration estimate (rate-dependent; RTCM/high traffic fills faster than sparse NMEA).
- **NTRIP corrections (phase 1)** — Connect tab can enable an NTRIP caster stream; RTCM is multiplexed onto COM alongside bridged network data (caster, mount, user/pass saved in prefs).

## v1.1.48

- **Log tab beside Connect (Standard)** — live log is now a **Log** tab right after **Connect** instead of a side panel, so the main window stays simpler.
- **Cleaner top bar** — removed **Show log**, **Pause log**, and **Clear log** from the survey bar; use the **Log** tab for filters, pause (if shown there), clear, and save.

## v1.1.47

- **Top bar is now customizable and positionable** — added a `Customize top bar…` manager (drag reorder + hide/show per control) and a one-click top/bottom move action, with per-layout persistence.
- **Handy keyboard shortcuts + in-app legend** — added bridge/theme/log/tab navigation shortcuts and a visible/hideable shortcuts legend panel with persisted visibility.
- **Preset quick menu now does auto test/connect** — selecting a top-bar preset now applies it, runs checklist test, and starts/restarts the bridge automatically for faster field workflow.
- **UI behavior rule codified** — added a dedicated workspace rule to keep hide/restore + reorder + crisp resize expectations enforced in future UI edits.

## v1.1.46

- **Log panel recoverability fix** — added a persistent top-bar **Show log** toggle (Standard/Minimal), so hiding the log never strands the user without a way to turn it back on.

## v1.1.45

- **Checklist preset labeling fix** — boat/bench checklist log lines now report the actual preset profile used (including fallback), avoiding misleading “Desk test” labels on boat checks.
- **Boat checklist preset safety** — when a non-boat active preset is selected, boat checklist now explicitly falls back to production profile args and marks that fallback.

## v1.1.44

- **Stronger zone separation** — updated zone tinting so tabs and buttons adopt their assigned zone hues more aggressively (less same-color blending), improving visual differentiation across the UI.
- **Tab hide UX** — right-click tab hide + top-bar Hidden tabs restore flow is now active and persisted.

## v1.1.43

- **Checklist preset alignment** — Bench/Boat checklist actions now resolve from the active saved preset first, so diagnostics run against the same settings you selected in the UI.
- **Tab hide/restore control** — tabs now support right-click **Hide tab** and a new top-bar **Hidden tabs** menu to restore hidden tabs.

## v1.1.42

- **Copy stats now exports real snapshot data** — replaced tooltip/help-text copying with a structured runtime snapshot (state, preset, serial/network settings, NMEA mode, status chips, wire Hz, drops/rejects, and session totals).

## v1.1.41

- **Checklists now use the active saved preset** — Bench/Boat checklist actions resolve the currently selected saved preset first (with production fallback only when required), so diagnostics align with your preset settings across tabs/layouts.
- **Checklist visibility feedback** — launching a checklist now writes an explicit UI log line naming the preset being used, making it clear the action fired.

## v1.1.40

- **Readable zone swatch labels** — zone color hex values now auto-select light/dark text for contrast and use a clearer monospace style so color codes stay legible.
- **Standardize button behavior upgrade** — single click still applies stable Field Slate, while a **double-click** now generates a new cohesive standardized variant (uniform palette family with low chaos).

## v1.1.39

- **Drag-everything pass (phase 2)** — main tools tabs are now movable with per-layout persisted order (`main_tabs` and `tools_tabs`).
- **Diagnostics card ordering** — added a `Reorder cards…` manager in Diagnostics with drag ordering that persists per UI mode.
- **Persistence coverage expanded** — added stored order for connection presets, recent sessions (plus pinning), diagnostics cards, theme zones, and tab strips so rearrangements stick across restarts.

## v1.1.38

- **Top-bar theme safety toggle** — added **Standardize theme** next to Randomize for one-click return to a stable slate look.
- **Drag-everything pass (phase 1)** — connection Presets list is now drag-reorderable with persistent order; Recent sessions now have a drag+pin manager; Theme zone rows are drag-reorderable for faster editing flow.

## v1.1.37

- **Drag-reorder for theme presets** — the saved Theme preset list now supports internal drag/drop reordering, and order persists across restarts.
- **Preset order persistence backend** — added explicit stored ordering for theme presets so manual arrangement is kept instead of alphabetical sorting.

## v1.1.36

- **Top-bar randomize button** — added **Randomize theme** to the survey bar for one-click palette changes during use.
- **Named theme presets** — Theme tab now has a saved preset list with **Save as preset**, **Load**, and **Delete**, so favorite looks live in-app with names (no clipboard workflow).

## v1.1.35

- **Theme pack export/import** — Theme tab now includes **Export theme pack…** and **Import theme pack…** to share and restore full zone color sets (plus seed-lock state) as JSON.
- **Share-ready fun themes** — imported packs apply immediately to `Randomized (current)` and can optionally include favorite-zone colors for quick reuse.

## v1.1.34

- **True multi-zone random themes** — randomize now generates distinct colors per UI zone (background, top bar, tabs, buttons, inputs, log panel, accent) so the app no longer stays in one monochrome family.
- **Per-zone color assignment** — Theme tab now exposes assignable swatches for each zone with color picker + reset, then applies the result instantly as `Randomized (current)` and supports saving that as favorite.

## v1.1.33

- **Theme polish / less monotony** — layered gradients now separate the window body, top survey bar, and default buttons so each area reads as a distinct surface instead of one flat color block.
- **Theme tab glow-up** — added dedicated Theme Studio styling (carded section, stronger hint/tip contrast, and distinct randomize/favorite button treatments) for a more playful feel without taking extra main workflow space.

## v1.1.32

- **Theme moved to dedicated tab** — removed the View → Theme menu to keep the survey bar uncluttered; all theme controls now live in a **Theme** tools tab across Standard, Field, Log-first, and Minimal layouts.
- **Theme tab includes everything** — base themes, randomize, favorite-save, and lock-seed controls are grouped in one place without consuming main run/connect space.

## v1.1.31

- **Seed lock for random themes** — View → Theme now has **Lock random seed (same vibe)** so Randomize follows a deterministic style family instead of jumping wildly each click.
- **Deterministic variation sequence** — when lock is on, each Randomize click advances to the next saved variant in that family (repeatable across restarts).

## v1.1.30

- **Theme randomizer** — View → Theme now includes **Randomize** to generate a wild one-off palette, plus **Randomized (current)** and **Favorite random** modes.
- **Favorite save** — added **Save current random as favorite** so a good randomized palette survives restart and can be re-applied later.

## v1.1.29

- **Presets menu (survey bar)** — clicking **1** or any preset now runs after the menu closes (fixes lost clicks on Windows); checkmark moves even while the bridge is Running (survey fields update; COM/UDP apply on Stop).

## v1.1.28

- **Presets click fix** — `itemClicked` handler (works inside scroll area / on Windows); survey bar Presets menu and list share `_activate_preset_by_name`; preset **1** and other short names load reliably; list row stays in sync with active preset.

## v1.1.27

- **Presets tab** — visible list selection (gold/maroon highlight); single-click loads preset when stopped; Load/Save/Delete enable states match bridge state; programmatic list updates no longer steal clicks.

## v1.1.26

- **Backend** — `verify_all.py` runs full `unittest discover` (all `test_*.py`); `check_setup` copy matches Presets/Checklists workflow; recent-session + minimal drawer prefs tests.
- **UI sweep** — compact intent hint styling; screenshot-friendly `objectName`s on presets/diagnostics; Standard min size; checklist actions focus Diagnostics; operator guide shot list rewritten for current UI.

## v1.1.25

- **Deep UI pass** — Field/Log-first/Minimal show a one-line **intent hint** (full text on hover); Minimal uses a tools drawer like Field with prominent Start/Stop. Survey bar **Checklists** menu (bench/boat preflight). Product demo and **OPERATOR_GUIDE** updated for Presets/Recent (no Desk/Boat buttons). TCP setup in demo points at Presets → Advanced.

## v1.1.24

- **Tab audit** — Standard Connect keeps Advanced network (no longer stolen by Presets tab); intent hint pinned above scroll; correct tab tooltips. NMEA strict sentence grid disables unless Strict is selected. Diagnostics TCP demo disables with other runners; drawer tabs renamed consistently.

## v1.1.23

- **GSOF removed** — dropped Trimble GSOF simulator (`gsof_codec.py`, `bench_gsof_survey.py`), Diagnostics **GSOF survey** button, and `docs/TRIMBLE_GSOF.md`. **Raw binary** mode remains for RTCM and other non-NMEA byte streams.

## v1.1.22

- **Raw GSOF log** — never decodes binary as text (avoids BEL/`0x07` beeps on Windows); verbose raw log always uses hex preview.
- **Status bar** — fixed height, stable elide width (no resize grow/reset loop); strip control chars from live log lines.

## v1.1.21

- **Diagnostics layout** — fixed tab blowing up when running bench scripts: capped output height, removed scroll-area stretch, status bar stays single-line (elided text + tooltip).

## v1.1.20

- **GSOF USV survey simulator** — Diagnostics **GSOF survey (UDP)** runs `bench_gsof_survey.py`: Trimble GENOUT (0x40) with **Time (1)**, **LLH (2)**, **Velocity (8)** at **5 Hz**, **~2 m/s** along a small box track. Requires **NMEA → Raw binary** and bridge **Running** on UDP listen. New `gsof_codec.py` + tests.

## v1.1.19

- **Survey HUD** — removed scale (50–150%) and column (Auto–4) dropdowns; layout is fixed at **100%** scale and **6** columns. Corner/Readable presets updated to match.

## v1.1.18

- **Named presets** — **Presets** tab replaces Desk/Boat buttons: load, save, save as, new, delete; custom names stored in `path_presets.json` (legacy desk/boat entries migrate automatically).
- **UI cleanup** — removed survey-bar Desk/Boat/COM/Preflight; **Net** tools tab removed (TCP/advanced network lives under Presets); **COM probe** removed from Diagnostics.

## v1.1.17

- **Bridge terminal (lite)** — live log **Save…** export; **Hex (raw)** preview for GSOF/RTCM when Raw binary + verbose; **Sentences** filter (all / GGA / RMC / GGA+RMC) with “Every NMEA line”.
- **Status bar** — **NMEA** chip (passthrough / strict / raw + running state) beside Serial and Network on Standard and Field.
- **Recent sessions** — survey bar **Recent** menu restores last 5 COM + UDP + NMEA combos (`ui_prefs.json`).

## v1.1.16

- **Serial auto-reconnect** — optional (default on): retry COM every 2 s after disconnect while bridge keeps Running.
- **NMEA → Raw binary (GSOF / RTCM)** — byte passthrough without line assembly; see `docs/TRIMBLE_GSOF.md`.
- **Docs** — README and `docs/OPERATOR_GUIDE.md` updated (network, Trimble, demo, layouts, troubleshooting).

## v1.1.15

- **Product demo** — **Stop auto** fully resets (orphan timers, stuck Auto chip, diagnostics process left “running” blocking TCP demo reload). Reopening Demo recovers a half-stopped presenter window.

## v1.1.14

- **Product demo** — **Manual pitch mode by default**: Prev / Next / Run selected step enabled on open; click the list to jump; **Auto-play script** is optional. Green **Next step** is the primary control.

## v1.1.13

- **Product demo** — Stop no longer locks **Next step**; use it to walk the script manually after aborting auto. Stop no longer shows “Demo complete” mid-run.

## v1.1.12

- **Product demo** — default **6s** hold per step (was ~3s on many beats); five new steps (survey bar, Tools/NMEA, wire Hz, HUD readout, Diagnostics, Preflight); step counter and `Ns of Ms` countdown.

## v1.1.11

- **Product demo** presenter UI: teleprompter card (large title, green cue, narration), phase-grouped step list, progress bar, countdown + **Next step**, **Stay on top**, dedicated warm theme; **Run automated demo** unchanged.

## v1.1.10

- HUD **From COM** wire Hz: coalesce rapid serial read bursts (com0com echo) so bench TCP demo tracks **Into COM** more closely; tooltips clarify wire Hz vs session sentence totals.

## v1.1.9

- **Product demo** — survey bar / View -> **Product demo**: ~6–8 min scripted walkthrough (UDP burst, Survey HUD, TCP map motion, Send, Boat preset) with on-screen narration for presenters.
- **TCP demo (~4 min)** — Diagnostics button + `bench_tcp_stress.py --demo` (fast LA legs, auto-stop); for live Hypack/chart motion without a 30 h soak.

## v1.1.8

- **TCP stress** drains inbound TCP while sending so long runs do not fill the COM→net queue (Transport **Warn** / `DROP s->n`).

## v1.1.7

- **TCP stress** — `bench_tcp_stress.py` + Diagnostics **TCP stress (LA→Sac)**: 5 sentences/tick @ 5 Hz, ~5 m/s from Los Angeles toward Sacramento; auto-reconnect; route resets at LA each session. Use **Stop** to end.

## v1.1.6

- **Survey HUD** — no more tiny “ghost” window on open: frameless flags set at creation, layout/size applied while hidden, invalid saved geometry discarded (< 420×168).

## v1.1.5

- Layout picker: disclosure sections (**About**, **Details**) collapse without leaving empty dialog space (`SetFixedSize` + reflow on toggle).
- Shared `ui/collapsible.py` for disclosure rows; diagnostics collapsible cards use zero-height collapse.

## v1.1.4

- **Windows** — Diagnostics / Preflight / Full verify no longer flash `python.exe` console windows (GUI uses `pythonw`; nested `verify_all` steps use `CREATE_NO_WINDOW`).
- Survey bar **HUD** uses a single **Survey HUD…** action (no duplicate shortcut wiring).

## v1.1.3

- Fix layout picker crash (`UI_FIELD` import) that made `launcher.py --pick-ui` / `pythonw` launches show no window.

## v1.1.2

- Layout picker: readable OK/Cancel buttons; “Remember” defaults **off** (clears saved choice when unchecked); collapsible **About** and per-layout **Details**; Field pre-selected when nothing saved.

## v1.1.1

- **Launcher / picker** — Standard + Field only; descriptions in console menu and first-run dialog; legacy `minimal` / `logfirst` choices auto-migrate to `field`; `launcher.py --ui field|standard` and `--pick-ui`.

## v1.1.0

- **Field UI** — merged Minimal + Log-first into one layout (large log, compact connect, tools drawer); launcher offers **Standard** + **Field** (saved `minimal` / `logfirst` map to Field).
- **Survey quick bar** — Desk, Boat, COM refresh, HUD, Tools, Pause log, Clear log, Preflight menu, Copy stats beside **View**.
- **Hz** — status shows **wire** update rate (UDP datagram / serial read per second), not NMEA sentences per second; session totals still count sentences.
- **Field log UX** — log presets with per-option hover help; font dense/readable applies to log; **Every NMEA line** label; smaller default window (720×520).
- Network fields editable while stopped; queue backlog threshold aligned with bench probe; generic GGA sample (DPT not DBT); flow/backpressure wording fixes.

## v1.0.0

- First stable release package for distribution (`nmea-serial-bridge-v1.0.0-win64.zip`) with Standard/Minimal/Log-first UI workflows, survey HUD popout, diagnostics improvements, and release tooling for repeatable drops.

## v0.5.12

- **View** menu on all layouts: **Full screen** (F11) with friendlier splitter ratios on large displays; **Pop out survey stats** (Ctrl+Shift+S) — large, optional always-on-top window for Hypack / multi-monitor survey ops (Cube COM NMEA path vs MAVLink called out in UI copy).

## v0.5.11

- `verify_all.py` imports are complete on a fresh clone (`py_interpreter`, extra tests).
- Skip `com_free` / headless / stress when the bench UDP port is already bound (bridge GUI running); `VERIFY_ALL_NO_SKIP=1` forces the full suite.
- Shared `ui/stats_line.py`, serial timeout log coalescing, and tests for stats line / log / survey contract.
- Bench stress uses the same Python executable selection as other scripts.

## v0.5.5

- Live bridge stats in the UI (rolling Hz, inject rate, session line counts) plus tooltips.
- `bridge_core` counters/metrics and `test_bridge_metrics`; `verify_all` runs that test.
- Desktop/launcher shortcuts and `launch_bridge_gui_menu.bat`; `_gen_mixin.py` for shared UI mixin code.

## v0.5.2 and earlier (see git)

- Multi-UI layouts (Standard / Minimal / Log-first), launcher picker for frozen exe, README bench/boat workflow (`c881cfa` and neighbors).

---

**Documenting a new drop:** bump `version.py`, commit, add a section above, then:

- `.\release.ps1` — build + zip under `dist\`
- `gh auth login` — once per PC that publishes
- `.\release.ps1 -Publish` — tag + GitHub Release + upload zip  
  If publish failed after a successful build: `.\release.ps1 -PublishOnly` (no PyInstaller rerun).

**Many PCs:** they only download the **Release zip** from GitHub (or you copy `dist\…zip`); no clone required on those machines.
