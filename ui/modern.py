"""Modern UI — tab-per-panel with persistent Global Header Strip.

Layout stack (top to bottom):
  ┌─ Survey bar (38 px)         — nav chips inserted by mixin ─────────────┐
  ├─ Global Header Strip (40 px) — Start/Stop · Status · COM — always on  ─┤
  ├─ Command Tab Bar (32 px)     — Log | Control | Hub | Settings | Telem  ─┤
  │  Content area (fills)                                                   │
  └─ Footer strip (24 px)        — backup status · version ────────────────┘

New in this revision:
  • Persistent Global Header Strip — run controls and status are always
    visible regardless of which tab is active.
  • Smart-Peek — bridge start auto-navigates to the Log tab.
  • _QuickViewPopup — hover over the "Telemetry" or "Hub" tab header to see
    a 3-line non-modal status preview without leaving the current tab.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.connect_panels import configure_connect_status_banner
from ui.connection_hub import ConnectionHubWidget
from ui.controls import (
    create_connection_controls,
    create_guide_tab,
    create_log_panel,
    create_nmea_controls,
    create_phone_dashboard_tab,
    create_presets_tab,
    create_send_controls,
    create_system_terminal_tab,
    refresh_status_bar_labels,
)
from ui.bridge_terminal import create_bridge_terminal_tab
from ui.mixin import BridgeLogicMixin
from ui.mission_review import create_mission_review_tab, hide_mission_review_tab
from ui.modern_styles import modern_stylesheet
from ui.network_help import create_network_help_button
from ui.theme_choice import THEME_SLATE
from ui.ui_prefs import CONFIG_PATH
from version import __version__


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vsep() -> QtWidgets.QFrame:
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    s.setObjectName("modernFooterSep")
    return s


def _make_telem_chip(title: str, value: QtWidgets.QLabel) -> QtWidgets.QFrame:
    card = QtWidgets.QFrame()
    card.setObjectName("modernTelemetryCard")
    row = QtWidgets.QHBoxLayout(card)
    row.setContentsMargins(15, 8, 15, 8)
    row.setSpacing(12)
    heading = QtWidgets.QLabel(title.upper())
    heading.setObjectName("modernTelemetryTitle")
    heading.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    value.setObjectName("modernTelemetryValue")
    value.setWordWrap(False)
    row.addWidget(heading)
    row.addWidget(value, 1)
    return card


# ─────────────────────────────────────────────────────────────────────────────
# Quick-View Popup
# ─────────────────────────────────────────────────────────────────────────────

class _QuickViewPopup(QtWidgets.QFrame):
    """Non-modal hover preview for Telemetry / Hub tab headers.

    Positioned just below the hovered tab chip; shows three key metrics.
    Mouse-transparent so it doesn't interfere with tab interaction.
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("quickViewPopup")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)

        self._title_lbl = QtWidgets.QLabel()
        self._title_lbl.setObjectName("quickViewTitle")
        lay.addWidget(self._title_lbl)

        self._key_lbls: list[QtWidgets.QLabel] = []
        self._val_lbls: list[QtWidgets.QLabel] = []
        for _ in range(3):
            row_w = QtWidgets.QWidget()
            row_w.setObjectName("quickViewRow")
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            k = QtWidgets.QLabel()
            k.setObjectName("quickViewKey")
            v = QtWidgets.QLabel()
            v.setObjectName("quickViewVal")
            row.addWidget(k)
            row.addWidget(v, 1)
            lay.addWidget(row_w)
            self._key_lbls.append(k)
            self._val_lbls.append(v)

    def populate(self, title: str, items: list[tuple[str, str]]) -> None:
        self._title_lbl.setText(title.upper())
        for i, (k, v) in enumerate(zip(self._key_lbls, self._val_lbls)):
            if i < len(items):
                k.setText(items[i][0])
                v.setText(items[i][1])
                k.setVisible(True)
                v.setVisible(True)
            else:
                k.setVisible(False)
                v.setVisible(False)

    def position_below_tab(
        self,
        tab_bar: QtWidgets.QTabBar,
        tab_index: int,
        main_win: QtWidgets.QWidget,
    ) -> None:
        rect = tab_bar.tabRect(tab_index)
        global_bl = tab_bar.mapToGlobal(QtCore.QPoint(rect.left(), rect.bottom()))
        local = main_win.mapFromGlobal(global_bl)
        self.adjustSize()
        x = max(0, min(local.x(), main_win.width() - self.width()))
        self.move(x, local.y() + 4)
        self.raise_()


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
        self.setMinimumSize(860, 540)

        self._init_bridge_state()
        create_connection_controls(self)
        self._apply_modern_stylesheet()

        # ── Persistent chrome widgets ─────────────────────────────────────
        # Status banner — compact inline horizontal
        self.status_banner = QtWidgets.QFrame()
        self.status_banner.setObjectName("modernStatusBanner")
        self.status_banner.setProperty("state", "stopped")
        bl = QtWidgets.QHBoxLayout(self.status_banner)
        bl.setContentsMargins(10, 0, 10, 0)
        bl.setSpacing(0)
        self.status_banner_text = QtWidgets.QLabel("Stopped")
        self.status_banner_text.setObjectName("modernStatusBannerText")
        self.status_banner_text.setWordWrap(False)
        bl.addWidget(self.status_banner_text)
        configure_connect_status_banner(self.status_banner, self.status_banner_text)

        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("modernIntentHint")
        self.intent_hint.setWordWrap(True)

        self.start_btn.setObjectName("modernStartBtn")
        self.start_btn.setText("▶  Start")
        self.start_btn.setFixedHeight(28)
        self.stop_btn.setObjectName("modernStopBtn")
        self.stop_btn.setText("■  Stop")
        self.stop_btn.setFixedHeight(28)

        # Telemetry labels
        self.status_serial  = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.status_nmea    = QtWidgets.QLabel("NMEA: passthrough")
        self.status_nmea.setToolTip("NMEA mode for the current session.")
        self.status_gnss    = QtWidgets.QLabel("GNSS: —")
        self.status_gnss.setToolTip("Live GGA fix while Running.")
        self.lbl_stats      = QtWidgets.QLabel("Stopped")
        self.lbl_stats.setObjectName("lblStats")

        # Hidden statusBar — mixin compat only
        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusBar.setMaximumHeight(0)
        self.statusBar.setVisible(False)

        # ── Global Header Strip (persistent, above tab bar) ───────────────
        global_hdr = self._build_global_header()

        # ── Tab contents ──────────────────────────────────────────────────
        log_tab      = create_log_panel(self, show_header=True)
        control_tab  = self._build_control_tab()
        wire_tab     = create_bridge_terminal_tab(self)
        # Settings (Diagnostics) must be built BEFORE hub_tab so that when
        # _build_hub_tab assigns self.connection_hub, it wins over the one
        # that mount_connection_hub_on_diagnostics would otherwise create.
        settings_tab = self._build_settings_tab()
        hub_tab      = self._build_hub_tab()
        telem_tab    = self._build_telem_tab()

        # ── Command tab widget ────────────────────────────────────────────
        self._modern_main_tabs = QtWidgets.QTabWidget()
        self._modern_main_tabs.setObjectName("modernMainTabs")
        self._modern_main_tabs.setDocumentMode(True)
        self._modern_main_tabs.setMovable(True)

        self._modern_main_tabs.addTab(log_tab,      "Log")
        self._modern_main_tabs.addTab(control_tab,  "Control")
        self._modern_main_tabs.addTab(wire_tab,     "Wire")
        self._modern_main_tabs.addTab(hub_tab,      "Hub")
        self._modern_main_tabs.addTab(settings_tab, "Settings")
        self._modern_main_tabs.addTab(telem_tab,    "Telemetry")

        mission_panel = create_mission_review_tab(self)
        self._mission_review_tab_index = self._modern_main_tabs.addTab(
            mission_panel, "Mission Review"
        )
        self._modern_main_tabs.setTabVisible(self._mission_review_tab_index, False)

        self._restore_active_tab()
        self._modern_main_tabs.currentChanged.connect(self._save_active_tab)

        # ── Footer (24 px: backup status + version) ───────────────────────
        footer = self._build_status_footer()

        # ── Shell layout ──────────────────────────────────────────────────
        # Order after _finalize_ui(): [survey_bar, global_hdr, tabs, footer]
        shell = QtWidgets.QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(global_hdr, 0)
        shell.addWidget(self._modern_main_tabs, 1)
        shell.addWidget(footer, 0)

        self._finalize_ui()

        # ── Tighten chip spacing; reset any skewed chip weights ───────────
        self._modernize_survey_bar()

        # ── Quick-View hover on Telemetry / Hub tab headers ───────────────
        self._install_quick_view_hover()

        # ── Hub: one-shot auto-scan on first visit ────────────────────────
        self._hub_auto_refreshed = False
        self._modern_main_tabs.currentChanged.connect(self._on_modern_tab_changed)

    # ── Global Header Strip ────────────────────────────────────────────────

    def _build_global_header(self) -> QtWidgets.QFrame:
        """Persistent strip: Start/Stop · status · version · COM chip."""
        hdr = QtWidgets.QFrame()
        hdr.setObjectName("modernGlobalHeader")
        row = QtWidgets.QHBoxLayout(hdr)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(8)

        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(_vsep())
        row.addWidget(self.status_banner, 1)
        row.addWidget(_vsep())

        ver = QtWidgets.QLabel(f"v{__version__}  ·  modern")
        ver.setObjectName("globalHeaderVersion")
        row.addWidget(ver)
        row.addWidget(_vsep())

        row.addWidget(self.com_lock_chip)
        return hdr

    # ── Survey bar tuning ─────────────────────────────────────────────────

    def _modernize_survey_bar(self) -> None:
        """Reduce inter-chip gap, hide irrelevant chips, and reset skewed
        chip weights so no label is truncated with an ellipsis."""
        bar = getattr(self, "_survey_top_bar", None)
        if bar is None:
            return
        # Tighten gap between chips: SurveyTopBar hard-codes 8 px; use 4 px.
        try:
            bar._track_lay.setSpacing(4)
        except AttributeError:
            pass
        # Modern has a fixed dark stylesheet — theme randomizer chips are noise.
        try:
            bar._hidden.add("randomize_theme")
            bar._hidden.add("standardize_theme")
        except AttributeError:
            pass
        # Reset chip weights to natural text widths so no chip is forced into
        # compact/ellipsis mode.  Weights are proportional, so text-derived
        # values keep wider labels wider than shorter ones.
        try:
            for key, chip in bar._chips.items():
                natural = chip.natural_total_width(compact=False)
                bar._chip_weights[key] = max(float(natural), 64.0)
            bar.rebuild()
            bar._emit_persist()
        except AttributeError:
            pass

    # ── Hub one-shot auto-discovery ───────────────────────────────────────

    def _on_modern_tab_changed(self, index: int) -> None:
        """When the Hub tab is first opened, trigger a discovery scan."""
        try:
            if self._hub_auto_refreshed:
                return
            if self._modern_main_tabs.tabText(index).strip() == "Hub":
                self._hub_auto_refreshed = True
                QtCore.QTimer.singleShot(150, self._on_hub_refresh_discovery)
        except Exception:
            pass

    # ── Quick-View hover preview ───────────────────────────────────────────

    def _install_quick_view_hover(self) -> None:
        self._qv_popup = _QuickViewPopup(self)
        self._qv_hovered_idx = -1

        self._qv_show_timer = QtCore.QTimer(self)
        self._qv_show_timer.setSingleShot(True)
        self._qv_show_timer.setInterval(320)
        self._qv_show_timer.timeout.connect(self._on_qv_show)

        self._qv_hide_timer = QtCore.QTimer(self)
        self._qv_hide_timer.setSingleShot(True)
        self._qv_hide_timer.setInterval(180)
        self._qv_hide_timer.timeout.connect(self._on_qv_hide)

        tab_bar = self._modern_main_tabs.tabBar()
        tab_bar.setMouseTracking(True)
        tab_bar.installEventFilter(self)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        try:
            tab_bar = self._modern_main_tabs.tabBar()
            if watched is tab_bar:
                etype = event.type()
                if etype == QtCore.QEvent.Type.MouseMove:
                    pos = event.pos()  # type: ignore[attr-defined]
                    idx = tab_bar.tabAt(pos)
                    preview_tabs = {"Telemetry", "Hub"}
                    tab_name = (
                        self._modern_main_tabs.tabText(idx) if idx >= 0 else ""
                    )
                    if tab_name in preview_tabs:
                        if idx != self._qv_hovered_idx:
                            self._qv_hovered_idx = idx
                            self._qv_hide_timer.stop()
                            self._qv_show_timer.start()
                    else:
                        if self._qv_hovered_idx >= 0:
                            self._qv_hovered_idx = -1
                            self._qv_show_timer.stop()
                            self._qv_hide_timer.start()
                elif etype in (
                    QtCore.QEvent.Type.Leave,
                    QtCore.QEvent.Type.MouseButtonPress,
                ):
                    self._qv_hovered_idx = -1
                    self._qv_show_timer.stop()
                    self._qv_hide_timer.start()
        except Exception:
            pass
        return super().eventFilter(watched, event)

    def _on_qv_show(self) -> None:
        try:
            idx = self._qv_hovered_idx
            if idx < 0:
                return
            tab_name = self._modern_main_tabs.tabText(idx)
            tab_bar  = self._modern_main_tabs.tabBar()
            if tab_name == "Telemetry":
                items = [
                    ("SERIAL",  self.status_serial.text()),
                    ("NETWORK", self.status_network.text()),
                    ("SESSION", self.lbl_stats.text()),
                ]
            elif tab_name == "Hub":
                items = [
                    ("COM",    self.com_lock_chip.text()),
                    ("PORT",   self.udp_port.text()),
                    ("STATUS", self.status_banner_text.text()),
                ]
            else:
                return
            self._qv_popup.populate(tab_name, items)
            self._qv_popup.position_below_tab(tab_bar, idx, self)
            self._qv_popup.show()
        except Exception:
            pass

    def _on_qv_hide(self) -> None:
        try:
            self._qv_popup.hide()
            self._qv_hovered_idx = -1
        except Exception:
            pass

    # ── Tab content builders ──────────────────────────────────────────────

    def _build_control_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer.setObjectName("modernControlTab")
        lay = QtWidgets.QVBoxLayout(outer)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)
        cols = QtWidgets.QHBoxLayout()
        cols.setSpacing(16)
        cols.addWidget(self._build_serial_group(), 1)
        cols.addWidget(self._build_network_group(), 1)
        lay.addLayout(cols)
        lay.addWidget(self.intent_hint)
        lay.addStretch(1)
        return outer

    def _build_hub_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setObjectName("modernHubTab")
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        hub = ConnectionHubWidget(standalone=True)
        hub.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        hub.attach_bridge_window(self)
        self.connection_hub = hub
        lay.addWidget(hub, 1)
        # Release the fixed-height cap on the card scroll area so it grows to
        # fill the full tab instead of leaving a dead void below the 2-row limit.
        scroll = getattr(hub, "_card_scroll", None)
        if scroll is not None:
            scroll.setMinimumHeight(0)
            scroll.setMaximumHeight(16777215)  # Qt QWIDGETSIZE_MAX
            scroll.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
        return w

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        from ui.tool_tabs import build_diagnostics_tab

        outer = QtWidgets.QWidget()
        outer.setObjectName("modernSettingsPage")
        root = QtWidgets.QHBoxLayout(outer)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left sidebar nav ──────────────────────────────────────────────
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("modernSettingsSidebar")
        sidebar.setFixedWidth(152)
        sb_lay = QtWidgets.QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 8, 0, 8)
        sb_lay.setSpacing(2)

        nav_header = QtWidgets.QLabel("SETTINGS")
        nav_header.setObjectName("modernSettingsNavHeader")
        sb_lay.addWidget(nav_header)
        sb_lay.addSpacing(6)

        # ── Right content stack ───────────────────────────────────────────
        stack = QtWidgets.QStackedWidget()
        stack.setObjectName("modernSettingsStack")

        # (label, icon, content-widget)
        sections = [
            ("Presets",     "⚙",  create_presets_tab(self, include_advanced_net=False)),
            ("Phone",       "📱",  create_phone_dashboard_tab(self)),
            ("NMEA",        "📡",  create_nmea_controls(self)),
            ("Diagnostics", "🔍",  build_diagnostics_tab(self, skip_hub=True)),
            ("Inject",      "💉",  create_send_controls(self)),
            ("Terminal",    "⌨",  create_system_terminal_tab(self)),
            ("Guide",       "📖",  create_guide_tab(self)),
        ]

        nav_buttons: list[QtWidgets.QPushButton] = []

        def _make_nav_btn(label: str, icon: str, idx: int) -> QtWidgets.QPushButton:
            btn = QtWidgets.QPushButton(f"  {icon}  {label}")
            btn.setObjectName("modernSettingsNavBtn")
            btn.setCheckable(True)
            btn.setProperty("navActive", False)
            btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(lambda _checked, i=idx: self._settings_nav_select(i, nav_buttons, stack))
            return btn

        for i, (lbl, icon, widget) in enumerate(sections):
            stack.addWidget(widget)
            btn = _make_nav_btn(lbl, icon, i)
            nav_buttons.append(btn)
            sb_lay.addWidget(btn)

        sb_lay.addStretch(1)
        self._settings_nav_buttons = nav_buttons

        # Separator line between sidebar and content
        sep = QtWidgets.QFrame()
        sep.setObjectName("modernSettingsSep")
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)

        root.addWidget(sidebar)
        root.addWidget(sep)
        root.addWidget(stack, 1)

        # Activate first entry
        self._settings_nav_select(0, nav_buttons, stack)
        self._settings_stack = stack
        return outer

    def _settings_nav_select(
        self,
        index: int,
        buttons: list,
        stack: QtWidgets.QStackedWidget,
    ) -> None:
        try:
            stack.setCurrentIndex(index)
            for i, btn in enumerate(buttons):
                active = i == index
                btn.setChecked(active)
                btn.setProperty("navActive", active)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        except Exception:
            pass

    def _build_telem_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer.setObjectName("modernTelemTab")
        lay = QtWidgets.QVBoxLayout(outer)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(8)
        title = QtWidgets.QLabel("Live Telemetry")
        title.setObjectName("modernTabSectionTitle")
        lay.addWidget(title)
        for label, lbl in (
            ("Serial",  self.status_serial),
            ("Network", self.status_network),
            ("NMEA",    self.status_nmea),
            ("GNSS",    self.status_gnss),
            ("Session", self.lbl_stats),
        ):
            lay.addWidget(_make_telem_chip(label, lbl))
        lay.addStretch(1)
        return outer

    # ── Sub-builders ──────────────────────────────────────────────────────

    def _build_serial_group(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Serial link")
        box.setObjectName("connectGroupBox")
        fl = QtWidgets.QFormLayout(box)
        fl.setVerticalSpacing(10)
        fl.setContentsMargins(8, 18, 8, 10)
        com_row = QtWidgets.QHBoxLayout()
        com_row.setSpacing(8)
        self.com_cb.setMinimumHeight(32)
        com_row.addWidget(self.com_cb, 1)
        com_row.addWidget(self.refresh_btn)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(com_row)
        fl.addRow("COM port", wrap)
        fl.addRow("Baud", self.baud_edit)
        fl.addRow("", self.chk_serial_auto_reconnect)
        fl.addRow("", self.chk_auto_discover)
        return box

    def _build_network_group(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Network path")
        box.setObjectName("connectGroupBox")
        lay = QtWidgets.QVBoxLayout(box)
        lay.setSpacing(10)
        lay.setContentsMargins(8, 18, 8, 10)
        fl = QtWidgets.QFormLayout()
        fl.setVerticalSpacing(10)
        fl.addRow("Listen host", self.udp_host)
        fl.addRow("Listen port", self.udp_port)
        lay.addLayout(fl)
        fan = QtWidgets.QHBoxLayout()
        fan.addWidget(self.chk_udp_fanout, 1)
        fan.addWidget(
            create_network_help_button(self),
            0,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        lay.addLayout(fan)
        sink = QtWidgets.QHBoxLayout()
        sink.setSpacing(8)
        sink.addWidget(self.chk_tcp_sink_enable)
        sink.addWidget(QtWidgets.QLabel("TCP mirror port"))
        sink.addWidget(self.tcp_sink_port)
        sink.addStretch(1)
        lay.addLayout(sink)
        lay.addWidget(self.chk_advanced_net)
        lay.addWidget(self._advanced_net)
        return box

    def _build_status_footer(self) -> QtWidgets.QFrame:
        footer = QtWidgets.QFrame()
        footer.setObjectName("modernStatusFooter")
        footer.setFixedHeight(24)
        row = QtWidgets.QHBoxLayout(footer)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(10)
        row.addWidget(self.lbl_backup_status, 0)
        row.addWidget(_vsep())
        row.addStretch(1)
        version_lbl = QtWidgets.QLabel(f"v{__version__}")
        version_lbl.setObjectName("modernFooterVersion")
        row.addWidget(version_lbl, 0)
        return footer

    # ── Tab helpers ────────────────────────────────────────────────────────

    def _tab_index_by_name(self, name: str) -> int:
        for i in range(self._modern_main_tabs.count()):
            if self._modern_main_tabs.tabText(i).strip() == name:
                return i
        return -1

    def _save_active_tab(self, index: int) -> None:
        try:
            import json
            raw: dict = {}
            if CONFIG_PATH.is_file():
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
            raw["modern_active_tab"] = index
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        except (OSError, ValueError):
            pass

    def _restore_active_tab(self) -> None:
        try:
            import json
            if not CONFIG_PATH.is_file():
                return
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            idx = raw.get("modern_active_tab", 0)
            if isinstance(idx, int) and 0 <= idx < self._modern_main_tabs.count():
                self._modern_main_tabs.setCurrentIndex(idx)
        except (OSError, ValueError):
            pass

    # ── Bridge lifecycle ───────────────────────────────────────────────────

    def _set_footer_running(self, running: bool) -> None:
        lbl = getattr(self, "lbl_stats", None)
        if lbl is not None:
            lbl.setProperty("bridgeRunning", "true" if running else "false")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def _on_bridge_started(self) -> None:
        super()._on_bridge_started()
        self._set_footer_running(True)
        # Smart-Peek: navigate to Log tab so the operator sees data immediately
        try:
            log_idx = self._tab_index_by_name("Log")
            if log_idx >= 0:
                self._modern_main_tabs.setCurrentIndex(log_idx)
        except Exception:
            pass

    def stop_bridge(self) -> None:
        super().stop_bridge()
        self._set_footer_running(False)

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
            "stopped", "Stopped", "Pick a COM port and UDP settings, then Start."
        )
        self._refresh_intent_hint()
        self._apply_modern_stylesheet()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        refresh_status_bar_labels(self)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._apply_modern_stylesheet()
        from ui.connect_qr_overlay import schedule_qr_on_window_show
        schedule_qr_on_window_show(self)

    def _show_modern_pipeline_tab(self) -> None:
        if getattr(self, "_modern_main_tabs", None) is not None:
            self._modern_main_tabs.setCurrentIndex(0)

    def _hide_mission_review_tab(self) -> None:
        hide_mission_review_tab(self)

    def _reveal_mission_review_tab(
        self, record: object, summary: dict[str, object]
    ) -> None:
        from ui.mission_review import reveal_mission_review_tab
        reveal_mission_review_tab(self, record, summary)  # type: ignore[arg-type]
