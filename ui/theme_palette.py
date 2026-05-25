"""Per-theme color remaps applied to the maroon base stylesheets."""
from __future__ import annotations

import colorsys
import random

from ui.theme_choice import (
    THEME_ARCTIC,
    THEME_FOREST,
    THEME_MAROON,
    THEME_MIDNIGHT,
    THEME_OCEAN,
    THEME_RANDOM_CURRENT,
    THEME_RANDOM_FAVORITE,
    THEME_SLATE,
    THEME_SUNSET,
    THEME_ZONE_KEYS,
    load_random_theme_current,
    load_random_theme_current_zones,
    load_random_theme_favorite,
    load_random_theme_favorite_zones,
)

# Longest keys first when applying (handled in apply_theme_colors).
_OCEAN_MAP = {
    "#2f2329": "#1a2838",
    "#241a1f": "#121c28",
    "#3a2a31": "#223044",
    "#2a1d22": "#182433",
    "#57333f": "#2a4560",
    "#7a4a58": "#3d6888",
    "#4a2f39": "#243a50",
    "#5a3543": "#2e4a62",
    "#6b3a4a": "#356080",
    "#5f3643": "#315a78",
    "#5a3240": "#2e4e68",
    "#6a3d4c": "#3a6888",
    "#4a2a36": "#243850",
    "#4c2d37": "#2a4a62",
    "#4a3a24": "#2a3e52",
    "#4a3038": "#2a4258",
    "#7a5a2d": "#2d5a7a",
    "#8d6a34": "#3a7a9e",
    "#b28a42": "#4a9cc4",
    "#d4af37": "#3db8e8",
    "#f1d483": "#8ee0ff",
    "#ffe2a1": "#b8ecff",
    "#ffe9b9": "#d0f2ff",
    "#ffe7b0": "#a8e4ff",
    "#f6eee0": "#e3f0ff",
    "#f2e7d2": "#d8e8f8",
    "#f5ead8": "#d4e6f6",
    "#eadcc8": "#c8dcef",
    "#ead9b7": "#b8d4eb",
    "#d9c5a4": "#9ec0de",
    "#f3ecdf": "#e8f2fa",
    "#f7f1e6": "#eef6fd",
    "#e7dcc9": "#d4e4f2",
    "#d9c6a1": "#b8cfe4",
    "#eadcc3": "#d0e2f0",
    "#dfcfaf": "#c0d4e8",
    "#4a202a": "#1a3048",
    "#5a2a33": "#243850",
    "#3a1f13": "#0f2438",
    "#1f1408": "#0a1828",
    "#b47a88": "#6aa8c8",
    "#c78f9b": "#7ab8d4",
    "#d08080": "#e07070",
    "#6b3643": "#2e5878",
    "#bf9928": "#2a98c8",
    "#e0be56": "#5cc8f0",
    "#e5be4f": "#4ab8e8",
}

_SLATE_MAP = {
    "#2f2329": "#252830",
    "#241a1f": "#1a1d24",
    "#3a2a31": "#2e333d",
    "#2a1d22": "#22262e",
    "#57333f": "#3a424f",
    "#7a4a58": "#525c6b",
    "#4a2f39": "#343a45",
    "#5a3543": "#404752",
    "#6b3a4a": "#4a5563",
    "#5f3643": "#454f5c",
    "#5a3240": "#3f4854",
    "#6a3d4c": "#505a68",
    "#4a2a36": "#363c46",
    "#4c2d37": "#3a424c",
    "#4a3a24": "#383e48",
    "#4a3038": "#3a4048",
    "#7a5a2d": "#4a5568",
    "#8d6a34": "#5c6a80",
    "#b28a42": "#7a8aa0",
    "#d4af37": "#8aa4c4",
    "#f1d483": "#c8d8ec",
    "#ffe2a1": "#dce6f4",
    "#ffe9b9": "#e8eef8",
    "#ffe7b0": "#d0dcf0",
    "#f6eee0": "#eceff4",
    "#f2e7d2": "#e2e6ee",
    "#f5ead8": "#e0e4ec",
    "#eadcc8": "#d4d8e0",
    "#ead9b7": "#c8ccd4",
    "#d9c5a4": "#a8b0bc",
    "#f3ecdf": "#eef0f4",
    "#f7f1e6": "#f4f6f8",
    "#e7dcc9": "#e0e4ea",
    "#d9c6a1": "#c0c8d4",
    "#eadcc3": "#d8dce4",
    "#dfcfaf": "#c8d0da",
    "#4a202a": "#2a3038",
    "#5a2a33": "#343a44",
    "#3a1f13": "#222830",
    "#1f1408": "#181c22",
    "#b47a88": "#98a8b8",
    "#c78f9b": "#a8b4c4",
    "#d08080": "#c87878",
    "#6b3643": "#4a5563",
    "#bf9928": "#6a88a8",
    "#e0be56": "#a0b8d4",
    "#e5be4f": "#90a8c8",
}

