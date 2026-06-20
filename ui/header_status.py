"""Modern header status strip - single-line elided status text."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

_STATUS_SEPARATORS: tuple[str, ...] = (" · ", "  ·  ", " — ", " - ")
_PROTECTED_TITLES: frozenset[str] = frozenset(
    {"Stopped", "Running", "Starting…", "Start failed"}
)


def split_status_title_detail(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    if not raw:
        return "", ""
    for sep in _STATUS_SEPARATORS:
        if sep in raw:
            title, detail = raw.split(sep, 1)
            return title.strip(), detail.strip()
    return raw, ""


class ElidedStatusLabel(QtWidgets.QLabel):
    """Header status line with trailing ellipsis when space is tight."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setMinimumWidth(0)
        self._apply_title_min_width()

    def _apply_title_min_width(self) -> None:
        fm = self.fontMetrics()
        self.setMinimumWidth(max(fm.horizontalAdvance("Stopped"), fm.horizontalAdvance("Running")) + 6)

    def set_full_text(self, text: str) -> None:
        self._full_text = str(text or "").strip()
        self.setToolTip(self._full_text if self._full_text else "")
        self.refresh_elide()
        if self._full_text:
            QtCore.QTimer.singleShot(0, self.refresh_elide)
            QtCore.QTimer.singleShot(120, self.refresh_elide)

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.refresh_elide()

    def _container_width(self) -> int:
        width = 0
        node: QtWidgets.QWidget | None = self.parentWidget()
        while node is not None:
            name = node.objectName() or ""
            if name == "modernHeaderStatusContainer":
                return max(width, node.width() - 8)
            if name == "modernStatusBanner":
                width = max(width, node.width() - 12)
            node = node.parentWidget()
        return width

    def _elide_width(self) -> int:
        label_w = max(0, self.contentsRect().width())
        if label_w > 32:
            return label_w
        banner_w = 0
        node: QtWidgets.QWidget | None = self.parentWidget()
        while node is not None:
            if (node.objectName() or "") == "modernStatusBanner":
                banner_w = max(0, node.width() - 16)
                break
            node = node.parentWidget()
        container_w = self._container_width()
        return max(24, label_w, banner_w, container_w)

    def refresh_elide(self) -> None:
        if not self._full_text:
            self.setText("")
            return
        width = self._elide_width()
        fm = self.fontMetrics()
        if fm.horizontalAdvance(self._full_text) <= width:
            self.setText(self._full_text)
            return

        title, detail = split_status_title_detail(self._full_text)
        if title in _PROTECTED_TITLES:
            title_width = fm.horizontalAdvance(title)
            if not detail or title_width + fm.horizontalAdvance(" · ") >= width:
                self.setText(title)
                return
            sep = " · "
            detail_width = max(0, width - title_width - fm.horizontalAdvance(sep))
            if detail_width <= 0:
                self.setText(title)
                return
            elided_detail = fm.elidedText(
                detail,
                QtCore.Qt.TextElideMode.ElideRight,
                detail_width,
            )
            self.setText(f"{title}{sep}{elided_detail}")
            return

        if not detail:
            self.setText(
                fm.elidedText(
                    title,
                    QtCore.Qt.TextElideMode.ElideRight,
                    width,
                )
            )
            return

        sep = " · "
        title_width = fm.horizontalAdvance(title)
        sep_width = fm.horizontalAdvance(sep)
        if title_width >= width:
            self.setText(
                fm.elidedText(
                    title,
                    QtCore.Qt.TextElideMode.ElideRight,
                    width,
                )
            )
            return

        detail_width = max(0, width - title_width - sep_width)
        if detail_width <= 0:
            self.setText(title)
            return

        elided_detail = fm.elidedText(
            detail,
            QtCore.Qt.TextElideMode.ElideRight,
            detail_width,
        )
        self.setText(f"{title}{sep}{elided_detail}")
