"""Detachable survey stats window (Hypack / multi-monitor / full-screen bridge work)."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class SurveyStatsPopout(QtWidgets.QWidget):
    """Large, readable live stats separate from the main status bar."""

    def __init__(self, bridge_window: QtWidgets.QWidget) -> None:
        super().__init__(None)
        self._bridge = bridge_window
        self.setObjectName("SurveyStatsPopout")
        self.setWindowTitle("Survey stats — NMEA bridge")
        self.setMinimumSize(420, 220)
        self.resize(520, 260)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        flags = (
            QtCore.Qt.WindowType.Window
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlags(flags)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        hint = QtWidgets.QLabel(
            "Hypack / survey: watch ↓ Hz (NMEA toward the autopilot COM) and the transport line. "
            "Mission Planner / MAVLink on another COM is outside this NMEA path."
        )
        hint.setWordWrap(True)
        hint.setObjectName("surveyPopoutHint")
        root.addWidget(hint)

        self._serial = QtWidgets.QLabel("Serial: —")
        self._serial.setObjectName("surveyPopoutSerial")
        self._network = QtWidgets.QLabel("Network: —")
        self._network.setObjectName("surveyPopoutNetwork")

        mono = QtGui.QFont("Consolas", 13)
        if not QtGui.QFontInfo(mono).fixedPitch():
            mono = QtGui.QFont("Cascadia Mono", 13)
        if not QtGui.QFontInfo(mono).fixedPitch():
            mono = self.font()
            mono.setPointSize(13)
            mono.setBold(True)

        self._stats = QtWidgets.QLabel("Stopped")
        self._stats.setFont(mono)
        self._stats.setWordWrap(True)
        self._stats.setObjectName("surveyPopoutStats")
        self._stats.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        root.addWidget(self._serial)
        root.addWidget(self._network)
        root.addWidget(self._stats, 1)

        row = QtWidgets.QHBoxLayout()
        self._chk_top = QtWidgets.QCheckBox("Stay on top")
        self._chk_top.toggled.connect(self._on_stay_on_top)
        row.addWidget(self._chk_top)
        row.addStretch(1)
        root.addLayout(row)

    def _on_stay_on_top(self, on: bool) -> None:
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()
        self.raise_()
        self.activateWindow()

    def set_status_lines(self, serial: str, network: str) -> None:
        self._serial.setText(serial)
        self._network.setText(network)

    def set_stats_text(self, text: str, tooltip: str) -> None:
        self._stats.setText(text)
        self._stats.setToolTip(tooltip)

    def bridge_window(self) -> QtWidgets.QWidget:
        return self._bridge
