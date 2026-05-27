"""Connect tab disclosure row appearance (pill / seamless / outline / accent)."""
from __future__ import annotations

from PySide6 import QtWidgets

CONNECT_ROW_PILL = "pill"
CONNECT_ROW_SEAMLESS = "seamless"
CONNECT_ROW_OUTLINE = "outline"
CONNECT_ROW_ACCENT = "accent"

CONNECT_ROW_STYLES: tuple[str, ...] = (
    CONNECT_ROW_PILL,
    CONNECT_ROW_SEAMLESS,
    CONNECT_ROW_OUTLINE,
    CONNECT_ROW_ACCENT,
)

CONNECT_ROW_LABELS: dict[str, str] = {
    CONNECT_ROW_PILL: "Pill (rounded cards)",
    CONNECT_ROW_SEAMLESS: "Seamless (flat list)",
    CONNECT_ROW_OUTLINE: "Outline (light borders)",
    CONNECT_ROW_ACCENT: "Accent bar (left stripe)",
}

CONNECT_ROW_DEFAULT = CONNECT_ROW_PILL


def normalize_connect_row_style(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if key in CONNECT_ROW_STYLES:
        return key
    return CONNECT_ROW_DEFAULT


def _repolish_widget_tree(root: QtWidgets.QWidget) -> None:
    """Force stylesheet re-evaluation for dynamic connectRowStyle selectors."""
    style = root.style()
    widgets = [root, *root.findChildren(QtWidgets.QWidget)]
    for widget in widgets:
        style.unpolish(widget)
        style.polish(widget)
        widget.update()


def apply_connect_row_style(
    win: QtWidgets.QWidget,
    style_id: str | None = None,
) -> str:
    """Set connectRowStyle Qt property on the panel host; returns active style id."""
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    if host is None:
        return CONNECT_ROW_DEFAULT
    if style_id is None:
        style_id = CONNECT_ROW_DEFAULT
    style_id = normalize_connect_row_style(style_id)
    host.setProperty("connectRowStyle", style_id)
    _repolish_widget_tree(host)
    return style_id
