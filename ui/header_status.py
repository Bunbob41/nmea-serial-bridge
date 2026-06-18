"""Modern header status strip - single-line elided status text."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class ElidedStatusLabel(QtWidgets.QLabel):
    """Header status line with trailing ellipsis when space is tight."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setMinimumWidth(0)

    def set_full_text(self, text: str) -> None:
        self._full_text = str(text or "").strip()
        self.setToolTip(self._full_text if self._full_text else "")
        self.refresh_elide()

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.refresh_elide()

    def refresh_elide(self) -> None:
        if not self._full_text:
            self.setText("")
            return
        width = max(24, self.width())
        parent = self.parentWidget()
        if parent is not None:
            width = max(width, parent.width() - 12)
        fm = self.fontMetrics()
        if fm.horizontalAdvance(self._full_text) <= width:
            self.setText(self._full_text)
            return
        self.setText(
            fm.elidedText(
                self._full_text,
                QtCore.Qt.TextElideMode.ElideRight,
                width,
            )
        )
