"""Persisted UI theme choice."""
from __future__ import annotations

import json
from pathlib import Path

THEME_MAROON = "maroon_classic"
# Legacy id saved by older builds — mapped to THEME_MAROON on load.
_THEME_LEGACY_MAROON_HC = "maroon_high_contrast"

THEME_OCEAN = "ocean_survey"
THEME_SLATE = "field_slate"
THEME_FOREST = "forest_night"
THEME_SUNSET = "sunset_copper"

THEME_DEFAULT = THEME_MAROON
THEME_IDS: tuple[str, ...] = (
    THEME_MAROON,
    THEME_OCEAN,
    THEME_SLATE,
    THEME_FOREST,
    THEME_SUNSET,
)

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_theme.json"


def _normalize_theme_id(theme: str) -> str:
    if theme == _THEME_LEGACY_MAROON_HC:
        return THEME_MAROON
    if theme in THEME_IDS:
        return theme
    return THEME_DEFAULT


def load_theme_choice() -> str:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return _normalize_theme_id(str(data.get("theme", THEME_DEFAULT)))
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return THEME_DEFAULT


def save_theme_choice(theme: str) -> None:
    theme = _normalize_theme_id(theme)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"theme": theme}, indent=2), encoding="utf-8")
