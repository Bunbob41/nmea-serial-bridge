"""Modern UI — persistent header + collapsible Tools sidebar + main content pane.

Layout stack (top to bottom):
  ┌─ Global Header — Start/Stop · status · pills · View/HUD/Layout ─────────┐
  ├─ Body: [Tools sidebar | main content stack]                              │
  └─ Footer strip — version ─────────────────────────────────────────────────┘

Smart-Peek: bridge start opens Activity; when live traffic arrives, auto-switch to Control for the map.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.connect_panels import configure_connect_status_banner
from ui.header_status import ElidedStatusLabel
from ui.controls import (
    create_connection_controls,
    refresh_status_bar_labels,
)
from ui.bridge_terminal import create_modern_activity_tab
from ui.mixin import BridgeLogicMixin
from ui.mission_review import create_mission_review_tab, hide_mission_review_tab
from ui.modern_header_split import (
    HEADER_SPLIT_MIN,
    ModernHeaderSplitter,
    header_split_mins,
    session_run_cluster_min_width,
    wrap_header_pane,
)
from ui.modern_styles import MODERN_TEXT, apply_modern_theme_colors
from ui.network_help import create_network_help_button
from ui.theme_choice import THEME_SLATE
from ui.view_menu import add_view_menu_section_header
from ui.tool_tabs import build_modern_tools_nav, build_modern_tools_nav_groups, build_modern_tools_nav_tiers, build_modern_tools_all_pages
from ui.ui_prefs import (
    CONFIG_PATH,
    load_hidden_tabs,
    load_modern_layout_prefs,
    save_hidden_tabs,
    save_modern_layout_prefs,
    save_tab_order,
)
from version import __version__

MODERN_SIDEBAR_EXPANDED_W = 196
MODERN_SIDEBAR_COLLAPSED_W = 52
# Side-by-side Serial/Network on Control tab down to window minimum (640px).
# Vertical stack only below this threshold — narrower than the allowed min width;
# kept for unit tests and future min-size experiments (see test_modern_control_forms_stack_narrow).
CONTROL_FORMS_STACK_BELOW_W = 520
MODERN_CHIP_RAIL_H = 48
MODERN_CHIP_BTN_H = 32
MODERN_COMPACT_STATUS_MAX_W = 220
MODERN_COMPACT_STATUS_MIN_W = 72
MODERN_COMPACT_STATUS_PAD = 26
# Open from global header only — omitted from the top chip rail to save space.
MODERN_HEADER_NAV_SIDS = frozenset({"guide"})
# Survey top bar chips that appear in the Modern global header (View / HUD / Layout).
MODERN_EMBEDDED_TOPBAR_KEYS = frozenset({"view", "hud", "ui_switch"})
# Legacy survey chips — persisted for Standard/Field but not shown in Modern header.
MODERN_EMBEDDED_TOPBAR_FORCE_HIDDEN = frozenset(
    {
        "presets",
        "recent",
        "tools",
        "ui_editor",
        "copy_stats",
        "shortcuts",
        "randomize_theme",
        "standardize_theme",
    }
)

MODERN_TOOLS_TAB_HINTS: dict[str, str] = {
    "Control": "COM, baud, UDP/TCP listen, and connection presets",
    "Presets": "Named COM/UDP path presets",
    "Hub": "Connection hub — scan, fan-out, and quick picks",
    "Fleet": "Multi-stream COM to network — up to 8 sensor pipes",
    "NMEA": "Passthrough, strict, or raw binary",
    "Theme": "Built-in palettes and per-zone colors",
    "Dashboard": "Web API, token, and QR dashboard",
    "Black box": "NMEA session capture (.nmea)",
    "File log": "Rotating bridge text log",
    "Activity": "Live wire-tap traffic, filters, pause, and save",
    "Inject": "Send test NMEA or raw bytes while Running",
    "Terminal": "Local shell for bench scripts",
    "Checks": "Automated bench checks",
    "Guide": "Operator workflows and scenario chips",
}

_MODERN_LEGACY_SECTION: dict[str, str] = {
    "Connect": "control",
    "Log": "activity",
    "Wire": "activity",
    "Tools": "presets",
    "Hub": "hub",
    "Fleet": "fleet",
    "Settings": "presets",
    "Mission Review": "mission_review",
    "Activity": "activity",
    "Control": "control",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def bridge_stats_show_live_traffic(stats: dict) -> bool:
    """True when bridge stats report wire movement (NET↔COM or inject)."""
    if not stats:
        return False
    for key in ("hz_down", "hz_up", "hz_gui", "lines_down", "lines_up"):
        try:
            if float(stats.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _vsep() -> QtWidgets.QFrame:
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    s.setObjectName("modernFooterSep")
    return s


class _ModernStatusBannerClickFilter(QtCore.QObject):
    """Left-click on the header status strip opens Control."""

    def __init__(self, opener: object, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._opener = opener

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            me = event
            if isinstance(me, QtGui.QMouseEvent) and me.button() == QtCore.Qt.MouseButton.LeftButton:
                if callable(self._opener):
                    self._opener()
                return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────

class BridgeWindowModern(BridgeLogicMixin, QtWidgets.QWidget):
    """Modern UI: persistent header above a compact command tab bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self.setProperty("uiMode", "modern")
        self._ui_mode = "modern"
        self._theme_id = THEME_SLATE
        self.setWindowTitle(f"Serial Link  v{__version__}")
        self.resize(1280, 800)
        self.setMinimumSize(560, 360)

        self._init_bridge_state()
        create_connection_controls(self)
        self._apply_modern_stylesheet()
        self._topbar_embed_in_header = True

        # ── Persistent chrome widgets ─────────────────────────────────────
        # Status banner — compact inline horizontal
        self.status_banner = QtWidgets.QFrame()
        self.status_banner.setObjectName("modernStatusBanner")
        self.status_banner.setProperty("state", "stopped")
        bl = QtWidgets.QHBoxLayout(self.status_banner)
        bl.setContentsMargins(8, 0, 8, 0)
        bl.setSpacing(4)
        self._status_capsule_dot = QtWidgets.QLabel()
        self._status_capsule_dot.setObjectName("modernStatusCapsuleDot")
        self._status_capsule_dot.setFixedSize(6, 6)
        self._status_capsule_dot.hide()
        bl.addWidget(self._status_capsule_dot, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.status_banner_text = ElidedStatusLabel()
        self.status_banner_text.setObjectName("modernStatusBannerText")
        bl.addWidget(self.status_banner_text, 1)
        configure_connect_status_banner(
            self.status_banner,
            self.status_banner_text,
            single_line=True,
        )
        self.status_banner.setMaximumHeight(30)
        self.status_banner.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.status_banner.setMinimumWidth(72)
        self._wire_modern_status_banner_nav()

        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("modernToolsLiveStatus")
        self.intent_hint.setWordWrap(False)
        self._compact_intent_hint = True

        self.start_btn.setObjectName("modernStartBtn")
        self.start_btn.setText("▶  Start")
        self.start_btn.setFixedHeight(28)
        self.start_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.stop_btn.setObjectName("modernStopBtn")
        self.stop_btn.setText("■  Stop")
        self.stop_btn.setFixedHeight(28)
        self.stop_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._session_pulse_timer = QtCore.QTimer(self)
        self._session_pulse_timer.setInterval(650)
        self._session_pulse_timer.timeout.connect(self._tick_session_pulse)
        self._build_modern_logging_indicator()

        # Status labels — updated by mixin; not shown as a dedicated tab.
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.status_nmea = QtWidgets.QLabel("NMEA: passthrough")
        self.status_nmea.setToolTip("NMEA mode for the current session.")
        self.status_gnss = QtWidgets.QLabel("GNSS: —")
        self.status_gnss.setToolTip("Live GGA fix while Running.")
        self.lbl_stats = QtWidgets.QLabel("Stopped")
        self.lbl_stats.setObjectName("lblStats")

        self.com_lock_chip.setObjectName("modernStatusPill")
        self.lbl_backup_status.setObjectName("modernStatusPill")
        self.lbl_backup_status.setProperty("pillKind", "backup")
        self.lbl_backpressure_chip = QtWidgets.QLabel("")
        self.lbl_backpressure_chip.setObjectName("modernStatusPill")
        self.lbl_backpressure_chip.setProperty("pillKind", "backpressure")
        self.lbl_backpressure_chip.setProperty("alertKind", "warn")
        self.lbl_backpressure_chip.hide()
        self.lbl_connection_health = QtWidgets.QLabel("")
        self.lbl_connection_health.setObjectName("modernStatusPill")
        self.lbl_connection_health.setProperty("pillKind", "health")
        self.lbl_connection_health.setProperty("healthKind", "idle")

        # Hidden statusBar — mixin compat only
        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusBar.setMaximumHeight(0)
        self.statusBar.setVisible(False)

        # ── Global Header Strip (persistent) ──────────────────────────────
        global_hdr = self._build_global_header()

        # ── Sidebar + main content (no top-level Activity/Control/Tools tabs) ─
        workspace = self._build_modern_workspace(
            activity_panel=create_modern_activity_tab(self),
            control_panel=self._build_control_tab(),
            mission_panel=create_mission_review_tab(self),
        )

        self._build_modern_tools_chip_rail_shell()
        self._setup_modern_ui_editor_catalogs()
        self._restore_active_section()

        footer = self._build_status_footer()

        shell = QtWidgets.QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(global_hdr, 0)
        shell.addWidget(self._modern_tools_chip_rail, 0)
        shell.addWidget(workspace, 1)
        shell.addWidget(footer, 0)

        self._finalize_ui()
        self._load_header_bar_prefs()
        self._header_layout_timer = QtCore.QTimer(self)
        self._header_layout_timer.setSingleShot(True)
        self._header_layout_timer.setInterval(80)
        self._header_layout_timer.timeout.connect(self._apply_modern_header_layout)
        self._sync_modern_run_chrome()

        nav_mode = str(load_modern_layout_prefs().get("tools_nav_mode", "sidebar"))
        self._apply_modern_tools_nav_mode(nav_mode, persist=False)
        self._apply_header_chips_icon_mode(
            getattr(self, "_header_chips_icon_mode", "auto"), persist=False
        )
        QtCore.QTimer.singleShot(0, self._restore_modern_header_split)
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_compression)
        self._wire_modern_tools_nav_mode_menu()

        self._hub_auto_refreshed = False
        self._tools_stack.currentChanged.connect(self._on_modern_section_changed)

    # ── Global Header Strip ────────────────────────────────────────────────

    def _build_global_header(self) -> QtWidgets.QFrame:
        """Persistent strip: Start/Stop · status banner · critical alert · layout nav.

        Intentionally minimal — hz, backup, COM-lock info live in the footer stats
        line and sidebar panels to avoid header congestion.
        """
        hdr = QtWidgets.QFrame()
        hdr.setObjectName("modernGlobalHeader")
        row = QtWidgets.QHBoxLayout(hdr)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(0)

        self._session_run_cluster = QtWidgets.QWidget()
        self._session_run_cluster.setObjectName("modernSessionRunCluster")
        cluster_lay = QtWidgets.QHBoxLayout(self._session_run_cluster)
        cluster_lay.setContentsMargins(0, 0, 4, 0)
        cluster_lay.setSpacing(6)
        cluster_lay.addWidget(self.start_btn)
        cluster_lay.addWidget(self.stop_btn)
        self._session_pulse = QtWidgets.QLabel("")
        self._session_pulse.setObjectName("modernSessionPulse")
        self._session_pulse.setFixedSize(8, 8)
        self._session_pulse.setProperty("pulseOn", "true")
        self._session_pulse.hide()
        cluster_lay.addWidget(
            self._session_pulse,
            0,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )

        self._header_status_container = QtWidgets.QWidget()
        self._header_status_container.setObjectName("modernHeaderStatusContainer")
        self._header_status_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._header_status_container.setMinimumWidth(HEADER_SPLIT_MIN[1])
        status_lay = QtWidgets.QHBoxLayout(self._header_status_container)
        status_lay.setContentsMargins(0, 0, 0, 0)
        status_lay.setSpacing(0)
        status_lay.addWidget(self.status_banner, 1)

        class _StatusContainerResizeFilter(QtCore.QObject):
            def __init__(self, host: "BridgeWindowModern") -> None:
                super().__init__(host)
                self._host = host

            def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
                if event.type() == QtCore.QEvent.Type.Resize:
                    self._host._sync_modern_status_banner_width()
                return False

        self._status_container_resize_filter = _StatusContainerResizeFilter(self)
        self._header_status_container.installEventFilter(
            self._status_container_resize_filter
        )

        self._header_chip_sep = _vsep()
        self._header_chip_host = QtWidgets.QWidget()
        self._header_chip_sep.setParent(self._header_chip_host)
        self._header_chip_sep.setFixedWidth(2)
        self._header_chip_sep.hide()

        self._header_chip_host.setObjectName("modernHeaderChipHost")
        self._header_chip_host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._header_chip_host.setMinimumWidth(HEADER_SPLIT_MIN[2])
        chip_host_lay = QtWidgets.QHBoxLayout(self._header_chip_host)
        chip_host_lay.setContentsMargins(0, 0, 0, 0)
        chip_host_lay.setSpacing(0)
        self._header_chip_host.hide()
        self._header_chips_icon_only = False
        from ui.modern_tools_chips import ChipFadeEdge

        self._header_chip_fade_l = ChipFadeEdge(self._header_chip_host, side="left")
        self._header_chip_fade_r = ChipFadeEdge(self._header_chip_host, side="right")

        class _ChipHostResizeFilter(QtCore.QObject):
            def __init__(self, host: "BridgeWindowModern") -> None:
                super().__init__(host)
                self._host = host

            def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
                if event.type() == QtCore.QEvent.Type.Resize:
                    self._host._sync_modern_header_chip_compression()
                    self._host._sync_modern_header_chip_scroll()
                    self._host._sync_header_chip_fade_edges()
                return False

        self._chip_host_resize_filter = _ChipHostResizeFilter(self)
        self._header_chip_host.installEventFilter(self._chip_host_resize_filter)

        self._header_pane_trail = QtWidgets.QWidget()
        self._header_pane_trail.setObjectName("modernHeaderPaneTrail")
        self._header_pane_trail.setMinimumWidth(HEADER_SPLIT_MIN[3])
        trail_lay = QtWidgets.QHBoxLayout(self._header_pane_trail)
        trail_lay.setContentsMargins(0, 0, 0, 0)
        trail_lay.setSpacing(6)
        trail_lay.addWidget(self._logging_indicator, 0)
        trail_lay.addWidget(self.lbl_backpressure_chip, 0)
        trail_lay.addStretch(1)

        self._btn_header_phone_qr = QtWidgets.QToolButton()
        self._btn_header_phone_qr.setObjectName("modernHeaderQrBtn")
        self._btn_header_phone_qr.setText("📱")
        self._btn_header_phone_qr.setToolTip(
            "Open local dashboard in your browser (Web API on this PC)."
        )
        self._btn_header_phone_qr.setFixedSize(28, 28)
        self._btn_header_phone_qr.clicked.connect(self._on_web_open_dashboard)
        self._btn_header_phone_qr.hide()

        self._modern_header_nav = QtWidgets.QWidget()
        self._modern_header_nav.setObjectName("modernHeaderNav")
        self._modern_header_nav.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._modern_header_nav.setMinimumWidth(0)
        nav_lay = QtWidgets.QHBoxLayout(self._modern_header_nav)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(6)
        nav_lay.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        nav_lay.addWidget(self._btn_header_phone_qr, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        trail_lay.addWidget(
            self._modern_header_nav,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )

        self._header_splitter = ModernHeaderSplitter(hdr)
        split_mins = header_split_mins()
        self._header_pane_run = wrap_header_pane(
            self._session_run_cluster,
            object_name="modernHeaderPaneRun",
            min_width=split_mins[0],
        )
        self._header_pane_status = wrap_header_pane(
            self._header_status_container,
            object_name="modernHeaderPaneStatus",
            min_width=split_mins[1],
        )
        self._header_pane_chips = wrap_header_pane(
            self._header_chip_host,
            object_name="modernHeaderPaneChips",
            min_width=split_mins[2],
            stretch=True,
        )
        for pane in (
            self._header_pane_run,
            self._header_pane_status,
            self._header_pane_chips,
            self._header_pane_trail,
        ):
            self._header_splitter.addWidget(pane)
        self._header_splitter.setStretchFactor(0, 0)
        self._header_splitter.setStretchFactor(1, 0)
        self._header_splitter.setStretchFactor(2, 1)
        self._header_splitter.setStretchFactor(3, 0)
        self._header_split_save_timer = QtCore.QTimer(self)
        self._header_split_save_timer.setSingleShot(True)
        self._header_split_save_timer.setInterval(250)
        self._header_split_save_timer.timeout.connect(self._persist_modern_header_split)
        self._header_splitter.splitterMoved.connect(self._on_modern_header_split_moved)
        row.addWidget(self._header_splitter, 1)

        self._global_header_row = row

        hdr.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        hdr.setMinimumHeight(40)
        self._modern_global_header = hdr

        # ── Keep stripped widgets alive for mixin state tracking ──────────
        # They are NOT in the header layout but mixin.py still reads/writes them.
        # hz chip
        self.lbl_hz_chip = QtWidgets.QLabel("")
        self.lbl_hz_chip.setObjectName("modernStatusPill")
        self.lbl_hz_chip.setProperty("pillKind", "hz")
        self.lbl_hz_chip.setParent(self)
        self.lbl_hz_chip.hide()
        # connection health label lives on the window, not in header row
        if hasattr(self, "lbl_connection_health"):
            self.lbl_connection_health.setParent(self)
            self.lbl_connection_health.hide()
        # COM lock chip stays on the window for mixin lock-state logic
        if hasattr(self, "com_lock_chip"):
            self.com_lock_chip.setParent(self)
            self.com_lock_chip.hide()
        # Backup label stays on the window for mixin backup-state logic
        if hasattr(self, "lbl_backup_status"):
            self.lbl_backup_status.setParent(self)
            self.lbl_backup_status.hide()

        # Presets / Recent / Stats buttons — menus still work, buttons are hidden
        self._btn_header_presets = QtWidgets.QToolButton()
        self._btn_header_presets.setObjectName("modernHeaderChipBtn")
        self._btn_header_presets.setText("Presets")
        self._btn_header_presets.setToolTip(
            "Click for Tools → Presets. Arrow ▾ to load a saved preset and Start."
        )
        self._btn_header_presets.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        self._btn_header_presets.clicked.connect(
            lambda: self._open_modern_tools_section("presets")
        )
        self._modern_presets_menu = QtWidgets.QMenu(self._btn_header_presets)
        self._modern_presets_menu.triggered.connect(self._on_presets_quick_menu_triggered)
        self._btn_header_presets.setMenu(self._modern_presets_menu)
        self._btn_header_presets.setParent(self)
        self._btn_header_presets.hide()

        self._btn_header_recent = QtWidgets.QToolButton()
        self._btn_header_recent.setObjectName("modernHeaderChipBtn")
        self._btn_header_recent.setText("Recent")
        self._btn_header_recent.setToolTip(
            "Restore a recent COM + UDP + NMEA session (last 5). Stop the bridge first."
        )
        self._btn_header_recent.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self._modern_recent_menu = QtWidgets.QMenu(self._btn_header_recent)
        self._btn_header_recent.setMenu(self._modern_recent_menu)
        self._btn_header_recent.setParent(self)
        self._btn_header_recent.hide()

        self._btn_header_stats = QtWidgets.QToolButton()
        self._btn_header_stats.setObjectName("modernHeaderChipBtn")
        self._btn_header_stats.setText("Stats")
        self._btn_header_stats.setToolTip("Copy session counters or save as CSV")
        self._btn_header_stats.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self._modern_stats_menu = QtWidgets.QMenu(self._btn_header_stats)
        self._btn_header_stats.setMenu(self._modern_stats_menu)
        self._btn_header_stats.setParent(self)
        self._btn_header_stats.hide()

        return hdr

    def _embed_survey_bar_in_header(self, bar) -> None:
        """P0/P1: cluster-sized View/HUD/Layout in the global header (no spring stretch)."""
        self._sync_modern_embedded_topbar_chrome(bar)

    def _sync_header_split_chips_pane(self, top_chips: bool) -> None:
        pane = getattr(self, "_header_pane_chips", None)
        host = getattr(self, "_header_chip_host", None)
        if pane is None or host is None:
            return
        pane.setVisible(top_chips)
        host.setVisible(top_chips)
        if top_chips:
            pane.setMaximumWidth(16777215)
            pane.setMinimumWidth(HEADER_SPLIT_MIN[2])
        else:
            pane.setMinimumWidth(0)
            pane.setMaximumWidth(0)
        QtCore.QTimer.singleShot(0, self._apply_modern_header_split_sizes)

    def _restore_modern_header_split(self) -> None:
        prefs = load_modern_layout_prefs()
        sizes = list(prefs.get("header_split") or [])
        locked = bool(prefs.get("header_split_locked", False))
        splitter = getattr(self, "_header_splitter", None)
        if splitter is None:
            return
        self._header_split_unlocked = not locked
        splitter.apply_lock(unlocked=not locked)
        self._apply_modern_header_split_sizes(sizes_override=sizes)
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_scroll)
        act = getattr(self, "_act_header_resize", None)
        if act is not None:
            act.blockSignals(True)
            act.setChecked(not locked)
            act.blockSignals(False)

    def _apply_modern_header_split_sizes(
        self, sizes_override: list[int] | None = None
    ) -> None:
        splitter = getattr(self, "_header_splitter", None)
        if splitter is None:
            return
        if sizes_override is None:
            prefs = load_modern_layout_prefs()
            sizes = list(prefs.get("header_split") or [])
        else:
            sizes = list(sizes_override)
        top_chips = getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips"
        if not top_chips and len(sizes) >= 3:
            freed = max(HEADER_SPLIT_MIN[2], int(sizes[2]))
            sizes[2] = 0
            sizes[3] = max(HEADER_SPLIT_MIN[3], int(sizes[3]) + freed)
        splitter.set_clamped_sizes(sizes)
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_compression)
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_scroll)
        self._schedule_modern_header_layout()

    def _persist_modern_header_split(self) -> None:
        splitter = getattr(self, "_header_splitter", None)
        if splitter is None:
            return
        save_modern_layout_prefs(header_split=list(splitter.sizes()))

    def _on_modern_header_split_moved(self, _pos: int, _index: int) -> None:
        if not getattr(self, "_header_split_unlocked", False):
            return
        timer = getattr(self, "_header_split_save_timer", None)
        if timer is not None:
            timer.start()
        QtCore.QTimer.singleShot(0, self._sync_modern_embedded_topbar_chrome)
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_compression)

    def _apply_modern_header_split_lock(self, *, unlocked: bool, persist: bool) -> None:
        self._header_split_unlocked = bool(unlocked)
        splitter = getattr(self, "_header_splitter", None)
        if splitter is not None:
            splitter.apply_lock(unlocked=unlocked)
        if not unlocked:
            self._persist_modern_header_split()
            if persist:
                save_modern_layout_prefs(header_split_locked=True)
            QtCore.QTimer.singleShot(0, self._sync_modern_embedded_topbar_chrome)
            self._schedule_modern_header_layout()
        elif persist:
            save_modern_layout_prefs(header_split_locked=False)

    def _on_header_resize_unlock_toggled(self, checked: bool) -> None:
        self._apply_modern_header_split_lock(unlocked=bool(checked), persist=True)

    def _header_trail_leading_width(self) -> int:
        """Width of trail-pane widgets left of View/HUD/Layout (logging, alerts, QR)."""
        spacing = 6
        widgets = [
            getattr(self, "_logging_indicator", None),
            getattr(self, "lbl_backpressure_chip", None),
        ]
        visible = [w for w in widgets if w is not None and not w.isHidden()]
        if not visible:
            return 0
        total = sum(max(w.sizeHint().width(), w.minimumWidth()) for w in visible)
        total += spacing * max(0, len(visible) - 1)
        total += spacing
        return total

    def _sync_modern_header_nav_width(self, need: int, bar=None) -> None:
        """Reserve header width for View/HUD/Layout — nav must not shrink below chip content."""
        from ui.survey_top_bar import _WIDGET_SIZE_MAX

        bar = bar or getattr(self, "_survey_top_bar", None)
        nav = getattr(self, "_modern_header_nav", None)
        track = getattr(bar, "_track", None) if bar is not None else None
        if nav is None:
            return
        floor = max(
            int(need),
            int(track.minimumWidth()) if track is not None else 0,
            int(bar.expanded_bar_width()) if bar is not None else 0,
        )
        nav.setMinimumWidth(floor)
        nav.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        if track is not None:
            track.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            track.setMinimumWidth(floor)
            track.setMaximumWidth(_WIDGET_SIZE_MAX)
        trail = getattr(self, "_header_pane_trail", None)
        if trail is not None:
            from ui.modern_header_split import embedded_nav_cluster_min_width

            leading = self._header_trail_leading_width()
            trail_floor = max(floor, embedded_nav_cluster_min_width()) + leading
            trail.setMinimumWidth(trail_floor)
            trail.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )

    def _ensure_header_trail_split_width(self) -> None:
        """Grow trail splitter pane when logging/alerts need more room than saved prefs."""
        splitter = getattr(self, "_header_splitter", None)
        trail = getattr(self, "_header_pane_trail", None)
        if splitter is None or trail is None:
            return
        trail_min = trail.minimumWidth()
        sizes = list(splitter.sizes())
        if len(sizes) < 4 or sizes[3] >= trail_min:
            return
        deficit = trail_min - sizes[3]
        sizes[3] = trail_min
        from ui.modern_header_split import header_split_mins

        chip_min = header_split_mins()[2]
        sizes[2] = max(chip_min, sizes[2] - deficit)
        splitter.set_clamped_sizes(sizes)

    def _sync_header_trail_layout(self) -> None:
        """Re-measure trail extras (logging chip, etc.) so header nav is not clipped."""
        bar = getattr(self, "_survey_top_bar", None)
        if bar is not None:
            track = getattr(bar, "_track", None)
            if track is not None:
                need = max(
                    track.minimumWidth(),
                    track.sizeHint().width(),
                    bar.expanded_bar_width(),
                )
                self._sync_modern_header_nav_width(need, bar)
            else:
                from ui.modern_header_split import embedded_nav_cluster_min_width

                self._sync_modern_header_nav_width(embedded_nav_cluster_min_width())
        else:
            from ui.modern_header_split import embedded_nav_cluster_min_width

            self._sync_modern_header_nav_width(embedded_nav_cluster_min_width())
        self._ensure_header_trail_split_width()

    def _sync_modern_embedded_topbar_chrome(self, bar=None) -> None:
        """Keep only View/HUD/Layout in the header; re-apply after UI editor saves."""
        bar = bar or getattr(self, "_survey_top_bar", None)
        if bar is None:
            return
        try:
            bar._hidden.update(MODERN_EMBEDDED_TOPBAR_FORCE_HIDDEN)
            # Never leave the embedded header cluster empty after a prefs edit.
            if not [
                k
                for k in MODERN_EMBEDDED_TOPBAR_KEYS
                if k not in bar._hidden and k in bar._chips
            ]:
                bar._hidden -= MODERN_EMBEDDED_TOPBAR_KEYS
                bar._hidden.update(MODERN_EMBEDDED_TOPBAR_FORCE_HIDDEN)
        except AttributeError:
            pass
        bar._chip_weights.clear()
        bar.set_layout_mode("cluster")
        bar.set_interactive_chrome(False)
        bar._track_lay.setSpacing(4)
        bar._track_lay.setContentsMargins(0, 0, 0, 0)
        host = self._modern_header_nav
        if host is None:
            return
        nav_lay = host.layout()
        if not isinstance(nav_lay, QtWidgets.QHBoxLayout):
            return
        track = getattr(bar, "_track", None)
        if track is not None:
            if track.parent() is not host:
                bar.embed_track_in(host, nav_lay)
            elif nav_lay.indexOf(track) < 0:
                nav_lay.addWidget(track, 0)
        bar.set_host_window(self)
        bar.set_cluster_width_callback(
            lambda need, _bar=bar: self._sync_modern_header_nav_width(need, _bar)
        )
        bar.rebuild()
        self._apply_modern_header_nav_button_palettes(bar)
        track = getattr(bar, "_track", None)
        if track is not None:
            need = max(track.minimumWidth(), track.sizeHint().width(), bar.expanded_bar_width())
            self._sync_modern_header_nav_width(need, bar)
        QtCore.QTimer.singleShot(0, self._sync_header_trail_layout)

    def _apply_modern_header_nav_button_palettes(self, bar=None) -> None:
        """Fusion on some Windows builds ignores QSS text color — set palette too."""
        bar = bar or getattr(self, "_survey_top_bar", None)
        track = getattr(bar, "_track", None) if bar is not None else None
        if track is None:
            return
        color = QtGui.QColor(MODERN_TEXT)
        for btn in track.findChildren(QtWidgets.QToolButton):
            pal = btn.palette()
            pal.setColor(QtGui.QPalette.ColorRole.ButtonText, color)
            pal.setColor(QtGui.QPalette.ColorRole.WindowText, color)
            btn.setPalette(pal)

    def _ensure_modern_nav_visible(self) -> None:
        """After layout edits, keep chip rail or sidebar navigation on screen."""
        mode = getattr(self, "_modern_tools_nav_mode", "top_chips")
        chip_rail = getattr(self, "_modern_tools_chip_rail", None)
        chip_count = len(getattr(self, "_tools_chip_buttons", [])) + len(
            getattr(self, "_tools_chip_dropdowns", [])
        )
        if mode == "top_chips" and chip_count == 0:
            self._apply_modern_tools_nav_mode("sidebar", persist=True)
            return
        self._apply_modern_tools_nav_mode(mode, persist=False)

    def _ensure_modern_launch_layout(self) -> None:
        """First show: reserve header height and keep the window on-screen."""
        hdr = getattr(self, "_modern_global_header", None)
        if hdr is not None:
            hdr.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            row_h = max(
                40,
                hdr.sizeHint().height(),
                self.start_btn.sizeHint().height() + 8,
            )
            hdr.setMinimumHeight(row_h)
            hdr.updateGeometry()

        self._sync_modern_status_banner_width()
        QtCore.QTimer.singleShot(0, self._restore_modern_header_split)
        QtCore.QTimer.singleShot(50, self._sync_modern_header_chip_compression)
        QtCore.QTimer.singleShot(50, self._sync_modern_header_chip_scroll)

        nav = getattr(self, "_modern_header_nav", None)
        if nav is not None:
            nav.setMinimumHeight(28)

        bar = getattr(self, "_survey_top_bar", None)
        if bar is not None:
            bar.set_host_window(self)
            bar._schedule_spring_layout()

        screen = self.screen() or QtGui.QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if not getattr(self, "_modern_launch_geometry_set", False):
                self._modern_launch_geometry_set = True
                w = min(max(self.width(), int(self.minimumWidth())), avail.width())
                h = min(max(self.height(), int(self.minimumHeight())), avail.height())
                x = avail.x() + max(0, (avail.width() - w) // 2)
                y = avail.y() + max(0, (avail.height() - h) // 16)
                self.setGeometry(x, y, w, h)
            else:
                fg = self.frameGeometry()
                x, y = fg.x(), fg.y()
                if fg.top() < avail.top():
                    y = avail.top()
                if fg.left() < avail.left():
                    x = avail.left()
                if x != fg.x() or y != fg.y():
                    self.move(x, y)

        lay = self.layout()
        if isinstance(lay, QtWidgets.QVBoxLayout):
            lay.activate()
        self.updateGeometry()
        refresh_status_bar_labels(self)

    # ── Hub one-shot auto-discovery ───────────────────────────────────────

    def _on_modern_tab_changed(self, index: int) -> None:
        """Reserved for tab-change hooks (Hub auto-scan runs from Tools nav)."""
        _ = index

    def _maybe_hub_auto_refresh(self) -> None:
        if getattr(self, "_hub_auto_refreshed", False):
            return
        self._hub_auto_refreshed = True
        QtCore.QTimer.singleShot(150, self._on_hub_refresh_discovery)

    # ── Tab content builders ──────────────────────────────────────────────

    def _build_control_tab(self) -> QtWidgets.QWidget:
        from ui.control_map import build_control_map_panel
        from ui.tool_tabs import _modern_flat_page
        from ui.ui_prefs import load_modern_layout_prefs

        outer, content_lay = _modern_flat_page(
            "modernControlTab",
            "Control",
            subtitle=(
                "COM port, baud, and network listen path — match Presets or pick a Hub tile before Start."
            ),
            icon="🎛",
        )
        content_lay.setSpacing(14)

        self._control_serial_group = self._build_serial_group()
        self._control_network_group = self._build_network_group()
        self._control_forms_host = QtWidgets.QWidget()
        self._control_forms_host.setObjectName("modernControlFormsHost")
        self._control_forms_host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._control_forms_grid = QtWidgets.QGridLayout(self._control_forms_host)
        self._control_forms_grid.setContentsMargins(0, 0, 0, 0)
        self._control_forms_grid.setHorizontalSpacing(14)
        self._control_forms_grid.setVerticalSpacing(14)
        self._control_forms_grid.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._control_forms_grid.addWidget(
            self._control_serial_group, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._control_forms_grid.addWidget(
            self._control_network_group, 0, 1, QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._control_forms_vertical = False
        content_lay.addWidget(self._control_forms_host, 0)

        preset_bar = QtWidgets.QFrame()
        preset_bar.setObjectName("modernControlPresetBar")
        preset_lay = QtWidgets.QHBoxLayout(preset_bar)
        preset_lay.setContentsMargins(14, 10, 14, 10)
        preset_lay.setSpacing(8)
        preset_icon = QtWidgets.QLabel("📌")
        preset_icon.setObjectName("modernControlPresetIcon")
        preset_lay.addWidget(preset_icon, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        preset_lay.addWidget(self.intent_hint, 1)
        self._control_preset_bar = preset_bar

        map_card, self.control_position_map = build_control_map_panel(
            self,
            on_layout_change=self._sync_control_tab_map_layout,
        )
        self._control_map_card = map_card

        self._control_split_host = QtWidgets.QWidget()
        self._control_split_host.setObjectName("modernControlSplitHost")
        split_lay = QtWidgets.QHBoxLayout(self._control_split_host)
        split_lay.setContentsMargins(0, 0, 0, 0)
        split_lay.setSpacing(14)

        self._control_left_col = QtWidgets.QWidget()
        left_lay = QtWidgets.QVBoxLayout(self._control_left_col)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(14)
        left_lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        left_lay.addWidget(self._control_forms_host, 1)
        left_lay.addWidget(preset_bar, 0)

        self._control_right_col = QtWidgets.QWidget()
        right_lay = QtWidgets.QVBoxLayout(self._control_right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(map_card, 0)
        self._control_map_bottom_spacer = QtWidgets.QWidget()
        self._control_map_bottom_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        right_lay.addWidget(self._control_map_bottom_spacer, 1)
        self._control_map_right_lay = right_lay

        split_lay.addWidget(self._control_left_col, 45)
        split_lay.addWidget(self._control_right_col, 55)
        content_lay.addWidget(self._control_split_host, 1)

        self._control_tab_lay = content_lay
        self._control_split_horizontal = True
        collapsed = bool(load_modern_layout_prefs().get("control_map_collapsed", False))
        self._sync_control_tab_map_layout(collapsed)

        QtCore.QTimer.singleShot(0, self._apply_control_forms_responsive)
        return outer

    def _apply_intent_hint_display(self) -> None:
        super()._apply_intent_hint_display()
        from ui.modern_live_status import apply_modern_live_status

        hint = self.intent_hint
        full = (hint.toolTip() or self._intent_hint_text() or "").strip()
        visible = hint.isVisible() and bool(hint.text().strip())
        if visible:
            apply_modern_live_status(
                hint,
                hint.text(),
                full,
                summary_kind="ok",
                status_kind="ok",
            )
        bar = getattr(self, "_control_preset_bar", None)
        if bar is not None:
            bar.setVisible(visible)

    def _apply_control_forms_responsive(self, width: int | None = None) -> None:
        """Stack Serial/Network vertically on narrow windows; collapse split below min width."""
        grid = getattr(self, "_control_forms_grid", None)
        serial = getattr(self, "_control_serial_group", None)
        network = getattr(self, "_control_network_group", None)
        split_host = getattr(self, "_control_split_host", None)
        left_col = getattr(self, "_control_left_col", None)
        right_col = getattr(self, "_control_right_col", None)
        map_card = getattr(self, "_control_map_card", None)
        tab_lay = getattr(self, "_control_tab_lay", None)
        if grid is None or serial is None or network is None:
            return
        win_w = width if width is not None else self.width()
        stack_vertical = win_w < CONTROL_FORMS_STACK_BELOW_W
        use_split = win_w >= 720

        if split_host is not None and left_col is not None and right_col is not None and map_card is not None and tab_lay is not None:
            if use_split != getattr(self, "_control_split_horizontal", True):
                tab_lay.removeWidget(split_host)
                if use_split:
                    split_lay = split_host.layout()
                    if split_lay is not None:
                        split_lay.removeWidget(left_col)
                        split_lay.removeWidget(right_col)
                        left_lay = left_col.layout()
                        if left_lay is not None:
                            left_lay.removeWidget(self._control_forms_host)
                            left_lay.removeWidget(self._control_preset_bar)
                        left_lay.addWidget(self._control_forms_host, 1)
                        left_lay.addWidget(self._control_preset_bar, 0)
                        right_lay = right_col.layout()
                        if right_lay is not None:
                            right_lay.addWidget(map_card, 1)
                        split_lay.addWidget(left_col, 45)
                        split_lay.addWidget(right_col, 55)
                    tab_lay.addWidget(split_host, 1)
                else:
                    tab_lay.addWidget(self._control_forms_host, 0)
                    tab_lay.addWidget(self._control_preset_bar, 0)
                    tab_lay.addWidget(map_card, 1)
                self._control_split_horizontal = use_split

        if stack_vertical == getattr(self, "_control_forms_vertical", False):
            QtCore.QTimer.singleShot(0, self._balance_control_form_cards)
            return

        grid.removeWidget(serial)
        grid.removeWidget(network)
        if stack_vertical:
            grid.addWidget(serial, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.addWidget(network, 1, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 0)
            grid.setRowStretch(0, 1)
            grid.setRowStretch(1, 0)
        else:
            grid.addWidget(serial, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.addWidget(network, 0, 1, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            grid.setRowStretch(0, 1)
            grid.setRowStretch(1, 0)
        self._control_forms_vertical = stack_vertical
        QtCore.QTimer.singleShot(0, self._balance_control_form_cards)

    def _sync_control_tab_map_layout(self, collapsed: bool) -> None:
        """Expanded map fills the column; collapsed header pins to the top via bottom spacer."""
        map_card = getattr(self, "_control_map_card", None)
        right_lay: QtWidgets.QVBoxLayout | None = getattr(self, "_control_map_right_lay", None)
        spacer = getattr(self, "_control_map_bottom_spacer", None)
        tab_lay: QtWidgets.QVBoxLayout | None = getattr(self, "_control_tab_lay", None)
        if map_card is None:
            return

        host_lay = right_lay
        if tab_lay is not None and tab_lay.indexOf(map_card) >= 0:
            host_lay = tab_lay

        if host_lay is None:
            return

        map_idx = host_lay.indexOf(map_card)
        if map_idx < 0:
            return

        if collapsed:
            host_lay.setStretch(map_idx, 0)
            if spacer is not None and host_lay is right_lay:
                spacer_idx = host_lay.indexOf(spacer)
                if spacer_idx >= 0:
                    host_lay.setStretch(spacer_idx, 1)
                    spacer.show()
            if tab_lay is not None and host_lay is tab_lay:
                host_lay.setStretch(map_idx, 0)
        else:
            host_lay.setStretch(map_idx, 1)
            if spacer is not None and host_lay is right_lay:
                spacer_idx = host_lay.indexOf(spacer)
                if spacer_idx >= 0:
                    host_lay.setStretch(spacer_idx, 0)
                    spacer.hide()
            map_card.setMinimumHeight(160)
        map_card.updateGeometry()

    def _wrap_live_activity_page(self, panel: QtWidgets.QWidget) -> QtWidgets.QWidget:
        host = QtWidgets.QWidget()
        host.setObjectName("modernLiveActivityPage")
        lay = QtWidgets.QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(panel, 1)
        return host

    def _build_modern_workspace(
        self,
        *,
        activity_panel: QtWidgets.QWidget,
        control_panel: QtWidgets.QWidget,
        mission_panel: QtWidgets.QWidget,
    ) -> QtWidgets.QWidget:
        from ui.tool_tabs import (
            build_modern_automated_checks_page,
            build_modern_black_box_page,
            build_modern_file_log_page,
            build_modern_fleet_page,
            build_modern_guide_page,
            build_modern_hub_page,
            build_modern_inject_page,
            build_modern_nmea_page,
            build_modern_phone_page,
            build_modern_presets_page,
            build_modern_terminal_page,
            build_modern_theme_page,
            build_modern_tools_nav,
            build_modern_tools_nav_groups,
        )

        live_activity = self._wrap_live_activity_page(activity_panel)
        page_builders = {
            "control": lambda: control_panel,
            "hub": lambda: build_modern_hub_page(self),
            "fleet": lambda: build_modern_fleet_page(self),
            "presets": lambda: build_modern_presets_page(self),
            "nmea": lambda: build_modern_nmea_page(self),
            "theme": lambda: build_modern_theme_page(self),
            "phone": lambda: build_modern_phone_page(self),
            "black_box": lambda: build_modern_black_box_page(self),
            "file_log": lambda: build_modern_file_log_page(self),
            "activity": lambda: live_activity,
            "inject": lambda: build_modern_inject_page(self),
            "terminal": lambda: build_modern_terminal_page(self),
            "checks": lambda: build_modern_automated_checks_page(self),
            "guide": lambda: build_modern_guide_page(self),
        }

        outer = QtWidgets.QWidget()
        outer.setObjectName("modernWorkspace")
        root = QtWidgets.QHBoxLayout(outer)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        nav_inner = QtWidgets.QWidget()
        nav_inner.setObjectName("modernSettingsSidebarInner")
        self._modern_tools_sidebar_inner = nav_inner
        sb_lay = QtWidgets.QVBoxLayout(nav_inner)
        sb_lay.setContentsMargins(0, 8, 0, 8)
        sb_lay.setSpacing(2)

        # ── Sidebar top strip: "TOOLS" label + collapse button ────────
        _top_row = QtWidgets.QWidget()
        _top_row.setObjectName("modernSidebarTopStrip")
        _top_lay = QtWidgets.QHBoxLayout(_top_row)
        _top_lay.setContentsMargins(8, 0, 4, 0)
        _top_lay.setSpacing(0)
        self._modern_nav_header = QtWidgets.QLabel("TOOLS")
        self._modern_nav_header.setObjectName("modernSettingsNavHeader")
        _top_lay.addWidget(self._modern_nav_header, 1)
        _collapse_btn_top = QtWidgets.QToolButton()
        _collapse_btn_top.setObjectName("modernSidebarCollapseBtn")
        _collapse_btn_top.setToolTip("Collapse sidebar to icons only")
        _collapse_btn_top.setAutoRaise(True)
        _collapse_btn_top.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        _collapse_btn_top.clicked.connect(self._toggle_modern_sidebar_collapsed)
        self._modern_sidebar_collapse_btn = _collapse_btn_top
        _top_lay.addWidget(_collapse_btn_top)
        sb_lay.addWidget(_top_row)
        sb_lay.addSpacing(2)

        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setObjectName("modernSettingsSidebar")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._modern_sidebar_scroll = sidebar_scroll

        stack = QtWidgets.QStackedWidget()
        stack.setObjectName("modernSettingsStack")

        nav_groups = build_modern_tools_nav_groups()
        nav_flat = build_modern_tools_nav()
        nav_buttons: list[QtWidgets.QPushButton] = []
        group_headers: list[QtWidgets.QLabel] = []
        self._tools_section_index = {}
        self._modern_sid_by_stack_index: dict[int, str] = {}

        nav_idx = 0
        for group_idx, (group_label, items) in enumerate(nav_groups):
            if group_idx > 0:
                sb_lay.addSpacing(6)
            grp_hdr = QtWidgets.QLabel(group_label.upper())
            grp_hdr.setObjectName("modernSettingsNavGroup")
            group_headers.append(grp_hdr)
            sb_lay.addWidget(grp_hdr)
            for sid, lbl, icon in items:
                stack.addWidget(page_builders[sid]())
                self._tools_section_index[sid] = nav_idx
                self._modern_sid_by_stack_index[nav_idx] = sid
                btn = self._modern_tools_nav_button(lbl, icon, nav_idx, nav_buttons, stack)
                nav_buttons.append(btn)
                sb_lay.addWidget(btn)
                nav_idx += 1

        if "guide" not in self._tools_section_index:
            stack.addWidget(page_builders["guide"]())
            self._tools_section_index["guide"] = nav_idx
            self._modern_sid_by_stack_index[nav_idx] = "guide"
            nav_idx += 1

        stack.addWidget(mission_panel)
        self._mission_review_stack_index = nav_idx
        self._modern_sid_by_stack_index[nav_idx] = "mission_review"

        sb_lay.addStretch(1)
        sidebar_scroll.setWidget(nav_inner)
        self._tools_nav_buttons = nav_buttons
        self._modern_nav_group_headers = group_headers

        sep = QtWidgets.QFrame()
        sep.setObjectName("modernSettingsSep")
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self._modern_sidebar_sep = sep

        root.addWidget(sidebar_scroll, 0)
        root.addWidget(sep, 0)
        root.addWidget(stack, 1)

        self._tools_stack = stack
        self._modern_bench_presets = stack.widget(self._tools_section_index.get("presets", 0))

        collapsed = bool(load_modern_layout_prefs().get("sidebar_collapsed", False))
        self._apply_modern_sidebar_collapsed(collapsed, persist=False)

        default_sid = "activity"
        if default_sid in self._tools_section_index:
            self._open_modern_section_by_sid(default_sid, save=False)
        elif nav_buttons:
            self._tools_nav_select(0)

        if hasattr(self, "_refresh_tools_page_status"):
            self._refresh_tools_page_status()
        return outer

    def _build_modern_tools_chip_rail_shell(self) -> None:
        from ui.modern_tools_chips import ModernToolsChipScrollArea

        frame = QtWidgets.QFrame()
        frame.setObjectName("modernToolsChipRail")
        frame.setFixedHeight(MODERN_CHIP_RAIL_H)
        frame.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        outer_lay = QtWidgets.QHBoxLayout(frame)
        outer_lay.setContentsMargins(10, 8, 10, 8)
        outer_lay.setSpacing(8)

        self._modern_tools_chip_rail_label = QtWidgets.QLabel("TOOLS")
        self._modern_tools_chip_rail_label.setObjectName("modernToolsChipRailLabel")
        self._modern_tools_chip_rail_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        outer_lay.addWidget(self._modern_tools_chip_rail_label, 0)

        scroll = ModernToolsChipScrollArea(frame)
        scroll.setMinimumWidth(0)
        scroll.setFixedHeight(MODERN_CHIP_BTN_H)
        inner = QtWidgets.QWidget()
        inner.setObjectName("modernToolsChipInner")
        inner.setMinimumWidth(0)
        inner.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        inner.setFixedHeight(MODERN_CHIP_BTN_H)
        row = QtWidgets.QHBoxLayout(inner)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        scroll.setWidget(inner)
        outer_lay.addWidget(scroll, 1)

        self._modern_tools_chip_rail = frame
        self._modern_tools_chip_scroll = scroll
        self._modern_tools_chip_inner = inner
        self._tools_chip_buttons: list[QtWidgets.QPushButton] = []
        self._tools_chip_dropdowns: list[QtWidgets.QToolButton] = []
        frame.hide()

    def _sync_modern_nav_highlight(self, index: int) -> None:
        """Keep sidebar + chip nav visually in sync with the content stack."""
        sid_by_index = getattr(self, "_modern_sid_by_stack_index", {})
        active_sid = sid_by_index.get(index, "")

        for btn in getattr(self, "_tools_nav_buttons", []):
            try:
                nav_idx = int(btn.property("navIndex"))
            except (TypeError, ValueError):
                continue
            active = nav_idx == index
            btn.setProperty("navActive", active)
            if btn.objectName() == "modernSettingsNavBtn":
                btn.setChecked(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        for btn in getattr(self, "_tools_chip_buttons", []):
            try:
                nav_idx = int(btn.property("navIndex"))
            except (TypeError, ValueError):
                continue
            active = nav_idx == index
            btn.setProperty("navActive", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        from ui.modern_tools_chips import apply_embedded_header_dropdown_style

        compact = getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips"
        icon_only = self._resolve_header_chips_icon_only()
        for btn in getattr(self, "_tools_chip_dropdowns", []):
            child_sids = btn.property("navChildSids")
            if not isinstance(child_sids, list):
                child_sids = []
            active = active_sid in child_sids
            btn.setProperty("navActive", active)
            btn.setProperty("navActiveChildSid", active_sid if active else "")
            active_icon = ""
            active_label = ""
            if active and active_sid:
                icon_by_label = getattr(self, "_modern_tools_icon_by_label", {})
                for lbl, sid in getattr(self, "_modern_tools_sid_by_label", {}).items():
                    if sid == active_sid:
                        active_icon = icon_by_label.get(lbl, "")
                        active_label = lbl
                        break
            apply_embedded_header_dropdown_style(
                btn,
                compact=compact,
                icon_only=icon_only,
                active_icon=active_icon,
                active_label=active_label,
            )
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _cycle_modern_tools_dropdown(self, tier_key: str, child_sids: list[str]) -> None:
        """Main chip click: advance to the next visible child in this tier."""
        if not child_sids:
            return
        section_index = getattr(self, "_tools_section_index", {})
        stack = getattr(self, "_tools_stack", None)
        if stack is None:
            return
        cur_idx = stack.currentIndex()
        current_sid = ""
        for sid in child_sids:
            if section_index.get(sid, -1) == cur_idx:
                current_sid = sid
                break
        if current_sid and current_sid in child_sids:
            next_i = (child_sids.index(current_sid) + 1) % len(child_sids)
            next_sid = child_sids[next_i]
        else:
            next_sid = child_sids[0]
        self._open_modern_section_by_sid(next_sid)

    def _tools_nav_select(
        self,
        index: int,
        buttons: list | None = None,
        stack: QtWidgets.QStackedWidget | None = None,
    ) -> None:
        stack = stack or getattr(self, "_tools_stack", None)
        if stack is None:
            return
        try:
            stack.setCurrentIndex(index)
            self._sync_modern_nav_highlight(index)
            hub_idx = getattr(self, "_tools_section_index", {}).get("hub", -1)
            if index == hub_idx:
                self._maybe_hub_auto_refresh()
            self._save_active_section()
        except Exception:
            pass

    def _open_modern_section_by_sid(self, sid: str, *, save: bool = True) -> None:
        key = sid.lower().strip().replace(" ", "_").replace("-", "_")
        aliases = {
            "hub": "hub",
            "connection_hub": "hub",
            "fleet": "fleet",
            "multi_stream": "fleet",
            "remote": "phone",
            "bench": "checks",
            "automated_checks": "checks",
            "local_backup": "black_box",
            "blackbox": "black_box",
            "filelog": "file_log",
            "screen_log": "file_log",
            "clear_view": "activity",
            "clear": "activity",
            "activity_panel": "activity",
            "logging": "activity",
            "mission_review": "mission_review",
        }
        target = aliases.get(key, key)
        stack = getattr(self, "_tools_stack", None)
        buttons = getattr(self, "_tools_nav_buttons", None)
        if stack is None:
            return
        if target == "mission_review":
            idx = getattr(self, "_mission_review_stack_index", -1)
            if idx >= 0:
                stack.setCurrentIndex(idx)
                if save:
                    self._save_active_section()
            return
        section_idx = getattr(self, "_tools_section_index", {}).get(target)
        if section_idx is None:
            return
        if buttons is not None:
            self._tools_nav_select(section_idx)
        else:
            stack.setCurrentIndex(section_idx)
            if save:
                self._save_active_section()

    def _open_modern_tools_section(self, section: str, *, focus: str | None = None) -> None:
        """Jump to a sidebar section (Control, Activity, Hub, …)."""
        if focus == "presets":
            self._open_modern_section_by_sid("presets")
            return
        self._open_modern_section_by_sid(section)

    def _toggle_modern_sidebar_collapsed(self) -> None:
        collapsed = not bool(getattr(self, "_modern_sidebar_collapsed", False))
        self._apply_modern_sidebar_collapsed(collapsed, persist=True)

    def _detach_widget_from_layout(self, widget: QtWidgets.QWidget) -> None:
        parent = widget.parentWidget()
        if parent is None:
            return
        lay = parent.layout()
        if lay is not None:
            lay.removeWidget(widget)

    def _header_chips_avail_width(self) -> int:
        pane = getattr(self, "_header_pane_chips", None)
        host = getattr(self, "_header_chip_host", None)
        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        if host is None or not host.isVisible():
            return 0
        candidates = [host.width()]
        if pane is not None and pane.isVisible():
            candidates.append(pane.width())
        if scroll is not None:
            candidates.append(scroll.viewport().width())
        return max(0, max(candidates) - 4)

    def _header_chips_labeled_width(self) -> int:
        from ui.modern_tools_chips import estimate_embedded_chips_row_width

        buttons = getattr(self, "_tools_chip_buttons", [])
        dropdowns = getattr(self, "_tools_chip_dropdowns", [])
        inner = getattr(self, "_modern_tools_chip_inner", None)
        spacing = 4
        if inner is not None:
            lay = inner.layout()
            if lay is not None:
                spacing = lay.spacing()
        return estimate_embedded_chips_row_width(
            buttons,
            dropdowns,
            icon_only=False,
            spacing=spacing,
        )

    def _resolve_header_chips_icon_only(self) -> bool:
        mode = getattr(self, "_header_chips_icon_mode", "auto")
        if mode == "icons":
            return True
        if mode == "labels":
            return False
        from ui.modern_tools_chips import should_use_header_icon_only

        avail = self._header_chips_avail_width()
        labeled = self._header_chips_labeled_width()
        return should_use_header_icon_only(
            avail,
            labeled,
            currently_icon_only=bool(getattr(self, "_header_chips_icon_only", False)),
        )

    def _header_status_width_needed(self) -> int:
        from ui.modern_header_layout import compact_status_display, measure_status_capsule_width

        label = self.status_banner_text
        compact = getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips"
        if compact:
            state = str(self.status_banner.property("state") or "stopped")
            if isinstance(label, ElidedStatusLabel):
                title, _detail = label.full_text().split(" · ", 1) if " · " in label.full_text() else (label.full_text(), "")
            else:
                title = str(label.text() or "Stopped")
            display = compact_status_display(state, title)
        elif isinstance(label, ElidedStatusLabel):
            display = label.full_text() or "Stopped"
        else:
            display = str(label.text() or "Stopped")
        return measure_status_capsule_width(
            label,
            display,
            include_dot=compact,
        )

    def _load_header_bar_prefs(self) -> None:
        from ui.header_bar_prefs import normalize_header_chips_icon_mode

        prefs = load_modern_layout_prefs()
        self._header_chips_icon_mode = normalize_header_chips_icon_mode(
            prefs.get("header_chips_icon_mode")
        )
        raw_icons = prefs.get("header_chip_icons")
        self._header_chip_icons = (
            {str(k): str(v) for k, v in raw_icons.items()}
            if isinstance(raw_icons, dict)
            else {}
        )

    def _schedule_modern_header_layout(self) -> None:
        if getattr(self, "_header_split_unlocked", False):
            return
        timer = getattr(self, "_header_layout_timer", None)
        if timer is not None:
            timer.start()

    def _apply_modern_header_layout(self) -> None:
        if getattr(self, "_header_split_unlocked", False):
            return
        if getattr(self, "_modern_tools_nav_mode", "sidebar") != "top_chips":
            return
        splitter = getattr(self, "_header_splitter", None)
        if splitter is None or splitter.width() <= 80:
            return

        from ui.modern_header_layout import apply_plan_sizes, compact_status_display, plan_header_layout
        from ui.modern_header_split import embedded_nav_cluster_min_width
        from ui.modern_tools_chips import estimate_embedded_chips_row_width

        label = self.status_banner_text
        state = str(self.status_banner.property("state") or "stopped")
        if isinstance(label, ElidedStatusLabel):
            raw = label.full_text() or "stopped"
            title = raw.split(" · ", 1)[0] if " · " in raw else raw
        else:
            title = str(label.text() or "stopped")
        status_display = compact_status_display(state, title)

        buttons = getattr(self, "_tools_chip_buttons", [])
        dropdowns = getattr(self, "_tools_chip_dropdowns", [])
        chips_labeled = estimate_embedded_chips_row_width(buttons, dropdowns, icon_only=False)
        chips_icon = estimate_embedded_chips_row_width(buttons, dropdowns, icon_only=True)
        phone = getattr(self, "_btn_header_phone_qr", None)
        phone_w = (
            phone.width() + 6
            if phone is not None and phone.isVisible()
            else 0
        )
        trail_need = embedded_nav_cluster_min_width() + phone_w + self._header_trail_leading_width()
        nav = getattr(self, "_modern_header_nav", None)
        if nav is not None:
            trail_need = max(trail_need, nav.minimumWidth() + self._header_trail_leading_width() + 8)

        plan = plan_header_layout(
            splitter.width(),
            run_cluster=self._session_run_cluster,
            status_display=status_display,
            status_label=label,
            chips_labeled_w=chips_labeled,
            chips_icon_w=chips_icon,
            trail_w=trail_need,
            handle_width=splitter.handleWidth(),
            chips_icon_only=bool(getattr(self, "_header_chips_icon_only", False)),
            chips_mode=getattr(self, "_header_chips_icon_mode", "auto"),
        )

        hdr = getattr(self, "_modern_global_header", None)
        if hdr is not None:
            hdr.setProperty("headerTight", "true" if plan.header_tight else "false")
            hdr.setProperty("startCompact", "true" if plan.start_compact else "false")
            hdr.style().unpolish(hdr)
            hdr.style().polish(hdr)

        if plan.force_chips_icon_only is not None:
            self._header_chips_icon_only = plan.force_chips_icon_only
            self._apply_embedded_header_chip_styles()
            stack = getattr(self, "_tools_stack", None)
            if stack is not None:
                self._sync_modern_nav_highlight(stack.currentIndex())
        elif getattr(self, "_header_chips_icon_mode", "auto") == "auto":
            want = self._resolve_header_chips_icon_only()
            if want != bool(getattr(self, "_header_chips_icon_only", False)):
                self._header_chips_icon_only = want
                self._apply_embedded_header_chip_styles()
                stack = getattr(self, "_tools_stack", None)
                if stack is not None:
                    self._sync_modern_nav_highlight(stack.currentIndex())

        apply_plan_sizes(splitter, plan)
        self._sync_session_run_cluster_width()
        status_floor = plan.sizes[1]
        status_pane = getattr(self, "_header_pane_status", None)
        if status_pane is not None:
            status_pane.setMinimumWidth(status_floor)
        status_container = getattr(self, "_header_status_container", None)
        if status_container is not None:
            status_container.setMinimumWidth(status_floor)
            status_container.setMaximumWidth(16777215)
        banner = getattr(self, "status_banner", None)
        if banner is not None:
            banner.setMinimumWidth(max(56, status_floor - 8))
            banner.setMaximumWidth(16777215)
        if isinstance(label, ElidedStatusLabel):
            fm = label.fontMetrics()
            label.setMinimumWidth(max(52, fm.horizontalAdvance(status_display) + 4))
            label.refresh_elide()
        self._sync_modern_header_chip_scroll()
        self._sync_header_chip_fade_edges()

    def _sync_modern_header_chip_compression(self) -> None:
        """Top chips: auto icons-only when tight unless View overrides."""
        if getattr(self, "_modern_tools_nav_mode", "sidebar") != "top_chips":
            if getattr(self, "_header_chips_icon_only", False):
                self._header_chips_icon_only = False
                self._apply_embedded_header_chip_styles()
            return

        want_icon_only = self._resolve_header_chips_icon_only()
        mode = getattr(self, "_header_chips_icon_mode", "auto")
        force_apply = mode in ("icons", "labels")
        if force_apply or want_icon_only != bool(getattr(self, "_header_chips_icon_only", False)):
            self._header_chips_icon_only = want_icon_only
            self._apply_embedded_header_chip_styles()
            stack = getattr(self, "_tools_stack", None)
            if stack is not None:
                self._sync_modern_nav_highlight(stack.currentIndex())
        self._sync_modern_header_chip_scroll()
        self._schedule_modern_header_layout()

    def _sync_modern_header_chip_scroll(self, *, follow_active: bool = False) -> None:
        """Keep chip row at natural width; scroll the viewport when the pane is narrower."""
        from ui.modern_tools_chips import (
            header_chip_scroll_policy,
            reveal_active_header_chip,
            snap_header_chip_scroll,
            sync_embedded_chip_inner_width,
        )

        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        inner = getattr(self, "_modern_tools_chip_inner", None)
        if (
            scroll is None
            or inner is None
            or getattr(self, "_modern_tools_nav_mode", "sidebar") != "top_chips"
            or scroll.widget() is not inner
        ):
            return
        icon_only = bool(getattr(self, "_header_chips_icon_only", False))
        buttons = getattr(self, "_tools_chip_buttons", [])
        dropdowns = getattr(self, "_tools_chip_dropdowns", [])
        chips = (*buttons, *dropdowns)
        row_w = sync_embedded_chip_inner_width(
            inner,
            buttons,
            dropdowns,
            icon_only=icon_only,
        )
        viewport = max(scroll.viewport().width(), self._header_chips_avail_width(), 0)
        scroll.setHorizontalScrollBarPolicy(
            header_chip_scroll_policy(row_w, viewport)
        )
        overflow = row_w > viewport
        scroll.setProperty("chipOverflow", "true" if overflow else "false")
        scroll.style().unpolish(scroll)
        scroll.style().polish(scroll)
        scroll.setToolTip(
            "More tool chips — scroll horizontally or use the mouse wheel"
            if overflow
            else ""
        )
        active = None
        for btn in chips:
            if str(btn.property("navActive") or "").lower() == "true":
                active = btn
                break
        if follow_active and active is not None:
            reveal_active_header_chip(scroll, chips, active)
        else:
            scroll.horizontalScrollBar().setValue(0)
            snap_header_chip_scroll(scroll, chips)
        self._sync_header_chip_fade_edges()

    def _header_chip_fade_color(self) -> str:
        zones = getattr(self, "_theme_zone_colors", None)
        if isinstance(zones, dict):
            topbar = str(zones.get("topbar") or "").strip()
            if topbar.startswith("#"):
                return topbar
        from ui.modern_styles import MODERN_SURFACE

        return MODERN_SURFACE

    def _sync_header_chip_fade_edges(self) -> None:
        from ui.modern_tools_chips import sync_header_chip_fade_edges

        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        sync_header_chip_fade_edges(
            scroll,
            getattr(self, "_header_chip_fade_l", None),
            getattr(self, "_header_chip_fade_r", None),
            fade_color=self._header_chip_fade_color(),
        )

    def _wire_header_chip_scroll_fades(self) -> None:
        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        if scroll is None or getattr(self, "_header_chip_fades_wired", False):
            return
        bar = scroll.horizontalScrollBar()
        bar.valueChanged.connect(lambda *_: self._sync_header_chip_fade_edges())
        scrolled = getattr(scroll, "scrolled", None)
        if scrolled is not None:
            scrolled.connect(self._sync_header_chip_fade_edges)
        self._header_chip_fades_wired = True

    def _ensure_active_header_chip_visible(self) -> None:
        self._sync_modern_header_chip_scroll(follow_active=True)

    def _apply_embedded_header_chip_styles(self) -> None:
        from ui.modern_tools_chips import (
            apply_embedded_header_chip_style,
            apply_embedded_header_dropdown_style,
        )

        compact = getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips"
        icon_only = bool(getattr(self, "_header_chips_icon_only", False))
        for btn in getattr(self, "_tools_chip_buttons", []):
            apply_embedded_header_chip_style(
                btn, compact=compact, icon_only=icon_only
            )
        for btn in getattr(self, "_tools_chip_dropdowns", []):
            active_sid = str(btn.property("navActiveChildSid") or "").strip()
            active_icon = ""
            active_label = ""
            if active_sid:
                icon_by_label = getattr(self, "_modern_tools_icon_by_label", {})
                for lbl, sid in getattr(self, "_modern_tools_sid_by_label", {}).items():
                    if sid == active_sid:
                        active_icon = icon_by_label.get(lbl, "")
                        active_label = lbl
                        break
            apply_embedded_header_dropdown_style(
                btn,
                compact=compact,
                icon_only=icon_only,
                active_icon=active_icon,
                active_label=active_label,
            )
        inner = getattr(self, "_modern_tools_chip_inner", None)
        if inner is not None:
            inner.setFixedHeight(30 if compact else MODERN_CHIP_BTN_H)
            lay = inner.layout()
            if lay is not None:
                lay.setSpacing(4 if compact else 6)
        if compact:
            self._sync_modern_header_chip_scroll()
        elif inner is not None:
            inner.setMinimumWidth(0)
            inner.setMaximumWidth(16777215)
            inner.adjustSize()

    def _mount_modern_tools_nav_chrome(self, top_chips: bool) -> None:
        """Top-chips mode: embed nav chips in the global header (Termius-style single bar)."""
        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        inner = getattr(self, "_modern_tools_chip_inner", None)
        chip_rail = getattr(self, "_modern_tools_chip_rail", None)
        chip_host = getattr(self, "_header_chip_host", None)
        chip_sep = getattr(self, "_header_chip_sep", None)
        chip_label = getattr(self, "_modern_tools_chip_rail_label", None)
        status_container = getattr(self, "_header_status_container", None)
        status_banner = getattr(self, "status_banner", None)
        hdr = getattr(self, "_modern_global_header", None)
        if scroll is None or chip_rail is None or chip_host is None or inner is None:
            return

        host_lay = chip_host.layout()
        if host_lay is None:
            return

        self._detach_widget_from_layout(scroll)
        self._detach_widget_from_layout(inner)
        scroll.setWidget(None)

        if top_chips:
            chip_rail.hide()
            chip_host.setProperty("topChipsEmbedded", "true")
            chip_host.style().unpolish(chip_host)
            chip_host.style().polish(chip_host)
            if chip_sep is not None:
                chip_sep.hide()
                self._detach_widget_from_layout(chip_sep)
            chip_host.show()
            scroll.setWidget(inner)
            scroll.setWidgetResizable(False)
            scroll.setFixedHeight(30)
            scroll.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            host_lay.addWidget(scroll, 1)
            self._wire_header_chip_scroll_fades()
            if chip_label is not None:
                chip_label.hide()
            if status_container is not None:
                status_container.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                status_container.setMaximumWidth(16777215)
                status_container.setProperty("headerCompact", "true")
                status_container.style().unpolish(status_container)
                status_container.style().polish(status_container)
                status_lay = status_container.layout()
                if status_lay is not None:
                    status_lay.setContentsMargins(6, 0, 0, 0)
                if status_lay is not None and status_banner is not None:
                    status_lay.setStretch(status_lay.indexOf(status_banner), 0)
            if status_banner is not None:
                status_banner.setProperty("headerCompact", "true")
                status_banner.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                status_banner.style().unpolish(status_banner)
                status_banner.style().polish(status_banner)
                banner_lay = status_banner.layout()
                if banner_lay is not None:
                    lbl = getattr(self, "status_banner_text", None)
                    if lbl is not None:
                        banner_lay.setStretch(banner_lay.indexOf(lbl), 0)
            label = getattr(self, "status_banner_text", None)
            if isinstance(label, ElidedStatusLabel):
                label.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
            elif isinstance(label, QtWidgets.QLabel):
                label.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
            if hdr is not None:
                hdr.setMinimumHeight(42)
                hdr.setProperty("toolsChipsEmbedded", "true")
                hdr.style().unpolish(hdr)
                hdr.style().polish(hdr)
        else:
            chip_host.hide()
            chip_host.setProperty("topChipsEmbedded", "false")
            chip_host.style().unpolish(chip_host)
            chip_host.style().polish(chip_host)
            for fade in (
                getattr(self, "_header_chip_fade_l", None),
                getattr(self, "_header_chip_fade_r", None),
            ):
                if fade is not None:
                    fade.hide()
            if chip_sep is not None:
                chip_sep.hide()
                self._detach_widget_from_layout(chip_sep)
            scroll.setWidget(inner)
            rail_lay = chip_rail.layout()
            if rail_lay is not None:
                rail_lay.addWidget(scroll, 1)
            chip_rail.setFixedHeight(MODERN_CHIP_RAIL_H)
            chip_rail.hide()
            if chip_label is not None:
                chip_label.show()
            if status_container is not None:
                status_container.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                status_container.setMaximumWidth(16777215)
                status_container.setProperty("headerCompact", "false")
                status_container.style().unpolish(status_container)
                status_container.style().polish(status_container)
                status_lay = status_container.layout()
                if status_lay is not None:
                    status_lay.setContentsMargins(0, 0, 0, 0)
                if status_lay is not None and status_banner is not None:
                    status_lay.setStretch(status_lay.indexOf(status_banner), 1)
            if status_banner is not None:
                status_banner.setProperty("headerCompact", "false")
                status_banner.setMaximumWidth(16777215)
                status_banner.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                status_banner.style().unpolish(status_banner)
                status_banner.style().polish(status_banner)
            label = getattr(self, "status_banner_text", None)
            if isinstance(label, QtWidgets.QLabel):
                label.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
            if hdr is not None:
                hdr.setMinimumHeight(40)
                hdr.setProperty("toolsChipsEmbedded", "false")
                hdr.style().unpolish(hdr)
                hdr.style().polish(hdr)

        self._sync_header_split_chips_pane(top_chips)

        self._apply_embedded_header_chip_styles()
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_compression)
        QtCore.QTimer.singleShot(0, self._sync_modern_status_banner_width)

    def _apply_modern_tools_nav_mode(self, mode: str, *, persist: bool) -> None:
        normalized = "top_chips" if str(mode).strip().lower() == "top_chips" else "sidebar"
        self._modern_tools_nav_mode = normalized
        top_chips = normalized == "top_chips"

        sidebar = getattr(self, "_modern_sidebar_scroll", None)
        sep = getattr(self, "_modern_sidebar_sep", None)
        if sidebar is not None:
            sidebar.setVisible(not top_chips)
        if sep is not None:
            sep.setVisible(not top_chips)
        self._mount_modern_tools_nav_chrome(top_chips)

        if top_chips:
            stack = getattr(self, "_tools_stack", None)
            if stack is not None:
                self._sync_modern_nav_highlight(stack.currentIndex())

        if persist:
            payload = load_modern_layout_prefs()
            save_modern_layout_prefs(
                hsplit=payload.get("hsplit"),
                left_vsplit=payload.get("left_vsplit"),
                right_vsplit=payload.get("right_vsplit"),
                slot_assignments=payload.get("slot_assignments"),
                sidebar_collapsed=payload.get("sidebar_collapsed"),
                control_map_collapsed=payload.get("control_map_collapsed"),
                tools_nav_mode=normalized,
            )
        from ui.header_status import split_status_title_detail

        label = self.status_banner_text
        state = str(self.status_banner.property("state") or "stopped")
        if isinstance(label, ElidedStatusLabel):
            title, detail = split_status_title_detail(
                label.full_text().removeprefix("● ").strip()
            )
        else:
            title, detail = split_status_title_detail(str(label.text()))
        if title:
            self._set_status_banner(state, title, detail)
        self._refresh_modern_tools_nav_mode_menu()
        self._schedule_modern_header_layout()

    def _wire_modern_tools_nav_mode_menu(self) -> None:
        view_btn = getattr(self, "_topbar_widgets", {}).get("view")
        menu = view_btn.menu() if view_btn is not None else None
        if menu is None:
            return
        if getattr(self, "_modern_nav_mode_menu_wired", False):
            return
        self._modern_nav_mode_menu_wired = True

        menu.addSeparator()
        add_view_menu_section_header(menu, "Tools navigation")
        self._act_tools_nav_sidebar = QtGui.QAction("Sidebar", self)
        self._act_tools_nav_sidebar.setCheckable(True)
        self._act_tools_nav_sidebar.triggered.connect(
            lambda: self._apply_modern_tools_nav_mode("sidebar", persist=True)
        )
        menu.addAction(self._act_tools_nav_sidebar)
        self._act_tools_nav_top_chips = QtGui.QAction("Top chips", self)
        self._act_tools_nav_top_chips.setCheckable(True)
        self._act_tools_nav_top_chips.triggered.connect(
            lambda: self._apply_modern_tools_nav_mode("top_chips", persist=True)
        )
        menu.addAction(self._act_tools_nav_top_chips)
        group = QtGui.QActionGroup(self)
        group.setExclusive(True)
        group.addAction(self._act_tools_nav_sidebar)
        group.addAction(self._act_tools_nav_top_chips)
        menu.addSeparator()
        self._view_header_bar_sep = menu.addSeparator()
        add_view_menu_section_header(menu, "Header bar")
        self._view_header_bar_section = menu.actions()[-1]

        chip_menu = menu.addMenu("Chip display")
        chip_menu.setObjectName("modernHeaderChipDisplayMenu")
        self._act_chip_mode_auto = QtGui.QAction("Auto (labels, icons when tight)", self)
        self._act_chip_mode_icons = QtGui.QAction("Icons only (no labels)", self)
        self._act_chip_mode_labels = QtGui.QAction("Labels only (scroll when tight)", self)
        for act in (
            self._act_chip_mode_auto,
            self._act_chip_mode_icons,
            self._act_chip_mode_labels,
        ):
            act.setCheckable(True)
            chip_menu.addAction(act)
        self._chip_mode_group = QtGui.QActionGroup(self)
        self._chip_mode_group.setExclusive(True)
        for act in (
            self._act_chip_mode_auto,
            self._act_chip_mode_icons,
            self._act_chip_mode_labels,
        ):
            self._chip_mode_group.addAction(act)
        self._act_chip_mode_auto.triggered.connect(
            lambda: self._on_chip_display_mode_chosen("auto")
        )
        self._act_chip_mode_icons.triggered.connect(
            lambda: self._on_chip_display_mode_chosen("icons")
        )
        self._act_chip_mode_labels.triggered.connect(
            lambda: self._on_chip_display_mode_chosen("labels")
        )
        chip_menu.aboutToShow.connect(self._refresh_chip_display_menu_checks)

        self._act_customize_chip_icons = QtGui.QAction("Customize chip icons…", self)
        self._act_customize_chip_icons.triggered.connect(self._open_header_chip_icon_dialog)
        menu.addAction(self._act_customize_chip_icons)
        self._act_reset_chip_icons = QtGui.QAction("Reset chip icons to defaults", self)
        self._act_reset_chip_icons.triggered.connect(self._reset_header_chip_icons)
        menu.addAction(self._act_reset_chip_icons)

        self._header_bar_view_actions = [
            self._view_header_bar_sep,
            self._view_header_bar_section,
            chip_menu.menuAction(),
            self._act_customize_chip_icons,
            self._act_reset_chip_icons,
        ]

        menu.addSeparator()
        self._view_header_resize_sep = menu.addSeparator()
        self._act_header_resize = QtGui.QAction("Resize header sections (manual)", self)
        self._act_header_resize.setCheckable(True)
        self._act_header_resize.setToolTip(
            "Check to drag dividers between Start, status, tool chips, and "
            "View/HUD/Layout."
        )
        self._act_header_resize.triggered.connect(self._on_header_resize_unlock_toggled)
        menu.addAction(self._act_header_resize)
        self._header_bar_view_actions.append(self._view_header_resize_sep)
        self._header_bar_view_actions.append(self._act_header_resize)
        menu.addSeparator()
        menu.aboutToShow.connect(self._refresh_modern_tools_nav_mode_menu)

    def _refresh_modern_tools_nav_mode_menu(self) -> None:
        mode = getattr(self, "_modern_tools_nav_mode", "sidebar")
        sidebar_act = getattr(self, "_act_tools_nav_sidebar", None)
        chips_act = getattr(self, "_act_tools_nav_top_chips", None)
        for act in (sidebar_act, chips_act):
            if act is not None:
                act.blockSignals(True)
        try:
            if sidebar_act is not None:
                sidebar_act.setChecked(mode != "top_chips")
            if chips_act is not None:
                chips_act.setChecked(mode == "top_chips")
        finally:
            for act in (sidebar_act, chips_act):
                if act is not None:
                    act.blockSignals(False)
        resize_act = getattr(self, "_act_header_resize", None)
        if resize_act is not None:
            resize_act.blockSignals(True)
            try:
                resize_act.setChecked(bool(getattr(self, "_header_split_unlocked", False)))
            finally:
                resize_act.blockSignals(False)
        top_chips = mode == "top_chips"
        for act in getattr(self, "_header_bar_view_actions", []):
            if act is not None:
                act.setVisible(top_chips)
                act.setEnabled(top_chips)
        mode = getattr(self, "_header_chips_icon_mode", "auto")
        self._refresh_chip_display_menu_checks(mode)

    def _on_chip_display_mode_chosen(self, mode: str) -> None:
        mode_map = {
            "auto": getattr(self, "_act_chip_mode_auto", None),
            "icons": getattr(self, "_act_chip_mode_icons", None),
            "labels": getattr(self, "_act_chip_mode_labels", None),
        }
        act = mode_map.get(mode)
        if act is None or not act.isChecked():
            return
        self._apply_header_chips_icon_mode(mode, persist=True)

    def _refresh_chip_display_menu_checks(
        self, mode: str | None = None
    ) -> None:
        mode = mode or getattr(self, "_header_chips_icon_mode", "auto")
        mode_map = {
            "auto": getattr(self, "_act_chip_mode_auto", None),
            "icons": getattr(self, "_act_chip_mode_icons", None),
            "labels": getattr(self, "_act_chip_mode_labels", None),
        }
        acts = [a for a in mode_map.values() if a is not None]
        for act in acts:
            act.blockSignals(True)
        try:
            for act in acts:
                act.setChecked(False)
            pick = mode_map.get(mode) or getattr(self, "_act_chip_mode_auto", None)
            if pick is not None:
                pick.setChecked(True)
        finally:
            for act in acts:
                act.blockSignals(False)

    def _apply_header_chips_icon_mode(self, mode: str, *, persist: bool) -> None:
        from ui.header_bar_prefs import normalize_header_chips_icon_mode

        self._header_chips_icon_mode = normalize_header_chips_icon_mode(mode)
        if persist:
            save_modern_layout_prefs(header_chips_icon_mode=self._header_chips_icon_mode)
        if self._header_chips_icon_mode == "icons":
            self._header_chips_icon_only = True
        elif self._header_chips_icon_mode == "labels":
            self._header_chips_icon_only = False
        else:
            self._header_chips_icon_only = self._resolve_header_chips_icon_only()
        self._apply_embedded_header_chip_styles()
        stack = getattr(self, "_tools_stack", None)
        if stack is not None:
            self._sync_modern_nav_highlight(stack.currentIndex())
        self._sync_modern_header_chip_scroll()
        self._schedule_modern_header_layout()
        self._refresh_chip_display_menu_checks(self._header_chips_icon_mode)

    def _open_header_chip_icon_dialog(self) -> None:
        from ui.header_icon_dialog import HeaderChipIconDialog

        dlg = HeaderChipIconDialog(getattr(self, "_header_chip_icons", {}), self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self._header_chip_icons = dlg.icons()
        save_modern_layout_prefs(header_chip_icons=self._header_chip_icons)
        self._rebuild_modern_tools_nav_from_state()
        self._schedule_modern_header_layout()

    def _reset_header_chip_icons(self) -> None:
        self._header_chip_icons = {}
        save_modern_layout_prefs(header_chip_icons={})
        self._rebuild_modern_tools_nav_from_state()
        self._schedule_modern_header_layout()

    def _apply_modern_sidebar_collapsed(self, collapsed: bool, *, persist: bool) -> None:
        self._modern_sidebar_collapsed = collapsed
        scroll = getattr(self, "_modern_sidebar_scroll", None)
        if scroll is not None:
            scroll.setFixedWidth(
                MODERN_SIDEBAR_COLLAPSED_W if collapsed else MODERN_SIDEBAR_EXPANDED_W
            )
        # "TOOLS" text label hides when collapsed; the top strip itself stays visible
        header = getattr(self, "_modern_nav_header", None)
        if header is not None:
            header.setVisible(not collapsed)
        for grp in getattr(self, "_modern_nav_group_headers", []):
            grp.setVisible(not collapsed)
        for btn in getattr(self, "_tools_nav_buttons", []):
            icon = str(btn.property("navIcon") or "").strip()
            label = str(btn.property("navLabel") or "").strip()
            if collapsed:
                btn.setText(icon or label[:1])
                btn.setToolTip(label)
            else:
                btn.setText(f"  {icon}  {label}".strip() if icon else f"  {label}")
                btn.setToolTip(label)
        collapse_btn = getattr(self, "_modern_sidebar_collapse_btn", None)
        if collapse_btn is not None:
            collapse_btn.setText("›" if collapsed else "‹")
            collapse_btn.setToolTip(
                "Expand sidebar labels" if collapsed else "Collapse to icons only"
            )
        if persist:
            payload = load_modern_layout_prefs()
            save_modern_layout_prefs(
                hsplit=payload.get("hsplit"),
                left_vsplit=payload.get("left_vsplit"),
                right_vsplit=payload.get("right_vsplit"),
                slot_assignments=payload.get("slot_assignments"),
                sidebar_collapsed=collapsed,
            )

    def _on_modern_section_changed(self, index: int) -> None:
        self._sync_modern_nav_highlight(index)
        if getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips":
            self._sync_modern_header_chip_scroll(follow_active=True)
        self._save_active_section()
        sid = getattr(self, "_modern_sid_by_stack_index", {}).get(index, "")
        if sid == "hub":
            self._maybe_hub_auto_refresh()
        QtCore.QTimer.singleShot(0, self._sync_modern_status_banner_width)

    # ── Sub-builders ──────────────────────────────────────────────────────

    def _modern_control_form_card(
        self, title: str, *, icon: str = ""
    ) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
        card = QtWidgets.QFrame()
        card.setObjectName("modernControlFormCard")
        card.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        lay = QtWidgets.QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        if icon:
            ic = QtWidgets.QLabel(icon)
            ic.setObjectName("modernControlSectionIcon")
            head.addWidget(ic, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        ttl = QtWidgets.QLabel(title)
        ttl.setObjectName("modernControlSectionTitle")
        head.addWidget(ttl, 1)
        lay.addLayout(head)
        sep = QtWidgets.QFrame()
        sep.setObjectName("modernControlSectionSep")
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        lay.addWidget(sep)
        return card, lay

    def _control_form_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("modernControlFormLabel")
        return lbl

    def _control_form_field(
        self, label: str, widget: QtWidgets.QWidget
    ) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._control_form_label(label))
        lay.addWidget(widget)
        return col

    def _build_serial_group(self) -> QtWidgets.QFrame:
        card, lay = self._modern_control_form_card("Serial link", icon="🔌")
        self._wire_modern_com_refresh_button()

        com_field = QtWidgets.QFrame()
        com_field.setObjectName("modernComFieldWrap")
        com_row = QtWidgets.QHBoxLayout(com_field)
        com_row.setContentsMargins(0, 0, 0, 0)
        com_row.setSpacing(0)
        self.com_cb.setMinimumHeight(34)
        com_row.addWidget(self.com_cb, 1)
        com_row.addWidget(
            self.refresh_btn,
            0,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        self.refresh_btn.raise_()

        fields = QtWidgets.QVBoxLayout()
        fields.setSpacing(10)
        com_baud_row = QtWidgets.QHBoxLayout()
        com_baud_row.setSpacing(10)
        com_baud_row.addWidget(self._control_form_field("COM port", com_field), 3)
        self.baud_edit.setMinimumHeight(34)
        self.baud_edit.setMaximumWidth(132)
        self.baud_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        com_baud_row.addWidget(self._control_form_field("Baud", self.baud_edit), 0)
        fields.addLayout(com_baud_row)
        chk_col = QtWidgets.QVBoxLayout()
        chk_col.setSpacing(6)
        chk_col.addWidget(self.chk_serial_auto_reconnect)
        chk_col.addWidget(self.chk_auto_discover)
        fields.addLayout(chk_col)
        body_host = QtWidgets.QWidget()
        body_host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        body_lay = QtWidgets.QVBoxLayout(body_host)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addLayout(fields)
        body_lay.addStretch(1)
        lay.addWidget(body_host, 1)
        return card

    def _wire_modern_com_refresh_button(self) -> None:
        """Icon refresh control beside COM dropdown — rescan serial ports."""
        btn = self.refresh_btn
        btn.setObjectName("modernComRefreshBtn")
        btn.setToolTip("Refresh COM port list")
        btn.setFixedSize(34, 34)
        btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        btn.setEnabled(True)
        sp = QtWidgets.QStyle.StandardPixmap
        icon = self.style().standardIcon(sp.SP_BrowserReload)
        btn.setIcon(icon)
        btn.setIconSize(QtCore.QSize(18, 18))
        btn.setText("" if not icon.isNull() else "\u21bb")
        btn.clicked.connect(self.refresh_ports)

    def _build_network_group(self) -> QtWidgets.QFrame:
        card, lay = self._modern_control_form_card("Network path", icon="📡")
        body_host = QtWidgets.QWidget()
        body_host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        body = QtWidgets.QVBoxLayout(body_host)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        host_col = QtWidgets.QVBoxLayout()
        host_col.setSpacing(4)
        host_col.addWidget(self._control_form_label("Listen host"))
        self.udp_host.setMinimumHeight(34)
        host_col.addWidget(self.udp_host)
        body.addLayout(host_col)
        port_col = QtWidgets.QVBoxLayout()
        port_col.setSpacing(4)
        port_col.addWidget(self._control_form_label("Listen port"))
        self.udp_port.setMinimumHeight(34)
        port_col.addWidget(self.udp_port)
        body.addLayout(port_col)
        fan = QtWidgets.QHBoxLayout()
        fan.addWidget(self.chk_udp_fanout, 1)
        fan.addWidget(
            create_network_help_button(self),
            0,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        body.addLayout(fan)
        mirror_row = QtWidgets.QHBoxLayout()
        mirror_row.setContentsMargins(0, 0, 0, 0)
        mirror_row.setSpacing(8)
        mirror_row.addWidget(self._control_form_label("Serial mirrors"), 0)
        self.serial_mirror_ports.setMinimumHeight(32)
        self.serial_mirror_ports.show()
        mirror_row.addWidget(self.serial_mirror_ports, 1)
        body.addLayout(mirror_row)
        mirror_tx_wrap = QtWidgets.QWidget()
        mirror_tx_wrap.setObjectName("modernControlNestedRow")
        mirror_tx_lay = QtWidgets.QHBoxLayout(mirror_tx_wrap)
        mirror_tx_lay.setContentsMargins(12, 0, 0, 0)
        mirror_tx_lay.setSpacing(0)
        self.chk_serial_mirror_device_tx.show()
        mirror_tx_lay.addWidget(self.chk_serial_mirror_device_tx)
        body.addWidget(mirror_tx_wrap)
        body.addWidget(self.chk_tcp_sink_enable)
        self._tcp_sink_port_panel = QtWidgets.QWidget()
        self._tcp_sink_port_panel.setObjectName("modernTcpSinkIndent")
        port_panel_lay = QtWidgets.QHBoxLayout(self._tcp_sink_port_panel)
        port_panel_lay.setContentsMargins(0, 2, 0, 0)
        port_panel_lay.setSpacing(10)
        indent = QtWidgets.QFrame()
        indent.setObjectName("modernControlIndentRule")
        indent.setFixedWidth(3)
        port_panel_lay.addWidget(indent, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        port_inner = QtWidgets.QVBoxLayout()
        port_inner.setSpacing(4)
        port_inner.addWidget(self._control_form_label("Mirror port"))
        self.tcp_sink_port.setFixedWidth(88)
        self.tcp_sink_port.setMaximumWidth(96)
        self.tcp_sink_port.setMinimumHeight(32)
        port_inner.addWidget(self.tcp_sink_port, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        port_panel_lay.addLayout(port_inner, 1)
        body.addWidget(self._tcp_sink_port_panel)
        body.addWidget(self.chk_advanced_net)
        self._advanced_net_scroll = QtWidgets.QScrollArea()
        self._advanced_net_scroll.setObjectName("modernAdvancedNetScroll")
        self._advanced_net_scroll.setWidgetResizable(True)
        self._advanced_net_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._advanced_net_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._advanced_net_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._advanced_net_scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._advanced_net_scroll.setWidget(self._advanced_net)
        self._advanced_net_scroll.setVisible(self.chk_advanced_net.isChecked())
        self._advanced_net.setVisible(True)
        body.addWidget(self._advanced_net_scroll, 1)
        lay.addWidget(body_host, 1)
        self.chk_tcp_sink_enable.toggled.connect(self._sync_tcp_sink_port_row)
        self._sync_tcp_sink_port_row(self.chk_tcp_sink_enable.isChecked())
        return card

    def _sync_tcp_sink_port_row(self, enabled: bool) -> None:
        panel = getattr(self, "_tcp_sink_port_panel", None)
        if panel is None:
            return
        panel.setVisible(bool(enabled))
        if hasattr(self, "_balance_control_form_cards"):
            QtCore.QTimer.singleShot(0, self._balance_control_form_cards)

    def _balance_control_form_cards(self) -> None:
        serial = getattr(self, "_control_serial_group", None)
        network = getattr(self, "_control_network_group", None)
        host = getattr(self, "_control_forms_host", None)
        if serial is None or network is None:
            return
        if host is not None and host.height() > 120:
            h = host.height()
        else:
            h = max(320, serial.sizeHint().height(), network.sizeHint().height())
        serial.setMinimumHeight(h)
        network.setMinimumHeight(h)
        self._sync_network_advanced_scroll()

    def _sync_network_advanced_scroll(self) -> None:
        scroll = getattr(self, "_advanced_net_scroll", None)
        if scroll is not None:
            scroll.updateGeometry()

    def _build_status_footer(self) -> QtWidgets.QFrame:
        footer = QtWidgets.QFrame()
        footer.setObjectName("modernStatusFooter")
        footer.setFixedHeight(22)
        row = QtWidgets.QHBoxLayout(footer)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(10)
        row.addStretch(1)
        version_lbl = QtWidgets.QLabel(f"Serial Link v{__version__} · modern")
        version_lbl.setObjectName("modernFooterVersion")
        row.addWidget(version_lbl, 0)
        return footer

    # ── UI editor (main tabs + Tools sidebar) ───────────────────────────────

    def _on_tools_nav_child_context_menu(self, sid: str, global_pos: QtCore.QPoint) -> None:
        if sid == "theme":
            self._popup_theme_quick_pick_menu(global_pos)

    def _modern_tools_nav_button(
        self,
        label: str,
        icon: str,
        idx: int,
        buttons: list[QtWidgets.QPushButton],
        stack: QtWidgets.QStackedWidget,
        *,
        sid: str = "",
    ) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(f"  {icon}  {label}")
        btn.setObjectName("modernSettingsNavBtn")
        btn.setProperty("navLabel", label)
        btn.setProperty("navIcon", icon)
        btn.setProperty("navIndex", idx)
        btn.setProperty("navSid", sid)
        btn.setCheckable(True)
        btn.setProperty("navActive", False)
        btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda _checked, i=idx: self._tools_nav_select(i))
        if sid == "theme":
            btn.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            btn.setToolTip(
                "Theme studio — right-click for built-in palettes and saved presets."
            )
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn: self._popup_theme_quick_pick_menu(b.mapToGlobal(pos))
            )
        return btn

    def _modern_tools_chip_button(
        self,
        label: str,
        icon: str,
        idx: int,
        stack: QtWidgets.QStackedWidget,
    ) -> QtWidgets.QPushButton:
        text = f"{icon}  {label}".strip() if icon else label
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("modernToolsNavChip")
        btn.setProperty("navLabel", label)
        btn.setProperty("navIcon", icon)
        btn.setProperty("navIndex", idx)
        btn.setProperty("navActive", False)
        btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        btn.setToolTip(label)
        btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(MODERN_CHIP_BTN_H)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.clicked.connect(lambda _checked, i=idx: self._tools_nav_select(i))
        return btn

    def _rebuild_modern_tools_chip_rail(
        self,
        visible_names: list[str],
        *,
        sid_by_label: dict[str, str],
        icon_by_label: dict[str, str],
        stack: QtWidgets.QStackedWidget,
    ) -> None:
        from ui.modern_tools_chips import make_chip_dropdown_button
        from ui.tool_tabs import build_modern_tools_nav_tiers

        inner = getattr(self, "_modern_tools_chip_inner", None)
        if inner is None:
            return
        lay = inner.layout()
        if lay is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        visible_set = set(visible_names)
        section_index = getattr(self, "_tools_section_index", {})
        chip_buttons: list[QtWidgets.QPushButton] = []
        chip_dropdowns: list[QtWidgets.QToolButton] = []

        def _visible_child_items(
            children: list[tuple[str, str, str]],
        ) -> list[tuple[str, str, str, int]]:
            out: list[tuple[str, str, str, int]] = []
            for sid, lbl, icon in children:
                if sid in MODERN_HEADER_NAV_SIDS:
                    continue
                if lbl not in visible_set:
                    continue
                idx = section_index.get(sid, -1)
                if idx < 0:
                    continue
                out.append((sid, lbl, icon, idx))
            return out

        from ui.header_bar_prefs import merge_chip_icon

        nav_leaves, nav_dropdowns = build_modern_tools_nav_tiers()
        from ui.tool_tabs import sort_modern_nav_by_saved_order

        nav_leaves = sort_modern_nav_by_saved_order(nav_leaves, visible_names)
        nav_dropdowns = sort_modern_nav_by_saved_order(
            nav_dropdowns, visible_names, tier=True
        )

        for sid, lbl, icon in nav_leaves:
            if sid in MODERN_HEADER_NAV_SIDS or lbl not in visible_set:
                continue
            icon = merge_chip_icon(sid, icon, getattr(self, "_header_chip_icons", None))
            idx = section_index.get(sid, 0)
            btn = self._modern_tools_chip_button(lbl, icon, idx, stack)
            chip_buttons.append(btn)
            lay.addWidget(btn)

        for _tier_key, tier_label, tier_icon, children in nav_dropdowns:
            child_items = _visible_child_items(children)
            if child_items:
                rank = {lbl: i for i, lbl in enumerate(visible_names)}
                child_items = sorted(
                    child_items, key=lambda t: rank.get(t[1], len(visible_names) + 1)
                )
            if not child_items:
                continue
            tier_icon = merge_chip_icon(
                _tier_key, tier_icon, getattr(self, "_header_chip_icons", None)
            )
            utilities = None
            if _tier_key == "bench_tools":
                utilities = [("Bench pair setup…", "🔧", self._open_bench_pair_setup)]
            dropdown = make_chip_dropdown_button(
                tier_key=_tier_key,
                label=tier_label,
                icon=tier_icon,
                children=child_items,
                on_pick=self._open_modern_section_by_sid,
                on_cycle=self._cycle_modern_tools_dropdown,
                utility_actions=utilities,
                child_context_menu_sids=frozenset({"theme"}),
                on_child_context_menu=self._on_tools_nav_child_context_menu,
            )
            chip_dropdowns.append(dropdown)
            lay.addWidget(dropdown)

        self._tools_chip_buttons = chip_buttons
        self._tools_chip_dropdowns = chip_dropdowns
        inner.setFixedHeight(MODERN_CHIP_BTN_H)
        inner.adjustSize()
        scroll = getattr(self, "_modern_tools_chip_scroll", None)
        if scroll is not None and scroll.widget() is not inner:
            scroll.setWidget(inner)

        cur = stack.currentIndex()
        self._tools_nav_select(cur)
        self._apply_embedded_header_chip_styles()
        QtCore.QTimer.singleShot(0, self._sync_modern_header_chip_compression)
        self._ensure_modern_nav_visible()

    def _setup_modern_ui_editor_catalogs(self) -> None:
        self._tab_catalog.pop("main_tabs", None)
        self._tab_hidden.pop("main_tabs", None)

        nav_flat = build_modern_tools_all_pages()
        self._modern_tools_nav_flat = nav_flat
        self._modern_tools_sid_by_label = {lbl: sid for sid, lbl, _icon in nav_flat}
        self._modern_tools_icon_by_label = {lbl: icon for _sid, lbl, icon in nav_flat}

        stack = self._tools_stack
        tools_catalog: dict[str, tuple[QtWidgets.QWidget, str]] = {}
        for sid, lbl, _icon in nav_flat:
            idx = self._tools_section_index.get(sid, -1)
            if idx < 0:
                continue
            if sid in MODERN_HEADER_NAV_SIDS:
                continue
            tools_catalog[lbl] = (
                stack.widget(idx),
                MODERN_TOOLS_TAB_HINTS.get(lbl, ""),
            )
        self._tab_catalog["tools_tabs"] = tools_catalog
        self._tab_hidden["tools_tabs"] = set(load_hidden_tabs("modern", "tools_tabs"))
        self._rebuild_modern_tools_nav_from_state()

    def _rebuild_modern_tools_nav_from_state(self, key: str = "tools_tabs") -> None:
        nav_inner = getattr(self, "_modern_tools_sidebar_inner", None)
        stack = getattr(self, "_tools_stack", None)
        catalog = self._tab_catalog.get(key, {})
        sid_by_label = getattr(self, "_modern_tools_sid_by_label", {})
        icon_by_label = getattr(self, "_modern_tools_icon_by_label", {})
        if nav_inner is None or stack is None or not catalog:
            return

        from ui.tool_tabs import build_modern_tools_nav_groups, order_modern_tools_nav_names

        saved_visible = self._visible_tools_tab_names(key)
        visible_names = order_modern_tools_nav_names(saved_visible)
        cur_w = stack.currentWidget()
        prev_sid = ""
        for lbl, (widget, _tip) in catalog.items():
            if widget is cur_w:
                prev_sid = sid_by_label.get(lbl, "")
                break
        if not prev_sid and cur_w is not None:
            guide_idx = getattr(self, "_tools_section_index", {}).get("guide", -1)
            if 0 <= guide_idx < stack.count() and stack.widget(guide_idx) is cur_w:
                prev_sid = "guide"

        mr_widget: QtWidgets.QWidget | None = None
        mr_idx = getattr(self, "_mission_review_stack_index", -1)
        if 0 <= mr_idx < stack.count():
            mr_widget = stack.widget(mr_idx)
            stack.removeWidget(mr_widget)

        guide_widget: QtWidgets.QWidget | None = None
        guide_idx = getattr(self, "_tools_section_index", {}).get("guide", -1)
        if 0 <= guide_idx < stack.count():
            guide_widget = stack.widget(guide_idx)
            stack.removeWidget(guide_widget)

        widgets = [catalog[name][0] for name in visible_names if name in catalog]
        while stack.count():
            w = stack.widget(0)
            stack.removeWidget(w)
        for widget in widgets:
            stack.addWidget(widget)
        if guide_widget is not None:
            stack.addWidget(guide_widget)
        if mr_widget is not None:
            stack.addWidget(mr_widget)
            self._mission_review_stack_index = stack.count() - 1

        sb_lay = nav_inner.layout()
        if sb_lay is None:
            return
        while sb_lay.count():
            item = sb_lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # ── Rebuild: top strip with TOOLS label + collapse button ────────────
        _top_row = QtWidgets.QWidget()
        _top_row.setObjectName("modernSidebarTopStrip")
        _top_lay = QtWidgets.QHBoxLayout(_top_row)
        _top_lay.setContentsMargins(8, 0, 4, 0)
        _top_lay.setSpacing(0)
        self._modern_nav_header = QtWidgets.QLabel("TOOLS")
        self._modern_nav_header.setObjectName("modernSettingsNavHeader")
        _top_lay.addWidget(self._modern_nav_header, 1)
        _collapse_btn = QtWidgets.QToolButton()
        _collapse_btn.setObjectName("modernSidebarCollapseBtn")
        _collapse_btn.setAutoRaise(True)
        _collapse_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        _collapse_btn.clicked.connect(self._toggle_modern_sidebar_collapsed)
        self._modern_sidebar_collapse_btn = _collapse_btn
        _top_lay.addWidget(_collapse_btn)
        sb_lay.addWidget(_top_row)
        sb_lay.addSpacing(2)

        sid_to_group: dict[str, str] = {}
        for group_label, items in build_modern_tools_nav_groups():
            for sid, _lbl, _icon in items:
                sid_to_group[sid] = group_label

        nav_buttons: list[QtWidgets.QPushButton] = []
        group_headers: list[QtWidgets.QLabel] = []
        self._tools_section_index = {}
        self._modern_sid_by_stack_index = {}
        current_group: str | None = None
        stack_idx = 0
        for name in visible_names:
            sid = sid_by_label.get(name, "")
            if sid in MODERN_HEADER_NAV_SIDS:
                continue
            icon = icon_by_label.get(name, "")
            grp = sid_to_group.get(sid, "")
            if grp and grp != current_group:
                if current_group is not None:
                    sb_lay.addSpacing(6)
                grp_hdr = QtWidgets.QLabel(grp.upper())
                grp_hdr.setObjectName("modernSettingsNavGroup")
                group_headers.append(grp_hdr)
                sb_lay.addWidget(grp_hdr)
                current_group = grp
            if sid:
                self._tools_section_index[sid] = stack_idx
                self._modern_sid_by_stack_index[stack_idx] = sid
            btn = self._modern_tools_nav_button(
                name, icon, stack_idx, nav_buttons, stack, sid=sid
            )
            nav_buttons.append(btn)
            sb_lay.addWidget(btn)
            stack_idx += 1

        if guide_widget is not None:
            g_idx = stack.indexOf(guide_widget)
            if g_idx >= 0:
                self._tools_section_index["guide"] = g_idx
                self._modern_sid_by_stack_index[g_idx] = "guide"

        sb_lay.addStretch(1)
        self._tools_nav_buttons = nav_buttons
        self._modern_nav_group_headers = group_headers

        if mr_widget is not None:
            self._modern_sid_by_stack_index[self._mission_review_stack_index] = (
                "mission_review"
            )

        collapsed = bool(getattr(self, "_modern_sidebar_collapsed", False))
        self._apply_modern_sidebar_collapsed(collapsed, persist=False)

        pick = 0
        if prev_sid and prev_sid in self._tools_section_index:
            pick = self._tools_section_index[prev_sid]
        elif visible_names:
            pick = 0
        if nav_buttons:
            self._tools_nav_select(pick)

        self._rebuild_modern_tools_chip_rail(
            saved_visible,
            sid_by_label=sid_by_label,
            icon_by_label=icon_by_label,
            stack=stack,
        )

        if "presets" in self._tools_section_index:
            self._modern_bench_presets = stack.widget(self._tools_section_index["presets"])
        if hasattr(self, "_refresh_tools_page_status"):
            self._refresh_tools_page_status()

    def _persist_modern_tools_nav_state(self, key: str = "tools_tabs") -> None:
        buttons = getattr(self, "_tools_nav_buttons", None)
        if not buttons:
            return
        order: list[str] = []
        for btn in buttons:
            label = btn.property("navLabel")
            if isinstance(label, str) and label.strip():
                order.append(label.strip())
                continue
            text = btn.text().strip()
            parts = [p for p in text.split("  ") if p.strip()]
            if parts:
                order.append(parts[-1].strip())
        if order:
            save_tab_order(getattr(self, "_ui_mode", "modern"), key, order)
        hidden = sorted(self._tab_hidden.get(key, set()))
        save_hidden_tabs(getattr(self, "_ui_mode", "modern"), key, hidden)

    # ── Tab helpers ────────────────────────────────────────────────────────

    _RETIRED_TAB_NAMES = frozenset({"Telemetry", "Log", "Wire", "Settings", "Hub", "Tools"})
    _RETIRED_SECTION_SIDS = frozenset({"tools", "telemetry", "log", "wire", "settings"})

    def _tab_index_by_name(self, name: str) -> int:
        """Legacy shim — routes tab names to sidebar sections."""
        key = name.strip()
        sid = _MODERN_LEGACY_SECTION.get(key, "")
        if sid:
            QtCore.QTimer.singleShot(0, lambda s=sid: self._open_modern_section_by_sid(s))
            return 0
        return -1

    def _save_active_section(self) -> None:
        try:
            import json

            stack = getattr(self, "_tools_stack", None)
            if stack is None:
                return
            idx = stack.currentIndex()
            sid = getattr(self, "_modern_sid_by_stack_index", {}).get(idx, "activity")
            raw: dict = {}
            if CONFIG_PATH.is_file():
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
            raw["modern_active_section"] = sid
            label = {
                "activity": "Activity",
                "control": "Control",
                "mission_review": "Mission Review",
            }.get(sid, sid)
            raw["modern_active_tab_name"] = label
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        except (OSError, ValueError):
            pass

    def _restore_active_section(self) -> None:
        try:
            import json

            if not CONFIG_PATH.is_file():
                return
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            sid = raw.get("modern_active_section")
            if not isinstance(sid, str) or not sid.strip():
                name = raw.get("modern_active_tab_name")
                if isinstance(name, str) and name.strip():
                    sid = _MODERN_LEGACY_SECTION.get(name.strip(), "activity")
                else:
                    sid = "activity"
            if sid in self._RETIRED_SECTION_SIDS or sid in self._RETIRED_TAB_NAMES:
                sid = "activity"
            self._open_modern_section_by_sid(str(sid), save=False)
        except (OSError, ValueError):
            pass

    def _save_active_tab(self, index: int) -> None:
        self._save_active_section()

    def _restore_active_tab(self) -> None:
        self._restore_active_section()

    # ── Bridge lifecycle ───────────────────────────────────────────────────

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        from ui.modern_header_layout import compact_status_display

        title = title.strip()
        detail = detail.strip()
        compact_top_chips = (
            getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips"
        )
        if compact_top_chips:
            if state == "running":
                display = compact_status_display("running", title)
                tip = f"Running · {detail}" if detail else "Running"
            else:
                display = compact_status_display(state, title)
                tip = f"{title} · {detail}" if detail else title
        elif state == "running":
            display = detail or "Bridge active"
            tip = f"Running · {detail}" if detail else "Running"
        elif detail:
            display = f"{title} · {detail}"
            tip = display
        else:
            display = title
            tip = title
        dot = getattr(self, "_status_capsule_dot", None)
        if dot is not None:
            show_dot = compact_top_chips and state in (
                "stopped",
                "starting",
                "running",
                "failed",
            )
            dot.setVisible(show_dot)
            if show_dot:
                dot.setProperty("state", state)
                dot.style().unpolish(dot)
                dot.style().polish(dot)
        self.status_banner.setProperty("state", state)
        self._polish_widget(self.status_banner)
        label = self.status_banner_text
        if isinstance(label, ElidedStatusLabel):
            label.set_full_text(display)
            label.setToolTip(tip)
        else:
            label.setText(display)
            label.setToolTip(tip)
        banner = self.status_banner
        if banner is not None:
            banner.setToolTip(tip)
        self._sync_modern_session_chrome()
        self._sync_modern_run_chrome()
        QtCore.QTimer.singleShot(0, self._sync_modern_status_banner_width)
        self._schedule_modern_header_layout()

    def _sync_modern_status_banner_width(self) -> None:
        """Refresh elided status text inside the header status pane."""
        if getattr(self, "_syncing_status_banner_width", False):
            return
        self._syncing_status_banner_width = True
        try:
            label = self.status_banner_text
            if isinstance(label, ElidedStatusLabel):
                label.refresh_elide()
            container = getattr(self, "_header_status_container", None)
            banner = getattr(self, "status_banner", None)
            if container is not None:
                container.setMaximumWidth(16777215)
            if banner is not None:
                banner.setMaximumWidth(16777215)
            if getattr(self, "_header_splitter", None) is not None:
                self._schedule_modern_header_layout()
        finally:
            self._syncing_status_banner_width = False

    def _sync_session_run_cluster_width(self) -> None:
        """Keep the run splitter pane wide enough for the visible Start/Stop control."""
        cluster = getattr(self, "_session_run_cluster", None)
        if cluster is None:
            return
        active = self.start_btn if self.start_btn.isVisible() else self.stop_btn
        active_w = max(active.sizeHint().width(), active.minimumSizeHint().width())
        pulse = getattr(self, "_session_pulse", None)
        pulse_w = (pulse.width() + 6) if pulse is not None and pulse.isVisible() else 0
        cluster.setMinimumWidth(max(session_run_cluster_min_width(), active_w + pulse_w + 4))

    def _sync_modern_run_chrome(self) -> None:
        """Single run control: Start when idle, Stop + pulse when running."""
        running = self._is_bridge_running()
        starting = bool(getattr(self, "_starting", False))
        self.start_btn.setVisible(not running and not starting)
        self.stop_btn.setVisible(running or starting)
        self.start_btn.setText("▶  Start")
        if starting:
            self.stop_btn.setText("…  Starting")
        else:
            self.stop_btn.setText("■  Stop")
        self._sync_session_run_cluster_width()
        pane_run = getattr(self, "_header_pane_run", None)
        if pane_run is not None:
            pane_run.setMinimumWidth(header_split_mins()[0])
        pulse = getattr(self, "_session_pulse", None)
        timer = getattr(self, "_session_pulse_timer", None)
        if pulse is not None:
            pulse.setVisible(running)
            if running:
                pulse.setProperty("active", "true")
                self._polish_widget(pulse)
        if timer is not None:
            logging_active = self._file_log_header_active()[0]
            if running or logging_active:
                if not timer.isActive():
                    timer.start()
            else:
                timer.stop()
        self._sync_modern_logging_indicator()

    def _build_modern_logging_indicator(self) -> None:
        self._logging_indicator = QtWidgets.QFrame()
        self._logging_indicator.setObjectName("modernLoggingIndicator")
        self._logging_indicator.hide()
        lay = QtWidgets.QHBoxLayout(self._logging_indicator)
        lay.setContentsMargins(4, 0, 6, 0)
        lay.setSpacing(4)
        self._logging_pulse = QtWidgets.QLabel("")
        self._logging_pulse.setObjectName("modernLoggingPulse")
        self._logging_pulse.setFixedSize(8, 8)
        self._logging_pulse.setProperty("pulseOn", "true")
        self._logging_label = QtWidgets.QLabel("Logging")
        self._logging_label.setObjectName("modernLoggingLabel")
        self._logging_indicator.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        lay.addWidget(
            self._logging_pulse,
            0,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        lay.addWidget(
            self._logging_label,
            0,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        self._wire_modern_logging_indicator()

    def _wire_modern_logging_indicator(self) -> None:
        ind = self._logging_indicator
        ind.setProperty("clickable", True)
        ind.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        opener = self._open_file_log_location
        filt = _ModernStatusBannerClickFilter(opener, ind)
        ind.installEventFilter(filt)
        for child in (self._logging_pulse, self._logging_label):
            child.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            child.installEventFilter(filt)
        self._modern_logging_click_filter = filt

    def _file_log_header_active(self) -> tuple[bool, str]:
        chk = getattr(self, "chk_file_log", None)
        enabled = bool(chk.isChecked()) if chk is not None else False
        if not enabled or not self._is_bridge_running():
            return False, ""
        fl = getattr(self, "_file_log", None)
        if fl is None:
            return False, ""
        return True, str(getattr(fl, "path", "") or "")

    def _sync_modern_logging_indicator(self) -> None:
        ind = getattr(self, "_logging_indicator", None)
        pulse = getattr(self, "_logging_pulse", None)
        if ind is None:
            return
        active, path = self._file_log_header_active()
        ind.setVisible(active)
        if active:
            tip = f"Recording to {path}\nClick to open the log folder."
            ind.setToolTip(tip)
            lbl = getattr(self, "_logging_label", None)
            if lbl is not None:
                lbl.setToolTip(tip)
            if pulse is not None:
                pulse.setProperty("pulseOn", "true")
                self._polish_widget(pulse)
        QtCore.QTimer.singleShot(0, self._sync_header_trail_layout)

    def _tick_session_pulse(self) -> None:
        for pulse in (
            getattr(self, "_session_pulse", None),
            getattr(self, "_logging_pulse", None),
        ):
            if pulse is None or pulse.isHidden():
                continue
            on = str(pulse.property("pulseOn") or "").lower() != "true"
            pulse.setProperty("pulseOn", "true" if on else "false")
            self._polish_widget(pulse)

    def _sync_run_button_state(self) -> None:
        super()._sync_run_button_state()
        self._sync_modern_run_chrome()

    def _sync_modern_start_stop_labels(self) -> None:
        self._sync_modern_run_chrome()

    def _wire_modern_status_banner_nav(self) -> None:
        banner = self.status_banner
        label = self.status_banner_text
        banner.setProperty("clickable", True)
        banner.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        tip = "Open Control — COM port, baud, and network listen settings."
        banner.setToolTip(tip)
        label.setToolTip(label.full_text() or tip)
        opener = lambda: self._open_modern_section_by_sid("control")
        filt = _ModernStatusBannerClickFilter(opener, banner)
        banner.installEventFilter(filt)
        label.installEventFilter(filt)
        self._modern_status_banner_click_filter = filt

    def _sync_modern_phone_qr_btn(self) -> None:
        btn = getattr(self, "_btn_header_phone_qr", None)
        if btn is None:
            return
        chk = getattr(self, "chk_web_enabled", None)
        btn.setVisible(chk is not None and chk.isChecked())
        QtCore.QTimer.singleShot(0, self._sync_header_trail_layout)

    def _sync_modern_session_chrome(self) -> None:
        hdr = getattr(self, "_modern_global_header", None)
        running = self._is_bridge_running()
        if hdr is not None:
            hdr.setProperty("sessionMode", "true" if running else "false")
            hdr.style().unpolish(hdr)
            hdr.style().polish(hdr)
        self._sync_modern_phone_qr_btn()
        backup = getattr(self, "lbl_backup_status", None)
        com = getattr(self, "com_lock_chip", None)
        bp = getattr(self, "lbl_backpressure_chip", None)
        hz = getattr(self, "lbl_hz_chip", None)
        # hz, backup, com_lock chips are orphaned (not in header layout) in Modern UI —
        # their state is tracked for mixin logic but they stay hidden in the header.
        # Only backpressure chip appears in the header (critical data-loss warning).
        if not running:
            if bp is not None:
                bp.hide()
            if hz is not None:
                hz.hide()
            QtCore.QTimer.singleShot(0, self._sync_header_trail_layout)
            return
        if bp is not None and not bp.isHidden():
            bp.show()
        if hz is not None and not hz.isHidden():
            hz.show()
        QtCore.QTimer.singleShot(0, self._sync_header_trail_layout)

    def _set_footer_running(self, running: bool) -> None:
        lbl = getattr(self, "lbl_stats", None)
        if lbl is not None:
            lbl.setProperty("bridgeRunning", "true" if running else "false")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def _on_bridge_started(self, b) -> None:
        super()._on_bridge_started(b)
        self._set_footer_running(True)
        self._sync_modern_start_stop_labels()
        # Smart-Peek: Activity first; return to Control when wire traffic arrives.
        self._smart_peek_pending = True
        try:
            self._open_modern_section_by_sid("activity")
        except Exception:
            pass

    def _stats_from_bridge(self, d: dict) -> None:
        super()._stats_from_bridge(d)
        stats = getattr(self, "_bridge_stats_cache", {})
        if not isinstance(stats, dict):
            stats = {}
        if not stats and isinstance(d, dict):
            stats = d
        self._maybe_finish_smart_peek(stats)

    def _maybe_finish_smart_peek(self, stats: dict) -> None:
        if not getattr(self, "_smart_peek_pending", False):
            return
        if not bridge_stats_show_live_traffic(stats):
            return
        if self._modern_current_section_sid() != "activity":
            self._smart_peek_pending = False
            return
        self._smart_peek_pending = False
        try:
            self._open_modern_section_by_sid("control")
        except Exception:
            pass

    def _modern_current_section_sid(self) -> str:
        stack = getattr(self, "_tools_stack", None)
        if stack is None:
            return ""
        idx = stack.currentIndex()
        return str(getattr(self, "_modern_sid_by_stack_index", {}).get(idx, ""))

    def stop_bridge(self) -> None:
        self._smart_peek_pending = False
        super().stop_bridge()
        self._set_footer_running(False)
        self._sync_modern_start_stop_labels()
        self._sync_modern_session_chrome()
        QtCore.QTimer.singleShot(0, self._sync_modern_status_banner_width)
        QtCore.QTimer.singleShot(120, self._sync_modern_status_banner_width)

    def _apply_modern_stylesheet(self) -> None:
        from ui.styles import apply_global_contrast_guard

        self._load_theme_zone_colors_for_active_theme()
        self.setStyleSheet(apply_modern_theme_colors(self._theme_zone_colors))
        self._refresh_theme_zone_buttons()
        self._sync_header_chip_fade_edges()
        apply_global_contrast_guard(QtWidgets.QApplication.instance())

    def _randomize_theme_now(self) -> None:
        self._log_ui("[UI] Theme randomization is not available in Modern layout.")

    def _standardize_theme_now(self) -> None:
        self._apply_theme(THEME_SLATE)

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def _init_fleet_supervisor(self) -> None:
        from core.fleet.supervisor import FleetSupervisor
        from ui.fleet_panel import FleetPanelWidget

        if getattr(self, "_fleet_supervisor", None) is not None:
            return
        self._fleet_supervisor = FleetSupervisor(self)
        panel = getattr(self, "_fleet_panel", None)
        if isinstance(panel, FleetPanelWidget):
            panel.attach_supervisor(self._fleet_supervisor)

    def _on_ui_ready(self) -> None:
        self._set_status_banner(
            "stopped", "Stopped", "Set COM & UDP, then Start."
        )
        self._refresh_intent_hint()
        self._apply_modern_stylesheet()
        self._sync_modern_start_stop_labels()
        self._refresh_tools_page_status()
        self._init_fleet_supervisor()
        sup = getattr(self, "_fleet_supervisor", None)
        if sup is not None:
            sup.apply_auto_start_if_enabled()

    def _modern_tools_content_width(self) -> int:
        """Approximate tools stack width (window minus sidebar or chip rail padding)."""
        w = self.width()
        if getattr(self, "_modern_tools_nav_mode", "sidebar") == "top_chips":
            return max(320, w - 24)
        if getattr(self, "_modern_sidebar_collapsed", False):
            return max(320, w - MODERN_SIDEBAR_COLLAPSED_W)
        return max(320, w - MODERN_SIDEBAR_EXPANDED_W)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        refresh_status_bar_labels(self)
        self._sync_modern_status_banner_width()
        self._apply_control_forms_responsive(event.size().width())
        from ui.tool_tabs import apply_phone_dashboard_responsive

        apply_phone_dashboard_responsive(self, self._modern_tools_content_width())
        self._schedule_modern_header_layout()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._apply_modern_stylesheet()
        self._sync_modern_phone_qr_btn()
        QtCore.QTimer.singleShot(0, self._ensure_modern_launch_layout)
        QtCore.QTimer.singleShot(120, self._ensure_modern_launch_layout)
        QtCore.QTimer.singleShot(0, self._sync_modern_status_banner_width)

    def changeEvent(self, event: QtCore.QEvent) -> None:
        super().changeEvent(event)
        if event.type() != QtCore.QEvent.Type.WindowStateChange:
            return
        if not self.windowState() & QtCore.Qt.WindowState.WindowMinimized:
            return
        if not self._is_bridge_running():
            return
        if getattr(self, "_tray_icon", None) is None:
            return
        try:
            QtCore.QTimer.singleShot(0, self._hide_to_tray)
        except Exception:
            pass

    def _show_modern_pipeline_tab(self) -> None:
        self._open_modern_section_by_sid("activity")

    def _hide_mission_review_tab(self) -> None:
        hide_mission_review_tab(self)

    def _reveal_mission_review_tab(
        self, record: object, summary: dict[str, object]
    ) -> None:
        from ui.mission_review import reveal_mission_review_tab

        reveal_mission_review_tab(self, record, summary)  # type: ignore[arg-type]
