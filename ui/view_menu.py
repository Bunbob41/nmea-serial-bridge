"""View / layout dropdown helpers - section headers and shortcut-aligned rows."""
from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets


def add_view_menu_section_header(menu: QtWidgets.QMenu, text: str) -> None:
    action = QtWidgets.QWidgetAction(menu)
    lbl = QtWidgets.QLabel(str(text).strip().upper())
    lbl.setObjectName("viewMenuSectionHeader")
    lbl.setEnabled(False)
    lbl.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    row = QtWidgets.QWidget()
    row.setObjectName("viewMenuSectionHeaderRow")
    lay = QtWidgets.QHBoxLayout(row)
    lay.setContentsMargins(12, 6, 12, 4)
    lay.setSpacing(0)
    lay.addWidget(lbl)
    action.setDefaultWidget(row)
    menu.addAction(action)


def add_view_menu_action(
    menu: QtWidgets.QMenu,
    text: str,
    callback: Callable[[], None],
    *,
    shortcut: QtGui.QKeySequence | None = None,
    status_tip: str = "",
    parent: QtWidgets.QWidget | None = None,
) -> QtGui.QAction:
    host = parent or menu.parentWidget()
    if shortcut is not None and not shortcut.isEmpty():
        action = QtWidgets.QWidgetAction(menu)
        row = QtWidgets.QWidget()
        row.setObjectName("viewMenuActionRow")
        lay = QtWidgets.QHBoxLayout(row)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)
        label = QtWidgets.QLabel(text)
        label.setObjectName("viewMenuActionLabel")
        shortcut_lbl = QtWidgets.QLabel(
            shortcut.toString(QtGui.QKeySequence.SequenceFormat.NativeText)
        )
        shortcut_lbl.setObjectName("viewMenuShortcutLabel")
        shortcut_lbl.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(label, 1)
        lay.addWidget(shortcut_lbl, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        action.setDefaultWidget(row)

        def _trigger() -> None:
            callback()
            menu.close()

        def _mouse_release(event: QtGui.QMouseEvent, fn: Callable[[], None] = _trigger) -> None:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                fn()
                event.accept()

        row.mouseReleaseEvent = _mouse_release  # type: ignore[method-assign]
        menu.addAction(action)
        if host is not None:
            key_action = QtGui.QAction(host)
            key_action.setShortcut(shortcut)
            key_action.triggered.connect(callback)
            if status_tip:
                key_action.setStatusTip(status_tip)
            host.addAction(key_action)
        return action

    act = QtGui.QAction(text, host)
    if status_tip:
        act.setStatusTip(status_tip)
    act.triggered.connect(callback)
    menu.addAction(act)
    return act
