"""Persisted Survey HUD layout (sections, metrics, collapse)."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "survey_hud_layout.json"

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
        "metrics": {mid: True for mid in METRIC_IDS},
        "footer": True,
        # Section strips: drag handles swap order; persisted here.
        "section_order": list(SECTION_IDS),
        "sections_row": False,
        "pin_on_top": True,
        "box_scale": 1.0,
        "forced_columns": 0,
        "show_subtitles": True,
        "show_nmea_log": False,
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


def load_layout() -> dict[str, Any]:
    base = default_layout()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return base
    if not isinstance(raw, dict):
        return base
    out = deepcopy(base)
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
            out["box_scale"] = float(raw["box_scale"])
        except (TypeError, ValueError):
            out["box_scale"] = 1.0
    out["box_scale"] = max(0.50, min(1.9, float(out.get("box_scale", 1.0))))
    if "forced_columns" in raw:
        try:
            out["forced_columns"] = int(raw["forced_columns"])
        except (TypeError, ValueError):
            out["forced_columns"] = 0
    out["forced_columns"] = max(0, min(6, int(out.get("forced_columns", 0))))
    if "show_subtitles" in raw:
        out["show_subtitles"] = bool(raw["show_subtitles"])
    if "show_nmea_log" in raw:
        out["show_nmea_log"] = bool(raw["show_nmea_log"])
    if "lock_size" in raw:
        out["lock_size"] = bool(raw["lock_size"])
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
    return out


def save_layout(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
