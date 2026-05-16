"""Minimal UI — light theme, single column, small chrome."""
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


class BridgeWindowMinimal(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self._ui_mode = "minimal"
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"NMEA Bridge (minimal) v{__version__}")
        self.resize(880, 620)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_line = QtWidgets.QLabel("Stopped")
        self.status_line.setObjectName("statusLine")
        self.status_line.setProperty("state", "stopped")
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setWordWrap(True)
        self.intent_hint.setStyleSheet("color: #5a2a33;")

        # Dummy banner attrs for mixin compatibility
        self.status_banner = self.status_line
        self.status_banner_text = self.status_line

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.btn_bench_preset)
        top.addWidget(self.btn_production_preset)
        top.addStretch(1)

        run_strip = QtWidgets.QGroupBox("Run")
        run_l = QtWidgets.QHBoxLayout(run_strip)
        self.start_btn.setText("Start bridge")
        self.stop_btn.setText("Stop bridge")
        run_l.addWidget(self.start_btn, 2)
        run_l.addWidget(self.stop_btn, 1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("COM"))
        row2.addWidget(self.com_cb, 1)
        row2.addWidget(self.refresh_btn)
        row2.addWidget(QtWidgets.QLabel("Baud"))
        row2.addWidget(self.baud_edit)
        row2.addWidget(QtWidgets.QLabel("Listen"))
        self.udp_host.setToolTip("UDP bind address (0.0.0.0 = all interfaces on this PC).")
        self.udp_port.setToolTip("UDP port the bridge listens on — senders target this port.")
        row2.addWidget(self.udp_host)
        row2.addWidget(self.udp_port)

        tools = QtWidgets.QTabWidget()
        tools.setMinimumHeight(220)
        tools.addTab(create_nmea_controls(self), "NMEA")
        tools.addTab(create_send_controls(self), "Send")
        tools.addTab(create_diagnostics_controls(self), "Diagnostics")
        adv_w = QtWidgets.QWidget()
        adv_l = QtWidgets.QVBoxLayout(adv_w)
        adv_l.addWidget(self.chk_advanced_net)
        adv_l.addWidget(self._advanced_net)
        tools.addTab(adv_w, "Network+")

        log_panel = create_log_panel(self)
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.addWidget(log_panel)
        cfg = QtWidgets.QWidget()
        cfg_l = QtWidgets.QVBoxLayout(cfg)
        cfg_l.addLayout(top)
        cfg_l.addWidget(self.status_line)
        cfg_l.addWidget(self.intent_hint)
        cfg_l.addLayout(row2)
        cfg_l.addWidget(tools)
        self._splitter.addWidget(cfg)
        self._splitter.setStretchFactor(0, 4)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([360, 140])

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, Hz + transport + session totals (hover)"
        )
        self.statusBar.addWidget(self.status_serial, 1)
        self.statusBar.addWidget(self.status_network, 1)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 4)
        outer.addWidget(run_strip)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)
        self._finalize_ui()

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_line.setProperty("state", state)
        style = self.status_line.style()
        style.unpolish(self.status_line)
        style.polish(self.status_line)
        text = title if not detail else f"{title} — {detail}"
        self.status_line.setText(text)

    def _toggle_log_panel(self, visible: bool) -> None:
        self._splitter.widget(0).setVisible(visible)

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped", "Desk or Boat, then Start")
        self._refresh_intent_hint()