_FOREST_MAP = {
    "#2f2329": "#1c2a22",
    "#241a1f": "#121c18",
    "#3a2a31": "#243830",
    "#2a1d22": "#1a2820",
    "#57333f": "#2e4a38",
    "#7a4a58": "#3d6248",
    "#4a2f39": "#283c32",
    "#5a3543": "#324a3c",
    "#6b3a4a": "#3a6048",
    "#5f3643": "#365640",
    "#5a3240": "#324a3a",
    "#6a3d4c": "#3e5c48",
    "#4a2a36": "#283830",
    "#4c2d37": "#2e4438",
    "#4a3a24": "#2a3c30",
    "#4a3038": "#2e4038",
    "#7a5a2d": "#3d6a48",
    "#8d6a34": "#4a8058",
    "#b28a42": "#5a9a68",
    "#d4af37": "#6dbf78",
    "#f1d483": "#a8e8b0",
    "#ffe2a1": "#c8f0cc",
    "#ffe9b9": "#d8f4dc",
    "#ffe7b0": "#b0e8b8",
    "#f6eee0": "#e4f2e6",
    "#f2e7d2": "#d4e8d8",
    "#f5ead8": "#d0e8d4",
    "#eadcc8": "#c0dcc4",
    "#ead9b7": "#b0d4b4",
    "#d9c5a4": "#90c098",
    "#f3ecdf": "#e8f4ea",
    "#f7f1e6": "#f0f8f2",
    "#e7dcc9": "#d8ece0",
    "#d9c6a1": "#b8d8c0",
    "#eadcc3": "#d0e8d4",
    "#dfcfaf": "#c0dcc8",
    "#4a202a": "#1a3020",
    "#5a2a33": "#243830",
    "#3a1f13": "#102018",
    "#1f1408": "#0a1810",
    "#b47a88": "#68a878",
    "#c78f9b": "#78b888",
    "#d08080": "#d07070",
    "#6b3643": "#3a5c48",
    "#bf9928": "#48a858",
    "#e0be56": "#78d080",
    "#e5be4f": "#68c870",
}

_SUNSET_MAP = {
    "#2f2329": "#2a2228",
    "#241a1f": "#1c161a",
    "#3a2a31": "#382830",
    "#2a1d22": "#302428",
    "#57333f": "#5a3848",
    "#7a4a58": "#6a4858",
    "#4a2f39": "#483438",
    "#5a3543": "#544040",
    "#6b3a4a": "#684850",
    "#5f3643": "#5c4048",
    "#5a3240": "#543c44",
    "#6a3d4c": "#644850",
    "#4a2a36": "#443038",
    "#4c2d37": "#4c343c",
    "#4a3a24": "#4a3828",
    "#4a3038": "#4c343c",
    "#7a5a2d": "#8a5838",
    "#8d6a34": "#a06840",
    "#b28a42": "#c08050",
    "#d4af37": "#e8a050",
    "#f1d483": "#ffd8a0",
    "#ffe2a1": "#ffe0b0",
    "#ffe9b9": "#ffe8c0",
    "#ffe7b0": "#ffd090",
    "#f6eee0": "#fff0e0",
    "#f2e7d2": "#f8e4d0",
    "#f5ead8": "#f8e0c8",
    "#eadcc8": "#f0d4c0",
    "#ead9b7": "#e8c8a8",
    "#d9c5a4": "#d0a888",
    "#f3ecdf": "#faf0e8",
    "#f7f1e6": "#fff4ec",
    "#e7dcc9": "#f0e0d0",
    "#d9c6a1": "#e0c0a0",
    "#eadcc3": "#f0dcc8",
    "#dfcfaf": "#e8d0b0",
    "#4a202a": "#3a2820",
    "#5a2a33": "#443028",
    "#3a1f13": "#281810",
    "#1f1408": "#201008",
    "#b47a88": "#c89070",
    "#c78f9b": "#d8a080",
    "#d08080": "#e07070",
    "#6b3643": "#884838",
    "#bf9928": "#d08830",
    "#e0be56": "#f0b060",
    "#e5be4f": "#e8a850",
}

