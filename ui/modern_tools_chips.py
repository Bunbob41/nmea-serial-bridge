"""Horizontal tools chip rail for Modern UI (top navigation mode)."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class ModernToolsChipScrollArea(QtWidgets.QScrollArea):
    """Single-row chip rail; mouse wheel scrolls horizontally."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modernToolsChipScroll")
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setWidgetResizable(False)
        self.setMinimumWidth(0)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - delta)
            event.accept()
            return
        super().wheelEvent(event)


def make_chip_group_separator() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setObjectName("modernToolsChipSep")
    sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setFixedHeight(22)
    return sep
