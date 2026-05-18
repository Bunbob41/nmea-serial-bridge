"""Minimal UI — light theme, log-first column, tools drawer (legacy; launcher maps to Field)."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.controls import (
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
from ui.ui_prefs import load_minimal_prefs, save_minimal_prefs
from version import __version__


class BridgeWindowMinimal(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self._ui_mode = "minimal"
        self._compact_intent_hint = True
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"NMEA Bridge (minimal) v{__version__}")
        self.resize(880, 640)
        self.setMinimumSize(640, 480)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_line = QtWidgets.QLabel("Stopped")
        self.status_line.setObjectName("statusLine")
        self.status_line.setProperty("state", "stopped")
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("intentHint")
        self.status_banner = self.status_line
        self.status_banner_text = self.status_line

        run_strip = QtWidgets.QFrame()
        run_strip.setObjectName("runStrip")
        run_l = QtWidgets.QHBoxLayout(run_strip)
        run_l.setContentsMargins(8, 6, 8, 6)
        self.start_btn.setText("Start bridge")
        self.start_btn.setMinimumHeight(36)
        self.stop_btn.setText("Stop bridge")
        self.stop_btn.setMinimumHeight(36)
        run_l.addWidget(self.start_btn, 2)
        run_l.addWidget(self.stop_btn, 1)

        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QtWidgets.QLabel("COM"))
        self.com_cb.setMinimumWidth(140)
        row2.addWidget(self.com_cb, 1)
        row2.addWidget(self.refresh_btn)
        row2.addWidget(QtWidgets.QLabel("Baud"))
        self.baud_edit.setMaximumWidth(88)
        row2.addWidget(self.baud_edit)
        row2.addWidget(QtWidgets.QLabel("UDP"))
        self.udp_host.setMaximumWidth(100)
        self.udp_host.setToolTip("UDP listen bind address (Tools → Presets for TCP modes).")
        row2.addWidget(self.udp_host)
        row2.addWidget(QtWidgets.QLabel(":"))
        self.udp_port.setMaximumWidth(64)
        self.udp_port.setToolTip("UDP listen port — senders use this port on the host above.")
        row2.addWidget(self.udp_port)

        drawer = QtWidgets.QToolButton()
        self._drawer_btn = drawer
        drawer.setText("Tools ▾")
        drawer.setToolTip(
            "Presets (TCP/UDP modes), NMEA mode, manual Send, and Diagnostics bench checks."
        )
        drawer.setCheckable(True)
        drawer_tabs = QtWidgets.QTabWidget()
        self._drawer_tabs = drawer_tabs
        drawer_tabs.setUsesScrollButtons(True)
        drawer_tabs.addTab(create_presets_tab(self), "Presets")
        drawer_tabs.addTab(create_nmea_controls(self), "NMEA")
        drawer_tabs.addTab(create_theme_controls(self), "Theme")
        drawer_tabs.addTab(create_guide_tab(self), "Guide")
        drawer_tabs.addTab(create_send_controls(self), "Terminal")
        drawer_tabs.addTab(create_diagnostics_controls(self), "Diagnostics")
        self._setup_reorderable_tabs(drawer_tabs, "tools_tabs")
        drawer_tabs.setVisible(False)
        drawer_tabs.setMinimumHeight(260)

        def _toggle(on: bool) -> None:
            drawer_tabs.setVisible(on)
            drawer.setText("Tools ▴" if on else "Tools ▾")
            self._save_minimal_ui_prefs()

        drawer.toggled.connect(_toggle)

        strip = QtWidgets.QFrame()
        strip.setObjectName("controlStrip")
        sl = QtWidgets.QVBoxLayout(strip)
        sl.setContentsMargins(8, 4, 8, 6)
        sl.addWidget(self.status_line)
        sl.addWidget(self.intent_hint)
        sl.addLayout(row2)
        r3 = QtWidgets.QHBoxLayout()
        r3.addWidget(drawer)
        r3.addStretch(1)
        sl.addLayout(r3)
        sl.addWidget(drawer_tabs)

        log_panel = create_log_panel(self)
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.addWidget(log_panel)
        self._splitter.addWidget(strip)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([380, 160])

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.status_nmea = QtWidgets.QLabel("NMEA: passthrough")
        self.status_nmea.setToolTip("NMEA passthrough, strict filter, or raw binary (RTCM / other).")
        self.status_gnss = QtWidgets.QLabel("GNSS: —")
        self.status_gnss.setToolTip("Live GGA fix, satellites, and HDOP while Running.")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, Hz + transport + session totals (hover)"
        )
        self.statusBar.addWidget(self.status_serial, 1)
        self.statusBar.addWidget(self.status_network, 1)
        self.statusBar.addWidget(self.status_nmea, 0)
        self.statusBar.addWidget(self.status_gnss, 1)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(run_strip)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)
        self._finalize_ui()
        prefs = load_minimal_prefs()
        drawer.setChecked(bool(prefs.get("tools_open", False)))

    def _save_minimal_ui_prefs(self) -> None:
        save_minimal_prefs({"tools_open": self._drawer_btn.isChecked()})

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_intent_hint_display()

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
        self._set_status_banner("stopped", "Stopped", "Load a preset or set COM/UDP, then Start")
        self._refresh_intent_hint()
