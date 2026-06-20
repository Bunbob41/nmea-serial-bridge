"""Draggable horizontal split for the Modern global header bar."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

HEADER_SPLIT_PANE_COUNT = 4
HEADER_HANDLE_LOCKED = 1
HEADER_HANDLE_UNLOCKED = 7

_HEADER_RUN_MIN = 90
_HEADER_STATUS_MIN = 72
_HEADER_CHIPS_MIN = 56
_STATIC_TRAIL_MIN = 240


def layout_chip_min_width() -> int:
    if QtWidgets.QApplication.instance() is None:
        return 98
    font = QtGui.QFont()
    font.setPointSizeF(9.0)
    font.setWeight(QtGui.QFont.Weight.DemiBold)
    metrics = QtGui.QFontMetrics(font)
    return metrics.horizontalAdvance("Layout") + 36


def embedded_nav_cluster_min_width() -> int:
    from ui.survey_top_bar import _CLUSTER_CHIP_MIN_WIDTH

    keys = ("view", "hud", "ui_switch")
    spacing = 4 * max(0, len(keys) - 1)
    chip_total = sum(
        max(
            _CLUSTER_CHIP_MIN_WIDTH.get(k, 52),
            layout_chip_min_width() if k == "ui_switch" else 0,
        )
        for k in keys
    )
    return max(_STATIC_TRAIL_MIN, chip_total + spacing + 12)


def header_split_mins() -> tuple[int, int, int, int]:
    trail = embedded_nav_cluster_min_width()
    return (_HEADER_RUN_MIN, _HEADER_STATUS_MIN, _HEADER_CHIPS_MIN, trail)


def header_split_defaults() -> tuple[int, int, int, int]:
    _run, _status, _chips, trail = header_split_mins()
    return (130, 100, 420, max(trail, 300))


HEADER_SPLIT_MIN = (_HEADER_RUN_MIN, _HEADER_STATUS_MIN, _HEADER_CHIPS_MIN, _STATIC_TRAIL_MIN)
HEADER_SPLIT_DEFAULT = (130, 100, 420, 300)


class ModernHeaderSplitter(QtWidgets.QSplitter):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)
        self.setObjectName("modernHeaderSplitter")
        self.setChildrenCollapsible(False)
        self._resize_unlocked = False

    def apply_lock(self, *, unlocked: bool) -> None:
        self._resize_unlocked = bool(unlocked)
        self.setHandleWidth(HEADER_HANDLE_UNLOCKED if unlocked else HEADER_HANDLE_LOCKED)
        cursor = (
            QtCore.Qt.CursorShape.SplitHCursor
            if unlocked
            else QtCore.Qt.CursorShape.ArrowCursor
        )
        tip = (
            "Drag to resize header sections. View -> Resize header sections: uncheck to lock."
            if unlocked
            else ""
        )
        for index in range(self.count() - 1):
            handle = self.handle(index)
            handle.setEnabled(unlocked)
            handle.setCursor(cursor)
            handle.setToolTip(tip)
        self.setProperty("resizeUnlocked", "true" if unlocked else "false")
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)

    def is_resize_unlocked(self) -> bool:
        return self._resize_unlocked

    def clamp_sizes(self, sizes: list[int]) -> list[int]:
        mins = header_split_mins()
        defaults = header_split_defaults()
        out = list(sizes[:HEADER_SPLIT_PANE_COUNT])
        while len(out) < HEADER_SPLIT_PANE_COUNT:
            out.append(defaults[len(out)])
        return [max(mins[i], int(out[i])) for i in range(HEADER_SPLIT_PANE_COUNT)]

    def set_clamped_sizes(self, sizes: list[int]) -> None:
        clamped = self.clamp_sizes(sizes)
        mins = header_split_mins()
        width = max(self.width(), 1)
        total = sum(clamped)

        if total < width:
            clamped[2] += width - total
        elif total > width:
            over = total - width
            # Shrink trail/status/run before the tool-chip rail when the bar is tight.
            for idx in (3, 1, 0, 2):
                if over <= 0:
                    break
                room = max(0, clamped[idx] - mins[idx])
                take = min(over, room)
                clamped[idx] -= take
                over -= take

        if len(clamped) >= 3:
            clamped[2] = max(mins[2], clamped[2] + (width - sum(clamped)))

        self.setSizes(clamped)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.count() < 3:
            return
        sizes = list(self.sizes())
        total = sum(sizes)
        width = self.width()
        if total < width:
            sizes[2] += width - total
            self.setSizes(sizes)
        host = self.window()
        sync = getattr(host, "_sync_modern_header_chip_compression", None)
        if callable(sync):
            QtCore.QTimer.singleShot(0, sync)


def wrap_header_pane(
    child: QtWidgets.QWidget,
    *,
    object_name: str,
    min_width: int,
    stretch: bool = False,
) -> QtWidgets.QWidget:
    pane = QtWidgets.QWidget()
    pane.setObjectName(object_name)
    pane.setMinimumWidth(min_width)
    policy = (
        QtWidgets.QSizePolicy.Policy.Expanding
        if stretch
        else QtWidgets.QSizePolicy.Policy.Minimum
    )
    pane.setSizePolicy(policy, QtWidgets.QSizePolicy.Policy.Fixed)
    lay = QtWidgets.QHBoxLayout(pane)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(child, 1 if stretch else 0)
    return pane
