"""Modern Tools page bodies — flat layouts with live summary banners."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets


def _tools_summary_label(parent: QtWidgets.QWidget, attr: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel("—")
    lbl.setObjectName("modernToolsSummary")
    lbl.setWordWrap(True)
    setattr(parent, attr, lbl)
    return lbl


def build_modern_presets_body(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.presets_panel import create_presets_tab

    host = QtWidgets.QWidget()
    host.setObjectName("modernPresetsBody")
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    lay.addWidget(_tools_summary_label(parent, "lbl_presets_live_status"))
    body = create_presets_tab(parent, include_advanced_net=False, embedded=True)
    lay.addWidget(body, 1)
    return host


def build_modern_activity_body(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    host.setObjectName("modernActivityBody")
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    lay.addWidget(_tools_summary_label(parent, "lbl_activity_live_status"))

    row = QtWidgets.QHBoxLayout()
    row.setSpacing(8)
    parent.btn_clear_ui = QtWidgets.QPushButton("Clear Activity panel")
    parent.btn_clear_ui.setObjectName("modernToolsPrimaryBtn")
    parent.btn_clear_ui.setToolTip(
        "Clears the on-screen Activity view — does not delete file logs or black-box .nmea files."
    )
    row.addWidget(parent.btn_clear_ui, 0)

    btn_open = QtWidgets.QPushButton("Open Activity tab")
    btn_open.setObjectName("modernToolsSecondaryBtn")
    btn_open.setToolTip("Jump to the main Activity tab (live wire-tap traffic).")
    show_tab = getattr(parent, "_show_modern_pipeline_tab", None)
    if callable(show_tab):
        btn_open.clicked.connect(show_tab)
    row.addWidget(btn_open, 0)
    row.addStretch(1)
    lay.addLayout(row)

    note = QtWidgets.QLabel(
        "Use Clear when the wire-tap view gets noisy. Pause and filters are on the Activity tab toolbar."
    )
    note.setWordWrap(True)
    note.setObjectName("tabNote")
    lay.addWidget(note)
    lay.addStretch(1)
    return host
