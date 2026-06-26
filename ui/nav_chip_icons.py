"""Colored squircle tiles for Modern header nav chips (icon-only mode).

Colours apply via *direct per-button setStyleSheet()*, not QSS property selectors,
so they are immune to Qt boolean-vs-string property matching issues.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.fonts import emoji_ui_font

NAV_CHIP_TILE_SIZE = 36   # px — full-width nav strip, generous tile
_NAV_ICON_FONT_PT = 16.0  # emoji point size inside each tile

# sid -> (nav emoji, tile hex colour)
NAV_CHIP_TILES: dict[str, tuple[str, str]] = {
    "control":     ("🎛",  "#4A7FE8"),
    "activity":    ("📋",  "#5A8FAF"),
    "presets":     ("⚙",   "#E8837A"),
    "hub":         ("🛰",   "#3D5A9E"),
    "fleet":       ("🔀",  "#8B6CC1"),
    "nmea":        ("📡",  "#C75B7A"),
    "logging":     ("📋",  "#5A9BD4"),
    "bench_tools": ("🧪",  "#3D8B5A"),
    "black_box":   ("💾",  "#6B8CAE"),
    "file_log":    ("📄",  "#7A9E6B"),
    "phone":       ("📱",  "#4A7FE8"),
    "inject":      ("💉",  "#8B6CC1"),
    "terminal":    ("⌨",   "#64748B"),
    "checks":      ("🧪",  "#E8837A"),
    "theme":       ("🎨",  "#3D8B5A"),
}
_DEFAULT_TILE = ("?", "#5B8DEF")


def _hex_darken(hex_color: str, factor: float = 0.7) -> str:
    """Slightly darken a hex colour for hover/active border."""
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return hex_color
    r = max(0, int(int(c[0:2], 16) * factor))
    g = max(0, int(int(c[2:4], 16) * factor))
    b = max(0, int(int(c[4:6], 16) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _make_emoji_pixmap(text: str, *, size: int) -> QtGui.QPixmap:
    """Render an emoji/glyph centered in a transparent square pixmap."""
    px = QtGui.QPixmap(size, size)
    px.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(px)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    f = emoji_ui_font(point_size=_NAV_ICON_FONT_PT)
    p.setFont(f)
    p.setPen(QtGui.QColor("#ffffff"))
    p.drawText(
        QtCore.QRect(0, 0, size, size),
        QtCore.Qt.AlignmentFlag.AlignCenter,
        str(text or "?"),
    )
    p.end()
    return px


def apply_squircle_nav_chip(
    btn: QtWidgets.QWidget,
    *,
    sid: str,
    emoji_fallback: str = "",
    style: "QtWidgets.QStyle | None" = None,
) -> None:
    """Apply coloured squircle appearance directly to a nav chip button."""
    key = str(sid or "").strip().lower()
    nav_emoji, color = NAV_CHIP_TILES.get(key, _DEFAULT_TILE)
    glyph = str(emoji_fallback or nav_emoji or "?").strip()

    radius = max(8, NAV_CHIP_TILE_SIZE // 3)
    dark = _hex_darken(color, 0.65)

    # Build inline stylesheet — works regardless of parent QSS property selectors
    ss = f"""
        background-color: {color};
        color: #ffffff;
        border: 1px solid {color};
        border-radius: {radius}px;
        padding: 0px;
        min-width:  {NAV_CHIP_TILE_SIZE}px;
        max-width:  {NAV_CHIP_TILE_SIZE}px;
        min-height: {NAV_CHIP_TILE_SIZE}px;
        max-height: {NAV_CHIP_TILE_SIZE}px;
    """
    btn.setStyleSheet(ss)

    # Set icon from rendered emoji pixmap
    px = _make_emoji_pixmap(glyph, size=NAV_CHIP_TILE_SIZE)
    icon = QtGui.QIcon(px)
    if isinstance(btn, QtWidgets.QAbstractButton):
        btn.setIcon(icon)
        btn.setIconSize(QtCore.QSize(NAV_CHIP_TILE_SIZE, NAV_CHIP_TILE_SIZE))
        btn.setText("")
    btn.setFixedSize(NAV_CHIP_TILE_SIZE, NAV_CHIP_TILE_SIZE)
    btn.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    # Tag for hover/active CSS tweaks in the global sheet (string "true" not bool)
    btn.setProperty("navGeminiTile", "true")
    btn.setProperty("navSid", key)

    # Install an event filter for hover border highlight
    filt = _HoverBorderFilter(btn, color=color, dark=dark, radius=radius)
    btn.installEventFilter(filt)
    btn._squircle_hover_filter = filt  # keep alive


class _HoverBorderFilter(QtCore.QObject):
    """Lightweight hover/leave border swap (avoids QSS property selector issues)."""

    def __init__(self, parent: QtWidgets.QWidget, *, color: str, dark: str, radius: int) -> None:
        super().__init__(parent)
        self._color = color
        self._dark = dark
        self._radius = radius
        self._base_ss = parent.styleSheet()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if event.type() == QtCore.QEvent.Type.Enter:
            assert isinstance(obj, QtWidgets.QWidget)
            r = self._radius
            obj.setStyleSheet(
                f"""
                background-color: {self._color};
                color: #ffffff;
                border: 2px solid rgba(255,255,255,0.55);
                border-radius: {r}px;
                padding: 0px;
                min-width:  {NAV_CHIP_TILE_SIZE}px; max-width:  {NAV_CHIP_TILE_SIZE}px;
                min-height: {NAV_CHIP_TILE_SIZE}px; max-height: {NAV_CHIP_TILE_SIZE}px;
                """
            )
        elif event.type() == QtCore.QEvent.Type.Leave:
            assert isinstance(obj, QtWidgets.QWidget)
            obj.setStyleSheet(self._base_ss)
        return False


def nav_chip_squircle_stylesheet() -> str:
    """Extra global QSS — clears menu-indicator arrow for squircle dropdown chips."""
    return """
QToolButton#modernToolsNavChipMenu[navGeminiTile="true"]::menu-button {
    width: 0; border: none; padding: 0;
}
QToolButton#modernToolsNavChipMenu[navGeminiTile="true"]::menu-indicator {
    image: none; width: 0;
}
"""
