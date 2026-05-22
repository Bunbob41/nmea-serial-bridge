# Changelog (personal progress)

High-level notes for **this fork / branch** (`feature/multi-ui-layouts-v0.5`).  
 Version = `version.py` / Git tag when you run `.\release.ps1` or tag manually.

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
