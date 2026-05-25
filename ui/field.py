"""Field UI — merged minimal + log-first: large log, compact connect, tools drawer."""
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
from ui.ui_prefs import load_field_prefs, save_field_prefs
from ui.ui_loader import LayoutLoadError, load_field_control_strip
from version import __version__

# Default log / control-strip split for ~960×580 (strip ≈ COM + status + preset + tool row).
_FIELD_DEFAULT_SPLITTER_SIZES = [500, 148]
_FIELD_STRIP_MIN_CLOSED = 118
_FIELD_STRIP_DRAWER_EXTRA = 284

_FIELD_LOG_PRESET_HELP: dict[str, str] = {
    "ops": (
        "Default for survey and boat work.\n\n"
        "Shows bridge events plus short traffic summaries — not every NMEA sentence."
    ),
    "survey": (
        "Survey-focused verbose log.\n\n"
        "Every GGA and RMC sentence, plus warnings and traffic summaries."
    ),
    "wire_tap": (
        "Full wire detail.\n\n"
        "Every accepted NMEA sentence (all types). Can scroll quickly at high rates."
    ),
    "warn_only": (
        "Problems only — drops, rejects, timeouts, and errors.\n\n"
        "Hides normal traffic."
    ),
    "debug": (
        "Everything: UI messages, all traffic, and every NMEA sentence."
    ),
}