_MIDNIGHT_MAP = dict(_OCEAN_MAP)
_MIDNIGHT_MAP.update(
    {
        "#2f2329": "#141c24",
        "#241a1f": "#0c1218",
        "#3a2a31": "#1a2834",
        "#2a1d22": "#121a22",
        "#6f8d63": "#2a6a78",
        "#7f9a73": "#3a7a88",
    }
)

_ARCTIC_MAP = dict(_SLATE_MAP)
_ARCTIC_MAP.update(
    {
        "#2f2329": "#e8eef4",
        "#241a1f": "#dce4ec",
        "#3a2a31": "#d0dae4",
        "#2a1d22": "#e2e8f0",
        "#f6eee0": "#1a2838",
        "#f4f0ea": "#1a2838",
        "#f2e7d2": "#243448",
        "#57333f": "#b8c8d8",
        "#6b3a4a": "#c8d8e8",
    }
)

THEME_COLOR_MAPS: dict[str, dict[str, str]] = {
    THEME_OCEAN: _OCEAN_MAP,
    THEME_SLATE: _SLATE_MAP,
    THEME_FOREST: _FOREST_MAP,
    THEME_SUNSET: _SUNSET_MAP,
    THEME_MIDNIGHT: _MIDNIGHT_MAP,
    THEME_ARCTIC: _ARCTIC_MAP,
}

DEFAULT_ZONE_COLORS: dict[str, str] = {
    "background": "#1f2430",
    "topbar": "#354b6b",
    "tabs": "#5a3f8c",
    "buttons": "#c54f8b",
    "inputs": "#2f6a7a",
    "logs": "#1d1530",
    "accent": "#f6c65b",
}

