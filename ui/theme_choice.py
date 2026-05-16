"""Persisted UI theme choice."""
from __future__ import annotations

import json
from pathlib import Path

THEME_MAROON_CLASSIC = "maroon_classic"
THEME_MAROON_HC = "maroon_high_contrast"
THEME_DEFAULT = THEME_MAROON_CLASSIC
THEME_IDS = (THEME_MAROON_CLASSIC, THEME_MAROON_HC)

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_theme.json"


def load_theme_choice() -> str:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        theme = str(data.get("theme", THEME_DEFAULT))
        if theme in THEME_IDS:
            return theme
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return THEME_DEFAULT


def save_theme_choice(theme: str) -> None:
    if theme not in THEME_IDS:
        theme = THEME_DEFAULT
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"theme": theme}, indent=2), encoding="utf-8")
