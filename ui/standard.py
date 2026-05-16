"""Standard UI — tabs + path cards (v0.4 layout)."""
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
from ui.styles import BRIDGE_STYLESHEET_STANDARD
from version import __version__


class BridgeWindowStandard(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self.setStyleSheet(BRIDGE_STYLESHEET_STANDARD)
        self.setWindowTitle(f"Network ↔ COM Bridge v{__version__}")
        self.resize(980, 560)
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

        connect_tab = QtWidgets.QWidget()
        cv = QtWidgets.QVBoxLayout(connect_tab)
        title = QtWidgets.QLabel("NMEA Serial Bridge")
        title.setObjectName("appTitle")
        sub = QtWidgets.QLabel(f"v{__version__} — UDP NMEA in, serial out")
        sub.setObjectName("appSubtitle")
        sub.setWordWrap(True)
        cv.addWidget(title)
        cv.addWidget(sub)
        cv.addWidget(self.status_banner)
        cv.addWidget(self.intent_hint)

        path_box = QtWidgets.QGroupBox("1 — Choose path")
        pl = QtWidgets.QHBoxLayout(path_box)
        self.btn_bench_preset.setText("Desk test\ncom0com · 127.0.0.1")
        self.btn_production_preset.setText("Boat / INS\nLAN UDP → Cube COM")
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

        net_box = QtWidgets.QGroupBox("3 — Network (UDP listen)")
        nv = QtWidgets.QVBoxLayout(net_box)
        uf = QtWidgets.QFormLayout()
        uf.addRow("Listen:", self.udp_host)
        uf.addRow("Port:", self.udp_port)
        nv.addLayout(uf)
        nv.addWidget(self.chk_advanced_net)
        nv.addWidget(self._advanced_net)
        cv.addWidget(net_box)

        act_box = QtWidgets.QGroupBox("4 — Run")
        al = QtWidgets.QHBoxLayout(act_box)
        self.start_btn.setText("Start bridge")
        self.stop_btn.setText("Stop bridge")
        al.addWidget(self.start_btn, 2)
        al.addWidget(self.stop_btn, 1)
        cv.addWidget(act_box)
        cv.addStretch(1)

        tabs = QtWidgets.QTabWidget()
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
        self._splitter.setSizes([580, 400])

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — ↓ inj↓ ↑ Hz = remote vs Send→COM vs COM→net when running (hover)"
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
