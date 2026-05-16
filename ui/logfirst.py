"""Log-first UI — dark theme, log uses most of the window."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

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
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setWordWrap(True)
        self.intent_hint.setVisible(False)

        log_panel = create_log_panel(self)
        self.chk_show_log.setChecked(True)
        self.chk_show_log.hide()

        strip = QtWidgets.QFrame()
        strip.setObjectName("controlStrip")
        sl = QtWidgets.QVBoxLayout(strip)
        sl.setContentsMargins(8, 6, 8, 6)
        r0 = QtWidgets.QHBoxLayout()
        r0.setSpacing(6)
        self.btn_bench_preset.setMinimumWidth(96)
        self.btn_production_preset.setMinimumWidth(96)
        self.refresh_btn.setMinimumWidth(64)
        r0.addWidget(self.btn_bench_preset)
        r0.addWidget(self.btn_production_preset)
        r0.addStretch(1)
        sl.addLayout(r0)

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
        self.udp_host.setToolTip("UDP listen bind address (see Network+ tab for TCP modes).")
        r1.addWidget(self.udp_host)
        r1.addWidget(QtWidgets.QLabel(":"))
        self.udp_port.setMaximumWidth(64)
        self.udp_port.setToolTip("UDP listen port — senders use this port on the host above.")
        r1.addWidget(self.udp_port)
        sl.addLayout(r1)
        sl.addWidget(self.status_line)

        drawer = QtWidgets.QToolButton()
        self._drawer_btn = drawer
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
        self.cmb_log_preset.addItem("Preset: Ops", "ops")
        self.cmb_log_preset.addItem("Preset: All", "all")
        self.cmb_log_preset.addItem("Preset: Warn", "warn")
        self.cmb_log_preset.setMinimumWidth(112)
        self.cmb_log_preset.setToolTip("Quick log filter presets")
        self.cmb_log_preset.currentIndexChanged.connect(self._on_log_preset_changed)
        r2.addWidget(self.cmb_log_preset)
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
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, Hz + transport + session totals (hover)"
        )
        self.statusBar.addWidget(self.status_serial, 1)
        self.statusBar.addWidget(self.status_network, 1)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(run_strip)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)
        self._finalize_ui()
        self._apply_log_density(0)
        self._restore_logfirst_ui_prefs(drawer)

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
        self._log_filter_rx = bool(on)
        self._save_logfirst_ui_prefs()

    def _on_log_filter_tx(self, on: bool) -> None:
        self._log_filter_tx = bool(on)
        self._save_logfirst_ui_prefs()

    def _on_log_filter_warn(self, on: bool) -> None:
        self._log_filter_warn = bool(on)
        self._save_logfirst_ui_prefs()

    def _on_log_pause_toggled(self, on: bool) -> None:
        self._set_log_pause(on)
        self._save_logfirst_ui_prefs()

    def _on_log_autoscroll_toggled(self, on: bool) -> None:
        self._set_log_autoscroll(on)
        self._save_logfirst_ui_prefs()

    def _preset_log_all(self) -> None:
        self.chk_log_rx.setChecked(True)
        self.chk_log_tx.setChecked(True)
        self.chk_log_warn.setChecked(True)
        self.chk_verbose_log.setChecked(True)

    def _preset_log_ops(self) -> None:
        self.chk_log_rx.setChecked(True)
        self.chk_log_tx.setChecked(True)
        self.chk_log_warn.setChecked(True)
        self.chk_verbose_log.setChecked(False)

    def _preset_log_warn(self) -> None:
        self.chk_log_rx.setChecked(False)
        self.chk_log_tx.setChecked(False)
        self.chk_log_warn.setChecked(True)
        self.chk_verbose_log.setChecked(False)

    def _on_log_preset_changed(self, _idx: int) -> None:
        mode = str(self.cmb_log_preset.currentData() or "ops")
        if mode == "all":
            self._preset_log_all()
        elif mode == "warn":
            self._preset_log_warn()
        else:
            self._preset_log_ops()
        self._save_logfirst_ui_prefs()

    def _restore_logfirst_ui_prefs(self, drawer_btn: QtWidgets.QToolButton) -> None:
        prefs = load_logfirst_prefs()
        self._restoring_log_prefs = True
        try:
            preset_idx = {"ops": 0, "all": 1, "warn": 2}.get(str(prefs.get("preset", "ops")), 0)
            self.cmb_log_preset.setCurrentIndex(preset_idx)
            self.chk_log_rx.setChecked(bool(prefs.get("rx", True)))
            self.chk_log_tx.setChecked(bool(prefs.get("tx", True)))
            self.chk_log_warn.setChecked(bool(prefs.get("warn", True)))
            self.chk_verbose_log.setChecked(bool(prefs.get("verbose", False)))
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
        preset = str(self.cmb_log_preset.currentData() or "ops")
        save_logfirst_prefs(
            {
                "rx": self.chk_log_rx.isChecked(),
                "tx": self.chk_log_tx.isChecked(),
                "warn": self.chk_log_warn.isChecked(),
                "pause": self.chk_log_pause.isChecked(),
                "autoscroll": self.chk_log_autoscroll.isChecked(),
                "verbose": self.chk_verbose_log.isChecked(),
                "preset": preset,
                "density": int(self.cmb_log_density.currentData() or 8),
                "tools_open": self._drawer_btn.isChecked(),
            }
        )
