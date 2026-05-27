"""Persisted UI theme choice and random palette snapshots."""
from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any

THEME_MAROON = "maroon_classic"
# Legacy id saved by older builds — mapped to THEME_MAROON on load.
_THEME_LEGACY_MAROON_HC = "maroon_high_contrast"

THEME_OCEAN = "ocean_survey"
THEME_SLATE = "field_slate"
THEME_FOREST = "forest_night"
THEME_SUNSET = "sunset_copper"
THEME_MIDNIGHT = "midnight_teal"
THEME_RANDOM_CURRENT = "random_current"
THEME_RANDOM_FAVORITE = "random_favorite"

# Neutral slate default — easier for long sessions than gold-on-cream maroon.
THEME_DEFAULT = THEME_SLATE
THEME_IDS: tuple[str, ...] = (
    THEME_MAROON,
    THEME_OCEAN,
    THEME_SLATE,
    THEME_FOREST,
    THEME_SUNSET,
    THEME_MIDNIGHT,
    THEME_RANDOM_CURRENT,
    THEME_RANDOM_FAVORITE,
)

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_theme.json"
_CURRENT_RANDOM_KEY = "random_theme_current"
_FAVORITE_RANDOM_KEY = "random_theme_favorite"
_CURRENT_ZONES_KEY = "random_theme_zones_current"
_FAVORITE_ZONES_KEY = "random_theme_zones_favorite"
_RANDOM_LOCK_KEY = "random_seed_lock"
_RANDOM_SEED_KEY = "random_seed_family"
_RANDOM_STEP_KEY = "random_seed_step"
_THEME_PRESETS_KEY = "theme_presets"
_THEME_PRESET_ORDER_KEY = "theme_preset_order"
_THEME_ZONE_ORDER_KEY = "theme_zone_order"
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
THEME_ZONE_KEYS: tuple[str, ...] = (
    "background",
    "topbar",
    "tabs",
    "buttons",
    "inputs",
    "logs",
    "accent",
)


