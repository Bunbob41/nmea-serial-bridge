# Changelog (personal progress)

High-level notes for **this fork / branch** (`2034-ui-journey-modernization` and descendants).  
 Version = `version.py` / Git tag when you run `.\release.ps1` or tag manually.

---

## v1.41.10

- **TCP serve loops** — `_serve_tcp_forever` / `_serve_tcp_sink_forever` tolerate test doubles that lack async context manager protocol; fixes CI `TypeError` on `_DummyServer`.

## v1.41.9

- **Linux headless (Phase 1)** — `serial_link_headless.py` runs `bridge_core` + existing web dashboard (port 8765) without PySide6; `headless_facade.py` and `headless_bridge_runner.py` back the same REST API as desktop.
- **No Qt in bridge_core import path** — `BridgeAsyncThread` moved to `bridge_qt_thread.py`; shared web DTOs in `web_facade_types.py` so Linux installs skip PySide6.
- **Packaging** — `requirements-linux-headless.txt`, `docs/LINUX_HEADLESS.md`, `packaging/linux/` (install, run, systemd unit, release tar script); CI `linux-headless` job builds `serial-link-vX.Y.Z-linux-headless.tar.gz`.
- **Spec** — `specs/011-linux-headless-bridge/` (FR-501–509, single-node, tar.gz delivery).

## v1.41.8

- **Operator copy** — replaced Trimble/R10 references in UI and docs with **professional GPS unit** (USB auto-detect keywords unchanged).
- **Top-chips status capsule** — removed the 220px max-width cap; status pane now keeps a readable floor so **stopped** no longer clips to **Stoppe…**; protected capsule titles never elide mid-word.

## v1.41.7

- **GitHub releases** — release notes generated from `CHANGELOG.md` via UTF-8 `--notes-file` (fixes em-dash mojibake on release pages); CI installs Pillow and uses Qt offscreen for GUI smoke.

## v1.41.6

- **CI verify_all** — GitHub Actions skips COM/com0com hardware benches (`com_free`, headless, stress, network, fanout); full suite still runs locally. Set `VERIFY_ALL_NO_SKIP=1` to force hardware steps.

## v1.41.5

- **Fluid header layout** — replaces rigid auto-arrange with a multi-pass engine: measure true minimums, compress Start padding under pressure, keep status/trail readable (lowercase `stopped` capsule + state dot), and scroll chips instead of clipping text.
- **View menu** — HEADER BAR section (chip display, icon customize, manual resize) hides when Tools navigation is Sidebar; chip display picks reliably refresh the top chip rail.
- **Phone dashboard icon** — moved from the crowded chip zone into the View/HUD/Layout cluster on the right.

## v1.41.4

- **Control → Network path** — Advanced network panel scrolls inside the card and expands with the column so TCP server/client fields no longer clip.

## v1.41.3

- **Theme quick pick** — right-click **Theme** in the Bench Tools dropdown (or sidebar) to apply a built-in palette or saved preset without opening Theme studio.

## v1.41.2

- **Activity toolbar height** — removed 40px `max-height` cap on the wire terminal toolbar so the transport row (Serial / UDP / Session) is no longer clipped under the filter bar or log pane in windowed and fullscreen layouts.
- **Compact status chip** — flatter compact banner (no left border / pill radius) and explicit `● Stopped` prefix so it no longer reads as `( Stopped )`.

## v1.41.1

- **Modern header launch** — compact status shows **Stopped** only (detail in tooltip); safer elision avoids `| (` garbage on first paint; chip rail separator uses CSS border instead of a stray VLine widget.
- **Activity transport row** — Serial / UDP / Session pills on their own row under filters; UDP dropdown arrow hidden until peers register.

## v1.41.0

- **Transport truth** — separates **Running** (Start→Stop), **COM data active** (serial bytes toward the network), and **UDP peer last seen** (inbound datagram age). Activity strip pills, Modern health chip suffix, Stop log summary, Mission Review duration tooltip, and web dashboard monitor rows (`session_running_s`, `com_active_total_s`, `last_com_to_net_age_s`, `udp_peer_newest_in_s`) all read the same bridge stats.

## v1.40.20

- **Header status elision** — child-owned defer timers, reentrancy guards, and safe teardown so full unittest runs no longer recurse or crash Qt shutdown on Windows.
- **Bluetooth SPP (docs)** — bookmark `docs/BLUETOOTH_SPP_WINDOWS.md` for Windows incoming/outgoing COM pair behavior (Sonarmite field note; companion-outgoing feature deferred).

## v1.40.19

- **Field layout raw / MAVLink log** — live log now shows binary wire traffic (hex) in Raw mode; fixes thread-unsafe verbose check that suppressed all traffic lines on Field.

## v1.40.18

- **Field layout launch** — hide orphan serial-mirror COM pickers that floated over the top-left View chip (only shown on Modern → Control).

## v1.40.17

- **UI editor chip order** — Navigation tab reorder now updates the top chip rail (sidebar still keeps group headers contiguous).

## v1.40.16

- **Chip display menu fix** — View → Chip display no longer shows two modes checked at once; picking Icons only / Labels only / Auto reliably applies (Qt `triggered` on uncheck was reverting the mode).

## v1.40.15

- **Modern header bar (View menu)** — **Auto-arrange header** sizes Start, status, chips, and View/HUD/Layout when the window or bridge state changes (no manual drag each resize). **Chip display** submenu: Auto / Icons only / Labels only. **Customize chip icons…** imports JSON per `docs/HEADER_CHIP_ICONS.md`; reset restores product defaults.

## v1.40.14

- **Modern header Start clip** — Run splitter pane min width now fits the Start/Stop button (was 90px); added gap before compact status pill so Start no longer overlaps the Stopped chip after resize or saved header splits.

## v1.40.13

- **Repo hygiene (PR 1)** — Dated inventory at `docs/repo-hygiene-inventory.md`; removed dead `_gen_mixin.py` and `_patch_guide.py`; moved 104 `test_*.py` files to `tests/` (discover path updated in CI, `verify_all`, `run_unittests`).

## v1.40.12

- **P0 frozen launch crash** — `serial-link.exe` (`console=False`) sets `sys.stderr` to `None`; startup called `stderr.isatty()` and crashed after the window appeared. Guard via `stream_isatty()` and `_should_minimize_launch_console()`.
- **QC** — New `tools/gui_no_console_check.py` step in `verify_all.py`; regression tests in `test_bridge_gui_no_console.py`. Release builds run `tools/frozen_gui_smoke.py` on `serial-link.exe` before zipping.

## v1.40.11

- **GitHub repo polish** — README hero (download badge, Modern + Field layouts), CI workflow on `main`, `.gitignore` for dev scratch files, repo About metadata (description, topics, latest release link), unpinned template flag.

## v1.40.10

- **Fleet UDP listen / Tailscale** — Fleet edit dialog exposes **UDP listen host** (default `0.0.0.0` for LAN + Tailscale). Port conflicts now treat `0.0.0.0` and `127.0.0.1` as overlapping on the same port. Network column tooltips and MAVLink preset copy explain remote Mission Planner (`Tailscale IP:14550`, firewall). Control ↔ Fleet UDP conflict checks use the same host-overlap rules.

## v1.40.9

- **Header chip overflow** — Hidden horizontal scroll (mouse wheel) plus subtle left/right edge fades when more chips sit off-screen — no drag bar, full labels preserved.

## v1.40.8

- **Header chip scroll** — Removed the visible horizontal drag bar; overflow chips scroll with the mouse wheel only.
- **Fleet table** — Label column no longer stretches across the window; long names elide with tooltip. Action buttons use native Qt icons (fixes empty glyph boxes). Window and table can shrink further vertically.

## v1.40.7

- **Header chip clipping** — Tool chips no longer launch with a partial left edge (`...ontrol`). Scroll resets to the start when chips fit; overflow uses chip-aligned horizontal scroll instead of `ensureWidgetVisible` mid-label clipping.

## v1.40.6

- **Launch without console** — `launch_bridge_gui.bat` and `launcher.py` spawn via `pythonw.exe` again (no terminal flash). Direct `python bridge_gui.py` auto-minimizes the console unless you pass `--foreground`.
- **Window focus fix** — Startup uses native Windows focus instead of `raise_()`, removing the “This plugin does not support raise()” warning and bringing Serial Link to the front reliably.
- **Fleet row height** — Stream table rows are shorter (compact action buttons, tighter cell padding) so COM / MAVLink labels no longer sit in oversized rows.

## v1.40.5

- **Header chips** — Labeled chips no longer crush to icon-only on launch; each chip keeps its natural width and the chip rail scrolls horizontally when space is tight.
- **Theme under Bench Tools** — Theme moved off the top chip rail into the **Bench Tools** dropdown (sidebar group unchanged).
- **Maroon palette** — Restored classic maroon & gold zone colors (`#241a1f` … `#d4af37`) instead of the magenta/purple drift from the Modern port.
- **Zone order readability** — Hex codes render in a dedicated high-contrast label beside each swatch on the Theme tab.

## v1.40.4

- **Modern header chips** — Tool-chip pane now absorbs horizontal slack on resize; tight layouts shrink trail/status before crushing the chip rail, so labeled chips return when space allows (fixes icon-only chips with empty header gap).

## v1.40.3

- **Windows launch fix** — Stopped auto-relaunching via `pythonw` (could leave invisible zombie processes). `launch_bridge_gui.bat` and `launcher.py` now detach `python.exe`; the main window is centered on-screen and brought to front at startup.

## v1.40.2

- **Windows launch** — Running `python bridge_gui.py` no longer leaves a blank terminal; the app auto-relaunches via `pythonw` (use `--foreground` to keep the console for debugging).

## v1.40.1

- **Startup lock recovery** — If a prior Serial Link crash left a stale single-instance lock, the app now clears it automatically instead of silently failing to open.

## v1.40.0

- **Theme in Modern layout** — Tools → Theme adds premade palettes, zone-order drag reorder, per-zone color pickers, saved presets, and export/import — without randomize/standardize/seed-lock controls.
- **Standard layout removed** — Workspace picker and layout cycle are **Field** and **Modern** only; legacy `standard` / `minimal` / `logfirst` ids map to Field.

## v1.39.35

- **Narrow header â€” no chip clipping** â€” Embedded tool chips now live in a horizontal scroll viewport at natural width (icon-only when tight, scroll + thin bar when overflow). Chips no longer overlap when the window is ~Â¼ screen; mouse wheel still scrolls the row.

## v1.39.34

- **Header tool chips at narrow width** â€” When the top-chips pane is too narrow for icon+label pills, tool nav switches to icon-only squares (full names stay in tooltips) instead of squished truncated text.

## v1.39.33

- **Web dashboard default grid** â€” Shipped grid layout: map + log on the left, compact status + configuration on the right, discovery/COM/tools as small bottom tiles; discovery and tools collapsed by default; layout lock and chrome prefs (hidden headers, satellite map, terminal-only log) in product defaults.

## v1.39.32

- **Web dashboard Modern parity** â€” Dashboard CSS tokens aligned with desktop `MODERN_*` palette; Maple Mono via `/static/fonts/` (same bundle as Qt); global header gradient + accent border; dark GNSS HUD badges; panel/tool button chrome; terminal log colors; favicon route.

## v1.39.31

- **Header logging chip layout** â€” Trail pane now reserves width for the red **Logging** indicator (and alerts/QR) so View/HUD/Layout are not clipped when file log is recording.

## v1.39.30

- **Ghost â€œpythonâ€ window** â€” Modern top-chips header separator was shown without a parent layout, so Qt opened it as a second top-level window (dark panel + white vertical line). Separator now lives inside the header chip host.

## v1.39.29

- **Fleet row detail** â€” Table adds **Mode** (NMEA mode, fan-out, backup) and **Mirror** (com0com legs + device TX) columns with full tooltips; COM/Network columns size to content so baud and listen ports are not truncated.

## v1.39.28

- **Fleet tab responsiveness** â€” UDP start waits now pump the Qt event loop instead of blocking with `msleep`; Start/Stop all and row actions debounce rapid clicks and refresh only affected rows instead of rebuilding the whole table.

## v1.39.27

- **Qt 6 font directory** â€” PySide6 no longer ships `lib/fonts`; app now sets `QT_QPA_FONTDIR` to `assets/fonts` before startup and seeds baseline sans/mono TTFs (Maple Mono bundle + Windows DejaVu/Segoe fallbacks) so `QFontDatabase: Cannot find font directory` no longer blocks launch.

## v1.39.26

- **Modern startup crash** â€” Header split module no longer calls `QFontMetrics` at import (before `QApplication` exists), which could abort launch on Windows.

## v1.39.25

- **NMEA backup extension** â€” Black-box session files now save as `backup_YYYYMMDD_HHMM.nmea` (legacy `.raw` still opens). Mission Review **Quick Export** opens a save dialog for `.nmea`, `.log`, or `.txt` handoff to GIS / hydro tools.

## v1.39.24

- **Header split file + Layout chip** â€” Regenerated `ui/modern_header_split.py` as clean UTF-8 (no null-byte corruption). Trail pane now enforces a computed minimum width for View/HUD/Layout so the Layout label does not elide to `L..t`; drag-to-resize still available via **View â†’ Resize header sections**.

## v1.39.23

- **Draggable header dividers** â€” Modern top bar white lines are splitter handles: **View â†’ Resize header sections** to drag widths between Start, status, tool chips, and View/HUD/Layout; uncheck to lock and save.

## v1.39.22

- **Logging header indicator** â€” Modern header shows a blinking red **Logging** dot while the rotating file log is recording; click it to open the log file location in Explorer.

## v1.39.21

- **Header Layout chip** â€” Removed tight inner `max-width` on embedded View/HUD/Layout chips that caused Qt to elide labels inside wide frames; nav track now reserves content width (90px floor for Layout) and status/tools chips absorb horizontal compression instead.

## v1.39.20

- **Activity beside Control** â€” Modern sidebar and top chips place Activity next to Control (out of the Logging dropdown) so you can flip between the map cockpit and live wire-tap log in one click.

## v1.39.19

- **Smart-Peek navigation** â€” Starting the bridge still opens Activity so you can confirm wire traffic; when live NETâ†”COM (or inject) data arrives, the UI auto-switches to Control so the position map is visible.

## v1.39.18

- **Position track rolling window** â€” Map track storage now prunes samples older than 5 s before paint and on each fix update; bounds, path, velocity, and dynamic grid spacing use only that window so long sessions no longer stretch the grid.
- **Header Layout chip** â€” Modern header nav reserves content width for View/HUD/Layout; embedded track uses Minimum size policy so Â«LayoutÂ» is not elided under compression.
- **Local backup** â€” NETâ†’COM backup taps at enqueue time (before serial write), so safeguarded bytes reflect UDP/TCP ingress even when COM write is delayed or unavailable.

## v1.39.17

- **Zombie process fix** â€” Close/Exit now always tears down tray icon, COM-lock probe, discovery, and bridge threads (terminate fallback); removed the re-entrant close loop that could leave a headless `python.exe` alive. `bridge_gui.py` uses `os._exit` after quit so stray QThreads cannot block process exit.

## v1.39.16

- **Guide chrome removed** â€” Floating `ðŸ“– Guide` overlay (status-bar / map overlap) removed; open Guide from the Tools sidebar instead.
- **Clean exit** â€” Central teardown stops bridge asyncio thread, Fleet workers, web server, discovery, NTRIP, and UI timers on close, layout switch, and `aboutToQuit`; stale bridge threads get a terminate fallback after join timeout.
- **Dynamic map grid** â€” Position track grid snaps from a 5 s rolling velocity + footprint window to standard intervals (`Grid: 10 m`).

## v1.39.15

- **Startup crash** â€” Fixed `NameError` for `ensure_dropdown_arrow` when highlighting Logging / Bench Tools dropdown chips (v1.39.14 regression).

## v1.39.14

- **Logging / Bench Tools chips** â€” Dropdown pills use a seamless rounded background; native menu-arrow box removed in favor of an inline â–¾ with clean padding.

## v1.39.13

- **Position track grid** â€” Grid spacing snaps to standard intervals (1â€“500 m); label reads `Grid: 50 m` instead of unrounded approximations.
- **Header Layout chip** â€” Demi-bold metrics, 84px floor, and non-shrinking nav track so Â«LayoutÂ» is not elided to `Lâ€¦t`.
- **Presets tab** â€” Dual-column layout (~40% list / ~60% details); action buttons grouped on the right; IP fields capped at 248px.

## v1.39.12

- **Mission Review chart** â€” `max â€¦` peak label moved to the title band (drawn last) on a charcoal pill with bright white text so it never sits inside green bars at 100% height.

## v1.39.11

- **Control COM refresh** â€” Refresh control uses the standard reload icon (â†» fallback), explicit `refresh_ports` binding, and clearer hit target beside the port dropdown.
- **Mission Review chart** â€” `max â€¦` peak label draws above bars on a dark contrast pill so it stays readable when buckets hit 100% height.

## v1.39.10

- **Header console spam** â€” Removed `max-width: 16777215px` from embedded `topBarChip` QSS (Qt rejects `QWIDGETSIZE_MAX` and logged hundreds of warnings). Cluster header layout is now cached so resize does not re-apply unchanged chip sizes.

## v1.39.9

- **Control map** â€” Position track shows a dynamic grid scale legend (e.g. `1 grid â‰ˆ 10 m`). COM port and Baud sit on one row with a narrower baud field.
- **Activity terminal** â€” Timeouts, disconnects, and retries highlight in amber/red; timestamp and routing prefixes are dimmed so payload text stands out.
- **Fleet table** â€” Idle State/Backlog/Activity cells show a grey em dash; Actions column header is centered with fixed width.
- **Dashboard** â€” Phone URL row gets an Open Link action (arrow icon); copy uses a link icon; QR code has white margin framing for easier phone scanning.
- **Presets** â€” List scrollbar appears only when needed; Delete is separated at the bottom with a red accent.

## v1.39.8

- **Header Layout chip** â€” Removed the 88px `max-width` cap on embedded View/HUD/Layout chips; cluster track now uses `Minimum` size policy so "Layout" is not elided to `La..ut`.
- **Mission Review chart** â€” Moved the `max â€¦` axis label into the chart area (top-right) so it no longer overlaps the section title.

## v1.39.7

- **Cross-app UI polish** â€” Activity terminal line spacing and uniform filter pills; Mission Review metric contrast, chart grid, and middle-elided paths; Control map idle icon and COM refresh alignment; Presets list card and notes layout; Fleet compact row actions and brighter table headers; NMEA card hover and checkbox grid columns; Dashboard form label alignment and QR padding; Layout header chip no longer truncates to `La..ut`.

## v1.39.6

- **Control tab UX** â€” Unified header Start/Stop (green Start when idle, red Stop + pulse when running; no redundant â€œRunningâ€¦â€ button). Serial and Network cards use labels-above-fields layout; COM Refresh is an in-field icon. Extra TCP mirror port hides until enabled (indented when shown). UDP Fan-out label shortened; position-track caption gets a readable pill overlay. Serial/Network card heights balanced.

## v1.39.5

- **Strict NMEA with binary prefix** â€” UDP sources that prepend a short binary header before `$GPRMC` on the same line are now parsed instead of rejected. Activity **REJECT** lines show the reason as text (not a confusing hex dump of the error message).

## v1.39.4

- **Activity log clarity** â€” Hex dump lines now read `[HEX N bytes]` instead of `[RAW N bytes]` so they are not confused with NMEA **raw** bridge mode or Fleet raw streams.

## v1.39.3

- **Fleet mirror hints** â€” Raw/MAVLink stream edit auto-checks **Include device TX** when mirrors are set; Fleet status warns if a running raw stream has mirrors without device TX (Cube output never reaches monitor COMs).

## v1.39.2

- **Fleet Start/Stop reliability** â€” Each stream row now has **Start**, **Stop**, and **Edit** buttons (not just a passive â€œEditâ€ label). **Stop all** reports timeouts instead of failing silently. Stopping clears Fleet COM ownership even when a worker times out, so Control can start again. Unchecking **Enabled** in Edit now stops that stream immediately.

## v1.39.1

- **Header chips legibility** â€” Top-bar nav shows icon **and** label again (tighter padding, 8pt) instead of icon-only squares. Floating guide reads **ðŸ“– Guide** on a small pill.

## v1.39.0

- **Floating guide** â€” Guide removed from the header row; draggable ðŸ“– button floats over the workspace. Right-click to hide; restore via **View â†’ Show guide button** (choice persisted).
- **Header chips fit without scroll** â€” Top-bar nav uses compact icon-only chips (tooltips keep full names) so all tools fit on one row.

## v1.38.9

- **Compact status pill** â€” In top-chips header mode the status badge now hugs its text (up to 220px) instead of always stretching to a wide empty pill.

## v1.38.8

- **Unified header (top chips)** â€” Tool nav chips live in the global header row beside Start/Stop and a compact status pill, not a second full-width **TOOLS** bar. Reclaims vertical space and matches Termius-style single chrome. Sidebar nav mode unchanged.

## v1.38.7

- **Space & layout polish** â€” Mission Review uses compact metric chips, side-by-side charts (no giant green slab on short runs), and tighter page margins. Sidebar nav respects canonical group order so **Setup** / **Bench Tools** headers no longer repeat when tab order is customized. Tools page headers slightly tighter.

## v1.38.6

- **Header â€œStoppeâ€ (real fix)** â€” Theme QSS was forcing `min-width: 0` on the status label, so the layout could crush it to ~6 characters after Stop. Label, banner, and header container now reserve enough width for **Stopped**; label uses `MinimumExpanding` size policy.

## v1.38.5

- **Header â€œStoppeâ€ after Stop** â€” Session titles (**Stopped**, **Running**, â€¦) are never truncated; elision uses the labelâ€™s real paint width (not an over-wide container guess). Banner refreshes again after Stop and Mission Review navigation.

## v1.38.4

- **Header â€œStoppeâ€ fix** â€” Status banner keeps the full **Stopped** / **Running** title and only elides the detail line when space is tight; refreshes after layout so the strip does not stay stuck at **Stoppe** on launch or after Stop.

## v1.38.3

- **Start fix** â€” Control **Start** no longer crashes when serial mirror dropdowns are present (`parse_serial_mirror_ports` import order).

## v1.38.2

- **Serial mirror dropdowns** â€” Control and Fleet no longer use a free-text mirror field. Pick up to two monitor COM ports from live port lists (refreshed with **Refresh**); primary COM is excluded; duplicate mirror picks are prevented.

## v1.38.1

- **Serial mirror fix** â€” Mirror COM ports no longer use `serial_asyncio` read polling (which caused `ClearCommError` / fatal transport errors on write-only monitor legs such as com0com). Mirrors are opened write-only via `pyserial` and written on a background thread.

## v1.38.0

- **Serial mirror ports** â€” Duplicate netâ†’COM (and optional inject) traffic to up to **two** extra COM ports at the same baud (com0com monitor-leg workflow). Optional **Include device TX** also copies primary COM reads to mirrors. Available on **Control** (Connect) and per **Fleet** stream; mirror COMs participate in Fleet conflict checks.

## v1.37.2

- **Fleet tab UI freeze fix** â€” Backlog/stats no longer rebuild the whole table ~5x/s per running stream. Stats updates are coalesced in the worker; the Fleet table patches only State/Backlog/Activity cells on a debounced timer (errors and drops still update immediately).

## v1.37.1

- **Fleet MAVLink / MP preset** â€” **Add MAVLink / MP** on the Fleet tab seeds a row with Raw binary, UDP listen **14550**, and fan-out on (matches Cube + Mission Planner UDP Client workflow). Pick your Cube COM in the dialog.
- **Fleet backlog column** â€” Running streams show **ok**, **drop N**, or **q netâ†’COM+COMâ†’net** when bridge queues or drop counters indicate pressure â€” no need to watch Activity for backlog alone.

## v1.37.0

