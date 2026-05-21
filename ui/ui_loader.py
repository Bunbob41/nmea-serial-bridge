"""Load Qt Designer .ui layouts at runtime (dev + frozen bundle)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtUiTools, QtWidgets

_LOG = logging.getLogger(__name__)


class LayoutLoadError(Exception):
    """Raised when a .ui resource is missing or invalid."""


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "ui" / "resources"
    return Path(__file__).resolve().parent / "resources"


def load_widget(name: str, parent: Optional[QtWidgets.QWidget] = None) -> QtWidgets.QWidget:
    path = resource_dir() / f"{name}.ui"
    if not path.is_file():
        raise LayoutLoadError(f"Layout file not found: {path}")
    loader = QtUiTools.QUiLoader()
    file = QtCore.QFile(str(path))
    if not file.open(QtCore.QFile.OpenModeFlag.ReadOnly):
        raise LayoutLoadError(f"Cannot open layout file: {path}")
    try:
        widget = loader.load(file, parent)
    finally:
        file.close()
    if widget is None:
        raise LayoutLoadError(f"QUiLoader returned None for {path}")
    return widget


def _require_child(root: QtWidgets.QWidget, name: str, type_name: type) -> QtWidgets.QWidget:
    child = root.findChild(type_name, name)
    if child is None:
        raise LayoutLoadError(f"Required widget '{name}' ({type_name.__name__}) missing in {root.objectName()}")
    return child


def load_standard_connect_shell(parent: Optional[QtWidgets.QWidget] = None) -> QtWidgets.QWidget:
    root = load_widget("standard_connect_shell", parent)
    _require_child(root, "connectPanelHost", QtWidgets.QWidget)
    _require_child(root, "statusBannerHost", QtWidgets.QWidget)
    _require_child(root, "appSubtitle", QtWidgets.QLabel)
    return root


def load_field_control_strip(parent: Optional[QtWidgets.QWidget] = None) -> QtWidgets.QWidget:
    root = load_widget("field_control_strip", parent)
    _require_child(root, "fieldStripHost", QtWidgets.QWidget)
    _require_child(root, "fieldStatusHost", QtWidgets.QWidget)
    return root
