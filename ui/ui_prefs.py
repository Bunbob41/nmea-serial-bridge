"""Persisted lightweight UI preferences."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_prefs.json"

_LOGFIRST_DEFAULTS = {
    "rx": True,
    "tx": True,
    "warn": True,
    "pause": False,
    "autoscroll": True,
    "verbose": False,
    "preset": "ops",
    "density": 8,
    "tools_open": False,
}


def _read_json() -> dict[str, Any]:
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _write_json(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_logfirst_prefs() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("logfirst")
    out = dict(_LOGFIRST_DEFAULTS)
    if isinstance(raw, dict):
        out["rx"] = bool(raw.get("rx", out["rx"]))
        out["tx"] = bool(raw.get("tx", out["tx"]))
        out["warn"] = bool(raw.get("warn", out["warn"]))
        out["pause"] = bool(raw.get("pause", out["pause"]))
        out["autoscroll"] = bool(raw.get("autoscroll", out["autoscroll"]))
        out["verbose"] = bool(raw.get("verbose", out["verbose"]))
        preset = str(raw.get("preset", out["preset"]))
        out["preset"] = preset if preset in {"ops", "all", "warn"} else "ops"
        density = int(raw.get("density", out["density"]) or out["density"])
        out["density"] = 10 if density >= 10 else 8
        out["tools_open"] = bool(raw.get("tools_open", out["tools_open"]))
    return out


def save_logfirst_prefs(prefs: dict[str, Any]) -> None:
    data = _read_json()
    old = load_logfirst_prefs()
    old.update(prefs or {})
    clean = {
        "rx": bool(old["rx"]),
        "tx": bool(old["tx"]),
        "warn": bool(old["warn"]),
        "pause": bool(old["pause"]),
        "autoscroll": bool(old["autoscroll"]),
        "verbose": bool(old["verbose"]),
        "preset": str(old["preset"]) if str(old["preset"]) in {"ops", "all", "warn"} else "ops",
        "density": 10 if int(old["density"]) >= 10 else 8,
        "tools_open": bool(old["tools_open"]),
    }
    data["logfirst"] = clean
    _write_json(data)


def load_diag_card_states(ui_mode: str) -> dict[str, bool]:
    data = _read_json()
    all_cards = data.get("diag_cards")
    if not isinstance(all_cards, dict):
        return {}
    mode_map = all_cards.get(ui_mode)
    if not isinstance(mode_map, dict):
        return {}
    return {str(k): bool(v) for k, v in mode_map.items()}


def save_diag_card_states(ui_mode: str, states: dict[str, bool]) -> None:
    data = _read_json()
    cards = data.get("diag_cards")
    if not isinstance(cards, dict):
        cards = {}
    cards[ui_mode] = {str(k): bool(v) for k, v in states.items()}
    data["diag_cards"] = cards
    _write_json(data)
