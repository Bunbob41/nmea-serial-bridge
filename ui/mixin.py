# ui/mixin.py — bridge start/stop, logging, validation (shared by all UIs)
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

import asyncio
import json
import sys
import time
import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from bench_config import (
    delete_preset,
    desk_udp_send_host,
    last_preset_name,
    list_preset_names,
    load_bench_defaults,
    load_preset,
    load_production_defaults,
    reorder_preset_names,
    save_preset,
    set_last_preset,
)
from bridge_core import (
    BridgeAsyncThread,
    NetMode,
    SerialNetBridge,
    SERIAL_OPEN_TIMEOUT_S,
    START_WATCHDOG_MS,
    UI_LOG_FLUSH_MS,
    UI_LOG_MAX_LINES_PER_FLUSH,
    UI_LOG_PENDING_MAX,
    _FileSurveyLog,
    file_log_retention_hint,
    _friendly_serial_error,
    _nmea_line_bytes,
    _open_serial_port_timed,
    _parse_port,
)
from ntrip_client import NtripConfig, parse_caster_host, run_ntrip_forwarder
from nmea_codec import NmeaFilter, NmeaMode
from ui.connection_fields import read_baud_widget
from ui.log_view import (
    PRESET_CUSTOM,
    LogViewState,
    log_line_allowed,
    state_from_preset,
)
from ui.log_view_dialog import LogViewDialog
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga
from log_serial_coalesce import serial_timeout_line_suppress
from py_interpreter import cli_python_gui_spawn, frozen_helper_program_args, qprocess_attach_no_console
from ui.bench_setup import extract_operator_guide_section, show_bench_setup_dialog
from ui.stats_line import (
    format_live_stats_line,
    stats_snapshot_from_merged,
    transport_alert_active,
)
from ui.stats_popout import SurveyStatsPopout
from ui.survey_dashboard import SurveyDashboard
from ui.app_icon import apply_app_icon
from ui.styles import apply_global_contrast_guard, bridge_stylesheet
from ui.theme_choice import (
    THEME_IDS,
    THEME_RANDOM_CURRENT,
    THEME_RANDOM_FAVORITE,
    THEME_SLATE,
    THEME_ZONE_KEYS,
    build_theme_pack,
    delete_theme_preset,
    list_theme_preset_names,
    load_random_seed_lock,
    load_random_theme_current_zones,
    load_random_theme_favorite_zones,
    load_random_theme_favorite,
    normalize_theme_pack,
    next_locked_random_variant,
    load_theme_preset,
    reorder_theme_presets,
    save_random_seed_lock,
    save_random_current_as_favorite,
    save_random_theme_current,
    save_random_theme_current_zones,
    save_random_theme_favorite_zones,
    save_theme_preset,
    save_theme_zone_order,
    load_theme_choice,
    save_theme_choice,
)
from ui.theme_palette import (
    DEFAULT_ZONE_COLORS,
    build_zone_theme_map,
    generate_random_zone_colors,
    generate_standardized_zone_colors,
)
from ui.picker import save_ui_choice
from ui.registry import create_window, normalize_ui_id
from ui.survey_top_bar import (
    SurveyTopBar,
    build_ui_switch_inner,
    configure_topbar_button,
    normalize_topbar_order,
)
from ui.ui_prefs import (
    load_bench_setup_prefs,
    load_diag_card_states,
    load_field_prefs,
    load_log_terminal_prefs,
    load_logfirst_prefs,
    load_recent_sessions,
    push_recent_session,
    recent_session_key,
    reorder_recent_sessions,
    save_diag_card_order,
    save_tab_order,
    save_top_bar_prefs,
    set_recent_session_pinned,
    load_diag_card_order,
    load_file_log_prefs,
    load_ntrip_prefs,
    load_tab_order,
    load_top_bar_prefs,
    load_hidden_tabs,
    save_file_log_prefs,
    save_ntrip_prefs,
    save_diag_card_states,
    save_field_prefs,
    save_log_terminal_prefs,
    save_logfirst_prefs,
    save_hidden_tabs,
)

