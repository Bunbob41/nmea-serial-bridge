"""Qt standard-icon tool buttons (crisp on Windows Fusion, no emoji glyphs)."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets


def icon_tool_button(
    style: QtWidgets.QStyle,
    pixmap: QtWidgets.QStyle.StandardPixmap,
    tooltip: str,
    *,
    object_name: str = "wireIconBtn",
    checkable: bool = False,
    size: int = 28,
    icon_px: int = 16,
    text_fallback: str = "",
) -> QtWidgets.QToolButton:
    btn = QtWidgets.QToolButton()
    btn.setObjectName(object_name)
    btn.setToolTip(tooltip)
    btn.setAutoRaise(False)
    btn.setFixedSize(size, size)
    icon = style.standardIcon(pixmap)
    if icon.isNull() and text_fallback:
        btn.setText(text_fallback)
        btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
    else:
        btn.setIconSize(QtCore.QSize(icon_px, icon_px))
        btn.setIcon(icon)
        btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
    if checkable:
        btn.setCheckable(True)
    return btn
