"""Modern Tools → NMEA — mode cards, strict presets, live next-Start summary."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from nmea_codec import NMEA_SENTENCE_TYPES

_SURVEY_TYPES = frozenset({"GGA", "RMC", "ZDA"})
_POSITION_TYPES = frozenset({"GGA"})
_ALL_TYPES = frozenset(NMEA_SENTENCE_TYPES)


def _apply_strict_types(
    parent: QtWidgets.QWidget,
    types: frozenset[str],
) -> None:
    rb = getattr(parent, "rb_nmea_strict", None)
    if rb is not None:
        rb.setChecked(True)
    checks = getattr(parent, "_nmea_type_checks", None)
    if not checks:
        return
    for st, cb in checks.items():
        cb.blockSignals(True)
        cb.setChecked(st in types)
        cb.blockSignals(False)
    sync = getattr(parent, "_sync_nmea_mode_ui", None)
    if callable(sync):
        sync()


def _on_type_check_toggled(parent: QtWidgets.QWidget) -> None:
    checks = getattr(parent, "_nmea_type_checks", None)
    rb_pass = getattr(parent, "rb_nmea_passthrough", None)
    rb_strict = getattr(parent, "rb_nmea_strict", None)
    if checks and rb_pass is not None and rb_strict is not None:
        if rb_pass.isChecked() and any(cb.isChecked() for cb in checks.values()):
            rb_strict.setChecked(True)
    sync = getattr(parent, "_sync_nmea_mode_ui", None)
    if callable(sync):
        sync()


def build_modern_nmea_settings(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """NMEA page for Modern Tools — same parent attrs as create_nmea_controls()."""
    host = QtWidgets.QWidget()
    host.setObjectName("modernNmeaSettings")
    root = QtWidgets.QVBoxLayout(host)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(14)

    parent.lbl_nmea_config_summary = QtWidgets.QLabel("")
    parent.lbl_nmea_config_summary.setObjectName("modernNmeaSummary")
    parent.lbl_nmea_config_summary.setWordWrap(True)
    root.addWidget(parent.lbl_nmea_config_summary)

    # ── Mode cards (reuse mixin radio attrs) ─────────────────────────────────
    parent.nmea_mode_group = QtWidgets.QButtonGroup(parent)
    parent.rb_nmea_passthrough = QtWidgets.QRadioButton()
    parent.rb_nmea_strict = QtWidgets.QRadioButton()
    parent.rb_nmea_raw = QtWidgets.QRadioButton()
    parent.rb_nmea_passthrough.setChecked(True)
    for rb in (parent.rb_nmea_passthrough, parent.rb_nmea_strict, parent.rb_nmea_raw):
        parent.nmea_mode_group.addButton(rb)

    cards = QtWidgets.QHBoxLayout()
    cards.setSpacing(10)
    cards.addWidget(
        _mode_card(
            parent.rb_nmea_passthrough,
            "Passthrough",
            "Default for Trimble R10 and survey UDP. Forwards NMEA with minimal changes.",
            mode_key="passthrough",
            recommended=True,
        ),
        1,
    )
    cards.addWidget(
        _mode_card(
            parent.rb_nmea_strict,
            "Strict filter",
            "Validates checksums and optionally limits which sentence types reach COM.",
            mode_key="strict",
        ),
        1,
    )
    cards.addWidget(
        _mode_card(
            parent.rb_nmea_raw,
            "Raw binary",
            "RTCM or other non-NMEA byte streams — no line assembly.",
            mode_key="raw",
        ),
        1,
    )
    root.addLayout(cards)

    # ── Strict panel ─────────────────────────────────────────────────────────
    strict_panel = QtWidgets.QFrame()
    strict_panel.setObjectName("modernNmeaStrictPanel")
    parent._nmea_strict_panel = strict_panel
    sp = QtWidgets.QVBoxLayout(strict_panel)
    sp.setContentsMargins(0, 0, 0, 0)
    sp.setSpacing(10)

    preset_lbl = QtWidgets.QLabel("Quick picks")
    preset_lbl.setObjectName("modernToolsInlineSection")
    sp.addWidget(preset_lbl)

    preset_row = QtWidgets.QHBoxLayout()
    preset_row.setSpacing(8)
    for label, types in (
        ("Survey GPS", _SURVEY_TYPES),
        ("Position only", _POSITION_TYPES),
        ("All types", _ALL_TYPES),
        ("Checksum only", frozenset()),
    ):
        btn = QtWidgets.QPushButton(label)
        btn.setObjectName("modernNmeaPresetBtn")
        tip = {
            "Survey GPS": "Strict + GGA, RMC, ZDA — typical GNSS survey feed.",
            "Position only": "Strict + GGA only.",
            "All types": "Strict + every listed sentence type enabled.",
            "Checksum only": "Strict + no type filter — valid checksum required for all types.",
        }[label]
        btn.setToolTip(tip)
        btn.clicked.connect(lambda _checked=False, t=types: _apply_strict_types(parent, t))
        preset_row.addWidget(btn)
    preset_row.addStretch(1)
    sp.addLayout(preset_row)

    types_box = QtWidgets.QGroupBox("Allowed sentence types")
    types_box.setObjectName("modernNmeaTypesBox")
    parent._nmea_strict_types_box = types_box
    grid = QtWidgets.QGridLayout(types_box)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(6)
    parent._nmea_type_checks = {}
    for i, st in enumerate(NMEA_SENTENCE_TYPES):
        cb = QtWidgets.QCheckBox(st)
        cb.setObjectName("modernNmeaTypeChip")
        cb.setChecked(st in _SURVEY_TYPES)
        cb.setToolTip(f"Allow ${st}… sentences through strict filter")
        cb.toggled.connect(lambda _checked, p=parent: _on_type_check_toggled(p))
        parent._nmea_type_checks[st] = cb
        grid.addWidget(cb, i // 4, i % 4)
    sp.addWidget(types_box)

    types_note = QtWidgets.QLabel(
        "Strict mode always validates checksums. Uncheck every type above for checksum-only "
        "(all sentence types pass if valid). Checking any type auto-selects Strict."
    )
    types_note.setWordWrap(True)
    types_note.setObjectName("tabNote")
    sp.addWidget(types_note)
    root.addWidget(strict_panel)

    # ── Preset link ──────────────────────────────────────────────────────────
    preset_link = QtWidgets.QFrame()
    preset_link.setObjectName("modernNmeaPresetLink")
    pl = QtWidgets.QVBoxLayout(preset_link)
    pl.setContentsMargins(0, 0, 0, 0)
    pl.setSpacing(8)

    parent.lbl_nmea_preset_link = QtWidgets.QLabel("")
    parent.lbl_nmea_preset_link.setObjectName("modernNmeaPresetLinkText")
    parent.lbl_nmea_preset_link.setWordWrap(True)
    pl.addWidget(parent.lbl_nmea_preset_link)

    preset_actions = QtWidgets.QHBoxLayout()
    preset_actions.setSpacing(8)
    parent.btn_nmea_load_preset = QtWidgets.QPushButton("Load from preset")
    parent.btn_nmea_load_preset.setObjectName("modernToolsSecondaryBtn")
    parent.btn_nmea_load_preset.setToolTip(
        "Apply NMEA mode and strict types from the selected or loaded preset."
    )
    parent.btn_nmea_save_preset = QtWidgets.QPushButton("Save NMEA to preset")
    parent.btn_nmea_save_preset.setObjectName("modernToolsPrimaryBtn")
    parent.btn_nmea_save_preset.setToolTip(
        "Write current NMEA mode and sentence types into the selected preset file."
    )
    load_fn = getattr(parent, "_load_nmea_from_preset", None)
    save_fn = getattr(parent, "_save_nmea_to_preset", None)
    if callable(load_fn):
        parent.btn_nmea_load_preset.clicked.connect(load_fn)
    if callable(save_fn):
        parent.btn_nmea_save_preset.clicked.connect(save_fn)
    preset_actions.addWidget(parent.btn_nmea_load_preset, 0)
    preset_actions.addWidget(parent.btn_nmea_save_preset, 0)
    preset_actions.addStretch(1)
    pl.addLayout(preset_actions)
    root.addWidget(preset_link)

    # ── Raw note ─────────────────────────────────────────────────────────────
    raw_note = QtWidgets.QFrame()
    raw_note.setObjectName("modernNmeaRawNote")
    parent._nmea_raw_note = raw_note
    rn = QtWidgets.QVBoxLayout(raw_note)
    rn.setContentsMargins(0, 0, 0, 0)
    raw_lbl = QtWidgets.QLabel(
        "Raw binary mode forwards bytes as-is. Do not use for standard NMEA text — "
        "survey targets expecting $GPGGA lines will see garbage."
    )
    raw_lbl.setWordWrap(True)
    raw_lbl.setObjectName("tabNote")
    rn.addWidget(raw_lbl)
    root.addWidget(raw_note)

    root.addStretch(1)

    parent._nmea_widgets = [
        parent.rb_nmea_passthrough,
        parent.rb_nmea_strict,
        parent.rb_nmea_raw,
        *parent._nmea_type_checks.values(),
    ]
    return host


def _mode_card(
    radio: QtWidgets.QRadioButton,
    title: str,
    body: str,
    *,
    mode_key: str,
    recommended: bool = False,
) -> QtWidgets.QFrame:
    frame = QtWidgets.QFrame()
    frame.setObjectName("modernNmeaModeCard")
    frame.setProperty("nmeaModeKey", mode_key)
    frame.setProperty("recommendedCard", recommended)
    frame.setProperty("modeCard", "recommended" if recommended else "normal")
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(4)

    title_row = QtWidgets.QHBoxLayout()
    title_row.setSpacing(8)
    radio.setText("")
    title_row.addWidget(radio, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    title_lbl = QtWidgets.QLabel(title)
    title_lbl.setObjectName("modernNmeaModeTitle")
    title_row.addWidget(title_lbl, 1)
    if recommended:
        badge = QtWidgets.QLabel("Recommended")
        badge.setObjectName("modernNmeaModeBadge")
        title_row.addWidget(badge, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    lay.addLayout(title_row)

    body_lbl = QtWidgets.QLabel(body)
    body_lbl.setWordWrap(True)
    body_lbl.setObjectName("modernNmeaModeBody")
    lay.addWidget(body_lbl)
    return frame
