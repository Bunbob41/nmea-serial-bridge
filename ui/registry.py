"""Registered UI variants."""
from __future__ import annotations

from typing import Dict, Type

from PySide6 import QtWidgets

from version import __version__

UI_STANDARD = "standard"  # legacy id → field (removed layout)
UI_FIELD = "field"
UI_MODERN = "modern"
UI_MINIMAL = "minimal"
UI_LOGFIRST = "logfirst"
UI_DEFAULT = UI_FIELD

UI_LABELS: Dict[str, str] = {
    UI_FIELD: f"Field — survey log + quick bar (v{__version__})",
    UI_MODERN: f"Modern — discovery dashboard (v{__version__})",
}

UI_DESCRIPTIONS: Dict[str, str] = {
    UI_FIELD: (
        "Day-to-day survey: large live log, Start/Stop strip, COM/UDP row, Tools drawer "
        "(Presets / NMEA / Send / Diagnostics / Theme), and survey bar (Presets, Recent, Checklists, HUD)."
    ),
    UI_MODERN: (
        "Focused bridge cockpit: Activity traffic view, Control setup, Hub discovery, "
        "and Tools (logging, theme, presets, checks, and more)."
    ),
}

UI_ORDER = [UI_FIELD, UI_MODERN]

UI_LEGACY_ALIASES: Dict[str, str] = {
    UI_MINIMAL: UI_FIELD,
    UI_LOGFIRST: UI_FIELD,
    UI_STANDARD: UI_FIELD,
}

UI_ALL_IDS = frozenset({UI_STANDARD, UI_FIELD, UI_MODERN, UI_MINIMAL, UI_LOGFIRST})


def normalize_ui_id(ui_id: str) -> str:
    return UI_LEGACY_ALIASES.get(ui_id, ui_id)


def get_window_class(ui_id: str) -> Type[QtWidgets.QWidget]:
    ui_id = normalize_ui_id(ui_id)
    if ui_id == UI_MODERN:
        from ui.modern import BridgeWindowModern

        return BridgeWindowModern
    if ui_id == UI_FIELD:
        from ui.field import BridgeWindowField

        return BridgeWindowField
    if ui_id == UI_MINIMAL:
        from ui.minimal import BridgeWindowMinimal

        return BridgeWindowMinimal
    if ui_id == UI_LOGFIRST:
        from ui.logfirst import BridgeWindowLogFirst

        return BridgeWindowLogFirst
    from ui.field import BridgeWindowField

    return BridgeWindowField


def create_window(ui_id: str) -> QtWidgets.QWidget:
    """Construct the main window; each class calls ``_finalize_ui()`` → launch preset restore."""
    cls = get_window_class(ui_id)
    return cls()
