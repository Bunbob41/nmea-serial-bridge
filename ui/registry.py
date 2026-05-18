"""Registered UI variants."""
from __future__ import annotations

from typing import Dict, Type

from PySide6 import QtWidgets

from version import __version__

UI_STANDARD = "standard"
UI_FIELD = "field"
UI_MINIMAL = "minimal"
UI_LOGFIRST = "logfirst"
UI_DEFAULT = UI_STANDARD

# Launcher / picker choices (merged minimal + log-first → field)
UI_LABELS: Dict[str, str] = {
    UI_STANDARD: f"Standard — full Connect tab (v{__version__})",
    UI_FIELD: f"Field — survey log + quick bar (v{__version__})",
}

UI_DESCRIPTIONS: Dict[str, str] = {
    UI_STANDARD: (
        "First-time setup: Connect tab (COM, UDP, advanced TCP), Presets, NMEA, Send, "
        "Diagnostics, and a side log panel."
    ),
    UI_FIELD: (
        "Day-to-day survey: large live log, Start/Stop strip, COM/UDP row, Tools drawer "
        "(Presets / NMEA / Send / Diagnostics), and survey bar (Presets, Recent, Checklists, HUD). "
        "Replaces the old Minimal and Log-first layouts."
    ),
}

UI_ORDER = [UI_STANDARD, UI_FIELD]

# Legacy ids still launch for saved configs / CLI; map to field on next save
UI_LEGACY_ALIASES: Dict[str, str] = {
    UI_MINIMAL: UI_FIELD,
    UI_LOGFIRST: UI_FIELD,
}

UI_ALL_IDS = frozenset({UI_STANDARD, UI_FIELD, UI_MINIMAL, UI_LOGFIRST})


def normalize_ui_id(ui_id: str) -> str:
    return UI_LEGACY_ALIASES.get(ui_id, ui_id)


def get_window_class(ui_id: str) -> Type[QtWidgets.QWidget]:
    ui_id = normalize_ui_id(ui_id)
    if ui_id == UI_FIELD:
        from ui.field import BridgeWindowField

        return BridgeWindowField
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