class BridgeWindowField(BridgeLogicMixin, QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._restoring_log_prefs = False
        self._field_splitter_syncing = False
        self.setObjectName("BridgeRoot")
        self._ui_mode = "field"
        self.setStyleSheet(bridge_stylesheet(self._ui_mode, load_theme_choice()))
        self.setWindowTitle(f"NMEA Bridge (field) v{__version__}")
        self.resize(960, 580)
        self.setMinimumSize(720, 480)
        self._init_bridge_state()
        create_connection_controls(self)

        self.status_line = QtWidgets.QLabel("Stopped")
        self.status_line.setObjectName("statusLine")
        self.status_line.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        self.status_banner = self.status_line
        self.status_banner_text = self.status_line
        self._compact_intent_hint = False
        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("intentHint")
        self.intent_hint.setWordWrap(True)
        self.intent_hint.setMinimumHeight(28)
        self.intent_hint.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )

        log_panel = create_log_panel(self, show_header=False)
        self.chk_show_log.setChecked(True)
        self.chk_show_log.hide()
        log_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        strip = self._build_field_control_strip()
        self._control_strip = strip

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
        drawer_tabs.setMinimumHeight(320)

        def _toggle(on: bool) -> None:
            drawer_tabs.setVisible(on)
            drawer.setText("Tools ▴" if on else "Tools ▾")
            self._update_field_strip_min_height()
            self._save_field_ui_prefs()

        drawer.toggled.connect(_toggle)
        self.btn_field_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_field_refresh.setToolTip("Refresh Connection Hub discovery (serial + LAN).")
        self.btn_field_refresh.clicked.connect(self._on_hub_refresh_discovery)
        self.btn_field_unlock = QtWidgets.QPushButton("Unlock")
        self.btn_field_unlock.setToolTip("Unlock COM / check UDP listen port.")
        self.btn_field_unlock.clicked.connect(self._on_hub_unlock_ports)
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(self.btn_field_refresh)
        r2.addWidget(self.btn_field_unlock)
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
        self.btn_log_view = QtWidgets.QPushButton("View…")
        self.btn_log_view.setToolTip("Open live log filters (RX/TX, NMEA types, presets).")
        self.btn_log_view.clicked.connect(self._open_log_view_dialog)
        r2.addWidget(self.btn_log_view)
        self.cmb_log_density = QtWidgets.QComboBox()
        self.cmb_log_density.addItem("Font: dense", 8)
        self.cmb_log_density.addItem("Font: readable", 12)
        self.cmb_log_density.setMinimumWidth(108)
        self.cmb_log_density.setToolTip("Live log text size (overrides theme default).")
        self.cmb_log_density.currentIndexChanged.connect(self._apply_log_density)
        r2.addWidget(self.cmb_log_density)
        self.btn_clear_log.show()
        self.btn_save_live_log.show()
        r2.addWidget(self.btn_clear_log)
        r2.addWidget(self.btn_save_live_log)
        r2.addStretch(1)
        strip_lay = strip.layout()
        if strip_lay is not None:
            strip_lay.addLayout(r2)
            strip_lay.addWidget(drawer_tabs)
            strip_lay.addStretch(1)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._splitter.setObjectName("fieldMainSplitter")
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(log_panel)
        self._splitter.addWidget(strip)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes(list(_FIELD_DEFAULT_SPLITTER_SIZES))
        self._update_field_strip_min_height()
        self._splitter.splitterMoved.connect(self._on_field_splitter_moved)

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
            "Stopped — Hz & transport here when Running (hover)"
        )
        self.lbl_stats.setObjectName("lblStats")
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
        self._restore_field_splitter_sizes()
        QtCore.QTimer.singleShot(80, self._restore_field_splitter_sizes)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_intent_hint_display()
        from ui.controls import refresh_status_bar_labels

        refresh_status_bar_labels(self)

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._refresh_field_layout_text)
        QtCore.QTimer.singleShot(120, self._refresh_field_layout_text)
        from ui.connect_qr_overlay import schedule_qr_on_window_show

        schedule_qr_on_window_show(self)

    def _refresh_field_layout_text(self) -> None:
        self._apply_intent_hint_display()
        from ui.controls import refresh_status_bar_labels

        refresh_status_bar_labels(self)
        bar = getattr(self, "_survey_top_bar", None)
        if bar is not None:
            bar._schedule_spring_layout()

    def _build_field_control_strip(self) -> QtWidgets.QFrame:
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
        self.udp_host.setMinimumWidth(88)
        self.udp_host.setMaximumWidth(132)
        self.udp_host.setToolTip("UDP listen bind address (Tools → Presets for TCP modes).")
        r1.addWidget(self.udp_host)
        r1.addWidget(QtWidgets.QLabel(":"))
        self.udp_port.setMinimumWidth(52)
        self.udp_port.setMaximumWidth(72)
        self.udp_port.setToolTip("UDP listen port — senders use this port on the host above.")
        r1.addWidget(self.udp_port)

        self._field_connect_summary = QtWidgets.QLabel("")
        self._field_connect_summary.setObjectName("fieldConnectSummary")
        self._field_connect_summary.setWordWrap(True)

        try:
            shell = load_field_control_strip(self)
            shell.setObjectName("controlStrip")
            shell.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            strip_host = shell.findChild(QtWidgets.QWidget, "fieldStripHost")
            if strip_host is not None:
                host_lay = QtWidgets.QVBoxLayout(strip_host)
                host_lay.setContentsMargins(0, 0, 0, 0)
                host_lay.setSpacing(3)
                host_lay.addLayout(r1)
                host_lay.addWidget(self._field_connect_summary)
            status_host = shell.findChild(QtWidgets.QWidget, "fieldStatusHost")
            if status_host is not None:
                st_lay = QtWidgets.QVBoxLayout(status_host)
                st_lay.setContentsMargins(0, 0, 0, 0)
                st_lay.setSpacing(3)
                st_lay.addWidget(self.status_line)
                st_lay.addWidget(self.intent_hint)
            return shell  # type: ignore[return-value]
        except LayoutLoadError:
            return self._build_field_strip_programmatic(r1)

    def _build_field_strip_programmatic(self, r1: QtWidgets.QHBoxLayout) -> QtWidgets.QFrame:
        strip = QtWidgets.QFrame()
        strip.setObjectName("controlStrip")
        strip.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        sl = QtWidgets.QVBoxLayout(strip)
        sl.setContentsMargins(8, 4, 8, 4)
        sl.setSpacing(3)
        sl.addLayout(r1)
        sl.addWidget(self._field_connect_summary)
        sl.addWidget(self.status_line)
        sl.addWidget(self.intent_hint)
        return strip

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_line.setProperty("state", state)
        text = title if not detail else f"{title} | {detail}"
        self.status_line.setText(text)

    def _toggle_log_panel(self, _visible: bool) -> None:
        pass

    def _on_ui_ready(self) -> None:
        self._set_status_banner("stopped", "Stopped")
        self._refresh_intent_hint()
        self._ensure_readable_top_bar()

    def _field_strip_min_height(self) -> int:
        if self._drawer_btn.isChecked():
            return _FIELD_STRIP_MIN_CLOSED + _FIELD_STRIP_DRAWER_EXTRA
        return _FIELD_STRIP_MIN_CLOSED

    def _update_field_strip_min_height(self) -> None:
        strip = getattr(self, "_control_strip", None)
        if strip is not None:
            strip.setMinimumHeight(self._field_strip_min_height())

    def _on_field_splitter_moved(self, *_a: object) -> None:
        if getattr(self, "_field_splitter_syncing", False):
            return
        if not hasattr(self, "_field_splitter_save_timer"):
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(self._save_field_ui_prefs)
            self._field_splitter_save_timer = t
        self._field_splitter_save_timer.start(200)

    def _restore_field_splitter_sizes(self) -> None:
        sp = getattr(self, "_splitter", None)
        if sp is None:
            return
        default = list(_FIELD_DEFAULT_SPLITTER_SIZES)
        prefs = load_field_prefs()
        raw = prefs.get("splitter_sizes")
        sizes = list(default)
        strip_floor = self._field_strip_min_height()
        if isinstance(raw, list) and len(raw) >= 2:
            try:
                sizes = [
                    max(int(raw[0]), 120),
                    max(int(raw[1]), strip_floor),
                ]
            except (TypeError, ValueError):
                sizes = list(default)
        # Older saves gave the strip ~40%+ of the window — pull it in on load.
        total = sum(sizes)
        if total > 0 and sizes[1] / total > 0.34:
            sizes = list(default)
        sizes[1] = max(sizes[1], strip_floor)
        self._field_splitter_syncing = True
        sp.blockSignals(True)
        try:
            sp.setSizes(sizes)
        finally:
            sp.blockSignals(False)
            self._field_splitter_syncing = False

    def _wire_field_log_preset_combo(self) -> None:
        combo = self.cmb_log_preset
        combo.clear()
        tip_role = QtCore.Qt.ItemDataRole.ToolTipRole
        status_role = QtCore.Qt.ItemDataRole.StatusTipRole
        for preset_id in TOOLBAR_PRESETS:
            if preset_id == PRESET_CUSTOM:
                continue
            label = PRESET_LABELS[preset_id]
            help_text = _FIELD_LOG_PRESET_HELP.get(preset_id, label)
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

    def _on_log_preset_changed(self, _idx: int) -> None:
        self._sync_log_preset_tooltip()
        if self._restoring_log_prefs:
            return
        self._on_log_preset_combo_changed(_idx)

    def _restore_field_ui_prefs(self, drawer_btn: QtWidgets.QToolButton) -> None:
        prefs = load_field_prefs()
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
            self._apply_log_density(self.cmb_log_density.currentIndex())
            self.chk_log_pause.setChecked(bool(prefs.get("pause", False)))
            self.chk_log_autoscroll.setChecked(bool(prefs.get("autoscroll", True)))
            drawer_btn.setChecked(bool(prefs.get("tools_open", False)))
        finally:
            self._restoring_log_prefs = False
        self._update_field_strip_min_height()
        self._sync_log_preset_tooltip()
        self._save_field_ui_prefs()

    def _save_field_ui_prefs(self) -> None:
        if self._restoring_log_prefs:
            return
        payload: dict = {
            **self._log_view_state.to_dict(),
            "pause": self.chk_log_pause.isChecked(),
            "autoscroll": self.chk_log_autoscroll.isChecked(),
            "density": int(self.cmb_log_density.currentData() or 8),
            "tools_open": self._drawer_btn.isChecked(),
        }
        sp = getattr(self, "_splitter", None)
        if sp is not None:
            payload["splitter_sizes"] = [int(x) for x in sp.sizes()]
        save_field_prefs(payload)
