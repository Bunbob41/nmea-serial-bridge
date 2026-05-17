"""Field UI — merged minimal + log-first: large log, compact connect, tools drawer."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.controls import (
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
from ui.ui_prefs import load_field_prefs, save_field_prefs
from version import __version__

# (dropdown label, saved id, hover help for field / first-time operators)
_FIELD_LOG_PRESETS: tuple[tuple[str, str, str], ...] = (
    (
        "Log: survey ops",
        "ops",
        "Default for survey and boat work.\n\n"
        "Shows: bridge start/stop, COM and UDP status, and short incoming/outgoing "
        "line summaries.\n\n"
        "Does not print every NMEA sentence — less noise when the INS sends many "
        "messages per second.\n\n"
        "Good first choice in the field if you are not sure which preset to use.",
    ),
    (
        "Log: full detail",
        "all",
        "Troubleshooting and bench checks.\n\n"
        "Shows everything in survey ops, plus each accepted NMEA sentence in the "
        "live log (same as turning on 'Every NMEA line').\n\n"
        "Use when you need to read exact GGA, RMC, etc. The log can scroll quickly "
        "at high data rates.",
    ),
    (
        "Log: problems only",
        "warn",
        "Alarms only.\n\n"
        "Shows drops (data arrived faster than the bridge could forward), rejects "
        "(invalid or filtered NMEA), and other warnings.\n\n"
        "Hides normal traffic. Use when Hypack, the autopilot path, or the status bar "
        "already looks wrong and you want a quiet log focused on faults.",
    ),
)


class BridgeWindowField(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._restoring_log_prefs = False
        self.setObjectName("BridgeRoot")
        self._ui_mode = "field"
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"NMEA Bridge (field) v{__version__}")
        self.resize(720, 520)
        self.setMinimumSize(560, 420)
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
        self.com_cb.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
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
        drawer_tabs.addTab(create_nmea_controls(self), "NMEA")
        drawer_tabs.addTab(create_theme_controls(self), "Theme")
        drawer_tabs.addTab(create_send_controls(self), "Send")
        drawer_tabs.addTab(create_diagnostics_controls(self), "Diagnostics")
        self._setup_reorderable_tabs(drawer_tabs, "tools_tabs")
        drawer_tabs.setVisible(False)
        drawer_tabs.setMinimumHeight(280)

        def _toggle(on: bool) -> None:
            drawer_tabs.setVisible(on)
            drawer.setText("Tools ▴" if on else "Tools ▾")
            self._save_field_ui_prefs()

        drawer.toggled.connect(_toggle)
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(drawer)
        self.chk_log_pause = QtWidgets.QCheckBox("Pause")
        self.chk_log_pause.setToolTip("Freeze the live log display (bridge keeps running).")
        self.chk_log_pause.toggled.connect(self._on_log_pause_toggled)
        self.chk_log_autoscroll = QtWidgets.QCheckBox("Auto-scroll")
        self.chk_log_autoscroll.setChecked(True)
        self.chk_log_autoscroll.setToolTip("Scroll to the newest line as traffic arrives.")
        self.chk_log_autoscroll.toggled.connect(self._on_log_autoscroll_toggled)
        r2.addWidget(self.chk_log_pause)
        r2.addWidget(self.chk_log_autoscroll)
        self.cmb_log_preset = QtWidgets.QComboBox()
        self._wire_field_log_preset_combo()
        self.cmb_log_preset.setMinimumWidth(148)
        self.cmb_log_preset.currentIndexChanged.connect(self._on_log_preset_changed)
        r2.addWidget(self.cmb_log_preset)
        self.cmb_log_density = QtWidgets.QComboBox()
        self.cmb_log_density.addItem("Font: dense", 8)
        self.cmb_log_density.addItem("Font: readable", 12)
        self.cmb_log_density.setMinimumWidth(108)
        self.cmb_log_density.setToolTip("Live log text size (overrides theme default).")
        self.cmb_log_density.currentIndexChanged.connect(self._apply_log_density)
        r2.addWidget(self.cmb_log_density)
        r2.addStretch(1)
        sl.addLayout(r2)
        sl.addWidget(drawer_tabs)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.addWidget(log_panel)
        self._splitter.addWidget(strip)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([440, 120])

        run_strip = QtWidgets.QFrame()
        run_strip.setObjectName("runStrip")
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
        self.status_nmea.setToolTip("NMEA passthrough, strict filter, or raw binary (RTCM / other).")
        self.status_gnss = QtWidgets.QLabel("GNSS: —")
        self.status_gnss.setToolTip("Live GGA fix, satellites, and HDOP while Running.")
        self.lbl_stats = QtWidgets.QLabel(
            "Stopped — when Running, wire Hz + transport + session totals (hover)"
        )
        self.lbl_stats.setToolTip(
            "Hz = wire update rate (UDP datagrams or serial read chunks per second), "
            "not NMEA sentences per second. Session totals count sentences."
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
        self._restore_field_ui_prefs(drawer)

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

    def _wire_field_log_preset_combo(self) -> None:
        combo = self.cmb_log_preset
        combo.clear()
        tip_role = QtCore.Qt.ItemDataRole.ToolTipRole
        status_role = QtCore.Qt.ItemDataRole.StatusTipRole
        for label, preset_id, help_text in _FIELD_LOG_PRESETS:
            combo.addItem(label, preset_id)
            idx = combo.count() - 1
            combo.setItemData(idx, help_text, tip_role)
            first_line = help_text.split("\n", 1)[0].strip()
            combo.setItemData(idx, first_line, status_role)
        combo.setToolTip(
            "How much to show in the live log.\n\n"
            "Open this list and hover each preset for a full explanation. "
            "Changing the preset does not stop the bridge or change your COM/UDP settings."
        )
        self._sync_log_preset_tooltip()

    def _sync_log_preset_tooltip(self) -> None:
        combo = self.cmb_log_preset
        idx = combo.currentIndex()
        if idx < 0:
            return
        item_tip = combo.itemData(idx, QtCore.Qt.ItemDataRole.ToolTipRole)
        if isinstance(item_tip, str) and item_tip.strip():
            combo.setToolTip(item_tip)
        combo.setStatusTip(
            str(combo.itemData(idx, QtCore.Qt.ItemDataRole.StatusTipRole) or combo.currentText())
        )

    def _apply_log_density(self, _idx: int) -> None:
        pt = int(self.cmb_log_density.currentData() or 8)
        self.log_view.setStyleSheet(
            f'QPlainTextEdit#logView {{ font-family: Consolas, "Cascadia Mono", monospace; '
            f"font-size: {pt}pt; }}"
        )
        self._save_field_ui_prefs()

    def _on_log_pause_toggled(self, on: bool) -> None:
        self._set_log_pause(on)
        self._save_field_ui_prefs()

    def _on_log_autoscroll_toggled(self, on: bool) -> None:
        self._set_log_autoscroll(on)
        self._save_field_ui_prefs()

    def _apply_log_view_preset(self, mode: str) -> None:
        if mode == "all":
            self._log_filter_rx = True
            self._log_filter_tx = True
            self._log_filter_warn = True
            self.chk_verbose_log.setChecked(True)
        elif mode == "warn":
            self._log_filter_rx = False
            self._log_filter_tx = False
            self._log_filter_warn = True
            self.chk_verbose_log.setChecked(False)
        else:
            self._log_filter_rx = True
            self._log_filter_tx = True
            self._log_filter_warn = True
            self.chk_verbose_log.setChecked(False)

    def _on_log_preset_changed(self, _idx: int) -> None:
        self._sync_log_preset_tooltip()
        if self._restoring_log_prefs:
            return
        mode = str(self.cmb_log_preset.currentData() or "ops")
        self._apply_log_view_preset(mode)
        self._save_field_ui_prefs()

    def _restore_field_ui_prefs(self, drawer_btn: QtWidgets.QToolButton) -> None:
        prefs = load_field_prefs()
        self._restoring_log_prefs = True
        try:
            preset_idx = {"ops": 0, "all": 1, "warn": 2}.get(str(prefs.get("preset", "ops")), 0)
            self.cmb_log_preset.setCurrentIndex(preset_idx)
            preset = str(prefs.get("preset", "ops"))
            self._apply_log_view_preset(preset)
            density = int(prefs.get("density", 8) or 8)
            self.cmb_log_density.setCurrentIndex(1 if density >= 10 else 0)
            self._apply_log_density(self.cmb_log_density.currentIndex())
            self.chk_log_pause.setChecked(bool(prefs.get("pause", False)))
            self.chk_log_autoscroll.setChecked(bool(prefs.get("autoscroll", True)))
            drawer_btn.setChecked(bool(prefs.get("tools_open", False)))
        finally:
            self._restoring_log_prefs = False
        self._sync_log_preset_tooltip()
        self._save_field_ui_prefs()

    def _save_field_ui_prefs(self) -> None:
        if self._restoring_log_prefs:
            return
        preset = str(self.cmb_log_preset.currentData() or "ops")
        save_field_prefs(
            {
                "rx": self._log_filter_rx,
                "tx": self._log_filter_tx,
                "warn": self._log_filter_warn,
                "pause": self.chk_log_pause.isChecked(),
                "autoscroll": self.chk_log_autoscroll.isChecked(),
                "verbose": self.chk_verbose_log.isChecked(),
                "preset": preset,
                "density": int(self.cmb_log_density.currentData() or 8),
                "tools_open": self._drawer_btn.isChecked(),
            }
        )
