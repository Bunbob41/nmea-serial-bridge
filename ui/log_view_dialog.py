"""Popup editor for live log view filters."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.collapsible import enable_dialog_content_fit, reflow_window
from ui.log_view import (
    PRESET_CUSTOM,
    PRESET_DEBUG,
    PRESET_LABELS,
    PRESET_OPS,
    PRESET_SURVEY,
    PRESET_WARN,
    PRESET_WIRE,
    LogViewState,
    sentence_type_choices,
    state_from_preset,
)


class LogViewDialog(QtWidgets.QDialog):
    """Choose what appears in the live log (independent of bridge NMEA passthrough/strict/raw)."""

    def __init__(
        self,
        state: LogViewState,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        nmea_mode_label: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Live log view")
        self.setMinimumWidth(420)
        self._initial = LogViewState(**{**state.to_dict(), "sentence_types": frozenset(state.sentence_types)})
        self._type_checks: dict[str, QtWidgets.QCheckBox] = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Controls what you <b>see</b> in the live log. "
            "Bridge NMEA mode (passthrough / strict / raw) is on the <b>NMEA</b> tab and "
            "controls what goes on the wire."
        )
        intro.setWordWrap(True)
        intro.setObjectName("tabHint")
        root.addWidget(intro)
        if nmea_mode_label:
            mode_lbl = QtWidgets.QLabel(f"Current bridge mode: <b>{nmea_mode_label}</b>")
            mode_lbl.setObjectName("tabNote")
            root.addWidget(mode_lbl)

        preset_grp = QtWidgets.QGroupBox("Quick presets")
        preset_lay = QtWidgets.QGridLayout(preset_grp)
        preset_lay.setHorizontalSpacing(8)
        preset_lay.setVerticalSpacing(6)
        presets = (
            (PRESET_OPS, 0, 0),
            (PRESET_SURVEY, 0, 1),
            (PRESET_WIRE, 0, 2),
            (PRESET_WARN, 1, 0),
            (PRESET_DEBUG, 1, 1),
        )
        self._preset_buttons: dict[str, QtWidgets.QPushButton] = {}
        for key, row, col in presets:
            btn = QtWidgets.QPushButton(PRESET_LABELS[key].replace(" (quiet)", "").replace("…", ""))
            btn.setToolTip(PRESET_LABELS[key])
            btn.clicked.connect(lambda _=False, k=key: self._apply_preset(k))
            preset_lay.addWidget(btn, row, col)
            self._preset_buttons[key] = btn
        root.addWidget(preset_grp)

        traffic = QtWidgets.QGroupBox("Traffic & status")
        tr_lay = QtWidgets.QVBoxLayout(traffic)
        self.chk_rx = QtWidgets.QCheckBox("Incoming (network → COM, inject)")
        self.chk_tx = QtWidgets.QCheckBox("Outgoing (COM → network)")
        self.chk_warn = QtWidgets.QCheckBox("Problems (drops, rejects, timeouts, errors)")
        self.chk_events = QtWidgets.QCheckBox("Bridge / UI messages (start, stop, presets, …)")
        for c in (self.chk_rx, self.chk_tx, self.chk_warn, self.chk_events):
            c.toggled.connect(self._mark_custom)
            tr_lay.addWidget(c)
        root.addWidget(traffic)

        nmea_grp = QtWidgets.QGroupBox("NMEA detail")
        nmea_lay = QtWidgets.QVBoxLayout(nmea_grp)
        self.chk_verbose = QtWidgets.QCheckBox("Every accepted NMEA sentence (high rate on busy links)")
        self.chk_verbose.setToolTip(
            "When off, the log still shows summaries and events; individual sentences are hidden."
        )
        self.chk_verbose.toggled.connect(self._on_verbose_toggled)
        self.chk_verbose.toggled.connect(self._mark_custom)
        nmea_lay.addWidget(self.chk_verbose)

        types_row = QtWidgets.QHBoxLayout()
        self.btn_types_all = QtWidgets.QPushButton("All types")
        self.btn_types_survey = QtWidgets.QPushButton("Survey (GGA+RMC)")
        self.btn_types_clear = QtWidgets.QPushButton("Clear")
        self.btn_types_all.clicked.connect(self._types_select_all)
        self.btn_types_survey.clicked.connect(self._types_select_survey)
        self.btn_types_clear.clicked.connect(self._types_clear)
        for b in (self.btn_types_all, self.btn_types_survey, self.btn_types_clear):
            b.clicked.connect(self._mark_custom)
        types_row.addWidget(QtWidgets.QLabel("Sentence types:"))
        types_row.addWidget(self.btn_types_all)
        types_row.addWidget(self.btn_types_survey)
        types_row.addWidget(self.btn_types_clear)
        types_row.addStretch(1)
        nmea_lay.addLayout(types_row)

        grid_host = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        for i, st in enumerate(sentence_type_choices()):
            cb = QtWidgets.QCheckBox(st)
            cb.toggled.connect(self._mark_custom)
            self._type_checks[st] = cb
            grid.addWidget(cb, i // 4, i % 4)
        nmea_lay.addWidget(grid_host)
        self._types_host = grid_host
        root.addWidget(nmea_grp)

        display = QtWidgets.QGroupBox("Display")
        disp_lay = QtWidgets.QVBoxLayout(display)
        self.chk_hex = QtWidgets.QCheckBox("Hex preview (raw binary mode only)")
        self.chk_hex.setToolTip(
            "Shows compact hex for binary chunks when the bridge is in raw mode. "
            "Enable raw on the NMEA tab first."
        )
        self.chk_hex.toggled.connect(self._mark_custom)
        disp_lay.addWidget(self.chk_hex)
        root.addWidget(display)

        self.lbl_custom = QtWidgets.QLabel("")
        self.lbl_custom.setObjectName("tabNote")
        root.addWidget(self.lbl_custom)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        enable_dialog_content_fit(self, min_width=420)
        self._load_state(state)
        self._on_verbose_toggled(self.chk_verbose.isChecked())

    def _apply_preset(self, key: str) -> None:
        self._load_state(state_from_preset(key))

    def _load_state(self, state: LogViewState) -> None:
        self._loading = True
        try:
            self.chk_rx.setChecked(state.rx)
            self.chk_tx.setChecked(state.tx)
            self.chk_warn.setChecked(state.warn)
            self.chk_events.setChecked(state.events)
            self.chk_verbose.setChecked(state.verbose)
            self.chk_hex.setChecked(state.hex)
            selected = state.sentence_types
            for st, cb in self._type_checks.items():
                cb.setChecked(not selected or st in selected)
            self._preset_active = state.preset if state.preset != PRESET_CUSTOM else None
            self._sync_custom_label(state)
        finally:
            self._loading = False

    def _mark_custom(self, *_a: object) -> None:
        if getattr(self, "_loading", False):
            return
        self._preset_active = None
        st = self.result_state()
        st.preset = PRESET_CUSTOM
        self._sync_custom_label(st)

    def _sync_custom_label(self, state: LogViewState) -> None:
        detected = state.detect_preset()
        if detected != PRESET_CUSTOM:
            self.lbl_custom.setText(f"Matches preset: {PRESET_LABELS[detected]}")
        else:
            self.lbl_custom.setText(state.toolbar_summary())

    def _on_verbose_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._types_host.setEnabled(enabled)
        self.btn_types_all.setEnabled(enabled)
        self.btn_types_survey.setEnabled(enabled)
        self.btn_types_clear.setEnabled(enabled)
        for cb in self._type_checks.values():
            cb.setEnabled(enabled)

    def _types_select_all(self) -> None:
        for cb in self._type_checks.values():
            cb.setChecked(True)

    def _types_select_survey(self) -> None:
        for st, cb in self._type_checks.items():
            cb.setChecked(st in ("GGA", "RMC"))

    def _types_clear(self) -> None:
        for cb in self._type_checks.values():
            cb.setChecked(False)

    def _selected_types(self) -> frozenset[str]:
        picked = {st for st, cb in self._type_checks.items() if cb.isChecked()}
        if len(picked) == len(self._type_checks):
            return frozenset()
        return frozenset(picked)

    def result_state(self) -> LogViewState:
        st = LogViewState(
            preset=getattr(self, "_preset_active", None) or PRESET_CUSTOM,
            rx=self.chk_rx.isChecked(),
            tx=self.chk_tx.isChecked(),
            warn=self.chk_warn.isChecked(),
            events=self.chk_events.isChecked(),
            verbose=self.chk_verbose.isChecked(),
            sentence_types=self._selected_types(),
            hex=self.chk_hex.isChecked(),
        )
        st.preset = st.detect_preset()
        return st

    @staticmethod
    def edit(
        state: LogViewState,
        parent: Optional[QtWidgets.QWidget],
        *,
        nmea_mode_label: str = "",
    ) -> Optional[LogViewState]:
        dlg = LogViewDialog(state, parent, nmea_mode_label=nmea_mode_label)
        dlg.show()
        reflow_window(dlg)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return dlg.result_state()
