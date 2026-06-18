"""Modern UI — persistent header + collapsible Tools sidebar + main content pane.

Layout stack (top to bottom):
  ┌─ Global Header — Start/Stop · status · pills · View/HUD/Layout ─────────┐
  ├─ Body: [Tools sidebar | main content stack]                              │
  └─ Footer strip — version ─────────────────────────────────────────────────┘

Smart-Peek: bridge start auto-navigates to Logging → Activity.
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
from ui.modern_styles import MODERN_TEXT, modern_stylesheet
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
    "NMEA": "Passthrough, strict, or raw binary",
    "Dashboard": "Web API, token, and QR dashboard",
    "Black box": "Raw session capture (.raw)",
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
    "Settings": "presets",
    "Mission Review": "mission_review",
    "Activity": "activity",
    "Control": "control",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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
        self.setMinimumSize(640, 420)

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
        bl.setSpacing(0)
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
        self.status_banner.setMinimumWidth(0)
        self._wire_modern_status_banner_nav()

        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("modernToolsLiveStatus")
        self.intent_hint.setWordWrap(False)
        self._compact_intent_hint = True

        self.start_btn.setObjectName("modernStartBtn")
        self.start_btn.setText("▶  Start")
        self.start_btn.setFixedHeight(28)
        self.stop_btn.setObjectName("modernStopBtn")
        self.stop_btn.setText("■  Stop")
        self.stop_btn.setFixedHeight(28)

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

        nav_mode = str(load_modern_layout_prefs().get("tools_nav_mode", "sidebar"))
        self._apply_modern_tools_nav_mode(nav_mode, persist=False)
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
        row.setSpacing(6)

        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(_vsep())

        self._header_status_container = QtWidgets.QWidget()
        self._header_status_container.setObjectName("modernHeaderStatusContainer")
        self._header_status_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._header_status_container.setMinimumWidth(0)
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
        row.addWidget(self._header_status_container, 1)

        self._btn_header_guide = QtWidgets.QToolButton()
        self._btn_header_guide.setObjectName("modernHeaderChipBtn")
        self._btn_header_guide.setText("📖  Guide")
        self._btn_header_guide.setToolTip(
            "Open the operator guide — connect steps, UDP/TCP modes, and bench checklists."
        )
        self._btn_header_guide.clicked.connect(
            lambda: self._open_modern_section_by_sid("guide")
        )
        row.addWidget(self._btn_header_guide, 0)

        # Backpressure chip — only visible when packets are being dropped (critical)
        row.addWidget(self.lbl_backpressure_chip, 0)

        # Phone / dashboard shortcut — only visible when Web API is enabled
        self._btn_header_phone_qr = QtWidgets.QToolButton()
        self._btn_header_phone_qr.setObjectName("modernHeaderQrBtn")
        self._btn_header_phone_qr.setText("📱")
        self._btn_header_phone_qr.setToolTip(
            "Open local dashboard in your browser (Web API on this PC)."
        )
        self._btn_header_phone_qr.setFixedSize(28, 28)
        self._btn_header_phone_qr.clicked.connect(self._on_web_open_dashboard)
        self._btn_header_phone_qr.hide()
        row.addWidget(self._btn_header_phone_qr, 0)

        row.addWidget(_vsep())

        # Layout-control cluster (View / HUD / Layout) from survey_top_bar
        self._modern_header_nav = QtWidgets.QWidget()
        self._modern_header_nav.setObjectName("modernHeaderNav")
        self._modern_header_nav.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._modern_header_nav.setMinimumWidth(0)
        nav_lay = QtWidgets.QHBoxLayout(self._modern_header_nav)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(4)
        row.addWidget(self._modern_header_nav, 0)

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

    def _sync_modern_embedded_topbar_chrome(self, bar=None) -> None:
        """Keep only View/HUD/Layout in the header; re-apply after UI editor saves."""
        bar = bar or getattr(self, "_survey_top_bar", None)
        if bar is None:
            return
        try:
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
        bar.rebuild()
        self._apply_modern_header_nav_button_palettes(bar)

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
        if mode == "top_chips" and chip_rail is not None:
            chip_rail.setFixedHeight(MODERN_CHIP_RAIL_H)
            chip_rail.show()

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
            QtWidgets.QSizePolicy.Policy.Maximum,
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
        left_lay.addWidget(self._control_forms_host, 0)
        left_lay.addWidget(preset_bar, 0)
        left_lay.addStretch(1)

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
                        left_lay.addWidget(self._control_forms_host, 0)
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
            return

        grid.removeWidget(serial)
        grid.removeWidget(network)
        if stack_vertical:
            grid.addWidget(serial, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.addWidget(network, 1, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 0)
            grid.setRowStretch(0, 0)
            grid.setRowStretch(1, 0)
        else:
            grid.addWidget(serial, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.addWidget(network, 0, 1, QtCore.Qt.AlignmentFlag.AlignTop)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            grid.setRowStretch(0, 0)
            grid.setRowStretch(1, 0)
        self._control_forms_vertical = stack_vertical

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
            build_modern_guide_page,
            build_modern_hub_page,
            build_modern_inject_page,
            build_modern_nmea_page,
            build_modern_phone_page,
            build_modern_presets_page,
            build_modern_terminal_page,
            build_modern_tools_nav,
            build_modern_tools_nav_groups,
        )

        live_activity = self._wrap_live_activity_page(activity_panel)
        page_builders = {
            "control": lambda: control_panel,
            "hub": lambda: build_modern_hub_page(self),
            "presets": lambda: build_modern_presets_page(self),
            "nmea": lambda: build_modern_nmea_page(self),
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

        for btn in getattr(self, "_tools_chip_dropdowns", []):
            child_sids = btn.property("navChildSids")
            if not isinstance(child_sids, list):
                child_sids = []
            active = active_sid in child_sids
            btn.setProperty("navActive", active)
            btn.setProperty("navActiveChildSid", active_sid if active else "")
            default_text = btn.property("navDefaultText")
            if active and active_sid:
                icon_by_label = getattr(self, "_modern_tools_icon_by_label", {})
                for lbl, sid in getattr(self, "_modern_tools_sid_by_label", {}).items():
                    if sid == active_sid:
                        icon = icon_by_label.get(lbl, "")
                        btn.setText(f"{icon}  {lbl}" if icon else lbl)
                        break
            elif default_text:
                btn.setText(str(default_text))
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

    def _apply_modern_tools_nav_mode(self, mode: str, *, persist: bool) -> None:
        normalized = "top_chips" if str(mode).strip().lower() == "top_chips" else "sidebar"
        self._modern_tools_nav_mode = normalized
        top_chips = normalized == "top_chips"

        sidebar = getattr(self, "_modern_sidebar_scroll", None)
        sep = getattr(self, "_modern_sidebar_sep", None)
        chip_rail = getattr(self, "_modern_tools_chip_rail", None)
        if sidebar is not None:
            sidebar.setVisible(not top_chips)
        if sep is not None:
            sep.setVisible(not top_chips)
        if chip_rail is not None:
            chip_rail.setVisible(top_chips)

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
        self._refresh_modern_tools_nav_mode_menu()

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
            QtWidgets.QSizePolicy.Policy.Maximum,
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

    def _build_serial_group(self) -> QtWidgets.QFrame:
        card, lay = self._modern_control_form_card("Serial link", icon="🔌")
        fl = QtWidgets.QFormLayout()
        fl.setVerticalSpacing(10)
        fl.setHorizontalSpacing(12)
        fl.setLabelAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        com_row = QtWidgets.QHBoxLayout()
        com_row.setSpacing(8)
        self.com_cb.setMinimumHeight(34)
        com_row.addWidget(self.com_cb, 1)
        com_row.addWidget(self.refresh_btn)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(com_row)
        fl.addRow(self._control_form_label("COM port"), wrap)
        self.baud_edit.setMinimumHeight(34)
        fl.addRow(self._control_form_label("Baud"), self.baud_edit)
        fl.addRow("", self.chk_serial_auto_reconnect)
        fl.addRow("", self.chk_auto_discover)
        lay.addLayout(fl)
        return card

    def _build_network_group(self) -> QtWidgets.QFrame:
        card, lay = self._modern_control_form_card("Network path", icon="📡")
        body = QtWidgets.QVBoxLayout()
        body.setSpacing(10)
        fl = QtWidgets.QFormLayout()
        fl.setVerticalSpacing(10)
        fl.setHorizontalSpacing(12)
        fl.setLabelAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.udp_host.setMinimumHeight(34)
        self.udp_port.setMinimumHeight(34)
        fl.addRow(self._control_form_label("Listen host"), self.udp_host)
        fl.addRow(self._control_form_label("Listen port"), self.udp_port)
        body.addLayout(fl)
        fan = QtWidgets.QHBoxLayout()
        fan.addWidget(self.chk_udp_fanout, 1)
        fan.addWidget(
            create_network_help_button(self),
            0,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        body.addLayout(fan)
        body.addWidget(self.chk_tcp_sink_enable)
        port_row = QtWidgets.QHBoxLayout()
        port_row.setContentsMargins(18, 0, 0, 0)
        port_row.setSpacing(8)
        port_row.addWidget(self._control_form_label("Mirror port"), 0)
        self.tcp_sink_port.setFixedWidth(76)
        self.tcp_sink_port.setMaximumWidth(88)
        self.tcp_sink_port.setMinimumHeight(32)
        port_row.addWidget(self.tcp_sink_port, 0)
        port_row.addStretch(1)
        body.addLayout(port_row)
        body.addWidget(self.chk_advanced_net)
        body.addWidget(self._advanced_net)
        lay.addLayout(body)
        return card

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

    def _modern_tools_nav_button(
        self,
        label: str,
        icon: str,
        idx: int,
        buttons: list[QtWidgets.QPushButton],
        stack: QtWidgets.QStackedWidget,
    ) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(f"  {icon}  {label}")
        btn.setObjectName("modernSettingsNavBtn")
        btn.setProperty("navLabel", label)
        btn.setProperty("navIcon", icon)
        btn.setProperty("navIndex", idx)
        btn.setCheckable(True)
        btn.setProperty("navActive", False)
        btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda _checked, i=idx: self._tools_nav_select(i))
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

        nav_leaves, nav_dropdowns = build_modern_tools_nav_tiers()
        from ui.tool_tabs import sort_modern_nav_by_saved_order

        nav_leaves = sort_modern_nav_by_saved_order(nav_leaves, visible_names)
        nav_dropdowns = sort_modern_nav_by_saved_order(
            nav_dropdowns, visible_names, tier=True
        )

        for sid, lbl, icon in nav_leaves:
            if sid in MODERN_HEADER_NAV_SIDS or lbl not in visible_set:
                continue
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

        visible_names = self._visible_tools_tab_names(key)
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
            btn = self._modern_tools_nav_button(name, icon, stack_idx, nav_buttons, stack)
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
            visible_names,
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
        compact_title = title.strip()
        if detail.strip():
            compact_title = f"{compact_title}  ·  {detail.strip()}"
        self.status_banner.setProperty("state", state)
        self._polish_widget(self.status_banner)
        label = self.status_banner_text
        if isinstance(label, ElidedStatusLabel):
            label.set_full_text(compact_title)
        else:
            label.setText(compact_title)
        self._sync_modern_session_chrome()
        self._sync_modern_start_stop_labels()

    def _sync_modern_status_banner_width(self) -> None:
        """Refresh elided status text when header geometry changes."""
        label = self.status_banner_text
        if isinstance(label, ElidedStatusLabel):
            label.refresh_elide()

    def _sync_modern_start_stop_labels(self) -> None:
        if self._is_bridge_running():
            self.start_btn.setText("Running…")
        elif getattr(self, "_starting", False):
            self.start_btn.setText("Starting…")
        else:
            self.start_btn.setText("▶  Start")
        self.stop_btn.setText("■  Stop")

    def _wire_modern_status_banner_nav(self) -> None:
        banner = self.status_banner
        label = self.status_banner_text
        banner.setProperty("clickable", True)
        banner.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        tip = "Open Control — COM port, baud, and network listen settings."
        banner.setToolTip(tip)
        label.setToolTip(tip)
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
            return
        if bp is not None and not bp.isHidden():
            bp.show()
        if hz is not None and not hz.isHidden():
            hz.show()

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
        # Smart-Peek: navigate to Activity tab so the operator sees data immediately
        try:
            self._open_modern_section_by_sid("activity")
        except Exception:
            pass

    def stop_bridge(self) -> None:
        super().stop_bridge()
        self._set_footer_running(False)
        self._sync_modern_start_stop_labels()
        self._sync_modern_session_chrome()

    # ── Theme lock ─────────────────────────────────────────────────────────

    def _apply_modern_stylesheet(self) -> None:
        self.setStyleSheet("")
        self.setStyleSheet(modern_stylesheet())
        from ui.styles import apply_global_contrast_guard

        apply_global_contrast_guard(QtWidgets.QApplication.instance())

    def _apply_theme(self, theme_id: str, *, persist: bool = True) -> None:
        _ = theme_id, persist
        self._theme_id = THEME_SLATE
        self._apply_modern_stylesheet()
        pop = getattr(self, "_stats_popout_window", None)
        if pop is not None:
            try:
                pop.set_theme(THEME_SLATE)
            except RuntimeError:
                self._stats_popout_window = None

    def _randomize_theme_now(self) -> None:
        self._log_ui("[UI] Modern keeps a fixed palette — random theme skipped.")
        self._apply_modern_stylesheet()

    def _standardize_theme_now(self) -> None:
        self._apply_modern_stylesheet()

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def _on_ui_ready(self) -> None:
        self._set_status_banner(
            "stopped", "Stopped", "Set COM & UDP, then Start."
        )
        self._refresh_intent_hint()
        self._apply_modern_stylesheet()
        self._sync_modern_start_stop_labels()
        self._refresh_tools_page_status()

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