_ZONE_COLOR_GROUPS: dict[str, tuple[str, ...]] = {
    "background": (
        "#2f2329",
        "#241a1f",
        "#2a1d22",
        "#e8e4de",
        "#f7f1e6",
        "#f0ece6",
    ),
    "topbar": (
        "#3a2a31",
        "#e7dcc9",
        "#ddd8d0",
    ),
    "tabs": (
        "#4a2f39",
        "#5a3543",
        "#6b3a4a",
        "#d0cbc4",
        "#d0cbc4",
    ),
    "buttons": (
        "#5a3240",
        "#6a3d4c",
        "#4a2a36",
        "#6b3643",
        "#d0cbc4",
        "#e8e0d4",
    ),
    "inputs": (
        "#1e181c",
        "#1b1418",
        "#2a1d22",
        "#f5f2ec",
        "#f7f1e6",
    ),
    "logs": (
        "#161214",
        "#1e181c",
        "#f5f2ec",
    ),
    "accent": (
        "#7a5a2d",
        "#8d6a34",
        "#b28a42",
        "#d4af37",
        "#f1d483",
        "#ffe2a1",
        "#ffe7b0",
        "#e0be56",
        "#bf9928",
    ),
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    c = color.lstrip("#")
    return int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    r = int(round(_clamp01(rgb[0]) * 255.0))
    g = int(round(_clamp01(rgb[1]) * 255.0))
    b = int(round(_clamp01(rgb[2]) * 255.0))
    return f"#{r:02x}{g:02x}{b:02x}"


def _zone_tint(source: str, target: str, *, weight: float) -> str:
    sr, sg, sb = _hex_to_rgb(source)
    tr, tg, tb = _hex_to_rgb(target)
    sh, sl, ss = colorsys.rgb_to_hls(sr, sg, sb)
    th, tl, ts = colorsys.rgb_to_hls(tr, tg, tb)
    # Keep source contrast envelope, but strongly adopt the target zone hue.
    h = th
    s = _clamp01((ss * (1.0 - weight)) + (ts * weight))
    l = _clamp01((sl * 0.62) + (tl * 0.38))
    return _rgb_to_hex(colorsys.hls_to_rgb(h, l, s))


def build_zone_theme_map(zone_colors: dict[str, str]) -> dict[str, str]:
    zones = dict(DEFAULT_ZONE_COLORS)
    for key in THEME_ZONE_KEYS:
        value = str(zone_colors.get(key, "")).strip().lower()
        if len(value) == 7 and value.startswith("#"):
            zones[key] = value
    out: dict[str, str] = {}
    for zone, sources in _ZONE_COLOR_GROUPS.items():
        weight_map = {
            "background": 0.70,
            "topbar": 0.84,
            "tabs": 0.92,
            "buttons": 0.95,
            "inputs": 0.82,
            "logs": 0.86,
            "accent": 0.98,
        }
        weight = weight_map.get(zone, 0.85)
        for src in sources:
            out[src.lower()] = _zone_tint(src, zones[zone], weight=weight)
    return out


def generate_random_zone_colors(
    seed: int | None = None, *, family_seed: int | None = None, variant: int = 0
) -> dict[str, str]:
    if family_seed is None:
        family_seed = int(seed) if seed is not None else random.SystemRandom().randrange(1, 2**31)
        variant = 0
    family_seed = max(1, int(family_seed))
    variant = max(0, int(variant))
    rng_family = random.Random(family_seed)
    rng_variant = random.Random((family_seed ^ ((variant + 1) * 524_287)) & 0x7FFFFFFF)
    base_h = rng_family.random()
    zones: dict[str, str] = {}
    for idx, zone in enumerate(THEME_ZONE_KEYS):
        hue = (base_h + (idx / max(len(THEME_ZONE_KEYS), 1)) + rng_variant.uniform(-0.06, 0.06)) % 1.0
        sat = _clamp01(0.52 + rng_variant.uniform(0.08, 0.34))
        if zone == "accent":
            sat = _clamp01(0.70 + rng_variant.uniform(0.08, 0.20))
            light = _clamp01(0.58 + rng_variant.uniform(0.08, 0.20))
        elif zone in {"background", "logs"}:
            light = _clamp01(0.17 + rng_variant.uniform(0.02, 0.10))
        elif zone == "topbar":
            light = _clamp01(0.24 + rng_variant.uniform(0.04, 0.12))
        else:
            light = _clamp01(0.32 + rng_variant.uniform(0.06, 0.18))
        zones[zone] = _rgb_to_hex(colorsys.hls_to_rgb(hue, light, sat))
    return zones


def generate_standardized_zone_colors(
    seed: int | None = None, *, family_seed: int | None = None, variant: int = 0
) -> dict[str, str]:
    """Generate a cohesive single-family palette (low visual chaos)."""
    if family_seed is None:
        family_seed = int(seed) if seed is not None else random.SystemRandom().randrange(1, 2**31)
        variant = 0
    family_seed = max(1, int(family_seed))
    variant = max(0, int(variant))
    rng = random.Random((family_seed ^ ((variant + 1) * 786_433)) & 0x7FFFFFFF)
    hue = rng.random()
    sat = _clamp01(0.26 + rng.uniform(0.03, 0.18))
    accent_hue = (hue + rng.uniform(0.02, 0.10)) % 1.0
    zones: dict[str, str] = {}
    zone_lightness = {
        "background": 0.17,
        "topbar": 0.24,
        "tabs": 0.30,
        "buttons": 0.36,
        "inputs": 0.28,
        "logs": 0.13,
        "accent": 0.62,
    }
    for zone in THEME_ZONE_KEYS:
        light = zone_lightness.get(zone, 0.30) + rng.uniform(-0.03, 0.03)
        zone_hue = accent_hue if zone == "accent" else hue
        zone_sat = sat + (0.22 if zone == "accent" else 0.0)
        zones[zone] = _rgb_to_hex(
            colorsys.hls_to_rgb(zone_hue, _clamp01(light), _clamp01(zone_sat))
        )
    return zones


def generate_random_theme_map(
    seed: int | None = None, *, family_seed: int | None = None, variant: int = 0
) -> dict[str, str]:
    """Create a vibrant random remap while preserving relative lightness contrast.

    - `seed`: one-off deterministic map
    - `family_seed` + `variant`: same style family with deterministic variations
    """
    zones = generate_random_zone_colors(seed, family_seed=family_seed, variant=variant)
    return build_zone_theme_map(zones)


def apply_theme_colors(css: str, theme_id: str) -> str:
    if theme_id == THEME_MAROON:
        return css
    if theme_id == THEME_RANDOM_CURRENT:
        zones = load_random_theme_current_zones()
        mapping = build_zone_theme_map(zones) if zones else load_random_theme_current()
    elif theme_id == THEME_RANDOM_FAVORITE:
        zones = load_random_theme_favorite_zones()
        mapping = build_zone_theme_map(zones) if zones else load_random_theme_favorite()
    else:
        mapping = THEME_COLOR_MAPS.get(theme_id)
    if not mapping:
        return css
    out = css
    for old, new in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
        out = out.replace(old, new)
    return out
