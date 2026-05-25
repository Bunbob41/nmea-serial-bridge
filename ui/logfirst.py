"""Log-first UI — dark theme, log uses most of the window."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.controls import (
    create_connection_controls,
    create_diagnostics_controls,
    create_guide_tab,
    create_phone_dashboard_tab,
    create_log_panel,
    create_nmea_controls,
    create_presets_tab,
    create_send_controls,
    create_theme_controls,
)
from ui.log_view import PRESET_CUSTOM, PRESET_LABELS, TOOLBAR_PRESETS, LogViewState
from ui.mixin import BridgeLogicMixin
from ui.styles import bridge_stylesheet
from ui.theme_choice import load_theme_choice
from ui.ui_prefs import load_logfirst_prefs, save_logfirst_prefs
from version import __version__


class BridgeWindowLogFirst(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._restoring_log_prefs = False
        self.setObjectName("BridgeRoot")
        self._ui_mode = "logfirst"
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"NMEA Bridge (log) v{__version__}")
        self.resize(1020, 700)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_line = QtWidgets.QLabel("Stopped")
        self.status_line.setObjectName("statusLine")
        self.status_banner = self.status_line
        self.status_banner_text = self.status_line
        self._compact_intent_hint = True
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("intentHint")
        self.intent_hint.setWordWrap(False)

        log_panel = create_log_panel(self)
        self.chk_show_log.setChecked(True)
        self.chk_show_log.hide()

        strip = QtWidgets.QFrame()
        strip.setObjectName("controlStrip")
        sl = QtWidgets.QVBoxLayout(strip)
        sl.setContentsMargins(8, 6, 8, 6)
        r1 = QtWidgets.QHBoxLayout()
        r1.setSpacing(6)
        self.com_cb.setMinimumWidth(170)
        self.com_cb.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.baud_edit.setMaximumWidth(88)
        r1.addWidget(QtWidgets.QLabel("COM"))
        r1.addWidget(self.com_cb, 1)
        r1.addWidget(self.refresh_btn)
        r1.addWidget(QtWidgets.QLabel("Baud"))
        r1.addWidget(self.baud_edit)
        r1.addWidget(QtWidgets.QLabel("UDP"))
        self.udp_host.setMaximumWidth(100)
        self.udp_host.setToolTip("UDP listen bind address (Tools → Presets for TCP modes).")
        r1.addWidget(self.udp_host)
        r1.addWidget(QtWidgets.QLabel(":"))
        self.udp_port.setMaximumWidth(64)
        self.udp_port.setToolTip("UDP listen port — senders use this port on the host above.")
        r1.addWidget(self.udp_port)
        sl.addLayout(r1)
        sl.addWidget(self.status_line)
        sl.addWidget(self.intent_hint)

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
        drawer_tabs.addTab(create_phone_dashboard_tab(self), "Phone")
        drawer_tabs.setTabToolTip(1, "Phone dashboard — Web API, token, QR (Tailscale/LAN)")
        drawer_tabs.addTab(create_nmea_controls(self), "NMEA")
        drawer_tabs.addTab(create_theme_controls(self), "Theme")
        drawer_tabs.addTab(create_guide_tab(self), "Guide")
        drawer_tabs.addTab(create_send_controls(self), "Terminal")
        drawer_tabs.addTab(create_diagnostics_controls(self), "Diagnostics")
        self._setup_reorderable_tabs(drawer_tabs, "tools_tabs")
        drawer_tabs.setVisible(False)
        drawer_tabs.setMinimumHeight(280)

        def _toggle(on: bool) -> None:
            drawer_tabs.setVisible(on)
            drawer.setText("Tools ▴" if on else "Tools ▾")
            self._save_logfirst_ui_prefs()

        drawer.toggled.connect(_toggle)
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(drawer)
        self.chk_log_rx = QtWidgets.QCheckBox("RX")
        self.chk_log_tx = QtWidgets.QCheckBox("TX")
        self.chk_log_warn = QtWidgets.QCheckBox("WARN")
        self.chk_log_rx.setChecked(True)
        self.chk_log_tx.setChecked(True)
        self.chk_log_warn.setChecked(True)
        self.chk_log_rx.toggled.connect(self._on_log_filter_rx)
        self.chk_log_tx.toggled.connect(self._on_log_filter_tx)
        self.chk_log_warn.toggled.connect(self._on_log_filter_warn)
        r2.addWidget(self.chk_log_rx)
        r2.addWidget(self.chk_log_tx)
        r2.addWidget(self.chk_log_warn)
        self.chk_log_pause = QtWidgets.QCheckBox("Pause")
        self.chk_log_pause.toggled.connect(self._on_log_pause_toggled)
        self.chk_log_autoscroll = QtWidgets.QCheckBox("Auto-scroll")
        self.chk_log_autoscroll.setChecked(True)
        self.chk_log_autoscroll.toggled.connect(self._on_log_autoscroll_toggled)
        r2.addWidget(self.chk_log_pause)
        r2.addWidget(self.chk_log_autoscroll)
        self.cmb_log_preset = QtWidgets.QComboBox()
        for key in TOOLBAR_PRESETS:
            if key == PRESET_CUSTOM:
                continue
            self.cmb_log_preset.addItem(PRESET_LABELS[key], key)
        self.cmb_log_preset.setMinimumWidth(132)
        self.cmb_log_preset.setToolTip("Quick live-log presets. Use View… for full control.")
        self.cmb_log_preset.currentIndexChanged.connect(self._on_log_preset_changed)
        r2.addWidget(self.cmb_log_preset)
        self.btn_log_view = QtWidgets.QPushButton("View…")
        self.btn_log_view.clicked.connect(self._open_log_view_dialog)
        r2.addWidget(self.btn_log_view)
        self.cmb_log_density = QtWidgets.QComboBox()
        self.cmb_log_density.addItem("Dense", 8)
        self.cmb_log_density.addItem("Readable", 10)
        self.cmb_log_density.setMinimumWidth(92)
        self.cmb_log_density.currentIndexChanged.connect(self._apply_log_density)
        r2.addWidget(self.cmb_log_density)
        self.btn_hud = QtWidgets.QPushButton("HUD")
        self.btn_hud.setToolTip("Open corner HUD")
        self.btn_hud.clicked.connect(self._open_stats_popout)
        r2.addWidget(self.btn_hud)
        r2.addStretch(1)
        sl.addLayout(r2)

        r3 = QtWidgets.QHBoxLayout()
        r3.setSpacing(6)
        r3.addStretch(1)
        r3.addWidget(self.chk_verbose_log)
        r3.addWidget(self.btn_clear_log)
        sl.addLayout(r3)
        sl.addWidget(drawer_tabs)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.addWidget(log_panel)
        self._splitter.addWidget(strip)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([440, 120])

        run_strip = QtWidgets.QFrame()
        run_strip.setObjectName("controlStrip")
        run_l = QtWidgets.QHBoxLayout(run_strip)
        run_l.setContentsMargins(8, 4, 8, 4)
        self.start_btn.setText("Start bridge")
        self.stop_btn.setText("Stop bridge")
        run_l.addWidget(self.start_btn, 2)
        run_l.addWidget(self.stop_btn, 1)

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.status_nmea = QtWidgets.QLabel("NMEA: passthrough")
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
        self._apply_log_density(0)
        self._restore_logfirst_ui_prefs(drawer)

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        from ui.connect_qr_overlay import schedule_qr_on_window_show

        schedule_qr_on_window_show(self)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_intent_hint_display()

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_line.setProperty("state", state)
        text = title if not detail else f"{title} | {detail}"
        self.status_line.setText(text)

    def _toggle_log_panel(self, _visible: bool) -> None:
        pass

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped")
        self._refresh_intent_hint()

    def _apply_log_density(self, _idx: int) -> None:
        size = int(self.cmb_log_density.currentData() or 8)
        f = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        f.setPointSize(size)
        self.log_view.setFont(f)
        self._save_logfirst_ui_prefs()

    def _on_log_filter_rx(self, on: bool) -> None:
        self._on_log_filter_chip_changed()
        self._save_logfirst_ui_prefs()

    def _on_log_filter_tx(self, on: bool) -> None:
        self._on_log_filter_chip_changed()
        self._save_logfirst_ui_prefs()

    def _on_log_filter_warn(self, on: bool) -> None:
        self._on_log_filter_chip_changed()
        self._save_logfirst_ui_prefs()

    def _on_log_pause_toggled(self, on: bool) -> None:
        self._set_log_pause(on)
        self._save_logfirst_ui_prefs()

    def _on_log_autoscroll_toggled(self, on: bool) -> None:
        self._set_log_autoscroll(on)
        self._save_logfirst_ui_prefs()

    def _on_log_preset_changed(self, _idx: int) -> None:
        if self._restoring_log_prefs:
            return
        self._on_log_preset_combo_changed(_idx)
        self._save_logfirst_ui_prefs()

    def _restore_logfirst_ui_prefs(self, drawer_btn: QtWidgets.QToolButton) -> None:
        prefs = load_logfirst_prefs()
        self._restoring_log_prefs = True
        try:
            self._apply_log_view_state(
                LogViewState.from_dict(prefs),
                persist=False,
                sync_widgets=True,
            )
            preset = self._log_view_state.preset
            for i in range(self.cmb_log_preset.count()):
                if str(self.cmb_log_preset.itemData(i) or "") == preset:
                    self.cmb_log_preset.setCurrentIndex(i)
                    break
            density = int(prefs.get("density", 8) or 8)
            self.cmb_log_density.setCurrentIndex(1 if density >= 10 else 0)
            self.chk_log_pause.setChecked(bool(prefs.get("pause", False)))
            self.chk_log_autoscroll.setChecked(bool(prefs.get("autoscroll", True)))
            drawer_btn.setChecked(bool(prefs.get("tools_open", False)))
        finally:
            self._restoring_log_prefs = False
        self._save_logfirst_ui_prefs()

    def _save_logfirst_ui_prefs(self) -> None:
        if self._restoring_log_prefs:
            return
        save_logfirst_prefs(
            {
                **self._log_view_state.to_dict(),
                "pause": self.chk_log_pause.isChecked(),
                "autoscroll": self.chk_log_autoscroll.isChecked(),
                "density": int(self.cmb_log_density.currentData() or 8),
                "tools_open": self._drawer_btn.isChecked(),
            }
        )
