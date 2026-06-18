"""Horizontal tools chip rail for Modern UI (top navigation mode)."""
from __future__ import annotations

from collections.abc import Callable

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


def make_chip_dropdown_button(
    *,
    tier_key: str,
    label: str,
    icon: str,
    children: list[tuple[str, str, str, int]],
    on_pick: Callable[[str], None],
    on_cycle: Callable[[str, list[str]], None],
    utility_actions: list[tuple[str, str, Callable[[], None]]] | None = None,
) -> QtWidgets.QToolButton:
    """Dropdown chip for grouped nav tiers (Logging, Bench Tools)."""
    btn = QtWidgets.QToolButton()
    btn.setObjectName("modernToolsNavChipMenu")
    text = f"{icon}  {label}".strip() if icon else label
    btn.setText(text)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
    btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    btn.setAutoRaise(False)
    btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(32)
    btn.setProperty("navTierKey", tier_key)
    btn.setProperty("navActive", False)
    btn.setProperty("navDefaultText", text)
    child_sids = [sid for sid, _lbl, _icon, _idx in children]
    btn.setProperty("navChildSids", child_sids)
    btn.setProperty("navActiveChildSid", "")

    menu = QtWidgets.QMenu(btn)
    menu.setObjectName("modernToolsNavChipMenuPopup")
    for sid, child_label, child_icon, _idx in children:
        action = menu.addAction(f"{child_icon}  {child_label}".strip())
        action.triggered.connect(lambda _checked=False, s=sid: on_pick(s))
    if utility_actions:
        menu.addSeparator()
        for util_label, util_icon, util_cb in utility_actions:
            util_action = menu.addAction(f"{util_icon}  {util_label}".strip())
            util_action.triggered.connect(util_cb)
    btn.setMenu(menu)
    btn.clicked.connect(
        lambda _checked=False, sids=list(child_sids): on_cycle(tier_key, sids)
    )
    tip_lines = [f"{child_icon}  {child_label}" for _sid, child_label, child_icon, _idx in children]
    btn.setToolTip(
        f"{label} — click to cycle, arrow for menu — " + " · ".join(tip_lines)
    )
    return btn
