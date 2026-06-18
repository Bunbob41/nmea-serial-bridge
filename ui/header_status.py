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

    def _elide_width(self) -> int:
        width = max(24, self.width())
        node: QtWidgets.QWidget | None = self.parentWidget()
        while node is not None:
            name = node.objectName() or ""
            if name == "modernHeaderStatusContainer":
                return max(width, node.width() - 8)
            if name == "modernStatusBanner":
                width = max(width, node.width() - 12)
            if name == "modernGlobalHeader":
                width = max(width, int(node.width() * 0.28))
            node = node.parentWidget()
        return width

    def refresh_elide(self) -> None:
        if not self._full_text:
            self.setText("")
            return
        width = self._elide_width()
        fm = self.fontMetrics()
        if fm.horizontalAdvance(self._full_text) <= width:
            self.setText(self._full_text)
            return
        mode = (
            QtCore.Qt.TextElideMode.ElideMiddle
            if " · " in self._full_text
            else QtCore.Qt.TextElideMode.ElideRight
        )
        self.setText(fm.elidedText(self._full_text, mode, width))
