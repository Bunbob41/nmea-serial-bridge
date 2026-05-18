"""Application icon (repo assets + frozen bundle)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtGui, QtWidgets

_ICON: Optional[QtGui.QIcon] = None


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "assets"
        return Path(sys.executable).resolve().parent / "assets"
    return Path(__file__).resolve().parents[1] / "assets"


def app_icon() -> QtGui.QIcon:
    global _ICON
    if _ICON is not None and not _ICON.isNull():
        return _ICON
    base = _assets_dir()
    for name in ("app-icon.ico", "app-icon.png"):
        path = base / name
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
