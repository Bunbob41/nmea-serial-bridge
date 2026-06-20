"""Serial mirror port pickers — two optional COM dropdowns (max 2 mirrors)."""
from __future__ import annotations

from typing import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import parse_serial_mirror_ports
from ui.connection_fields import sort_com_devices

NONE_LABEL = "(none)"
NO_PORTS_LABEL = "(no ports — Refresh)"


class _MirrorCombo(QtWidgets.QComboBox):
    """COM mirror dropdown; ignore mouse wheel."""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()


class SerialMirrorPortPicker(QtWidgets.QWidget):
    """Two optional mirror COM selectors backed by live port enumeration."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("serialMirrorPortPicker")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._cb1 = _MirrorCombo()
        self._cb2 = _MirrorCombo()
        for cb in (self._cb1, self._cb2):
            cb.setObjectName("serialMirrorCombo")
            cb.setEditable(False)
            cb.setMinimumHeight(32)
            cb.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
            cb.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            layout.addWidget(cb, 1)
        self.setToolTip(
            "Optional write-only COM copies at the same baud as the primary port.\n\n"
            "Pick up to two monitor legs (e.g. com0com far end). Primary COM is hidden here."
        )
        self._cb1.currentTextChanged.connect(self._dedupe_selections)
        self._cb2.currentTextChanged.connect(self._dedupe_selections)
        self.refresh()

    def text(self) -> str:
        ports: list[str] = []
        for cb in (self._cb1, self._cb2):
            value = cb.currentText().strip().upper()
            if value and value not in (NONE_LABEL.upper(), NO_PORTS_LABEL.upper()) and not value.startswith("("):
                if value not in ports:
                    ports.append(value)
        return ", ".join(ports)

    def setText(self, raw: str) -> None:
        self.set_ports(raw)

    def set_ports(self, raw: str | Iterable[str]) -> None:
        if isinstance(raw, str):
            ports = list(parse_serial_mirror_ports(raw, primary=""))
        else:
            ports = [str(p).strip().upper() for p in raw if str(p).strip()][:2]
        selections = [ports[0] if len(ports) > 0 else "", ports[1] if len(ports) > 1 else ""]
        for cb, port in zip((self._cb1, self._cb2), selections, strict=True):
            self._set_combo_port(cb, port)

    def refresh(
        self,
        devices: list[str] | None = None,
        *,
        primary_com: str = "",
    ) -> None:
        if devices is None:
            import serial.tools.list_ports

            devices = [p.device for p in serial.tools.list_ports.comports()]
        primary = (primary_com or "").strip().upper()
        available = [
            d for d in sort_com_devices(devices) if d.strip().upper() != primary
        ]
        for cb in (self._cb1, self._cb2):
            prev = cb.currentText().strip().upper()
            if prev in ("", NONE_LABEL.upper()) or prev.startswith("("):
                prev = ""
            cb.blockSignals(True)
            try:
                cb.clear()
                cb.addItem(NONE_LABEL)
                if not available:
                    cb.addItem(NO_PORTS_LABEL)
                else:
                    for device in available:
                        cb.addItem(device)
                cb.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
                cb.setMaxVisibleItems(16)
                if prev and prev != primary:
                    idx = cb.findText(prev, QtCore.Qt.MatchFlag.MatchFixedString)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
                    else:
                        cb.insertItem(1, prev)
                        cb.setCurrentIndex(1)
                else:
                    cb.setCurrentIndex(0)
            finally:
                cb.blockSignals(False)

    def _set_combo_port(self, cb: QtWidgets.QComboBox, port: str) -> None:
        value = (port or "").strip().upper()
        if not value:
            idx = cb.findText(NONE_LABEL)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            return
        idx = cb.findText(value, QtCore.Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            cb.setCurrentIndex(idx)
        else:
            none_idx = cb.findText(NONE_LABEL)
            insert_at = 1 if none_idx >= 0 else 0
            cb.insertItem(insert_at, value)
            cb.setCurrentIndex(insert_at)

    def _dedupe_selections(self, _text: str = "") -> None:
        a = self._cb1.currentText().strip().upper()
        b = self._cb2.currentText().strip().upper()
        if not a or not b or a == NONE_LABEL.upper() or b == NONE_LABEL.upper():
            return
        if a != b:
            return
        sender = self.sender()
        if sender is self._cb1:
            self._cb2.blockSignals(True)
            try:
                self._set_combo_port(self._cb2, "")
            finally:
                self._cb2.blockSignals(False)
        elif sender is self._cb2:
            self._cb1.blockSignals(True)
            try:
                self._set_combo_port(self._cb1, "")
            finally:
                self._cb1.blockSignals(False)