"""Layout chip cycle order (Standard → Field → Modern → …)."""
from __future__ import annotations

LAYOUT_CYCLE_ORDER: tuple[str, ...] = ("standard", "field", "modern")

_LAYOUT_LABELS: dict[str, str] = {
    "standard": "Standard",
    "field": "Field",
    "modern": "Modern",
}


def next_layout_id(current: str) -> str:
    """Return the next workspace id after ``current`` in the cycle."""
    cur = (current or "standard").strip().lower()
    if cur not in LAYOUT_CYCLE_ORDER:
        return "standard"
    idx = LAYOUT_CYCLE_ORDER.index(cur)
    return LAYOUT_CYCLE_ORDER[(idx + 1) % len(LAYOUT_CYCLE_ORDER)]


def other_layout_ids(current: str) -> tuple[str, ...]:
    """All workspace ids except ``current`` (menu shows every layout you are not on)."""
    cur = (current or "standard").strip().lower()
    return tuple(lid for lid in LAYOUT_CYCLE_ORDER if lid != cur)


def layout_display_name(ui_id: str) -> str:
    return _LAYOUT_LABELS.get((ui_id or "").strip().lower(), ui_id.title())
