"""Modern header bar preferences: auto-arrange, chip icon mode, custom icons."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ui.tool_tabs import build_modern_tools_all_pages, build_modern_tools_nav_tiers

CHIP_ICON_SCHEMA_VERSION = 1
CHIP_ICON_MAX_CHARS = 4
_CHIP_ICON_RE = re.compile(r"^.{1,4}$", re.UNICODE)

# Section ids + dropdown tier keys operators may override.
KNOWN_CHIP_ICON_KEYS: frozenset[str] = frozenset(
    {sid for sid, _lbl, _icon in build_modern_tools_all_pages()}
    | {tier_key for tier_key, _lbl, _icon, _kids in build_modern_tools_nav_tiers()[1]}
)


def default_chip_icons_by_sid() -> dict[str, str]:
    out: dict[str, str] = {sid: icon for sid, _lbl, icon in build_modern_tools_all_pages()}
    for tier_key, _lbl, icon, _kids in build_modern_tools_nav_tiers()[1]:
        out[tier_key] = icon
    return out


def normalize_header_chips_icon_mode(raw: str | None) -> str:
    mode = str(raw or "auto").strip().lower()
    if mode in ("auto", "icons", "labels"):
        return mode
    return "auto"


def parse_chip_icons_import(text: str) -> dict[str, str]:
    """Validate JSON import; returns sid/tier_key -> icon glyph."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Root must be a JSON object.")
    if "schema_version" in data and int(data.get("schema_version", 0)) != CHIP_ICON_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {CHIP_ICON_SCHEMA_VERSION}.")
    icons_raw = data.get("icons", data)
    if not isinstance(icons_raw, dict):
        raise ValueError('Missing "icons" object (or use flat { "control": "🎛", ... }).')
    out: dict[str, str] = {}
    for key, value in icons_raw.items():
        sid = str(key).strip().lower().replace(" ", "_").replace("-", "_")
        if sid not in KNOWN_CHIP_ICON_KEYS:
            raise ValueError(f"Unknown section id '{key}'. See docs/HEADER_CHIP_ICONS.md.")
        glyph = str(value).strip()
        if not _CHIP_ICON_RE.match(glyph):
            raise ValueError(
                f"Icon for '{key}' must be 1–{CHIP_ICON_MAX_CHARS} visible characters (emoji or text)."
            )
        out[sid] = glyph
    if not out:
        raise ValueError("No icons defined.")
    return out


def merge_chip_icon(sid: str, default_icon: str, overrides: dict[str, str] | None) -> str:
    key = sid.strip().lower()
    if overrides and key in overrides:
        return overrides[key]
    return default_icon


def export_chip_icons_json(overrides: dict[str, str]) -> str:
    payload = {"schema_version": CHIP_ICON_SCHEMA_VERSION, "icons": dict(sorted(overrides.items()))}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def example_chip_icons_json() -> str:
    defaults = default_chip_icons_by_sid()
    sample = {
        k: defaults[k]
        for k in ("control", "activity", "hub", "fleet", "logging", "bench_tools")
        if k in defaults
    }
    return export_chip_icons_json(sample)
