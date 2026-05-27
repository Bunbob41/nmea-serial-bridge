"""Safe monospace fonts — avoids legacy Windows OEM faces (e.g. 8514oem) that break DirectWrite."""
from __future__ import annotations

import sys

from PySide6 import QtGui

# VGA / legacy faces Qt 6 + DirectWrite often cannot load (spams qt.qpa.fonts warnings).
_UNUSABLE_FIXED_FAMILIES = frozenset(
    {
        "8514oem",
        "terminal",
        "system",
        "fixedsys",
        "modern",
        "ms sans serif",
        "ms serif",
        "small fonts",
    }
)

_WIN_MONO_FALLBACKS = ("Cascadia Mono", "Consolas", "Courier New", "Lucida Console")
_UNIX_MONO_FALLBACKS = ("Menlo", "Monaco", "DejaVu Sans Mono", "Courier New", "monospace")


def _family_available(family: str) -> bool:
    if not family:
        return False
    needle = family.strip().lower()
    if needle in _UNUSABLE_FIXED_FAMILIES:
        return False
    for name in QtGui.QFontDatabase.families():
        if name.lower() == needle:
            return True
    return False


def _pick_monospace_family() -> str:
    system = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
    if _family_available(system.family()):
        return system.family()
    candidates = _WIN_MONO_FALLBACKS if sys.platform == "win32" else _UNIX_MONO_FALLBACKS
    for name in candidates:
        if _family_available(name):
            return name
    return "monospace"


def monospace_ui_font(*, point_size: int | None = None) -> QtGui.QFont:
    """Monospace font for logs, terminal, and diagnostics (DirectWrite-safe on Windows)."""
    font = QtGui.QFont(_pick_monospace_family())
    font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    if point_size is not None:
        font.setPointSize(max(9, int(point_size)))
    else:
        system = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        pt = system.pointSize() if system.pointSize() > 0 else 10
        font.setPointSize(max(9, pt))
    return font
