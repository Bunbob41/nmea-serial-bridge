"""Registered UI variants."""
from __future__ import annotations

from typing import Callable, Dict, Type

from PySide6 import QtWidgets

UI_STANDARD = "standard"
UI_MINIMAL = "minimal"
UI_LOGFIRST = "logfirst"
UI_DEFAULT = UI_STANDARD

UI_LABELS: Dict[str, str] = {
    UI_STANDARD: "Standard (v0.4 — tabs, path cards)",
    UI_MINIMAL: "Minimal (light, compact, log below)",
    UI_LOGFIRST: "Log-first (dark, log dominates)",
}

UI_ORDER = [UI_STANDARD, UI_MINIMAL, UI_LOGFIRST]


def get_window_class(ui_id: str) -> Type[QtWidgets.QWidget]:
    if ui_id == UI_MINIMAL:
        from ui.minimal import BridgeWindowMinimal

        return BridgeWindowMinimal
    if ui_id == UI_LOGFIRST:
        from ui.logfirst import BridgeWindowLogFirst

        return BridgeWindowLogFirst
    from ui.standard import BridgeWindowStandard

    return BridgeWindowStandard


def create_window(ui_id: str) -> QtWidgets.QWidget:
    cls = get_window_class(ui_id)
    return cls()
