"""Standard UI — tabs + path cards."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.connect_panels import setup_connect_tab_panels
from ui.controls import (
    create_connect_mini_log,
    create_connect_quick_terminal,
    create_connection_controls,
    create_diagnostics_controls,
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
        self.resize(1100, 680)
        self.setMinimumSize(900, 560)
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
        cv = QtWidgets.QVBoxLayout(connect_body)
        cv.setContentsMargins(10, 8, 10, 8)
        cv.setSpacing(6)
        sub = QtWidgets.QLabel(f"v{__version__} — Network ↔ serial (UDP/TCP NMEA)")
        sub.setObjectName("appSubtitle")
        sub.setWordWrap(True)
        cv.addWidget(sub)
        cv.addWidget(self.status_banner)

        ser_box = QtWidgets.QGroupBox("Serial")
        sf = QtWidgets.QFormLayout(ser_box)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.com_cb, 1)
        row.addWidget(self.refresh_btn)
        cw = QtWidgets.QWidget()
        cw.setLayout(row)
        sf.addRow("COM:", cw)
        sf.addRow("Baud:", self.baud_edit)
        sf.addRow("", self.chk_serial_auto_reconnect)
        cv.addWidget(ser_box)

        net_box = QtWidgets.QGroupBox("Network (UDP listen)")
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
        nv.addWidget(self.chk_advanced_net)
        nv.addWidget(self._advanced_net)
        cv.addWidget(net_box)
        cv.addStretch(1)

        connect_scroll = QtWidgets.QScrollArea()
        connect_scroll.setWidgetResizable(True)
        connect_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        connect_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        connect_scroll.setWidget(connect_body)
        connect_scroll.setMinimumHeight(120)
        connect_scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        act_box = QtWidgets.QWidget()
        act_box.setObjectName("runGroup")
        al = QtWidgets.QHBoxLayout(act_box)
        al.setContentsMargins(0, 0, 0, 0)
        self.start_btn.setText("Start bridge")
        self.stop_btn.setText("Stop bridge")
        al.addWidget(self.start_btn, 2)
        al.addWidget(self.stop_btn, 1)
        self.btn_bench_pair_setup = QtWidgets.QPushButton("Bench pair setup…")
        self.btn_bench_pair_setup.setToolTip(
            "Open the bench/com0com operator guide and run com_free + check_setup preflight "
            "(install com0com separately — see guide §5)."
        )
        self.btn_bench_pair_setup.clicked.connect(self._open_bench_pair_setup)
        al.addWidget(self.btn_bench_pair_setup, 1)

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

        tabs = QtWidgets.QTabWidget()
        self._main_tabs = tabs
        tabs.setDocumentMode(True)
        tabs.setUsesScrollButtons(True)
        log_panel = create_log_panel(self)
        tabs.addTab(connect_tab, "Connect")
        tabs.addTab(log_panel, "Log")
        tabs.addTab(create_presets_tab(self, include_advanced_net=False), "Presets")
        tabs.addTab(create_nmea_controls(self), "NMEA")
        tabs.addTab(create_theme_controls(self), "Theme")
        send_tab = create_send_controls(self)
        diag_tab = create_diagnostics_controls(self)
        tabs.addTab(send_tab, "Send")
        tabs.addTab(diag_tab, "Diagnostics")
        self._setup_reorderable_tabs(tabs, "main_tabs")
        tabs.setTabToolTip(0, "COM, UDP listen, advanced TCP/UDP, Start and Stop")
        tabs.setTabToolTip(1, "Live bridge log, filters, pause, clear, and save")
        tabs.setTabToolTip(2, "Named presets and optional boat LAN reference fields")
        tabs.setTabToolTip(3, "Passthrough, strict filter, or raw binary forwarding")
        tabs.setTabToolTip(4, "Theme studio: randomize, favorite, and seed-lock options")
        tabs.setTabToolTip(5, "Inject test NMEA while the bridge is Running")
        tabs.setTabToolTip(6, "File log, automated bench checks, UI layout switch")

        self.statusBar = QtWidgets.QStatusBar()
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
        outer.addWidget(tabs, 1)
        outer.addWidget(self.statusBar)

        self._finalize_ui()

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped", "Load a preset or set COM/UDP, then Start.")
        self._refresh_intent_hint()
        self._restore_ntrip_prefs()
        self._focus_connect_tab()