def _resolve_repo_root() -> Path:
    """Return the directory that contains loose helper scripts.

    Dev (source run): two levels up from this file → project root.
    Frozen (PyInstaller one-folder): sys._MEIPASS is the exe directory where
    datas (verify_all.py, com_free.py, …) are extracted by the spec.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


_REPO_ROOT = _resolve_repo_root()
_DEFAULT_DIAG_CARD_ORDER = [
    "file_log",
    "screen_log",
    "traffic_quality",
    "automated_checks",
]

# Let Windows release the COM handle after Stop before Start (avoids “stuck until restart”).
START_AFTER_STOP_COOLDOWN_S = 0.35


def _start_cooldown_remaining_s(
    last_stop_mono: float,
    now: float,
    *,
    cooldown: float = START_AFTER_STOP_COOLDOWN_S,
) -> float:
    if last_stop_mono <= 0:
        return 0.0
    return max(0.0, cooldown - (now - last_stop_mono))


class BridgeLogicMixin:
    """Shared bridge GUI logic; subclasses must create widgets before _finalize_ui()."""

    @staticmethod
    def _bridge_running_safe(bridge_obj: object | None) -> bool:
        try:
            return bool(getattr(bridge_obj, "running", False))
        except Exception:
            return False

    def _is_bridge_running(self) -> bool:
        return self._bridge_running_safe(getattr(self, "bridge", None))

    def _init_bridge_state(self) -> None:
        self.bridge: Optional[SerialNetBridge] = None
        self._worker: Optional[BridgeAsyncThread] = None
        self._file_log: Optional[_FileSurveyLog] = None
        self._stopping = False
        self._start_gen = 0
        self._active_preset_name: Optional[str] = None
        self._presets_menu_pending: Optional[str] = None
        self._preset_list_syncing = False
        self._preset_editor_selection: Optional[str] = None
        self._starting = False
        self._bridge_stop_mono = 0.0
        self._start_defer_pending = False
        self._stop_guard_timer = QtCore.QTimer(self)
        self._stop_guard_timer.setSingleShot(True)
        self._stop_guard_timer.timeout.connect(self._stop_timeout_guard)
        self._start_watchdog_timer = QtCore.QTimer(self)
        self._start_watchdog_timer.setSingleShot(True)
        self._start_watchdog_timer.timeout.connect(self._start_watchdog_fired)
        self._pending_ui: Deque[str] = deque()
        self._ui_drops = 0
        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)
        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)
        self._stats_popout_window: Optional[SurveyStatsPopout] = None
        self._dashboard_window: Optional[SurveyDashboard] = None
        self._splitter_sizes_backup: Optional[list[int]] = None
        self._diag_qprocess: Optional[QtCore.QProcess] = None
        self._diag_current_title = ""
        self._ui_log_serial_dup_last: Optional[str] = None
        self._ui_log_serial_dup_mono: float = 0.0
        self._theme_id = load_theme_choice()
        self._theme_actions: dict[str, QtGui.QAction] = {}
        self._theme_random_current_action: Optional[QtGui.QAction] = None
        self._theme_random_favorite_action: Optional[QtGui.QAction] = None
        self._theme_save_favorite_action: Optional[QtGui.QAction] = None
        self._theme_random_lock_action: Optional[QtGui.QAction] = None
        self._theme_combo_syncing = False
        self._theme_zone_colors: dict[str, str] = dict(DEFAULT_ZONE_COLORS)
        self._standardize_click_timer = QtCore.QTimer(self)
        self._standardize_click_timer.setSingleShot(True)
        self._standardize_click_timer.timeout.connect(self._apply_standardized_default)
        self._tab_catalog: dict[str, dict[str, tuple[QtWidgets.QWidget, str]]] = {}
        self._tab_hidden: dict[str, set[str]] = {}
        self._tab_rebuild_guard = False
        self._primary_tabs_key: Optional[str] = None
        self._topbar_widgets: dict[str, QtWidgets.QWidget] = {}
        self._topbar_labels: dict[str, str] = {}
        self._topbar_order: list[str] = []
        self._topbar_hidden: set[str] = set()
        self._topbar_chip_weights: dict[str, float] = {}
        self._topbar_rebuild_guard = False
        self._shortcuts_visible = False
        self._shortcut_legend_lines: list[str] = []
        self._topbar_position = "top"
        self._log_pause = False
        self._log_autoscroll = True
        self._log_filter_rx = True
        self._log_filter_tx = True
        self._log_filter_warn = True
        self._log_view_state = LogViewState()
        self._log_view_sync_guard = False
        self._log_paused_dropped = 0
        self._diag_card_states = load_diag_card_states(getattr(self, "_ui_mode", "standard"))
        self._log_tab_auto_timer = QtCore.QTimer(self)
        self._log_tab_auto_timer.setSingleShot(True)
        self._log_tab_auto_timer.timeout.connect(self._auto_switch_to_log_tab)
        self._ntrip_future: Optional[asyncio.Future] = None
        self._bench_preflight_chain = False
        from app_facade import BridgeAppFacade

        self._app_facade = BridgeAppFacade(self)
        self._web_server = None
        self._web_start_retry_gen = 0
        self._layout_switch_in_progress = False
        self._serial_retry_refresh_mono = 0.0

    @staticmethod
    def _qt_widget_alive(widget: Optional[QtWidgets.QWidget]) -> bool:
        if widget is None:
            return False
        try:
            from shiboken6 import isValid

            return bool(isValid(widget))
        except Exception:
            try:
                widget.isVisible()
                return True
            except RuntimeError:
                return False

    def _close_auxiliary_windows(self) -> None:
        """Survey HUD + Dashboard — must close before layout switch or main window teardown."""
        timer = getattr(self, "_stats_timer", None)
        if timer is not None:
            timer.stop()
        for attr in ("_stats_popout_window", "_dashboard_window"):
            pop = getattr(self, attr, None)
            if pop is None:
                continue
            try:
                pop.close()
            except RuntimeError:
                pass
            setattr(self, attr, None)

    def _stop_bridge_worker_sync(self, wait_ms: int = 4000) -> None:
        """Join asyncio bridge thread so the process can exit cleanly."""
        worker = getattr(self, "_worker", None)
        if worker is None:
            return
        try:
            if worker.isRunning():
                worker.request_stop()
                worker.wait(max(500, int(wait_ms)))
        except RuntimeError:
            pass
        self._worker = None
        self.bridge = None

    def _reset_ui_log_serial_coalesce(self) -> None:
        self._ui_log_serial_dup_last = None
        self._ui_log_serial_dup_mono = 0.0

    def _finalize_ui(self) -> None:
        lay = self.layout()
        if isinstance(lay, QtWidgets.QVBoxLayout) and not getattr(self, "_survey_menu_placed", False):
            bar = self._create_survey_menu_bar()
            legend = self._create_shortcuts_legend_panel()
            if self._topbar_position == "bottom":
                lay.addWidget(legend)
                lay.addWidget(bar)
            else:
                lay.insertWidget(0, bar)
                lay.insertWidget(1, legend)
            self._survey_menu_placed = True

        from ui.controls import wire_connection_controls
        wire_connection_controls(self)
        self.refresh_ports()
        self._apply_startup_connection_fields()
        self._mode_toggle()
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)
        self._stats_timer.start(400)
        self._restore_log_view_prefs()
        self._sync_nmea_mode_ui()
        self._refresh_nmea_status_chip()
        self._sync_bench_setup_button_visibility()
        self._rebuild_recent_sessions_menu()
        self._refresh_preset_list()
        self._sync_preset_action_buttons()
        self._apply_theme(self._theme_id, persist=False)
        self._apply_fixed_connect_row_style()
        apply_app_icon(self)
        self._force_quit = False
        from ui.tray_support import install_tray_icon

        self._tray_icon = install_tray_icon(self)
        self._restore_file_log_prefs_ui()
        self._restore_auto_discover_pref()
        self._log_startup_self_check()
        self._on_ui_ready()
        self._init_web_and_facade()
        self._start_auto_discovery_thread()

    def _log_startup_self_check(self) -> None:
        from version import __version__
        from ui import picker, ui_prefs

        mode = str(getattr(self, "_ui_mode", "unknown"))
        self._log_ui(
            "Startup self-check: "
            f"v{__version__} | mode={mode} | "
            f"ui_choice={picker.CONFIG_PATH} | ui_prefs={ui_prefs.CONFIG_PATH}"
        )

    def _create_survey_menu_bar(self) -> QtWidgets.QWidget:
        """Draggable chip top bar — drag ⋮⋮ grip to reorder; right-click to hide."""
        from ui.ui_editor import migrate_topbar_hidden, migrate_topbar_order

        prefs = load_top_bar_prefs(getattr(self, "_ui_mode", "standard"))
        self._topbar_order = migrate_topbar_order(list(prefs.get("order", [])))
        self._topbar_hidden = migrate_topbar_hidden(set(str(x) for x in prefs.get("hidden", [])))
        self._topbar_chip_weights = dict(prefs.get("chip_weights", {}))
        self._shortcuts_visible = bool(prefs.get("shortcuts_visible", False))
        self._topbar_position = str(prefs.get("position", "top")).strip().lower() or "top"
        self._topbar_widgets.clear()
        self._topbar_labels.clear()
        bar = SurveyTopBar(self)
        self._survey_top_bar = bar

        view_btn = QtWidgets.QToolButton()
        view_btn.setText("View")
        view_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        view_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        view_btn.setAutoRaise(True)
        view_menu = QtWidgets.QMenu(view_btn)

        act_fs = QtGui.QAction("Full screen", self)
        act_fs.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F11))
        act_fs.setStatusTip("Toggle full screen (survey / multi-monitor layouts)")
        act_fs.triggered.connect(self._toggle_fullscreen)
        self.addAction(act_fs)
        view_menu.addAction(act_fs)

        act_hud = QtGui.QAction("HUD…", self)
        act_hud.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        act_hud.setStatusTip(
            "Open Survey HUD (Hz, GNSS, session) and Dashboard (bridge trust & reliability)"
        )
        act_hud.triggered.connect(self._open_hud)
        self.addAction(act_hud)
        view_menu.addAction(act_hud)

        act_pop = QtGui.QAction("Survey HUD only…", self)
        act_pop.setStatusTip("Live metrics window only (Hz, GNSS, backpressure tiles)")
        act_pop.triggered.connect(self._open_stats_popout)
        view_menu.addAction(act_pop)

        act_dashboard = QtGui.QAction("Dashboard only…", self)
        act_dashboard.setStatusTip("Bridge trust panel only (reliability checks & connection chips)")
        act_dashboard.triggered.connect(self._open_dashboard)
        view_menu.addAction(act_dashboard)

        act_ui_editor = QtGui.QAction("UI editor…", self)
        act_ui_editor.setStatusTip(self._ui_editor_status_tip())
        act_ui_editor.triggered.connect(self._open_ui_editor)
        view_menu.addAction(act_ui_editor)
        act_bench = QtGui.QAction("Bench pair setup…", self)
        act_bench.setStatusTip(
            "Open the bench/com0com guide and run com_free + check_setup (same as preflight_bench.bat)"
        )
        act_bench.triggered.connect(self._open_bench_pair_setup)
        view_menu.addAction(act_bench)
        act_reset_bar = QtGui.QAction("Reset top bar layout", self)
        act_reset_bar.setStatusTip("Restore default chip order and show all hidden chips")
        act_reset_bar.triggered.connect(lambda: self._survey_top_bar.reset_layout())
        view_menu.addAction(act_reset_bar)
        act_show_bar = QtGui.QAction("Show all top bar chips", self)
        act_show_bar.triggered.connect(lambda: self._survey_top_bar.show_all_chips())
        view_menu.addAction(act_show_bar)
        act_shortcuts = QtGui.QAction("Toggle shortcuts legend", self)
        act_shortcuts.triggered.connect(lambda: self._toggle_shortcuts_legend(not self._shortcuts_visible))
        view_menu.addAction(act_shortcuts)
        act_move_bar = QtGui.QAction("Move top bar to bottom", self)
        act_move_bar.triggered.connect(
            lambda: self._set_top_bar_position("top" if self._topbar_position == "bottom" else "bottom")
        )
        view_menu.addAction(act_move_bar)

        view_btn.setMenu(view_menu)
        configure_topbar_button(
            view_btn, "View", tooltip="Layout, HUD, and bar options"
        )
        self._topbar_widgets["view"] = view_btn
        self._topbar_labels["view"] = "View"
        bar.register("view", "View", view_btn)

        presets_btn = QtWidgets.QToolButton()
        presets_btn.setObjectName("surveyQuickBtn")
        presets_btn.setText("Presets")
        presets_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        # MenuButtonPopup: left-click navigates to the Presets page;
        # the small arrow on the right still opens the quick-load dropdown.
        presets_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        presets_btn.setAutoRaise(True)
        presets_btn.setToolTip(
            "Click to open the Presets page. "
            "Click the arrow ▾ to load a saved preset and start the bridge."
        )
        presets_btn.clicked.connect(self._open_presets_tab)
        self._presets_quick_menu = QtWidgets.QMenu(presets_btn)
        self._presets_menu_group = QtGui.QActionGroup(self)
        self._presets_menu_group.setExclusive(True)
        self._presets_quick_menu.triggered.connect(self._on_presets_quick_menu_triggered)
        presets_btn.setMenu(self._presets_quick_menu)
        configure_topbar_button(
            presets_btn,
            "Presets",
            tooltip="Click to open Presets page · Arrow ▾ to quick-load a preset",
        )
        self._topbar_widgets["presets"] = presets_btn
        self._topbar_labels["presets"] = "Presets"
        bar.register("presets", "Presets", presets_btn)

        recent_btn = QtWidgets.QToolButton()
        recent_btn.setObjectName("surveyQuickBtn")
        recent_btn.setText("Recent")
        recent_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        recent_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        recent_btn.setAutoRaise(True)
        recent_btn.setToolTip("Restore a recent COM + network + NMEA session (last 5)")
        self._recent_sessions_btn = recent_btn
        self._recent_sessions_menu = QtWidgets.QMenu(recent_btn)
        recent_btn.setMenu(self._recent_sessions_menu)
        configure_topbar_button(
            recent_btn,
            "Recent",
            tooltip="Restore a recent COM + network + NMEA session (last 5)",
        )
        self._topbar_widgets["recent"] = recent_btn
        self._topbar_labels["recent"] = "Recent"
        bar.register("recent", "Recent", recent_btn)

        hud_btn = self._make_topbar_tool_button(
            "HUD", act_hud.statusTip(), None, key="hud"
        )
        hud_btn.setDefaultAction(act_hud)
        bar.register("hud", "HUD", hud_btn)

        # Tools chip is only meaningful on layouts with a floating drawer (Field).
        # Standard layout has a dedicated "Tools" tab; skip to avoid ribbon clutter.
        if getattr(self, "_ui_mode", "standard") != "standard":
            tools_btn = self._make_topbar_tool_button(
                "Tools",
                "Show or hide NMEA / Terminal / Diagnostics (Field layout)",
                None,
                key="tools",
                checkable=True,
            )
            self._survey_btn_tools = tools_btn
            bar.register("tools", "Tools", tools_btn)

        for key, text, tip, slot in (
            (
                "randomize_theme",
                "Randomize theme",
                "Instantly generate a new fun multi-zone theme palette",
                self._randomize_theme_now,
            ),
            (
                "standardize_theme",
                "Standardize theme",
                "Switch to the stable Field Slate style",
                self._standardize_theme_now,
            ),
            (
                "ui_editor",
                "UI editor",
                self._ui_editor_status_tip(),
                self._open_ui_editor,
            ),
            (
                "copy_stats",
                "Copy stats",
                "Copy status-bar metrics to clipboard (paste into notes / chat)",
                self._copy_stats_to_clipboard,
            ),
        ):
            btn = self._make_topbar_tool_button(text, tip, slot, key=key)
            bar.register(key, text, btn)

        ui_inner = build_ui_switch_inner(self, on_toggle=self._toggle_ui_layout)
        bar.register("ui_switch", "Layout", ui_inner, pin_right=True)

        drawer = getattr(self, "_drawer_btn", None)
        _tools_chip = getattr(self, "_survey_btn_tools", None)
        if _tools_chip is not None:
            if drawer is not None:
                _tools_chip.setChecked(drawer.isChecked())
                drawer.toggled.connect(_tools_chip.setChecked)
                _tools_chip.toggled.connect(drawer.setChecked)
            else:
                _tools_chip.clicked.connect(self._toggle_tools_drawer)
        shortcuts_btn = self._make_topbar_tool_button(
            "Shortcuts",
            "Show or hide the keyboard shortcuts legend",
            self._toggle_shortcuts_button_clicked,
            key="shortcuts",
            checkable=True,
        )
        shortcuts_btn.setChecked(self._shortcuts_visible)
        self._shortcuts_toggle_btn = shortcuts_btn
        bar.register("shortcuts", "Shortcuts", shortcuts_btn)

        # Handy always-on shortcuts
        self._register_shortcut("Start bridge", "Ctrl+B", self.start_bridge)
        self._register_shortcut("Stop bridge", "Ctrl+Shift+B", self.stop_bridge)
        self._register_shortcut("Randomize theme", "Ctrl+R", self._randomize_theme_now)
        self._register_shortcut("Standardize theme", "Ctrl+Shift+R", self._standardize_theme_now)
        self._register_shortcut("Toggle log panel", "Ctrl+L", self._toggle_log_visibility_shortcut)
        self._register_shortcut(
            "Toggle shortcuts legend",
            "F1",
            lambda: self._toggle_shortcuts_legend(not self._shortcuts_visible),
        )
        for i in range(1, 7):
            self._register_shortcut(
                f"Jump tab {i}",
                f"Ctrl+{i}",
                lambda idx=i - 1: self._jump_to_tab_index(idx),
            )

        bar.set_persist_callback(self._persist_top_bar_from_bar)
        bar.set_host_window(self)
        bar.set_prefs(
            self._topbar_order,
            self._topbar_hidden,
            self._topbar_chip_weights,
        )
        self.survey_menu_bar = bar
        self._ensure_readable_top_bar()
        return bar

    def _ensure_readable_top_bar(self) -> None:
        """First impression: full top-bar labels when possible, else short readable tiles."""
        if getattr(self, "_readable_topbar_done", False):
            return
        self._readable_topbar_done = True
        bar = getattr(self, "_survey_top_bar", None)
        if bar is None:
            return
        bar.ensure_host_fits_full_labels(self)
        bar.prefer_expanded_on_show(self)
        bar.sync_host_minimum_width(self)

    def _open_ui_editor(self) -> None:
        from ui.ui_editor import open_ui_editor

        open_ui_editor(self)

    def _persist_top_bar_from_bar(
        self,
        order: list[str],
        hidden: set[str],
        chip_weights: Optional[dict[str, float]] = None,
    ) -> None:
        from ui.ui_editor import migrate_topbar_hidden, migrate_topbar_order

        self._topbar_order = migrate_topbar_order(order)
        self._topbar_hidden = migrate_topbar_hidden(hidden)
        if chip_weights:
            self._topbar_chip_weights = dict(chip_weights)
        self._save_top_bar_prefs()

    def _rebuild_top_bar_widgets(self) -> None:
        bar = getattr(self, "_survey_top_bar", None)
        if bar is None:
            return
        if self._topbar_rebuild_guard:
            return
        self._topbar_rebuild_guard = True
        try:
            bar.set_prefs(
                self._topbar_order,
                self._topbar_hidden,
                self._topbar_chip_weights,
            )
        finally:
            self._topbar_rebuild_guard = False

    def _save_top_bar_prefs(self) -> None:
        weights = dict(getattr(self, "_topbar_chip_weights", {}))
        bar = getattr(self, "_survey_top_bar", None)
        if bar is not None:
            weights = bar.chip_weights()
        save_top_bar_prefs(
            getattr(self, "_ui_mode", "standard"),
            {
                "order": list(self._topbar_order),
                "hidden": sorted(self._topbar_hidden),
                "shortcuts_visible": bool(self._shortcuts_visible),
                "position": self._topbar_position,
                "chip_weights": weights,
            },
        )

    def _set_top_bar_position(self, position: str) -> None:
        pos = "bottom" if str(position).strip().lower() == "bottom" else "top"
        self._topbar_position = pos
        lay = self.layout()
        bar = getattr(self, "survey_menu_bar", None)
        legend = getattr(self, "_shortcuts_panel", None)
        if isinstance(lay, QtWidgets.QVBoxLayout) and bar is not None and legend is not None:
            lay.removeWidget(bar)
            lay.removeWidget(legend)
            if pos == "bottom":
                lay.addWidget(legend)
                lay.addWidget(bar)
            else:
                lay.insertWidget(0, bar)
                lay.insertWidget(1, legend)
        self._save_top_bar_prefs()
        self._log_ui(f"[UI] Top bar moved to {pos}.")

    def _create_shortcuts_legend_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame(self)
        panel.setObjectName("statusBanner")
        row = QtWidgets.QHBoxLayout(panel)
        row.setContentsMargins(8, 4, 8, 4)
        lbl = QtWidgets.QLabel()
        lbl.setObjectName("tabHint")
        lbl.setWordWrap(True)
        self._shortcuts_label = lbl
        row.addWidget(lbl, 1)
        close_btn = QtWidgets.QPushButton("Hide")
        close_btn.setObjectName("themeStudioIOBtn")
        close_btn.clicked.connect(lambda: self._toggle_shortcuts_legend(False))
        row.addWidget(close_btn, 0)
        self._shortcut_legend_lines = [
            "F11 Full screen",
            "F1 Toggle shortcuts legend",
            "Ctrl+B Start bridge",
            "Ctrl+Shift+B Stop bridge",
            "Ctrl+R Randomize theme",
            "Ctrl+Shift+R Standardize theme",
            "Ctrl+L Open Log tab",
            "Ctrl+1..6 Jump tabs",
        ]
        lbl.setText("Shortcuts: " + " | ".join(self._shortcut_legend_lines))
        panel.setVisible(self._shortcuts_visible)
        self._shortcuts_panel = panel
        return panel

    def _toggle_shortcuts_legend(self, visible: bool) -> None:
        self._shortcuts_visible = bool(visible)
        panel = getattr(self, "_shortcuts_panel", None)
        if panel is not None:
            panel.setVisible(self._shortcuts_visible)
        btn = getattr(self, "_shortcuts_toggle_btn", None)
        if btn is not None and btn.isChecked() != self._shortcuts_visible:
            btn.setChecked(self._shortcuts_visible)
        self._save_top_bar_prefs()

    def _toggle_shortcuts_button_clicked(self, checked: bool) -> None:
        self._toggle_shortcuts_legend(bool(checked))

    def _make_topbar_tool_button(
        self,
        text: str,
        tooltip: str,
        slot: object | None,
        *,
        key: str,
        checkable: bool = False,
    ) -> QtWidgets.QToolButton:
        btn = QtWidgets.QToolButton()
        btn.setObjectName("surveyQuickBtn")
        btn.setAutoRaise(True)
        configure_topbar_button(btn, text, tooltip=tooltip)
        if checkable:
            btn.setCheckable(True)
        if slot is not None:
            btn.clicked.connect(slot)  # type: ignore[arg-type]
        self._topbar_widgets[key] = btn
        self._topbar_labels[key] = text
        return btn

    def _toggle_tools_drawer(self) -> None:
        drawer = getattr(self, "_drawer_btn", None)
        if drawer is not None:
            drawer.setChecked(not drawer.isChecked())
            return
        QtWidgets.QMessageBox.information(
            self,
            "Tools",
            "Open the Connect, NMEA, Terminal, or Diagnostics tabs in this layout.",
        )

    def _setup_reorderable_tools_nav(
        self,
        nav: QtWidgets.QListWidget,
        stack: QtWidgets.QStackedWidget,
        catalog: dict[str, tuple[QtWidgets.QWidget, str]],
        key: str = "tools_tabs",
    ) -> None:
        """Standard Tools tab: sidebar list + stacked pages (UI editor reorders this)."""
        self._tab_catalog[key] = dict(catalog)
        self._tab_hidden[key] = set(load_hidden_tabs(getattr(self, "_ui_mode", "standard"), key))
        self._rebuild_tools_nav_from_state(key)
        nav.setToolTip(
            "Tools sidebar — order and visibility are set in View → UI editor → Tools tabs."
        )

    def _visible_tools_tab_names(self, key: str) -> list[str]:
        catalog = self._tab_catalog.get(key, {})
        if not catalog:
            return []
        hidden = self._tab_hidden.get(key, set())
        from ui.ui_prefs import dedupe_preserve_order

        saved = load_tab_order(getattr(self, "_ui_mode", "standard"), key)
        visible_saved = dedupe_preserve_order(
            [name for name in saved if name in catalog and name not in hidden]
        )
        visible_names = list(visible_saved)
        for name in catalog.keys():
            if name not in hidden and name not in visible_names:
                visible_names.append(name)
        visible_names = dedupe_preserve_order(visible_names)
        if (
            key == "tools_tabs"
            and "Phone" in catalog
            and "Phone" not in hidden
            and "Phone" not in visible_names
        ):
            if "Presets" in visible_names:
                visible_names.insert(visible_names.index("Presets") + 1, "Phone")
            else:
                visible_names.insert(0, "Phone")
        return visible_names

    def _rebuild_tools_nav_from_state(self, key: str) -> None:
        nav = getattr(self, "_tools_nav", None)
        stack = getattr(self, "_tools_stack", None)
        catalog = self._tab_catalog.get(key, {})
        if nav is None or stack is None or not catalog:
            return
        visible_names = self._visible_tools_tab_names(key)
        prev_label = ""
        item = nav.currentItem()
        if item is not None:
            prev_label = item.text().strip()
        while stack.count():
            w = stack.widget(0)
            stack.removeWidget(w)
        nav.clear()
        for name in visible_names:
            widget, tip = catalog[name]
            stack_idx = stack.indexOf(widget)
            if stack_idx < 0:
                stack.addWidget(widget)
                stack_idx = stack.count() - 1
            row = QtWidgets.QListWidgetItem(name)
            row.setToolTip(tip)
            row.setData(QtCore.Qt.ItemDataRole.UserRole, stack_idx)
            nav.addItem(row)
        if not visible_names:
            return
        pick = 0
        if prev_label:
            for i in range(nav.count()):
                it = nav.item(i)
                if it is not None and it.text().strip() == prev_label:
                    pick = i
                    break
        nav.blockSignals(True)
        try:
            nav.setCurrentRow(pick)
            stack.setCurrentIndex(pick)
        finally:
            nav.blockSignals(False)

    def _persist_tools_nav_state(self, key: str) -> None:
        nav = getattr(self, "_tools_nav", None)
        if nav is None:
            return
        order = [
            nav.item(i).text().strip()
            for i in range(nav.count())
            if nav.item(i) is not None and nav.item(i).text().strip()
        ]
        if order:
            save_tab_order(getattr(self, "_ui_mode", "standard"), key, order)
        hidden = sorted(self._tab_hidden.get(key, set()))
        save_hidden_tabs(getattr(self, "_ui_mode", "standard"), key, hidden)

    def _setup_reorderable_tabs(self, tabs: QtWidgets.QTabWidget, key: str) -> None:
        catalog: dict[str, tuple[QtWidgets.QWidget, str]] = {}
        for i in range(tabs.count()):
            label = tabs.tabText(i)
            if not label:
                continue
            catalog[label] = (tabs.widget(i), tabs.tabToolTip(i))
        self._tab_catalog[key] = catalog
        self._tab_hidden[key] = set(load_hidden_tabs(getattr(self, "_ui_mode", "standard"), key))
        self._primary_tabs_key = key
        bar = tabs.tabBar()
        bar.setMovable(True)
        bar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        bar.customContextMenuRequested.connect(
            lambda pos, t=tabs, k=key: self._on_tabs_context_menu(t, k, pos)
        )
        self._rebuild_tabs_from_state(tabs, key)
        bar.tabMoved.connect(lambda *_args, t=tabs, k=key: self._persist_tab_state(t, k))

    def _rebuild_tabs_from_state(self, tabs: QtWidgets.QTabWidget, key: str) -> None:
        catalog = self._tab_catalog.get(key, {})
        if not catalog:
            return
        visible_names = self._visible_tools_tab_names(key)
        self._tab_rebuild_guard = True
        try:
            while tabs.count():
                tabs.removeTab(0)
            for name in visible_names:
                widget, tip = catalog[name]
                idx = tabs.addTab(widget, name)
                if tip:
                    tabs.setTabToolTip(idx, tip)
        finally:
            self._tab_rebuild_guard = False
        bar = tabs.tabBar()
        bar.setMovable(True)
        bar.setToolTip(
            "Drag tabs to reorder. Right-click a tab to hide it; "
            "right-click empty tab-bar space to restore hidden tabs."
        )

    def _persist_tab_state(self, tabs: QtWidgets.QTabWidget, key: str) -> None:
        if self._tab_rebuild_guard:
            return
        order = [tabs.tabText(i) for i in range(tabs.count()) if tabs.tabText(i).strip()]
        save_tab_order(getattr(self, "_ui_mode", "standard"), key, order)
        hidden = sorted(self._tab_hidden.get(key, set()))
        save_hidden_tabs(getattr(self, "_ui_mode", "standard"), key, hidden)
        self._log_ui(f"[UI] Reordered {key.replace('_', ' ')}.")

    def _populate_hidden_tab_restore_actions(self, menu: QtWidgets.QMenu, key: str) -> bool:
        hidden = sorted(self._tab_hidden.get(key, set()))
        if not hidden:
            return False
        show_all = QtGui.QAction("Show all hidden tabs", self)
        show_all.triggered.connect(lambda checked=False, k=key: self._show_all_hidden_tabs(k))
        menu.addAction(show_all)
        for label in hidden:
            act = QtGui.QAction(f"Show {label}", self)
            act.triggered.connect(lambda checked=False, n=label, k=key: self._show_hidden_tab(k, n))
            menu.addAction(act)
        return True

    def _on_tabs_context_menu(
        self, tabs: QtWidgets.QTabWidget, key: str, pos: QtCore.QPoint
    ) -> None:
        bar = tabs.tabBar()
        idx = bar.tabAt(pos)
        menu = QtWidgets.QMenu(self)
        if idx >= 0:
            label = tabs.tabText(idx).strip()
            if label:
                hide_action = QtGui.QAction(f"Hide tab: {label}", self)
                hide_action.setEnabled(tabs.count() > 1)
                menu.addAction(hide_action)
                if self._tab_hidden.get(key):
                    menu.addSeparator()
                    self._populate_hidden_tab_restore_actions(menu, key)
                chosen = menu.exec(bar.mapToGlobal(pos))
                if chosen is hide_action and tabs.count() > 1:
                    self._tab_hidden.setdefault(key, set()).add(label)
                    self._rebuild_tabs_from_state(tabs, key)
                    self._persist_tab_state(tabs, key)
                return
        if self._populate_hidden_tab_restore_actions(menu, key):
            menu.exec(bar.mapToGlobal(pos))

    def _show_hidden_tab(self, key: str, label: str) -> None:
        hidden = self._tab_hidden.setdefault(key, set())
        if label in hidden:
            hidden.remove(label)
        if key == "tools_tabs" and getattr(self, "_tools_nav", None) is not None:
            self._rebuild_tools_nav_from_state(key)
            self._persist_tools_nav_state(key)
            return
        tabs = getattr(self, "_main_tabs", None) if key == "main_tabs" else getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        self._rebuild_tabs_from_state(tabs, key)
        self._persist_tab_state(tabs, key)

    def _show_all_hidden_tabs(self, key: str) -> None:
        hidden = self._tab_hidden.setdefault(key, set())
        if not hidden:
            return
        hidden.clear()
        if key == "tools_tabs" and getattr(self, "_tools_nav", None) is not None:
            self._rebuild_tools_nav_from_state(key)
            self._persist_tools_nav_state(key)
            return
        tabs = getattr(self, "_main_tabs", None) if key == "main_tabs" else getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        self._rebuild_tabs_from_state(tabs, key)
        self._persist_tab_state(tabs, key)

    def _toggle_log_pause_quick(self) -> None:
        chk = getattr(self, "chk_log_pause", None)
        if chk is not None:
            chk.setChecked(not chk.isChecked())
            return
        self._set_log_pause(not getattr(self, "_log_pause", False))

    def _register_shortcut(self, title: str, seq: str, slot: object) -> None:
        act = QtGui.QAction(title, self)
        act.setShortcut(QtGui.QKeySequence(seq))
        act.triggered.connect(slot)  # type: ignore[arg-type]
        self.addAction(act)

    def _ui_editor_status_tip(self) -> str:
        mode = getattr(self, "_ui_mode", "standard")
        if mode == "standard":
            return (
                "Show or hide top bar tiles, Connect sections, main tabs, and "
                "Tools sidebar items (Presets, Phone, NMEA, …)"
            )
        return "Show or hide top bar tiles and Tools drawer tabs (Field layout)"

    def _toggle_log_visibility_shortcut(self) -> None:
        if getattr(self, "_ui_mode", "") == "standard":
            self._focus_log_tab()
            return
        view = getattr(self, "log_view", None)
        if view is not None:
            view.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
            return
        chk = getattr(self, "chk_show_log", None)
        if chk is not None:
            chk.setChecked(not chk.isChecked())

    def _jump_to_tab_index(self, idx: int) -> None:
        tabs = getattr(self, "_main_tabs", None) or getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        if 0 <= idx < tabs.count():
            tabs.setCurrentIndex(idx)
            drawer = getattr(self, "_drawer_btn", None)
            if drawer is not None and not drawer.isChecked():
                drawer.setChecked(True)

    def _clear_live_log(self) -> None:
        view = getattr(self, "log_view", None)
        if view is not None:
            view.clear()

    def _save_live_log(self) -> None:
        view = getattr(self, "log_view", None)
        if view is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save live log",
            "",
            "Text files (*.txt);;Log files (*.log);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(view.toPlainText(), encoding="utf-8")
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Save live log", f"Could not write file:\n{e}")
            return
        self._log_ui(f"[UI] Saved live log ({len(view.toPlainText())} chars) → {path}")

    def _log_view_prefs_dict(self) -> dict:
        mode = getattr(self, "_ui_mode", "standard")
        if mode == "field":
            return load_field_prefs()
        if mode == "logfirst":
            return load_logfirst_prefs()
        return load_log_terminal_prefs()

    def _restore_log_view_prefs(self) -> None:
        self._apply_log_view_state(
            LogViewState.from_dict(self._log_view_prefs_dict()),
            persist=False,
            sync_widgets=True,
        )

    def _save_log_view_prefs(self) -> None:
        if self._log_view_sync_guard:
            return
        payload = self._log_view_state.to_dict()
        mode = getattr(self, "_ui_mode", "standard")
        if mode == "field":
            existing = load_field_prefs()
            existing.update(payload)
            save_field_prefs(existing)
        elif mode == "logfirst":
            save_logfirst_prefs(payload)
        else:
            save_log_terminal_prefs(payload)

    def _save_log_terminal_prefs(self, *_args) -> None:
        self._save_log_view_prefs()

    def _sync_log_view_widgets(self) -> None:
        st = self._log_view_state
        self._log_view_sync_guard = True
        try:
            verbose = getattr(self, "chk_verbose_log", None)
            if verbose is not None and verbose.isChecked() != st.verbose:
                verbose.setChecked(st.verbose)
            hex_chk = getattr(self, "chk_log_hex", None)
            if hex_chk is not None and hex_chk.isChecked() != st.hex:
                hex_chk.setChecked(st.hex)
            combo = getattr(self, "cmb_log_preset", None)
            if combo is not None:
                key = st.preset
                for i in range(combo.count()):
                    if str(combo.itemData(i) or "") == key:
                        if combo.currentIndex() != i:
                            combo.setCurrentIndex(i)
                        break
            for attr, val in (
                ("chk_log_rx", st.rx),
                ("chk_log_tx", st.tx),
                ("chk_log_warn", st.warn),
            ):
                chk = getattr(self, attr, None)
                if chk is not None and chk.isChecked() != val:
                    chk.setChecked(val)
        finally:
            self._log_view_sync_guard = False

    def _apply_log_view_state(
        self,
        state: LogViewState,
        *,
        persist: bool = True,
        sync_widgets: bool = False,
    ) -> None:
        self._log_view_state = state
        self._log_filter_rx = state.rx
        self._log_filter_tx = state.tx
        self._log_filter_warn = state.warn
        if sync_widgets:
            self._sync_log_view_widgets()
        if persist:
            self._save_log_view_prefs()

    def _on_log_preset_combo_changed(self, _idx: int = 0) -> None:
        if self._log_view_sync_guard:
            return
        combo = getattr(self, "cmb_log_preset", None)
        if combo is None:
            return
        key = str(combo.currentData() or "")
        if key == PRESET_CUSTOM:
            self._open_log_view_dialog()
            return
        self._apply_log_view_state(state_from_preset(key), sync_widgets=True)

    def _on_log_verbose_toggled(self, _on: bool = False) -> None:
        if self._log_view_sync_guard:
            return
        verbose = getattr(self, "chk_verbose_log", None)
        if verbose is None:
            return
        st = LogViewState(**{**self._log_view_state.to_dict(), "sentence_types": frozenset(self._log_view_state.sentence_types)})
        st.verbose = verbose.isChecked()
        st.preset = st.detect_preset()
        self._apply_log_view_state(st, sync_widgets=True)

    def _on_log_filter_chip_changed(self) -> None:
        if self._log_view_sync_guard:
            return
        st = LogViewState(**{**self._log_view_state.to_dict(), "sentence_types": frozenset(self._log_view_state.sentence_types)})
        st.rx = bool(getattr(self, "chk_log_rx", None) and self.chk_log_rx.isChecked())
        st.tx = bool(getattr(self, "chk_log_tx", None) and self.chk_log_tx.isChecked())
        st.warn = bool(getattr(self, "chk_log_warn", None) and self.chk_log_warn.isChecked())
        st.preset = st.detect_preset()
        self._apply_log_view_state(st, sync_widgets=True)

    def _open_log_view_dialog(self) -> None:
        updated = LogViewDialog.edit(
            self._log_view_state,
            self,
            nmea_mode_label=self._nmea_mode_label(),
        )
        if updated is None:
            self._sync_log_view_widgets()
            return
        self._apply_log_view_state(updated, sync_widgets=True)
        self._log_ui(f"[UI] Live log view: {updated.toolbar_summary()}")

    def _sync_nmea_mode_ui(self, *_args) -> None:
        strict_on = bool(
            getattr(self, "rb_nmea_strict", None) and self.rb_nmea_strict.isChecked()
        )
        box = getattr(self, "_nmea_strict_types_box", None)
        if box is not None:
            box.setEnabled(strict_on)
        for cb in getattr(self, "_nmea_type_checks", {}).values():
            cb.setEnabled(strict_on)
        self._sync_log_hex_toggle()

    def _sync_log_hex_toggle(self, *_args) -> None:
        chk = getattr(self, "chk_log_hex", None)
        raw_rb = getattr(self, "rb_nmea_raw", None)
        if chk is None or raw_rb is None:
            self._refresh_nmea_status_chip()
            return
        raw_on = raw_rb.isChecked()
        chk.setEnabled(raw_on)
        if not raw_on:
            chk.setChecked(False)
        self._refresh_nmea_status_chip()

    def _nmea_mode_label(self) -> str:
        if getattr(self, "rb_nmea_raw", None) and self.rb_nmea_raw.isChecked():
            return "raw"
        if getattr(self, "rb_nmea_strict", None) and self.rb_nmea_strict.isChecked():
            return "strict"
        return "passthrough"

    def _refresh_nmea_status_chip(self) -> None:
        chip = getattr(self, "status_nmea", None)
        if chip is None:
            return
        from ui.controls import elide_status_label

        from ui.nmea_display import nmea_mode_display_label

        mode = nmea_mode_display_label(self._nmea_mode_label())
        if self._is_bridge_running():
            elide_status_label(chip, f"NMEA: {mode} · running")
        elif self._starting:
            elide_status_label(chip, f"NMEA: {mode} · starting")
        else:
            elide_status_label(chip, f"NMEA: {mode}")
        self._refresh_gnss_status_chip()

    def _refresh_gnss_status_chip(self) -> None:
        chip = getattr(self, "status_gnss", None)
        if chip is None:
            return
        from survey_quality import (
            format_gnss_status_chip,
            format_gnss_status_tooltip,
            gnss_status_badge_quality,
            gnss_status_badge_stylesheet,
        )
        from ui.controls import elide_status_label

        running = self._is_bridge_running()
        raw_mode = self._nmea_mode_label() == "raw"
        nav = self.bridge.navigation_quality() if running and self.bridge and not raw_mode else None
        text = format_gnss_status_chip(nav, running=running, raw_mode=raw_mode)
        elide_status_label(chip, text)
        chip.setStyleSheet(
            gnss_status_badge_stylesheet(
                gnss_status_badge_quality(nav, running=running, raw_mode=raw_mode)
            )
        )
        chip.setToolTip(format_gnss_status_tooltip(nav, running=running, raw_mode=raw_mode))

    def _rebuild_recent_sessions_menu(self) -> None:
        menu = getattr(self, "_recent_sessions_menu", None)
        if menu is None:
            return
        menu.clear()
        sessions = load_recent_sessions()
        if not sessions:
            empty = QtGui.QAction("(no recent sessions)", self)
            empty.setEnabled(False)
            menu.addAction(empty)
        else:
            for entry in sessions:
                com = str(entry.get("com", "?"))
                baud = entry.get("baud", "")
                host = entry.get("udp_host", "")
                port = entry.get("udp_port", "")
                mode = str(entry.get("nmea_mode", "passthrough"))
                pin = "📌 " if bool(entry.get("pinned", False)) else ""
                label = f"{pin}{com} @ {baud} · {host}:{port} · {mode}"
                act = QtGui.QAction(label, self)

                def _apply(e: dict = entry) -> None:
                    self._apply_recent_session(e)

                act.triggered.connect(_apply)
                menu.addAction(act)
        menu.addSeparator()
        manage = QtGui.QAction("Manage recent sessions…", self)
        manage.triggered.connect(self._open_recent_sessions_manager)
        menu.addAction(manage)

    def _open_recent_sessions_manager(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Manage recent sessions")
        dlg.resize(640, 360)
        lay = QtWidgets.QVBoxLayout(dlg)
        hint = QtWidgets.QLabel(
            "Drag to reorder. Pinned sessions stay at the top of the Recent menu."
        )
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lst = QtWidgets.QListWidget()
        lst.setObjectName("presetList")
        lst.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        lst.setDragEnabled(True)
        lst.setAcceptDrops(True)
        lst.setDropIndicatorShown(True)
        lst.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        lst.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        sessions = load_recent_sessions()
        for entry in sessions:
            com = str(entry.get("com", "?"))
            baud = entry.get("baud", "")
            host = entry.get("udp_host", "")
            port = entry.get("udp_port", "")
            mode = str(entry.get("nmea_mode", "passthrough"))
            pin = "📌 " if bool(entry.get("pinned", False)) else ""
            item = QtWidgets.QListWidgetItem(f"{pin}{com} @ {baud} · {host}:{port} · {mode}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, dict(entry))
            lst.addItem(item)
        lay.addWidget(lst, 1)
        row = QtWidgets.QHBoxLayout()
        btn_pin = QtWidgets.QPushButton("Toggle pin")
        btn_apply = QtWidgets.QPushButton("Apply order")
        btn_close = QtWidgets.QPushButton("Close")
        row.addWidget(btn_pin)
        row.addStretch(1)
        row.addWidget(btn_apply)
        row.addWidget(btn_close)
        lay.addLayout(row)

        def _toggle_pin() -> None:
            item = lst.currentItem()
            if item is None:
                return
            entry = dict(item.data(QtCore.Qt.ItemDataRole.UserRole) or {})
            if not entry:
                return
            entry["pinned"] = not bool(entry.get("pinned", False))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, entry)
            com = str(entry.get("com", "?"))
            baud = entry.get("baud", "")
            host = entry.get("udp_host", "")
            port = entry.get("udp_port", "")
            mode = str(entry.get("nmea_mode", "passthrough"))
            pin = "📌 " if bool(entry.get("pinned", False)) else ""
            item.setText(f"{pin}{com} @ {baud} · {host}:{port} · {mode}")

        def _apply_order() -> None:
            keys: list[str] = []
            for i in range(lst.count()):
                item = lst.item(i)
                if item is None:
                    continue
                entry = dict(item.data(QtCore.Qt.ItemDataRole.UserRole) or {})
                if not entry:
                    continue
                key = recent_session_key(entry)
                if key:
                    keys.append(key)
                    set_recent_session_pinned(key, bool(entry.get("pinned", False)))
            reorder_recent_sessions(keys)
            self._rebuild_recent_sessions_menu()
            self._log_ui("[UI] Updated recent session order/pinning.")
            dlg.accept()

        btn_pin.clicked.connect(_toggle_pin)
        btn_apply.clicked.connect(_apply_order)
        btn_close.clicked.connect(dlg.reject)
        dlg.exec()

    def _apply_recent_session(self, entry: dict) -> None:
        if self.bridge is not None or self._starting:
            QtWidgets.QMessageBox.information(
                self,
                "Recent session",
                "Stop the bridge before loading a recent session.",
            )
            return
        com = str(entry.get("com", "")).strip()
        if not com:
            return
        from ui.connection_fields import coerce_baud

        self.baud_edit.setCurrentText(str(coerce_baud(int(entry.get("baud", 115200) or 115200))))
        idx = self.com_cb.findText(com)
        if idx >= 0:
            self.com_cb.setCurrentIndex(idx)
        else:
            self.com_cb.insertItem(0, com)
            self.com_cb.setCurrentIndex(0)
        self.udp_host.setText(str(entry.get("udp_host", "0.0.0.0")))
        self.udp_port.setText(str(entry.get("udp_port", "10110")))
        nmea = str(entry.get("nmea_mode", "passthrough"))
        if hasattr(self, "_apply_preset_nmea_mode"):
            payload: dict = {"nmea_mode": nmea}
            types = entry.get("nmea_types")
            if isinstance(types, list):
                payload["nmea_types"] = types
            self._apply_preset_nmea_mode(payload)
        else:
            if nmea == "raw" and getattr(self, "rb_nmea_raw", None):
                self.rb_nmea_raw.setChecked(True)
            elif nmea == "strict" and getattr(self, "rb_nmea_strict", None):
                self.rb_nmea_strict.setChecked(True)
            elif getattr(self, "rb_nmea_passthrough", None):
                self.rb_nmea_passthrough.setChecked(True)
        self._sync_log_hex_toggle()
        self._refresh_nmea_status_chip()
        baud_s = read_baud_widget(self.baud_edit)
        self._log_ui(f"[UI] Loaded recent session: {com} @ {baud_s} · NMEA {nmea}")

    def _record_recent_session(self) -> None:
        push_recent_session(
            {
                "com": self.com_cb.currentText().strip(),
                "baud": read_baud_widget(self.baud_edit),
                "net_mode": "udp_listen",
                "udp_host": self.udp_host.text().strip(),
                "udp_port": self.udp_port.text().strip(),
                "nmea_mode": self._nmea_mode_label(),
            }
        )
        self._rebuild_recent_sessions_menu()

    def _copy_stats_to_clipboard(self) -> None:
        mode = "udp_listen"
        if self.chk_advanced_net.isChecked():
            if self.rb_udp_remote.isChecked():
                mode = "udp_remote"
            elif self.rb_tcp_server.isChecked():
                mode = "tcp_server"
            elif self.rb_tcp_client.isChecked():
                mode = "tcp_client"
        com = self.com_cb.currentText().strip() or "?"
        baud = read_baud_widget(self.baud_edit) or "?"
        udp_host = self.udp_host.text().strip() or "0.0.0.0"
        udp_port = self.udp_port.text().strip() or "10110"
        if mode == "udp_remote":
            net_detail = f"{self.remote_host.text().strip() or '?'}:{self.remote_port.text().strip() or '?'}"
        elif mode == "tcp_server":
            net_detail = (
                f"{self.tcp_srv_host.text().strip() or '0.0.0.0'}:"
                f"{self.tcp_srv_port.text().strip() or '4001'}"
            )
        elif mode == "tcp_client":
            net_detail = (
                f"{self.tcp_cli_host.text().strip() or '127.0.0.1'}:"
                f"{self.tcp_cli_port.text().strip() or '4001'}"
            )
        else:
            net_detail = f"{udp_host}:{udp_port}"

        running = self.bridge is not None
        merged = self._merge_bridge_stats({}) if running else {}
        snap = stats_snapshot_from_merged(merged)
        nav = merged if running else {}

        status_serial = (self.status_serial.text() or "").strip()
        status_network = (self.status_network.text() or "").strip()
        status_nmea = (self.status_nmea.text() or "").strip()
        status_gnss = (getattr(self, "status_gnss", None).text() if hasattr(self, "status_gnss") else "") or ""
        stats_line = (getattr(self, "lbl_stats", None).text() if hasattr(self, "lbl_stats") else "") or ""
        preset = (self._active_preset_name or "").strip() or last_preset_name()
        state = "running" if running else ("starting" if self._starting else "stopped")

        text = (
            "Serial Link stats snapshot\n"
            f"state: {state}\n"
            f"preset: {preset}\n"
            f"serial: {com} @ {baud}\n"
            f"network_mode: {mode}\n"
            f"network_target: {net_detail}\n"
            f"nmea_mode: {self._nmea_mode_label()}\n"
            f"status_serial: {status_serial}\n"
            f"status_network: {status_network}\n"
            f"status_nmea: {status_nmea}\n"
            f"status_gnss: {status_gnss.strip()}\n"
            f"wire_hz_down: {snap['hz_down']:.2f}\n"
            f"wire_hz_up: {snap['hz_up']:.2f}\n"
            f"inject_hz: {snap['hz_gui']:.2f}\n"
            f"drops_down: {snap['drops_n2s']}\n"
            f"drops_up: {snap['drops_s2n']}\n"
            f"rejects_down: {snap['rej_n2s']}\n"
            f"rejects_up: {snap['rej_sn']}\n"
            f"session_down: {snap['lines_down']}\n"
            f"session_up: {snap['lines_up']}\n"
            f"gnss_summary: {nav.get('summary', '—')}\n"
            f"stats_line: {stats_line.strip()}"
        ).strip()
        QtWidgets.QApplication.clipboard().setText(text)
        self._log_ui(f"[UI] Copied stats: {text[:120]}{'…' if len(text) > 120 else ''}")

    def _apply_theme(self, theme_id: str, *, persist: bool = True) -> None:
        if theme_id not in THEME_IDS:
            theme_id = load_theme_choice()
        self._theme_id = theme_id
        if persist:
            save_theme_choice(theme_id)
        for tid, act in self._theme_actions.items():
            act.setChecked(tid == theme_id)
        ui_mode = getattr(self, "_ui_mode", "standard")
        self.setStyleSheet("")  # clear cached rules so theme swap is visible
        self.setStyleSheet(bridge_stylesheet(ui_mode, theme_id))
        apply_global_contrast_guard(QtWidgets.QApplication.instance())
        from ui.connect_row_style import apply_connect_row_style

        apply_connect_row_style(self)
        pop = getattr(self, "_stats_popout_window", None)
        if pop is not None:
            try:
                pop.set_theme(theme_id)
            except RuntimeError:
                self._stats_popout_window = None
        self._sync_random_theme_actions()

    def _sync_random_theme_actions(self) -> None:
        favorite = load_random_theme_favorite()
        act_favorite = self._theme_random_favorite_action
        if act_favorite is not None:
            act_favorite.setEnabled(bool(favorite))
            if not favorite and self._theme_id == THEME_RANDOM_FAVORITE:
                self._apply_theme(THEME_SLATE)
                return
        act_save = self._theme_save_favorite_action
        if act_save is not None:
            act_save.setEnabled(self._theme_id == THEME_RANDOM_CURRENT)
        btn_save = getattr(self, "btn_theme_save_favorite", None)
        if btn_save is not None:
            btn_save.setEnabled(self._theme_id == THEME_RANDOM_CURRENT)
        lock_now = load_random_seed_lock()
        act_lock = self._theme_random_lock_action
        if act_lock is not None and act_lock.isChecked() != lock_now:
            act_lock.blockSignals(True)
            act_lock.setChecked(lock_now)
            act_lock.blockSignals(False)
        chk_lock = getattr(self, "chk_theme_seed_lock", None)
        if chk_lock is not None and chk_lock.isChecked() != lock_now:
            chk_lock.blockSignals(True)
            chk_lock.setChecked(lock_now)
            chk_lock.blockSignals(False)
        combo = getattr(self, "cmb_theme_choice", None)
        if combo is not None:
            fav_idx = combo.findData(THEME_RANDOM_FAVORITE)
            if fav_idx >= 0:
                item = combo.model().item(fav_idx)
                if item is not None:
                    item.setEnabled(bool(favorite))
            idx = combo.findData(self._theme_id)
            if idx >= 0 and combo.currentIndex() != idx:
                self._theme_combo_syncing = True
                combo.setCurrentIndex(idx)
                self._theme_combo_syncing = False
        self._load_theme_zone_colors_for_active_theme()
        self._refresh_theme_zone_buttons()
        self._refresh_theme_preset_list()
        self._sync_theme_preset_buttons()

    def _load_theme_zone_colors_for_active_theme(self) -> None:
        from ui.theme_palette import zone_colors_for_theme

        self._theme_zone_colors = zone_colors_for_theme(self._theme_id)

    def _refresh_theme_zone_buttons(self) -> None:
        buttons = getattr(self, "_theme_zone_buttons", None)
        if not isinstance(buttons, dict):
            return
        for zone in THEME_ZONE_KEYS:
            btn = buttons.get(zone)
            if btn is None:
                continue
            color = self._theme_zone_colors.get(zone, DEFAULT_ZONE_COLORS.get(zone, "#333333"))
            txt_color = self._contrast_text_color(color)
            btn.setText(color.upper())
            btn.setStyleSheet(
                "QPushButton#themeStudioZoneSwatch {"
                f"background-color: {color};"
                f"color: {txt_color};"
                "border: 1px solid #202020;"
                "font-weight: 700;"
                "font-family: Consolas, 'Cascadia Mono', monospace;"
                "font-size: 9pt;"
                "padding: 2px 6px;"
                "border-radius: 4px;"
                "}"
            )

    @staticmethod
    def _contrast_text_color(bg_hex: str) -> str:
        c = str(bg_hex or "").strip().lstrip("#")
        if len(c) != 6:
            return "#f4f4f4"
        try:
            r = int(c[0:2], 16)
            g = int(c[2:4], 16)
            b = int(c[4:6], 16)
        except ValueError:
            return "#f4f4f4"
        luma = (0.299 * r) + (0.587 * g) + (0.114 * b)
        return "#111111" if luma >= 150 else "#f8f8f8"

    def _selected_theme_preset_name(self) -> str:
        lst = getattr(self, "theme_preset_list", None)
        if lst is None:
            return ""
        item = lst.currentItem()
        return item.text().strip() if item is not None else ""

    def _refresh_theme_preset_list(self) -> None:
        lst = getattr(self, "theme_preset_list", None)
        if lst is None:
            return
        current_name = self._selected_theme_preset_name()
        names = list_theme_preset_names()
        lst.blockSignals(True)
        lst.clear()
        for name in names:
            lst.addItem(name)
        if current_name:
            for i in range(lst.count()):
                if lst.item(i).text() == current_name:
                    lst.setCurrentRow(i)
                    break
        lst.blockSignals(False)

    def _sync_theme_preset_buttons(self) -> None:
        has_sel = bool(self._selected_theme_preset_name())
        btn_load = getattr(self, "btn_theme_preset_load", None)
        if btn_load is not None:
            btn_load.setEnabled(has_sel)
        btn_del = getattr(self, "btn_theme_preset_delete", None)
        if btn_del is not None:
            btn_del.setEnabled(has_sel)

    def _randomize_theme_now(self) -> None:
        lock_seed = load_random_seed_lock()
        if lock_seed:
            family_seed, variant = next_locked_random_variant()
            zones = generate_random_zone_colors(family_seed=family_seed, variant=variant)
        else:
            zones = generate_random_zone_colors()
        self._theme_zone_colors = dict(DEFAULT_ZONE_COLORS)
        self._theme_zone_colors.update(zones)
        color_map = build_zone_theme_map(self._theme_zone_colors)
        save_random_theme_current_zones(self._theme_zone_colors)
        save_random_theme_current(color_map)
        self._apply_theme(THEME_RANDOM_CURRENT)
        if lock_seed:
            self._log_ui(
                "[UI] Theme randomized (locked seed family). Use Tools -> Theme to save this palette as favorite."
            )
        else:
            self._log_ui(
                "[UI] Theme randomized. Use Tools -> Theme to save this palette as favorite."
            )

    def _standardize_theme_now(self) -> None:
        # Single click: standard slate. Double click: new cohesive "uniform but fresh" variant.
        if self._standardize_click_timer.isActive():
            self._standardize_click_timer.stop()
            self._apply_standardized_variant()
            return
        self._standardize_click_timer.start(280)

    def _apply_standardized_default(self) -> None:
        self._theme_zone_colors = dict(DEFAULT_ZONE_COLORS)
        self._apply_theme(THEME_SLATE)
        self._log_ui("[UI] Theme standardized to Field Slate.")

    def _apply_standardized_variant(self) -> None:
        zones = generate_standardized_zone_colors()
        self._theme_zone_colors = dict(DEFAULT_ZONE_COLORS)
        self._theme_zone_colors.update(zones)
        save_random_theme_current_zones(self._theme_zone_colors)
        save_random_theme_current(build_zone_theme_map(self._theme_zone_colors))
        self._apply_theme(THEME_RANDOM_CURRENT)
        self._log_ui("[UI] Standardized double-click: applied a new cohesive uniform variant.")

    def _save_current_random_theme_as_favorite(self) -> None:
        if not save_random_current_as_favorite():
            QtWidgets.QMessageBox.information(
                self,
                "Theme",
                "Randomize a theme first, then save it as a favorite.",
            )
            return
        self._sync_random_theme_actions()
        self._apply_theme(THEME_RANDOM_FAVORITE)
        self._log_ui("[UI] Saved current randomized theme as favorite.")

    def _on_theme_preset_item_clicked(self, _item: QtWidgets.QListWidgetItem) -> None:
        self._sync_theme_preset_buttons()

    def _on_theme_preset_rows_moved(self, *args: object) -> None:
        lst = getattr(self, "theme_preset_list", None)
        if lst is None:
            return
        names = [lst.item(i).text().strip() for i in range(lst.count()) if lst.item(i) is not None]
        if reorder_theme_presets(names):
            self._log_ui("[UI] Reordered theme presets.")
        self._sync_theme_preset_buttons()

    def _save_theme_preset_prompt(self) -> None:
        default_name = self._selected_theme_preset_name() or "My Theme"
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Save theme preset",
            "Preset name:",
            text=default_name,
        )
        if not ok:
            return
        clean = str(name).strip()
        if not clean:
            return
        zones = dict(DEFAULT_ZONE_COLORS)
        zones.update(self._theme_zone_colors)
        preset = {
            "theme": THEME_RANDOM_CURRENT,
            "seed_lock": load_random_seed_lock(),
            "zones": zones,
        }
        if not save_theme_preset(clean, preset):
            QtWidgets.QMessageBox.warning(self, "Theme preset", "Could not save theme preset.")
            return
        self._refresh_theme_preset_list()
        lst = getattr(self, "theme_preset_list", None)
        if lst is not None:
            for i in range(lst.count()):
                if lst.item(i).text() == clean:
                    lst.setCurrentRow(i)
                    break
        self._sync_theme_preset_buttons()
        self._log_ui(f"[UI] Saved theme preset: {clean}")

    def _load_selected_theme_preset(self) -> None:
        name = self._selected_theme_preset_name()
        if not name:
            return
        preset = load_theme_preset(name)
        if not preset:
            QtWidgets.QMessageBox.warning(self, "Theme preset", f"Preset not found: {name}")
            self._refresh_theme_preset_list()
            self._sync_theme_preset_buttons()
            return
        zones = dict(DEFAULT_ZONE_COLORS)
        zones.update(dict(preset.get("zones", {})))
        self._theme_zone_colors = zones
        save_random_theme_current_zones(zones)
        save_random_theme_current(build_zone_theme_map(zones))
        save_random_seed_lock(bool(preset.get("seed_lock", False)))
        self._apply_theme(THEME_RANDOM_CURRENT)
        self._log_ui(f"[UI] Loaded theme preset: {name}")

    def _delete_selected_theme_preset(self) -> None:
        name = self._selected_theme_preset_name()
        if not name:
            return
        if not delete_theme_preset(name):
            QtWidgets.QMessageBox.warning(self, "Theme preset", f"Could not delete preset: {name}")
            return
        self._refresh_theme_preset_list()
        self._sync_theme_preset_buttons()
        self._log_ui(f"[UI] Deleted theme preset: {name}")

    def _on_theme_choice_changed(self, _idx: int) -> None:
        if self._theme_combo_syncing:
            return
        combo = getattr(self, "cmb_theme_choice", None)
        if combo is None:
            return
        theme_id = str(combo.currentData() or THEME_SLATE)
        self._apply_theme(theme_id)

    def _apply_fixed_connect_row_style(self) -> None:
        """One house style for Connect (pill cards) — not an operator tuning knob."""
        from ui.connect_row_style import CONNECT_ROW_PILL, apply_connect_row_style

        apply_connect_row_style(self, CONNECT_ROW_PILL)

    def _request_stop_from_tray(self) -> None:
        if self._is_bridge_running():
            self.stop_bridge()

    def _quit_application(self) -> None:
        self._force_quit = True
        if self._is_bridge_running():
            self.stop_bridge()
        self._shutdown_background_services()
        from ui.tray_support import destroy_tray_icon

        destroy_tray_icon(self)
        self._close_auxiliary_windows()
        self.close()
        self._request_application_quit()

    def _request_application_quit(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()

    def _shutdown_background_services(self) -> None:
        """Stop web UI, discovery workers, and background threads (idempotent)."""
        self._stop_web_server()
        self._diag_stop()
        self._cancel_discovery_worker()
        timer = getattr(self, "_discovery_timer", None)
        if timer is not None:
            timer.stop()
            self._discovery_timer = None
        self._stop_auto_discovery_thread()

    def _hide_to_tray(self) -> None:
        from ui.tray_support import update_tray_tooltip

        self.hide()
        tray = getattr(self, "_tray_icon", None)
        if tray is None:
            return
        running = self._is_bridge_running()
        tip = (
            "Serial Link — bridge running (double-click to show)"
            if running
            else "Serial Link"
        )
        update_tray_tooltip(tray, tip)
        if running:
            tray.showMessage(
                "Serial Link",
                "Bridge still running. Double-click the tray icon to reopen.",
                QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def _pick_theme_zone_color(self, zone_id: str) -> None:
        current = self._theme_zone_colors.get(zone_id, DEFAULT_ZONE_COLORS.get(zone_id, "#222222"))
        start = QtGui.QColor(current)
        color = QtWidgets.QColorDialog.getColor(start, self, f"Pick {zone_id} color")
        if not color.isValid():
            return
        self._theme_zone_colors[zone_id] = color.name().lower()
        self._apply_current_zone_theme()

    def _on_theme_zone_rows_moved(self, *args: object) -> None:
        lst = getattr(self, "theme_zone_list", None)
        if lst is None:
            return
        order: list[str] = []
        for i in range(lst.count()):
            item = lst.item(i)
            if item is None:
                continue
            zone_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "").strip()
            if zone_id:
                order.append(zone_id)
        if save_theme_zone_order(order):
            self._log_ui("[UI] Reordered theme zones.")

    def _reset_theme_zone_color(self, zone_id: str) -> None:
        from ui.theme_palette import zone_colors_for_theme

        canonical = zone_colors_for_theme(self._theme_id)
        if zone_id not in canonical:
            return
        self._theme_zone_colors[zone_id] = canonical[zone_id]
        if self._theme_id in (THEME_RANDOM_CURRENT, THEME_RANDOM_FAVORITE):
            self._apply_current_zone_theme()
        else:
            self._refresh_theme_zone_buttons()

    def _apply_current_zone_theme(self) -> None:
        zone_map = dict(DEFAULT_ZONE_COLORS)
        zone_map.update(self._theme_zone_colors)
        self._theme_zone_colors = zone_map
        save_random_theme_current_zones(zone_map)
        save_random_theme_current(build_zone_theme_map(zone_map))
        self._apply_theme(THEME_RANDOM_CURRENT)
        self._log_ui("[UI] Applied zone colors to randomized theme.")

    def _export_theme_pack(self) -> None:
        zone_map = dict(DEFAULT_ZONE_COLORS)
        zone_map.update(self._theme_zone_colors)
        favorite_zones = load_random_theme_favorite_zones()
        pack = build_theme_pack(
            self._theme_id,
            zone_map,
            seed_lock=load_random_seed_lock(),
            favorite_zones=favorite_zones,
        )
        default_name = f"theme-pack-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export theme pack",
            str(Path.home() / default_name),
            "JSON files (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(pack, indent=2), encoding="utf-8")
            self._log_ui(f"[UI] Exported theme pack: {path}")
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Theme pack", f"Could not export theme pack:\n{exc}")

    def _import_theme_pack(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import theme pack",
            str(Path.home()),
            "JSON files (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            QtWidgets.QMessageBox.warning(self, "Theme pack", f"Could not read theme pack:\n{exc}")
            return
        pack = normalize_theme_pack(raw)
        if not pack:
            QtWidgets.QMessageBox.warning(
                self,
                "Theme pack",
                "Invalid theme pack format. Expected zones with valid #RRGGBB colors.",
            )
            return
        zones = dict(DEFAULT_ZONE_COLORS)
        zones.update(pack["zones"])
        self._theme_zone_colors = zones
        save_random_theme_current_zones(zones)
        save_random_theme_current(build_zone_theme_map(zones))
        if "favorite_zones" in pack:
            fav = dict(DEFAULT_ZONE_COLORS)
            fav.update(dict(pack["favorite_zones"]))
            save_random_theme_favorite_zones(fav)
        save_random_seed_lock(bool(pack.get("seed_lock", False)))
        imported_theme = str(pack.get("theme", THEME_RANDOM_CURRENT))
        if imported_theme in {THEME_RANDOM_CURRENT, THEME_RANDOM_FAVORITE}:
            self._apply_theme(imported_theme)
        else:
            self._apply_theme(THEME_RANDOM_CURRENT)
        self._refresh_theme_preset_list()
        self._sync_theme_preset_buttons()
        self._log_ui(f"[UI] Imported theme pack: {path}")

    def _set_random_seed_lock(self, enabled: bool) -> None:
        save_random_seed_lock(bool(enabled))
        state = "ON" if enabled else "OFF"
        self._log_ui(f"[UI] Random seed lock: {state}")
        self._sync_random_theme_actions()

    def _toggle_ui_layout(self) -> None:
        """Switch Standard ↔ Field (double-click Layout on the survey bar)."""
        cur = normalize_ui_id(getattr(self, "_ui_mode", "standard"))
        other = "field" if cur == "standard" else "standard"
        self._switch_ui_layout(other)

    def _switch_ui_layout(self, ui_id: str) -> None:
        if getattr(self, "_layout_switch_in_progress", False):
            return
        if self.bridge is not None or (self._worker is not None and self._worker.isRunning()):
            QtWidgets.QMessageBox.information(
                self,
                "Layout",
                "Stop the bridge before switching layout.",
            )
            return
        if ui_id == getattr(self, "_ui_mode", ""):
            return
        btn = getattr(self, "btn_ui_layout", None)
        try:
            self._layout_switch_in_progress = True
            if btn is not None:
                btn.setEnabled(False)
            self._close_auxiliary_windows()
            self._shutdown_background_services()
            from ui.tray_support import destroy_tray_icon

            destroy_tray_icon(self)
            save_ui_choice(ui_id)
            nw = create_window(ui_id)
            if hasattr(nw, "_apply_theme"):
                nw._apply_theme(self._theme_id, persist=False)
            nw.show()
            nw.raise_()
            nw.activateWindow()
            self.close()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "UI Switch",
                f"Could not switch UI layout: {exc}",
            )
            self._layout_switch_in_progress = False
            if btn is not None:
                btn.setEnabled(True)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            if self._splitter_sizes_backup and hasattr(self, "_splitter"):
                self._splitter.setSizes(self._splitter_sizes_backup)
                self._splitter_sizes_backup = None
        else:
            if hasattr(self, "_splitter"):
                self._splitter_sizes_backup = list(self._splitter.sizes())
                self._apply_fullscreen_splitter_bias()
            self.showFullScreen()

    def _apply_fullscreen_splitter_bias(self) -> None:
        """Give logs / tools a friendlier ratio on large displays."""
        sp = getattr(self, "_splitter", None)
        if sp is None:
            return
        o = sp.orientation()
        total = max(sum(sp.sizes()), 1)
        if o == QtCore.Qt.Orientation.Horizontal:
            # Standard: favor slightly more log width when very wide
            w = max(self.width(), total)
            tabs_w = int(w * 0.62)
            log_w = max(w - tabs_w, 200)
            sp.setSizes([tabs_w, log_w])
        else:
            h = max(self.height(), total)
            name = self.__class__.__name__.lower()
            if "logfirst" in name or "field" in name:
                top = int(h * 0.74)
                bot = max(h - top, 100)
                sp.setSizes([top, bot])
            else:
                # Minimal: more log height for survey noise
                top = int(h * 0.58)
                bot = max(h - top, 120)
                sp.setSizes([top, bot])

    def _open_stats_popout(self) -> None:
        pop = self._stats_popout_window
        if pop is not None:
            try:
                if pop.width() < 280 or pop.height() < 120:
                    pop.close()
                    pop = None
                    self._stats_popout_window = None
            except RuntimeError:
                self._stats_popout_window = None
                pop = None
        if pop is not None:
            pop.prepare_for_display()
            pop.show()
            pop.raise_()
            pop.activateWindow()
            self._refresh_stats_popout()
            return
        pop = SurveyStatsPopout(self)
        pop.destroyed.connect(self._on_stats_popout_destroyed)
        self._stats_popout_window = pop
        try:
            seed = self.log_view.toPlainText().splitlines()[-120:]
            pop.append_nmea_log_lines(seed)
        except Exception:
            pass
        pop.prepare_for_display()
        self._refresh_stats_popout()
        pop.show()
        pop.raise_()
        pop.activateWindow()

    def _on_stats_popout_destroyed(self, *_args: object) -> None:
        self._stats_popout_window = None

    def _refresh_stats_popout(self) -> None:
        pop = self._stats_popout_window
        if pop is None:
            return
        try:
            vis = pop.isVisible()
        except RuntimeError:
            self._stats_popout_window = None
            return
        if not vis:
            return
        if not self._qt_widget_alive(self):
            self._stats_popout_window = None
            return
        try:
            serial = self.status_serial.text()
            network = self.status_network.text()
        except RuntimeError:
            self._stats_popout_window = None
            return
        running = self.bridge is not None
        merged = self._merge_bridge_stats({}) if running else {}
        pop.apply_snapshot(merged, serial, network, running=running)

    def _open_hud(self) -> None:
        """Survey HUD (metrics) + Dashboard (bridge trust)."""
        self._open_stats_popout()
        self._open_dashboard()
        hud = self._stats_popout_window
        dash = self._dashboard_window
        if hud is not None and dash is not None:
            try:
                dash.place_beside(hud)
                dash.raise_()
            except RuntimeError:
                pass

    def _open_dashboard(self) -> None:
        pop = self._dashboard_window
        if pop is not None:
            try:
                if pop.width() < 200 or pop.height() < 120:
                    pop.close()
                    pop = None
                    self._dashboard_window = None
            except RuntimeError:
                self._dashboard_window = None
                pop = None
        if pop is not None:
            pop.show()
            pop.raise_()
            pop.activateWindow()
            self._refresh_dashboard()
            return
        pop = SurveyDashboard(self)
        pop.destroyed.connect(self._on_dashboard_destroyed)
        self._dashboard_window = pop
        anchor = self._stats_popout_window or self
        try:
            pop.place_beside(anchor)
        except RuntimeError:
            bg = self.frameGeometry()
            pop.move(bg.x() + 40, bg.y() + 80)
        self._refresh_dashboard()
        pop.show()
        pop.raise_()
        pop.activateWindow()

    def _on_dashboard_destroyed(self, *_args: object) -> None:
        self._dashboard_window = None

    def _refresh_dashboard(self) -> None:
        pop = self._dashboard_window
        if pop is None:
            return
        try:
            if not pop.isVisible():
                return
        except RuntimeError:
            self._dashboard_window = None
            return
        if not self._qt_widget_alive(self):
            self._dashboard_window = None
            return
        try:
            serial = self.status_serial.text()
            network = self.status_network.text()
        except RuntimeError:
            self._dashboard_window = None
            return
        running = self.bridge is not None
        merged = self._merge_bridge_stats({}) if running else {}
        pop.apply_snapshot(merged, serial, network, running=running)

    def _on_ui_ready(self) -> None:
        self._wire_connection_hub()
        # Note: facade window attachment and web server start are handled
        # in _init_web_and_facade(), called from _finalize_ui() after
        # _on_ui_ready(), so they always run regardless of subclass overrides.

    def _init_web_and_facade(self) -> None:
        """Always called from _finalize_ui after _on_ui_ready.
        Guarantees facade.attach_window and web server start even when
        subclasses override _on_ui_ready without calling super()."""
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.attach_window(self)
        self._ensure_discovery_for_web()
        self._restore_web_ui_prefs()
        self._update_web_listen_label()
        QtCore.QTimer.singleShot(0, self._ensure_web_server_running)
        from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

        schedule_refresh_connect_qr_overlay(self)

    def _web_enabled_effective(self) -> bool:
        chk = getattr(self, "chk_web_enabled", None)
        if chk is not None:
            return chk.isChecked()
        from ui.ui_prefs import load_web_ui_prefs

        return bool(load_web_ui_prefs().get("enabled"))

    def _web_server_running(self) -> bool:
        server = getattr(self, "_web_server", None)
        return server is not None and bool(getattr(server, "running", False))

    def _ensure_web_server_running(self) -> None:
        """Start Web API after the Qt event loop is idle; retry once if bind races."""
        if not self._web_enabled_effective():
            self._update_web_listen_label()
            return
        if self._web_server_running():
            self._update_web_listen_label()
            return
        self._maybe_start_web_server()
        self._update_web_listen_label()
        if self._web_enabled_effective() and not self._web_server_running():
            gen = getattr(self, "_web_start_retry_gen", 0) + 1
            self._web_start_retry_gen = gen

            def _retry() -> None:
                if gen != getattr(self, "_web_start_retry_gen", 0):
                    return
                if not self._web_enabled_effective() or self._web_server_running():
                    return
                from web_server import wait_port_free
                from ui.ui_prefs import load_web_ui_prefs

                prefs = load_web_ui_prefs()
                port = int(prefs.get("port", 8765))
                if wait_port_free(
                    port,
                    lan_bind=bool(prefs.get("lan_bind")),
                    host=str(prefs.get("host", "127.0.0.1")),
                    timeout=2.0,
                ):
                    self._maybe_start_web_server()
                    self._update_web_listen_label()

            QtCore.QTimer.singleShot(1200, _retry)

    def _web_token_from_ui(self) -> Optional[str]:
        edit = getattr(self, "edit_web_token", None)
        if edit is None:
            return None
        text = edit.text().strip()
        return text or None

    def _restore_web_ui_prefs(self) -> None:
        from ui.ui_prefs import load_web_ui_prefs

        prefs = load_web_ui_prefs()
        chk = getattr(self, "chk_web_enabled", None)
        if chk is not None:
            chk.blockSignals(True)
            chk.setChecked(bool(prefs.get("enabled")))
            chk.blockSignals(False)
        spin = getattr(self, "spin_web_port", None)
        if spin is not None:
            spin.blockSignals(True)
            spin.setValue(int(prefs.get("port", 8765)))
            spin.blockSignals(False)
        lan = getattr(self, "chk_web_lan", None)
        if lan is not None:
            lan.blockSignals(True)
            lan.setChecked(bool(prefs.get("lan_bind")))
            lan.blockSignals(False)
        edit = getattr(self, "edit_web_token", None)
        if edit is not None:
            edit.blockSignals(True)
            edit.setText(str(prefs.get("token") or ""))
            edit.blockSignals(False)
        phone_edit = getattr(self, "edit_web_phone_url", None)
        if phone_edit is not None:
            from web.phone_url import normalize_phone_base_url

            phone_edit.blockSignals(True)
            phone_edit.setText(
                normalize_phone_base_url(str(prefs.get("phone_base_url") or ""))
            )
            phone_edit.blockSignals(False)
        chk_qr = getattr(self, "chk_web_show_qr", None)
        if chk_qr is not None and str(prefs.get("token") or "").strip():
            chk_qr.blockSignals(True)
            chk_qr.setChecked(True)
            chk_qr.blockSignals(False)
        self._refresh_phone_tab_qr()

    def _tools_nav_is_phone(self) -> bool:
        nav = getattr(self, "_tools_nav", None)
        if nav is None:
            return False
        item = nav.currentItem()
        if item is None:
            return False
        return item.text().strip().lower() == "phone"

    def _on_tools_nav_row_changed(self, row: int) -> None:
        stack = getattr(self, "_tools_stack", None)
        nav = getattr(self, "_tools_nav", None)
        if stack is None or row < 0:
            return
        stack_idx = row
        if nav is not None:
            item = nav.item(row)
            if item is not None:
                data = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if isinstance(data, int) and 0 <= data < stack.count():
                    stack_idx = data
        if 0 <= stack_idx < stack.count():
            stack.setCurrentIndex(stack_idx)
        if self._tools_nav_is_phone():
            self._refresh_phone_tab_qr()
            floater = getattr(self, "_connect_qr_overlay", None)
            if floater is not None and floater.isVisible():
                floater.hide()
        else:
            from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

            schedule_refresh_connect_qr_overlay(self, delay_ms=0)

    def _sync_web_port_unlock_chrome(self, unlocked: bool | None = None) -> None:
        chk = getattr(self, "chk_web_port_unlock", None)
        if unlocked is None:
            unlocked = chk is not None and chk.isChecked()
        if chk is not None:
            chk.blockSignals(True)
            chk.setChecked(unlocked)
            chk.setText("🔓" if unlocked else "🔒")
            chk.blockSignals(False)
        lbl = getattr(self, "lbl_web_port_status", None)
        if lbl is not None:
            lbl.setText("Editable · 10s" if unlocked else "Locked")
            lbl.setProperty("statusKind", "open" if unlocked else "locked")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            lbl.update()

    def _sync_web_port_spin_locked(self) -> None:
        spin = getattr(self, "spin_web_port", None)
        if spin is None:
            return
        chk = getattr(self, "chk_web_port_unlock", None)
        unlocked = chk is not None and chk.isChecked()
        spin.setEnabled(True)
        spin.setReadOnly(not unlocked)
        spin.setProperty("portLocked", not unlocked)
        spin.style().unpolish(spin)
        spin.style().polish(spin)
        spin.update()
        self._sync_web_port_unlock_chrome(unlocked)

    def _on_web_port_unlock_toggled(self, checked: bool) -> None:
        self._sync_web_port_spin_locked()
        timer: QtCore.QTimer | None = getattr(self, "_web_port_unlock_timer", None)
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._on_web_port_unlock_expired)
            self._web_port_unlock_timer = timer
        timer.stop()
        if checked:
            timer.start(10_000)

    def _on_web_port_unlock_expired(self) -> None:
        chk = getattr(self, "chk_web_port_unlock", None)
        if chk is None or not chk.isChecked():
            return
        chk.blockSignals(True)
        chk.setChecked(False)
        chk.blockSignals(False)
        self._sync_web_port_spin_locked()

    def _web_dashboard_local_url(self, port: int | None = None) -> str:
        p = int(port if port is not None else self._web_port_from_ui())
        return f"http://127.0.0.1:{p}/"

    def _sync_phone_url_port(self, port: int) -> None:
        """Keep Phone dashboard URL port aligned when the spin box changes."""
        edit = getattr(self, "edit_web_phone_url", None)
        if edit is None:
            return
        raw = edit.text().strip()
        if not raw:
            return
        from urllib.parse import urlparse, urlunparse

        text = raw if "://" in raw else f"http://{raw}"
        parsed = urlparse(text)
        host = parsed.hostname
        if not host:
            return
        port_i = max(1024, min(65535, int(port)))
        userinfo = ""
        if parsed.username:
            userinfo = parsed.username
            if parsed.password:
                userinfo += f":{parsed.password}"
            userinfo += "@"
        host_part = host
        if ":" in host and not host.startswith("["):
            host_part = f"[{host}]"
        netloc = f"{userinfo}{host_part}:{port_i}"
        new_url = urlunparse(parsed._replace(netloc=netloc))
        if new_url.rstrip("/") != text.rstrip("/"):
            edit.blockSignals(True)
            edit.setText(new_url)
            edit.blockSignals(False)

    def _web_listen_label_text(self, headline: str, detail: str = "") -> str:
        headline = headline.strip()
        detail = detail.strip()
        if detail:
            return f"{headline}\n{detail}"
        return headline

    def _update_web_listen_label(self, *, pending_restart: bool = False) -> None:
        lbl = getattr(self, "lbl_web_listen", None)
        if lbl is None:
            return
        enabled = getattr(self, "chk_web_enabled", None)
        if enabled is None or not enabled.isChecked():
            lbl.setText(
                self._web_listen_label_text(
                    "Web API off",
                    "Enable above, then open the dashboard URL on this PC.",
                )
            )
            lbl.updateGeometry()
            return
        port_ui = self._web_port_from_ui()
        local = self._web_dashboard_local_url(port_ui)
        if pending_restart:
            lbl.setText(
                self._web_listen_label_text(
                    f"Applying port {port_ui}",
                    f"Restarting API at {local}",
                )
            )
            lbl.updateGeometry()
            return
        server = getattr(self, "_web_server", None)
        if server is not None and server.running:
            live_port = int(getattr(server, "_port", port_ui) or port_ui)
            live = self._web_dashboard_local_url(live_port)
            if live_port != port_ui:
                lbl.setText(
                    self._web_listen_label_text(
                        f"Live on port {live_port} (spin shows {port_ui})",
                        live,
                    )
                )
            else:
                lbl.setText(
                    self._web_listen_label_text("This PC dashboard", live)
                )
            lbl.updateGeometry()
            return
        lbl.setText(self._web_listen_label_text("Starting Web API", local))
        lbl.updateGeometry()

    def _on_web_port_spin_changed(self, _value: int) -> None:
        chk = getattr(self, "chk_web_port_unlock", None)
        if chk is not None and not chk.isChecked():
            return
        self._persist_web_ui_prefs()
        self._sync_phone_url_port(self._web_port_from_ui())
        self._schedule_web_server_restart(300)

    def _schedule_web_server_restart(self, delay_ms: int = 400) -> None:
        """One debounced restart — avoids overlapping stop/start on the same port."""
        self._update_web_listen_label(pending_restart=True)
        for attr in ("_web_port_restart_timer", "_web_prefs_debounce_timer"):
            t: QtCore.QTimer | None = getattr(self, attr, None)
            if t is not None:
                t.stop()
        gen = getattr(self, "_web_restart_gen", 0) + 1
        self._web_restart_gen = gen
        self._web_restart_scheduled_gen = gen
        timer: QtCore.QTimer | None = getattr(self, "_web_restart_timer", None)
        if timer is None:
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(self._on_web_restart_timer_fired)
            self._web_restart_timer = t
            timer = t
        timer.stop()
        timer.start(max(50, int(delay_ms)))

    def _on_web_restart_timer_fired(self) -> None:
        if getattr(self, "_web_restart_scheduled_gen", -1) != getattr(self, "_web_restart_gen", -1):
            return
        self._apply_web_server_restart()

    def _apply_web_server_restart(self) -> None:
        if getattr(self, "_web_restart_busy", False):
            self._web_restart_pending = True
            return
        self._web_restart_busy = True
        try:
            self._persist_web_ui_prefs()
            self._stop_web_server()
            from ui.ui_prefs import load_web_ui_prefs
            from web_server import wait_port_free

            prefs = load_web_ui_prefs()
            if not prefs.get("enabled"):
                self._update_web_listen_label()
                return
            port = int(prefs.get("port", 8765))
            lan = bool(prefs.get("lan_bind"))
            host = str(prefs.get("host", "127.0.0.1"))
            if not wait_port_free(port, lan_bind=lan, host=host, timeout=3.0):
                self._report_web_bind_failure(port)
                return
            self._maybe_start_web_server()
            self._update_web_listen_label()
        finally:
            self._web_restart_busy = False
            if getattr(self, "_web_restart_pending", False):
                self._web_restart_pending = False
                self._schedule_web_server_restart(200)

    def _report_web_bind_failure(self, port: int) -> None:
        msg = (
            f"Port {port} is already in use — close another bridge window, "
            "stop any test using that port, or choose a different port."
        )
        lbl = getattr(self, "lbl_web_listen", None)
        if lbl is not None:
            lbl.setText(f"Web API failed: {msg}")
        self._log_ui(f"[Web] {msg}")
        self._web_server = None

    def _report_web_start_failure(self, detail: str) -> None:
        msg = f"Web API failed to start: {detail}"
        lbl = getattr(self, "lbl_web_listen", None)
        if lbl is not None:
            lbl.setText(msg)
        self._log_ui(f"[Web] {msg}")
        self._web_server = None

    def _web_port_from_ui(self) -> int:
        spin = getattr(self, "spin_web_port", None)
        if spin is not None:
            return int(spin.value())
        from ui.ui_prefs import load_web_ui_prefs

        return int(load_web_ui_prefs().get("port", 8765))

    def _web_lan_bind_from_ui(self) -> bool:
        lan = getattr(self, "chk_web_lan", None)
        if lan is not None:
            return bool(lan.isChecked())
        from ui.ui_prefs import load_web_ui_prefs

        return bool(load_web_ui_prefs().get("lan_bind"))

    def _phone_dashboard_base_url(self) -> str:
        from web.phone_url import normalize_phone_base_url

        edit = getattr(self, "edit_web_phone_url", None)
        if edit is not None:
            text = normalize_phone_base_url(edit.text())
            if text:
                return text
        from ui.ui_prefs import load_web_ui_prefs

        return normalize_phone_base_url(
            str(load_web_ui_prefs().get("phone_base_url") or "")
        )

    def _normalize_phone_url_field(self) -> None:
        from web.phone_url import normalize_phone_base_url

        edit = getattr(self, "edit_web_phone_url", None)
        if edit is None:
            return
        clean = normalize_phone_base_url(edit.text())
        if clean != edit.text().strip():
            edit.blockSignals(True)
            edit.setText(clean)
            edit.blockSignals(False)

    def _phone_url_ready_for_remote(self) -> tuple[bool, str]:
        """Return (ok, message) for QR / copy when LAN is enabled."""
        from web.phone_url import is_loopback_base

        if not self._web_lan_bind_from_ui():
            return True, ""
        base = self._phone_dashboard_base_url()
        if base and not is_loopback_base(base):
            return True, ""
        return (
            False,
            "Set Phone dashboard URL to this PC's Tailscale IP (100.x.x.x:port) — "
            "127.0.0.1 only works on this computer, not on your phone.",
        )

    def _maybe_autofill_phone_url(self) -> bool:
        """Try Tailscale/LAN detect when remote access is on. Returns True if filled."""
        from web.phone_url import is_loopback_base, suggest_phone_base_urls

        if not self._web_lan_bind_from_ui():
            return False
        base = self._phone_dashboard_base_url()
        if base and not is_loopback_base(base):
            return False
        port = self._web_port_from_ui()
        urls = suggest_phone_base_urls(port)
        if not urls:
            return False
        edit = getattr(self, "edit_web_phone_url", None)
        if edit is None:
            return False
        edit.setText(urls[0])
        self._persist_web_ui_prefs()
        self._log_ui(f"[Web] Phone dashboard URL set to {urls[0]} (detected for tailnet/LAN).")
        return True

    def _build_phone_setup_url(self) -> Optional[str]:
        token = self._web_token_from_ui()
        if not token:
            return None
        ok, msg = self._phone_url_ready_for_remote()
        if not ok:
            self._log_ui(f"[Web] {msg}")
            return None
        base = self._phone_dashboard_base_url()
        if not base:
            from web.phone_url import is_loopback_base, suggest_phone_base_urls

            port = self._web_port_from_ui()
            if self._web_lan_bind_from_ui():
                urls = suggest_phone_base_urls(port)
                if urls:
                    base = urls[0]
                else:
                    self._log_ui(
                        "[Web] Enter Phone dashboard URL (Tailscale IP from tailscale ip -4)."
                    )
                    return None
            else:
                base = f"http://127.0.0.1:{port}"
            if is_loopback_base(base) and self._web_lan_bind_from_ui():
                return None
        from web.token_setup import build_setup_url

        return build_setup_url(base, token)

    def _persist_web_ui_prefs(self) -> None:
        from ui.ui_prefs import load_web_ui_prefs, save_web_ui_prefs

        prev = load_web_ui_prefs()
        enabled = getattr(self, "chk_web_enabled", None)
        port = getattr(self, "spin_web_port", None)
        lan = getattr(self, "chk_web_lan", None)
        token_ui = self._web_token_from_ui()
        phone_edit = getattr(self, "edit_web_phone_url", None)
        phone_url = None
        if phone_edit is not None:
            from web.phone_url import normalize_phone_base_url

            phone_url = normalize_phone_base_url(phone_edit.text()) or None
        save_web_ui_prefs(
            enabled=enabled.isChecked() if enabled is not None else prev["enabled"],
            host=str(prev.get("host", "127.0.0.1")),
            port=port.value() if port is not None else int(prev.get("port", 8765)),
            lan_bind=lan.isChecked() if lan is not None else bool(prev.get("lan_bind")),
            token=token_ui if getattr(self, "edit_web_token", None) is not None else prev.get("token"),
            phone_base_url=phone_url if phone_edit is not None else prev.get("phone_base_url"),
        )

    def _on_web_lan_toggled(self, checked: bool) -> None:
        if checked and not self._web_token_from_ui():
            from ui.ui_prefs import generate_web_api_token

            edit = getattr(self, "edit_web_token", None)
            if edit is not None:
                edit.setText(generate_web_api_token())
                self._log_ui("[Web] Generated remote control token for LAN/Tailscale access.")
        if checked:
            self._maybe_autofill_phone_url()
        self._on_web_ui_prefs_changed()
        self._refresh_web_token_qr()

    def _on_web_generate_token(self) -> None:
        from ui.ui_prefs import generate_web_api_token

        edit = getattr(self, "edit_web_token", None)
        if edit is not None:
            edit.setText(generate_web_api_token())
        self._log_ui("[Web] New API token generated.")
        self._on_web_ui_prefs_changed()
        self._refresh_web_token_qr()

    def _on_web_show_qr_toggled(self, checked: bool) -> None:
        self._refresh_web_token_qr()

    def _on_web_token_text_changed(self, *_args: object) -> None:
        chk = getattr(self, "chk_web_show_qr", None)
        if chk is not None and chk.isChecked():
            self._refresh_web_token_qr()

    def _refresh_web_token_qr(self) -> None:
        self._refresh_phone_tab_qr()
        from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

        schedule_refresh_connect_qr_overlay(self)

    def _refresh_phone_tab_qr(self) -> None:
        lbl = getattr(self, "lbl_web_token_qr", None)
        chk = getattr(self, "chk_web_show_qr", None)
        if lbl is None or chk is None:
            return
        if not chk.isChecked():
            lbl.setVisible(False)
            lbl.clear()
            return
        token = self._web_token_from_ui()
        if not token:
            lbl.setPixmap(QtGui.QPixmap())
            lbl.setText("Generate\na token\nfirst")
            lbl.setVisible(True)
            return
        from ui.token_qr import make_token_qr_pixmap

        setup_url = self._build_phone_setup_url()
        pix = make_token_qr_pixmap(token, size=180, setup_url=setup_url)
        if pix is None or pix.isNull():
            lbl.setPixmap(QtGui.QPixmap())
            lbl.setText(
                "QR unavailable.\n"
                "Run: pip install\n"
                "qrcode"
            )
            lbl.setWordWrap(True)
            lbl.setVisible(True)
            return
        lbl.setWordWrap(False)
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl.setText("")
        lbl.setPixmap(pix)
        lbl.setScaledContents(False)
        lbl.setVisible(True)

    def _refresh_connect_qr_overlay(self) -> None:
        from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

        schedule_refresh_connect_qr_overlay(self)

    def _on_web_copy_token(self) -> None:
        token = self._web_token_from_ui()
        if not token:
            self._log_ui("[Web] No token to copy — click Generate token first.")
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.clipboard().setText(token)
        self._log_ui("[Web] API token copied to clipboard.")

    def _on_web_detect_phone_url(self) -> None:
        if self._maybe_autofill_phone_url():
            self._refresh_web_token_qr()
            return
        self._log_ui(
            "[Web] Could not detect a Tailscale/LAN IP — run `tailscale ip -4` and paste "
            "http://THAT-IP:8765 into Phone dashboard URL."
        )

    def _on_web_open_dashboard(self) -> None:
        if not self._web_lan_bind_from_ui():
            base = self._web_dashboard_local_url()
        else:
            base = self._phone_dashboard_base_url()
            if not base:
                if self._maybe_autofill_phone_url():
                    base = self._phone_dashboard_base_url()
        if not base:
            self._log_ui(
                "[Web] Set Phone dashboard URL (Tailscale/LAN IP) or click Detect Tailscale IP."
            )
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(base.rstrip("/") + "/"))
        self._log_ui(f"[Web] Opened dashboard in browser ({base}).")

    def _on_web_copy_phone_setup(self) -> None:
        ok, msg = self._phone_url_ready_for_remote()
        if not ok:
            if self._maybe_autofill_phone_url():
                ok, msg = self._phone_url_ready_for_remote()
        if not ok:
            self._log_ui(f"[Web] {msg}")
            return
        url = self._build_phone_setup_url()
        if not url:
            self._log_ui("[Web] Generate a token first, then set Phone dashboard URL (Tailscale IP).")
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.clipboard().setText(url)
        base = self._phone_dashboard_base_url()
        self._log_ui(
            f"[Web] Phone setup link copied ({base}) — open once on the phone or Paste setup link there."
        )

    def _apply_token_from_text(self, text: str) -> bool:
        from web.token_setup import parse_token_from_text

        parsed = parse_token_from_text(text)
        if not parsed:
            return False
        edit = getattr(self, "edit_web_token", None)
        if edit is not None:
            edit.setText(parsed)
        self._persist_web_ui_prefs()
        self._refresh_web_token_qr()
        return True

    def _on_web_paste_setup(self) -> None:
        app = QtWidgets.QApplication.instance()
        clip = app.clipboard().text() if app is not None else ""
        if self._apply_token_from_text(clip):
            self._log_ui("[Web] Token imported from setup link — same token is now on this PC.")
            return
        self._log_ui(
            "[Web] Clipboard has no setup link. On the phone: Tools → Copy setup link or Share link, "
            "then copy that text and click Paste setup link again."
        )

    def _on_web_ui_prefs_changed(self, *_args: object) -> None:
        self._schedule_web_server_restart(400)

    def _restart_web_control_plane(self) -> None:
        self._apply_web_server_restart()
        from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

        schedule_refresh_connect_qr_overlay(self)

    def _maybe_start_web_server(self) -> None:
        from ui.ui_prefs import load_web_ui_prefs

        if not self._web_enabled_effective():
            return
        prefs = load_web_ui_prefs()
        port = int(prefs.get("port", 8765))
        try:
            from version import __version__
            from web_api import create_app, resolve_static_dir
            from web_server import WebServerThread, port_is_free

            static = resolve_static_dir()
            if static is None:
                self._log_ui(
                    "[Web] Dashboard files (web/static) are missing from this portable build. "
                    "Download the latest serial-link zip from GitHub releases."
                )
                return
            try:
                import fastapi  # noqa: F401
                import uvicorn  # noqa: F401
            except ImportError as exc:
                self._log_ui(
                    f"[Web] Server libraries missing ({exc}). "
                    "Reinstall from the latest GitHub release zip."
                )
                return

            if not port_is_free(
                port,
                lan_bind=bool(prefs.get("lan_bind")),
                host=str(prefs.get("host", "127.0.0.1")),
            ):
                self._report_web_bind_failure(port)
                return

            token = prefs.get("token") if prefs.get("lan_bind") else None
            app = create_app(
                self._app_facade,
                version=__version__,
                lan_token=token,
            )
            server = WebServerThread()
            server.start(
                app,
                host=str(prefs.get("host", "127.0.0.1")),
                port=port,
                lan_bind=bool(prefs.get("lan_bind")),
            )
            self._web_server = server
            if prefs.get("lan_bind"):
                self._log_ui(
                    f"Web API listening on LAN port {port} — open http://127.0.0.1:{port}/ "
                    "on this PC (paste API token in the dashboard if prompted). "
                    "Phone: scan QR or use your PC LAN IP."
                )
            else:
                self._log_ui(
                    f"Web API: http://127.0.0.1:{port}/ "
                    "(Tools → Phone — no token required on this PC)"
                )
        except Exception as exc:
            self._web_server = None
            self._log_ui(f"[Web] Start failed: {exc}")
            msg = str(exc).lower()
            if "already in use" in msg or "10048" in msg or "address already in use" in msg:
                self._report_web_bind_failure(port)
            else:
                self._report_web_start_failure(str(exc))

    def _stop_web_server(self) -> None:
        server = getattr(self, "_web_server", None)
        if server is not None:
            server.stop(join_timeout=2.0)
            self._web_server = None
        self._update_web_listen_label()

    def _ensure_discovery_for_web(self) -> None:
        """Passive discovery poll + web façade feed (Field/minimal have no Connection Hub)."""
        if not hasattr(self, "_discovery_stable_counts"):
            self._discovery_stable_counts = {}
        if not hasattr(self, "_bridge_stats_cache"):
            self._bridge_stats_cache = {}
        if not hasattr(self, "_discovery_worker"):
            self._discovery_worker = None
        self._start_discovery_poll()

    def _wire_connection_hub(self) -> None:
        hub = getattr(self, "connection_hub", None)
        if hub is None:
            return
        self._ensure_discovery_for_web()
        self._hub_selected_device_id: Optional[str] = None
        self._manual_override_dirty = False
        hub.selection_changed.connect(self._on_hub_selection)
        hub.manual_override_toggled.connect(self._on_manual_override_toggled)
        hub.refresh_requested.connect(self._on_hub_refresh_discovery)
        hub.unlock_requested.connect(self._on_hub_unlock_ports)
        for w in (
            self.com_cb,
            self.baud_edit,
            self.udp_host,
            self.udp_port,
            getattr(self, "remote_host", None),
            getattr(self, "remote_port", None),
        ):
            if w is None:
                continue
            if hasattr(w, "textChanged"):
                w.textChanged.connect(self._mark_manual_override_dirty)
            elif hasattr(w, "currentTextChanged"):
                w.currentTextChanged.connect(self._mark_manual_override_dirty)
        for rb in (
            getattr(self, "rb_udp_listen", None),
            getattr(self, "rb_udp_remote", None),
            getattr(self, "rb_tcp_server", None),
            getattr(self, "rb_tcp_client", None),
        ):
            if rb is not None:
                rb.toggled.connect(self._mark_manual_override_dirty)
    def _mark_manual_override_dirty(self, *_args: object) -> None:
        self._manual_override_dirty = True

    def _on_manual_override_toggled(self, enabled: bool) -> None:
        if not enabled:
            self._manual_override_dirty = False

    def _start_discovery_poll(self) -> None:
        if getattr(self, "_discovery_timer", None) is not None:
            return
        timer = QtCore.QTimer(self)
        timer.setInterval(2000)
        timer.timeout.connect(self._poll_discovery_snapshot)
        timer.start()
        self._discovery_timer = timer
        QtCore.QTimer.singleShot(0, self._poll_discovery_snapshot)

    def _discovery_scan_params(self) -> dict:
        presets: list[dict] = []
        try:
            from bench_config import list_preset_names, load_preset

            for name in list_preset_names()[:12]:
                try:
                    presets.append({"name": name, **load_preset(name)})
                except KeyError:
                    pass
        except Exception:
            presets = []
        try:
            udp_port = int(self.udp_port.text().strip())
        except ValueError:
            udp_port = 10110
        skip_bind: Optional[int] = None
        if self._is_bridge_running() and self.bridge and getattr(self.bridge, "udp_listen", None):
            from bridge_core import NetMode

            if self.bridge.mode == NetMode.UDP_LISTEN:
                skip_bind = int(self.bridge.udp_listen[1])
        return {
            "stable_counts": getattr(self, "_discovery_stable_counts", None),
            "presets": presets,
            "active_preset": getattr(self, "_active_preset_name", None),
            "bridge_stats": getattr(self, "_bridge_stats_cache", None),
            "udp_host": self.udp_host.text().strip() or "0.0.0.0",
            "udp_port": udp_port,
            "selected_port": self.com_cb.currentText().strip() or None,
            "skip_bind_port": skip_bind,
        }

    def _cancel_discovery_worker(self) -> None:
        worker = getattr(self, "_discovery_worker", None)
        if worker is not None:
            worker.cancel()
            if worker.isRunning():
                worker.wait(3000)
            self._discovery_worker = None

    def _on_hub_refresh_discovery(self) -> None:
        hub = getattr(self, "connection_hub", None)
        self._cancel_discovery_worker()
        from ui.discovery_worker import DiscoveryScanWorker

        if hub is not None:
            hub.set_scan_busy(True)
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.set_discovery_scan_busy(True)
        worker = DiscoveryScanWorker(self._discovery_scan_params(), full_network_scan=True, parent=self)

        def _clear_busy() -> None:
            if hub is not None:
                hub.set_scan_busy(False)
            if facade is not None:
                facade.set_discovery_scan_busy(False)

        worker.snapshot_ready.connect(self._on_discovery_worker_snapshot)
        worker.scan_failed.connect(self._on_discovery_worker_failed)
        worker.finished.connect(_clear_busy)
        self._discovery_worker = worker
        worker.start()

    def _on_discovery_worker_snapshot(self, snap: object, counts: object) -> None:
        if snap is not None:
            self._discovery_stable_counts = counts if isinstance(counts, dict) else {}
            hub = getattr(self, "connection_hub", None)
            if hub is not None:
                hub.set_snapshot(snap)
            self._update_field_connect_summary()
            facade = getattr(self, "_app_facade", None)
            if facade is not None:
                facade.update_discovery_snapshot(snap)
        self._cancel_discovery_worker()

    def _on_discovery_worker_failed(self, message: str) -> None:
        self._log_ui(f"[Discovery] Scan failed: {message}")
        hub = getattr(self, "connection_hub", None)
        if hub is not None:
            hub.set_scan_busy(False)
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.set_discovery_scan_busy(False)
        self._poll_discovery_snapshot()
        self._cancel_discovery_worker()

    def _on_hub_unlock_ports(self) -> None:
        from port_release import hint_udp_listen_busy, smart_release_com

        from ui.connection_fields import parse_baud

        hub = getattr(self, "connection_hub", None)
        com = self.com_cb.currentText().strip()
        baud = parse_baud(read_baud_widget(self.baud_edit)) or 115200
        running = self._is_bridge_running()
        bridge_com = self.bridge.com if self.bridge else None
        state = smart_release_com(
            com,
            baud,
            bridge_running=running,
            bridge_com=bridge_com,
        )
        if not state.safe_to_release:
            QtWidgets.QMessageBox.information(self, "Unlock ports", state.reason)
            return
        if state.last_attempt_ok:
            self._log_ui(f"[Unlock] {state.reason}")
        else:
            self._log_ui(f"[Unlock] {state.reason}")
            QtWidgets.QMessageBox.warning(self, "Unlock ports", state.reason)
        try:
            udp_port = int(self.udp_port.text().strip())
        except ValueError:
            udp_port = 10110
        hint = hint_udp_listen_busy(self.udp_host.text().strip() or "0.0.0.0", udp_port)
        if hint:
            self._log_ui(f"[Unlock] {hint}")
        self.refresh_ports()
        if hub is not None:
            self._on_hub_refresh_discovery()

    def _poll_discovery_snapshot(self) -> None:
        from discovery_service import build_snapshot

        if getattr(self, "_discovery_worker", None) is not None and self._discovery_worker.isRunning():
            return
        params = self._discovery_scan_params()
        snap, self._discovery_stable_counts = build_snapshot(
            stable_counts=params.get("stable_counts"),
            presets=params.get("presets"),
            active_preset=params.get("active_preset"),
            bridge_stats=params.get("bridge_stats"),
            udp_host=params.get("udp_host"),
            udp_port=params.get("udp_port"),
            selected_port=params.get("selected_port"),
            network_scan_results=None,
        )
        hub = getattr(self, "connection_hub", None)
        if hub is not None:
            hub.set_snapshot(snap)
        self._update_field_connect_summary()
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.update_discovery_snapshot(snap)
        if self._is_bridge_running():
            self._apply_hub_quality()

    def _update_field_connect_summary(self) -> None:
        lbl = getattr(self, "_field_connect_summary", None)
        if lbl is None:
            return
        hub = getattr(self, "connection_hub", None)
        sel = hub.selected_device_id() if hub else None
        sel_note = f" · hub: {sel}" if sel else ""
        preset = (self._active_preset_name or "").strip()
        preset_note = f" · preset: {preset}" if preset else ""
        nmea = self._nmea_mode_label() if hasattr(self, "_nmea_mode_label") else ""
        nmea_note = f" · NMEA {nmea}" if nmea else ""
        lbl.setText(
            f"{self.com_cb.currentText().strip()} @ {read_baud_widget(self.baud_edit)} · "
            f"UDP {self.udp_host.text().strip()}:{self.udp_port.text().strip()}"
            f"{preset_note}{nmea_note}{sel_note}"
        )

    def _on_hub_selection(self, device_id: str) -> None:
        from ui.ui_prefs import load_last_known_good

        self._hub_selected_device_id = device_id
        hub = getattr(self, "connection_hub", None)
        lkg = load_last_known_good(device_id)
        if lkg:
            self._apply_last_known_good(lkg)
            return
        if hub is None:
            return
        if device_id.startswith("serial:"):
            port = hub.find_serial_port(device_id)
            if port:
                idx = self.com_cb.findText(port)
                if idx >= 0:
                    self.com_cb.setCurrentIndex(idx)
                else:
                    self.com_cb.insertItem(0, port)
                    self.com_cb.setCurrentIndex(0)
        elif device_id.startswith("net:"):
            card = hub.find_network_card(device_id)
            if card:
                self.rb_udp_listen.setChecked(True)
                self.udp_host.setText(card.host)
                self.udp_port.setText(str(card.port))
        self._mode_toggle()
        self._refresh_intent_hint()

    def _apply_last_known_good(self, lkg: dict) -> None:
        com = str(lkg.get("com", "")).strip()
        if com:
            idx = self.com_cb.findText(com)
            if idx >= 0:
                self.com_cb.setCurrentIndex(idx)
            else:
                self.com_cb.insertItem(0, com)
                self.com_cb.setCurrentIndex(0)
        if lkg.get("baud") is not None:
            from ui.connection_fields import coerce_baud

            self.baud_edit.setCurrentText(str(coerce_baud(int(lkg["baud"]))))
        if lkg.get("udp_host"):
            self.udp_host.setText(str(lkg["udp_host"]))
        if lkg.get("udp_port") is not None:
            self.udp_port.setText(str(lkg["udp_port"]))
        fanout = getattr(self, "chk_udp_fanout", None)
        if fanout is not None and "udp_fanout" in lkg:
            fanout.setChecked(bool(lkg["udp_fanout"]))
        sink_chk = getattr(self, "chk_tcp_sink_enable", None)
        if sink_chk is not None and "tcp_sink_enabled" in lkg:
            sink_chk.setChecked(bool(lkg["tcp_sink_enabled"]))
        if getattr(self, "tcp_sink_port", None) is not None and lkg.get("tcp_sink_port"):
            self.tcp_sink_port.setText(str(lkg["tcp_sink_port"]))
        mode = str(lkg.get("net_mode", "")).strip()
        if mode == "udp_remote":
            self.rb_udp_remote.setChecked(True)
        elif mode == "tcp_server":
            self.rb_tcp_server.setChecked(True)
        elif mode == "tcp_client":
            self.rb_tcp_client.setChecked(True)
        else:
            self.rb_udp_listen.setChecked(True)
        self._mode_toggle()
        self._refresh_intent_hint()

    def _should_apply_hub_for_start(self) -> bool:
        hub = getattr(self, "connection_hub", None)
        if hub is None or not hub.selected_device_id():
            return False
        if getattr(self, "_manual_override_dirty", False):
            return False
        return True

    def _apply_hub_selection_for_start(self) -> None:
        hub = getattr(self, "connection_hub", None)
        if hub is None:
            return
        device_id = hub.selected_device_id()
        if device_id:
            self._on_hub_selection(device_id)

    def _collect_last_known_good_config(self) -> dict:
        cfg: dict = {
            "com": self.com_cb.currentText().strip(),
            "baud": read_baud_widget(self.baud_edit),
            "udp_host": self.udp_host.text().strip(),
            "udp_port": self.udp_port.text().strip(),
            "udp_fanout": getattr(self, "chk_udp_fanout", None) is None
            or self.chk_udp_fanout.isChecked(),
            "net_mode": "udp_listen",
        }
        if self.rb_udp_remote.isChecked():
            cfg["net_mode"] = "udp_remote"
        elif self.rb_tcp_server.isChecked():
            cfg["net_mode"] = "tcp_server"
        elif self.rb_tcp_client.isChecked():
            cfg["net_mode"] = "tcp_client"
        sink_chk = getattr(self, "chk_tcp_sink_enable", None)
        if sink_chk is not None:
            cfg["tcp_sink_enabled"] = sink_chk.isChecked()
            cfg["tcp_sink_port"] = getattr(self, "tcp_sink_port", None) and self.tcp_sink_port.text().strip()
        return cfg

    def _save_hub_last_known_good(self) -> None:
        from ui.ui_prefs import save_last_known_good

        hub = getattr(self, "connection_hub", None)
        device_id = hub.selected_device_id() if hub else getattr(self, "_hub_selected_device_id", None)
        if not device_id:
            return
        save_last_known_good(device_id, self._collect_last_known_good_config())

    def _apply_hub_quality(self) -> None:
        from ui.hub_quality import quality_from_bridge_stats

        hub = getattr(self, "connection_hub", None)
        if hub is None:
            return
        stats = getattr(self, "_bridge_stats_cache", None) or {}
        if self.bridge:
            stats = {**stats, "running": True}
        else:
            stats = {**stats, "running": False}
        device_id = hub.selected_device_id()
        hub.set_quality(device_id, quality_from_bridge_stats(stats))

    def _apply_startup_connection_fields(self) -> None:
        """Single launch-restore path: last preset → Connect fields (FR-201).

        Called once from ``_finalize_ui`` after widgets exist. All layouts
        (``bridge_gui.create_window`` → standard/field/minimal/logfirst) use
        this path; do not duplicate preset load in ``_on_ui_ready`` subclasses.
        """
        try:
            self._apply_preset_by_name(last_preset_name(), log=False)
        except KeyError:
            d = load_bench_defaults()
            self._apply_preset_data(d, name=None, log=False)

    def _preflight_com(self, com: str, baud: int) -> Optional[str]:
        """Quick COM probe on GUI thread before async start."""
        try:
            ser = _open_serial_port_timed(com, baud, SERIAL_OPEN_TIMEOUT_S)
            ser.close()
            return None
        except Exception as exc:
            return _friendly_serial_error(exc, com)

    def _main_tab_index_by_label(self, label: str) -> int:
        tabs = getattr(self, "_main_tabs", None)
        if tabs is None:
            return -1
        target = label.strip().lower()
        for i in range(tabs.count()):
            if tabs.tabText(i).strip().lower() == target:
                return i
        return -1

    def _focus_log_tab(self) -> None:
        idx = self._main_tab_index_by_label("Log")
        tabs = getattr(self, "_main_tabs", None)
        if tabs is not None and idx >= 0:
            tabs.setCurrentIndex(idx)

    def _focus_connect_tab(self) -> None:
        idx = self._main_tab_index_by_label("Connect")
        tabs = getattr(self, "_main_tabs", None)
        if tabs is not None and idx >= 0:
            tabs.setCurrentIndex(idx)

    def _auto_switch_to_log_tab(self) -> None:
        if self.bridge is None or not getattr(self.bridge, "running", False):
            return
        if getattr(self, "_ui_mode", "") != "standard":
            return
        self._focus_log_tab()
        self._log_ui("[UI] Switched to Log tab (bridge running >20 s).")

    def _append_connect_mini_log(self, lines: list[str]) -> None:
        mini = getattr(self, "connect_mini_log", None)
        if mini is None or not lines:
            return
        try:
            mini.appendPlainText("\n".join(lines))
            sb = mini.verticalScrollBar()
            sb.setValue(sb.maximum())
        except RuntimeError:
            self.connect_mini_log = None

    def _append_connect_terminal(self, text: str) -> None:
        out = getattr(self, "connect_terminal_out", None)
        if out is None or not text:
            return
        out.appendPlainText(text.rstrip("\n"))
        sb = out.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _connect_terminal_send_line(self) -> None:
        inp = getattr(self, "connect_terminal_input", None)
        if inp is None:
            return
        line = inp.text().strip()
        if not line:
            return
        self._send_raw_manual("serial", line)
        inp.clear()

    def _toggle_log_panel(self, visible: bool) -> None:
        if getattr(self, "_ui_mode", "") == "standard":
            if visible:
                self._focus_log_tab()
            return
        sp = getattr(self, "_splitter", None)
        if sp is None or sp.count() < 2:
            return
        if sp.orientation() == QtCore.Qt.Orientation.Horizontal:
            sp.widget(1).setVisible(visible)
            if visible:
                sp.setSizes([520, 360])
            else:
                sp.setSizes([900, 0])
        else:
            sp.widget(0).setVisible(visible)

    def _polish_widget(self, w: QtWidgets.QWidget) -> None:
        style = w.style()
        style.unpolish(w)
        style.polish(w)

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_banner.setProperty("state", state)
        self._polish_widget(self.status_banner)
        lbl = self.status_banner_text
        if getattr(lbl, "objectName", lambda: "")() == "statusBannerText":
            from ui.connect_panels import format_connect_status_banner_html

            lbl.setTextFormat(QtCore.Qt.TextFormat.RichText)
            lbl.setText(format_connect_status_banner_html(title, detail))
        else:
            lbl.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            lbl.setText(title if not detail else f"{title} | {detail}")

    def _set_active_preset(self, name: Optional[str]) -> None:
        self._active_preset_name = name.strip() if name else None
        if self._active_preset_name:
            set_last_preset(self._active_preset_name)
        self._refresh_preset_list_selection()
        self._rebuild_presets_quick_menu()
        self._refresh_intent_hint()

    def _intent_hint_text(self) -> str:
        if self.chk_advanced_net.isChecked() and self.rb_tcp_server.isChecked():
            host = self.tcp_srv_host.text().strip() or "0.0.0.0"
            port = self.tcp_srv_port.text().strip() or "4001"
            return (
                f"TCP server on {host}:{port}. After Start, connect a TCP client to send NMEA "
                f"(bench: python bench_tcp_test.py --port {port}). COM→TCP needs a connected client."
            )
        if self.chk_advanced_net.isChecked() and self.rb_tcp_client.isChecked():
            host = self.tcp_cli_host.text().strip() or "127.0.0.1"
            port = self.tcp_cli_port.text().strip() or "4001"
            return (
                f"TCP client → {host}:{port}. Bridge connects outbound; device must already be listening."
            )
        if self.rb_udp_remote.isChecked():
            return (
                "Wrong mode: UDP remote talks to a fixed peer. "
                "For INS/simulator use UDP listen (Presets → Advanced, or disable Advanced)."
            )
        if not self.rb_udp_listen.isChecked() and self.chk_advanced_net.isChecked():
            return "Pick a network mode under Advanced (UDP listen is typical for NMEA)."
        if self._active_preset_name:
            try:
                d = load_preset(self._active_preset_name)
            except KeyError:
                d = {}
            com = self.com_cb.currentText() or "COM?"
            pc = d.get("pc_ip")
            if pc:
                return (
                    f"Preset «{self._active_preset_name}»: INS → UDP {pc}:{self.udp_port.text()} "
                    f"on this PC → {com}. Keep this COM dedicated to the bridge while running."
                )
            return (
                f"Preset «{self._active_preset_name}»: bridge owns {com}. "
                f"Send UDP to 127.0.0.1:{self.udp_port.text()} (bench). "
                f"Watch paired com0com, not {com}."
            )
        return "Load a preset (Presets tab or survey bar), or set COM + UDP listen, then Start."

    def _apply_intent_hint_display(self) -> None:
        hint = getattr(self, "intent_hint", None)
        if hint is None:
            return
        try:
            from shiboken6 import isValid

            if not isValid(hint):
                return
        except ImportError:
            pass
        full = self._intent_hint_text()
        compact = getattr(self, "_compact_intent_hint", False)
        hint.setProperty("intentCompact", compact)
        hint.style().unpolish(hint)
        hint.style().polish(hint)
        if compact:
            from ui.controls import apply_compact_intent_hint

            apply_compact_intent_hint(hint, full)
        else:
            hint.setWordWrap(True)
            hint.setToolTip("")
            hint.setText(full)
            hint.setVisible(bool(full))

    def _refresh_intent_hint(self) -> None:
        self._apply_intent_hint_display()

    def _validate_before_start(self) -> Optional[str]:
        if self._worker and self._worker.isRunning():
            return "Bridge is still stopping. Wait a moment, then try again."
        if self._starting:
            return "Start already in progress."
        if not self.com_cb.currentText().strip():
            return "Select a COM port (Refresh ports if the list is empty)."
        from ui.connection_fields import validate_baud, validate_udp_port

        baud_err = validate_baud(read_baud_widget(self.baud_edit))
        if baud_err:
            return baud_err

        if self.chk_advanced_net.isChecked():
            try:
                if self.rb_udp_listen.isChecked():
                    _parse_port(self.udp_port.text(), "UDP port")
                elif self.rb_udp_remote.isChecked():
                    if not self.remote_host.text().strip():
                        return "UDP remote host is required."
                    _parse_port(self.remote_port.text(), "UDP remote port")
                elif self.rb_tcp_server.isChecked():
                    _parse_port(self.tcp_srv_port.text(), "TCP server port")
                else:
                    if not self.tcp_cli_host.text().strip():
                        return "TCP client host is required."
                    _parse_port(self.tcp_cli_port.text(), "TCP client port")
            except ValueError as e:
                return str(e)
            return None

        if self.rb_udp_remote.isChecked():
            return (
                "UDP remote is wrong for typical INS/bench. Load a preset with UDP listen, "
                "or enable Advanced network and select UDP listen."
            )
        if not self.rb_udp_listen.isChecked():
            return "For standard NMEA UDP, select UDP listen (or use Advanced network)."
        try:
            _parse_port(self.udp_port.text(), "UDP port")
        except ValueError as e:
            return str(e)
        return None

    def _compose_com_preflight_error(self, com: str, detail: str) -> str:
        """Operator-facing COM exclusivity guidance before async start."""
        port = com.strip() or "selected COM"
        base = (detail or f"Cannot open {port}.").strip()
        return (
            f"{base}\n\n"
            "Quick fixes:\n"
            f"1) Close any app using {port} (PuTTY, terminal, another bridge).\n"
            "2) Click Connect → Unlock, then Refresh.\n"
            "3) Replug the USB/serial adapter if the port disappeared."
        )

    def _restore_ntrip_prefs(self) -> None:
        prefs = load_ntrip_prefs()
        caster = getattr(self, "ntrip_caster", None)
        if caster is None:
            return
        self._ntrip_prefs_sync = True
        try:
            self.chk_ntrip_enable.setChecked(bool(prefs.get("enabled", False)))
            self.ntrip_caster.setText(str(prefs.get("caster", "")))
            self.ntrip_mount.setText(str(prefs.get("mountpoint", "")))
            self.ntrip_user.setText(str(prefs.get("username", "")))
            self.ntrip_pass.setText(str(prefs.get("password", "")))
        finally:
            self._ntrip_prefs_sync = False
        if not getattr(self, "_ntrip_prefs_wired", False):
            self._ntrip_prefs_wired = True
            self.chk_ntrip_enable.toggled.connect(self._persist_ntrip_prefs)
            for w in (self.ntrip_caster, self.ntrip_mount, self.ntrip_user, self.ntrip_pass):
                w.textChanged.connect(self._persist_ntrip_prefs)

    def _persist_ntrip_prefs(self, *_args: object) -> None:
        if getattr(self, "_ntrip_prefs_sync", False):
            return
        if not hasattr(self, "chk_ntrip_enable"):
            return
        save_ntrip_prefs(
            {
                "enabled": self.chk_ntrip_enable.isChecked(),
                "caster": self.ntrip_caster.text(),
                "mountpoint": self.ntrip_mount.text(),
                "username": self.ntrip_user.text(),
                "password": self.ntrip_pass.text(),
            }
        )

    def _ntrip_config_from_ui(self) -> NtripConfig:
        host, port = parse_caster_host(getattr(self, "ntrip_caster", None).text() if hasattr(self, "ntrip_caster") else "")
        return NtripConfig(
            host=host,
            port=port,
            mountpoint=self.ntrip_mount.text().strip() if hasattr(self, "ntrip_mount") else "",
            username=self.ntrip_user.text().strip() if hasattr(self, "ntrip_user") else "",
            password=self.ntrip_pass.text() if hasattr(self, "ntrip_pass") else "",
        )

    def _start_ntrip_if_enabled(self) -> None:
        if not hasattr(self, "chk_ntrip_enable") or not self.chk_ntrip_enable.isChecked():
            return
        cfg = self._ntrip_config_from_ui()
        if not cfg.enabled:
            self._log_ui("NTRIP: enable checkbox set but caster/mount missing.")
            return
        worker = self._worker
        bridge = self.bridge
        loop = worker._loop if worker else None
        if not loop or not bridge:
            return
        self._persist_ntrip_prefs()

        async def _runner() -> None:
            await run_ntrip_forwarder(
                cfg,
                bridge.inject_correction_bytes,
                self._log_ui,
                lambda: self._is_bridge_running(),
            )

        self._ntrip_future = asyncio.run_coroutine_threadsafe(_runner(), loop)

    def _stop_ntrip(self) -> None:
        fut = self._ntrip_future
        self._ntrip_future = None
        if fut is not None and not fut.done():
            fut.cancel()

    def _restore_file_log_prefs_ui(self) -> None:
        combo_mb = getattr(self, "cmb_file_log_mb", None)
        combo_bk = getattr(self, "cmb_file_log_backups", None)
        if combo_mb is None or combo_bk is None:
            return
        prefs = load_file_log_prefs()
        for i in range(combo_mb.count()):
            if int(combo_mb.itemData(i)) == prefs["max_mb"]:
                combo_mb.setCurrentIndex(i)
                break
        for i in range(combo_bk.count()):
            if int(combo_bk.itemData(i)) == prefs["backups"]:
                combo_bk.setCurrentIndex(i)
                break
        self._refresh_file_log_retention_hint()

    def _refresh_file_log_retention_hint(self) -> None:
        lbl = getattr(self, "lbl_file_log_retention", None)
        combo_mb = getattr(self, "cmb_file_log_mb", None)
        combo_bk = getattr(self, "cmb_file_log_backups", None)
        if lbl is None or combo_mb is None or combo_bk is None:
            return
        max_mb = int(combo_mb.currentData())
        backups = int(combo_bk.currentData())
        lbl.setText(file_log_retention_hint(max_mb, backups))
        save_file_log_prefs(max_mb, backups)

    def _apply_com_preset(self, com: str, baud: int, udp_host: str, udp_port: int) -> None:
        idx = self.com_cb.findText(com)
        if idx >= 0:
            self.com_cb.setCurrentIndex(idx)
        else:
            self.com_cb.addItem(com)
            self.com_cb.setCurrentText(com)
        from ui.connection_fields import coerce_baud

        self.baud_edit.setCurrentText(str(coerce_baud(baud)))
        self.rb_udp_listen.setChecked(True)
        self.udp_host.setText(udp_host)
        self.udp_port.setText(str(udp_port))
        self.rb_nmea_passthrough.setChecked(True)
        self.chk_verbose_log.setChecked(True)
        self._mode_toggle()
        self._refresh_intent_hint()

    def _connection_preset_from_ui(self) -> dict[str, str | int]:
        com = self.com_cb.currentText().strip()
        try:
            baud = int(read_baud_widget(self.baud_edit))
        except ValueError:
            baud = 0
        udp_host = self.udp_host.text().strip() or "0.0.0.0"
        try:
            udp_port = _parse_port(self.udp_port.text(), "UDP port")
        except ValueError:
            udp_port = 0
        fanout_chk = getattr(self, "chk_udp_fanout", None)
        udp_fanout = fanout_chk is None or fanout_chk.isChecked()
        out: dict[str, str | int | bool] = {
            "com": com,
            "baud": baud,
            "udp_host": udp_host,
            "udp_port": udp_port,
            "udp_fanout": udp_fanout,
        }
        sink_chk = getattr(self, "chk_tcp_sink_enable", None)
        if sink_chk is not None:
            out["tcp_sink_enabled"] = sink_chk.isChecked()
            if getattr(self, "tcp_sink_port", None) is not None:
                try:
                    out["tcp_sink_port"] = int(self.tcp_sink_port.text().strip())
                except ValueError:
                    out["tcp_sink_port"] = 10111
        return out

    def _validate_connection_preset_fields(self, fields: dict[str, str | int]) -> Optional[str]:
        if not fields["com"]:
            return "Select a COM port before saving."
        if int(fields["baud"]) <= 0:
            return "Enter a valid baud rate before saving."
        if int(fields["udp_port"]) <= 0:
            return "Enter a valid UDP listen port before saving."
        return None

    def _preset_survey_fields_from_ui(self) -> dict[str, str]:
        if not hasattr(self, "preset_pc_ip"):
            return {}
        return {
            "pc_ip": self.preset_pc_ip.text().strip(),
            "subnet_mask": self.preset_subnet.text().strip(),
            "ins_ip": self.preset_ins_ip.text().strip(),
            "notes": self.preset_notes.toPlainText().strip(),
        }

    def _preset_full_from_ui(self) -> dict[str, str | int]:
        merged = dict(self._connection_preset_from_ui())
        merged.update(self._preset_survey_fields_from_ui())
        merged.update(self._preset_nmea_from_ui())
        return merged

    def _preset_nmea_from_ui(self) -> dict[str, str | list[str]]:
        out: dict[str, str | list[str]] = {"nmea_mode": self._nmea_mode_label()}
        checks = getattr(self, "_nmea_type_checks", None)
        if self._nmea_mode_label() == "strict" and checks:
            types = [st for st, cb in checks.items() if cb.isChecked()]
            if types:
                out["nmea_types"] = types
        return out

    def _apply_preset_nmea_mode(self, data: dict) -> None:
        nmea = str(data.get("nmea_mode", "passthrough")).strip().lower()
        if nmea == "raw" and getattr(self, "rb_nmea_raw", None):
            self.rb_nmea_raw.setChecked(True)
        elif nmea == "strict" and getattr(self, "rb_nmea_strict", None):
            self.rb_nmea_strict.setChecked(True)
        elif getattr(self, "rb_nmea_passthrough", None):
            self.rb_nmea_passthrough.setChecked(True)
        types = data.get("nmea_types")
        checks = getattr(self, "_nmea_type_checks", None)
        if nmea == "strict" and isinstance(types, list) and checks:
            enabled = {str(t).strip().upper() for t in types}
            for st, cb in checks.items():
                cb.setChecked(st in enabled)
        self._sync_nmea_mode_ui()
        self._refresh_nmea_status_chip()

    def _apply_preset_survey_fields(self, data: dict) -> None:
        if not hasattr(self, "preset_pc_ip"):
            return
        self.preset_pc_ip.setText(str(data.get("pc_ip", "")))
        self.preset_subnet.setText(str(data.get("subnet_mask", "255.255.255.0")))
        self.preset_ins_ip.setText(str(data.get("ins_ip", "")))
        self.preset_notes.setPlainText(str(data.get("notes", "")))

    @staticmethod
    def _preset_name_from_item(item: Optional[QtWidgets.QListWidgetItem]) -> str:
        if item is None:
            return ""
        stored = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if stored is not None:
            return str(stored).strip()
        return item.text().strip()

    def _refresh_preset_list(self) -> None:
        lst = getattr(self, "preset_list", None)
        if lst is None:
            self._rebuild_presets_quick_menu()
            return
        names = list_preset_names()
        lst.blockSignals(True)
        lst.clear()
        for name in names:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)
            lst.addItem(item)
        lst.blockSignals(False)
        self._refresh_preset_list_selection()
        self._rebuild_presets_quick_menu()

    def _select_preset_row(self, name: str, *, scroll: bool = False) -> bool:
        """Highlight a preset in the list without loading it."""
        lst = getattr(self, "preset_list", None)
        if lst is None or not name:
            return False
        target = name.strip()
        self._preset_list_syncing = True
        lst.blockSignals(True)
        try:
            for i in range(lst.count()):
                item = lst.item(i)
                if item is not None and self._preset_name_from_item(item) == target:
                    lst.setCurrentRow(i)
                    lst.setCurrentItem(item)
                    if scroll:
                        lst.scrollToItem(
                            item,
                            QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter,
                        )
                    return True
            return False
        finally:
            lst.blockSignals(False)
            self._preset_list_syncing = False

    def _refresh_preset_list_selection(self) -> None:
        lst = getattr(self, "preset_list", None)
        if lst is None:
            return
        target = self._active_preset_name or last_preset_name()
        if not self._select_preset_row(target):
            if lst.count() > 0:
                self._select_preset_row(self._preset_name_from_item(lst.item(0)) or "")
        self._sync_preset_action_buttons()

    def _presets_menu_checked_name(self) -> Optional[str]:
        if (self.bridge is not None or self._starting) and self._presets_menu_pending:
            return self._presets_menu_pending
        return self._active_preset_name

    def _on_presets_quick_menu_triggered(self, action: QtGui.QAction) -> None:
        """Run after the popup closes — avoids lost clicks on Windows."""
        if action is None:
            return
        role = action.data()
        if role == "open_presets_tab":
            QtCore.QTimer.singleShot(0, self._open_presets_tab)
            return
        name = str(role).strip() if role is not None else action.text().strip()
        if not name or name.startswith("("):
            return
        QtCore.QTimer.singleShot(0, lambda n=name: self._quick_connect_preset(n))

    def _quick_connect_preset(self, name: str) -> None:
        """Survey bar Presets menu: apply full preset and start (no diagnostics checklist)."""
        clean = (name or "").strip()
        if not clean:
            return
        try:
            data = load_preset(clean)
        except KeyError:
            QtWidgets.QMessageBox.warning(
                self,
                "Presets",
                f"Preset «{clean}» was not found in path_presets.json.",
            )
            return
        running = self.bridge is not None or self._starting
        if running:
            self.stop_bridge()
        self._select_preset_row(clean, scroll=True)
        self._presets_menu_pending = None
        self._apply_preset_data(data, name=clean, log=True)
        self._rebuild_presets_quick_menu()
        if running:
            QtCore.QTimer.singleShot(300, self.start_bridge)
        else:
            self.start_bridge()

    def _rebuild_presets_quick_menu(self) -> None:
        menu = getattr(self, "_presets_quick_menu", None)
        group = getattr(self, "_presets_menu_group", None)
        if menu is None or group is None:
            return
        for old in list(group.actions()):
            group.removeAction(old)
        menu.clear()
        names = list_preset_names()
        checked = self._presets_menu_checked_name()
        if not names:
            act = QtGui.QAction("(no presets)", self)
            act.setEnabled(False)
            menu.addAction(act)
            return
        for name in names:
            act = QtGui.QAction(name, self)
            act.setCheckable(True)
            act.setData(name)
            group.addAction(act)
            act.setChecked(name == checked)
            menu.addAction(act)
        menu.addSeparator()
        act_edit = QtGui.QAction("Open Presets tab…", self)
        act_edit.setData("open_presets_tab")
        menu.addAction(act_edit)

    def _open_phone_tab(self) -> None:
        tools_nav = getattr(self, "_tools_nav", None)
        main_tabs = getattr(self, "_main_tabs", None)
        if tools_nav is not None and main_tabs is not None:
            for i in range(main_tabs.count()):
                if main_tabs.tabText(i).lower() == "tools":
                    main_tabs.setCurrentIndex(i)
                    break
            for row in range(tools_nav.count()):
                item = tools_nav.item(row)
                if item is not None and item.text().strip().lower() == "phone":
                    tools_nav.setCurrentRow(row)
                    return
            return
        tabs = getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        drawer = getattr(self, "_drawer_btn", None)
        if drawer is not None and not drawer.isChecked():
            drawer.setChecked(True)
        for i in range(tabs.count()):
            if tabs.tabText(i).strip().lower() == "phone":
                tabs.setCurrentIndex(i)
                return

    def _open_presets_tab(self) -> None:
        # Standard layout: Presets lives inside the Tools tab as a sidebar nav item.
        tools_nav = getattr(self, "_tools_nav", None)
        main_tabs = getattr(self, "_main_tabs", None)
        if tools_nav is not None and main_tabs is not None:
            for i in range(main_tabs.count()):
                if main_tabs.tabText(i).lower() == "tools":
                    main_tabs.setCurrentIndex(i)
                    break
            for row in range(tools_nav.count()):
                item = tools_nav.item(row)
                if item is not None and item.text().lower().startswith("preset"):
                    tools_nav.setCurrentRow(row)
                    return
            return
        # Field / drawer layouts: Presets is a top-level drawer tab.
        tabs = getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        drawer = getattr(self, "_drawer_btn", None)
        if drawer is not None and not drawer.isChecked():
            drawer.setChecked(True)
        for i in range(tabs.count()):
            if tabs.tabText(i).lower().startswith("preset"):
                tabs.setCurrentIndex(i)
                return

    def _selected_preset_name(self) -> Optional[str]:
        lst = getattr(self, "preset_list", None)
        if lst is None:
            return self._active_preset_name
        item = lst.currentItem()
        name = self._preset_name_from_item(item)
        return name or None

    def _apply_preset_data(self, data: dict, *, name: Optional[str], log: bool = True) -> None:
        com = str(data["com"])
        baud = int(data["baud"])
        udp_host = str(data["udp_host"])
        udp_port = int(data["udp_port"])
        self._apply_com_preset(com, baud, udp_host, udp_port)
        fanout_chk = getattr(self, "chk_udp_fanout", None)
        if fanout_chk is not None:
            fanout_chk.setChecked(bool(data.get("udp_fanout", True)))
        sink_chk = getattr(self, "chk_tcp_sink_enable", None)
        if sink_chk is not None:
            sink_chk.setChecked(bool(data.get("tcp_sink_enabled", False)))
        if getattr(self, "tcp_sink_port", None) is not None and data.get("tcp_sink_port"):
            self.tcp_sink_port.setText(str(data["tcp_sink_port"]))
        self._apply_preset_survey_fields(data)
        self._apply_preset_nmea_mode(data)
        self._update_field_connect_summary()
        if name:
            self._set_active_preset(name)
        if not log:
            return
        pc_ip = str(data.get("pc_ip", "")).strip()
        ins_ip = str(data.get("ins_ip", "")).strip()
        nmea = str(data.get("nmea_mode", "passthrough"))
        lines = [
            f"Loaded preset{f' «{name}»' if name else ''}: {com} @ {baud}, "
            f"UDP listen {udp_host}:{udp_port}, NMEA {nmea}."
        ]
        if pc_ip:
            lines.append(f"Survey PC {pc_ip} / {data.get('subnet_mask', '255.255.255.0')} — INS → {pc_ip}:{udp_port}.")
            if ins_ip:
                lines.append(f"INS reference IP: {ins_ip}.")
            lines.append("Start the bridge first and keep the selected COM dedicated while running.")
        else:
            lines.append(f"Bench: send UDP to 127.0.0.1:{udp_port}. Watch paired com0com, not {com}.")
        notes = str(data.get("notes", "")).strip()
        if notes:
            lines.append(notes)
        self._log_ui("\n".join(lines))

    def _select_preset_for_editing(self, name: str) -> None:
        """List click / keyboard: highlight preset and fill survey editor only."""
        clean = (name or "").strip()
        if not clean:
            return
        if clean == self._preset_editor_selection:
            self._sync_preset_action_buttons()
            return
        self._preset_editor_selection = clean
        try:
            data = load_preset(clean)
        except KeyError:
            self._sync_preset_action_buttons()
            return
        self._apply_preset_survey_fields(data)
        self._sync_preset_action_buttons()

    def _activate_preset_by_name(self, name: str, *, log: bool = True) -> None:
        """Select in list + load Connect + survey fields (Load, double-click, menu)."""
        clean = (name or "").strip()
        if not clean:
            return
        self._select_preset_row(clean, scroll=True)
        try:
            data = load_preset(clean)
        except KeyError:
            QtWidgets.QMessageBox.warning(
                self,
                "Presets",
                f"Preset «{clean}» was not found in path_presets.json.",
            )
            return
        if self.bridge is not None or self._starting:
            self._apply_preset_survey_fields(data)
            self._apply_preset_nmea_mode(data)
            self._presets_menu_pending = clean
            self._rebuild_presets_quick_menu()
            self._sync_preset_action_buttons()
            self._log_ui(
                f"Preset «{clean}» selected (survey + NMEA fields). "
                "Stop the bridge to apply COM/UDP from this preset."
            )
            return
        self._presets_menu_pending = None
        self._preset_editor_selection = clean
        self._apply_preset_data(data, name=clean, log=log)
        self._rebuild_presets_quick_menu()

    def _apply_preset_by_name(self, name: str, *, log: bool = True) -> None:
        self._activate_preset_by_name(name, log=log)

    def _preset_load_selected(self) -> None:
        name = self._selected_preset_name()
        if not name:
            QtWidgets.QMessageBox.information(self, "Presets", "Select a preset in the list.")
            return
        self._activate_preset_by_name(name, log=True)

    def _sync_preset_action_buttons(self) -> None:
        """Enable preset actions only when they can run (selection + bridge state)."""
        lst = getattr(self, "preset_list", None)
        if lst is None:
            return
        name = self._selected_preset_name()
        running = self.bridge is not None or self._starting
        has_selection = bool(name)
        names = list_preset_names()
        can_delete = has_selection and len(names) > 1

        load_tip_stopped = "Apply the selected preset to COM, UDP, and survey fields"
        load_tip_running = "Stop the bridge before loading a different preset"

        delete_tip = (
            "Remove the selected preset"
            if not running
            else "Stop the bridge before deleting a preset"
        )
        for attr, enabled, tip in (
            ("btn_preset_load", has_selection and not running, load_tip_stopped if not running else load_tip_running),
            ("btn_preset_save", has_selection, "Overwrite the selected preset with current fields"),
            (
                "btn_preset_save_as",
                True,
                "Save current fields under a new preset name (safe while the bridge is running)",
            ),
            ("btn_preset_new", True, "Create a new named preset"),
            ("btn_preset_delete", can_delete, delete_tip),
        ):
            btn = getattr(self, attr, None)
            if btn is None:
                continue
            btn.setEnabled(bool(enabled))
            if tip:
                btn.setToolTip(tip)

    def _on_preset_list_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        """Primary click — select for editing; use Load or double-click to apply Connect fields."""
        if self._preset_list_syncing:
            return
        name = self._preset_name_from_item(item)
        if not name:
            return
        self._select_preset_for_editing(name)

    def _on_preset_rows_moved(self, *args: object) -> None:
        lst = getattr(self, "preset_list", None)
        if lst is None:
            return
        names: list[str] = []
        for i in range(lst.count()):
            item = lst.item(i)
            if item is None:
                continue
            name = self._preset_name_from_item(item)
            if name:
                names.append(name)
        if reorder_preset_names(names):
            self._rebuild_presets_quick_menu()
            self._log_ui("[UI] Reordered connection presets.")

    def _on_preset_list_selection_changed(self) -> None:
        """Keyboard / programmatic selection — same as click (editor only)."""
        if self._preset_list_syncing:
            return
        name = self._selected_preset_name()
        if not name:
            self._sync_preset_action_buttons()
            return
        self._select_preset_for_editing(name)

    def _preset_save_selected(self) -> None:
        name = self._selected_preset_name()
        if not name:
            self._preset_save_as()
            return
        fields = self._preset_full_from_ui()
        err = self._validate_connection_preset_fields(fields)
        if err:
            QtWidgets.QMessageBox.warning(self, "Save preset", err)
            return
        boat = bool(fields.get("pc_ip") or fields.get("ins_ip"))
        path = save_preset(name, fields, boat_style=boat)
        self._set_active_preset(name)
        self._refresh_preset_list()
        self._log_ui(f"Saved preset «{name}» → {path}")

    def _preset_save_as(self) -> None:
        from ui.path_preset_dialog import ask_preset_name

        fields = self._preset_full_from_ui()
        err = self._validate_connection_preset_fields(fields)
        if err:
            QtWidgets.QMessageBox.warning(self, "Save preset", err)
            return
        name = ask_preset_name(self, "Save preset as", initial=self._active_preset_name or "")
        if not name:
            return
        boat = bool(fields.get("pc_ip") or fields.get("ins_ip"))
        path = save_preset(name, fields, boat_style=boat)
        self._set_active_preset(name)
        self._refresh_preset_list()
        self._log_ui(f"Saved preset «{name}» → {path}")

    def _preset_new(self) -> None:
        from ui.path_preset_dialog import ask_preset_name

        name = ask_preset_name(self, "New preset")
        if not name:
            return
        try:
            load_preset(name)
        except KeyError:
            fields = self._preset_full_from_ui()
            boat = bool(fields.get("pc_ip") or fields.get("ins_ip"))
            save_preset(name, fields, boat_style=boat)
        self._refresh_preset_list()
        self._set_active_preset(name)
        self._log_ui(f"Preset «{name}» ready — adjust fields and Save.")

    def _preset_delete_selected(self) -> None:
        if self.bridge is not None or self._starting:
            QtWidgets.QMessageBox.information(
                self,
                "Delete preset",
                "Stop the bridge before deleting a preset.",
            )
            return
        name = self._selected_preset_name()
        if not name:
            QtWidgets.QMessageBox.information(
                self, "Presets", "Select a preset in the list first."
            )
            return
        names = list_preset_names()
        if len(names) <= 1:
            QtWidgets.QMessageBox.information(
                self,
                "Delete preset",
                "Keep at least one preset on this PC.",
            )
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete preset",
            f"Delete preset «{name}»?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        if not delete_preset(name):
            QtWidgets.QMessageBox.warning(
                self,
                "Delete preset",
                "Could not delete — keep at least one preset, or name not found.",
            )
            return
        if self._active_preset_name == name:
            self._active_preset_name = None
        self._refresh_preset_list()
        self._log_ui(f"Deleted preset «{name}».")

    def _apply_bench_preset(self) -> None:
        names = list_preset_names()
        name = next(
            (n for n in names if "desk" in n.lower() or "bench" in n.lower()),
            names[0] if names else "Desk test",
        )
        self._apply_preset_by_name(name)

    def _apply_production_preset(self) -> None:
        names = list_preset_names()
        name = next(
            (n for n in names if "boat" in n.lower() or "ins" in n.lower()),
            names[-1] if names else "Boat / INS",
        )
        self._apply_preset_by_name(name)

    def _save_desk_preset(self) -> None:
        self._preset_save_as()

    def _save_boat_preset(self) -> None:
        self._preset_save_as()


    def _on_advanced_net_toggle(self, checked: bool) -> None:
        self._advanced_net.setVisible(checked)
        if not checked and not self.rb_udp_listen.isChecked():
            self.rb_udp_listen.setChecked(True)
        self._mode_toggle()


    def _selected_nmea_mode(self) -> NmeaMode:
        if getattr(self, "rb_nmea_raw", None) and self.rb_nmea_raw.isChecked():
            return NmeaMode.RAW
        if self.rb_nmea_strict.isChecked():
            return NmeaMode.STRICT
        return NmeaMode.PASSTHROUGH

    def _selected_nmea_filter(self) -> NmeaFilter:
        enabled = {st for st, cb in self._nmea_type_checks.items() if cb.isChecked()}
        return NmeaFilter(enabled_types=enabled)


    def _insert_send_sample(self) -> None:
        when = datetime.now(timezone.utc)
        gga = build_gga(when, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M)
        self.send_edit.setPlainText(gga)


    def _browse_log(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Survey log file", self.file_log_path.text(), "Log files (*.log);;All files (*)")
        if path:
            self.file_log_path.setText(path)

    def _mode_toggle(self, *_args) -> None:
        advanced = self.chk_advanced_net.isChecked()
        m_udp_l = self.rb_udp_listen.isChecked()
        m_udp_r = self.rb_udp_remote.isChecked()
        m_tcp_s = self.rb_tcp_server.isChecked()
        m_tcp_c = self.rb_tcp_client.isChecked()

        if not advanced and not m_udp_l:
            self.rb_udp_listen.setChecked(True)
            m_udp_l = True
            m_udp_r = False

        self._udp_box.setVisible(advanced and m_udp_r)
        self._tcp_srv_box.setVisible(advanced and m_tcp_s)
        self._tcp_cli_box.setVisible(advanced and m_tcp_c)

        locked = self.bridge is not None or self._starting
        if not locked:
            for w in (
                self.udp_host,
                self.udp_port,
                self.remote_host,
                self.remote_port,
                self.tcp_srv_host,
                self.tcp_srv_port,
                self.tcp_cli_host,
                self.tcp_cli_port,
                self.tcp_reconnect_spin,
            ):
                w.setEnabled(True)

        self._refresh_intent_hint()
        if advanced:
            self._advanced_net.updateGeometry()

    def _enqueue_ui(self, line: str) -> None:
        while len(self._pending_ui) >= UI_LOG_PENDING_MAX:
            self._pending_ui.popleft()
            self._ui_drops += 1
        self._pending_ui.append(line)

    def _flush_ui_log(self) -> None:
        if self._log_pause or not self._pending_ui:
            return
        n = min(UI_LOG_MAX_LINES_PER_FLUSH, len(self._pending_ui))
        chunk = [self._pending_ui.popleft() for _ in range(n)]
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.set_log_paused(
                self._log_pause,
                dropped=int(getattr(self, "_log_paused_dropped", 0) or 0),
            )
            if not self._log_pause:
                facade.append_log_lines(chunk)
        self.log_view.appendPlainText("\n".join(chunk))
        self._append_connect_mini_log(chunk)
        if self._log_autoscroll:
            sb = self.log_view.verticalScrollBar()
            sb.setValue(sb.maximum())
        pop = getattr(self, "_stats_popout_window", None)
        if pop is not None:
            try:
                if pop.isVisible():
                    pop.append_nmea_log_lines(chunk)
            except RuntimeError:
                self._stats_popout_window = None

    def _log_ui(self, txt: str) -> None:
        from log_serial_coalesce import ui_safe_text

        txt = ui_safe_text(txt)
        if self._should_coalesce_serial_gui_log(txt):
            return
        if not self._log_line_allowed(txt):
            return
        if self._log_pause:
            self._log_paused_dropped += 1
            return
        self._enqueue_ui(txt)

    def _log_line_allowed(self, txt: str) -> bool:
        return log_line_allowed(txt, self._log_view_state)

    def _on_log_hex_toggled(self, _on: bool = False) -> None:
        if self._log_view_sync_guard:
            return
        chk = getattr(self, "chk_log_hex", None)
        if chk is None:
            return
        st = LogViewState(
            **{
                **self._log_view_state.to_dict(),
                "sentence_types": frozenset(self._log_view_state.sentence_types),
            }
        )
        st.hex = chk.isChecked()
        st.preset = st.detect_preset()
        self._apply_log_view_state(st, sync_widgets=True)

    def _set_log_pause(self, paused: bool) -> None:
        prev = self._log_pause
        self._log_pause = bool(paused)
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.set_log_paused(
                self._log_pause,
                dropped=int(getattr(self, "_log_paused_dropped", 0) or 0),
            )
        if self._log_pause:
            self._log_paused_dropped = 0
            return
        if prev and self._log_paused_dropped:
            dropped = self._log_paused_dropped
            self._log_paused_dropped = 0
            self._enqueue_ui(f"[PAUSE] resumed — {dropped} lines skipped while paused")
            self._flush_ui_log()

    def _set_log_autoscroll(self, enabled: bool) -> None:
        self._log_autoscroll = bool(enabled)

    def _load_diag_card_states(self) -> dict[str, bool]:
        return dict(self._diag_card_states)

    def _save_diag_card_state(self, key: str, is_open: bool) -> None:
        self._diag_card_states[str(key)] = bool(is_open)
        save_diag_card_states(getattr(self, "_ui_mode", "standard"), self._diag_card_states)

    def _load_diag_card_order(self) -> list[str]:
        order = load_diag_card_order(getattr(self, "_ui_mode", "standard"))
        return order or list(_DEFAULT_DIAG_CARD_ORDER)

    def _save_diag_card_order(self, order: list[str]) -> None:
        save_diag_card_order(getattr(self, "_ui_mode", "standard"), order)

    def _apply_diag_card_order(self) -> None:
        widgets = getattr(self, "_diag_card_widgets", None)
        if not isinstance(widgets, dict):
            return
        order = self._load_diag_card_order()
        ordered_widgets = [widgets[k] for k in order if k in widgets]
        for key, w in widgets.items():
            if w not in ordered_widgets:
                ordered_widgets.append(w)
        splitter: QtWidgets.QSplitter | None = getattr(self, "_diag_cards_splitter", None)
        if splitter is not None:
            for w in ordered_widgets:
                w.setParent(None)
            for w in ordered_widgets:
                splitter.addWidget(w)
        else:
            lay = getattr(self, "_diag_cards_layout", None)
            if lay is None:
                return
            for w in ordered_widgets:
                lay.removeWidget(w)
                lay.addWidget(w)
        from ui.tool_tabs import refresh_diag_cards

        refresh_diag_cards(self)

    def _open_diag_card_order_manager(self) -> None:
        labels = {
            "file_log": "Rotating file log",
            "screen_log": "On-screen log",
            "traffic_quality": "Traffic & data quality",
            "automated_checks": "Automated checks",
        }
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Reorder diagnostics cards")
        dlg.setMinimumSize(480, 360)
        dlg.resize(560, 400)
        lay = QtWidgets.QVBoxLayout(dlg)
        hint = QtWidgets.QLabel("Drag cards into your preferred order, then Apply.")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lst = QtWidgets.QListWidget()
        lst.setObjectName("presetList")
        lst.setMinimumHeight(220)
        lst.setDragEnabled(True)
        lst.setAcceptDrops(True)
        lst.setDropIndicatorShown(True)
        lst.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        lst.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        lst.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        order = self._load_diag_card_order()
        for key in order:
            text = labels.get(key, key)
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsDragEnabled
            )
            lst.addItem(item)
        lay.addWidget(lst, 1)
        row = QtWidgets.QHBoxLayout()
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_cancel = QtWidgets.QPushButton("Cancel")
        row.addStretch(1)
        row.addWidget(btn_apply)
        row.addWidget(btn_cancel)
        lay.addLayout(row)

        def _apply() -> None:
            new_order: list[str] = []
            for i in range(lst.count()):
                item = lst.item(i)
                if item is None:
                    continue
                key = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "").strip()
                if key:
                    new_order.append(key)
            self._save_diag_card_order(new_order)
            self._apply_diag_card_order()
            self._log_ui("[UI] Reordered diagnostics cards.")
            dlg.accept()

        btn_apply.clicked.connect(_apply)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def _should_coalesce_serial_gui_log(self, txt: str, window_s: float = 2.5) -> bool:
        """Live log: drop repeat ``Serial COMx: timed out (open/write).`` within window."""
        suppress, last, mono = serial_timeout_line_suppress(
            self._ui_log_serial_dup_last,
            self._ui_log_serial_dup_mono,
            txt,
            window_s=window_s,
        )
        self._ui_log_serial_dup_last = last
        self._ui_log_serial_dup_mono = mono
        return suppress

    def _sync_serial_status_chrome(self, serial_line: str) -> None:
        chip = getattr(self, "status_serial", None)
        if chip is None:
            return
        low = serial_line.lower()
        alert = self._is_bridge_running() and any(
            token in low
            for token in (
                "disconnected",
                "reconnect",
                "retry",
                "cannot open",
                "timed out",
                "not found",
            )
        )
        if alert:
            chip.setStyleSheet(
                "QLabel { background-color: #7f1d1d; color: #fff3f3; "
                "border: 1px solid #ef9a9a; border-radius: 4px; padding: 0 4px; }"
            )
        else:
            chip.setStyleSheet("")

    def _maybe_refresh_ports_on_serial_retry(self, serial_line: str) -> None:
        """USB re-enumeration may change COM name while bridge is retrying."""
        low = serial_line.lower()
        if not any(token in low for token in ("reconnect", "disconnected", "not found", "retry")):
            return
        now = time.monotonic()
        if now - getattr(self, "_serial_retry_refresh_mono", 0.0) < 5.0:
            return
        self._serial_retry_refresh_mono = now
        self.refresh_ports()

    def _update_status_bar(self, serial_line: str, network_line: str) -> None:
        from ui.controls import elide_status_label
        from ui.tray_support import update_tray_tooltip

        self._maybe_refresh_ports_on_serial_retry(serial_line)
        elide_status_label(self.status_serial, serial_line)
        elide_status_label(self.status_network, network_line)
        self._sync_serial_status_chrome(serial_line)
        self._refresh_nmea_status_chip()
        self._refresh_stats_popout()
        tray = getattr(self, "_tray_icon", None)
        if tray is not None:
            update_tray_tooltip(tray, f"Serial Link — {serial_line} | {network_line}")

    def _set_connection_locked(self, locked: bool) -> None:
        for w in self._connection_widgets:
            w.setEnabled(not locked)
        for w in getattr(self, "_nmea_widgets", []):
            w.setEnabled(not locked)
        self.start_btn.setEnabled(not locked)
        self.stop_btn.setEnabled(locked)
        if not locked:
            self._mode_toggle()

    def _stats_tooltip(self) -> str:
        return (
            "Live QA (this session)\n\n"
            "↓ Hz — Complete NMEA sentences per second from UDP/TCP toward the serial port "
            "(rolling 1 s window). Matches what your simulator/INS sends after line assembly — "
            "not raw packet count.\n"
            "↑ Hz — Sentences per second from COM toward the network.\n"
            "Send→COM …/s — Only when Tools → Inject is actively sending at ≥ ~0.05/s "
            "(rolling 1 s). Does not add to ↓ Hz.\n\n"
            "transport OK — No drops, no rejects, and no queue backlog "
            "(a few queued chunks while data is moving is normal).\n"
            "Warn/backlog when depth reaches ~12+ on a side, or on drops/rejects.\n\n"
            "session totals — Lifetime sentences forwarded: remote →COM (UDP/TCP) and COM→net.\n\n"
            "GNSS — Latest GGA: fix (RTK fixed best), satellites (5+ min, 7+ preferred with low HDOP), "
            "HDOP (ideal <2.5, acceptable <4; POSPac MMS Ch.16). Stale if no GGA ~2 s.\n\n"
            "Live log: identical “Serial … timed out (open/write).” lines are shown at most once per ~2.5 s "
            "(same window as the bridge engine; avoids spam during stress or Stop)."
        )

    def _starting_network_blurb(self) -> str:
        if self.rb_udp_listen.isChecked():
            return f"UDP listen {self.udp_host.text().strip()}:{self.udp_port.text().strip()}"
        if self.rb_udp_remote.isChecked():
            return f"UDP remote {self.remote_host.text().strip()}:{self.remote_port.text().strip()}"
        if self.rb_tcp_server.isChecked():
            return f"TCP server {self.tcp_srv_host.text().strip()}:{self.tcp_srv_port.text().strip()}"
        return f"TCP client {self.tcp_cli_host.text().strip()}:{self.tcp_cli_port.text().strip()}"

    def _running_banner_detail(self, b: SerialNetBridge) -> str:
        if b.mode == NetMode.UDP_LISTEN and b.udp_listen:
            host, port = b.udp_listen
            return f"{b.com} @ {b.baud} — UDP listen {host}:{port}"
        if b.mode == NetMode.UDP_REMOTE and b.udp_remote:
            host, port = b.udp_remote
            return f"{b.com} @ {b.baud} — UDP → {host}:{port}"
        if b.mode == NetMode.TCP_SERVER:
            return f"{b.com} @ {b.baud} — TCP server {b.tcp_bind_host}:{b.tcp_bind_port}"
        if b.mode == NetMode.TCP_CLIENT:
            return f"{b.com} @ {b.baud} — TCP client → {b.tcp_client_host}:{b.tcp_client_port}"
        return f"{b.com} @ {b.baud}"

    def _merge_bridge_stats(self, base: Optional[dict] = None) -> dict:
        b = self.bridge
        if not b or not hasattr(b, "drops_net_to_serial"):
            return {}
        _ = base  # worker may send partial snapshots; always read live counters
        return {
            "drops_n2s": b.drops_net_to_serial,
            "drops_s2n": b.drops_serial_to_net,
            "rej_n2s": b.rejected_net_to_serial,
            "rej_s2n": b.rejected_serial_to_net,
            "n2s_q": b.net_to_serial.qsize(),
            "s2n_q": b.serial_to_net.qsize(),
            "hz_down": b.hz_remote_to_serial(),
            "hz_gui": b.hz_gui_to_serial(),
            "hz_up": b.hz_serial_to_net(),
            "lines_down": b.lines_remote_to_serial,
            "lines_up": b.lines_serial_to_net,
            "udp_peers": b.udp_peer_count,
            **b.navigation_quality_stats(),
            **b.navigation_position_stats(),
        }

    def _sync_transport_alert_chrome(self, merged: dict) -> None:
        lbl = getattr(self, "lbl_stats", None)
        if lbl is None:
            return
        active = transport_alert_active(merged)
        if active:
            lbl.setStyleSheet(
                "QLabel { background-color: #7f1d1d; color: #fff3f3; "
                "border: 1px solid #ef9a9a; border-radius: 4px; padding: 0 6px; }"
            )
        else:
            lbl.setStyleSheet("")

    def _stats_from_bridge(self, _d: dict) -> None:
        if not self.bridge:
            return
        merged = self._merge_bridge_stats(_d)
        self._bridge_stats_cache = dict(merged)
        import time as _time

        hub = getattr(self, "connection_hub", None)
        if hub is not None and (_time.monotonic() - getattr(self, "_last_hub_poll_mono", 0.0)) >= 2.0:
            self._last_hub_poll_mono = _time.monotonic()
            self._poll_discovery_snapshot()
        self._apply_hub_quality()
        facade = getattr(self, "_app_facade", None)
        if facade is not None:
            facade.publish_from_window(self)
        from ui.controls import elide_status_label

        elide_status_label(self.lbl_stats, format_live_stats_line(merged))
        self._sync_transport_alert_chrome(merged)
        self.lbl_stats.setToolTip(self._stats_tooltip())
        self._refresh_gnss_status_chip()
        self._refresh_stats_popout()
        self._refresh_dashboard()

    def _tick_stats(self) -> None:
        if self._is_bridge_running():
            self._stats_from_bridge({})
        else:
            facade = getattr(self, "_app_facade", None)
            if facade is not None:
                facade.publish_from_window(self)
            from ui.controls import elide_status_label

            elide_status_label(
                self.lbl_stats,
                "Stopped — Hz & transport here when Running (hover)",
            )
            self._sync_transport_alert_chrome({})
            self.lbl_stats.setToolTip(self._stats_tooltip())
            self._refresh_gnss_status_chip()
            self._refresh_stats_popout()
            self._refresh_dashboard()

    def _diag_udp_port(self) -> Optional[int]:
        try:
            return _parse_port(self.udp_port.text(), "UDP port")
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self,
                "Diagnostics",
                "Enter a valid UDP listen port on the Connect tab first.",
            )
            return None

    def _diag_set_running_ui(self, running: bool) -> None:
        for b in getattr(self, "_diag_run_buttons", ()):
            b.setEnabled(not running)
        if hasattr(self, "btn_diag_stop"):
            self.btn_diag_stop.setEnabled(running)

    def _focus_diagnostics_tab(self) -> None:
        from ui.tool_tabs import refresh_diag_cards

        tabs = getattr(self, "_main_tabs", None) or getattr(self, "_drawer_tabs", None)
        if tabs is None:
            return
        for i in range(tabs.count()):
            label = tabs.tabText(i).lower()
            if label.startswith("diag") or label == "diagnostics":
                tabs.setCurrentIndex(i)
                break
        drawer = getattr(self, "_drawer_btn", None)
        if drawer is not None and not drawer.isChecked():
            drawer.setChecked(True)
        QtCore.QTimer.singleShot(0, lambda: refresh_diag_cards(self))

    def _diag_expand_card(self, key: str) -> None:
        from ui.tool_tabs import _IosCollapsibleCard

        card = getattr(self, "_diag_card_widgets", {}).get(key)
        if isinstance(card, _IosCollapsibleCard):
            card.set_expanded(True)

    def _append_diag_output(self, text: str) -> None:
        from log_serial_coalesce import ui_safe_text

        text = ui_safe_text(text)
        self._append_connect_terminal(text)
        if not hasattr(self, "diag_output"):
            return
        self.diag_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.diag_output.insertPlainText(text)
        self.diag_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        if getattr(self, "chk_diag_mirror_log", None) and self.chk_diag_mirror_log.isChecked():
            for line in text.splitlines():
                if line.strip():
                    self._log_ui(line)

    def _diag_start_script(
        self,
        title: str,
        script: str,
        args: list[str],
        *,
        focus_diag: bool | None = None,
        clear_output: bool | None = None,
    ) -> None:
        if self._diag_qprocess is not None and self._diag_qprocess.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._append_diag_output("A check is already running — press Stop or wait for it to finish.\n")
            return
        if not hasattr(self, "diag_output"):
            QtWidgets.QMessageBox.information(
                self,
                "Diagnostics",
                "This layout has no Diagnostics panel — use Standard UI or Field → Tools → Diag.",
            )
            return
        bench_chain = bool(getattr(self, "_bench_preflight_chain", False))
        if focus_diag is None:
            focus_diag = not bench_chain
        if clear_output is None:
            clear_output = not bench_chain
        if focus_diag:
            self._focus_diagnostics_tab()
            self._diag_expand_card("automated_checks")
        if clear_output:
            self.diag_output.clear()
        self._diag_current_title = title
        exe = cli_python_gui_spawn()
        rel = _REPO_ROOT / script
        if not rel.is_file():
            self._append_diag_output(f"Script not found: {rel}\n")
            if bench_chain:
                self._bench_preflight_chain = False
            self._log_ui(f"[UI] Missing script: {rel.name}")
            return
        cmd = f"{exe} {rel.name} {' '.join(args)}".strip()
        self._append_diag_output(f"$ {cmd}\n(working dir: {_REPO_ROOT})\n\n")
        self.diag_status_label.setText(f"Running: {title}…")
        self._diag_set_running_ui(True)

        proc = QtCore.QProcess(self)
        proc.setProgram(exe)
        proc.setArguments(frozen_helper_program_args(str(rel), args))
        proc.setWorkingDirectory(str(_REPO_ROOT))
        # Ensure the subprocess can import project modules (bench_config, nmea_codec,
        # bridge_core, etc.) from the same directory the scripts live in.  In a frozen
        # build _REPO_ROOT = sys._MEIPASS where the spec bundles all HELPER_MODULES as
        # raw .py files; in dev _REPO_ROOT is the project root.
        env = QtCore.QProcessEnvironment.systemEnvironment()
        existing_pypath = env.value("PYTHONPATH", "")
        new_pypath = (
            f"{_REPO_ROOT}{';' if sys.platform == 'win32' else ':'}{existing_pypath}"
            if existing_pypath
            else str(_REPO_ROOT)
        )
        env.insert("PYTHONPATH", new_pypath)
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.SeparateChannels)
        proc.readyReadStandardOutput.connect(self._diag_on_stdout)
        proc.readyReadStandardError.connect(self._diag_on_stderr)
        proc.finished.connect(self._diag_on_finished)
        proc.errorOccurred.connect(self._diag_on_error)
        self._diag_qprocess = proc
        try:
            qprocess_attach_no_console(proc)
        except Exception as exc:
            self._append_diag_output(
                f"\n[Diagnostics spawn setup failed: {exc!r}]\n"
                "Restart the app after updating to the latest bridge build.\n"
            )
            self._diag_release_process(user_stop=False)
            if bench_chain:
                self._bench_preflight_chain = False
            self._log_ui(f"[UI] Diagnostics spawn failed: {exc!r}")
            return
        proc.start()
        if not proc.waitForStarted(5000):
            err = proc.errorString() or "unknown error"
            self._append_diag_output(f"\n[failed to start script: {err}]\n")
            self._diag_release_process(user_stop=False)
            if bench_chain:
                self._bench_preflight_chain = False
            self._log_ui(f"[UI] Could not start {script}: {err}")
            return

    def _diag_on_stdout(self) -> None:
        p = self._diag_qprocess
        if not p:
            return
        self._append_diag_output(bytes(p.readAllStandardOutput()).decode(errors="replace"))

    def _diag_on_stderr(self) -> None:
        p = self._diag_qprocess
        if not p:
            return
        self._append_diag_output(bytes(p.readAllStandardError()).decode(errors="replace"))

    def _diag_on_error(self, error: QtCore.QProcess.ProcessError) -> None:
        self._append_diag_output(f"\n[process error: {int(error)}]\n")

    def _diag_on_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        p = self.sender()
        if p is not self._diag_qprocess:
            return
        normal = exit_status == QtCore.QProcess.ExitStatus.NormalExit
        ok = normal and exit_code == 0
        label = "PASS" if ok else "FAIL"
        self.diag_status_label.setText(
            f"Finished: {self._diag_current_title} — exit code {exit_code} — {label}"
        )
        self._append_diag_output(f"\n--- done (exit {exit_code}) — {label} ---\n")
        chain = self._bench_preflight_chain
        title = self._diag_current_title.lower()
        if p is self._diag_qprocess:
            self._diag_release_process(user_stop=False)
        if chain:
            if "com_free" in title:
                if ok:
                    self._append_diag_output("\n--- Next: check_setup (bench preset) ---\n")
                    QtCore.QTimer.singleShot(0, self._diag_run_check_setup)
                else:
                    self._bench_preflight_chain = False
                    self._log_ui(
                        "[UI] Bench preflight stopped at com_free — free the bridge COM and retry."
                    )
            elif "check_setup" in title:
                self._bench_preflight_chain = False
                if ok:
                    self._log_ui(
                        "[UI] Bench preflight OK — load bench preset, Start bridge, watch paired COM."
                    )
                else:
                    self._log_ui("[UI] Bench preflight: check_setup reported issues (see Diagnostics).")

    def _diag_release_process(self, *, user_stop: bool = False) -> None:
        p = self._diag_qprocess
        if p is None:
            return
        for sig in (
            p.readyReadStandardOutput,
            p.readyReadStandardError,
            p.finished,
            p.errorOccurred,
        ):
            try:
                sig.disconnect()
            except (RuntimeError, TypeError):
                pass
        self._diag_qprocess = None
        self._diag_set_running_ui(False)
        if user_stop and hasattr(self, "diag_status_label"):
            self.diag_status_label.setText("Stopped by user")
        p.deleteLater()

    def _diag_stop(self) -> None:
        p = self._diag_qprocess
        if p is None:
            return
        if p.state() != QtCore.QProcess.ProcessState.NotRunning:
            p.kill()
            p.waitForFinished(3000)
        self._append_diag_output("\n[stopped by user]\n")
        self._bench_preflight_chain = False
        self._diag_release_process(user_stop=True)

    def _diag_run_verify_all(self) -> None:
        if getattr(sys, "frozen", False):
            # verify_all.py runs the full unit-test tree which is not shipped in the
            # portable build.  Detect this early and tell the user instead of silently
            # failing deep inside the script.
            test_probe = _REPO_ROOT / "test_bridge_core.py"
            if not test_probe.is_file():
                self._append_diag_output(
                    "Full verify is not available in the portable (.exe) build.\n"
                    "The unit-test files are not included in the distribution.\n\n"
                    "To run verify_all, clone the repository and use:\n"
                    "  python verify_all.py\n"
                )
                self._log_ui("[UI] verify_all skipped — portable build has no test tree.")
                return
        self._diag_start_script("verify_all (full automated suite)", "verify_all.py", [])

    def _operator_guide_path(self) -> Path:
        return _REPO_ROOT / "docs" / "OPERATOR_GUIDE.md"

    def _open_operator_guide_bench(self) -> bool:
        from ui.doc_viewer import resolve_bundled_doc, show_bundled_doc

        if resolve_bundled_doc("docs/OPERATOR_GUIDE.md") is None:
            guide = self._operator_guide_path()
            QtWidgets.QMessageBox.warning(
                self,
                "Operator guide",
                f"Guide not found:\n{guide}\n\nSee README.md bench section.",
            )
            return False
        show_bundled_doc(self, "docs/OPERATOR_GUIDE.md", window_title="Operator guide")
        return True

    def _open_bench_pair_setup(self) -> None:
        """Open bench/com0com guide and run preflight on Connect (quick terminal)."""
        from ui.connect_panels import expand_connect_panel

        self._sync_bench_setup_button_visibility()
        if bool(load_bench_setup_prefs().get("hide_dialog", False)):
            self._log_ui("[UI] Bench setup window hidden by preference. Running preflight only.")

        self._focus_connect_tab()
        expand_connect_panel(self, "quick_terminal")

        guide_path = self._operator_guide_path()
        section = extract_operator_guide_section(guide_path, "5. Desk / bench workflow")
        dlg = show_bench_setup_dialog(
            self,
            section,
            on_open_full_guide=self._open_operator_guide_bench,
            on_hide_pref_changed=lambda _on: self._sync_bench_setup_button_visibility(),
        )
        if dlg is None:
            self._log_ui("[UI] Bench setup window is hidden by preference (preflight still runs).")

        intro = (
            "=== Bench pair setup ===\n"
            "Guide: see the Bench pair setup window (section 5).\n"
            "1) Install com0com and create a PAIRED port pair.\n"
            "2) Bridge uses one COM; Tera Term uses the paired port (not the same COM).\n"
            "3) Running com_free, then check_setup…\n\n"
        )
        self._append_connect_terminal(intro)
        out = getattr(self, "connect_terminal_out", None)
        if out is not None:
            out.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

        if not hasattr(self, "diag_output"):
            QtWidgets.QMessageBox.information(
                self,
                "Bench pair setup",
                "Preflight runs in the Quick terminal on Connect.\n\n"
                "Switch to Standard UI if scripts cannot start.",
            )
            return
        if self._diag_qprocess is not None and self._diag_qprocess.state() != QtCore.QProcess.ProcessState.NotRunning:
            QtWidgets.QMessageBox.information(
                self,
                "Bench pair setup",
                "A diagnostics script is already running. Stop it on Diagnostics, then retry.",
            )
            return
        self._log_ui("[UI] Bench pair setup: running preflight (com_free → check_setup)…")
        self._bench_preflight_chain = True
        self._diag_run_com_free()

    def _sync_bench_setup_button_visibility(self) -> None:
        """Hide/show Bench pair setup buttons based on bench_setup preference."""
        hide = bool(load_bench_setup_prefs().get("hide_dialog", False))
        for name in ("btnBenchPairSetupRun", "btnBenchPairSetupDiag"):
            for btn in self.findChildren(QtWidgets.QPushButton, name):
                btn.setVisible(not hide)

    def _diag_run_com_free(self) -> None:
        d = load_bench_defaults()
        active = (self._active_preset_name or "").strip()
        if active:
            try:
                d = load_preset(active)
            except KeyError:
                pass
        com = str(d.get("com", "")).strip() or str(load_bench_defaults()["com"])
        baud = int(d.get("baud", load_bench_defaults()["baud"]))
        args = ["--com", com, "--baud", str(baud)]
        self._diag_start_script(f"com_free ({com})", "com_free.py", args)

    def _diag_desk_udp_target(self) -> tuple[str, int]:
        d = load_bench_defaults()
        return desk_udp_send_host(d), int(d["udp_port"])

    def _diag_tcp_server_connect_host(self) -> str:
        """Host for an external TCP client to reach our TCP server bind address."""
        host = self.tcp_srv_host.text().strip() or "0.0.0.0"
        if host in ("0.0.0.0", "::", "", "*"):
            return "127.0.0.1"
        if host.lower() in ("localhost",):
            return "127.0.0.1"
        return host

    def _diag_tcp_server_target(self) -> tuple[str, int]:
        try:
            port = _parse_port(self.tcp_srv_port.text(), "TCP server port")
        except ValueError:
            port = 4001
        return self._diag_tcp_server_connect_host(), port

    def _diag_check_setup_args(self, *, production: bool) -> list[str]:
        """Build check_setup CLI args and remember which preset profile was used."""
        active = (self._active_preset_name or "").strip()
        chosen_name = active or last_preset_name()
        d: dict[str, object]
        used_name = chosen_name or ("Boat / INS" if production else "Desk test")
        used_fallback = False
        if chosen_name:
            try:
                d = load_preset(chosen_name)
            except KeyError:
                d = load_production_defaults() if production else load_bench_defaults()
                used_fallback = True
        else:
            d = load_production_defaults() if production else load_bench_defaults()
            used_fallback = True

        # Boat checklist requires boat-style fields; if missing, use production defaults explicitly.
        if production and not str(d.get("pc_ip", "")).strip():
            d = load_production_defaults()
            used_name = "Boat / INS"
            used_fallback = True

        self._diag_last_check_setup_preset = used_name
        self._diag_last_check_setup_fallback = used_fallback
        args = ["--production"] if production else []
        send_host = (
            str(d.get("pc_ip", "192.168.1.10")).strip() or "192.168.1.10"
            if production
            else desk_udp_send_host(d)
        )
        port = int(d.get("udp_port", 10110))
        com = str(d.get("com", "")).strip()
        args.extend(["--port", str(port), "--host", send_host])
        if com:
            args.extend(["--com", com])
        return args

    def _diag_run_check_setup(self) -> None:
        self._focus_diagnostics_tab()
        args = self._diag_check_setup_args(production=False)
        preset_name = str(getattr(self, "_diag_last_check_setup_preset", "") or "Desk test")
        used_fallback = bool(getattr(self, "_diag_last_check_setup_fallback", False))
        self._log_ui(
            f"[UI] Running bench checklist using preset «{preset_name}»"
            f"{' (fallback)' if used_fallback else ''}."
        )
        self._diag_start_script("check_setup (bench preset)", "check_setup.py", args)

    def _diag_run_check_setup_production(self) -> None:
        self._focus_diagnostics_tab()
        args = self._diag_check_setup_args(production=True)
        preset_name = str(getattr(self, "_diag_last_check_setup_preset", "") or "Boat / INS")
        used_fallback = bool(getattr(self, "_diag_last_check_setup_fallback", False))
        self._log_ui(
            f"[UI] Running boat checklist using preset «{preset_name}»"
            f"{' (fallback)' if used_fallback else ''}."
        )
        self._diag_start_script("check_setup --production (boat preset)", "check_setup.py", args)

    def _diag_run_network_bench(self) -> None:
        self._diag_start_script(
            "bench_network_automation (P0 network auto)",
            "bench_network_automation.py",
            [],
        )

    def _diag_run_fanout_bench(self) -> None:
        self._diag_start_script(
            "bench_fanout_automation (two UDP peers)",
            "bench_fanout_automation.py",
            [],
        )

    def _diag_run_udp_sample(self) -> None:
        host, port = self._diag_desk_udp_target()
        self._diag_start_script(
            "nmea_static_sample (2.5 s UDP burst @ 5 Hz)",
            "nmea_static_sample.py",
            [
                "--dest-host",
                host,
                "--dest-port",
                str(port),
                "--duration",
                "2.5",
                "--quiet",
            ],
        )

    def _diag_run_tcp_stress(self) -> None:
        if not self.chk_advanced_net.isChecked() or not self.rb_tcp_server.isChecked():
            QtWidgets.QMessageBox.information(
                self,
                "TCP stress",
                "Set Connect → Advanced network → TCP server, then Start the bridge.\n\n"
                "The stress client connects to your TCP server port (not TCP client mode).",
            )
            return
        host, port = self._diag_tcp_server_target()
        self._diag_start_script(
            f"TCP stress LA→Sac @ 5 Hz → {host}:{port}",
            "bench_tcp_stress.py",
            [
                "--host",
                host,
                "--port",
                str(port),
                "--hz",
                "5",
                "--speed-mps",
                "5",
            ],
        )

    def _diag_run_tcp_demo(self) -> None:
        if not self.chk_advanced_net.isChecked() or not self.rb_tcp_server.isChecked():
            QtWidgets.QMessageBox.information(
                self,
                "TCP demo",
                "Start the bridge in TCP server mode first (Connect -> Advanced -> TCP server).",
            )
            return
        host, port = self._diag_tcp_server_target()
        self._diag_start_script(
            f"TCP presenter demo (~4 min) -> {host}:{port}",
            "bench_tcp_stress.py",
            ["--host", host, "--port", str(port), "--hz", "5", "--demo"],
        )

    def _diag_run_capacity_probe(self) -> None:
        d = load_bench_defaults()
        com = str(d["com"]).strip()
        baud = int(d["baud"])
        port = int(d["udp_port"])
        dest_host = desk_udp_send_host(d)
        if not com:
            QtWidgets.QMessageBox.warning(
                self,
                "Diagnostics",
                "Desk preset has no COM — set Connect and Save Desk preset first.",
            )
            return
        prof = {}
        box = getattr(self, "cmb_diag_capacity", None)
        if box is not None:
            raw = box.currentData()
            if isinstance(raw, dict):
                prof = raw
        hz_start = float(prof.get("start", 5))
        hz_stop = float(prof.get("stop", 40))
        hz_step = float(prof.get("step", 5))
        if hz_step <= 0:
            hz_step = 5.0
        sent = int(prof.get("sent", 8))
        sec = float(prof.get("sec", 6.0))
        profile_name = str(prof.get("name", "custom"))
        if hz_stop < hz_start:
            hz_stop = hz_start
        stages = int((hz_stop - hz_start) / hz_step) + 1
        max_runtime = max(20.0, stages * (sec + 0.5) + 12.0)
        args = [
            "--com",
            com,
            "--baud",
            str(baud),
            "--udp-host",
            str(d["udp_host"]),
            "--udp-port",
            str(port),
            "--dest-host",
            dest_host,
            "--hz-start",
            f"{hz_start:g}",
            "--hz-stop",
            f"{hz_stop:g}",
            "--hz-step",
            f"{hz_step:g}",
            "--sentences",
            str(sent),
            "--stage-seconds",
            f"{sec:g}",
            "--max-runtime",
            f"{max_runtime:g}",
            "--stop-on-clog",
        ]
        chk = getattr(self, "chk_diag_capacity_strict", None)
        if chk is not None and chk.isChecked():
            args.append("--strict")
        self._diag_start_script(
            f"capacity probe [{profile_name}] (ramp no-drop threshold)",
            "bench_capacity_probe.py",
            args,
        )

    def refresh_ports(self) -> None:
        prev = self.com_cb.currentText().strip()
        self.com_cb.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            self.com_cb.addItem("(no ports — click Refresh)")
            self.com_cb.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
            return
        for device in ports:
            self.com_cb.addItem(device)
        self.com_cb.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        if prev:
            idx = self.com_cb.findText(prev)
            if idx >= 0:
                self.com_cb.setCurrentIndex(idx)
            else:
                self.com_cb.setCurrentText(prev)

    def _send_raw_manual(self, where: str, raw: str) -> None:
        if not self._is_bridge_running():
            self._log_ui(
                "Send: bridge not running — Connect tab: choose path, Start, wait for Running."
            )
            return
        data = _nmea_line_bytes(raw)
        if not data:
            self._log_ui("Send: empty or invalid line.")
            return
        self._log_ui(f"Send: {len(data)} bytes -> {where}")
        b = self.bridge
        w = self._worker

        def _do() -> None:
            if not self._bridge_running_safe(b):
                return
            if where == "serial":
                b.schedule_net_to_serial(data, "GUI→SER")
            elif where == "net":
                b.schedule_serial_to_net(data, "GUI→NET")
            else:
                b.schedule_net_to_serial(data, "GUI→SER")
                b.schedule_serial_to_net(data, "GUI→NET")

        if w:
            w.call_on_loop(_do)
        else:
            _do()

    def _send_manual(self, where: str) -> None:
        if not self._is_bridge_running():
            self._log_ui(
                "Send: bridge not running — Connect tab: choose path, Start, wait for Running."
            )
            return
        raw = self.send_edit.toPlainText()
        if not raw.strip():
            self._log_ui(
                "Send: box is empty — type/paste NMEA in Tools → Inject, or click Insert sample GGA."
            )
            return
        self._send_raw_manual(where, raw)

    def start_bridge(self) -> None:
        if self._starting:
            self._log_ui("Start already in progress — wait for Running or click Stop.")
            return
        if self._stopping:
            self._log_ui("Bridge is still stopping — try Start again in a moment.")
            return
        remain = _start_cooldown_remaining_s(
            getattr(self, "_bridge_stop_mono", 0.0),
            time.monotonic(),
        )
        if remain > 0:
            if not getattr(self, "_start_defer_pending", False):
                self._start_defer_pending = True
                wait_ms = max(50, int(remain * 1000) + 25)
                self._log_ui(
                    f"Start queued ~{wait_ms}ms — releasing COM port after last Stop."
                )
                QtCore.QTimer.singleShot(wait_ms, self._start_bridge_after_cooldown)
            return
        self._start_bridge_impl()

    def _start_bridge_after_cooldown(self) -> None:
        self._start_defer_pending = False
        self.start_bridge()

    def _start_bridge_impl(self) -> None:
        if self._should_apply_hub_for_start():
            self._apply_hub_selection_for_start()
        err = self._validate_before_start()
        if err:
            self._log_ui(err)
            QtWidgets.QMessageBox.warning(self, "Cannot start", err)
            return
        self._starting = True
        self._sync_preset_action_buttons()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        com = self.com_cb.currentText().strip()
        try:
            baud = int(read_baud_widget(self.baud_edit))
            if baud <= 0:
                raise ValueError("baud must be positive")
        except ValueError:
            self._clear_stale_start_ui()
            self._log_ui("Invalid baud rate — enter a positive number (e.g. 115200).")
            QtWidgets.QMessageBox.warning(self, "Cannot start", "Enter a valid baud rate.")
            return
        self.refresh_ports()
        preflight_err = self._preflight_com(com, baud)
        if preflight_err:
            self._clear_stale_start_ui()
            self._focus_connect_tab()
            msg = self._compose_com_preflight_error(com, preflight_err)
            self._log_ui(f"[Start preflight] {preflight_err}")
            QtWidgets.QMessageBox.warning(self, "Cannot start", msg)
            return

        if self.chk_file_log.isChecked():
            try:
                fl = load_file_log_prefs()
                self._file_log = _FileSurveyLog(
                    Path(self.file_log_path.text().strip()),
                    max_bytes=int(fl["max_mb"]) * 1024 * 1024,
                    backup_count=int(fl["backups"]),
                )
            except Exception as e:
                self._log_ui(f"File log error: {e}")
                QtWidgets.QMessageBox.warning(self, "File log", f"Could not open log file:\n{e}")
                self._file_log = None
        else:
            self._file_log = None

        udp_listen = None
        udp_remote = None
        mode: NetMode
        tcp_reconnect = self.tcp_reconnect_spin.value()

        try:
            if self.rb_udp_listen.isChecked():
                mode = NetMode.UDP_LISTEN
                udp_listen = (self.udp_host.text().strip(), _parse_port(self.udp_port.text(), "UDP port"))
            elif self.rb_udp_remote.isChecked():
                mode = NetMode.UDP_REMOTE
                host = self.remote_host.text().strip()
                if not host:
                    raise ValueError("UDP remote host is required")
                udp_remote = (host, _parse_port(self.remote_port.text(), "UDP remote port"))
            elif self.rb_tcp_server.isChecked():
                mode = NetMode.TCP_SERVER
                tcp_bh = self.tcp_srv_host.text().strip()
                tcp_bp = _parse_port(self.tcp_srv_port.text(), "TCP server port")
            else:
                mode = NetMode.TCP_CLIENT
                tcp_ch = self.tcp_cli_host.text().strip()
                if not tcp_ch:
                    raise ValueError("TCP client host is required")
                tcp_cp = _parse_port(self.tcp_cli_port.text(), "TCP client port")
        except ValueError as e:
            self._clear_stale_start_ui()
            self._log_ui(str(e))
            QtWidgets.QMessageBox.warning(self, "Cannot start", str(e))
            return

        if self._worker and self._worker.isRunning():
            self._clear_stale_start_ui()
            self._log_ui("Stop the bridge before starting again.")
            return

        file_log = self._file_log
        nmea_mode = self._selected_nmea_mode()
        nmea_filter = self._selected_nmea_filter()
        verbose = self.chk_verbose_log.isChecked
        log_hex = getattr(self, "chk_log_hex", None) is not None and self.chk_log_hex.isChecked()
        _fanout_chk = getattr(self, "chk_udp_fanout", None)
        udp_fanout = _fanout_chk is None or _fanout_chk.isChecked()

        from bridge_core import TcpSinkConfig

        tcp_sink: Optional[TcpSinkConfig] = None
        sink_chk = getattr(self, "chk_tcp_sink_enable", None)
        if sink_chk is not None and sink_chk.isChecked():
            try:
                sink_port = int(self.tcp_sink_port.text().strip())
                if sink_port <= 0 or sink_port > 65535:
                    raise ValueError("Extra TCP output port must be 1–65535")
            except ValueError as e:
                self._clear_stale_start_ui()
                self._log_ui(str(e))
                QtWidgets.QMessageBox.warning(self, "Cannot start", str(e))
                return
            tcp_sink = TcpSinkConfig(enabled=True, bind_port=sink_port)

        def build(loop: asyncio.AbstractEventLoop) -> SerialNetBridge:
            common = dict(
                loop=loop,
                ui_log=self._worker.log_msg.emit,
                ui_log_verbose=verbose,
                ui_log_hex=lambda: log_hex and nmea_mode == NmeaMode.RAW,
                status_cb=self._worker.status_msg.emit,
                stats_cb=self._worker.stats_msg.emit,
                file_log=file_log,
                tcp_reconnect_delay=tcp_reconnect,
                udp_fanout=udp_fanout,
                tcp_sink=tcp_sink,
                nmea_mode=nmea_mode,
                nmea_filter=nmea_filter,
                serial_auto_reconnect=getattr(
                    self, "chk_serial_auto_reconnect", None
                )
                is None
                or self.chk_serial_auto_reconnect.isChecked(),
            )
            if mode == NetMode.TCP_SERVER:
                return SerialNetBridge(
                    com, baud, mode, tcp_bind_host=tcp_bh, tcp_bind_port=tcp_bp, **common
                )
            if mode == NetMode.TCP_CLIENT:
                return SerialNetBridge(
                    com, baud, mode, tcp_client_host=tcp_ch, tcp_client_port=tcp_cp, **common
                )
            return SerialNetBridge(
                com, baud, mode, udp_listen=udp_listen, udp_remote=udp_remote, **common
            )

        self._set_connection_locked(True)
        self._update_status_bar("Serial: starting…", "Network: starting…")
        self._set_status_banner(
            "starting",
            "Starting…",
            f"Opening {com} @ {baud} — {self._starting_network_blurb()}",
        )
        self._start_gen += 1
        gen = self._start_gen
        self._log_ui(f"Start: opening {com} @ {baud} (background thread)…")

        self._worker = BridgeAsyncThread(build)
        self._worker.log_msg.connect(self._log_ui)
        self._worker.status_msg.connect(self._update_status_bar)
        self._worker.stats_msg.connect(self._stats_from_bridge)
        self._worker.start_done.connect(lambda ok: self._on_worker_start_done(ok, gen))
        self._start_watchdog_timer.start(START_WATCHDOG_MS)
        self._worker.start()

    def _on_worker_start_done(self, ok: bool, gen: int) -> None:
        self._start_watchdog_timer.stop()
        if gen != self._start_gen:
            self._clear_stale_start_ui()
            return
        worker = self._worker
        if ok and worker and worker.bridge:
            self.bridge = worker.bridge
            self._on_bridge_started(self.bridge)
            return
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._worker = None
        self.bridge = None
        self._fail_start_ui(
            "Serial or network could not be opened. See the live log for details."
        )

    def _clear_stale_start_ui(self) -> None:
        """Reset UI when a background start was superseded (Stop, second Start, etc.)."""
        if not self._starting:
            return
        self._starting = False
        self._set_connection_locked(False)
        self.start_btn.setText("Start bridge")
        self._sync_preset_action_buttons()
        self._refresh_nmea_status_chip()

    def _fail_start_ui(self, message: str) -> None:
        self.bridge = None
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._worker.wait(2000)
        self._worker = None
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self._update_status_bar("Serial: stopped", "Network: stopped")
        self._starting = False
        self._set_status_banner("failed", "Start failed", message)
        self.start_btn.setText("Start bridge")
        self._sync_preset_action_buttons()
        QtWidgets.QMessageBox.critical(self, "Bridge failed to start", message)

    def _start_watchdog_fired(self) -> None:
        worker = self._worker
        b = self.bridge or (worker.bridge if worker else None)
        if b and b.running and b._network_ready:
            return
        self._start_gen += 1
        self._log_ui(
            "Start timed out (>15s).\n"
            "Close the app, run: python com_free.py, then launch again."
        )
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._fail_start_ui(
            "Start timed out after 15 seconds.\n\n"
            "Close any app using the COM port, run python com_free.py, then try again."
        )

    def _on_bridge_started(self, b: SerialNetBridge) -> None:
        self._starting = False
        QtCore.QTimer.singleShot(0, self._ensure_web_server_running)
        self._save_hub_last_known_good()
        self._log_tab_auto_timer.start(20_000)
        self._start_ntrip_if_enabled()
        self._reset_ui_log_serial_coalesce()
        self._record_recent_session()
        self._refresh_nmea_status_chip()
        self._sync_preset_action_buttons()
        self._set_status_banner("running", "Running", self._running_banner_detail(b))
        self.start_btn.setText("Running…")
        if b.mode == NetMode.UDP_LISTEN and b.udp_listen:
            host, port = b.udp_listen
            dest = f"127.0.0.1:{port}" if host in ("0.0.0.0", "", "::") else f"{host}:{port}"
            self._log_ui(
                "=== BRIDGE RUNNING ===\n"
                f"UDP listen {host}:{port} -> {b.com} @ {b.baud}.\n"
                "The bridge is idle until NMEA arrives — that is normal.\n"
                f"Send traffic to {dest} (e.g. python nmea_static_sample.py), or Tab 3 Send -> serial.\n"
                f"Watch paired COM (e.g. COM12) in Tera Term — not {b.com}."
            )
        else:
            self._log_ui(
                f"=== BRIDGE RUNNING === {b.com} @ {b.baud} ({b.mode.value}). "
                "Idle until data moves on the wire."
            )

    def stop_bridge(self) -> None:
        self._start_defer_pending = False
        self._start_gen += 1
        self._start_watchdog_timer.stop()
        if self._stopping:
            self._finish_stop_ui()
            return
        if self._starting and self._worker is None:
            self._clear_stale_start_ui()
            self._finish_stop_ui()
            return
        worker = self._worker
        self.bridge = None
        self._worker = None
        if not worker:
            self._finish_stop_ui()
            return

        self._stopping = True
        self._update_status_bar("Serial: stopping…", "Network: stopping…")
        self._log_ui("Stopping bridge…")
        worker.request_stop()
        worker.wait(4000)
        self._finish_stop_ui()

    def _stop_bridge(self) -> None:
        """Legacy name used by older tray/quit paths; prefer stop_bridge()."""
        self.stop_bridge()

    def _stop_timeout_guard(self) -> None:
        if not self._stopping:
            return
        self._log_ui(
            "Stop took too long — UI reset. Close Tera Term/PuTTY on the COM port, then try again."
        )
        self._finish_stop_ui()

    def _finish_stop_ui(self) -> None:
        """Re-enable controls on the Qt main thread after async stop."""
        self._bridge_stop_mono = time.monotonic()
        self._log_tab_auto_timer.stop()
        self._stop_ntrip()
        self._reset_ui_log_serial_coalesce()
        self._stop_guard_timer.stop()
        self._stopping = False
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self.stop_btn.setText("■  Stop bridge")
        self._starting = False
        self.start_btn.setText("Start bridge")
        self._set_status_banner("stopped", "Stopped", "Choose a path and Start when ready.")
        self._update_status_bar("Serial: stopped", "Network: stopped")
        self._refresh_nmea_status_chip()
        self._sync_preset_action_buttons()
        self._apply_hub_quality()
        pending = self._presets_menu_pending
        if pending:
            self._presets_menu_pending = None
            QtCore.QTimer.singleShot(
                0, lambda n=pending: self._activate_preset_by_name(n, log=True)
            )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not getattr(self, "_force_quit", False):
            tray = getattr(self, "_tray_icon", None)
            if tray is not None and self._is_bridge_running():
                event.ignore()
                self._hide_to_tray()
                return

        self._shutdown_background_services()
        self._close_auxiliary_windows()
        if getattr(self, "_layout_switch_in_progress", False):
            from ui.tray_support import destroy_tray_icon

            destroy_tray_icon(self)
            self._stop_bridge_worker_sync(2000)
            event.accept()
            return
        running = self._is_bridge_running()
        worker = self._worker
        if running or (worker and worker.isRunning()):
            if worker:
                self.bridge = None
                worker.request_stop()
                worker.wait(4000)
            self._worker = None
            self._finish_stop_ui()
            self._start_gen += 1
            if not getattr(self, "_force_quit", False):
                event.ignore()
                QtCore.QTimer.singleShot(200, self.close)
                return
        from ui.tray_support import destroy_tray_icon

        destroy_tray_icon(self)
        event.accept()
        if getattr(self, "_force_quit", False) or not self._is_bridge_running():
            self._request_application_quit()

    # ------------------------------------------------------------------
    # Auto-discovery: background GNSS device watcher
    # ------------------------------------------------------------------

    def _start_auto_discovery_thread(self) -> None:
        """Start the background USB-serial scanner (low-overhead, always on)."""
        from auto_discovery import AutoDiscoveryThread

        if getattr(self, "_auto_discovery_thread", None) is not None:
            return
        thread = AutoDiscoveryThread(parent=self)
        thread.device_detected.connect(self._on_auto_device_detected)
        thread.start()
        self._auto_discovery_thread = thread

    def _stop_auto_discovery_thread(self) -> None:
        thread = getattr(self, "_auto_discovery_thread", None)
        if thread is None:
            return
        try:
            thread.device_detected.disconnect(self._on_auto_device_detected)
        except (RuntimeError, TypeError):
            pass
        thread.stop()
        if thread.isRunning():
            thread.wait(4000)
        try:
            thread.deleteLater()
        except RuntimeError:
            pass
        self._auto_discovery_thread = None

    def _restore_auto_discover_pref(self) -> None:
        """Apply the persisted auto-discover checkbox state on startup."""
        from ui.ui_prefs import load_auto_discover_pref

        chk = getattr(self, "chk_auto_discover", None)
        if chk is None:
            return
        enabled = load_auto_discover_pref()
        chk.setChecked(enabled)
        chk.toggled.connect(self._on_auto_discover_toggled)

    def _on_auto_discover_toggled(self, enabled: bool) -> None:
        from ui.ui_prefs import save_auto_discover_pref

        save_auto_discover_pref(enabled)

    def _on_auto_device_detected(self, port_name: str) -> None:
        """Called on the Qt main thread when a GNSS device is found.

        Always refreshes the COM dropdown and selects the detected port.
        Auto-starts the bridge only when the user has opted in via the
        'Auto-connect on GNSS device detected' checkbox AND the bridge is
        currently stopped.
        """
        chk = getattr(self, "chk_auto_discover", None)
        if chk is None or not chk.isChecked():
            return

        self._log_ui(f"[AutoDiscover] GNSS device detected: {port_name}")

        # Refresh the port list so the new device appears.
        self.refresh_ports()

        # Select the detected port in the COM dropdown.
        idx = self.com_cb.findText(port_name)
        if idx >= 0:
            self.com_cb.setCurrentIndex(idx)
        else:
            self.com_cb.insertItem(0, port_name)
            self.com_cb.setCurrentIndex(0)

        # Auto-start only if bridge is idle and validation would pass.
        if self._is_bridge_running() or getattr(self, "_starting", False):
            self._log_ui(
                f"[AutoDiscover] Bridge already active — COM set to {port_name}, not restarting."
            )
            return

        err = self._validate_before_start()
        if err:
            self._log_ui(
                f"[AutoDiscover] {port_name} selected; bridge not started: {err}"
            )
            return

        self._log_ui(f"[AutoDiscover] Auto-starting bridge on {port_name}…")
        self.start_bridge()

