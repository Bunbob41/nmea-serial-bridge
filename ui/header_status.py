"""Modern header status strip - single-line elided status text."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

_STATUS_SEPARATORS: tuple[str, ...] = (" · ", "  ·  ", " — ", " - ")
_PROTECTED_TITLES: frozenset[str] = frozenset(
    {
        "Stopped",
        "Running",
        "Starting…",
        "Start failed",
        "● Stopped",
        "● Starting…",
        "● Start failed",
        "stopped",
        "running",
        "starting…",
        "failed",
    }
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


def _safe_widget_width(widget: QtWidgets.QWidget) -> int:
    try:
        return max(0, widget.width())
    except RuntimeError:
        return 0


class ElidedStatusLabel(QtWidgets.QLabel):
    """Header status line with trailing ellipsis when space is tight."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self._elide_refresh_depth = 0
        self.setWordWrap(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setMinimumWidth(0)
        self._defer_elide_timer = QtCore.QTimer(self)
        self._defer_elide_timer.setSingleShot(True)
        self._defer_elide_timer.timeout.connect(self.refresh_elide)
        self._defer_elide_late_timer = QtCore.QTimer(self)
        self._defer_elide_late_timer.setSingleShot(True)
        self._defer_elide_late_timer.setInterval(120)
        self._defer_elide_late_timer.timeout.connect(self.refresh_elide)
        self._apply_title_min_width()

    def _apply_title_min_width(self) -> None:
        fm = self.fontMetrics()
        self.setMinimumWidth(
            max(
                fm.horizontalAdvance("stopped"),
                fm.horizontalAdvance("Stopped"),
                fm.horizontalAdvance("running"),
                fm.horizontalAdvance("Running"),
            )
            + 10
        )

    def set_full_text(self, text: str) -> None:
        self._full_text = str(text or "").strip()
        self.setToolTip(self._full_text if self._full_text else "")
        self.refresh_elide()
        if self._full_text:
            self._defer_elide_timer.start(0)
            self._defer_elide_late_timer.start()

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if event.size().width() == event.oldSize().width():
            return
        if not self._defer_elide_timer.isActive():
            self._defer_elide_timer.start(0)

    def _container_width(self) -> int:
        width = 0
        node: QtWidgets.QWidget | None = self.parentWidget()
        while node is not None:
            try:
                name = node.objectName() or ""
                if name == "modernHeaderStatusContainer":
                    return max(width, _safe_widget_width(node) - 8)
                if name == "modernStatusBanner":
                    width = max(width, _safe_widget_width(node) - 12)
                node = node.parentWidget()
            except RuntimeError:
                break
        return width

    def _elide_width(self) -> int:
        try:
            label_w = max(0, self.contentsRect().width())
        except RuntimeError:
            return 24
        if label_w > 32:
            return label_w
        banner_w = 0
        node: QtWidgets.QWidget | None = self.parentWidget()
        while node is not None:
            try:
                if (node.objectName() or "") == "modernStatusBanner":
                    banner_w = max(0, _safe_widget_width(node) - 16)
                    break
                node = node.parentWidget()
            except RuntimeError:
                break
        container_w = self._container_width()
        return max(24, label_w, banner_w, container_w)

    def refresh_elide(self) -> None:
        if self._elide_refresh_depth > 0:
            return
        self._elide_refresh_depth += 1
        try:
            self._refresh_elide_impl()
        finally:
            self._elide_refresh_depth -= 1

    def _refresh_elide_impl(self) -> None:
        if not self._full_text:
            self.setText("")
            return
        width = self._elide_width()
        fm = self.fontMetrics()
        title, detail = split_status_title_detail(self._full_text)
        if title in _PROTECTED_TITLES:
            if fm.horizontalAdvance(self._full_text) <= width:
                self.setText(self._full_text)
                return
            # Protected capsule titles must never clip mid-word (e.g. "Stoppe…").
            self.setText(title)
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
