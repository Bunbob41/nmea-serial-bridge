"""Standard UI — tabs + path cards."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.controls import (
    create_connection_controls,
    create_diagnostics_controls,
    create_log_panel,
    create_nmea_controls,
    create_send_controls,
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
        act_box = QtWidgets.QGroupBox("Run")
        al = QtWidgets.QHBoxLayout(act_box)
        self.start_btn.setText("Start bridge")
        self.stop_btn.setText("Stop bridge")
        al.addWidget(self.start_btn, 2)
        al.addWidget(self.stop_btn, 1)
        cv.addWidget(self.status_banner)
        cv.addWidget(self.intent_hint)

        path_box = QtWidgets.QGroupBox("1 — Choose path")
        pl = QtWidgets.QHBoxLayout(path_box)
        self.btn_bench_preset.setText("Desk test (com0com · 127.0.0.1)")
        self.btn_production_preset.setText("Boat / INS (LAN UDP → Cube COM)")
        pl.addWidget(self.btn_bench_preset)
        pl.addWidget(self.btn_production_preset)
        cv.addWidget(path_box)

        ser_box = QtWidgets.QGroupBox("2 — Serial")
        sf = QtWidgets.QFormLayout(ser_box)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.com_cb, 1)
        row.addWidget(self.refresh_btn)
        cw = QtWidgets.QWidget()
        cw.setLayout(row)
        sf.addRow("COM:", cw)
        sf.addRow("Baud:", self.baud_edit)
        cv.addWidget(ser_box)

        net_box = QtWidgets.QGroupBox("3 — Network endpoint")
        nv = QtWidgets.QVBoxLayout(net_box)
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

        connect_tab = QtWidgets.QWidget()
        connect_tab_l = QtWidgets.QVBoxLayout(connect_tab)
        connect_tab_l.setContentsMargins(0, 0, 0, 0)
        connect_tab_l.setSpacing(6)
        connect_tab_l.addWidget(act_box)
        connect_tab_l.addWidget(connect_scroll, 1)

        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setUsesScrollButtons(True)
        tabs.addTab(connect_tab, "Connect")
        tabs.addTab(create_nmea_controls(self), "NMEA")
        send_tab = create_send_controls(self)
        diag_tab = create_diagnostics_controls(self)
        tabs.addTab(send_tab, "Send")
        tabs.addTab(diag_tab, "Diagnostics")
        tabs.setTabToolTip(2, "Inject NMEA while bridge is Running")
        tabs.setTabToolTip(3, "File log and log panel utilities")

        log_panel = create_log_panel(self)
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.addWidget(tabs)
        self._splitter.addWidget(log_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([660, 420])

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, this line shows Hz, transport health, and session totals (hover)"
        )
        self.lbl_stats.setToolTip("")  # filled when running / see mixin._stats_tooltip
        self.statusBar.addWidget(self.status_serial, 2)
        self.statusBar.addWidget(self.status_network, 2)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 4)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)

        self._finalize_ui()

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped", "Choose a path, then Start.")
        self._refresh_intent_hint()