def _read_json() -> dict[str, Any]:
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _write_json(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _normalize_color_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for old, new in raw.items():
        old_s = str(old).strip().lower()
        new_s = str(new).strip().lower()
        if _HEX_COLOR_RE.match(old_s) and _HEX_COLOR_RE.match(new_s):
            out[old_s] = new_s
    return out


def _normalize_theme_id(theme: str) -> str:
    if theme == _THEME_LEGACY_MAROON_HC:
        return THEME_MAROON
    if theme == "arctic_day":
        return THEME_SLATE
    if theme in THEME_IDS:
        return theme
    return THEME_DEFAULT


def _normalize_zone_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in THEME_ZONE_KEYS:
        value = str(raw.get(key, "")).strip().lower()
        if _HEX_COLOR_RE.match(value):
            out[key] = value
    return out


def load_theme_zone_order() -> list[str]:
    data = _read_json()
    raw = data.get(_THEME_ZONE_ORDER_KEY)
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(raw, list):
        for name in raw:
            clean = str(name).strip()
            if clean in THEME_ZONE_KEYS and clean not in seen:
                out.append(clean)
                seen.add(clean)
    for key in THEME_ZONE_KEYS:
        if key not in seen:
            out.append(key)
    return out


def save_theme_zone_order(order: list[str]) -> bool:
    clean = [str(x).strip() for x in order if str(x).strip() in THEME_ZONE_KEYS]
    out: list[str] = []
    seen: set[str] = set()
    for key in clean:
        if key not in seen:
            out.append(key)
            seen.add(key)
    for key in THEME_ZONE_KEYS:
        if key not in seen:
            out.append(key)
    data = _read_json()
    data[_THEME_ZONE_ORDER_KEY] = out
    _write_json(data)
    return True


def load_theme_choice() -> str:
    data = _read_json()
    return _normalize_theme_id(str(data.get("theme", THEME_DEFAULT)))


def save_theme_choice(theme: str) -> None:
    theme = _normalize_theme_id(theme)
    data = _read_json()
    data["theme"] = theme
    _write_json(data)


def load_random_theme_current() -> dict[str, str]:
    return _normalize_color_map(_read_json().get(_CURRENT_RANDOM_KEY))


def save_random_theme_current(color_map: dict[str, str]) -> None:
    clean = _normalize_color_map(color_map)
    if not clean:
        return
    data = _read_json()
    data[_CURRENT_RANDOM_KEY] = clean
    _write_json(data)


def load_random_theme_favorite() -> dict[str, str]:
    return _normalize_color_map(_read_json().get(_FAVORITE_RANDOM_KEY))


def save_random_theme_favorite(color_map: dict[str, str]) -> None:
    clean = _normalize_color_map(color_map)
    if not clean:
        return
    data = _read_json()
    data[_FAVORITE_RANDOM_KEY] = clean
    _write_json(data)


def load_random_theme_current_zones() -> dict[str, str]:
    return _normalize_zone_map(_read_json().get(_CURRENT_ZONES_KEY))


def save_random_theme_current_zones(zone_map: dict[str, str]) -> None:
    clean = _normalize_zone_map(zone_map)
    if not clean:
        return
    data = _read_json()
    data[_CURRENT_ZONES_KEY] = clean
    _write_json(data)


def load_random_theme_favorite_zones() -> dict[str, str]:
    return _normalize_zone_map(_read_json().get(_FAVORITE_ZONES_KEY))


def save_random_theme_favorite_zones(zone_map: dict[str, str]) -> None:
    clean = _normalize_zone_map(zone_map)
    if not clean:
        return
    data = _read_json()
    data[_FAVORITE_ZONES_KEY] = clean
    _write_json(data)


def save_random_current_as_favorite() -> bool:
    current = load_random_theme_current()
    if not current:
        return False
    data = _read_json()
    data[_FAVORITE_RANDOM_KEY] = current
    zones = _normalize_zone_map(data.get(_CURRENT_ZONES_KEY))
    if zones:
        data[_FAVORITE_ZONES_KEY] = zones
    _write_json(data)
    return True


def load_random_seed_lock() -> bool:
    return bool(_read_json().get(_RANDOM_LOCK_KEY, False))


def save_random_seed_lock(enabled: bool) -> None:
    data = _read_json()
    data[_RANDOM_LOCK_KEY] = bool(enabled)
    _write_json(data)


def next_locked_random_variant() -> tuple[int, int]:
    """Return stable family seed + next deterministic variant index."""
    data = _read_json()
    raw_family = int(data.get(_RANDOM_SEED_KEY, 0) or 0)
    family = raw_family if raw_family > 0 else int(secrets.randbits(31) or 1)
    step = max(0, int(data.get(_RANDOM_STEP_KEY, 0) or 0))
    data[_RANDOM_SEED_KEY] = family
    data[_RANDOM_STEP_KEY] = step + 1
    _write_json(data)
    return family, step


def _normalize_theme_preset(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    zones = _normalize_zone_map(raw.get("zones"))
    if not zones:
        return None
    return {
        "theme": _normalize_theme_id(str(raw.get("theme", THEME_RANDOM_CURRENT))),
        "seed_lock": bool(raw.get("seed_lock", False)),
        "zones": zones,
    }


def load_theme_presets() -> dict[str, dict[str, Any]]:
    raw = _read_json().get(_THEME_PRESETS_KEY)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for name, entry in raw.items():
        clean_name = str(name).strip()
        if not clean_name:
            continue
        clean_entry = _normalize_theme_preset(entry)
        if clean_entry:
            out[clean_name] = clean_entry
    return out


def _theme_preset_order(data: dict[str, Any], presets: dict[str, dict[str, Any]]) -> list[str]:
    raw_order = data.get(_THEME_PRESET_ORDER_KEY)
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(raw_order, list):
        for name in raw_order:
            clean = str(name).strip()
            if clean and clean in presets and clean not in seen:
                out.append(clean)
                seen.add(clean)
    for name in presets.keys():
        if name not in seen:
            out.append(name)
    return out


def list_theme_preset_names() -> list[str]:
    data = _read_json()
    presets = load_theme_presets()
    return _theme_preset_order(data, presets)


def save_theme_preset(name: str, preset: dict[str, Any]) -> bool:
    clean_name = str(name).strip()
    if not clean_name:
        return False
    clean_entry = _normalize_theme_preset(preset)
    if not clean_entry:
        return False
    data = _read_json()
    presets = load_theme_presets()
    is_new = clean_name not in presets
    presets[clean_name] = clean_entry
    order = _theme_preset_order(data, presets)
    if is_new and clean_name not in order:
        order.append(clean_name)
    data[_THEME_PRESETS_KEY] = presets
    data[_THEME_PRESET_ORDER_KEY] = order
    _write_json(data)
    return True


def load_theme_preset(name: str) -> dict[str, Any] | None:
    presets = load_theme_presets()
    entry = presets.get(str(name).strip())
    return dict(entry) if isinstance(entry, dict) else None


def delete_theme_preset(name: str) -> bool:
    clean_name = str(name).strip()
    if not clean_name:
        return False
    data = _read_json()
    presets = load_theme_presets()
    if clean_name not in presets:
        return False
    del presets[clean_name]
    order = [n for n in _theme_preset_order(data, presets) if n != clean_name]
    data[_THEME_PRESETS_KEY] = presets
    data[_THEME_PRESET_ORDER_KEY] = order
    _write_json(data)
    return True


def reorder_theme_presets(ordered_names: list[str]) -> bool:
    data = _read_json()
    presets = load_theme_presets()
    if not presets:
        return False
    clean = [str(n).strip() for n in ordered_names if str(n).strip()]
    seen: set[str] = set()
    order: list[str] = []
    for name in clean:
        if name in presets and name not in seen:
            order.append(name)
            seen.add(name)
    for name in _theme_preset_order(data, presets):
        if name not in seen:
            order.append(name)
    data[_THEME_PRESETS_KEY] = presets
    data[_THEME_PRESET_ORDER_KEY] = order
    _write_json(data)
    return True


def build_theme_pack(
    theme: str,
    zones: dict[str, str],
    *,
    seed_lock: bool,
    favorite_zones: dict[str, str] | None = None,
) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "format": "udp-com-bridge-theme-pack/v1",
        "theme": _normalize_theme_id(str(theme)),
        "seed_lock": bool(seed_lock),
        "zones": _normalize_zone_map(zones),
    }
    fav = _normalize_zone_map(favorite_zones or {})
    if fav:
        pack["favorite_zones"] = fav
    return pack


def normalize_theme_pack(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    zones = _normalize_zone_map(raw.get("zones"))
    if not zones:
        return None
    out: dict[str, Any] = {
        "theme": _normalize_theme_id(str(raw.get("theme", THEME_RANDOM_CURRENT))),
        "seed_lock": bool(raw.get("seed_lock", False)),
        "zones": zones,
    }
    fav = _normalize_zone_map(raw.get("favorite_zones"))
    if fav:
        out["favorite_zones"] = fav
    return out
