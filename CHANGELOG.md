# Changelog (personal progress)

High-level notes for **this fork / branch** (`feature/multi-ui-layouts-v0.5`).  
Version = `version.py` / Git tag when you run `.\release.ps1` or tag manually.

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
