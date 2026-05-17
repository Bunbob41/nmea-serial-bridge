"""Persisted Survey HUD layout (sections, metrics, collapse)."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "survey_hud_layout.json"

LAYOUT_VERSION = 3

# Default: wide strip along the top of the main bridge window (log-first / survey HUD).
DEFAULT_WINDOW_DOCK = "top_strip"
TOP_STRIP_HEIGHT_RATIO = 0.21
TOP_STRIP_MIN_HEIGHT = 168
TOP_STRIP_MAX_HEIGHT = 235
TOP_STRIP_H_MARGIN = 6
TOP_STRIP_BELOW_TITLE_PX = 50
DEFAULT_SPLITTER_NMEA_RATIO = 0.34

# Smaller saved sizes are treated as corrupt (avoids a tiny “flash” window on open).
HUD_MIN_WINDOW_WIDTH = 420
HUD_MIN_WINDOW_HEIGHT = 168

# Legacy free-floating size (only when window_customized is true).
DEFAULT_WINDOW_WIDTH = 0
DEFAULT_WINDOW_HEIGHT = 0

SECTION_IDS = ("rates", "session", "backpressure")

SECTION_LABELS = {
    "rates": "Sentence rates",
    "session": "Session & transport",
    "backpressure": "Backpressure",
}

METRIC_IDS = (
    "hz_dn",
    "hz_up",
    "hz_inj",
    "sess_dn",
    "sess_up",
    "health",
    "gnss_q",
    "gnss_sats",
    "gnss_hdop",
    "dr_ns",
    "dr_sn",
    "rj_ns",
    "rj_sn",
    "q_ns",
    "q_sn",
)

METRIC_LABELS = {
    "hz_dn": "Into COM (Hz)",
    "hz_up": "From COM (Hz)",
    "hz_inj": "Inject (Send tab)",
    "sess_dn": "Toward COM (total)",
    "sess_up": "Toward network (total)",
    "health": "Transport",
    "gnss_q": "GNSS quality",
    "gnss_sats": "GNSS satellites",
    "gnss_hdop": "GNSS HDOP",
    "dr_ns": "Drops network → COM",
    "dr_sn": "Drops COM → network",
    "rj_ns": "Rejected toward COM",
    "rj_sn": "Rejected from COM",
    "q_ns": "Queued toward COM",
    "q_sn": "Queued toward network",
}

METRIC_SECTION: dict[str, str] = {
    "hz_dn": "rates",
    "hz_up": "rates",
    "hz_inj": "rates",
    "sess_dn": "session",
    "sess_up": "session",
    "health": "session",
    "gnss_q": "session",
    "gnss_sats": "session",
    "gnss_hdop": "session",
    "dr_ns": "backpressure",
    "dr_sn": "backpressure",
    "rj_ns": "backpressure",
    "rj_sn": "backpressure",
    "q_ns": "backpressure",
    "q_sn": "backpressure",
}


def default_layout() -> dict[str, Any]:
    return {
        "sections": {
            sid: {"visible": True, "collapsed": sid == "backpressure"}
            for sid in SECTION_IDS
        },
        "metrics": {
            mid: True
            for mid in METRIC_IDS
            if mid not in ("gnss_hdop",)
        },
        "footer": True,
        # Section strips: drag handles swap order; persisted here.
        "section_order": list(SECTION_IDS),
        "sections_row": True,
        "pin_on_top": True,
        "box_scale": 1.0,
        "forced_columns": 6,
        "show_subtitles": False,
        "show_nmea_log": True,
        "layout_version": LAYOUT_VERSION,
        "window_dock": DEFAULT_WINDOW_DOCK,
        "window_customized": False,
        "window_width": DEFAULT_WINDOW_WIDTH,
        "window_height": DEFAULT_WINDOW_HEIGHT,
        "lock_size": False,
        "metric_style": {
            mid: {"value_on_top": False, "compact": False} for mid in METRIC_IDS
        },
    }


def normalized_section_order(raw: Any) -> list[str]:
    """Return SECTION_IDS permutation from config (stable merge if invalid)."""
    base = list(SECTION_IDS)
    if not isinstance(raw, list):
        return base
    seen: set[str] = set()
    out: list[str] = []
    for sid in raw:
        if sid in base and sid not in seen:
            out.append(sid)
            seen.add(sid)
    for sid in base:
        if sid not in seen:
            out.append(sid)
    return out


def sanitize_window_geometry(cfg: dict[str, Any]) -> dict[str, Any]:
    """Drop invalid saved window sizes so the HUD never opens as a postage stamp."""
    if not cfg.get("window_customized"):
        return cfg
    try:
        w = int(cfg.get("window_width") or 0)
        h = int(cfg.get("window_height") or 0)
    except (TypeError, ValueError):
        w, h = 0, 0
    if w >= HUD_MIN_WINDOW_WIDTH and h >= HUD_MIN_WINDOW_HEIGHT:
        return cfg
    out = deepcopy(cfg)
    out["window_customized"] = False
    out["window_width"] = DEFAULT_WINDOW_WIDTH
    out["window_height"] = DEFAULT_WINDOW_HEIGHT
    out["window_x"] = 0
    out["window_y"] = 0
    out["window_dock"] = DEFAULT_WINDOW_DOCK
    return out


def load_layout() -> dict[str, Any]:
    base = default_layout()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return base
    if not isinstance(raw, dict):
        return base
    out = deepcopy(base)
    try:
        ver = int(raw.get("layout_version", 1))
    except (TypeError, ValueError):
        ver = 1
    if ver < LAYOUT_VERSION:
        opening = default_layout()
        for key in (
            "box_scale",
            "forced_columns",
            "show_subtitles",
            "show_nmea_log",
            "sections_row",
            "layout_version",
            "window_dock",
            "window_customized",
            "window_width",
            "window_height",
        ):
            out[key] = opening[key]
    elif "window_width" not in raw:
        opening = default_layout()
        for key in (
            "box_scale",
            "forced_columns",
            "show_subtitles",
            "show_nmea_log",
            "sections_row",
            "window_dock",
            "window_customized",
            "window_width",
            "window_height",
        ):
            out[key] = opening[key]
    sec = raw.get("sections")
    if isinstance(sec, dict):
        for sid in SECTION_IDS:
            block = sec.get(sid)
            if isinstance(block, dict):
                if "visible" in block:
                    out["sections"][sid]["visible"] = bool(block["visible"])
                if "collapsed" in block:
                    out["sections"][sid]["collapsed"] = bool(block["collapsed"])
    met = raw.get("metrics")
    if isinstance(met, dict):
        for mid in METRIC_IDS:
            if mid in met:
                out["metrics"][mid] = bool(met[mid])
    if "footer" in raw:
        out["footer"] = bool(raw["footer"])
    out["section_order"] = normalized_section_order(raw.get("section_order"))
    if "sections_row" in raw:
        out["sections_row"] = bool(raw["sections_row"])
    if "pin_on_top" in raw:
        out["pin_on_top"] = bool(raw["pin_on_top"])
    if "box_scale" in raw:
        try:
            out["box_scale"] = max(0.5, min(2.0, float(raw["box_scale"])))
        except (TypeError, ValueError):
            out["box_scale"] = 1.0
    if "forced_columns" in raw:
        try:
            out["forced_columns"] = max(1, min(12, int(raw["forced_columns"])))
        except (TypeError, ValueError):
            out["forced_columns"] = 6
    if "show_subtitles" in raw:
        out["show_subtitles"] = bool(raw["show_subtitles"])
    if "show_nmea_log" in raw:
        out["show_nmea_log"] = bool(raw["show_nmea_log"])
    if "lock_size" in raw:
        out["lock_size"] = bool(raw["lock_size"])
    if "window_dock" in raw:
        dock = str(raw["window_dock"])
        if dock in ("top_strip", "free"):
            out["window_dock"] = dock
    if "window_customized" in raw:
        out["window_customized"] = bool(raw["window_customized"])
    if "layout_version" in raw:
        try:
            out["layout_version"] = max(1, int(raw["layout_version"]))
        except (TypeError, ValueError):
            pass
    for key, lo, hi, default in (
        ("window_width", 0, 4096, DEFAULT_WINDOW_WIDTH),
        ("window_height", 0, 2160, DEFAULT_WINDOW_HEIGHT),
        ("window_x", -4096, 8192, 0),
        ("window_y", -4096, 8192, 0),
    ):
        if key in raw:
            try:
                val = int(raw[key])
                out[key] = max(lo, min(hi, val))
            except (TypeError, ValueError):
                out[key] = default
    metric_style = raw.get("metric_style")
    if isinstance(metric_style, dict):
        for mid in METRIC_IDS:
            block = metric_style.get(mid)
            if not isinstance(block, dict):
                continue
            if "value_on_top" in block:
                out["metric_style"][mid]["value_on_top"] = bool(block["value_on_top"])
            if "compact" in block:
                out["metric_style"][mid]["compact"] = bool(block["compact"])
    return sanitize_window_geometry(out)


def save_layout(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
