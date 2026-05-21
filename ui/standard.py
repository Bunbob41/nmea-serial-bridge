"""Standard UI — tabs + path cards."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.connect_panels import (
    embed_connection_hub_on_connect_body,
    setup_connect_tab_panels,
    sync_connect_panel_layout,
)
from ui.controls import (
    create_connect_mini_log,
    create_connect_quick_terminal,
    create_connection_controls,
    create_diagnostics_controls,
    create_guide_tab,
    create_log_panel,
    create_nmea_controls,
    create_presets_tab,
    create_send_controls,
    create_theme_controls,
)
from ui.mixin import BridgeLogicMixin
from ui.styles import bridge_stylesheet
from ui.theme_choice import load_theme_choice
from version import __version__


class BridgeWindowStandard(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self._ui_mode = "standard"
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"Network ↔ COM Bridge v{__version__}")
        self.resize(1100, 520)
        self.setMinimumSize(900, 380)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_banner = QtWidgets.QFrame()
        self.status_banner.setObjectName("statusBanner")
        self.status_banner.setProperty("state", "stopped")
        bl = QtWidgets.QVBoxLayout(self.status_banner)
        self.status_banner_text = QtWidgets.QLabel("Stopped")
        self.status_banner_text.setObjectName("statusBannerText")
        self.status_banner_text.setWordWrap(True)
        bl.addWidget(self.status_banner_text)

        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("intentHint")
        self.intent_hint.setWordWrap(True)

        connect_body = QtWidgets.QWidget()
        connect_body.setObjectName("connectSectionBody")
        connect_body.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        cv = QtWidgets.QVBoxLayout(connect_body)
        cv.setContentsMargins(10, 8, 10, 8)
        cv.setSpacing(6)
        sub = QtWidgets.QLabel(f"v{__version__} — Network ↔ serial (UDP/TCP NMEA)")
        sub.setObjectName("appSubtitle")
        sub.setWordWrap(True)
        cv.addWidget(sub)
        cv.addWidget(self.status_banner)

        ser_box = QtWidgets.QGroupBox("Serial")
        ser_box.setObjectName("connectGroupBox")
        sf = QtWidgets.QFormLayout(ser_box)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.com_cb, 1)
        row.addWidget(self.refresh_btn)
        cw = QtWidgets.QWidget()
        cw.setLayout(row)
        sf.addRow("COM:", cw)
        sf.addRow("Baud:", self.baud_edit)
        sf.addRow("", self.chk_serial_auto_reconnect)
        sf.addRow("", self.chk_auto_discover)

        net_box = QtWidgets.QGroupBox("Network (UDP listen)")
        net_box.setObjectName("connectGroupBox")
        nv = QtWidgets.QVBoxLayout(net_box)
        hint_net = QtWidgets.QLabel(
            "Bind address and port on this PC. Enable Advanced below for TCP or UDP remote."
        )
        hint_net.setWordWrap(True)
        hint_net.setObjectName("tabHint")
        nv.addWidget(hint_net)
        uf = QtWidgets.QFormLayout()
        uf.addRow("Listen host:", self.udp_host)
        uf.addRow("Listen port:", self.udp_port)
        nv.addLayout(uf)
        nv.addWidget(self.chk_udp_fanout)
        sink_row = QtWidgets.QHBoxLayout()
        sink_row.addWidget(self.chk_tcp_sink_enable)
        sink_row.addWidget(QtWidgets.QLabel("Port:"))
        sink_row.addWidget(self.tcp_sink_port)
        sink_row.addStretch(1)
        nv.addLayout(sink_row)
        nv.addWidget(self.chk_advanced_net)
        nv.addWidget(self._advanced_net)
        embed_connection_hub_on_connect_body(self, connect_body, [ser_box, net_box])
        cv.addStretch(1)

        connect_scroll = QtWidgets.QScrollArea()
        connect_scroll.setObjectName("connectSectionScroll")
        connect_scroll.setWidgetResizable(True)
        connect_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        connect_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        connect_scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        connect_scroll.viewport().setObjectName("connectSectionScrollViewport")
        connect_scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        connect_scroll.setWidget(connect_body)
        connect_scroll.setMinimumHeight(180)
        connect_scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        act_box = QtWidgets.QWidget()
        act_box.setObjectName("runGroup")
        act_box.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        al = QtWidgets.QHBoxLayout(act_box)
        al.setContentsMargins(5, 5, 5, 5)
        al.setSpacing(10)
        _fixed_row_policy = (
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.start_btn.setText("Start bridge")
        self.start_btn.setSizePolicy(*_fixed_row_policy)
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setMaximumWidth(200)
        self.stop_btn.setText("Stop bridge")
        self.stop_btn.setSizePolicy(*_fixed_row_policy)
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setMaximumWidth(200)
        al.addWidget(self.start_btn)
        al.addWidget(self.stop_btn)
        al.addStretch(1)

        ntrip_box = QtWidgets.QWidget()
        ntrip_box.setObjectName("connectNtripBox")
        ntrip_l = QtWidgets.QVBoxLayout(ntrip_box)
        ntrip_l.setContentsMargins(0, 0, 0, 0)
        self.chk_ntrip_enable = QtWidgets.QCheckBox("Enable NTRIP while bridge runs")
        self.chk_ntrip_enable.setToolTip(
            "Streams RTCM from a caster onto the bridge COM alongside INS/NMEA from the network. "
            "Use for live corrections (POSPAC/post-processing still uses your survey workflow)."
        )
        ntrip_l.addWidget(self.chk_ntrip_enable)
        ntrip_form = QtWidgets.QFormLayout()
        self.ntrip_caster = QtWidgets.QLineEdit()
        self.ntrip_caster.setPlaceholderText("caster.example.com:2101")
        self.ntrip_mount = QtWidgets.QLineEdit()
        self.ntrip_mount.setPlaceholderText("MOUNTPOINT")
        self.ntrip_user = QtWidgets.QLineEdit()
        self.ntrip_pass = QtWidgets.QLineEdit()
        self.ntrip_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ntrip_pass.setToolTip(
            "Saved in %USERPROFILE%\\.cursor-udp-com-bridge\\ui_prefs.json as plain text. "
            "Use a caster account you can rotate; avoid shared PCs."
        )
        ntrip_form.addRow("Caster:", self.ntrip_caster)
        ntrip_form.addRow("Mount:", self.ntrip_mount)
        ntrip_form.addRow("User:", self.ntrip_user)
        ntrip_form.addRow("Password:", self.ntrip_pass)
        ntrip_l.addLayout(ntrip_form)

        connect_tab = QtWidgets.QWidget()
        self._connect_tab = connect_tab
        setup_connect_tab_panels(
            self,
            connect_tab,
            {
                "run": act_box,
                "hint": self.intent_hint,
                "quick_log": create_connect_mini_log(self),
                "quick_terminal": create_connect_quick_terminal(self),
                "connection": connect_scroll,
                "ntrip": ntrip_box,
            },
        )
        # --- Tools tab: sidebar nav (left) + stacked pages (right) ---
        tools_tab = QtWidgets.QWidget()
        tools_tab.setObjectName("toolsDrawerTab")
        tools_h = QtWidgets.QHBoxLayout(tools_tab)
        tools_h.setContentsMargins(0, 0, 0, 0)
        tools_h.setSpacing(0)

        tools_nav = QtWidgets.QListWidget()
        tools_nav.setObjectName("toolsNavList")
        tools_nav.setMaximumWidth(130)
        tools_nav.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        for item_text in ("Presets", "NMEA", "Terminal", "Diagnostics", "Theme", "Guide"):
            tools_nav.addItem(item_text)

        tools_stack = QtWidgets.QStackedWidget()
        tools_stack.addWidget(create_presets_tab(self, include_advanced_net=False))  # 0
        tools_stack.addWidget(create_nmea_controls(self))                             # 1
        tools_stack.addWidget(create_send_controls(self))                             # 2
        tools_stack.addWidget(create_diagnostics_controls(self))                      # 3
        tools_stack.addWidget(create_theme_controls(self))                            # 4
        tools_stack.addWidget(create_guide_tab(self))                                 # 5

        tools_nav.currentRowChanged.connect(tools_stack.setCurrentIndex)
        tools_nav.setCurrentRow(0)

        self._tools_nav = tools_nav
        self._tools_stack = tools_stack

        tools_h.addWidget(tools_nav)
        tools_h.addWidget(tools_stack, 1)
        # ----------------------------------------------------------------

        tabs = QtWidgets.QTabWidget()
        self._main_tabs = tabs
        tabs.setDocumentMode(True)
        tabs.setUsesScrollButtons(True)
        log_panel = create_log_panel(self)
        tabs.addTab(connect_tab, "Connect")
        tabs.addTab(log_panel, "Log")
        tabs.addTab(tools_tab, "Tools")
        self._setup_reorderable_tabs(tabs, "main_tabs")
        tabs.currentChanged.connect(lambda *_args: self._schedule_connect_reflow(0))
        tabs.currentChanged.connect(lambda *_args: self._schedule_connect_reflow(48))
        tabs.installEventFilter(self)
        connect_tab.installEventFilter(self)
        tabs.setTabToolTip(0, "COM, UDP listen, advanced TCP/UDP, Start and Stop")
        tabs.setTabToolTip(1, "Live bridge log, filters, pause, clear, and save")
        tabs.setTabToolTip(2, "Presets, NMEA mode, Terminal injection, Diagnostics, Theme, and Guide")

        self.statusBar = QtWidgets.QStatusBar()
        # Fixed vertical policy prevents the status bar from absorbing spare stretch.
        self.statusBar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.status_nmea = QtWidgets.QLabel("NMEA: passthrough")
        self.status_nmea.setToolTip("Selected NMEA / raw mode for the next Start (or current session).")
        self.status_gnss = QtWidgets.QLabel("GNSS: —")
        self.status_gnss.setToolTip("Live GGA fix, satellites, and HDOP while Running.")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, this line shows Hz, transport health, and session totals (hover)"
        )
        self.lbl_stats.setToolTip("")  # filled when running / see mixin._stats_tooltip
        self.statusBar.addWidget(self.status_serial, 2)
        self.statusBar.addWidget(self.status_network, 2)
        self.statusBar.addWidget(self.status_nmea, 1)
        self.statusBar.addWidget(self.status_gnss, 2)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(2)
        outer.addWidget(tabs, 1)        # stretch=1: all spare vertical space goes here
        outer.addWidget(self.statusBar, 0)  # stretch=0: always fixed height at bottom

        self._finalize_ui()
        self._schedule_connect_reflow(0)
        self._schedule_connect_reflow(80)
        self._schedule_connect_reflow(180)

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped", "Load a preset or set COM/UDP, then Start.")
        self._refresh_intent_hint()
        self._restore_ntrip_prefs()
        self._focus_connect_tab()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_connect_reflow(0)
        self._schedule_connect_reflow(60)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_connect_reflow(24)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        et = event.type()
        if watched in (getattr(self, "_main_tabs", None), getattr(self, "_connect_tab", None)):
            if et in (
                QtCore.QEvent.Type.Show,
                QtCore.QEvent.Type.Resize,
                QtCore.QEvent.Type.LayoutRequest,
            ):
                self._schedule_connect_reflow(0)
                self._schedule_connect_reflow(48)
        return super().eventFilter(watched, event)

    def _is_connect_tab_active(self) -> bool:
        tabs = getattr(self, "_main_tabs", None)
        ctab = getattr(self, "_connect_tab", None)
        if tabs is None or ctab is None:
            return False
        idx = tabs.currentIndex()
        return idx >= 0 and tabs.widget(idx) is ctab

    def _schedule_connect_reflow(self, delay_ms: int) -> None:
        QtCore.QTimer.singleShot(max(int(delay_ms), 0), self._sync_connect_layout_if_active)

    def _sync_connect_layout_if_active(self) -> None:
        if self._is_connect_tab_active():
            sync_connect_panel_layout(self)
