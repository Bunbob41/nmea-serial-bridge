"""Log-first UI — dark theme, log uses most of the window."""
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
from ui.styles import BRIDGE_STYLESHEET_LOGFIRST
from version import __version__


class BridgeWindowLogFirst(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self.setStyleSheet(BRIDGE_STYLESHEET_LOGFIRST)
        self.setWindowTitle(f"NMEA Bridge (log) v{__version__}")
        self.resize(900, 600)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_line = QtWidgets.QLabel("Stopped")
        self.status_line.setObjectName("statusLine")
        self.status_banner = self.status_line
        self.status_banner_text = self.status_line
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setWordWrap(True)

        log_panel = create_log_panel(self)
        self.chk_show_log.setChecked(True)
        self.chk_show_log.hide()

        strip = QtWidgets.QFrame()
        strip.setObjectName("controlStrip")
        sl = QtWidgets.QVBoxLayout(strip)
        sl.setContentsMargins(8, 6, 8, 6)
        r1 = QtWidgets.QHBoxLayout()
        r1.addWidget(self.btn_bench_preset)
        r1.addWidget(self.btn_production_preset)
        r1.addWidget(QtWidgets.QLabel("COM"))
        r1.addWidget(self.com_cb, 1)
        r1.addWidget(self.refresh_btn)
        r1.addWidget(QtWidgets.QLabel("Baud"))
        r1.addWidget(self.baud_edit)
        r1.addWidget(QtWidgets.QLabel(":"))
        r1.addWidget(self.udp_port)
        r1.addWidget(self.start_btn)
        r1.addWidget(self.stop_btn)
        sl.addLayout(r1)
        sl.addWidget(self.status_line)
        sl.addWidget(self.intent_hint)

        drawer = QtWidgets.QToolButton()
        drawer.setText("Tools ▾")
        drawer.setCheckable(True)
        drawer_tabs = QtWidgets.QTabWidget()
        drawer_tabs.addTab(create_nmea_controls(self), "NMEA")
        drawer_tabs.addTab(create_send_controls(self), "Send")
        drawer_tabs.addTab(create_diagnostics_controls(self), "Diag")
        adv = QtWidgets.QWidget()
        av = QtWidgets.QVBoxLayout(adv)
        av.addWidget(self.chk_advanced_net)
        av.addWidget(self._advanced_net)
        drawer_tabs.addTab(adv, "Net")
        drawer_tabs.setVisible(False)
        drawer_tabs.setMinimumHeight(260)

        def _toggle(on: bool) -> None:
            drawer_tabs.setVisible(on)
            drawer.setText("Tools ▴" if on else "Tools ▾")

        drawer.toggled.connect(_toggle)
        r2 = QtWidgets.QHBoxLayout()
        r2.addWidget(drawer)
        r2.addStretch(1)
        r2.addWidget(self.chk_verbose_log)
        r2.addWidget(self.btn_clear_log)
        sl.addLayout(r2)
        sl.addWidget(drawer_tabs)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.addWidget(log_panel)
        self._splitter.addWidget(strip)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([440, 120])

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — ↓ inj↓ ↑ when running (hover)"
        )
        self.statusBar.addWidget(self.status_serial, 1)
        self.statusBar.addWidget(self.status_network, 1)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)
        self._finalize_ui()

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_line.setProperty("state", state)
        text = title if not detail else f"{title} | {detail}"
        self.status_line.setText(text)

    def _toggle_log_panel(self, _visible: bool) -> None:
        pass

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped")
        self._refresh_intent_hint()