- **Fleet hardening (#4â€“5â€“7)** â€” `start_all` waits for each UDP stream to reach running/error before starting the next (fixes port probe races). Stop timeout leaves the row in **error** (not idle) when COM/network may still be held. Start validates **enabled streams only** â€” a disabled row with a bad label no longer blocks Start all.

## v1.36.9

- **Fleet hardening (#1â€“3)** â€” STARTING/STOPPING workers now count as active for COM/UDP conflict checks; Fleet start is blocked while Control owns the same COM or UDP listen port; auto-start failures surface in the Fleet status line and Activity log (`[Fleet] Auto-start failed: â€¦`).

## v1.36.8

- **Fleet UDP port conflicts** â€” Fleet auto-start on UDP 10110 no longer silently blocks Control (or a second stream) on the same port. Preflight checks surface **UDP busy** in the Fleet table Activity column and status line; new streams default to the next free port (10111â€“10118). Control **Start** is blocked early when a running Fleet stream already listens on that UDP port. Fleet worker logs forward to the main Activity log with a `[Fleet label]` prefix.

## v1.36.7

- **Fleet COM wiring** â€” Editing a running stream's COM/baud/network now restarts that worker on the saved port (table was showing COM12 while the thread still held COM7). Control **Start** is blocked when Fleet already owns that COM; auto-start conflict message names the Fleet stream.

## v1.36.6

- **UI editor â€” Modern header** â€” Reordering View/HUD/Layout no longer wipes the header cluster. Header-tab visibility edits apply only to those three chips (legacy hidden prefs are preserved). Editor list shows them in saved order.

## v1.36.5

- **Startup warning** â€” Fixed `QStatusBar::insertPermanentWidget: Index out of range` on Modern layout (empty hidden status bar).

## v1.36.4

- **Fleet COM list** â€” ports sort numerically (COM1, COM3, COM7â€¦ not COM1, COM10, COM3). Dropdown chevron uses native Qt arrow (fixes square glyph on Baud/NMEA/Network). Dialog min height increased so footer buttons are not clipped.

## v1.36.3

- **Fleet COM picker** â€” COM is now a non-editable dropdown (no text cursor); saved ports not currently plugged in stay in the list. Dropdown chevron is styled visibly on the right.

## v1.36.2

- **Fleet edit dialog polish** â€” COM/NMEA/Network/Baud use proper dropdown styling (visible chevron + popup list) matching Connect/Control. Baud is a preset combo (fixes accidental 65535 from port-style spinbox). TCP client/server modes now show their host/port fields instead of an empty form.

## v1.36.1

- **Fleet edit dialog** â€” COM is now a refreshable port dropdown (same scan as Control). UDP/TCP port spinboxes use wide `NoWheelSpinBox` step buttons; network fields show/hide by mode (listen vs remote) so step arrows are not clipped.

## v1.36.0

- **Fleet multi-stream (alpha)** â€” Modern **Fleet** tab: configure up to 8 COMâ†’network streams, Start/Stop all, per-row edit (double-click), Primary flag for future HUD binding, optional auto-start on launch. Core supervisor in `core/fleet/` with tests; thin pipes by default per spec `011-fleet-multi-stream`.

## v1.35.13

- **Modern header (frozen / Fusion)** â€” View/HUD/Layout chips now set explicit light text color in QSS and Qt palette so Windows builds no longer show black labels on dark buttons.
- **Hub cards** â€” Scroll viewport and endpoint tiles use styled dark backgrounds (`NoFrame` + `WA_StyledBackground`) instead of native white `StyledPanel` panels on some PCs.
- **Status banner** â€” Elision uses the full header status container width, middle-elides long lines, and a shorter default stopped message so **Stopped** stays readable on Mission Review and narrow layouts.

## v1.35.12

- **View menu (shipped Modern)** â€” Frozen builds hide dev-only **Save UI as product default** and Standard top-bar items that do not apply to Modern (reset/show chips, move bar, shortcuts legend). Operators keep full screen, HUD, UI editor, reset layout, layout switches, and Tools navigation.

## v1.35.11

- **Modern chip rail** â€” Added a **TOOLS** section label to the left of the navigation chips (matches the sidebar header).

## v1.35.10

- **Modern navigation recovery** â€” UI editor Apply re-syncs the chip rail after reorder/hide; falls back to sidebar if chips would be empty; header embed no longer re-parents View/HUD/Layout on every save.

## v1.35.9

- **Modern UI editor** â€” Scoped to what Modern actually uses: **Header** (View/HUD/Layout only), **Navigation** (chip rail + sidebar pages). Connect / main-tabs editors stay Standard-only; chip rail now respects saved page order from the editor.

## v1.35.8

- **Serial link card** â€” Form cards no longer stretch vertically to match the taller Network column; content stays compact at the top of the left column.
- **Header status** â€” Full â€œStopped Â· Pick a COM portâ€¦â€ line shows when the header has room; elision refreshes on window resize instead of staying stuck at â€œStoppâ€¦â€.

## v1.35.7

- **Position track header** â€” Click anywhere on the â€œPosition trackâ€ bar to expand/collapse (not just the chevron).

## v1.35.6

- **Position track fix** â€” Restored map canvas height on Control (layout alignment was preventing the track body from expanding); idle â€œStoppedâ€ message shows on launch again.

## v1.35.5

- **Control tab polish** â€” Extra TCP mirror port on its own indented row with a compact port field (no label overlap); Position track expanded by default and pinned to the top of the column when collapsed.
- **Rejects chip** â€” Header âš  rej chip is clickable; shows a plain-language breakdown and optional jump to Activity.

## v1.35.4

- **View â†’ Layout switches** â€” Menu lists every workspace you are not on (Standard, Field, Modern); two choices when three layouts exist, instead of a single toggle target.

## v1.35.3

- **Header status flex** â€” Status banner expands into available header width with trailing ellipsis instead of hard clipping; Guide and layout controls no longer steal space via a premature stretch.
- **Dashboard port lock countdown** â€” Web API port unlock shows a live `Editable Â· Ns` tick each second and re-locks the spin box at zero.
- **View menu structure** â€” Grouped separators, non-clickable section headers, right-aligned shortcut rows; **Bench pair setup** moved to **Bench Tools â–¾** menu.
- **Mission Review / Black box** (v1.35.2) â€” Chart title clearance, path elide + copy, placeholder contrast, footer button group.

## v1.35.2

- **Mission Review / Black box polish** â€” Chart title band clearance fixes bar overlap; session `.raw` path middle-ellipsis + copy button; brighter backup-path placeholder; Quick Export and Back to Activity grouped bottom-right.

## v1.35.1

- **Nav dropdown chips** â€” Extra right padding and menu-arrow inset so the caret is not flush to the border; main-button click cycles Logging/Bench Tools children (Activity â†’ Black box â†’ â€¦) instead of resetting to the first item; active child name stays on the chip with blue highlight.

## v1.35.0

- **Modern nav density** â€” Top chip rail consolidated to 6 items: Control, Presets, Hub, NMEA, **Logging â–¾**, **Bench Tools â–¾** (Activity/Black box/File log and Dashboard/Inject/Terminal/Checks). Guide stays in the header; sidebar groups updated to match.
- **Control split layout** â€” Serial + network stack in a 45% left column; position track map fills the 55% right column (stacks vertically below 720px).
- **Hub filters** â€” All / Hardware COM / Network Adapters / Presets toggle row above the card grid.
- **NMEA quick picks** â€” Active preset button highlights while checkboxes update in real time.
- **Dashboard pairing copy** â€” Phone Pairing help is a plain ordered list (not italic paragraph).
- **Inject / Checks / Terminal polish** â€” Send buttons anchored bottom-right of the inject editor; Checks grouped with amber header + red Stop; Terminal Quick presets inline with Ping and console hint on the output frame.

## v1.34.10

- **Revert chip drag-reorder** â€” Removed drag-to-reorder on the top tools chip rail (could corrupt tab order and header layout). Reorder via **View â†’ UI editor â†’ Tools tabs** instead. **Dashboard** rename kept.

## v1.34.9

- **Dashboard tab label** â€” Modern Tools **Phone** chip/sidebar/page renamed **Dashboard** (ðŸ“± icon unchanged); saved order/hidden prefs migrate from Phone automatically.

## v1.34.8

- **Header layout** â€” Status banner shrinks to its message instead of stretching across the top bar; **Guide** moves to the header beside it and is removed from the top chip rail to reduce tab clutter.

## v1.34.7

- **Icon chrome** â€” Title bar, tray, and embedded ICO use the dark squircle (`app-icon.png`) again so the logo blends with the grey top bar; `app-icon-source.png` remains edit-only source art (white matte).

## v1.34.6

- **Typography â€” Maple Mono** â€” Bundled Maple Mono (OFL) under `assets/fonts/`; app-wide Qt font + stylesheets use it with Cascadia/Consolas fallbacks.

## v1.34.5

- **EXE icon â€” taskbar fix** â€” Windows ICO now uses BMP frames (PNG-compressed ICO broke taskbar â†’ white placeholder). Embedded ICO uses your white-matte IMG_1118 art; title bar / tray load `app-icon-source.png` directly.

## v1.34.4

- **EXE icon â€” stop mangling small sizes** â€” Removed the separate â€œshellâ€ ICO tier that turned the DE-9 into an abstract white blob / Windows placeholder. All ICO sizes now downscale the same detail master as `app-icon.png`; Qt prefers PNG for the title bar; ICO save uses Pillowâ€™s native multi-size writer for taskbar embedding.

## v1.34.3

- **EXE icon â€” shell tier fix** â€” Small Windows icon layers (16â€“32px) no longer flatten the DE-9 into a solid white â€œtoolboxâ€ blob; shell tier keeps colored pins and connector outline on the dark tile. Re-copied IMG_1118 source and regenerated ICO.

## v1.34.2

- **EXE icon â€” original IMG_1118 source** â€” Installed your provided DE-9 art as `assets/app-icon-source.png` and regenerated PNG/ICO.

## v1.34.1

- **EXE icon â€” restore provided DE-9 art** â€” Removed auto-generated DB-9/RJ-45 bootstrap; recovered your connector logo into `assets/app-icon-source.png` from git history (v1.17.47 composed icon); regenerated PNG/ICO. If you still have the original IMG_1118 file, drop it on `app-icon-source.png` for a cleaner matte.

## v1.34.0

- **EXE icon â€” readable branding (PKG-ICON-01)** â€” Restored `assets/app-icon-source.png` (bold DB-9 + RJ-45 on white matte); stronger shell-tier ICO layers for 16â€“48px taskbar/Explorer; `test_app_icon` 16px gate; wired into `verify_all.py`; frozen bundle checks `assets/app-icon.ico`; `release.ps1 -SkipTests` regenerates icon before PyInstaller.
- **Pre-release audit inventory** â€” `docs/pre-release-audit-inventory.md` with ship gates for GitHub release (010 spec).
- **Release pipeline** â€” Icon assets in `frozen_bundle_manifest.py`; version sync verified for v1.34.0.

### Deferred

- **ROADMAP-SCOPE-01** â€” MAVLink GPS injector and kernel virtual COM remain bookmarked in `docs/ROADMAP.md`, not shipped.

## v1.33.1

- **Phone tab â€” minimum width layout** â€” Server & Network and Phone Pairing cards stack vertically when content is narrow; form rows wrap; removed 320px card floor; shorter Open dashboard label and compact QR.

## v1.33.0

- **Control preset strip â€” Presets parity** â€” Loaded preset summary on Control uses the shared `modernToolsLiveStatus` green **ok** styling (same family as Presets â€œLoaded:â€), via new `ui/modern_live_status.py` helper.
- **Advanced network styling** â€” Expanded TCP/UDP mode panel inside the Modern Network card matches form field borders and typography.
- **Visual hierarchy** â€” Preset strip icon ðŸ“Œ (distinct from Activity ðŸ“‹); Position track title aligned with section headers.
- **Tests** â€” Chrome tests for Control page banner/preset bar and Hub banner without duplicate hub title.
- **Stylesheet** â€” Removed duplicate `modernControlTab` QSS block; transparent preset bar frame.
- **Docs** â€” OPERATOR_GUIDE Modern Control layout and View â†’ Tools navigation note.

## v1.32.7

- **Control tab â€” minimum width layout** â€” Serial and Network cards stay side-by-side at the 640Ã—420 window floor instead of stacking vertically.

## v1.32.6

- **Control tab â€” visual redesign** â€” Page banner (icon + title + subtitle), card-style Serial/Network forms with section headers, and a styled preset summary strip instead of floating plain text. Position track card matches the softer rounded layout.

## v1.32.5

- **Hub tab â€” page banner** â€” Hub now uses the same icon + title + subtitle header as Presets, NMEA, and other Modern tools pages (Refresh/Unlock toolbar kept below the banner).

## v1.32.4

- **Top chips â€” consistent active styling** â€” Nav chips no longer mix Qt â€œcheckedâ€ border styling with the filled active pill; only the current section highlights. Nav highlight also re-syncs when the content stack changes.

## v1.32.3

- **Top chips â€” vertical clipping fix** â€” Chip rail height and button sizing aligned (32px chips in a 48px rail) so pill borders are no longer cut off at launch.

## v1.32.2

- **Top chips â€” scroll / minimum width** â€” Chip rail no longer forces window width or shows a grey scrollbar track; scroll with the mouse wheel over the chip row. Window minimum lowered to 640Ã—420.
- **Presets â€” preview before Load** â€” Selecting a preset in the list shows a **Preview** line (COM, baud, NMEA, UDP, fan-out, survey IPs) from the saved file, not the current Control UI. Hover for preset notes.

## v1.32.1

- **Control tab â€” responsive forms** â€” Serial link and Network path stack vertically when the window is narrower than 800px, so you can shrink width without squashing the two-column layout.
- **Position track â€” collapsed by default** â€” New installs start with the map card collapsed (saved preference still respected). Expanded map minimum height reduced from 168px to 120px.

## v1.32.0

- **Modern UI â€” top tools chip rail** â€” Toggle Tools navigation between the left sidebar (default) and a horizontal icon chip row under the header. Compact icon-left pills with group separators; scroll horizontally when the window is narrow. Switch via **View â†’ Tools navigation â†’ Sidebar / Top chips**; preference persists across restarts. UI editor reorder/hide applies to both modes.

## v1.31.9

- **Control tab â€” compact top-aligned layout** â€” When the position track is collapsed, extra vertical space now goes to the bottom of the page instead of floating the preset line and map header in the middle. Forms, preset caption, and position track header stay packed at the top; the map only stretches when expanded.

## v1.31.8

- **Sidebar â€” collapse button moved to top** â€” The `â€¹/â€º` collapse toggle is now in the top-right corner of the sidebar next to the "TOOLS" label, not buried at the bottom. Much easier to find on first use.
- **Activity terminal â€” wrap toggle** â€” `âŽ` button added to the terminal toolbar. Click to toggle line-wrap mode so long NMEA/MAVLink lines fold instead of scrolling off-screen. State is per-session (default off for telemetry, enable for readable NMEA).

## v1.31.7

- **New preset: Cube GPS UART** â€” Built-in preset for NMEA GPS injection into ArduPilot via a dedicated UART (Telem2 / Serial4 etc.). NMEA passthrough mode, 38400 baud, fan-out off. Preset note includes the required ArduPilot params (`SERIALx_PROTOCOL=5`, `SERIALx_BAUD=38`, `GPS_TYPE2=5`). Designed to run alongside the Cube MAVLink instance for a full USV parallel setup: one instance relays MAVLink on the USB port, a second injects simulated or real NMEA GPS over a UART.
- **Fix: `udp_fanout` now persists correctly in built-in presets** â€” `udp_fanout` was missing from `_PRESET_KEYS` so it was silently dropped when loading any built-in preset. Fixed by adding it to `_PRESET_KEYS` and `_normalize_desk`.

## v1.31.6

- **Bridge terminal â€” binary stream auto-detection** â€” The terminal now samples the first 32+ bytes of live traffic. If >25% are non-printable (catches MAVLink v1/v2, RTCM, any binary protocol), it immediately shows the Hex button, enables hex display, and logs `[Terminal] Binary stream detected â€” hex display enabled automatically.` This works regardless of what NMEA mode the bridge was started in, so loading an NMEA preset but pointing it at a Cube Orange / MAVLink device still auto-switches the terminal to hex. Detection resets on Clear and on each new bridge session.

## v1.31.5

- **Bridge terminal â€” auto hex on raw/binary mode** â€” Switching to Raw mode (or loading any raw-mode preset such as MAVLink / CubeOrange) now automatically enables hex display in the Activity terminal. No need to manually click the Hex button. Switching back to NMEA passthrough or strict turns hex off. The hex state also primes correctly when the mode selector is changed before the bridge is started.

## v1.31.4

- **Header â€” minimal strip** â€” Stripped the header down to: Start/Stop Â· status banner Â· backpressure warning (when active) Â· ðŸ“± (when Web API on) Â· View/HUD/Layout. Hz pill, backup pill, COM-lock chip, Presets, Recent, and Stats shortcuts are removed from the header row. That info lives in the footer status line and the sidebar â€” the header no longer competes with itself for space at any window width.

## v1.31.3

- **Control layout â€” clean full-width stack** â€” Removed the 40/60 side-by-side split that left dead space on the left when the map was visible/collapsed. Forms (Serial | Network) â†’ Preset hint â†’ Position track now stack vertically, each full-width. No dead zones at any window size.
- **Header responsive collapse** â€” When the window narrows below ~820 px, lower-priority header chips (Hz pill, Backup pill, Presets / Recent / Stats shortcut buttons) hide automatically; they reappear above ~860 px. This prevents the top-bar clipping visible on smaller windowed sessions.
- **Minimum window size** â€” Reduced from 860 Ã— 540 to 720 Ã— 460, matching the tighter header footprint.
- **Tighter chip padding** â€” Status pills and nav chip buttons trimmed from 10 px to 6â€“7 px side padding; status banner left-padding reduced; header row spacing tightened. Fits more content at smaller widths without truncation.

## v1.31.2

- **Control layout â€” Option C + B** â€” Forms stay top row (Serial | Network side-by-side). Bottom half splits: preset hint on the left, position track on the right (40/60). Map card has a **â–¼/â–¶ collapse toggle** that hides the plot to free vertical space on short/laptop windows; preference persists across restarts.

## v1.31.1

- **Control map â€” hybrid full map** â€” **Open full map** on Control opens the local Web dashboard with Position map enabled and prioritized (`?map=1`). Double-click the in-app track plot for the same shortcut.

## v1.31.0

- **Modern Control â€” position track** â€” Light Qt map in the Control tab empty space: live GGA/RMC dot, short track line, fix-quality colors, and **Clear track**. No map tiles (use the web dashboard for street/satellite). Hidden in raw binary mode.

## v1.30.1

- **Modern header shortcuts** â€” ðŸ“± opens the local Web dashboard in your browser (when Web API is on). Click the Running/Stopped status strip to jump straight to **Control** (COM + network).

## v1.30.0

- **Modern layout â€” persistent Tools sidebar** â€” Removed top-level Activity / Control / Tools tabs. The Tools column stays on the left; main content fills the right. **Control** is its own sidebar group; **Activity** (live wire-tap) lives under **Logging**. Collapse control (â€¹/â€º) shrinks the sidebar to icons only; preference persists across restarts. UI editor now manages sidebar items only (no main tabs).

## v1.29.5

- **Modern layout defaults** â€” Shipped Tools sidebar order matches operator layout: Logging leads with Activity; Bench leads with Guide. `product_ui_defaults.json` seeds Modern main/tools tab order and header chip visibility for fresh installs.

## v1.29.4

- **Modern UI editor** â€” View â†’ UI editor now lists **Activity / Control / Tools** main tabs and the full **Tools** sidebar (Hub, Presets, NMEA, Black box, â€¦). Reorder and show/hide apply to the Modern layout; legacy Connect/Log/Hub main-tab prefs migrate cleanly.

## v1.29.3

- **Modern UI â€” Hub under Tools** â€” Connection Hub moved from the top tab bar to **Tools â†’ Hub** (Setup group). Saved â€œHubâ€ tab preference opens Tools â†’ Hub. One-shot discovery scan on first Hub visit unchanged.

## v1.29.2

- **Preset Load sticks on Control** â€” loading a preset (e.g. Cube MAVLink) no longer gets overwritten by the Hub blue tile on the next discovery refresh; preset apply marks manual override and syncs the hub tile to match. Removed erroneous Passthrough flash during preset COM apply (NMEA mode comes from preset only).

## v1.29.1

- **Cube MAVLink preset appears in list** â€” `bench_defaults.json` block is now registered as built-in **Cube MAVLink** (alongside Desk test, Boat / INS, NORBIT DCT). Existing `path_presets.json` files pick it up via `setdefault` on next launch.

## v1.29.0

- **Cube / MAVLink operator guide** â€” `docs/OPERATOR_GUIDE.md` Â§5.6 documents Cube Orange + Mission Planner over **UDP Client** (full COM-level GCS access via Raw binary). Â§6.5 covers survey-stack theory: fan-out, Hypack/sonar NMEA paths, mesh/VPN, and limits. Shipped **Cube MAVLink** preset in `bench_defaults.json`. Tools â†’ Guide adds **Cube / MAVLink** scenario chip.

## v1.28.10

- **Listen port sticks on Control** â€” changing UDP listen port (e.g. 14550 for MAVLink) on Control no longer snaps back to 10110 when Start applies a serial hub tile or last-known-good preset; serial hub picks restore COM/baud only, not network fields you edited on Control.

## v1.28.9

- **Hub COM pick sticks** â€” background discovery no longer snaps the blue tile back to Controlâ€™s COM after you click a different port on Hub; hub tile wins unless you changed COM manually on Control (`manual override`).

## v1.28.8

- **Black box (local backup)** â€” now records **networkâ†’COM** writes, not just COM reads. Survey UDP/TCPâ†’serial sessions populate `backup_*.raw` again; empty dated folders from NET-only traffic are fixed.

## v1.28.7

- **Hub â†” Control COM sync** â€” clicking a serial hub tile always updates Control COM (even when last-known-good omits `com`); launch and discovery refresh align the blue tile with the Control preset; Start uses Control when hub and Control disagree.

## v1.28.6

- **Modern launch layout** â€” global header (Start/Stop + nav chips) no longer collapses or opens off-screen on first show; window centers on the available desktop and header height is reserved before the first paint.

## v1.28.5

- **Hub restored** â€” network/preset tile picks no longer get overwritten every 2 s by Control COM sync; hub clicks are authoritative again (Start respects blue tile). Control COM still updates the matching serial tile when you change it there.

## v1.28.4

- **Hub â†” Control sync** â€” changing the COM dropdown on Control now moves the hub blue selection to match (and stays aligned after discovery refresh).

## v1.28.3

- **Hub discovery** â€” Refresh discovery probe results now stick (background polls were resetting tiles to gray Detected). Single-click probes that COM; double-click opens Control. Header shows counts like `3 COM free Â· 1 busy` after refresh.

## v1.28.2

- **Control COM picker** â€” while the bridge runs, changing COM on Control no longer snaps back to the active port every stats tick; hub selection clears when you pick a port manually so Start wonâ€™t force the old hub tile.

## v1.28.1

- **Hub tiles** â€” status chips are color-coded (gray = detected only, green = active/live, amber = busy/warn); â€œAvailableâ€ renamed to **Detected**; hint explains click fills Control without Start.

## v1.28.0

- **Mission Review backup folders** â€” choose where `.raw` backups save (Browse), auto-create dated subfolders each Start (`YYYY-MM-DD_HH-MM`), or click **New dated folderâ€¦** to make one now. Same controls live under Tools â†’ Black box. Preference persists for the next session.

## v1.27.5

- **Modern UI console** â€” removed unsupported `font-variant-numeric` from Qt stylesheets (was spamming â€œUnknown propertyâ€ on launch).

## v1.27.4

- **Hz pill legibility** â€” removed Unicode â†“/â†‘ from the header rate pill (e.g. `â†“8.0 â†‘0.0` was misread as `18.0`); shows `GNSS 1.0 Hz Â· 8 msg/s` with plain `net`/`COM` labels in tooltips and status line.

## v1.27.3

- **GNSS fix Hz (header pill)** â€” pill shows **GGA/RMC update rate** (survey Hz), e.g. `GNSS 1.0 Hz` for a 1 Hz INS burst with many auxiliary sentences. Total sentence rate (e.g. 18 msg/s) moves to the tooltip and status line.

## v1.27.2

- **Ingress Hz (fix)** â€” msg/s now counts **all NMEA sentences received** on the wire (rolling 1 s), including strict-mode rejects. Disabling a sentence type no longer lowers the displayed GNSS rate â€” only forwarded totals and reject counters change.

## v1.27.1

- **Sentence-rate Hz (fix)** â€” header pill and status line now count **NMEA sentences per second** (rolling 1 s window), not UDP datagrams or serial read bursts. A 5 Hz GNSS stream bundled in one packet now reads ~5 msg/s, not ~1.

## v1.27.0

- **Presets quick-pick (Modern header)** â€” **Presets** button: click opens Tools â†’ Presets; arrow menu loads a saved preset and Starts (same as the survey top bar).
- **Running Hz chip (Modern header)** â€” while Running, a compact **â†“wire â†‘wire Hz** pill stays visible in the header (hover for full transport line); no need to open Activity for live rates.

## v1.26.1

- **Recent session apply fix** â€” menu clicks now pass the session entry correctly (`QAction.triggered` was overwriting it with a bool); applying a recent session also jumps to **Control** and refreshes page summaries.

## v1.26.0

- **Recent quick-pick (Modern header)** â€” **Recent** dropdown beside the status pills restores saved COM + UDP + NMEA sessions (same menu as the survey top bar, including Manage).
- **Session stats export** â€” **Stats** header menu: **Copy stats to clipboard** or **Save stats as CSV** (Hz, drops/rejects, queues, GNSS, session totals).
- **Serial auto-reconnect hardening** â€” reconnect follows USB hwid across COM re-enumeration on read/write errors and open timeouts; write failures tear down the serial session so the lifecycle loop can reopen cleanly.

## v1.25.5

- **Connection health chip (Modern header)** â€” compact pill shows **COM Â· network Â· NMEA Â· session** at a glance (green when healthy, amber/red on retry or errors); hover for full serial/network lines.

## v1.25.4

- **Backpressure chip (Modern header)** â€” while Running, drops/rejects/queue backlog show as a compact amber/red pill beside backup status (hidden when transport is healthy).
- **COM preflight dialog** â€” Start blocked by a busy/missing COM port opens an actionable dialog (Open Control, Unlock COM, Run com_free) instead of a generic warning; COM lock chip uses clearer blocked styling.

## v1.25.3

- **NMEA â†” Presets (Modern)** â€” Tools â†’ NMEA shows whether settings match the loaded/selected preset, with **Load from preset** and **Save NMEA to Â«nameÂ»** actions.
- **Strict start guard** â€” starting with Strict mode and no sentence types checked prompts checksum-only confirmation (Open NMEA / Start anyway / Cancel).

## v1.25.2

- **Tools polish (Presets + Logging)** â€” **Presets** drops the nested scroll area for a flat layout with a live summary (loaded preset, COM, NMEA, network). **File log** is disk-only again. **Activity** is its own Logging sidebar page with a prominent Clear button and live line count â€” no longer buried under File log.

## v1.25.1

- **Modern header polish** â€” fixed View/HUD/Layout stretching (spring timer no longer overrides cluster layout); status line is single-line and no longer clips; Start/Stop use compact labels; idle **Backup: 0 B** pill hidden; nav chips align right at content width.

## v1.25.0

- **Tools â†’ NMEA redesign (Modern)** â€” three mode cards (Passthrough / Strict / Raw) with a live **Next Start** summary banner; Strict panel adds **Quick picks** (Survey GPS, Position only, All types, Checksum only) and shows sentence types only when Strict is selected; checking any type auto-selects Strict so you cannot forget the mode/type pairing.

## v1.24.1

- **Activity toolbar (Modern)** â€” direction filters are a single segmented control; Type appears only after sentence types are seen; Pause/Clear/Save are compact icon buttons on the right (Termius-style session chrome).
- **Phone QR off Activity canvas** â€” floating `ConnectQrFloat` is suppressed in Modern UI; scan the code from **Tools â†’ Phone**, or use the ðŸ“± header button when Web API + LAN are enabled.
- **Running session mode** â€” while the bridge runs, the header compacts (shorter bar, single-line status, COM/backup pills hidden unless they need attention).

## v1.24.0

- **Modern header chrome (P0/P1)** â€” merged the survey top bar into the global header: View/HUD/Layout are content-sized pills on the right (no full-width stretch, no drag grips). COM and backup status are compact pills beside the status line; version lives in the footer only.

## v1.23.0

- **Operator Guide redesign (Modern Tools â†’ Guide)** â€” scenario picker (First time, UDP survey, TCP setup, Fix it), visual data-flow diagram, numbered step cards with **Open Control / Activity / Presets** shortcuts, plain-language troubleshooting cards, and full manuals kept at the bottom.

## v1.22.2

- **Modern Tools visual pass** â€” sidebar grouped into **Setup / Logging / Bench**; each page gets a large header band + content card (icon + 16pt title); **Clear view** folded into **File log** (9 sidebar items); live status chips use green/blue/gray color states; **Checks** shows an amber bench-only banner.

## v1.22.1

- **Modern Tools polish** â€” unified title + subtitle on every Tools page; **Activity** sidebar item renamed **Clear view**; live **Recording toâ€¦** status on Black box and File log while the bridge runs; stripped duplicate hints on Inject, Terminal, and Checks; Guide copy fixed (Tools â†’ Phone) and double-scroll removed.

## v1.22.0

- **Modern Tools flat sidebar** â€” every tool is its own sidebar item (Presets, NMEA, Phone, Black box, File log, Activity, Inject, Terminal, Checks, Guide). Removed grouped **Logging**, **Remote**, and **More** buckets so nothing is hidden behind scroll or search.

## v1.21.1

- **Modern Tools usability pass** â€” replaced the crowded single **Bench** scroll with six focused Tools pages: **Logging**, **Remote**, **Presets**, **NMEA**, **Checks**, and **More** (inject, terminal, guide). **Checks** now owns the full panel height with an expandable output area instead of a tiny nested diagnostics card.

## v1.21.0

- **Modern UI bloat trim (Phase 3)** â€” **HUD** opens one metrics window only (removed auto-open trust dashboard and redundant View menu entries). **Tools** tab replaces Settings with focused pages: **Logging**, **Remote**, **Presets**, **NMEA**, **Checks** (full-height automated checks output), and **More** (inject, terminal, guide). **Tray**: minimize or close while running hides to tray; tray Stop is enabled only when the bridge is running; tooltip shows live COM/network status.

## v1.20.0

- **Modern UI bloat trim (Phase 2)** â€” merged the separate **Log** and **Wire** tabs into a single **Activity** tab: live wire-tap traffic (direction filters, NMEA highlighting, hex in raw mode, pause/save) plus bridge status lines shown as muted **EVENT** rows. Survey bar trimmed to essentials in Modern mode â€” **View**, **HUD**, and **Layout** only; Presets, Recent, Tools, UI editor, Copy stats, Shortcuts, and theme chips hidden (still reachable via View menu or Settings). Saved tab preference migrates from retired Log/Wire tabs.

## v1.19.4

- **Modern UI bloat trim (Phase 1)** â€” removed the **Telemetry** tab (duplicated header status labels with no added value), the **Quick-View** hover popup on tab headers, and the static **Traffic & data quality (honest counters)** Diagnostics card (legend text only, no live data). Guide copy now points operators to **HUD**, **Wire**, and the header status banner instead. Saved tab preference migrates away from the retired Telemetry tab.

## v1.19.3

- **BUGFIX â€” Wire tab layout and filters** â€” each sentence now renders on its own line (QPlainTextEdit requires a trailing newline per insert; without it all traffic ran together on one horizontal row). Direction and sentence-type filters now replay from a session history buffer, so selecting `COMâ†’NET` hides prior `NETâ†’COM` lines instead of leaving stale traffic visible.

## v1.19.2

- **BUGFIX â€” Wire tab empty while bridge running** â€” `BridgeTerminalPanel.feed()` no longer uses `QMetaObject.invokeMethod` with `Q_ARG(bytes, â€¦)` (unreliable in PySide6 from the bridge thread). Traffic is now queued via a `Signal(str, object)` with `QueuedConnection`, matching the same cross-thread pattern as `BridgeAsyncThread.log_msg`.

## v1.19.1

- **BUGFIX â€” Modern UI bridge start crash** â€” `BridgeWindowModern._on_bridge_started()` now accepts the `SerialNetBridge` instance passed by `BridgeLogicMixin._on_worker_start_done`, fixing `TypeError: takes 1 positional argument but 2 were given` when clicking Start in Modern mode.

## v1.19.0 â€” Bridge Terminal (Wire-Tap Panel)

- **[FEATURE] Wire tab â€” live bridge traffic viewer** â€” new `Wire` tab in the Modern UI cockpit (between `Control` and `Hub`) showing every assembled NMEA sentence or raw binary block flowing through the bridge in real time. Direction-labelled entries (`NETâ†’COM` in blue, `COMâ†’NET` in green, `REJECT` in amber) with `HH:MM:SS.mmm` wall-clock timestamps.
- **NMEA syntax highlighting** â€” `_NmeaHighlighter` (`QSyntaxHighlighter`) colours the talker prefix, sentence type, and checksum separately for fast visual scanning. Hex-dump rows use a distinct blue for byte values.
- **Direction filter chips** â€” `All / NETâ†’COM / COMâ†’NET / Reject` toggle chips in the toolbar; selecting one hides all other directions without pausing the bridge.
- **Sentence type filter** â€” `QComboBox` auto-populates with every NMEA sentence type seen since last clear (`GGA`, `RMC`, `VTG`, â€¦); selecting one shows only that type across all directions.
- **Hex toggle** â€” visible only when the bridge is in RAW/binary mode; renders each block as a 16-byte-wide hex dump with printable ASCII side-car. Automatically hidden in NMEA modes.
- **Pause / Resume** â€” freezes the display without dropping data from the bridge; amber button state makes the paused condition obvious.
- **Clear** â€” wipes the view and resets the sentence-type combo; the bridge keeps running.
- **Save** â€” saves the current visible traffic to a timestamped `.txt` file via a file dialog.
- **Thread safety** â€” `BridgeTerminalPanel.feed()` uses `QMetaObject.invokeMethod` with `QueuedConnection` so the bridge asyncio thread never touches Qt directly. A 40 ms batch-flush timer coalesces rapid bursts (e.g. 10 Hz NMEA) into a single `insertText` call to keep the UI responsive.
- **`bridge_core.py`** â€” added `wire_tap_cb` parameter to `SurveyBridge.__init__`; called with `(direction, data_bytes)` at every forward and reject point in `_ingest_net` and `_ingest_serial` (after NMEA assembly so each call always carries a complete sentence, never a partial UDP fragment). RAW mode taps the raw bytes directly. Callback wrapped with `_wrap_bridge_callback` so a UI exception can never abort the bridge loop.
- **`ui/mixin.py`** â€” `_on_bridge_wire_tap` method routes tap events to `self.bridge_terminal`; `_on_bridge_started` notifies the panel of the current NMEA mode so the hex toggle shows/hides correctly.
- **`version_info.txt`** synced to 1.19.0 via `tools/sync_version_info.py`.

## v1.18.0 â€” UI & Workflow Journey Modernization

> **Release summary for the `2034-ui-journey-modernization` branch.**  
> This release replaces the legacy splitter-based layout with a fully redesigned high-density cockpit UI,
> ships a mission-grade data-safeguard pipeline, and hardens the UI thread against bridge-core interference.

---

### [FEATURE] Modern UI 'Cockpit' Overhaul

A complete ground-up rewrite of `BridgeWindowModern` (`ui/modern.py`, `ui/modern_styles.py`) centered on a tab-per-panel architecture with a persistent global status header.

- **Persistent Global Header Strip** â€” `â–¶ Start`, `â–  Stop`, live status banner, version chip, and COM lock chip are always visible above the tab bar regardless of which panel is active. Mission state is never hidden behind a tab switch.
- **Command Tab Bar** â€” compact 32 px dark rail (`#05070a`) with five primary tabs: `Log | Control | Hub | Settings | Telemetry`. Active tab uses a bright `#60a5fa` bottom-border glow. Tabs are individually movable (`setMovable(True)`).
- **Smart-Peek** â€” bridge start automatically navigates to the `Log` tab so the operator sees live data immediately without a manual click.
- **Quick-View Popup** â€” hovering over the `Telemetry` or `Hub` tab header shows a non-modal, mouse-transparent 3-line status preview (`_QuickViewPopup`) without leaving the current view. Show/hide is debounced at 320 ms / 180 ms.
- **Settings â€” VS Code-style sidebar navigation** â€” the Settings tab was restructured from a nested `QTabWidget` to a 152 px vertical sidebar (`QListWidget`-style `QPushButton` stack) controlling a `QStackedWidget`. All 7 sections (Presets, Phone, NMEA, Diagnostics, Inject, Terminal, Guide) receive a full Modern QSS cascade: dark surface `QGroupBox` cards, blue-accented inputs, custom checkbox/radio indicators, terminal-dark plain text areas, themed preset list, and iOS-style collapsible diagnostics cards.
- **Hub tab** â€” `ConnectionHubWidget` fills the full tab height; internal scroll-area `maxHeight` cap released so the card grid expands to the window edge. One-shot auto-discovery scan fires on first Hub tab visit.
- **Status Footer** â€” 24 px strip spanning the full window bottom carries backup status and version label; replaces the per-panel status bar.
- **Fixed high-contrast palette** â€” `#0a0e14` root, `#111827` surface, `#1a2332` alt-surface, `#3b82f6` accent, `#60a5fa` accent-bright. Theme randomizer is suppressed in Modern mode.

---

### [IMPROVEMENT] Mission Review & Export

Post-mission visual integrity auditing added as a hidden tab (`Mission Review`) that is revealed automatically after `Stop bridge` if a backup session was active.

- **`ThroughputBarChart`** â€” custom `QWidget` painter renders backup bytes-per-5 s bucket as a high-contrast bar chart (`#38bdf8` bars, `#34d399` peak highlight) against a terminal-dark background. Peak throughput annotated at the bottom axis.
- **`HealthTimeline`** â€” companion painter renders a colour-coded tick strip (green `ok` / amber `warn` / red `bad` / grey `idle`) derived from `MissionSessionRecord.health_ticks`, giving the operator an immediate read on data quality before leaving the field.
- **Integrity Note** â€” plain-language annotation below the timeline promotes critical/caution window counts and disk-verification result to the operator without requiring log inspection.
- **Quick Export** â€” one-click button zips the session `.raw` backup and an auto-generated `mission_summary.txt` (duration, avg Hz, total bytes, drop count) into a timestamped archive ready for survey office handoff.
- **Back to Pipeline** â€” button navigates directly to the `Log` tab without closing the review.

---

### [IMPROVEMENT] 'Black-Box' Persistence

Crash-safe raw data logging integrated at the bridge core level for zero-loss field capture.

- **`core/local_logger.py`** â€” daemon-driven non-blocking queue feeding `os.open` / `os.write` / `os.fsync` writes to a rotating `.raw` file. Write latency is fully decoupled from the asyncio bridge loop; a bounded queue prevents runaway memory growth under sustained load.
- **Backup status chip** (`lbl_backup_status`) â€” live health indicator in the status footer; transitions between `ok`, `warn`, and `error` states with colour-coded QSS.
- **Post-stop integrity report** â€” `verify_backup_on_disk` checks file size and growth at session end. A zero-byte or stale file surfaces a `Warning: No data written` alert so the operator knows before hauling hardware out of the water.
- **`MissionSessionRecord`** â€” lightweight dataclass accumulates throughput buckets and health ticks in memory during the session; no disk overhead beyond the `.raw` file itself.

---

### [REFACTOR] Container-Manager Pattern

Full removal of legacy layout systems that accumulated across prior iterations.

- **`QSplitter` eliminated** â€” no `QSplitter` references remain in `BridgeWindowModern`. Layout is driven entirely by `QVBoxLayout` / `QHBoxLayout` stretch factors and a `QStackedWidget` for the Settings pane.
- **`QDockWidget` eliminated** â€” dock-based layout was trialled and fully reverted; no residual imports or state.
- **Accordion / floating-card remnants removed** â€” `ModernModule`, `HUDOverlay`, and accordion toggle references purged. `ui/modern.py` now imports only what it uses.
- **`create_diagnostics_controls`** import removed â€” was made redundant by the inline `build_diagnostics_tab(skip_hub=True)` call inside `_build_settings_tab`.
- **Duplicate `ConnectionHubWidget` resolved** â€” `build_diagnostics_tab` accepts `skip_hub: bool = False`; Modern passes `skip_hub=True` so only the dedicated Hub tab owns the widget.

---

### [BUGFIX] Navigation, Theme Hooks & UI Thread Stability

- **Chip truncation** (`...` mid-word) â€” `_modernize_survey_bar()` resets all `chip_weights` to natural text widths after `_finalize_ui()`, eliminating the `Randâ€¦heme` / `Stanâ€¦heme` ellipsis caused by skewed proportional weights from prior sessions.
- **Inter-chip spacing** â€” survey bar chip gap reduced from 8 px to 4 px for a denser, less sparse top bar.
- **Randomize/Standardize theme chips** â€” suppressed in Modern mode via `bar._hidden`; Modern's fixed palette makes them irrelevant and they were appearing as stale menu noise.
- **`QWIDGETSIZE_MAX` crash** â€” `QtWidgets.QWIDGETSIZE_MAX` is not exposed in PySide6; replaced with the Qt-spec literal `16777215` to prevent `AttributeError` on launch.
- **Orphaned object names** â€” `modernZoneTitle` / `modernZoneSubtitle` in `ui/mission_review.py` were artefacts of the zone architecture with no matching QSS rules; corrected to `modernTabSectionTitle` / `modernIntentHint`.
- **UI thread isolation** â€” `eventFilter`, `_on_qv_show`, `_on_qv_hide`, `_on_modern_tab_changed`, `_on_bridge_started` Smart-Peek, `_settings_nav_select`, `reveal_mission_review_tab`, and `hide_mission_review_tab` are all wrapped in `try/except`. A UI interaction exception can no longer propagate to the `bridge_core` asyncio serial loop.
- **Telemetry chip padding** â€” inner horizontal padding corrected to 15 px (spec-aligned) from 14 px.

---

## v1.17.85

- **System Audit â€” release hardening** â€” code hygiene, error boundaries, and asset alignment pass before GitHub release. (1) **Hygiene**: removed unused `create_diagnostics_controls` import from `ui/modern.py`; removed legacy `/* Settings (nested tool-drawer tabs) */` comment from `ui/modern_styles.py` (artefact from the old `QTabWidget` era); updated stylesheet docstring to remove stale v1.17.77 version reference; fixed orphaned `modernZoneTitle` / `modernZoneSubtitle` object names in `ui/mission_review.py` â†’ now correctly `modernTabSectionTitle` / `modernIntentHint` so both headline and summary receive proper QSS styling. (2) **Error boundaries**: all tab-switching and visibility paths that could propagate to the bridge serial loop are now wrapped in `try/except`: `eventFilter` (highest-risk â€” `event.pos()` type guard), `_on_qv_show`, `_on_qv_hide`, `_on_modern_tab_changed`, `_on_bridge_started` Smart-Peek, `_settings_nav_select`, `reveal_mission_review_tab`, `hide_mission_review_tab`. A UI interaction error can no longer propagate to `bridge_core`. (3) **Asset alignment**: Telemetry chip horizontal padding corrected to 15 px (was 14 px); Hub and Telemetry tabs confirmed on `#0a0e14` / `MODERN_SURFACE` palette throughout.

## v1.17.84

- **Settings â€” full Modern UI makeover across all 7 sections** â€” comprehensive QSS cascade applied inside `#modernSettingsStack` context covering all sections without touching underlying widget trees or mixin attributes. Changes: (1) GroupBoxes â†’ dark surface cards with rounded corners, blue accent titles. (2) All inputs (QLineEdit, QSpinBox, QComboBox) â†’ dark `MODERN_SURFACE_ALT` with blue focus ring. (3) Checkboxes and radio buttons â†’ custom dark square/circle indicators with blue checked state. (4) Buttons â†’ uniform dark chip style with blue hover; Preset Load gets blue tint, Delete gets red tint. (5) Preset list â†’ dark surface with blue selection highlight, hover row. (6) Phone dashboard cards (`#phoneDashboardCard`) â†’ rounded dark cards, blue card titles, green status labels. (7) Guide text browsers â†’ `MODERN_TERMINAL_BG` background, dark tab bar. (8) Diagnostics iOS-card toggles and splitter handle â†’ dark surface styling. (9) Plain text areas (Inject/Diagnostics) â†’ terminal dark mono. Scroll host backgrounds fixed to `MODERN_BG` throughout.

## v1.17.83

- **Settings tab redesigned â€” sidebar + stacked content** â€” replaced the nested `QTabWidget` (horizontal sub-tabs inside the main Settings tab) with a VS Code-style vertical sidebar nav + `QStackedWidget` content area. Left sidebar (152 px, `MODERN_SURFACE` bg) lists all 7 sections (Presets âš™, Phone ðŸ“±, NMEA ðŸ“¡, Diagnostics ðŸ”, Inject ðŸ’‰, Terminal âŒ¨, Guide ðŸ“–) with a 1 px separator line. Active item has a blue left-border accent, blue text, and a subtle blue tint. Content fills the remaining width. All section content (Presets, Phone, NMEA, Diagnostics, Inject, Terminal, Guide) is unchanged.

## v1.17.82

- **Modern Hub: card scroll fills full tab height** â€” the root cause of the empty gap was `scroll.setMaximumHeight(cards_view_h)` inside `ConnectionHubWidget._build_cards_pane` capping the scroll area at 184 px. In `_build_hub_tab` the cap is now released (`setMaximumHeight(QWIDGETSIZE_MAX)`, policy `Expanding`) so the card grid stretches to fill the whole tab. Other layouts (Standard, Field) are unaffected. Floating QR overlay restored â€” user prefers the draggable chip.

## v1.17.81

- **Modern: Hub tab fills + floating QR removed** â€” (1) `ConnectionHubWidget.standalone` cards pane now uses stretch=1 so the card grid fills all available vertical space instead of leaving a dead void below the two fixed rows. Hub tab widget's size policy changed from `Minimum` to `Expanding` so the tab's height is fully used. (2) `refresh_connect_qr_overlay` now returns immediately when `_ui_mode == "modern"`, suppressing the draggable `ConnectQrFloat` that was overlaying tabs (phone QR is already available inline in Settings â†’ Phone). (3) Hub tab margins trimmed to 0 so cards reach the edges cleanly.

## v1.17.80

- **Modern: duplicate ConnectionHub + theme chips fixed** â€” (1) `build_diagnostics_tab` now accepts a `skip_hub=False` keyword; Modern's `_build_settings_tab` passes `skip_hub=True` so the Diagnostics sub-tab no longer instantiates a second `ConnectionHubWidget`. Build order inside `__init__` was also flipped (settings â†’ hub) so `self.connection_hub` is unambiguously the Hub tab's widget when `_finalize_ui` wires it up. (2) `_modernize_survey_bar` now adds `randomize_theme` and `standardize_theme` to the bar's hidden set before rebuilding, removing those two chips from Modern where the fixed dark stylesheet makes them irrelevant.

## v1.17.79

- **Survey bar chip fix + Hub auto-discovery** â€” (1) `_modernize_survey_bar()` runs after `_finalize_ui()` and does two things: reduces inter-chip spacing from 8 px to 4 px, and resets all `chip_weights` to values derived from each chip's natural text width â€” eliminating the "Randâ€¦heme" / "Stanâ€¦heme" middle-ellipsis truncation without making short chips ("HUD") unnecessarily wide. Weights are persisted so the reset survives restarts. (2) `_on_modern_tab_changed` wires a one-shot `QTimer` that triggers `_on_hub_refresh_discovery` the first time the Hub tab is opened, so the device list populates automatically instead of showing a blank area waiting for a manual Refresh click. (3) Hub empty-state instructional text updated from "Connect â†’ Serial & network" to "Control tab".

## v1.17.78

- **Hub tab + Guide refinement** â€” Two quality-of-life improvements. (1) **Hub tab**: removed the duplicate Refresh/Unlock action bar that was appended below `ConnectionHubWidget` (those buttons already exist inside the widget itself); the Hub now has zero wasted space. (2) **Guide aesthetic overhaul** (`ui/tool_tabs.py`): replaced the parchment `#f8f3e8` HTML background that clashed with the dark Modern palette with a fully dark theme matching `#0a0e14` (bg), `#c8d8f0` (body text), `#60a5fa`/`#93c5fd` headings, `#67e8f9` code chips, and a styled left-border `.note` callout block. (3) **Guide content rewrite**: all five tabs ("Start here", "UDP", "TCP Client", "TCP Server", "Checklist") now reference Modern UI navigation â€” **Control tab** (was "Connect tab"), **Settings â†’ Presets/NMEA/Diagnostics/Phone** (was "Tools â†’ â€¦"), **â–¶ Start in the header** (was "Run bridge panel â†’ Start bridge"), **Telemetry tab for Serial/Network chips** (was "bottom status bar"), **Hub tab for Unlock COM** (was "connection hub"). Removed references to "Standard layout", "Field/Minimal" layout variants, and "Tools drawer" terminology throughout.

## v1.17.77

- **Modern layout â€” persistent Global Header Strip + Smart-Peek + Quick-View** â€” Three interaction flow improvements to the tab-per-panel layout. (1) **Persistent Global Header Strip**: a dedicated 40 px row sits between the survey bar and the tab bar and contains â–¶ Start, â–  Stop, the colour-coded status banner, version chip, and COM lock chip â€” always visible no matter which tab is active. (2) **Smart-Peek**: when the bridge starts `_on_bridge_started` automatically navigates to the Log tab so the operator immediately sees data without manually switching. (3) **_QuickViewPopup**: hovering over the "Telemetry" or "Hub" tab header for 320 ms shows a non-modal 3-row preview (Serial Â· Network Â· Session for Telemetry; COM Â· Port Â· Status for Hub) positioned just below the hovered chip â€” lets the operator monitor state without leaving Log. Popup is mouse-transparent and auto-hides on hover-out (180 ms debounce). Active tab indicator upgraded to a 3 px `#60a5fa` bottom border with a top-to-bottom blue-gradient glow background. Tab horizontal padding widened to 15 px for legibility.

## v1.17.76

- **Modern layout â€” unified compact header + command tab bar** â€” Navigation density pass. The separate 54 px Start/Stop chrome strip is gone; run controls (â–¶ Start, â–  Stop, inline status banner, version chip, COM lock chip) are now injected into the right side of the survey bar, collapsing two stacked rows into one 40 px unified header. Net vertical saving: ~66 px. Survey quick-action chips reduced 25 % in height (`padding: 4px 9px`, `font-size: 9pt`). Main tab bar receives a dedicated `#05070a` background rail (visually distinct from the `#0a0e14` content area), with tabs tightened to `padding: 7px 14px` / `9pt` weight â€” a dense command-bar feel rather than oversized buttons. Footer simplified to 24 px (backup status + version only; `lbl_stats` lives in the Telemetry tab). All tab content areas remain flush and aligned across tab switches.

## v1.17.75

- **Modern layout â€” tab-per-panel** â€” Complete rewrite based on user preference. Every panel is a first-class tab: **Log**, **Control**, **Hub**, **Settings**, **Telemetry**. No floating tiles, no forced splits, no locked background layer. A compact always-visible chrome strip (54 px) sits below the survey bar and holds Start/Stop buttons, an inline status banner with a colour-coded left border, and the COM lock chip + session stats. The main `QTabWidget` fills the rest of the window; tabs are reorderable by drag. The Settings tab contains the nested Presets / Phone / NMEA / Diagnostics / Inject / Terminal / Guide sub-tabs. Control tab shows serial + network config side-by-side. Last active tab is saved and restored. Mission Review tab appears after Stop (if backup was active).

## v1.17.74

- **Modern layout â€” HUD overlay architecture** â€” Complete rewrite. Log conduit now fills the entire canvas (full height Ã— full width, no splitters, no columns). Control Panel, Settings, Connection Hub, and Telemetry are refactored into `HudModule` floating overlay cards that sit on top of the log. Each card is semi-transparent (`rgba(10, 18, 30, 215)` background + drop shadow) and pinned by default to a corner of the canvas (Control â†’ top-left, Settings â†’ bottom-left, Hub â†’ top-right, Telemetry â†’ bottom-right). **Interactions**: drag the header to free-float the card anywhere; single-click header to toggle Pin/Float; double-click header to expand/collapse; `âŠž/âŠŸ` button for explicit pin control. **HUD View Bar** â€” thin strip below the survey bar with four toggle buttons to show/hide individual modules plus a "Reset HUD" button. All visibility, pin, collapse, and float-position states persist to `hud_states` in `ui_prefs.json`. Removed all `QSplitter` references. Text is `#f8fafc` (off-white); headers use `#3b82f6` accent blue; borders removed in favour of drop shadows.

## v1.17.73

- **Modern layout â€” Module-Container architecture (floating cards)** â€” Complete architectural rewrite. Replaced all `QSplitter` logic with a `ModernModule(QWidget)` base class and a `QHBoxLayout`-of-`QVBoxLayout` column system. Each of the five panels (Control Panel, Settings, Core Conduit, Connection Hub, Telemetry) is now an independent floating card with: `#141a22` background, `8px` border-radius, `10px` outer margin, and a `15px` internal padding. Card header is a clean strip with a left-aligned title and a right-aligned `âœ• / â–¼` toggle button. Clicking `âœ•` collapses a card to its 40 px header strip; clicking `â–¼` or the title re-expands it. Remaining expanded cards in the same column automatically fill the freed space via `QSizePolicy.Expanding`. Window background is `#0a0e14`; card gaps reveal this background for the "floating" look. Collapse/expand state persists across restarts (`modern_module_states` key in `ui_prefs.json`). Footer has an **Expand all** button that expands all collapsed panels at once. Session telemetry (`lbl_stats`) promoted into the Telemetry card for tighter context.

## v1.17.72

- **Modern layout â€” swappable panel grid** â€” Replaced QDockWidget (snapping, immovable Pipeline) with nested QSplitters (smooth continuous drag in both X and Y). Every panel now has a header bar with a `â‡„` swap button; clicking it shows a menu to swap that panel with any other slot. All 5 panels (Control, Settings, Core conduit, Connection Hub, Telemetry) are in 5 named slots (left_top, left_bottom, center, right_top, right_bottom) and can be placed in any order. Slot assignments and splitter sizes auto-save to `modern_layout` in `ui_prefs.json`. "Reset layout" in the footer restores defaults in-place instantly.

## v1.17.71

- **Modern dock UX fixes** â€” Control panel default height increased to 480px so the Serial link and Network path groups are both visible on launch without scrolling. Removed redundant subtitle from Control panel dock (dock title already names it). Removed "Core conduit" zone title from log panel (log fills to the top edge). Reset layout now works in-place â€” no relaunch required. Dock title bars now show a 3px accent left border as a visual drag hint; hover brightens it.

## v1.17.70

- **Modern layout â€” free-form QDockWidget grid** â€” All four panels (Control panel, Settings, Connection Hub, Telemetry) are now `QDockWidget`s inside an inner `QMainWindow`. Drag any panel's title bar to move it to the left, right, top, or bottom edge, stack panels as tabs, or float them as independent windows. Settings panel is fully uncapped â€” give it as much space as you want. Dock state auto-saves on every resize/move and restores on relaunch. A **Reset layout** button in the footer clears the saved state (relaunch to restore factory positions).

## v1.17.69

- **Modern layout â€” free-form 2Ã—3 splitter grid** â€” Removed the fixed 2:6:2 constraint entirely. Left column splits vertically into **Control panel** (top) and **Settings** (bottom); right column splits into **Connection Hub** (top) and **Telemetry** (bottom). All three horizontal and both vertical splitter positions are independently draggable and auto-saved to `ui_prefs.json` (`modern_layout` key). Settings panel (`modernToolsDrawer`) has no height cap â€” drag the left vertical splitter to give Presets / Phone / NMEA / Diagnostics / Inject as much space as needed. Added `load_modern_layout_prefs` / `save_modern_layout_prefs` to `ui_prefs.py`.

## v1.17.68

- **Modern layout hierarchy** â€” Center conduit is now the unambiguous dominant anchor (log panel fills all vertical space). Right zone restructured with `QVBoxLayout`: **Connection Hub** sits at the top and expands to fill available height; five compact single-row **telemetry chips** (Serial / Network / NMEA / GNSS) are pinned below. Removed per-zone subtitle clutter from the conduit. Old multi-line telemetry cards replaced by slim horizontal chips. **Status Footer** â€” a new full-width 30 px strip at the bottom of the window replaces the `QStatusBar` chrome; carries the backup status chip, session stats, and version label. `QStatusBar` is retained as a zero-height invisible widget for mixin compatibility.

## v1.17.67

- **Mission Review (Modern UI)** â€” After **Stop bridge** with active backup, a **Mission Review** tab appears with backup throughput bar chart, data-health timeline (green/amber/red ticks), and **Quick Export** (timestamped zip: `.raw` + `mission_summary.txt` with duration, avg Hz, bytes). Standard/Field layouts keep the post-stop dialog.

## v1.17.66

- **Mission Summary** â€” After **Stop bridge**, if local black-box backup was active, a non-modal dialog reports bytes written, chunks dropped, and backup path. Zero-byte or missing/empty files raise **Warning: No data written**. Backup now flushes on `abort_now()` (normal Stop path).

## v1.17.65

- **Black-box backup audit** â€” Queue headroom raised to 8192 chunks (~32 MiB at 4 KiB reads); queue depth/max in stats; thread-safe immediate **Backup:** status refresh on disk/queue errors; compact elided status bar (`Backup: 1.2 MB`) with full path/bytes in tooltip (Modern layout safe on tactical displays).

## v1.17.64

- **Local black-box backup** â€” Optional raw COM safeguard (`core/local_logger.py`): every physical serial read is copied to `logs/backup_YYYYMMDD_HHMM.raw` on a dedicated writer thread with per-chunk `fsync`. Survives network/Tailscale outages; disk errors disable backup without stopping the bridge. Toggle in **Diagnostics â†’ Local black-box backup**; status chip **Backup:** on the status bar.

## v1.17.63

- **Modern layout redesign** â€” Ground-up **Streamlined Pipeline** UX: left control panel (serial + network), center **Core Conduit** live log (~56% width), right **Insight** rail (telemetry cards + Connection Hub). Fixed high-contrast palette; random theme is disabled so the survey top bar never clips or disappears. 14px scrollbars throughout.

## v1.17.62

- **Modern layout** â€” Third workspace (`ui/modern.py`): discovery-forward dashboard with high-contrast COM/LAN cards, wide scrollbars, centered live log, and connect/run modules. Layout chip cycles Standard â†’ Field â†’ Modern (via `ui/layout_switch_hook.py`).

## v1.17.61

- **Web network mode save** â€” Saving TCP client/server or UDP remote no longer snaps back to UDP listen. The web API was forcing UDP listen whenever listen host/port were in the patch; remote host/port now map to the correct desktop fields for each mode.

## v1.17.60

- **Web COM lock freeze** â€” `/ports/probe` and `/ports/unlock` no longer open COM on the Qt main thread (was blocking the UI for up to 5s). `/status` is read-only again (no main-thread wait on every poll).

## v1.17.59

- **Web COM lock** â€” Phone/dashboard `/status` exposes COM availability (checking / available / in use). **Start** is disabled when the configured port is busy, with a COM lock chip in the header and COM & ports panel (matches desktop Connect chip). **Test COM**, **Unlock**, and **Refresh** re-sync lock state. Server-side start validation blocks busy ports.

## v1.17.58

- **COM lock probe** â€” Fix chip stuck on â€œchecking availabilityâ€¦â€: probe results use primitive Qt signals (queued), no GUI-thread `wait()` on the worker, 4s watchdog timeout, and fewer duplicate probes during port refresh.

## v1.17.57

- **P0 COM reliability** â€” Background COM exclusivity probe on Connect: **COM lock chip** shows available vs in use, **Start** stays disabled while another app holds the port. Discovery hub marks the selected serial card **Port busy**. **Unlock** + **Refresh** re-probe. Serial auto-reconnect tracks USB **hwid** and follows COM re-enumeration (e.g. COM7 â†’ COM12 after cable bump).

## v1.17.56

- **Layout switch** â€” Top-bar **Layout** chip now works on a **single click** (was double-click only). Failed switches (bridge still running) no longer leave the chip disabled. **View â†’ Switch to Field layout** / **Switch to Standard layout** as a fallback. Compact **Standardize theme** tile reads **Slate** so it is not confused with Standard workspace layout.

## v1.17.55

- **Readability sweep (work PC)** â€” Brighter web scrollbars (11px, visible thumb on dark tracks). Dashboard `<strong>` hints no longer render browser-default black on dark panels. Desktop: styled `QScrollBar` handles, COM dropdown lists, and Tools/Connect/Discovery labels on dark tab surfaces.

## v1.17.54

- **Discovery COM contrast** â€” Web dashboard serial rows and COM `<select>` controls use explicit dark-surface backgrounds and readable text (fixes white-on-white COM lists on some work PCs). Desktop Connection Hub endpoint cards get matching QSS so COM/LAN cards are not unreadable on default Windows panel chrome.

## v1.17.53

- **Phone â€” Detect Tailscale / LAN** â€” Detect button now **overwrites** the Phone dashboard URL (fixes â€œnothing happensâ€ when a stale URL was seeded from another PC). Tailscale CLI tries `tailscale ip -4` then `tailscale ip` when `-4` fails on Windows. **Open local dashboard** always opens `http://127.0.0.1:PORT/` on this PC. Product UI defaults no longer ship a machine-specific `phone_base_url`.

## v1.17.52

- **Web dashboard log** â€” Removed non-working **Expand log (full screen)** from the log panel context menu and toolbar; clears any stale expand state on load.

## v1.17.51

- **GridStack reset** â€” **Reset layout** now destroys and rebuilds the grid from the real panel widgets (prunes empty placeholder tiles left by a bad `load()`). Saved layouts with fewer than four tiles are ignored on boot.

## v1.17.50

- **Web dashboard layout guard** â€” Ignore/sync-reject grid layouts with fewer than four tiles (fixes a one-panel dashboard after a bad save or dev test writing to real `ui_prefs.json`). API tests now use an isolated prefs file.

## v1.17.49

- **Product UI defaults â€” web dashboard layout** â€” Grid/classic dashboard tile order, collapse, chrome, map, and log panel prefs sync to `ui_prefs.json` via `GET`/`PUT /dashboard-layout` (debounced from the browser). **Save UI as product default** now includes `web_dashboard` (API token and log search text excluded). Open the dashboard once before saving so layout syncs from the browser.

## v1.17.48

- **Product UI defaults** â€” New installs and missing `ui_prefs.json` seed **Standard** layout from `assets/product_ui_defaults.json` (optional `product_ui_defaults.local.json` beside the exe for fleet overrides). **View â†’ Save UI as product defaultâ€¦** exports layout chrome only (not COM/UDP path presets). **View â†’ Reset UI to product defaultâ€¦** restores shipped/fleet layout for power users without wiping other prefs.

## v1.17.47

- **Taskbar / shortcut icon (shell tier)** â€” Small ICO layers now crop to connector ink, thicken strokes, and fill ~82% of the tile so the DB-9 logo stays visible (not a faint speck on a colored square).

## v1.17.46

- **Taskbar / title bar icon** â€” ICO layers at 48px and below now use a high-contrast shell variant (lighter DB-9 glyph, lifted tile, subtle ring) so the logo stays visible on dark taskbars; larger sizes keep the detailed squircle.

## v1.17.45

- **App icon / shortcuts** â€” Regenerated `app-icon.ico` with larger in-frame artwork (~92% vs 78%) so the DB-9 glyph reads clearly on taskbar and desktop shortcuts; added 512px and extra Windows DPI sizes. Desktop shortcut script prefers the built `serial-link.exe` icon (`exe,0`) for release folders.

## v1.17.44

- **In-app operator manuals** â€” **Tools â†’ Guide** buttons (**Getting startedâ€¦**, **Operator guideâ€¦**, **NORBIT DCTâ€¦**) and bench **Open operator guide** open formatted markdown inside Serial Link (Qt viewer, offline). Links between `.md` files stay in-app; http(s) links still use the system browser.

## v1.17.43

- **GETTING_STARTED.md** â€” Operator-first layout: field install and 15-minute bench walkthrough up front; developer paths, JSON tables, and terminal commands moved to an appendix. Notes to use **Tools â†’ Guide** in-app when browser shows raw markdown.

## v1.17.42

- **Web COM & ports** â€” **Test COM port** replaces **Apply COM** (probes open/close on the chosen port; use **Select** or Configuration to save the active COM). Unlock/probe failures no longer show as green success badges.

## v1.17.41

- **Terminal ping Save preset** â€” Save dialog prefills from the **current ping host** (updated on every Ping), not the last preset selected in the dropdown. Example: ping `pi-nd` then Save suggests `pi-nd`, not a previous name like `noah`.

## v1.17.40

- **Web phone landscape HUD** â€” On phone-sized landscape viewports, the dashboard header auto-hides Start/Stop and shows a compact line (`Running Â· COM7`) with brand and connection dot. Portrait layout unchanged; rotate to portrait to use run controls from the phone.

## v1.17.39

- **Web startup robustness** â€” Embedded uvicorn now runs with internal logging config disabled (fixes `Unable to configure formatter 'default'` on some PCs). Startup errors are reported accurately; non-bind failures no longer masquerade as `Port ... already in use`.
- **Guide visibility hardening** â€” Guide tab HTML now sets explicit background/text colors to avoid all-white rendering on some Windows theme/driver combos.

## v1.17.38

- **Portable build parity** â€” Bundle `bench_tcp_test.py` for Diagnostics P0 network auto; collect all `ui.*` submodules and pywinpty/winpty; resolve `bench_defaults.json` from `_MEIPASS`; clearer Web start errors when static or FastAPI/uvicorn missing. Post-build `check_frozen_bundle.py` validates helpers + dashboard assets (replaces narrow web-only check). `-SkipTests` release builds also install `requirements-web.txt`.

## v1.17.37

- **Frozen Web dashboard fix** â€” PyInstaller build now installs `requirements-web.txt` and bundles FastAPI, uvicorn, and `web/static` so **http://127.0.0.1:8765/** serves the operator UI from the `.exe` (was missing deps â†’ server failed or JSON-only `/`). Post-build `tools/check_frozen_web.py` guards the zip.

## v1.17.36

- **Windows font warning** â€” Terminal, log, and diagnostics use a DirectWrite-safe monospace font instead of legacy system fixed fonts (e.g. `8514oem`) that spam `qt.qpa.fonts: DirectWrite: CreateFontFaceFromHDC() failed` on startup.

## v1.17.35

- **Terminal ping presets** â€” **Delete** removes the preset chosen in the dropdown (with confirmation). Right-click a **Quick** chip to delete that preset.

## v1.17.34

- **Presets tab click** â€” Single click only selects a preset and fills the survey-network editor (PC IP, subnet, notes). **Load** or double-click applies COM/UDP/NMEA to Connect; no jump to the Log tab. Survey-bar **Presets** menu still quick-connects (apply + Start).

## v1.17.33

- **Layout switch zombie process** â€” Stop web server, discovery thread, and tray icon on the **old** window before creating the new layout (was starting duplicate background services). Tray destroyed on handoff; auto-discovery thread joins cleanly. Single-instance lock file prevents a second `python.exe` when one copy is already running.

## v1.17.32

- **Layout switch crash** â€” Switching Standard/Field no longer calls `app.quit()` when the bridge is stopped (old window close during handoff). Survey HUD and Dashboard close cleanly before layout swap; refresh paths guard deleted Qt widgets.

## v1.17.31

- **Dashboard + HUD** â€” Top bar **HUD** and **View â†’ HUDâ€¦** open **Survey HUD** (metrics) and **Dashboard** (bridge trust: Ready/Caution/Stopped, health chips, issues-only reliability checks). **View** also offers each window alone. Dashboard replaces the Beta HUD preview; slimmer layout (no duplicate Hz tiles).

## v1.17.30

- **Beta HUD (P0 preview)** â€” superseded by Dashboard in v1.17.31.

## v1.17.29

- **Fan-out probe fix** â€” `bench_fanout_probe.py` and automation use one bound socket per peer so bridge replies reach the listener (was split tx/rx ports).

## v1.17.28

- **P0 fan-out bench automation** â€” `bench_fanout_automation.py` headless: two UDP peers both receive `schedule_serial_to_net` inject (fan-out ON), then last-peer-only (fan-out OFF). Live mode registers peers when the GUI bridge holds the port. **Diagnostics â†’ Fan-out bench (auto)**; `verify_all.py` / `bench_all.py`. No HUD changes.

## v1.17.27

- **P0 bench automation** â€” `bench_network_automation.py` runs headless UDP zero-drop ingest + TCP reconnect (port 41099) when the bench UDP port is free, or a live UDP burst when the GUI bridge is already listening. Wired into `verify_all.py`, `bench_all.py`, and **Diagnostics â†’ Network bench (auto)**. No Survey HUD changes.

## v1.17.26

- **P0 network operator docs** â€” Added **Â§6.4 Network reliability checklist** to `docs/OPERATOR_GUIDE.md` (UDP listen direction, firewall, Fan-out vs last-sender, Extra TCP output, TCP client reconnect, Tailscale). `docs/GETTING_STARTED.md` points operators there; `test_operator_guide_network.py` keeps the section present.

## v1.17.25

- **P0 serial reconnect** â€” Clear partial NMEA assembly buffers after COM drop/reopen so reconnect cannot splice stale bytes; status bar highlights serial retry/disconnect and refreshes the COM list every few seconds during reconnect.
- **P0 raw binary** â€” Tests confirm RAW mode forwards binary payloads unchanged (no line assembly or rejects).

## v1.17.24

- **Layout switch crash** â€” Double-clicking the top-bar **Layout** control now runs a one-shot guarded transition; re-entrant toggles are ignored while the new window is being created/activated, preventing rapid double-click crashes.

## v1.17.23

- **P0 COM exclusivity** â€” Start now runs a synchronous COM preflight probe before async startup; when the port is busy, the dialog gives explicit recovery steps (close conflicting app, Connect â†’ Unlock, Refresh, replug) instead of a generic late failure.

## v1.17.22

- **P0 transport visibility** â€” Status-bar stats now turn into a high-contrast warning chip whenever drops, rejects, or queue backlog are present, so backpressure issues are immediately visible in Standard/Field layouts (not hover-only).

## v1.17.21

- **Survey HUD GNSS** â€” Idle stream shows **Idle** (not clipped â€œNo streamâ€); tighter badge padding in the HUD; badge width follows label text. Full meaning stays in the hover tooltip.

## v1.17.20

- **Tools sidebar (Standard)** â€” Fix wrong page after UI editor reorder: legacy prefs mapped **Terminal** â†’ **Inject** even when both tabs exist, duplicating **Inject** and scrambling the stacked pages. Order is deduped on load/save; nav rows store the correct stack index.

## v1.17.19

- **Standard layout** â€” Fix startup crash building Tools sidebar (Presets factory must accept the window like other tool tabs).

## v1.17.18

- **Tray Exit** â€” Restored `_stop_bridge()` as an alias of `stop_bridge()` so tray **Exit** cannot crash if an older `mixin.py` or cached copy still calls the legacy name.

## v1.17.17

- **UI editor (Standard)** â€” **Tools tabs** page reorders and hides Tools sidebar items (Presets, Phone, NMEA, Terminal, â€¦); Field drawer tabs use the same editor page.

## v1.17.16

- **Auto-connect on GNSS** â€” Fix crash: auto-start now calls `_validate_before_start()` (was missing `_validate_start`).

## v1.17.15

- **Connect (Standard)** â€” **?** network guide beside Fan-out: popout explains Listen host/port, Fan-out, Extra TCP output, and Advanced network.

## v1.17.14

- **Connect** â€” Rename **TCP sink mirror** to **Extra TCP output**; clearer tooltip and operator guide notes.

## v1.17.13

- **Start / Stop** â€” Ignore double-clicks while starting or stopping; brief COM release delay after Stop before the next Start; reset UI if a background start was cancelled.

## v1.17.12

- **Tools â†’ Terminal** â€” Fix doubled keystrokes on Windows (IME + keyPress dedupe); disable **PSReadLine** in embedded PowerShell so backspace and line editing work in the PTY.

## v1.17.11

- **Tools â†’ Phone** â€” Short in-tab **API token** help: purpose, when required (LAN/Tailscale), **Generate** vs custom token / setup link.

## v1.17.10

- **Web dashboard map (grid)** â€” Map fills the tile height in grid layout; removed Leaflet layer-control square (Street/Satellite via right-click or map **â‹¯** menu).

## v1.17.9

- **Web grid dashboard** â€” Strip/remove legacy layout banner on load (fixes cached HTML showing banner text without the blue box). Dashboard HTML responses use `no-store` cache headers.

## v1.17.8

- **Web grid dashboard** â€” Removed the top blue layout banner; **Classic layout** link and **Reset layout** stay in the page footer. **Lock layout** remains in the header.

## v1.17.7

- **Survey HUD â€” Corner mode GNSS** â€” GNSS fix tile spans two columns; Corner uses a 2-column session grid; narrow tiles show **RTK-F** (etc.) with full **RTK fixed** on hover. Relayout after resize updates the label.

## v1.17.6

- **Survey HUD / status bar GNSS** â€” Hover shows full fix type (e.g. **RTK fixed**), satellites, HDOP, summary, and assessment â€” not only the short POSPac hint. HUD GNSS badge minimum width increased so labels clip less in compact layouts.

## v1.17.5

- **Tools â†’ Guide** â€” Rewritten for current UI: **Start here** tab, correct Connect vs Presets paths, **Listen host/port** vs UDP remote **Host/Port**, exact Advanced network and Fan-out labels. Doc buttons unchanged; Phone/Web still pointed to **Tools â†’ Phone**.
- **Product demo removed** â€” Presenter teleprompter and `bridge_gui.py --demo` removed (stale script). Use Guide + **GETTING_STARTED.md** / **OPERATOR_GUIDE.md** instead.

## v1.17.4

- **Tray Exit / close** â€” Tray icon is torn down and `QApplication.quit()` runs so the process exits (no Task Manager zombie). Closing the window while the bridge is stopped also quits fully.

## v1.17.3

- **Tray Exit** â€” Fixed crash (`_stop_bridge` missing); tray **Stop bridge** and **Exit** now call `stop_bridge()` like the main UI.

## v1.17.2

- **Theme studio** â€” Zone-order swatches now reflect the selected built-in theme (Forest, Ocean, etc.), not a fixed generic palette. **Arctic Day** removed (saved `arctic_day` maps to Field Slate). **Standardize** button restored beside **Randomize** (same as survey-bar standardize theme).

## v1.17.1

- **Web API auto-start** â€” Dashboard defaults **on** for new/migrated prefs; server starts after the UI is ready with a one-shot retry if the port is slow to free. Bridge **Start** also re-checks the listener (fixes â€œhad to toggle bridgeâ€ when launch bind raced).

## v1.17.0

- **Tray-first monitoring** â€” Closing the window while the bridge is running hides to the **system tray** (bridge keeps running). Tray menu: Show, Stop bridge, Exit; tooltip shows Serial | Network status.
- **Less UI personalization** â€” Connect section style is fixed to **pill** cards (removed Theme studio picker). Theme tab copy defers to defaults for field use.

## v1.16.2

- **Tools â†’ Terminal** â€” **Open externalâ€¦** launches a visible console from the GUI build (Windows `CREATE_NEW_CONSOLE` + `cmd start` fallback; shows an error dialog if launch fails).

## v1.16.1

- **Tools â†’ Terminal** â€” Compact Shell row; **Ping** host field with **Saveâ€¦** presets, dropdown, and quick bubble buttons (first five presets). Runs in the embedded shell or subprocess when pywinpty is missing.

## v1.16.0

- **Public release defaults** â€” Shipped `bench_defaults.json` uses neutral placeholder COM/LAN values (no survey-site IPs in the zip). Optional `bench_defaults.local.json` (gitignored; see `bench_defaults.local.json.example`) overrides for your desk/boat without baking personal config into `serial-link.exe`.

## v1.15.4

- **Rotating file log** â€” **Keep old files: None** â€” single-file mode clears the log at roll size instead of keeping `.log.1` siblings (and removes stale rotated files when selected).

## v1.15.3

- **Diagnostics â€” Rotating file log** â€” Renamed **Backups** to **Keep old files** with clearer tooltips; retention hint explains `.log.1` rollover and disk total (not â€œcloud backupâ€).

## v1.15.2

- **App icon** â€” `make_app_icon.py` strips the white matte, composites on dark `#1a1d27` squircle (matches UI); optional `assets/app-icon-source.png` for re-exports.

## v1.15.1

- **Tagline** â€” **Ethernet â†” serial** on Connect chrome, layout picker, web dashboard header, and Windows exe description (matches RJ-45 + DB-9 icon).

## v1.15.0

- **Rebrand: Serial Link** â€” Product name, window titles, web dashboard, and Windows build artifacts are now **Serial Link** (`serial-link.exe`, `serial-link-vX.Y.Z-win64.zip`). New DE-9 serial connector app icon. GitHub repo name unchanged.

## v1.14.5

- **Web position map â€” Satellite layer** â€” **Street** (OpenStreetMap) or **Satellite** (Esri imagery + place labels) via the mapâ€™s layer control (top-right); choice persists in the browser. Right-click **Position map** for the same shortcuts.

## v1.14.4

- **Web Survey monitor â€” Rows vs Columns** â€” **Rows** uses bordered metric tiles inside collapsible sections; **Columns** uses a true aligned grid table (header row + value row, column borders) per section so the two modes read clearly different.

## v1.14.3

- **Web Survey monitor â€” Simple layout** â€” Flattens nested section grids (fixes vertical letter-stacking and cramped tiles); clean 3Ã—2 stat grid + GNSS strip; UDP shows port only (`10110`); nowrap values and tighter labels.

## v1.14.2

- **Tools â†’ Terminal (typing)** â€” Backspace sends Windows BS (`0x08`) instead of DEL; PTY writes run on a background I/O thread so keys do not block the UI; small shell echo is painted immediately (bulk output still batched).

## v1.14.1

- **Tools â†’ Terminal (smoothness)** â€” Batched PTY output (~28 ms) so the UI does not repaint on every byte; larger reads; debounced window resize; no outer scroll wrapper (terminal fills the pane); PowerShell starts with `-NoProfile` for less startup noise. Click **New session** to start (no auto-spawn on tab open).

## v1.14.0

- **Tools â†’ Terminal** â€” Embedded local shell (PowerShell / cmd via optional **pywinpty** on Windows); **Open externalâ€¦** when pywinpty is missing. Use for bench scripts and COM tools, not bridge traffic.
- **Tools â†’ Inject** â€” Former â€œTerminalâ€ NMEA inject tab moved here; saved tab order migrates `Send` / old `Terminal` â†’ **Inject**. Product demo and Connect quick **Sendâ†’COM** unchanged.

## v1.13.14

- **PassThru label** â€” NMEA passthrough shows as **PassThru** on status chips and web Survey monitor (internal mode unchanged).
- **Survey monitor Simple** â€” Flat 2-column stat cards (state, transport, COM, UDP port, NMEA, Hz, GNSS) matching Rows styling; hides backpressure/extra Hz/line counters for narrow tiles.

## v1.13.13

- **Tools â†’ Phone port/status** â€” Wider port spin box (left-aligned value, no `max-width` squeeze); **This PC** URL on two lines with full-width wrap; both cards min-width 320px.

## v1.13.12

- **Tools â†’ Phone** â€” Extra spacing and top alignment for the **This PC** dashboard URL row so it no longer crowds the port spin box.

## v1.13.11

- **Phone port spin box** â€” Removed custom QSS â€œtriangleâ€ arrows on `webPortSpin`; uses standard Qt up/down step buttons (still gated by unlock).

## v1.13.10

- **Tools â†’ Phone â€” Server card alignment** â€” Every row uses a real label (`Web API`, `Port`, `This PC`, â€¦); field hosts span the column so checkboxes and buttons stay left-aligned with the port spin (fixes centered Enable/Open). Local dashboard URL on its own labeled row below port.

## v1.13.9

- **Tools â†’ Phone â€” Server card** â€” Same `QFormLayout` rows as Phone Pairing: port controls on their own row, dashboard URL/status on the next row (no overlap), checkboxes aligned in the field column. Inline actions use `QStyle` icons (`SP_BrowserReload`, `SP_FileIcon`, etc.) with `webIconRole` for optional custom SVG.

## v1.13.8

- **Tools â†’ Phone panel alignment** â€” Strict `QFormLayout` columns (right-aligned labels, left-aligned fields), left-aligned checkboxes, text-only inline action buttons (no broken theme icons), listen URL under port with dimmed `webListenStatus` styling.

## v1.13.7

- **Tools â†’ Phone panel UX** â€” Two cards (**Server & Network** / **Phone Pairing**), inline icon actions beside URL and token fields, lock/unlock port control with status text, subtle dark styling (no yellow port highlight), tooltips and **?** help on labels instead of paragraph copy.

## v1.13.6

- **Web default = grid layout** â€” `GET /` serves the GridStack dashboard; classic accordion UI remains at `/static/index.html` (linked from grid banner/footer). Fixed `build_gridstack_index.py` script injection when `dashboard.js` uses `?v=` query (grid page was missing GridStack JS).

## v1.13.5

- **Grid map â‹¯ menu (stale script fix)** â€” `gridstack-layout.js` patches the menu when an old cached `dashboard.js` is loaded (typical with frozen v1.13.0 zip). Map actions: center on fix, clear/fit track, etc. Web API serves `.js` with `Cache-Control: no-store`.

## v1.13.4

- **Web map context menu** â€” Map right-click / â‹¯ now lists center on fix, track, and related actions first; clicks on the Leaflet map resolve to the map panel. `dashboard.js?v=` cache bust so browsers load the latest script.

## v1.13.3

- **Web dashboard â‹¯ chrome menus** â€” Panel-specific actions: **Map** â€” center on fix, fit/clear track, show/hide track, toggle map, refresh size; **Log** â€” pause, auto-scroll, clear, expand; **Survey monitor** â€” expand all sections; **COM / Discovery / Tools** â€” refresh, unlock, copy setup link.

## v1.13.2

- **Removed Layout 2.0 beta** â€” Dropped `/static/layouts/v2/` trial; **GridStack** remains the customizable web layout (`/static/layouts/gridstack/`). Focus next: tile resizeâ€“aware panels and map/tools enhancements on the grid.

## v1.13.1

- **Fix: frozen build console storms** â€” Diagnostics and verify scripts no longer spawn system `python.exe` windows (use bundled `nmea-serial-bridge.exe --run-helper â€¦`). `arp`/`ipconfig`/`netstat`/`bench_stress` subprocesses use `CREATE_NO_WINDOW` on Windows. **Do not use v1.13.0** if you see flashing blank terminals.

## v1.13.0

**Release build** â€” Web operator dashboard + GridStack beta (v1.11â€“1.12) packaged in frozen `web/static` (standard UI at `GET /`, grid trial at `/static/layouts/gridstack/`). Field strip layout tests aligned with current compact strip sizes. Use `.\release.ps1` for zip + optional `gh release`.

**Known issue:** v1.13.0 may flash many console windows when Diagnostics or LAN discovery runs â€” replaced by v1.13.1.

- **Web dashboard** â€” Status, config, discovery, start/stop, live log, position map, Survey monitor (Rows / Columns / Simple), section chrome menus (hide headers, terminal-only log, prioritize map), context menu stability.
- **GridStack beta** â€” Drag/resize tiles, â–²â–¼ reorder, collapse shrink, Lock layout, touch **â‹¯** / long-press, iPhone resize bars, left-edge width bar, optional hide resize bars.
- **Static routing** â€” Directory `index.html` served for layout folders (`html=True`).
- **Qt** â€” UI journey modernization (008), returning-user launch restore, Product Demo snapshot (v1.10).
- **Release tooling** â€” `build.ps1` uses `tools/run_unittests.py`; `verify_all` tolerates expected bridge test log tracebacks; `docs/RELEASE_CHECKLIST.md` added.

## v1.12.8

- **Survey monitor Columns** â€” True two-row table per section (all labels on one line, all values on the next); no stretched mini-columns. GNSS spans full width. Switching back to Rows restores normal stat cards.

## v1.12.7

- **Grid layout lock** â€” **Lock layout** checkbox in the header (grid beta page) saves tile positions/sizes/order; disables drag, resize, â–²â–¼ reorder, and resize bars until unchecked.

## v1.12.6

- **Survey monitor Columns layout** â€” Fixed Columns mode on grid/standard dashboard: true table per section (label row, value row) instead of looking identical to Rows.

## v1.12.5

- **Web dashboard context menu** â€” Options menu no longer closes every ~1â€“2 s from log autoscroll; removed global scroll-dismiss, added brief open guard, outside-tap/click to close.

## v1.12.4

- **GridStack resize bars** â€” Left-edge width bar added (mirrors right). **Hide resize bars** in â‹¯ / long-press menu restores corner resize on desktop when hidden.

## v1.12.3

- **GridStack touch resize** â€” Full-width blue **bottom resize bar** on each tile (and right edge on phone) for reliable iPhone resize; disables tiny corner handles on coarse pointers. Live height/width updates while dragging.

## v1.12.2

- **Touch layout options** â€” **â‹¯** on each section header opens the same menu as right-click (hide header, terminal-only log, prioritize map, Survey monitor layouts). Long-press (~Â½ s) on a section also opens it on phone. When the header is hidden, a floating **â‹¯** appears on the tile.

## v1.12.1

- **GridStack iPhone resize** â€” Resize handles always visible with larger touch targets; fixes tile resize on iPhone after autohide/hover-only handles.

## v1.12.0

- **GridStack + standard controls** â€” Grid layout beta now has â–²â–¼ section reorder (swaps tile positions), plus existing drag/resize, collapse shrink, and right-click chrome (hide headers, terminal-only log, prioritize map, Survey monitor layouts). â–²â–¼ no longer starts a drag on grid tiles.

## v1.11.8

- **Survey monitor columns layout** â€” Fixed crushed vertical text; columns mode now shows labels on top and values below, left-to-right (e.g. State / Running Â· COM port / COM3 Â· Baud / 115200).

## v1.11.7

- **Survey monitor layouts** â€” Right-click Survey monitor (header or inside): **Rows** (default sections), **Columns** (table-style headers over values), **Simple** (state, transport, GNSS badge, sats, HDOP only; keeps green/red/blue GNSS and transport alerts).

## v1.11.6

- **GridStack collapse** â€” Collapsing a section (â–¶) now shrinks the tile to header height; expanding restores the previous tile size. Saved layout keeps expanded heights, not collapsed stubs.

## v1.11.5

- **Web dashboard chrome menus** â€” Right-click any section header (â–¼ label bar) to hide that header or all headers; right-click **Live log** for **Terminal only**; right-click **Position map** for **Prioritize map**. Choices persist in the browser. Works on standard and GridStack layouts.

## v1.11.4

- **GridStack beta** â€” Removed per-tile viewport fullscreen (â›¶ / right-click restore); drag-resize grid only.

## v1.11.3

- **GridStack tile fullscreen** (reverted in v1.11.4) â€” Experimental overlay fullscreen per panel.

## v1.11.2

- **GridStack beta polish** â€” Default 12-column tile positions (COM + Survey top row, map/config second, tools/discovery, full-width log); disable CSS grid conflict on beta page; **Reset layout** button; layout storage key `v2` (clears old left-stacked saves).

## v1.11.1

- **Web static â€” directory index** â€” `StaticFiles` now uses `html=True` so `/static/layouts/gridstack/` (and other folders with `index.html`) return the page instead of FastAPI `{"detail":"Not Found"}`.

## v1.11.0

- **Web dashboard â€” GridStack beta** â€” Standard layout unchanged at `GET /`; optional trial at `/static/layouts/gridstack/` with vendored GridStack 10.3.1 (drag/resize tiles, layout in `localStorage`). Baseline snapshotted in `web/static/layouts/1.0/`. Footer link **Grid layout (beta)** on the standard page.

## v1.10.0

- **UI journey modernization (008)** â€” Returning-user launch restore, UI audit inventory (zero P0), Product Demo session snapshot/restore, web dashboard handoff copy aligned with **Tools â†’ Phone**, and `test_web_handoff.py` / `test_demo_snapshot.py` gates.

## v1.9.86

- **Returning user (008 US1)** â€” Launch restores `last_preset` through one path in `_finalize_ui`; Field strip shows active preset and NMEA mode; tests for `last_preset` and recent-session apply.
- **UI audit (008 US2)** â€” `docs/ui-audit-inventory.md` with all P0 closed; operator docs no longer mention removed **Reset sizes**; Phone tab auto-enables **Show QR** when a saved token exists; Standard default window 1200Ã—720.

## v1.9.85

- **Product Demo â€” session restore** â€” Opening **View â†’ Product demo** snapshots your COM, network, NMEA, preset, and bridge run/stop state; closing the presenter restores it within a few seconds. Demo steps no longer write presets or recent sessions while presenting. Status banner shows **Demonstration** while the dialog is open. **Reset demo script** rewinds the presenter to Welcome without touching Connect.

## v1.9.84

- **Tools â†’ Phone â€” port â–²â–¼** â€” Web API port step buttons use a visible button strip and triangle arrows (dark/light themes); no more invisible controls on the right.
- **Connect toolbar** â€” Removed **Reset sizes** (disclosure layout no longer uses splitters; button had no effect). Saved toolbar prefs drop `reset_sizes` automatically.

## v1.9.83

- **Tools â†’ Phone â€” QR panel** â€” Embedded Phone-tab QR refreshes when prefs load (no stale â€œGenerate a token firstâ€ while a token exists). Floating Connect QR hides on **Tools â†’ Phone** so it does not stack on the built-in QR; it returns on Connect/Log.

## v1.9.82

- **Tools â†’ Phone â€” Web API port spin** â€” Port field is compact with â–²â–¼ pinned on the right edge (no wide empty gap). Unlock uses read-only lock instead of disabling the whole control so both step buttons work. Port prefs save immediately when you change the value.

## v1.9.81

- **Standard Connect â€” Serial & network side-by-side** â€” **Serial** and **Network (UDP listen)** sit in one row (like your layout mockup) so both are visible without scrolling the connection section. Default panel height targets updated for the shorter block.

## v1.9.80

- **Tools â†’ Phone â€” Web API port lock** â€” Dashboard port spin box ignores the mouse wheel (scroll moves the page, not the port). Port is locked by default; check **Unlock port (10 s)** to edit, then it auto-locks again.

## v1.9.79

- **Presets + NMEA mode** â€” Tools â†’ Presets **Save** / **Save asâ€¦** now stores the current **Passthrough / Strict / Raw** choice from Tools â†’ NMEA (and strict sentence-type checkboxes). Loading a preset restores those radios; log line includes the mode. Existing presets without `nmea_mode` default to passthrough on load.

## v1.9.78

- **Web COM & ports + Discovery Select** â€” Fixed the same silent click block on COM rows while Running (`pointer-events: none`). Row/Select taps always reach the handler: network updates live, COM shows **Stop first** with a visible warning. One click delegate on the dashboard panel root; token errors show in the relevant section.

## v1.9.77

- **Web Discovery Select** â€” Network adapter rows and **Select** work again (including while the bridge is running). COM rows still require **Stop** first. Clicks use delegated handlers so row taps register reliably on phone layout.

## v1.9.76

- **Web dashboard (phone)** â€” Discovery adapter rows use a 3-line grid (name, host:port, mode tag) so preset labels no longer overlap IP text. **Expand log** pins the log panel under the Start/Stop header for most of the screen (Ctrl+F5 to pick up CSS).

## v1.9.75

- **Phone QR â€” all layouts** â€” Floating setup QR matches Field behavior everywhere (Standard, Minimal, Log-first): always visible when Web API + LAN bind are on, centered in the log area on startup, stays put across layout switches. Position is saved once in **global** prefs (normalized) so drag-to-move applies to every layout.

## v1.9.74

- **Field layout â€” phone QR** â€” Floating setup QR defaults to the **center of the live log** on startup (not the bottom-right). Stays centered when you resize until you drag it; your position is still saved per layout.

## v1.9.73

- **Web API port bind (WinError 10048)** â€” Restarts are serialized: wait for the old listener to release the port before starting again, skip duplicate overlapping restarts, and show a clear **Port N is already in use** message in Tools â†’ Phone instead of repeated uvicorn errors.

## v1.9.72

- **Tools â†’ Phone â€” Web API port** â€” Port spin arrows restart the API immediately (no need to press Enter). A live line shows **This PC dashboard: http://127.0.0.1:PORT/**; Phone dashboard URL port stays in sync. **Open dashboard** uses localhost when LAN bind is off.

## v1.9.71

- **Web dashboard rolled back to Layout 1.0** â€” Live `web/static/` restored from `web/static/layouts/1.0/` (preâ€“Layout 2.0). Offline UI no longer shows the false â€œBridge is runningâ€ banner when the API is down.

## v1.9.70

- **Web dashboard offline state** â€” When the API is unreachable, the UI no longer shows the misleading â€œBridge is runningâ€ lock on Configuration; forms stay disabled with the correct **Backend offline** message and recovery hint.

## v1.9.69

- **Web COM picker** â€” Selecting COM7 no longer snaps back to COM1: hub â€œlast known goodâ€ is applied before explicit `com_port` in `PATCH /config`, and the dashboard uses **configured** vs **runtime** COM (`configured_com_port` vs open serial while Running).

## v1.9.68

- **Tools â†’ Presets** â€” **Save asâ€¦** works while the bridge is running (writes a new named preset only). **Delete** stays blocked until Stop, with a clear message and Yes/No confirm. Preset name dialog uses a raised modal so it is not hidden behind the main window.

## v1.9.67

- **Connect status banner** â€” â€œStopped / Load a presetâ€¦â€ text bumped +3 pt (title 9 pt, detail 8.5 pt) so it stays compact but easier to read than v1.9.65â€“66.

## v1.9.66

- **Web dashboard â€” Select + layout** â€” COM & ports and Discovery **Select** / row tap use delegated clicks (fixes no-op on some browsers). Network select sends `udp_listen_host`/`port` plus `hub_device_id` so presets and NIC rows apply when stopped. **Tailscale** appears from `Unknown adapter Tailscale` in ipconfig and from `tailscale ip -4` when missing. **Panel â–²â–¼ order** follows saved DOM order on desktop grid. **layout-desktop** / **layout-mobile** body classes tighten spacing on PC vs phone.

## v1.9.65

- **Connect status banner (Standard UI)** â€” â€œStopped / Load a presetâ€¦â€ box is ~40% smaller: tighter padding, smaller type, and vertical size capped so it takes less room above the green panel headers.

## v1.9.64

- **Web dashboard Layout 2.0 Phase A (PC polish)** â€” Map in default panel order; desktop opens COM + Survey monitor + map (setup panels collapsed). Map spans two columns when open; Leaflet resizes on panel open/resize. Run-alert auto-hides and clears when status disagrees (no more â€œBridge stoppedâ€ under Running). Discovery serial list hidden on wide screens (use COM & ports).

## v1.9.63

- **Web dashboard: position map (GGA/RMC)** â€” Collapsible **Position map** panel with **Show map** toggle. Live lat/lon from `/status` (`position_lat`, `position_lon`, `position_source`, `position_stale`); vendored Leaflet + OpenStreetMap tiles when online. `bridge.navigation_position()` reserved for a future Survey HUD map (no Qt map in this release).

## v1.9.62

- **Fix: bridge thread crash after UDP/GGA** â€” Bridge thread errors now log a full traceback (not only `repr`). Stats/status Qt callbacks and the UDP datagram handler are wrapped so a bad UI callback cannot tear down the asyncio loop after NMEA is received.

## v1.9.61

- **Fix: Connect section styles (Pill / Seamless / Outline / Accent)** â€” Section style from Tools â†’ Theme now visibly updates Run and Serial & network headers. Fixed early no-op apply before the panel host existed, disabled AutoRaise on disclosure buttons (stylesheet backgrounds were ignored), repolish the full panel tree on change, and re-apply after theme swaps.

## v1.9.60

- **Fix: COM/Baud scroll wheel (complete block)** â€” Wheel input is fully disabled on COM, Baud, and TCP reconnect controls (not only when unfocused). Focus policy is ClickFocus so hover-scroll no longer changes values under Qt StrongFocus.
- **Fix: COM/Baud dropdown arrow clipping** â€” Connect serial combos get min height, drop-down subcontrol padding, and form row spacing so the arrow is not cut off by rounded styling.

## v1.9.59

- **Fix: scroll wheel on COM/Baud** â€” COM and Baud dropdowns (and TCP reconnect delay) ignore the mouse wheel unless you click into them first, so scrolling the Connect tab no longer changes values accidentally.

## v1.9.58

- **Connection hub â†’ Diagnostics** â€” Card grid moved to **Tools â†’ Diagnostics** (two visible rows + scroll). **Connect â†’ Serial & network** is COM/UDP settings only â€” no hub splitter fighting your layout.
- **Hub pick vs manual COM** â€” Editing Connect fields still overrides a hub card pick on Start (same as before, without Manual override checkbox).

## v1.9.57

- **Fix: Connect empty gap / clipped hub** â€” Stopped stretching the panel stack to fill the viewport (that left a tall dead zone above the COM cards). Connection hub keeps ~280px+ for the card grid when Manual override is off; scroll the Connect tab for more sections.

## v1.9.56

- **Fix: Connection hub narrow column** â€” Removed the extra scroll wrapper around Serial/network (one Connect tab scroll only). Hub card grid now measures the real tab width so COM cards use the full row instead of a thin strip on the left.

## v1.9.55

- **Fix: Connect layout on startup** â€” Ignores junk saved panel heights from the old splitter (e.g. 26â€“48px) that squashed **Serial & network**; multi-open sections size naturally with full-width scroll. Click **Reset sizes** once if prefs were already corrupted.

## v1.9.54

- **Fix: Connect narrow column** â€” Expanding sections (or startup with Run + Serial open) no longer leaves the scroll page stuck at a tiny fixed width from a prior **Collapse all**; viewport resize clears the width lock so Connect uses the full tab again.

## v1.9.53

- **Fix: Connect startup / Expand all** â€” Default **Run** + **Serial & network** layout no longer caps section height or pins the outer scroll page; the connection hub sizes from content so cards are not trapped in a tiny inner scrollbar. One deferred relayout pass after first paint.

## v1.9.52

- **Fix: Expand all** â€” Multiple open Connect sections stack at their natural heights (no bottom stretch or vertical `Expanding` fight), so **Run** and **Serial & network** no longer overlap or clip the connection hub. Scroll area uses a fixed content height when two or more sections are open.

## v1.9.51

- **Fix: Collapse all (layout)** â€” Connect sections use a vertical stack instead of a `QSplitter` inside a resizable scroll area, so **Collapse all** keeps normal header strips without squashing into one line or leaving a tall empty gap. Scroll area turns off `widgetResizable` when every section is collapsed so height matches content.

## v1.9.50

- **Fix: Collapse all (again)** â€” Scroll-area geometry no longer clears the compact height lock, so sections stack as normal strips instead of a thin red stack with a huge empty void below.

## v1.9.49

- **Fix: Connect Collapse all** â€” Splitter height is pinned before `setSizes` so collapsed strips stack compactly (no tall dead gap). Thinner handles when all collapsed.
- **Fix: QR flicker** â€” Debounced refresh; skips redundant hide/show during layout reflow.
- **Fix: Web API restart** â€” Debounced server stop/start (port spinner no longer kills the server on every click); clearer log lines for browser URL and LAN token.

## v1.9.48

- **Fix: UI editor / restore defaults crash** â€” Rebuilding Connect panels no longer deletes `intent_hint` and other shared widgets (`libshiboken â€¦ already deleted`).

## v1.9.47

- **Fix: Connect collapse spacing** â€” Collapsed sections no longer leave a tall empty gap with a floating splitter handle; **Collapse all** stacks compact strips. Expanded sections still absorb slack; multi-open layouts keep draggable handles.

## v1.9.46

- **Fix: UI editor desync** â€” Apply no longer rebuilds Connect panels unless section order/visibility actually changed (top bar / main tab edits stay isolated). Splitter heights clamp to the visible area so green rows are not squashed flat.

## v1.9.45

- **Connect QR** â€” Floating draggable chip on the window (no right-hand column). **Right-click â†’ Hide**; toggle **Web API** off and on to show again. Position saved in prefs.
- **Fix: UI editor tab reorder** â€” After changing main/Connect layout, panel splitters and row styles resync so **Serial & network** no longer clips.
- **Connection hub** â€” Taller minimum height so hub header/cards stay below the section title.

## v1.9.44

- **Fix: UI editor** â€” Typo (`sub_l_lbl`) crashed dialog open; **UI editor** and **UI editorâ€¦** work again.
- **Fix: Connect splitters** â€” Tab focus no longer resets section heights; drag handles keep your sizes (persisted on release).

## v1.9.43

- **Connection hub resize** â€” Vertical splitter between discovery cards and **Manual override** (drag the handle); sizes saved in prefs. Taller default **Serial & network** panel. Card grid scrolls horizontally when needed.

## v1.9.42

- **UI editor** â€” Wider default window (760Ã—540) so labels are not cut off; **â†‘ â†“** buttons replace broken drag-reorder; clearer instructions per tab. Tab renamed **Toolbar** (was Connect toolbar).

## v1.9.41

- **Connect launch layout** â€” Version line and status banner stay **above** the collapsible sections (not buried inside **Serial & network**). That section is now COM/UDP + Connection hub only.

## v1.9.40

- **Fix: Connect QR crash / layout thrash** â€” Restored missing `recommended_qr_lane_width`; debounced QR splitter updates so enabling API + LAN no longer hides the code or bounces the Connect panels.

## v1.9.39

- **Connect QR default width** â€” Lane opens wide enough to show the full code (saved width bumped if too narrow).
- **Connect section styles** â€” **Tools â†’ Theme â†’ Connect sections**: Pill, Seamless, Outline, Accent bar (persisted).
- **New color themes** â€” **Midnight Teal** and **Arctic Day** in the theme picker.

## v1.9.38

- **Connect seamless layout** â€” Flat disclosure rows (no pill cards); QR sidebar uses a **horizontal splitter** (drag to resize, width saved). QR matches app background with white quiet zone only on the code; scales with lane width.

## v1.9.37

- **Connect tab QR layout** â€” QR uses a dedicated right column so green disclosure rows end cleanly (no overlap under the code). Subtle lane divider when API + LAN are on.

## v1.9.36

- **Connect tab QR (Standard)** â€” When **Enable Web API** and **Allow LAN / Tailscale** are both on, a compact setup QR floats top-right on **Connect** (over Run / Serial & network panels). Stays visible while sections expand/collapse; **Tools â†’ Phone** unchanged.

## v1.9.35

- **Phone tab** â€” Web API, Tailscale/LAN URL, token, QR, and setup-link actions moved from Guide to **Tools â†’ Phone** (2nd after Presets) in Standard, Field, and drawer layouts. Guide keeps connection workflows only. **Show QR** on by default on the Phone page; **Open dashboard in browser** button added.

## v1.9.34

- **Field layout** â€” Preset/intent hint wraps (no single-line elision); taller default control strip; wider UDP host/port fields; status bar stats use remaining width with shorter stopped text; top bar **Shortcuts** tile reads **Keys** when narrow.

## v1.9.33

- **Bridge thread** â€” Suppress benign `ConnectionResetError` (WinError 10054) asyncio callback spam on Windows/Python 3.14 when UDP/TCP peers drop.
- **Diagnostics** â€” Catch spawn-setup errors in the panel instead of only printing a traceback to the terminal.

## v1.9.32

- **Diagnostics** â€” Automated checks work on PySide6 builds without `setCreateProcessArgumentsModifier` (Python 3.14 / current wheels); no-console spawn falls back to `pythonw.exe`.
- **Connect** â€” Fix `QBoxLayout::insert: index 2 out of range` when embedding Connection Hub on an empty connect body layout.

## v1.9.31

- **Docs** â€” NORBIT DCT wording neutralized (no personal names in preset notes or operator doc).

## v1.9.30

- **NORBIT DCT** â€” [docs/NORBIT_DCT.md](docs/NORBIT_DCT.md) and preset notes: DCT target **depends where DCT runs** â€” **127.0.0.1:40810** on boat PC; **192.168.1.8:40810** from operator laptop (MikroTik PTP boat IP); **Tailscale/ZeroTier StaticIp:40810** over VPN. Bridge still listens **40810** on the boat PC.

## v1.9.29

- **NORBIT DCT** â€” Preset and [docs/NORBIT_DCT.md](docs/NORBIT_DCT.md): boat PC **UDP port 40810**; DCT and Applanix use the PCâ€™s **local IPv4** (e.g. 192.168.1.4) or **Tailscale IP** on that port (not 10110 for this stack).

## v1.9.28

- **Documentation** â€” New [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) (install + 15-minute walkthrough), [docs/README.md](docs/README.md) index; [OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) and [README.md](README.md) updated for Standard `Connect | Log | Tools`, UI editor, web dashboard, Diagnostics cards, and NORBIT/NTRIP notes.
- **Guide tab** â€” Buttons open Getting started / Operator guide / NORBIT DCT; in-app UDP/TCP steps match current Presets UI.
- **Diagnostics** â€” Default card order puts **Automated checks** first; traffic legend card uses a compact width; **Reorder cardsâ€¦** dialog enlarged with reliable drag flags.

## v1.9.27

- **UI editor** â€” Connect and Connect toolbar lists use drag-and-drop reorder (`InternalMove`); dialog opens larger and stays resizable. **Serial & network** defaults directly under **Run bridge** (legacy factory order migrates on load). Use **Restore defaults** in the Connect tab to reset section order and splitter sizes.

## v1.9.26

- **NTRIP hidden** â€” Connect tab NTRIP panel removed from Standard layout and UI editor; saved `enabled` is forced off (Applanix/iWBMSe workflows use internal RTK). `ntrip_client` remains in tree for possible future use.

## v1.9.25

- **NORBIT DCT preset** â€” Defaults for Applanix+iWBMSe stack: survey PC **192.168.1.4**, Applanix **192.168.1.150**, UDP **10110**; docs clarify Trimble **192.168.142.1** â†’ Applanix, Bluetooth **$SDDBT** â†’ separate DCT COM (not the bridge).

## v1.9.24

- **NORBIT DCT** â€” Built-in preset **NORBIT DCT** (boat-style LAN notes) and operator doc `docs/NORBIT_DCT.md` for INS UDP â†’ COM â†’ DCT positioning workflow.

## v1.9.23

- **Web dashboard header** â€” Removed empty Control panel; Start/Stop alerts show in a strip under the top bar. Live **status chip** (`COM Â· UDP port Â· Running/Stopped Â· Hz`) between the run buttons and connection indicator.

## v1.9.22

- **Web dashboard** â€” **Start/Stop** moved to the top bar beside the version tag; Control panel keeps status messages.
- **Web live log NMEA filter** â€” Dropdown replaced with picker + **Customâ€¦** dialog (checkbox grid like desktop). Click one type; **Shift+click** in the list to combine (e.g. GGA+RMC). Presets: All types, Survey (GGA+RMC), Clear.

## v1.9.21

- **Web dashboard reorder (localhost + phone)** â€” Same **â–²â–¼** controls on every screen size; removed unreliable drag handles. Wide layouts no longer pin sections to fixed grid cells, so saved order applies on desktop too.

## v1.9.20

- **Fix â€” web dashboard â–²â–¼ reorder on portrait phone** â€” Removed fixed CSS `order` on sections (it ignored DOM moves in vertical layout); order now follows saved layout on all orientations. Larger â–²â–¼ touch targets on narrow screens.

## v1.9.19

- **Web live log â€” expand** â€” **Expand log** checkbox fills the dashboard (hides Control/COM/Config/etc.) for a near full-screen terminal; uncheck or tap the Live Log header to minimize and configure again. Preference saved in the browser.

## v1.9.18

- **Web discovery â€” host NICs** â€” Network adapters list now includes this PCâ€™s Ethernet/Wiâ€‘Fi/Tailscale IPv4 addresses (from `ipconfig`), not only UDP listen/presets/LAN scan.
- **Web live log** â€” Filter by NMEA sentence (GGA, RMC, â€¦) or custom substring; kind filter unchanged; filters are view-only in the browser.
- **Web COM Select** â€” Tap/Select applies COM with visible confirmation, updates Active COM immediately; works without desktop Connection Hub; network select requires bridge stopped.
- **Unlock ports copy** â€” COM & ports hint explains unlock probes/releases stuck COM and checks UDP listen port busy state.

## v1.9.17

- **COM port scan (web)** â€” Discovery lists **all** PC COM ports (pyserial), not only GNSS-keyword matches; **Refresh ports** calls fast `/ports/refresh` (no separate scanner app).
- **Dashboard reorder** â€” Drag **â‹®â‹®** handles (desktop) or **â–²â–¼** (phone) to reorder sections; order saved in the browser.

## v1.9.16

- **Web discovery fix (Field UI)** â€” COM/LAN discovery now runs without the desktop Connection Hub widget; phone Refresh ports / Discovery scan populate serial + network lists (fixes stuck 15 s timeout and empty COM dropdown).
- **Web GNSS colors** â€” Survey monitor GNSS tile uses RTK/GPS/no-fix badge colors; card header strip reflects fix quality while running.

## v1.9.15

- **Fix** â€” Baud `QComboBox` startup crash (`AttributeError: text`) â€” all desktop paths use `read_baud_widget()` / `currentText()`.

## v1.9.14

- **Standard baud dropdown** â€” Desktop Connect and web Configuration use a fixed list (4800â€“460800 survey/GNSS rates); legacy custom baud values snap to the nearest preset on load.

## v1.9.13

- **Phone COM workflow** â€” New collapsible **COM & ports** section under Control (tap-to-select, Apply COM, Refresh/Unlock); all dashboard cards collapse like Survey monitor (state saved); phone order Control â†’ COM â†’ monitor; Live Log/Discovery collapsed by default on mobile.

## v1.9.12

- **GNSS status badges** â€” Status bar and Survey HUD GNSS fix tile use color-coded badges (green RTK 4/5, blue GPS/DGPS 1/2, red no-fix/idle) with padding and rounded corners; idle stream shows soft red with â€œNo Data Streamâ€.

## v1.9.11

- **GNSS stale reset** â€” When NMEA traffic hits 0 Hz or no GGA/NMEA is parsed for 2 s, HUD/status/web GNSS fields clear (0 sats, fix quality 0, â€œNo Data Streamâ€) instead of holding the last simulator values.

## v1.9.10

- **Web Survey monitor UX** â€” 2-column stat grid (larger type, like v1.8); collapsible HUD sections (Connection, Sentence rates, Session, Backpressure) with one-line summaries when collapsed; mobile defaults hide Session/Backpressure until expanded.

## v1.9.9

- **Web Survey monitor** â€” `/status` exposes HUD metrics (inject Hz, session line totals, per-direction drops/rejects/queues, GNSS, transport OK). Dashboard uses a full-width monitor strip and denser layout (less empty space in status/control/discovery cards).

## v1.9.8

- **Web Live Log** â€” removed **Cards** layout trial; **Terminal** and **Table** only.

## v1.9.7

- **Phone setup link / QR use Tailscale IP, not 127.0.0.1** â€” LAN mode blocks localhost in QR and Copy phone setup link; **Detect Tailscale IP** button; Phone dashboard URL field strips pasted `#bridge-token` fragments. Renamed visible **Remote control token** label.

## v1.9.6

- **iPhone web UX** â€” clearer token onboarding copy; Copy failures on HTTP show a helpful message; Share link fallback when copy is blocked.

## v1.9.5

- **Fix: phone web UI token handoff** â€” setup links (`#bridge-token=â€¦`) apply again (JavaScript `split` limit bug broke hash parsing). Token Tools panel shows whenever LAN bind is enabled, not only after a token exists in prefs.
- **Fix: PC Guide Web controls** â€” **Web & phone** is the first Guide tab with API token, setup links, and QR (no longer buried above long workflow docs).

## v1.9.4

- **Web dashboard â€” Live Log** â€” `GET /logs` mirrors the desktop live log; new **Live Log** card with three trial layouts (**Terminal**, **Cards**, **Table**), filter, auto-scroll, pause view, and clear. Layout choice persists in browser localStorage.
- **Release gate** â€” `verify_all` / `run_unittests` treat Windows Qt `0xC0000409` shutdown and uvicorn bind noise correctly after tests pass.

## v1.9.3

- **Symmetric token handoff (all devices)** â€” **Paste setup link** on web dashboard and PC Tools â†’ Guide imports a link/token from clipboard (phone â†’ PC without typing). **Share link** on phones (system share sheet). Bidirectional hints on dashboard and Guide.

## v1.9.2

- **Phone token onboarding (no self-scan QR)** â€” Setup links use `#bridge-token=â€¦` so opening the link on the phone saves the token automatically. Mobile dashboard hides the QR block, adds **Copy token** / **Copy setup link** / **Show** token, and shows PC-first instructions. Desktop Guide: **Phone dashboard URL** (Tailscale/LAN), **Copy phone setup link**, QR encodes the setup URL (scan from PC screen with phone camera).
- **`GET /token-qr?setup=1&base_url=â€¦`** â€” QR payload is a one-tap dashboard URL, not raw token text.

## v1.9.1

- **Guide tab â€” desktop QR for API token** â€” **Show QR** checkbox beside Generate token; scannable QR appears on the right side of Web control (uses `qrcode` package). Fixes gap where QR existed only on the browser dashboard, not on Tools â†’ Guide.

## v1.9.0

- **Web dashboard â€” editable configuration** â€” COM, baud, network mode (UDP listen/remote, TCP client/server), listen/remote host/port; Save via `PATCH /config`; locked while bridge is running.
- **API token QR** â€” `GET /token-qr` (SVG); dashboard checkbox **Show QR for API token** for phone scan from PC screen (`qrcode` in `requirements-web.txt`).
- **FaÃ§ade** â€” `network_mode`, `remote_host`, `remote_port` applied on main thread; config readback includes remote fields.
- **Field layout** â€” Guide tab in scroll area; Web control group minimum height; drawer min height 320px (fixes clipped token/port rows).
- **Standard Connect** â€” COM `refresh_ports` preserves selection + empty-state placeholder; Connect splitter handle 10px + minimum height.

## v1.8.4

- **Guide â†’ Web control: API token field** â€” LAN checkbox no longer says "token in ui_prefs" with no UI. Added **API token** line edit, **Generate token**, and **Copy** on Tools â†’ Guide. Token is saved to `ui_prefs.json` and used for `X-Bridge-Token`. Enabling LAN auto-generates a token if missing. Phone dashboard: paste the same token in Tools â†’ API token field.

## v1.8.3

- **Fix: commands still fail with "Application window not available"** â€” `_window()` only consulted a weakref set by `attach_window()`, which never ran on Standard/Field/Minimal layouts. The faÃ§ade is always constructed as `BridgeAppFacade(main_window)`, so `_window()` now falls back to `self.parent()`. `publish_from_window()` also re-attaches if the ref was missing. `GET /meta` adds `commands_ready` for dashboard diagnostics.
- **Dashboard (LAN / phone)** â€” clear message when `token_required` but no token in `localStorage` (POST needs `X-Bridge-Token` over Tailscale/cellular).

## v1.8.2

- **Fix: Start/Stop/Unlock/Discovery commands never worked** â€” `BridgeAppFacade.attach_window()` was placed in `mixin._on_ui_ready()`, but every UI subclass (`standard.py`, `field.py`, `minimal.py`) overrides `_on_ui_ready` without calling `super()`, so that method never ran. `_window_ref` stayed `None` and every command returned "Application window not available". Also: `_maybe_start_web_server` suffered the same bypass, meaning the web server only started if the user manually toggled the web settings after launch. Fix: extracted both into a new `_init_web_and_facade()` method called unconditionally from `_finalize_ui()` after `_on_ui_ready()`, bypassing the override gap entirely.

## v1.8.1

- **Dashboard CSS `[hidden]` fix** â€” CSS `display: flex/inline-block/grid` rules were overriding the HTML `hidden` attribute. Added `[hidden] { display: none !important; }` reset at top of `dashboard.css`. Fixes: offline banner always showing alongside live data; "âŸ³ Scanningâ€¦" spinner always animating; token field always visible even when not required; status grid not hiding on backend-offline.
- **Clear stale window-error alerts on reconnect** â€” "Application window not available" alerts left over from early startup clicks are automatically dismissed the first time the status poll comes back online.
- **`extractApiError()` helper** â€” API error detail can be a plain string (401) or an object with `.message` (our command results). Centralised parsing replaces all inline patterns so error messages display cleanly in all cases.

## v1.8.0

- **Phase B Operator Dashboard** â€” static HTML/CSS/JS dashboard served at `GET /` by the FastAPI web server (no CDN, fully offline-capable).
  - **US1 Telemetry**: live Hz, drops/rejects, bridge state refreshed every second; offline banner on backend loss.
  - **US2 Start/Stop**: large tap-friendly buttons map to `POST /bridge/start` and `POST /bridge/stop` with in-flight disable and inline error messages.
  - **US3 Unlock Ports**: Unlock button â†’ `POST /ports/unlock`; `smart_release_com` result shown inline (no QMessageBox on API path).
  - **US4 Discovery + COM picker**: Refresh Scan â†’ `POST /discovery/refresh`; polls `GET /discovery` every 500 ms (â‰¤ 15 s); click any serial/network row â†’ `PATCH /config` with 409 running-guard message.
- **New API routes**: `GET /meta` (version, lan_bind, token_required), `GET /discovery`, `POST /discovery/refresh`, `POST /ports/unlock`, `GET /api` (JSON index, old `GET /`).
- **`BridgeAppFacade` extensions**: `SerialDeviceDto`, `NetworkCardDto`, `WebDiscoveryPayload`, `WebMeta` dataclasses; thread-safe discovery cache; `request_refresh_discovery()` and `request_unlock_ports()` via Qt signal dispatch.
- **`ui/mixin.py`**: wires `facade.update_discovery_snapshot(snap)` after hub `set_snapshot()` (both worker and fallback paths).
- **Token support**: token field appears only when `meta.token_required`; persisted in `localStorage` (`nmea-bridge-web-token`).
- **PyInstaller**: `web/static` folder added to `datas` in `nmea_serial_bridge.spec`.
- **Tests**: expanded `test_web_api.py` (10+ new cases) and `test_app_facade.py` (discovery cache, unlock, refresh with Qt event-loop harness).

## v1.7.2

- **Web API config + OpenAPI** â€” `GET /config` reads Qt fields on the main thread (fixes empty/wrong `com_port` vs `/status`); Swagger shows real response schemas (`StatusResponse`, `ConfigResponse`, `CommandResponse`) instead of generic placeholders.

## v1.7.1

- **Web API start/stop** â€” Commands from the HTTP thread now queue to the Qt main thread via a signal; `QTimer.singleShot` from uvicorn never ran, so Swagger/curl start/stop could time out or appear dead.

## v1.7.0

- **Hybrid UI Layer 1** â€” Standard Connect and Field control strip load from Qt Designer `.ui` files at runtime (`ui/ui_loader.py`, `ui/resources/`); programmatic fallback if assets are missing.
- **Hybrid UI Layer 2** â€” Optional **Web control plane** on `127.0.0.1:8765` (FastAPI): `GET /status`, `GET/PATCH /config`, `POST /bridge/start`, `POST /bridge/stop`; background uvicorn thread; `BridgeAppFacade` delegates to the same mixin as the desktop UI.
- **Tools â†’ Guide** â€” Enable Web API, port, and LAN bind checkbox; prefs in `ui_prefs.json`.
- **Tests** â€” `test_ui_loader.py`, `test_app_facade.py`, `test_web_api.py`; optional `requirements-web.txt` and `bench_web_api.py`.

## v1.6.0

- **Connection Hub Phase 2** â€” responsive card grid (1â€“3 columns, card-only scroll), **Refresh discovery** (ARP + bounded UDP probes on survey ports), **Unlock ports** (Smart Release COM without restart), traffic **QoS** chips on the active card from bridge stats.
- **`network_scanner.py`** â€” LAN host list from `arp -a`, `scan_network()` with host/port budget; **`port_release.py`** â€” COM lock probe and smart release; **`ui/discovery_worker.py`**, **`ui/hub_quality.py`**, **`ui/connection_fields.py`**.
- **Field layout** â€” **Refresh** / **Unlock** on the bottom strip wired to the same handlers as Standard.
- **Tests** â€” `test_network_scanner.py`, `test_port_release.py`, `test_hub_quality.py`, `test_connection_fields.py`; extended discovery/hub/connect-panel tests.

## v1.5.1

- **verify_all / Qt teardown** â€” `ui/qt_test_harness.py`, `tools/run_unittests.py`, and `verify_all.py` treat Windows `0xC0000409` fast-fail as pass when unittest/GUI smoke output already shows OK. `bench_gui_smoke.py` closes windows and exits cleanly.

## v1.5.0

- **Connection Hub (Connect tab)** â€” card grid for detected GNSS serial ports and UDP listen context; selection drives COM/UDP for Start with per-device **last-known-good** in `ui_prefs.json`. Legacy serial/network fields live under collapsible **Manual override**.
- **`discovery_service.py`** â€” Qt-free discovery snapshots (serial stability, UDP port probe, live peer counts); `auto_discovery.py` delegates serial scan to the service.
- **TCP sink mirror** â€” optional `TcpSinkConfig` on `SerialNetBridge` mirrors serialâ†’net bytes to a parallel TCP server (independent of UDP fan-out).
- **Field layout** â€” compact connection summary line under COM/UDP strip.
- **Tests** â€” `test_discovery_service.py`, `test_connection_hub.py`, `test_tcp_sink.py`.

## v1.4.10

- **Spec Kit baseline delivery** â€” `specs/001-baseline-spec/`: as-built spec (FR-001â€“FR-020), plan, tasks, traceability matrix, contracts, quickstart. No bridge logic changes.
- **Operator docs aligned with fan-out** â€” `README.md` and `docs/OPERATOR_GUIDE.md` document default-on fan-out vs single-link; new Â§5.5 two-client bench procedure (one bridge, not two apps).
- **`bench_fanout_probe.py`** â€” registers a UDP peer and listens for serialâ†’net replies during fan-out bench tests.
- **`test_baseline_docs.py`** â€” guards README/operator-guide/traceability keywords.
- **Baseline cleanup** â€” `version_info.txt` synced to `version.py` (1.4.10) via `tools/sync_version_info.py`; **FR-021** auto-discovery formalized in baseline spec; **SC-003** HUD stress validation doc (`sc003-hud-stress-validation.md`); traceability waivers for OpenCPN UDP port conflict and `bench_gui_smoke` environment failures; `test_version_sync.py` added.

## v1.4.9

### Auto-Discovery â€” headless GNSS device watcher

- **`auto_discovery.py`** (new) â€” `AutoDiscoveryThread(QThread)` polls USB-serial ports every 2 s. Emits `device_detected(port_name: str)` once a matching device has been seen for 2 consecutive polls (stability guard prevents false fires during Windows USB enumeration churn). Resets after absence so reconnecting the same cable triggers again. Default keyword list covers Trimble, U-blox, NovAtel, Septentrio, Leica, Topcon, Hemisphere, SiRF, Garmin â€” intentionally excludes generic "FTDI" / "Serial" to avoid matching printers and Arduinos.
- **"Auto-connect on GNSS device detected" checkbox** â€” added to the serial connection section (below Auto-reconnect). Off by default; state is persisted to `ui_prefs.json`. When checked: COM port is updated automatically on device appearance; bridge auto-starts if the bridge is stopped and configuration passes `_validate_start()`.
- **Thread lifecycle** â€” started at `_finalize_ui()` close, stopped cleanly in `closeEvent()` (waits up to 2.5 s). Safe to run alongside all layouts (Standard / Field / Minimal / Log-first).
- **Tests** â€” `test_auto_discovery.py`: 13 new cases covering default keywords, `_scan()` matching (description / manufacturer / case-insensitive / custom keywords), stable-poll guard, no-re-emit guard, device-absence reset, `stop()` flag, and a live `run()` smoke test.

## v1.4.8

- **Diagnostic scripts work in the portable `.exe` build** â€” three-part fix:
  1. `nmea_serial_bridge.spec`: added `HELPER_MODULES` list (`bench_config.py`, `bench_udp_test.py`, `nmea_codec.py`, `bridge_core.py`, `py_interpreter.py`) to `datas` alongside the existing helper scripts so a fresh Python subprocess can import project modules from `_MEIPASS`.
  2. `ui/mixin.py` `_diag_start_script`: now injects `PYTHONPATH=_REPO_ROOT` into the `QProcess` environment, guaranteeing imports resolve even if the working-directory rule doesn't fire.
  3. `_diag_run_verify_all`: in a frozen build, checks for `test_bridge_core.py` and shows a clear "not available in portable build / clone and run from source" message instead of silently failing.
- Scripts that work in the portable build after this fix: `com_free`, `check_setup`, `nmea_static_sample`, `bench_tcp_stress`, `bench_capacity_probe`. `verify_all` requires the source tree.

## v1.4.7

- **Diagnostics scripts found in frozen `.exe` build** â€” `_REPO_ROOT` in `ui/mixin.py` was resolved using `Path(__file__).parent.parent` which points inside PyInstaller's bootstrap tree, not the exe directory. Replaced with `_resolve_repo_root()`: when `sys.frozen` is set, uses `sys._MEIPASS` (the one-folder dist directory where the spec bundles `verify_all.py`, `com_free.py`, etc. via `helper_datas`). Source runs unchanged. Added top-level `import sys` to `mixin.py`.

## v1.4.6

- **Guide tab rewritten** â€” replaced the old three-line disclaimer with a full structured workflow guide. Four tabs: UDP Flow, TCP Client, TCP Server, and Checklist. Each method has numbered setup steps with inline code spans for IPs/ports. Rendered via `QTextBrowser` with per-theme QSS (dark and light). The old static `QLabel` body is gone.

## v1.4.5

### Part A â€” "Run bridge" panel cleanup
- **Ghost text removed** â€” `CONNECT_PANEL_COLLAPSED_HINTS["run"]` trimmed to `"Start/Stop"` (dropped stale "bench setup" copy). Same fix in `CONNECT_PANEL_HINTS` in `ui_editor.py`.
- **Button row breathing room** â€” `al.setContentsMargins` changed from `(0,4,0,4)` to `(5,5,5,5)` and spacing from `6` to `10` px, eliminating the Start/Stop button overhang.

### Part B â€” HUD `KeyError` killed permanently
- **`default_layout()` fixed** (`ui/survey_hud_layout.py`) â€” `gnss_hdop` is now included in the metrics dict with value `False` (off by default) instead of absent. Old configs that exclude it are no longer broken at the source.
- **`_migrate_hud_metrics()` added** (`ui/stats_popout.py`) â€” migration helper called at the top of `_HudLayoutDialog.__init__` before `deepcopy`. Any metric ID missing from the saved config is back-filled with `True` before checkboxes are built, making future metric additions safe without a version bump.

## v1.4.4

- **Splitter state save/restore fixed** â€” reverted the 1.3.8 over-fix that always wiped panel sizes on every rebuild. `_rebuild_connect_panels` now passes the normalized `saved_sizes` dict back to `save_connect_panel_prefs` (corruption guard already cleaned it to `{}` when needed) and uses the `use_default_sizes` flag from `_normalize_connect_launch_prefs`. Result: drag-to-resize heights are restored on every normal relaunch; corrupted states still boot from defaults.
- **"Run bridge" panel cap raised** â€” `_PANEL_EXPANDED_CAP["run"]` raised from 72 â†’ 120 px so the Start/Stop buttons + Fan-out checkbox aren't cramped on first-launch defaults.
- **Status bar anchored** â€” `self.statusBar` now has `Expanding Ã— Fixed` size policy and explicit `stretch=0` in the outer VBox, ensuring it is always pinned to the bottom of the window regardless of splitter sizing.

## v1.4.3

- **UDP Mode toggle UI** â€” "Fan-out â€” send serial data to all UDP peers" checkbox added to the Network (UDP listen) section of the Connect tab. Checked = fan-out to all registered peers (new default); unchecked = single-link, replies only to the most recent sender (legacy behaviour). Setting is saved per-preset and restored when a preset is loaded.
- **`bridge_core.SerialNetBridge`** â€” new `udp_fanout: bool = True` constructor parameter; `_send_net` branches on `self._udp_fanout` to select fan-out vs single-link path.
- **Tests** â€” 3 new cases in `test_udp_fanout.py`: single-link sends only to `last_udp_addr`, single-link with no addr sends nothing, default constructor has fan-out enabled.

## v1.4.2

- **UDP fan-out (one COM â†’ many network clients)** â€” in `UDP_LISTEN` mode the bridge now tracks every UDP sender that contacts it during a session (`_udp_peers: set`) and forwards the serialâ†’net stream to all of them simultaneously. Previously only the most-recent sender received serial data. Key behaviour:
  - First new peer shows `peer <addr>` in the network status label; additional peers show `N peers`.
  - If `sendto` fails for a peer (e.g. ICMP unreachable), that peer is silently pruned from the fan-out set; remaining peers continue receiving.
  - `abort_now` / Stop clears the peer set so the next session starts fresh.
  - `UDP_REMOTE` and TCP modes are unchanged (single-endpoint, no fan-out).
  - New `udp_peer_count` property; `udp_peers` key added to stats dict.
- **Tests** â€” `test_udp_fanout.py`: 12 new tests covering peer registration, multi-peer send, dead-peer pruning, remote-mode isolation, abort cleanup, and stats emission.

## v1.4.1

- **Native scrolling restored** â€” nuked the entire manual geometry-toggle system in `connect_panels.py` that was the root cause of clipping and scrollbar breakage:
  - `_sync_connect_panel_scroll_geometry` now only **releases** previously-applied Fixed height locks (scroll, page, tab) and re-applies `Expanding Ã— Expanding` on the scroll area â€” it never pins anything to a content height.
  - `_reflow_connect_panel_host` replaced: all `sole_expanded` / `in_scroll` / `setFixedHeight` branching removed; host and splitter are always set to `Preferred Ã— Minimum` and released from any prior lock.
  - `_set_connect_tab_stretch` always uses stretch=1 â€” the old `compactâ†’0` path was zeroing the scroll area out of the layout entirely.
  - `panel_scroll` construction now explicitly sets `Expanding Ã— Expanding` policy so no subsequent call can accidentally override it.
- **Top-alignment preserved** â€” `page_lay.setAlignment(AlignTop)` and `addStretch(1)` already ensured panels stack from the top; the cleanup ensures this is always restored after any geometry flush.
- **Test updated** â€” `test_sync_scroll_compact_height` and `test_sync_scroll_geometry_reapplies_when_signature_same` reflect the new lock-release contract.

## v1.4.0

- **Panel expand clipping fix** â€” `DisclosureRow._set_expanded(True)` now releases the row's own `maximumHeight` cap (`setMaximumHeight(WIDGET_SIZE_MAX)`) before making the body visible. Previously the row stayed clamped at 44 px while the body tried to render, causing content to paint underneath the splitter handle until the deferred reflow timer fired.
- **"Tools" chip removed from ribbon** â€” the top utility ribbon no longer creates or registers a "Tools" chip for Standard layout (it has a dedicated Tools tab instead). Field layout is unaffected â€” the chip is still created and wired to `_drawer_btn` there. Drawer-sync code now uses `getattr(self, "_survey_btn_tools", None)` so it is safe on any layout.
- **Reverted `load_top_bar_prefs` default-hidden approach** â€” prefs loading is back to the original clean implementation; ribbon visibility is now controlled structurally (chip not created) rather than via a hidden pref.

## v1.3.9

- **Collapse-all 0 px fix** â€” `_apply_connect_splitter_sizes` now clamps every slot to `_COLLAPSED_STRIP_HEIGHT` before calling `splitter.setSizes()`, preventing Qt from distributing below widget minimums when available height is tight. "Collapse all" also flushes the QScrollArea geometry via timer so the area compacts immediately.
- **Full header bubble clickable** â€” `DisclosureRow` button now uses `Expanding Ã— Fixed` size policy so it fills the entire header strip width; `PointingHandCursor` is set on hover. Clicking anywhere on the panel header title bar now toggles it.
- **Toolbar buttons right-aligned** â€” Connect toolbar `addStretch(1)` moved to the front of the layout, pushing UI editor / Expand all / Collapse all / Reset sizes flush against the right edge.
- **Run bridge panel cleanup** â€” removed the "Bench pair setupâ€¦" button; Start bridge and Stop bridge are now capped to 200 px wide with a trailing stretch so they stay left-aligned and compact at any window width.
- **Standard layout chip bar defaults** â€” "Tools" and "UI editor" chips are hidden by default on first launch (Standard mode) since the Tools tab and Connect toolbar already cover both functions. Users can restore them via the UI editor.
- **Window freely resizable** â€” confirmed no `setFixedSize` anywhere on `BridgeWindowStandard`.

## v1.3.8

- **Ghost-state splitter fix** â€” Connect tab panels no longer crush to 0 px on boot from a corrupted saved layout. `_rebuild_connect_panels` now always boots with default geometry (`use_defaults=True`) and clears the prefs sizes dict on every rebuild, so stale values can never override `setMinimumHeight` constraints. Drag-to-resize still persists new sizes for "Reset sizes" baseline; they are simply not re-applied on next launch.
- **`_normalize_connect_launch_prefs` hardened** â€” added an explicit any-zero/any-negative guard in addition to the existing all-at-strip-height check; either condition now wipes the saved sizes dict before it can reach `splitter.setSizes()`.

## v1.3.7

- **3-tab Standard layout** â€” reduced top-level tabs from 8 down to 3 (Connect, Log, Tools); Presets, NMEA, Terminal, Diagnostics, Theme, and Guide now live inside a clean sidebar-nav + stacked-page Tools drawer, eliminating tab overload.
- **Greedy button fix** â€” Start bridge / Stop bridge / Bench pair setup buttons now use `Expanding Ã— Fixed` size policy with enforced minimum heights so they resize horizontally but never stretch vertically inside the Run bridge panel.
- **Connect tab scroll & anti-squish** â€” every splitter panel gets a hard minimum height floor (preventing 0-pixel collapse), and the scroll area is stretch-weighted so it grows to fill available space on large monitors.
- **DPI scaling cleanup** â€” removed conflicting `ctypes.SetProcessDpiAwareness` call; Qt6-native env vars (`QT_AUTO_SCREEN_SCALE_FACTOR`, `QT_ENABLE_HIGHDPI_SCALING`) are now set before `QApplication` construction, fixing Windows taskbar shrink on launch.
- **Top-bar box model** â€” replaced CSS `margin` on clickable buttons with `padding` (larger hitboxes); removed rigid `max-height` constraints; layout now uses `setSpacing` / `setContentsMargins` for breathing room.
- **UI editor resilience** â€” `_apply_tab_visibility` and `_apply` wrap rebuild calls in `hasattr` + `try/except`; `ordered_checked()` strict-None guards prevent crashes on dynamic drag.
- **Tools sidebar styling** â€” `QListWidget#toolsNavList` gets themed background, border-right separator, and hover/selected states in both dark and light themes.
- **Test update** â€” `test_standard_has_theme_tab` updated to assert Theme lives inside the Tools sidebar nav rather than as a top-level tab.

## v1.3.6

- **UI review polish** â€” product demo steps open the **Terminal** tab reliably (`send`/`terminal` aliases); Field **Ctrl+L** focuses the live log when the log panel is always visible; UI editor copy and tooltips are layout-aware (Standard vs Field Tools tabs).
- **Field UI editor** â€” **Tools tabs** page for hiding/reordering drawer tabs (Presets, NMEA, Terminal, â€¦); tab visibility apply uses `_drawer_tabs` for Field instead of main window tabs.
- **Top-bar migration** â€” `migrate_topbar_order()` now delegates to `normalize_topbar_order()` so legacy chip cleanup stays in one place.
- **Tests** â€” demo tab aliases, tools_tabs hidden-tab prefs roundtrip, migration parity.

## v1.3.5

- **Removed Hidden top-bar chip** â€” the dedicated **Hidden** tile is gone from the survey bar; tab hide/restore now lives on the tab strip (right-click a tab to hide, right-click empty tab-bar space to restore hidden tabs, or use **UI editor â†’ Main tabs**).
- **Top-bar migration** â€” saved layouts that still reference the old `hidden_tabs` chip are cleaned up automatically on load.

## v1.3.4

- **Connect Serial section no longer falls back to white on some PCs** â€” Standard layout Connect panels (`Serial & network`, inner Serial/Network group boxes, and scroll viewport) now force styled backgrounds on Windows so green/dark surfaces render consistently in packaged builds, not just on dev machines.

## v1.3.3

- **High-contrast dialog guardrail** â€” added an app-wide contrast stylesheet for `QMessageBox` and tooltips so startup/bridge-failure dialogs no longer show low-contrast text on light backgrounds.
- **Theme-safe application of contrast rules** â€” contrast guard is now re-applied on theme changes from shared UI logic, keeping warnings/errors readable across Standard/Field/Minimal/Log-first and random theme variants.
- **Regression coverage added** â€” new tests lock in global contrast guard injection and idempotent re-application behavior.

## v1.3.2

- **Frozen Diagnostics scripts restored** â€” PyInstaller spec now bundles Diagnostics helper scripts (`check_setup.py`, `com_free.py`, `verify_all.py`, TCP/UDP bench helpers, and related runtime tools) so Bench/Boat checklist and Automated checks run from the downloaded zip build.
- **Frozen guide availability fixed** â€” `docs/` is now included in one-folder releases so Bench setup guidance and in-app operator guide links resolve in packaged deployments.

## v1.3.1

- **UI workflow polish shipped** â€” Connect panel stability improvements and UI editor/log-view/top-bar tooling are now committed together with targeted regression tests for collapsibles, field strip sizing, top-bar chips, log filtering, and editor behavior.
- **Launcher reliability pass** â€” launcher and Windows launch scripts now run with safer cwd/interpreter handling and no-console subprocess helpers for smoother GUI startup and diagnostics scripts.
- **NTRIP mux hardening** â€” serial correction injection now uses a write lock to avoid write interleaving under concurrent bridge/NTRIP traffic, with benchmark helper and parser-tail test coverage.

## v1.3.0

- **Backend runtime invariants hardened** â€” UI timer/chip code now uses object-safe bridge-running checks, eliminating `bridge.running` attribute tracebacks during mixed test/mocked UI states.
- **Startup self-check line added** â€” app logs a single startup line with version, active UI mode, and effective prefs/config paths for faster field diagnostics.
- **Prefs schema/versioning introduced** â€” `ui_prefs.json` now tracks `schema_version` with migration hooks (including Connect toolbar order backfill) and recovers cleanly from malformed JSON.
- **Release gates tightened** â€” `verify_all.py` now fails the run when traceback markers appear in subprocess output even if return codes are zero; `build.ps1` enforces `verify_all` before packaging.
- **Packaging reproducibility artifacts** â€” `release.ps1` now emits a build environment lock snapshot (`pip freeze` + tool versions), plus a release manifest with SHA-256 checksums/sizes for exe+zip and includes both files in GitHub releases.
- **New consistency tests** â€” added deterministic bridge mode start/stop cycle tests, queue-pressure counter invariants, traceback-gate tests, and prefs schema recovery migration tests.

## v1.2.50

- **Collapsed Connect labels visible again** â€” increased collapsed strip height to match rounded header padding so section text/arrows remain readable when rows are collapsed.

## v1.2.49

- **Collapsed Connect reassurance text** â€” each collapsed Connect section title now includes a short purpose hint so operators can identify sections without expanding all.
- **Bench setup hide now hides buttons** â€” checking â€œHide this setup window next timeâ€ now hides Bench pair setup buttons in Standard and Diagnostics after close/startup instead of leaving a no-op button.
- **Hidden tabs menu: Show all** â€” added a one-click â€œShow all hidden tabsâ€ action.
- **Guide tab + Demo sync** â€” added a transparent Guide tab (main tab in Standard; drawer tab in Field/log-first/minimal), shortened Traffic/quality legend toward quick health read, and updated Product Demo to point at Guide for truthful strengths/limits/current focus.
- **Connect toolbar button order** â€” `UI editorâ€¦ / Expand all / Collapse all / Reset sizes` can be reordered in `UI editor â†’ Connect toolbar` and persisted.

## v1.2.48

- **Bench setup dialog hide toggle** â€” added a bottom checkbox to hide the Bench pair setup window on future runs while still running preflight scripts.
- **Reorder Connect toolbar buttons** â€” `UI editorâ€¦ / Expand all / Collapse all / Reset sizes` order is now configurable via **UI editor â†’ Connect toolbar** and persisted per workspace.

## v1.2.47

- **Connect iOS-card polish** â€” increased per-row card separation, rounded corners, and soft gradient fills for Connect disclosure headers so each section reads as a distinct card block without visual merging.

## v1.2.46

- **Connect section cards + rounded UI pass** â€” collapsed Connect rows now render as individual bordered cards (not a continuous strip), and core controls/chips/tabs use stronger rounded corners for a cleaner Apple-style look.

## v1.2.45

- **Top-bar chip readability** â€” compact chips now try readable words with smaller font before abbreviations (e.g. `Random` / `Standard` before `Rand` / `Strd`), reducing unnecessary shorthand while still preventing clipping.

## v1.2.44

- **Standard first-paint Connect fix** â€” added activation/show/resize/layout-request reflow hooks for the Connect tab so launch-time geometry settles automatically without requiring a manual click.

## v1.2.43

- **Connect tab auto-reflow on activation** â€” Standard now forces a Connect splitter/scroll geometry sync when Connect becomes active (plus startup deferred passes), removing the â€œclips until I clickâ€ behavior after tab navigation.

## v1.2.42

- **Standard Connect stability after tab navigation** â€” hardened Connect scroll/page reflow to always re-apply geometry locks and keep panel content top-aligned, preventing intermittent â€œfloatingâ€/clipped Connect blocks after moving around tabs.

## v1.2.41

- **Connect expand/collapse no-clip pass** â€” expanded rows now always honor their natural content height (saved size caps no longer force clipping), and Run/Status defaults are taller so first-open state stays readable.

## v1.2.40

- **Layout chip** â€” survey bar shows one **Layout** tile (not separate Standard / Field buttons). **Double-click** toggles to the other workspace; label stays Â«LayoutÂ» on both layouts. Stop the bridge before switching.

## v1.2.39

- **Removed inline Edit layout** â€” dropped the buggy live Connect canvas editor. Connect sections are back in the **UI editorâ€¦** checkbox dialog (with Top bar and Main tabs). Use **Expand all / Collapse all** and drag splitter handles on Connect for sizes.

## v1.2.38

- **Field control strip** â€” COM / Stopped / preset banner sit tight on launch (layout stretch at bottom, smaller default splitter pane, strip min 92px when Tools closed). Drag the bar between the log and the strip to resize; saved layouts that gave the strip >34% height reset once to the compact default.

## v1.2.37

- **Diagnostics cards** â€” vertical splitter between cards (drag handles like Connect): expanded sections size to content (On-screen log no longer fills the drawer), heights persist per layout, sole-open card does not absorb all slack.

## v1.2.36

- **Field layout launch fix** â€” restored missing `load_field_prefs` / `save_field_prefs` imports in `ui/mixin.py` so **Field** (and saved layout via `launch_bridge_gui.bat`) opens instead of exiting silently under `pythonw`.

## v1.2.35

- **Connect Edit layout** â€” iOS-style inline editor on the live Connect tab: per-tile Up/Down/Hide, green edit bar with Done/Cancel/Restore defaults, highlighted splitter handles. **Workspaceâ€¦** opens top bar + main tabs dialog (Connect checklist tab removed). Cursor rule `100-layout-canvas-editor` tracks phased layout work; NTRIP stays on backburner.

## v1.2.34

- **UI editor Restore defaults** â€” no longer hides **Serial & network** and other required Connect sections (non-checkable rows were saved as hidden). Restore resets collapse/sizes and shows all sections except NTRIP by default.

## v1.2.33

- **UI editor polish** â€” **Main tabs** list shows tab names and short descriptions (fixed blank checkbox rows caused by empty tooltips at catalog build). All three tabs have clearer legends, styled lists, and main-tab reorder persists on OK.

## v1.2.32

- **Top bar Presets** â€” choosing a preset loads COM/UDP/survey fields and **starts** (or restarts) the bridge only â€” no automatic bench checklist. Checklists remain on **Diagnostics** (Bench / Boat checklist buttons).

## v1.2.31

- **Diagnostics cards after Presets quick-load** â€” collapsed cards no longer render as clipped ~0px strips (minimum header height + layout refresh on tab show). **Automated checks** expands automatically when a diagnostic script starts so output is visible.

## v1.2.30

- **Connect Run bridge layout** â€” after **Collapse all**, expanding **Run bridge** (or any single section) again shows full Start/Stop/Bench controls instead of crushed 26px strips; splitter heights now follow each rowâ€™s real size hint, and sole-expanded mode no longer locks the splitter with `setFixedHeight`.

## v1.2.29

- **Connect panels after Collapse all** â€” reopening one section (e.g. Run bridge) no longer stretches it through the whole tab with a huge empty gap; extra height is only shared when two or more sections are expanded.

## v1.2.28

- **Top bar overlap fix** â€” **Std** and **Layout** no longer stack on each other: the layout chip clips to its tile and switches to the single **Layout** menu when too narrow for Standard | Field buttons.

## v1.2.27

- **UI editor** â€” removed **Demo** from the top bar; new **UI** tile and **View â†’ UI editor** open a workspace editor to show/hide and reorder top bar chips, Connect sections (hide NTRIP, Quick log, etc.), and main tabs. Connect tab **UI editorâ€¦** button opens the same dialog. **Restore defaults** applies a recommended survey layout.

## v1.2.26

- **Live log view** â€” replaced the narrow â€œSentences: all / GGA onlyâ€ dropdown with **log presets** (Ops, Survey GGA+RMC, Wire tap, Problems only, Debug) plus a **Viewâ€¦** dialog to toggle RX/TX/warnings/UI messages, every-NMEA verbosity, sentence types, and hex preview. Display-only â€” bridge NMEA mode stays on the NMEA tab.

## v1.2.25

- **Diagnostics cards** â€” expand/collapse no longer caps the whole card to a thin strip; only the body hides, with `set_expanded()` for reliable open state (same class of fix as Connect panels).

## v1.2.24

- **Send tab â†’ Terminal** â€” main and drawer tabs renamed; saved tab order migrates `Send` â†’ `Terminal`.
- **Top bar stability** â€” Layout chip uses a stacked Standard|Field vs Layout menu (never both); bar-wide compact hysteresis stops jitter; Shortcuts tile keeps full **Shortcuts** label in compact mode (not **Keys**).

## v1.2.23

- **Memory / freeze fix** â€” stopped top-bar resize layout storms and debounced Connect panel geometry updates; launch window widening runs once. Fixes runaway RAM use introduced around v1.2.17â€“1.2.22.

## v1.2.22

- **Top bar first impression** â€” on launch the window widens when needed for full tile titles; otherwise every tile uses short readable labels (**Presets**, **Hidden**, **Stats**) with no `Prâ€¦` ellipsis clipping.

## v1.2.21

- **Field layout launch** â€” wider default window, balanced log/control splitter (not a huge empty log band), readable top-bar shorts instead of `Prâ€¦` ellipses, preset hint wraps, duplicate log toolbar hidden (controls live in the bottom strip).

## v1.2.20

- **Bench pair setup** â€” opens a stay-open setup window with guide section 5 (no flash/auto-close from external viewers). Expands **Quick terminal**, runs preflight there, and suppresses console popups on Windows.

## v1.2.19

- **Expand all / Collapse all** â€” section bodies now open and close with the headers (bulk actions no longer leave panels at zero height while chevrons show expanded).

## v1.2.18

- **Connect tab dead space** â€” tool buttons stay fixed at the top; only the panel stack scrolls. When all sections are collapsed, the scroll region matches panel height (no huge empty band you cannot shrink).

## v1.2.17

- **Connect panel toggles** â€” expanding/collapsing sections no longer shrinks the main window or traps you in a short, hard-to-resize frame. Connect tab scrolls when content is taller than the viewport.
- **Window height** â€” if a prior build left the window very short, opening any Connect panel restores a comfortable default height.

## v1.2.16

- **Top bar labels** â€” no more mystery **N** / **O** tiles; narrow tiles use readable shorts (**Rand**, **Std**, **Hidden**, **Stats**, â€¦). Full titles when space allows. Bar fills edge-to-edge.
- **Connect panel drag** â€” pink splitter bars between sections are easier to grab; dragging no longer gets reset by layout. Sections keep sensible heights instead of stretching Run into a giant band.
- **Main tabs** â€” drag tabs on the tab strip to reorder (tooltip reminder); movable flag re-applied after layout rebuilds.

## v1.2.15

- **Top bar resize** â€” drag the right edge of any tile (â†” cursor) to change widths; sizes persist. â‹®â‹® grip still reorders. Letter tiles (N, O, â€¦) show full name on hover.
- **Main tabs** â€” more gap between Connect / Diagnostics / Log tabs.
- **Diagnostics tab** â€” removed bottom stretch that left a huge empty void when cards are collapsed.

## v1.2.14

- **Top bar equal-width tiles** â€” each chip gets an explicit computed width so the row always spans the full bar (fixes trailing empty gutter and uneven tile sizes). Full label only when it fits inside the tile; otherwise a single letter (no `Shoâ€¦` ellipsis).

## v1.2.13

- **Top bar spring fill (always)** â€” visible chips share the full bar width at every window size; no empty track between tiles. Full labels when each chip's share fits; centered single letter when narrow. `TOPBAR_ALWAYS_FILL_TRACK` invariant in `ui/survey_top_bar.py`.

## v1.2.12

- **Connect tab fits content** â€” collapsed panels stack at the top without a huge empty gap; window height shrinks on launch when everything is collapsed. Bottom filler no longer steals vertical space.
- **Connect splitter drag** â€” splitter grows inside the host when expanded; drag handles work (no fixed-height lock while resizing). Run/Status panels cap height so Start is not a giant band.
- **Top bar labels on wide launch** â€” letter tiles only when the window is actually too narrow; launch keeps full chip titles on a normal/wide desktop width.

## v1.2.11

- **Standard launch readability** â€” top bar no longer defaults to unreadable one-letter tiles on first paint; window opens wide enough for full labels and waits for real layout width before choosing letter mode.

## v1.2.10

- **Top bar: no clipped labels** â€” full-text tiles only when they fully fit; otherwise letter tiles (no overlapping/bunched chips). Hysteresis applies when growing out of letter mode only. Launch width includes a small margin.

## v1.2.9

- **Top bar resize hysteresis** â€” slight window shrink no longer snaps every chip to one-letter mode; full labels stay until clearly too narrow, and letter mode needs extra width before expanding back. Field/Standard open wide enough for full labels when possible (comfort width like your mid-size screenshot).

## v1.2.8

- **Fix hide top-bar chip** â€” hiding a chip (e.g. Copy stats) no longer leaves a ghost tile overlapping neighbors; hidden chips are removed from layout and not painted.

## v1.2.7

- **Top bar content-sized tiles** â€” each chip is only as wide as its label (character width + minimal border); spare space stays on the right. Fixes oversized â€œViewâ€ and truncated â€œStandardâ€ on wide windows. Layout/Field buttons size to their text.

## v1.2.6

- **Top bar spring layout** â€” chips share bar width equally (expand to the right); adding/hiding chips redistributes space. Letter tiles stay centered inside each expanded chip; full titles when wide enough.

## v1.2.5

- **Top bar letter tiles** â€” narrow window collapses chips to v1.2.3-sized boxes with a **single letter** (Viewâ†’V, Presetsâ†’P, â€¦) instead of abbreviations or forced wide window. Wide window shows full titles. Drag grip on the right with hand cursor unchanged. Layout chip compact letter **L** opens Standard/Field menu.

## v1.2.4

- **Top bar readability** â€” chip text comes first; **â‹®â‹®** drag grip on the **right** with open/closed **hand** cursor (not resize arrows). Buttons keep full titles at normal width; abbreviate only when squeezed (tooltip keeps full name). Window minimum width grows to fit all chips; Field opens at the same readable width as Standard.

## v1.2.3

- **Draggable top bar chips** â€” each survey bar action is a bordered box with consistent padding; drag the **â‹®â‹®** grip to reorder and snap on the bar (no separate rearrange dialog). Right-click a chip to hide it; **View â†’ Show all top bar chips** to restore.
- **Layout switch on top bar** â€” **Standard** / **Field** moved from Diagnostics to the far-right top bar chip (replaces Quick UI switch card).

## v1.2.2

- **Connect expand/collapse polish** â€” releasing fixed height when any panel expands; splitter target height uses the Connect tab (not a shrunken post-collapse splitter). Tab stretch keeps collapsed stacks at the top; expanding a section grows the host again. Disclosure toggles reflow the splitter immediately.
- **Diagnostics cards** â€” all sections default collapsed (including Quick UI switch and file log); closed cards use a compact strip; spare space packs below the card stack.

## v1.2.1

- **Connect tab compact collapse** â€” collapsed panels stack at the top with no dead space inside the splitter; **Collapse all** shrinks the panel host to strip height only. Stretch goes below the stack (not between headers). Default: only **Run** and **Serial & network** expanded; optional sections start collapsed. Removed launch logic that forced all panels open when prefs were collapsed.

## v1.2.0 â€” survey bridge release

**Operator-facing**

- **Standard + Field layouts** â€” Connect tab (collapsible/resizable panels, quick log/terminal, NTRIP phase 1), dedicated **Log** tab, survey bar (Presets, Recent, HUD, checklists).
- **Live GNSS quality** â€” GGA fix, satellites, HDOP on status bar and Survey HUD (POSPac Ch.16-style hints); stale detection; raw mode shows `n/a`.
- **Survey HUD** â€” Hz, transport/backpressure, session totals, GNSS tiles; layout persists (including box scale).
- **Operator guide** â€” `docs/OPERATOR_GUIDE.md` for bench/boat workflows.

**Reliability**

- Bridge asyncio thread, bounded queues, coalesced stats/logs, serial auto-reconnect, TCP client reconnect.
- Copy stats clipboard fixed; frozen EXE `version_info.txt` synced via `tools/sync_version_info.py`.
- `verify_all.py` compile excludes `dist/`; 100+ unit tests.

**Packaging**

- `.\build.ps1` / `.\release.ps1` â€” PyInstaller one-folder; zip `nmea-serial-bridge-v1.2.0-win64.zip`.

## v1.1.57

- **Audit fixes** â€” **Copy stats** uses correct bridge counters (was always zero); Windows `version_info.txt` syncs from `version.py` at build; Survey HUD **box scale** persists; **GNSS** chip shows **n/a (raw)** in raw binary mode; `verify_all` compile skips `dist/`; removed unused `qasync` dependency; NTRIP password field warns about plain-text local storage.

## v1.1.56

- **GNSS survey quality (live)** â€” parses GGA fix, satellite count, and HDOP using POSPac MMS Ch.16-style thresholds; shows on the **GNSS** status chip, stats bar, and Survey HUD (GNSS / Sats / HDOP tiles). Stale if no GGA for ~3 s. New module `survey_quality.py`.

## v1.1.55

- **Connect tab opens expanded** â€” all Connect sections start expanded by default (NTRIP and Quick terminal no longer start collapsed). Saved â€œcollapse allâ€ / strip-only sizes are reset on launch so the splitter fills the tab sensibly.

## v1.1.54

- **Connect panel sizes** â€” collapsed sections snap to a minimal strip height; expanded heights are remembered separately so reopening a panel restores your last size (drag-resize and collapse no longer overwrite saved heights with the strip size).

## v1.1.53

- **Connect collapse/expand fix** â€” panel toggles no longer call `adjustSize()` on the whole window (that was breaking the vertical splitter layout).
- **Bench pair setup fix** â€” stays on **Connect**, expands **Quick terminal**, opens the operator guide via desktop/`startfile` fallback, and runs preflight without clearing terminal output or forcing a jump to Diagnostics.

## v1.1.52

- **Resizable Connect panels** â€” Connect sections now sit in a vertical splitter: drag the handles between Run, Quick log, Quick terminal, Serial & network, NTRIP, etc. Sizes persist across restarts; **Reset sizes** restores defaults.

## v1.1.51

- **Connect tab panels** â€” Quick log, new **Quick terminal** (preflight output + one-line Sendâ†’COM), serial/network, NTRIP, and Run are collapsible with **Expand all / Collapse all** and **Arrange panelsâ€¦** (drag reorder + default collapsed state, persisted).

## v1.1.50

- **Bench pair setup** â€” **View â†’ Bench pair setupâ€¦**, **Connect** tab, and **Diagnostics** run the operator guide (bench/com0com Â§5) plus automated **com_free â†’ check_setup** preflight (no kernel driver; install com0com per guide).

## v1.1.49

- **Connect tab defaults** â€” Standard layout opens on **Connect** with a compact **Quick log** strip for bench testing.
- **Auto Log tab** â€” after the bridge has been **Running** for 20 seconds, the UI switches to the full **Log** tab.
- **File log retention choices** â€” Diagnostics file log now offers **10 / 25 / 50 / 100 MB** per file and **3 / 5 / 10** backups, with an on-screen duration estimate (rate-dependent; RTCM/high traffic fills faster than sparse NMEA).
- **NTRIP corrections (phase 1)** â€” Connect tab can enable an NTRIP caster stream; RTCM is multiplexed onto COM alongside bridged network data (caster, mount, user/pass saved in prefs).

## v1.1.48

- **Log tab beside Connect (Standard)** â€” live log is now a **Log** tab right after **Connect** instead of a side panel, so the main window stays simpler.
- **Cleaner top bar** â€” removed **Show log**, **Pause log**, and **Clear log** from the survey bar; use the **Log** tab for filters, pause (if shown there), clear, and save.

## v1.1.47

- **Top bar is now customizable and positionable** â€” added a `Customize top barâ€¦` manager (drag reorder + hide/show per control) and a one-click top/bottom move action, with per-layout persistence.
- **Handy keyboard shortcuts + in-app legend** â€” added bridge/theme/log/tab navigation shortcuts and a visible/hideable shortcuts legend panel with persisted visibility.
- **Preset quick menu now does auto test/connect** â€” selecting a top-bar preset now applies it, runs checklist test, and starts/restarts the bridge automatically for faster field workflow.
- **UI behavior rule codified** â€” added a dedicated workspace rule to keep hide/restore + reorder + crisp resize expectations enforced in future UI edits.

## v1.1.46

- **Log panel recoverability fix** â€” added a persistent top-bar **Show log** toggle (Standard/Minimal), so hiding the log never strands the user without a way to turn it back on.

## v1.1.45

- **Checklist preset labeling fix** â€” boat/bench checklist log lines now report the actual preset profile used (including fallback), avoiding misleading â€œDesk testâ€ labels on boat checks.
- **Boat checklist preset safety** â€” when a non-boat active preset is selected, boat checklist now explicitly falls back to production profile args and marks that fallback.

## v1.1.44

- **Stronger zone separation** â€” updated zone tinting so tabs and buttons adopt their assigned zone hues more aggressively (less same-color blending), improving visual differentiation across the UI.
- **Tab hide UX** â€” right-click tab hide + top-bar Hidden tabs restore flow is now active and persisted.

## v1.1.43

- **Checklist preset alignment** â€” Bench/Boat checklist actions now resolve from the active saved preset first, so diagnostics run against the same settings you selected in the UI.
- **Tab hide/restore control** â€” tabs now support right-click **Hide tab** and a new top-bar **Hidden tabs** menu to restore hidden tabs.

## v1.1.42

- **Copy stats now exports real snapshot data** â€” replaced tooltip/help-text copying with a structured runtime snapshot (state, preset, serial/network settings, NMEA mode, status chips, wire Hz, drops/rejects, and session totals).

## v1.1.41

- **Checklists now use the active saved preset** â€” Bench/Boat checklist actions resolve the currently selected saved preset first (with production fallback only when required), so diagnostics align with your preset settings across tabs/layouts.
- **Checklist visibility feedback** â€” launching a checklist now writes an explicit UI log line naming the preset being used, making it clear the action fired.

## v1.1.40

- **Readable zone swatch labels** â€” zone color hex values now auto-select light/dark text for contrast and use a clearer monospace style so color codes stay legible.
- **Standardize button behavior upgrade** â€” single click still applies stable Field Slate, while a **double-click** now generates a new cohesive standardized variant (uniform palette family with low chaos).

## v1.1.39

- **Drag-everything pass (phase 2)** â€” main tools tabs are now movable with per-layout persisted order (`main_tabs` and `tools_tabs`).
- **Diagnostics card ordering** â€” added a `Reorder cardsâ€¦` manager in Diagnostics with drag ordering that persists per UI mode.
- **Persistence coverage expanded** â€” added stored order for connection presets, recent sessions (plus pinning), diagnostics cards, theme zones, and tab strips so rearrangements stick across restarts.

## v1.1.38

- **Top-bar theme safety toggle** â€” added **Standardize theme** next to Randomize for one-click return to a stable slate look.
- **Drag-everything pass (phase 1)** â€” connection Presets list is now drag-reorderable with persistent order; Recent sessions now have a drag+pin manager; Theme zone rows are drag-reorderable for faster editing flow.

## v1.1.37

- **Drag-reorder for theme presets** â€” the saved Theme preset list now supports internal drag/drop reordering, and order persists across restarts.
- **Preset order persistence backend** â€” added explicit stored ordering for theme presets so manual arrangement is kept instead of alphabetical sorting.

## v1.1.36

- **Top-bar randomize button** â€” added **Randomize theme** to the survey bar for one-click palette changes during use.
- **Named theme presets** â€” Theme tab now has a saved preset list with **Save as preset**, **Load**, and **Delete**, so favorite looks live in-app with names (no clipboard workflow).

## v1.1.35

- **Theme pack export/import** â€” Theme tab now includes **Export theme packâ€¦** and **Import theme packâ€¦** to share and restore full zone color sets (plus seed-lock state) as JSON.
- **Share-ready fun themes** â€” imported packs apply immediately to `Randomized (current)` and can optionally include favorite-zone colors for quick reuse.

## v1.1.34

- **True multi-zone random themes** â€” randomize now generates distinct colors per UI zone (background, top bar, tabs, buttons, inputs, log panel, accent) so the app no longer stays in one monochrome family.
- **Per-zone color assignment** â€” Theme tab now exposes assignable swatches for each zone with color picker + reset, then applies the result instantly as `Randomized (current)` and supports saving that as favorite.

## v1.1.33

- **Theme polish / less monotony** â€” layered gradients now separate the window body, top survey bar, and default buttons so each area reads as a distinct surface instead of one flat color block.
- **Theme tab glow-up** â€” added dedicated Theme Studio styling (carded section, stronger hint/tip contrast, and distinct randomize/favorite button treatments) for a more playful feel without taking extra main workflow space.

## v1.1.32

- **Theme moved to dedicated tab** â€” removed the View â†’ Theme menu to keep the survey bar uncluttered; all theme controls now live in a **Theme** tools tab across Standard, Field, Log-first, and Minimal layouts.
- **Theme tab includes everything** â€” base themes, randomize, favorite-save, and lock-seed controls are grouped in one place without consuming main run/connect space.

## v1.1.31

- **Seed lock for random themes** â€” View â†’ Theme now has **Lock random seed (same vibe)** so Randomize follows a deterministic style family instead of jumping wildly each click.
- **Deterministic variation sequence** â€” when lock is on, each Randomize click advances to the next saved variant in that family (repeatable across restarts).

## v1.1.30

- **Theme randomizer** â€” View â†’ Theme now includes **Randomize** to generate a wild one-off palette, plus **Randomized (current)** and **Favorite random** modes.
- **Favorite save** â€” added **Save current random as favorite** so a good randomized palette survives restart and can be re-applied later.

## v1.1.29

- **Presets menu (survey bar)** â€” clicking **1** or any preset now runs after the menu closes (fixes lost clicks on Windows); checkmark moves even while the bridge is Running (survey fields update; COM/UDP apply on Stop).

## v1.1.28

- **Presets click fix** â€” `itemClicked` handler (works inside scroll area / on Windows); survey bar Presets menu and list share `_activate_preset_by_name`; preset **1** and other short names load reliably; list row stays in sync with active preset.

## v1.1.27

- **Presets tab** â€” visible list selection (gold/maroon highlight); single-click loads preset when stopped; Load/Save/Delete enable states match bridge state; programmatic list updates no longer steal clicks.

## v1.1.26

- **Backend** â€” `verify_all.py` runs full `unittest discover` (all `test_*.py`); `check_setup` copy matches Presets/Checklists workflow; recent-session + minimal drawer prefs tests.
- **UI sweep** â€” compact intent hint styling; screenshot-friendly `objectName`s on presets/diagnostics; Standard min size; checklist actions focus Diagnostics; operator guide shot list rewritten for current UI.

## v1.1.25

- **Deep UI pass** â€” Field/Log-first/Minimal show a one-line **intent hint** (full text on hover); Minimal uses a tools drawer like Field with prominent Start/Stop. Survey bar **Checklists** menu (bench/boat preflight). Product demo and **OPERATOR_GUIDE** updated for Presets/Recent (no Desk/Boat buttons). TCP setup in demo points at Presets â†’ Advanced.

## v1.1.24

- **Tab audit** â€” Standard Connect keeps Advanced network (no longer stolen by Presets tab); intent hint pinned above scroll; correct tab tooltips. NMEA strict sentence grid disables unless Strict is selected. Diagnostics TCP demo disables with other runners; drawer tabs renamed consistently.

## v1.1.23

- **GSOF removed** â€” dropped Trimble GSOF simulator (`gsof_codec.py`, `bench_gsof_survey.py`), Diagnostics **GSOF survey** button, and `docs/TRIMBLE_GSOF.md`. **Raw binary** mode remains for RTCM and other non-NMEA byte streams.

## v1.1.22

- **Raw GSOF log** â€” never decodes binary as text (avoids BEL/`0x07` beeps on Windows); verbose raw log always uses hex preview.
- **Status bar** â€” fixed height, stable elide width (no resize grow/reset loop); strip control chars from live log lines.

## v1.1.21

- **Diagnostics layout** â€” fixed tab blowing up when running bench scripts: capped output height, removed scroll-area stretch, status bar stays single-line (elided text + tooltip).

## v1.1.20

- **GSOF USV survey simulator** â€” Diagnostics **GSOF survey (UDP)** runs `bench_gsof_survey.py`: Trimble GENOUT (0x40) with **Time (1)**, **LLH (2)**, **Velocity (8)** at **5 Hz**, **~2 m/s** along a small box track. Requires **NMEA â†’ Raw binary** and bridge **Running** on UDP listen. New `gsof_codec.py` + tests.

## v1.1.19

- **Survey HUD** â€” removed scale (50â€“150%) and column (Autoâ€“4) dropdowns; layout is fixed at **100%** scale and **6** columns. Corner/Readable presets updated to match.

## v1.1.18

- **Named presets** â€” **Presets** tab replaces Desk/Boat buttons: load, save, save as, new, delete; custom names stored in `path_presets.json` (legacy desk/boat entries migrate automatically).
- **UI cleanup** â€” removed survey-bar Desk/Boat/COM/Preflight; **Net** tools tab removed (TCP/advanced network lives under Presets); **COM probe** removed from Diagnostics.

## v1.1.17

- **Bridge terminal (lite)** â€” live log **Saveâ€¦** export; **Hex (raw)** preview for GSOF/RTCM when Raw binary + verbose; **Sentences** filter (all / GGA / RMC / GGA+RMC) with â€œEvery NMEA lineâ€.
- **Status bar** â€” **NMEA** chip (passthrough / strict / raw + running state) beside Serial and Network on Standard and Field.
- **Recent sessions** â€” survey bar **Recent** menu restores last 5 COM + UDP + NMEA combos (`ui_prefs.json`).

## v1.1.16

- **Serial auto-reconnect** â€” optional (default on): retry COM every 2 s after disconnect while bridge keeps Running.
- **NMEA â†’ Raw binary (GSOF / RTCM)** â€” byte passthrough without line assembly; see `docs/TRIMBLE_GSOF.md`.
- **Docs** â€” README and `docs/OPERATOR_GUIDE.md` updated (network, Trimble, demo, layouts, troubleshooting).

## v1.1.15

- **Product demo** â€” **Stop auto** fully resets (orphan timers, stuck Auto chip, diagnostics process left â€œrunningâ€ blocking TCP demo reload). Reopening Demo recovers a half-stopped presenter window.

## v1.1.14

- **Product demo** â€” **Manual pitch mode by default**: Prev / Next / Run selected step enabled on open; click the list to jump; **Auto-play script** is optional. Green **Next step** is the primary control.

## v1.1.13

- **Product demo** â€” Stop no longer locks **Next step**; use it to walk the script manually after aborting auto. Stop no longer shows â€œDemo completeâ€ mid-run.

## v1.1.12

- **Product demo** â€” default **6s** hold per step (was ~3s on many beats); five new steps (survey bar, Tools/NMEA, wire Hz, HUD readout, Diagnostics, Preflight); step counter and `Ns of Ms` countdown.

## v1.1.11

- **Product demo** presenter UI: teleprompter card (large title, green cue, narration), phase-grouped step list, progress bar, countdown + **Next step**, **Stay on top**, dedicated warm theme; **Run automated demo** unchanged.

## v1.1.10

- HUD **From COM** wire Hz: coalesce rapid serial read bursts (com0com echo) so bench TCP demo tracks **Into COM** more closely; tooltips clarify wire Hz vs session sentence totals.

## v1.1.9

- **Product demo** â€” survey bar / View -> **Product demo**: ~6â€“8 min scripted walkthrough (UDP burst, Survey HUD, TCP map motion, Send, Boat preset) with on-screen narration for presenters.
- **TCP demo (~4 min)** â€” Diagnostics button + `bench_tcp_stress.py --demo` (fast LA legs, auto-stop); for live Hypack/chart motion without a 30 h soak.

## v1.1.8

- **TCP stress** drains inbound TCP while sending so long runs do not fill the COMâ†’net queue (Transport **Warn** / `DROP s->n`).

## v1.1.7

- **TCP stress** â€” `bench_tcp_stress.py` + Diagnostics **TCP stress (LAâ†’Sac)**: 5 sentences/tick @ 5 Hz, ~5 m/s from Los Angeles toward Sacramento; auto-reconnect; route resets at LA each session. Use **Stop** to end.

## v1.1.6

- **Survey HUD** â€” no more tiny â€œghostâ€ window on open: frameless flags set at creation, layout/size applied while hidden, invalid saved geometry discarded (< 420Ã—168).

## v1.1.5

- Layout picker: disclosure sections (**About**, **Details**) collapse without leaving empty dialog space (`SetFixedSize` + reflow on toggle).
- Shared `ui/collapsible.py` for disclosure rows; diagnostics collapsible cards use zero-height collapse.

## v1.1.4

- **Windows** â€” Diagnostics / Preflight / Full verify no longer flash `python.exe` console windows (GUI uses `pythonw`; nested `verify_all` steps use `CREATE_NO_WINDOW`).
- Survey bar **HUD** uses a single **Survey HUDâ€¦** action (no duplicate shortcut wiring).

## v1.1.3

- Fix layout picker crash (`UI_FIELD` import) that made `launcher.py --pick-ui` / `pythonw` launches show no window.

## v1.1.2

- Layout picker: readable OK/Cancel buttons; â€œRememberâ€ defaults **off** (clears saved choice when unchecked); collapsible **About** and per-layout **Details**; Field pre-selected when nothing saved.

## v1.1.1

- **Launcher / picker** â€” Standard + Field only; descriptions in console menu and first-run dialog; legacy `minimal` / `logfirst` choices auto-migrate to `field`; `launcher.py --ui field|standard` and `--pick-ui`.

## v1.1.0

- **Field UI** â€” merged Minimal + Log-first into one layout (large log, compact connect, tools drawer); launcher offers **Standard** + **Field** (saved `minimal` / `logfirst` map to Field).
- **Survey quick bar** â€” Desk, Boat, COM refresh, HUD, Tools, Pause log, Clear log, Preflight menu, Copy stats beside **View**.
- **Hz** â€” status shows **wire** update rate (UDP datagram / serial read per second), not NMEA sentences per second; session totals still count sentences.
- **Field log UX** â€” log presets with per-option hover help; font dense/readable applies to log; **Every NMEA line** label; smaller default window (720Ã—520).
- Network fields editable while stopped; queue backlog threshold aligned with bench probe; generic GGA sample (DPT not DBT); flow/backpressure wording fixes.

## v1.0.0

- First stable release package for distribution (`nmea-serial-bridge-v1.0.0-win64.zip`) with Standard/Minimal/Log-first UI workflows, survey HUD popout, diagnostics improvements, and release tooling for repeatable drops.

## v0.5.12

- **View** menu on all layouts: **Full screen** (F11) with friendlier splitter ratios on large displays; **Pop out survey stats** (Ctrl+Shift+S) â€” large, optional always-on-top window for Hypack / multi-monitor survey ops (Cube COM NMEA path vs MAVLink called out in UI copy).

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

- `.\release.ps1` â€” build + zip under `dist\`
- `gh auth login` â€” once per PC that publishes
- `.\release.ps1 -Publish` â€” tag + GitHub Release + upload zip  
  If publish failed after a successful build: `.\release.ps1 -PublishOnly` (no PyInstaller rerun).

**Many PCs:** they only download the **Release zip** from GitHub (or you copy `dist\â€¦zip`); no clone required on those machines.
