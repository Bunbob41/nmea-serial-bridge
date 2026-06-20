"""Application fonts — bundled Maple Mono with safe fallbacks."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PySide6 import QtGui

PRIMARY_FONT_FAMILY = "Maple Mono"
FONT_FAMILY_QSS = (
    '"Maple Mono", "Cascadia Mono", Consolas, "Courier New", monospace'
)

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

_WIN_MONO_FALLBACKS = (PRIMARY_FONT_FAMILY, "Cascadia Mono", "Consolas", "Courier New", "Lucida Console")
_UNIX_MONO_FALLBACKS = (PRIMARY_FONT_FAMILY, "Menlo", "Monaco", "DejaVu Sans Mono", "Courier New", "monospace")

# Qt 6 no longer ships fonts inside PySide6 — point QPA at our bundle before QApplication.
_QT_BASELINE_SEED: tuple[tuple[str, str], ...] = (
    ("DejaVuSans.ttf", "DejaVuSans.ttf"),
    ("DejaVuSansMono.ttf", "DejaVuSansMono.ttf"),
    ("SegoeUI.ttf", "segoeui.ttf"),
    ("Consolas.ttf", "consola.ttf"),
)

_BUNDLED_LOADED = False
_QT_FONT_ENV_CONFIGURED = False


def _fonts_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "assets" / "fonts"
        return Path(sys.executable).resolve().parent / "assets" / "fonts"
    return Path(__file__).resolve().parents[1] / "assets" / "fonts"


def _windows_fonts_dir() -> Path | None:
    if sys.platform != "win32":
        return None
    windir = os.environ.get("WINDIR", "C:/Windows")
    candidate = Path(windir) / "Fonts"
    return candidate if candidate.is_dir() else None


def _seed_qt_baseline_fonts(fonts_dir: Path) -> None:
    """Ensure Qt has at least one sans + mono TTF (Qt 6 dropped bundled fonts)."""
    fonts_dir.mkdir(parents=True, exist_ok=True)
    have_sans = any(fonts_dir.glob("DejaVuSans.ttf")) or any(fonts_dir.glob("SegoeUI.ttf"))
    have_mono = any(fonts_dir.glob("DejaVuSansMono.ttf")) or any(
        fonts_dir.glob("MapleMono-*.ttf")
    ) or any(fonts_dir.glob("Consolas.ttf"))
    if have_sans and have_mono:
        return

    win_fonts = _windows_fonts_dir()
    for dest_name, src_name in _QT_BASELINE_SEED:
        dest = fonts_dir / dest_name
        if dest.is_file():
            continue
        if win_fonts is not None:
            src = win_fonts / src_name
            if src.is_file():
                try:
                    shutil.copy2(src, dest)
                except OSError:
                    pass


def configure_qt_font_environment() -> Path:
    """Set QT_QPA_FONTDIR before QGuiApplication — silences missing PySide6/lib/fonts."""
    global _QT_FONT_ENV_CONFIGURED
    fonts_dir = _fonts_dir()
    _seed_qt_baseline_fonts(fonts_dir)
    resolved = str(fonts_dir.resolve())
    os.environ.setdefault("QT_QPA_FONTDIR", resolved)
    _QT_FONT_ENV_CONFIGURED = True
    return fonts_dir


def ensure_bundled_fonts() -> None:
    """Load Maple Mono from assets/fonts (dev + frozen bundle). Idempotent."""
    global _BUNDLED_LOADED
    if _BUNDLED_LOADED:
        return
    if not _QT_FONT_ENV_CONFIGURED:
        configure_qt_font_environment()
    fonts_dir = _fonts_dir()
    if fonts_dir.is_dir():
        for path in sorted(fonts_dir.glob("*.ttf")):
            QtGui.QFontDatabase.addApplicationFont(str(path))
    _BUNDLED_LOADED = True


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


def _pick_ui_family() -> str:
    if _family_available(PRIMARY_FONT_FAMILY):
        return PRIMARY_FONT_FAMILY
    candidates = _WIN_MONO_FALLBACKS if sys.platform == "win32" else _UNIX_MONO_FALLBACKS
    for name in candidates:
        if _family_available(name):
            return name
    return "monospace"


def _default_point_size() -> int:
    system = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.GeneralFont)
    pt = system.pointSize() if system.pointSize() > 0 else 10
    return max(9, pt)


def app_ui_font(*, point_size: int | None = None) -> QtGui.QFont:
    """Default UI font for the whole application."""
    ensure_bundled_fonts()
    font = QtGui.QFont(_pick_ui_family())
    font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    font.setPointSize(max(9, int(point_size)) if point_size is not None else _default_point_size())
    return font


def monospace_ui_font(*, point_size: int | None = None) -> QtGui.QFont:
    """Monospace font for logs, terminal, and diagnostics."""
    return app_ui_font(point_size=point_size)
