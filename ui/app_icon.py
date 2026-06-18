"""Application icon (repo assets + frozen bundle)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

_ICON: Optional[QtGui.QIcon] = None


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "assets"
        return Path(sys.executable).resolve().parent / "assets"
    return Path(__file__).resolve().parents[1] / "assets"


def _icon_from_png(path: Path) -> QtGui.QIcon:
    icon = QtGui.QIcon()
    for dim in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addFile(str(path), QtCore.QSize(dim, dim), QtGui.QIcon.Mode.Normal)
    return icon


def app_icon() -> QtGui.QIcon:
    global _ICON
    if _ICON is not None and not _ICON.isNull():
        return _ICON
    base = _assets_dir()
    # Title bar / tray: dark squircle matches the Modern chrome (not white-matte source art).
    for name in ("app-icon.png", "app-icon.ico"):
        path = base / name
        if path.is_file():
            icon = _icon_from_png(path)
            if not icon.isNull():
                _ICON = icon
                return icon
    path = base / "app-icon.ico"
    if path.is_file():
        icon = QtGui.QIcon(str(path))
        if not icon.isNull():
            _ICON = icon
            return icon
    _ICON = QtGui.QIcon()
    return _ICON


def apply_app_icon(target: QtWidgets.QWidget | QtWidgets.QApplication) -> None:
    icon = app_icon()
    if not icon.isNull():
        target.setWindowIcon(icon)
