"""Right-click quick picker for built-in palettes and saved theme presets."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6 import QtGui, QtWidgets

from ui.styles import THEME_LABELS
from ui.theme_choice import (
    THEME_FOREST,
    THEME_MAROON,
    THEME_MIDNIGHT,
    THEME_OCEAN,
    THEME_SLATE,
    THEME_SUNSET,
    list_theme_preset_names,
)

BUILTIN_THEME_QUICK_PICK_IDS: tuple[str, ...] = (
    THEME_MAROON,
    THEME_OCEAN,
    THEME_SLATE,
    THEME_FOREST,
    THEME_SUNSET,
    THEME_MIDNIGHT,
)


class ThemeQuickPickHost(Protocol):
    _theme_id: str

    def _apply_theme(self, theme_id: str, *, persist: bool = True) -> None: ...

    def _apply_theme_preset_by_name(self, name: str) -> None: ...

    def _open_modern_section_by_sid(self, sid: str) -> None: ...


def populate_theme_quick_pick_menu(
    menu: QtWidgets.QMenu, host: ThemeQuickPickHost
) -> None:
    """Fill menu with built-in palettes, saved presets, and Theme studio link."""
    builtin_menu = menu.addMenu("Built-in palettes")
    builtin_group = QtGui.QActionGroup(builtin_menu)
    builtin_group.setExclusive(True)
    active = str(getattr(host, "_theme_id", "") or "")
    for theme_id in BUILTIN_THEME_QUICK_PICK_IDS:
        label = THEME_LABELS.get(theme_id, theme_id)
        act = builtin_menu.addAction(label)
        act.setCheckable(True)
        act.setChecked(active == theme_id)
        act.triggered.connect(
            lambda _checked=False, tid=theme_id: host._apply_theme(tid)
        )
        builtin_group.addAction(act)

    saved = list_theme_preset_names()
    if saved:
        menu.addSeparator()
        preset_menu = menu.addMenu("Saved presets")
        for name in saved:
            act = preset_menu.addAction(name)
            act.triggered.connect(
                lambda _checked=False, preset=name: host._apply_theme_preset_by_name(
                    preset
                )
            )

    menu.addSeparator()
    studio = menu.addAction("Open Theme studio…")
    studio.triggered.connect(lambda: host._open_modern_section_by_sid("theme"))
