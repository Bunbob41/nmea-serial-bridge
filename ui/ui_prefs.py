"""Persisted lightweight UI preferences."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_prefs.json"
PREFS_SCHEMA_VERSION = 2

_LOG_VIEW_DEFAULTS = {
    "rx": True,
    "tx": True,
    "warn": True,
    "events": True,
    "pause": False,
    "autoscroll": True,
    "verbose": False,
    "preset": "ops",
    "density": 8,
    "tools_open": False,
    "hex": False,
    "sentence_types": [],
    "log_hex": False,
    "log_sentence": "",
}

_LOGFIRST_DEFAULTS = dict(_LOG_VIEW_DEFAULTS)

RECENT_SESSIONS_MAX = 5


def _read_json() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        try:
            from product_ui_defaults import seed_user_ui_prefs_if_missing

            seed_user_ui_prefs_if_missing()
        except Exception:
            pass
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        # Recover cleanly from malformed/partial files at startup.
        recovered = {"schema_version": PREFS_SCHEMA_VERSION}
        try:
            _write_json(recovered)
        except OSError:
            pass
        return recovered
    if not isinstance(raw, dict):
        raw = {}
    migrated, changed = _migrate_schema(raw)
    if changed:
        try:
            _write_json(migrated)
        except OSError:
            pass
    return migrated


def _write_json(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = dict(data or {})
    out["schema_version"] = PREFS_SCHEMA_VERSION
    CONFIG_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")


def _migrate_schema(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    data = dict(raw or {})
    changed = False
    try:
        ver = int(data.get("schema_version", 0))
    except (TypeError, ValueError):
        ver = 0
    if ver < 1:
        ver = 1
        changed = True
    if ver < 2:
        ver = 2
        changed = True
        connect_raw = data.get("connect_panels")
        if isinstance(connect_raw, dict):
            for key, mode_map in connect_raw.items():
                if not isinstance(mode_map, dict):
                    continue
                toolbar = mode_map.get("toolbar_order")
                if not isinstance(toolbar, list) or not any(str(x).strip() for x in toolbar):
                    mode_map["toolbar_order"] = list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
                    changed = True
                connect_raw[str(key)] = mode_map
            data["connect_panels"] = connect_raw
    if ver < 3:
        ver = 3
        changed = True
        if "web_ui" not in data:
            data["web_ui"] = {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 8765,
                "lan_bind": False,
            }
        else:
            raw_web = data.get("web_ui")
            if isinstance(raw_web, dict) and "enabled" not in raw_web:
                raw_web["enabled"] = True
                data["web_ui"] = raw_web
    if "schema_version" not in data or data.get("schema_version") != ver:
        changed = True
    data["schema_version"] = ver
    return data, changed


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
        out["density"] = 12 if density >= 10 else 8
        out["tools_open"] = bool(raw.get("tools_open", out["tools_open"]))
        out["events"] = bool(raw.get("events", out.get("events", True)))
        out["hex"] = bool(raw.get("hex", raw.get("log_hex", out.get("hex", False))))
        out["log_hex"] = out["hex"]
        out["log_sentence"] = str(raw.get("log_sentence", out["log_sentence"]) or "")
        types = raw.get("sentence_types")
        if isinstance(types, list):
            out["sentence_types"] = [str(t) for t in types if str(t).strip()]
    return out


def save_logfirst_prefs(prefs: dict[str, Any]) -> None:
    data = _read_json()
    old = load_logfirst_prefs()
    old.update(prefs or {})
    clean = _clean_log_ui_prefs(old)
    data["logfirst"] = clean
    _write_json(data)


def _clean_log_ui_prefs(old: dict[str, Any]) -> dict[str, Any]:
    preset = str(old.get("preset", "ops"))
    if preset == "all":
        preset = "wire_tap"
    allowed = {"ops", "survey", "wire_tap", "warn_only", "debug", "custom", "warn"}
    if preset not in allowed:
        preset = "ops"
    hex_on = bool(old.get("hex", old.get("log_hex", False)))
    types = old.get("sentence_types")
    st_list: list[str] = []
    if isinstance(types, list):
        st_list = [str(t).strip().upper() for t in types if str(t).strip()]
    return {
        "rx": bool(old["rx"]),
        "tx": bool(old["tx"]),
        "warn": bool(old["warn"]),
        "events": bool(old.get("events", True)),
        "pause": bool(old["pause"]),
        "autoscroll": bool(old["autoscroll"]),
        "verbose": bool(old["verbose"]),
        "preset": preset,
        "density": 12 if int(old["density"]) >= 10 else 8,
        "tools_open": bool(old["tools_open"]),
        "hex": hex_on,
        "log_hex": hex_on,
        "log_sentence": str(old.get("log_sentence", "") or ""),
        "sentence_types": st_list,
    }


def load_log_terminal_prefs() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("log_terminal")
    out = dict(_LOG_VIEW_DEFAULTS)
    if isinstance(raw, dict):
        out.update(_clean_log_ui_prefs({**out, **raw}))
    return out


def save_log_terminal_prefs(prefs: dict[str, Any]) -> None:
    data = _read_json()
    old = load_log_terminal_prefs()
    old.update(prefs or {})
    data["log_terminal"] = _clean_log_ui_prefs(old)
    _write_json(data)


def load_recent_sessions() -> list[dict[str, Any]]:
    data = _read_json()
    raw = data.get("recent_sessions")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("com"):
            cur = dict(item)
            cur["pinned"] = bool(cur.get("pinned", False))
            out.append(cur)
    return out[:RECENT_SESSIONS_MAX]


def _recent_session_key(entry: dict[str, Any]) -> str:
    return "|".join(
        str(entry.get(k, ""))
        for k in ("com", "baud", "net_mode", "udp_host", "udp_port", "nmea_mode")
    )


def recent_session_key(entry: dict[str, Any]) -> str:
    return _recent_session_key(entry)


def push_recent_session(entry: dict[str, Any]) -> None:
    if not str(entry.get("com", "")).strip():
        return
    key = _recent_session_key(entry)
    data = _read_json()
    sessions = [s for s in load_recent_sessions() if _recent_session_key(s) != key]
    pinned = bool(entry.get("pinned", False))
    sessions.insert(0, {**dict(entry), "pinned": pinned})
    pinned_rows = [s for s in sessions if bool(s.get("pinned", False))]
    free_rows = [s for s in sessions if not bool(s.get("pinned", False))]
    data["recent_sessions"] = (pinned_rows + free_rows)[:RECENT_SESSIONS_MAX]
    _write_json(data)


def set_recent_session_pinned(key: str, pinned: bool) -> bool:
    sessions = load_recent_sessions()
    changed = False
    for s in sessions:
        if _recent_session_key(s) == key:
            s["pinned"] = bool(pinned)
            changed = True
            break
    if not changed:
        return False
    pinned_rows = [s for s in sessions if bool(s.get("pinned", False))]
    free_rows = [s for s in sessions if not bool(s.get("pinned", False))]
    data = _read_json()
    data["recent_sessions"] = (pinned_rows + free_rows)[:RECENT_SESSIONS_MAX]
    _write_json(data)
    return True


def reorder_recent_sessions(ordered_keys: list[str]) -> bool:
    sessions = load_recent_sessions()
    if not sessions:
        return False
    by_key = {_recent_session_key(s): s for s in sessions}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ordered_keys:
        clean = str(key).strip()
        if clean and clean in by_key and clean not in seen:
            out.append(by_key[clean])
            seen.add(clean)
    for s in sessions:
        k = _recent_session_key(s)
        if k not in seen:
            out.append(s)
    data = _read_json()
    data["recent_sessions"] = out[:RECENT_SESSIONS_MAX]
    _write_json(data)
    return True


def _load_log_ui_prefs(key: str) -> dict[str, Any]:
    data = _read_json()
    raw = data.get(key)
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
        out["density"] = 12 if density >= 10 else 8
        out["tools_open"] = bool(raw.get("tools_open", out["tools_open"]))
    return out


def load_field_prefs() -> dict[str, Any]:
    data = _read_json()
    if isinstance(data.get("field"), dict):
        out = _load_log_ui_prefs("field")
        raw = data["field"]
        if isinstance(raw, dict) and isinstance(raw.get("splitter_sizes"), list):
            out["splitter_sizes"] = raw["splitter_sizes"]
        return out
    if isinstance(data.get("logfirst"), dict):
        return _load_log_ui_prefs("logfirst")
    return dict(_LOGFIRST_DEFAULTS)


def save_field_prefs(prefs: dict[str, Any]) -> None:
    data = _read_json()
    old = load_field_prefs()
    old.update(prefs or {})
    clean = _clean_log_ui_prefs(old)
    raw_sizes = prefs.get("splitter_sizes") if prefs else None
    if isinstance(raw_sizes, list) and len(raw_sizes) >= 2:
        try:
            clean["splitter_sizes"] = [max(int(x), 80) for x in raw_sizes[:2]]
        except (TypeError, ValueError):
            pass
    data["field"] = clean
    _write_json(data)


def load_minimal_prefs() -> dict[str, Any]:
    data = _read_json()
    if isinstance(data.get("minimal"), dict):
        return _load_log_ui_prefs("minimal")
    return {"tools_open": False}


def save_minimal_prefs(prefs: dict[str, Any]) -> None:
    data = _read_json()
    old = load_minimal_prefs()
    old.update(prefs or {})
    data["minimal"] = {"tools_open": bool(old.get("tools_open", False))}
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


def dedupe_preserve_order(names: list[str]) -> list[str]:
    """Drop duplicate labels while keeping the first occurrence."""
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        text = str(name).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def load_tab_order(ui_mode: str, key: str) -> list[str]:
    data = _read_json()
    all_tabs = data.get("tab_order")
    if not isinstance(all_tabs, dict):
        return []
    mode_map = all_tabs.get(ui_mode)
    if not isinstance(mode_map, dict):
        return []
    raw = mode_map.get(key)
    if not isinstance(raw, list):
        return []
    raw_labels = [str(item).strip() for item in raw if str(item).strip()]
    raw_set = set(raw_labels)
    # v1.13.x: lone "Terminal" tab was NMEA inject; modern layouts have Inject + shell Terminal.
    legacy_terminal_is_inject = (
        "Terminal" in raw_set and "Inject" not in raw_set and "Send" not in raw_set
    )
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        if text == "Send":
            text = "Inject"
        elif text == "Terminal" and legacy_terminal_is_inject:
            text = "Inject"
        out.append(text)
    return dedupe_preserve_order(out)


def save_tab_order(ui_mode: str, key: str, order: list[str]) -> None:
    clean = dedupe_preserve_order([str(x).strip() for x in order if str(x).strip()])
    data = _read_json()
    all_tabs = data.get("tab_order")
    if not isinstance(all_tabs, dict):
        all_tabs = {}
    mode_map = all_tabs.get(ui_mode)
    if not isinstance(mode_map, dict):
        mode_map = {}
    mode_map[key] = clean
    all_tabs[ui_mode] = mode_map
    data["tab_order"] = all_tabs
    _write_json(data)


def load_hidden_tabs(ui_mode: str, key: str) -> list[str]:
    data = _read_json()
    all_hidden = data.get("hidden_tabs")
    if not isinstance(all_hidden, dict):
        return []
    mode_map = all_hidden.get(ui_mode)
    if not isinstance(mode_map, dict):
        return []
    raw = mode_map.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        if text == "Send":
            text = "Inject"
        elif text == "Terminal":
            # Hidden old inject tab → hide new Inject name.
            text = "Inject"
        out.append(text)
    return out


def save_hidden_tabs(ui_mode: str, key: str, hidden: list[str]) -> None:
    clean = [str(x).strip() for x in hidden if str(x).strip()]
    data = _read_json()
    all_hidden = data.get("hidden_tabs")
    if not isinstance(all_hidden, dict):
        all_hidden = {}
    mode_map = all_hidden.get(ui_mode)
    if not isinstance(mode_map, dict):
        mode_map = {}
    mode_map[key] = clean
    all_hidden[ui_mode] = mode_map
    data["hidden_tabs"] = all_hidden
    _write_json(data)


def load_diag_card_order(ui_mode: str) -> list[str]:
    data = _read_json()
    all_cards = data.get("diag_card_order")
    if not isinstance(all_cards, dict):
        return []
    raw = all_cards.get(ui_mode)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def save_diag_card_order(ui_mode: str, order: list[str]) -> None:
    clean = [str(x).strip() for x in order if str(x).strip()]
    data = _read_json()
    all_cards = data.get("diag_card_order")
    if not isinstance(all_cards, dict):
        all_cards = {}
    all_cards[ui_mode] = clean
    data["diag_card_order"] = all_cards
    _write_json(data)


def load_diag_card_sizes(ui_mode: str) -> dict[str, int]:
    data = _read_json()
    all_sizes = data.get("diag_card_sizes")
    if not isinstance(all_sizes, dict):
        return {}
    raw = all_sizes.get(ui_mode)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, val in raw.items():
        try:
            out[str(key)] = int(val)
        except (TypeError, ValueError):
            continue
    return out


def save_diag_card_sizes(ui_mode: str, sizes: dict[str, int]) -> None:
    clean: dict[str, int] = {}
    for key, val in sizes.items():
        try:
            clean[str(key)] = int(val)
        except (TypeError, ValueError):
            continue
    data = _read_json()
    all_sizes = data.get("diag_card_sizes")
    if not isinstance(all_sizes, dict):
        all_sizes = {}
    all_sizes[ui_mode] = clean
    data["diag_card_sizes"] = all_sizes
    _write_json(data)


def load_top_bar_prefs(ui_mode: str) -> dict[str, Any]:
    data = _read_json()
    raw_all = data.get("top_bar")
    if not isinstance(raw_all, dict):
        return {"order": [], "hidden": [], "shortcuts_visible": False}
    raw = raw_all.get(ui_mode)
    if not isinstance(raw, dict):
        return {"order": [], "hidden": [], "shortcuts_visible": False}
    order_raw = raw.get("order")
    hidden_raw = raw.get("hidden")
    order = [str(x).strip() for x in order_raw] if isinstance(order_raw, list) else []
    hidden = [str(x).strip() for x in hidden_raw] if isinstance(hidden_raw, list) else []
    weights_raw = raw.get("chip_weights")
    chip_weights: dict[str, float] = {}
    if isinstance(weights_raw, dict):
        for k, v in weights_raw.items():
            key = str(k).strip()
            if not key:
                continue
            try:
                chip_weights[key] = max(float(v), 0.25)
            except (TypeError, ValueError):
                continue
    return {
        "order": [x for x in order if x],
        "hidden": [x for x in hidden if x],
        "shortcuts_visible": bool(raw.get("shortcuts_visible", False)),
        "position": str(raw.get("position", "top")).strip().lower() or "top",
        "chip_weights": chip_weights,
    }


def save_top_bar_prefs(ui_mode: str, prefs: dict[str, Any]) -> None:
    data = _read_json()
    raw_all = data.get("top_bar")
    if not isinstance(raw_all, dict):
        raw_all = {}
    weights_in = prefs.get("chip_weights", {})
    chip_weights: dict[str, float] = {}
    if isinstance(weights_in, dict):
        for k, v in weights_in.items():
            key = str(k).strip()
            if not key:
                continue
            try:
                chip_weights[key] = max(float(v), 0.25)
            except (TypeError, ValueError):
                continue
    clean = {
        "order": [str(x).strip() for x in prefs.get("order", []) if str(x).strip()],
        "hidden": [str(x).strip() for x in prefs.get("hidden", []) if str(x).strip()],
        "shortcuts_visible": bool(prefs.get("shortcuts_visible", False)),
        "position": str(prefs.get("position", "top")).strip().lower() or "top",
        "chip_weights": chip_weights,
    }
    raw_all[ui_mode] = clean
    data["top_bar"] = raw_all
    _write_json(data)


def load_file_log_prefs() -> dict[str, int]:
    data = _read_json()
    raw = data.get("file_log")
    if not isinstance(raw, dict):
        return {"max_mb": 10, "backups": 5}
    try:
        max_mb = int(raw.get("max_mb", 10))
    except (TypeError, ValueError):
        max_mb = 10
    try:
        backups = int(raw.get("backups", 5))
    except (TypeError, ValueError):
        backups = 5
    if max_mb not in (10, 25, 50, 100):
        max_mb = 10
    if backups not in (0, 3, 5, 10):
        backups = 5
    return {"max_mb": max_mb, "backups": backups}


def save_file_log_prefs(max_mb: int, backups: int) -> None:
    data = _read_json()
    data["file_log"] = {"max_mb": int(max_mb), "backups": int(backups)}
    _write_json(data)


_MODERN_SLOT_DEFAULTS: dict[str, str] = {
    "left_top": "control",
    "left_bottom": "settings",
    "center": "log",
    "right_top": "hub",
    "right_bottom": "telem",
}
_MODERN_SPLIT_DEFAULTS: dict[str, list[int]] = {
    "hsplit": [300, 720, 300],
    "left_vsplit": [480, 260],
    "right_vsplit": [490, 250],
}
_MODERN_ALL_PANELS = frozenset(_MODERN_SLOT_DEFAULTS.values())
_MODERN_ALL_SLOTS = frozenset(_MODERN_SLOT_DEFAULTS.keys())


def load_modern_layout_prefs() -> dict[str, Any]:
    """Return splitter sizes and panel slot assignments for the Modern layout."""
    data = _read_json()
    raw = data.get("modern_layout")
    out: dict[str, Any] = {
        "slot_assignments": dict(_MODERN_SLOT_DEFAULTS),
        **{k: list(v) for k, v in _MODERN_SPLIT_DEFAULTS.items()},
    }
    if not isinstance(raw, dict):
        return out
    for key, default in _MODERN_SPLIT_DEFAULTS.items():
        val = raw.get(key)
        if isinstance(val, list) and len(val) >= len(default):
            try:
                out[key] = [max(80, int(x)) for x in val[: len(default)]]
            except (TypeError, ValueError):
                pass
    raw_slots = raw.get("slot_assignments")
    if isinstance(raw_slots, dict):
        used: set[str] = set()
        clean: dict[str, str] = {}
        for slot in _MODERN_ALL_SLOTS:
            panel = str(raw_slots.get(slot, "")).strip()
            if panel in _MODERN_ALL_PANELS and panel not in used:
                clean[slot] = panel
                used.add(panel)
        for slot in _MODERN_ALL_SLOTS:
            if slot not in clean:
                remaining = [p for p in _MODERN_ALL_PANELS if p not in used]
                if remaining:
                    clean[slot] = remaining[0]
                    used.add(remaining[0])
        out["slot_assignments"] = clean
    return out


def save_modern_layout_prefs(
    *,
    hsplit: list[int] | None = None,
    left_vsplit: list[int] | None = None,
    right_vsplit: list[int] | None = None,
    slot_assignments: dict[str, str] | None = None,
) -> None:
    data = _read_json()
    prev = data.get("modern_layout")
    payload: dict[str, Any] = dict(prev) if isinstance(prev, dict) else {}
    if hsplit is not None:
        payload["hsplit"] = [max(80, int(x)) for x in hsplit[:3]]
    if left_vsplit is not None:
        payload["left_vsplit"] = [max(80, int(x)) for x in left_vsplit[:2]]
    if right_vsplit is not None:
        payload["right_vsplit"] = [max(80, int(x)) for x in right_vsplit[:2]]
    if slot_assignments is not None:
        payload["slot_assignments"] = {str(k): str(v) for k, v in slot_assignments.items()}
    data["modern_layout"] = payload
    _write_json(data)


def load_local_backup_prefs() -> dict[str, bool]:
    """Black-box raw COM backup (independent of rotating NMEA file log)."""
    data = _read_json()
    raw = data.get("local_backup")
    if not isinstance(raw, dict):
        return {"enabled": True}
    return {"enabled": bool(raw.get("enabled", True))}


def save_local_backup_prefs(*, enabled: bool) -> None:
    data = _read_json()
    data["local_backup"] = {"enabled": bool(enabled)}
    _write_json(data)


def load_ntrip_prefs() -> dict[str, str | bool]:
    """NTRIP UI removed — always disabled (Applanix/INS workflows use internal RTK)."""
    data = _read_json()
    raw = data.get("ntrip")
    if not isinstance(raw, dict):
        raw = {}
    return {
        "enabled": False,
        "caster": str(raw.get("caster", "")).strip(),
        "mountpoint": str(raw.get("mountpoint", "")).strip(),
        "username": str(raw.get("username", "")).strip(),
        "password": str(raw.get("password", "")),
    }


_CONNECT_PANEL_DEFAULT_ORDER = [
    "run",
    "connection",
    "hint",
    "quick_log",
    "quick_terminal",
]
# Pre-1.9.27 factory order (Serial & network last).
_LEGACY_CONNECT_PANEL_ORDER = [
    "run",
    "hint",
    "quick_log",
    "quick_terminal",
    "connection",
]
_CONNECT_TOOLBAR_DEFAULT_ORDER = [
    "ui_editor",
    "expand_all",
    "collapse_all",
]
_CONNECT_TOOLBAR_VALID_KEYS = frozenset(_CONNECT_TOOLBAR_DEFAULT_ORDER)


def load_connect_panel_prefs(ui_mode: str) -> dict[str, Any]:
    data = _read_json()
    raw_all = data.get("connect_panels")
    if not isinstance(raw_all, dict):
        return {
            "order": list(_CONNECT_PANEL_DEFAULT_ORDER),
            "collapsed": {},
            "sizes": {},
            "hidden": [],
            "toolbar_order": list(_CONNECT_TOOLBAR_DEFAULT_ORDER),
            "qr_lane_width": 228,
            "connect_row_style": "pill",
            "hub_split_sizes": [320, 200],
        }
    raw = raw_all.get(ui_mode)
    if not isinstance(raw, dict):
        return {
            "order": list(_CONNECT_PANEL_DEFAULT_ORDER),
            "collapsed": {},
            "sizes": {},
            "hidden": [],
            "toolbar_order": list(_CONNECT_TOOLBAR_DEFAULT_ORDER),
            "qr_lane_width": 228,
            "connect_row_style": "pill",
            "hub_split_sizes": [320, 200],
        }
    order_raw = raw.get("order")
    order = [str(x).strip() for x in order_raw] if isinstance(order_raw, list) else []
    if not order:
        order = list(_CONNECT_PANEL_DEFAULT_ORDER)
    order = [k for k in order if k in _CONNECT_PANEL_DEFAULT_ORDER and k != "ntrip"]
    if order == _LEGACY_CONNECT_PANEL_ORDER:
        order = list(_CONNECT_PANEL_DEFAULT_ORDER)
    for k in _CONNECT_PANEL_DEFAULT_ORDER:
        if k not in order:
            order.append(k)
    collapsed_raw = raw.get("collapsed")
    collapsed: dict[str, bool] = {}
    if isinstance(collapsed_raw, dict):
        for k, v in collapsed_raw.items():
            collapsed[str(k).strip()] = bool(v)
    sizes_raw = raw.get("sizes")
    sizes: dict[str, int] = {}
    if isinstance(sizes_raw, dict):
        for k, v in sizes_raw.items():
            key = str(k).strip()
            if not key:
                continue
            try:
                sizes[key] = max(28, int(v))
            except (TypeError, ValueError):
                continue
    hidden_raw = raw.get("hidden")
    hidden: list[str] = []
    if isinstance(hidden_raw, list):
        hidden = [
            str(x).strip()
            for x in hidden_raw
            if str(x).strip() and str(x).strip() != "ntrip"
        ]
    toolbar_raw = raw.get("toolbar_order")
    toolbar_order = (
        [str(x).strip() for x in toolbar_raw if str(x).strip()]
        if isinstance(toolbar_raw, list)
        else list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
    )
    if not toolbar_order:
        toolbar_order = list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
    toolbar_order = [k for k in toolbar_order if k in _CONNECT_TOOLBAR_VALID_KEYS]
    for k in _CONNECT_TOOLBAR_DEFAULT_ORDER:
        if k not in toolbar_order:
            toolbar_order.append(k)
    qr_lane_width = 228
    try:
        qr_lane_width = max(120, min(480, int(raw.get("qr_lane_width", 228))))
    except (TypeError, ValueError):
        pass
    qr_float_pos: list[int] | None = None
    raw_pos = raw.get("qr_float_pos")
    if isinstance(raw_pos, (list, tuple)) and len(raw_pos) >= 2:
        try:
            qr_float_pos = [max(0, int(raw_pos[0])), max(0, int(raw_pos[1]))]
        except (TypeError, ValueError):
            qr_float_pos = None
    from ui.connect_row_style import normalize_connect_row_style

    connect_row_style = normalize_connect_row_style(str(raw.get("connect_row_style", "pill")))
    hub_split_sizes: list[int] = [320, 200]
    raw_hub = raw.get("hub_split_sizes")
    if isinstance(raw_hub, (list, tuple)) and len(raw_hub) >= 2:
        try:
            hub_split_sizes = [
                max(120, int(raw_hub[0])),
                max(100, int(raw_hub[1])),
            ]
        except (TypeError, ValueError):
            pass
    return {
        "order": order,
        "collapsed": collapsed,
        "sizes": sizes,
        "hidden": hidden,
        "toolbar_order": toolbar_order,
        "qr_lane_width": qr_lane_width,
        "qr_float_pos": qr_float_pos,
        "connect_row_style": connect_row_style,
        "hub_split_sizes": hub_split_sizes,
    }


def save_connect_panel_prefs(
    ui_mode: str,
    order: list[str],
    collapsed: dict[str, bool],
    *,
    sizes: dict[str, int] | None = None,
    hidden: list[str] | None = None,
    toolbar_order: list[str] | None = None,
    qr_lane_width: int | None = None,
    qr_float_pos: list[int] | None = None,
    connect_row_style: str | None = None,
    hub_split_sizes: list[int] | None = None,
) -> None:
    data = _read_json()
    raw_all = data.get("connect_panels")
    if not isinstance(raw_all, dict):
        raw_all = {}
    prev = raw_all.get(ui_mode) if isinstance(raw_all.get(ui_mode), dict) else {}
    size_out: dict[str, int] = {}
    if sizes is not None:
        for k, v in sizes.items():
            key = str(k).strip()
            if key:
                size_out[key] = max(28, int(v))
    elif isinstance(prev, dict) and isinstance(prev.get("sizes"), dict):
        for k, v in prev["sizes"].items():
            key = str(k).strip()
            if key:
                try:
                    size_out[key] = max(28, int(v))
                except (TypeError, ValueError):
                    pass
    hidden_out: list[str] = []
    if hidden is not None:
        hidden_out = [str(x).strip() for x in hidden if str(x).strip()]
    elif isinstance(prev, dict) and isinstance(prev.get("hidden"), list):
        hidden_out = [str(x).strip() for x in prev["hidden"] if str(x).strip()]
    toolbar_out: list[str] = []
    if toolbar_order is not None:
        toolbar_out = [str(x).strip() for x in toolbar_order if str(x).strip()]
    elif isinstance(prev, dict) and isinstance(prev.get("toolbar_order"), list):
        toolbar_out = [str(x).strip() for x in prev["toolbar_order"] if str(x).strip()]
    if not toolbar_out:
        toolbar_out = list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
    toolbar_out = [k for k in toolbar_out if k in _CONNECT_TOOLBAR_VALID_KEYS]
    for k in _CONNECT_TOOLBAR_DEFAULT_ORDER:
        if k not in toolbar_out:
            toolbar_out.append(k)
    qr_w = 228
    if qr_lane_width is not None:
        qr_w = max(120, min(480, int(qr_lane_width)))
    elif isinstance(prev, dict):
        try:
            qr_w = max(120, min(480, int(prev.get("qr_lane_width", 228))))
        except (TypeError, ValueError):
            pass
    from ui.connect_row_style import normalize_connect_row_style

    row_style = normalize_connect_row_style(
        str(connect_row_style or (prev.get("connect_row_style") if isinstance(prev, dict) else "") or "pill")
    )
    hub_out = [320, 200]
    if hub_split_sizes is not None and len(hub_split_sizes) >= 2:
        hub_out = [max(120, int(hub_split_sizes[0])), max(100, int(hub_split_sizes[1]))]
    elif isinstance(prev, dict):
        raw_hub = prev.get("hub_split_sizes")
        if isinstance(raw_hub, (list, tuple)) and len(raw_hub) >= 2:
            try:
                hub_out = [max(120, int(raw_hub[0])), max(100, int(raw_hub[1]))]
            except (TypeError, ValueError):
                pass
    float_pos_out = None
    if qr_float_pos is not None and len(qr_float_pos) >= 2:
        try:
            float_pos_out = [max(0, int(qr_float_pos[0])), max(0, int(qr_float_pos[1]))]
        except (TypeError, ValueError):
            float_pos_out = None
    elif isinstance(prev, dict):
        raw_fp = prev.get("qr_float_pos")
        if isinstance(raw_fp, (list, tuple)) and len(raw_fp) >= 2:
            try:
                float_pos_out = [max(0, int(raw_fp[0])), max(0, int(raw_fp[1]))]
            except (TypeError, ValueError):
                float_pos_out = None
    raw_all[ui_mode] = {
        "order": [str(x).strip() for x in order if str(x).strip()],
        "collapsed": {str(k).strip(): bool(v) for k, v in collapsed.items() if str(k).strip()},
        "sizes": size_out,
        "hidden": hidden_out,
        "toolbar_order": toolbar_out,
        "qr_lane_width": qr_w,
        "qr_float_pos": float_pos_out,
        "connect_row_style": row_style,
        "hub_split_sizes": hub_out,
    }
    data["connect_panels"] = raw_all
    _write_json(data)


def load_bench_setup_prefs() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("bench_setup")
    if not isinstance(raw, dict):
        return {"hide_dialog": False}
    return {"hide_dialog": bool(raw.get("hide_dialog", False))}


def save_bench_setup_prefs(*, hide_dialog: bool) -> None:
    data = _read_json()
    data["bench_setup"] = {"hide_dialog": bool(hide_dialog)}
    _write_json(data)


def load_auto_discover_pref() -> bool:
    """Return whether the auto-discover checkbox should be checked (default False)."""
    data = _read_json()
    raw = data.get("auto_discover")
    if isinstance(raw, dict):
        return bool(raw.get("enabled", False))
    return False


def save_auto_discover_pref(enabled: bool) -> None:
    data = _read_json()
    data["auto_discover"] = {"enabled": bool(enabled)}
    _write_json(data)


def load_last_known_good(device_id: str) -> Optional[dict]:
    """Per-device last successful bridge settings (COM, UDP, TCP sink, …)."""
    did = (device_id or "").strip()
    if not did:
        return None
    data = _read_json()
    lkg = data.get("last_known_good")
    if not isinstance(lkg, dict):
        return None
    entry = lkg.get(did)
    return entry if isinstance(entry, dict) else None


def load_discovery_scan_prefs() -> dict:
    data = _read_json()
    raw = data.get("discovery_scan")
    if not isinstance(raw, dict):
        return {"background_enabled": False, "background_interval_s": 30}
    return {
        "background_enabled": bool(raw.get("background_enabled", False)),
        "background_interval_s": max(10, int(raw.get("background_interval_s", 30))),
    }


def save_discovery_scan_prefs(*, background_enabled: bool, background_interval_s: int) -> None:
    data = _read_json()
    data["discovery_scan"] = {
        "background_enabled": bool(background_enabled),
        "background_interval_s": max(10, int(background_interval_s)),
    }
    _write_json(data)


_WEB_UI_DEFAULTS = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8765,
    "lan_bind": False,
    "token": None,
    "phone_base_url": None,
}


def load_web_ui_prefs() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("web_ui")
    if not isinstance(raw, dict):
        return dict(_WEB_UI_DEFAULTS)
    port = raw.get("port", 8765)
    try:
        port_i = int(port)
    except (TypeError, ValueError):
        port_i = 8765
    token = raw.get("token")
    phone_base = raw.get("phone_base_url")
    phone_s = str(phone_base).strip() if phone_base else None
    return {
        "enabled": bool(raw.get("enabled", True)),
        "host": str(raw.get("host", "127.0.0.1")).strip() or "127.0.0.1",
        "port": max(1024, min(65535, port_i)),
        "lan_bind": bool(raw.get("lan_bind", False)),
        "token": str(token).strip() if token else None,
        "phone_base_url": phone_s or None,
    }


def generate_web_api_token() -> str:
    """URL-safe random token for X-Bridge-Token when LAN bind is enabled."""
    import secrets

    return secrets.token_urlsafe(24)


def save_web_ui_prefs(
    *,
    enabled: bool,
    host: str,
    port: int,
    lan_bind: bool,
    token: Optional[str],
    phone_base_url: Optional[str] = None,
) -> None:
    prev = load_web_ui_prefs()
    phone = phone_base_url if phone_base_url is not None else prev.get("phone_base_url")
    phone_s = (phone or "").strip() or None
    data = _read_json()
    data["web_ui"] = {
        "enabled": bool(enabled),
        "host": (host or "127.0.0.1").strip(),
        "port": max(1024, min(65535, int(port))),
        "lan_bind": bool(lan_bind),
        "token": (token or "").strip() or None,
        "phone_base_url": phone_s,
    }
    _write_json(data)


# Web operator dashboard layout (browser localStorage mirror for product defaults).
WEB_DASHBOARD_STORAGE_KEYS: tuple[str, ...] = (
    "nmea-gridstack-layout-v2",
    "nmea-dashboard-chrome-v1",
    "nmea-dashboard-layout-locked",
    "nmea-monitor-collapse",
    "nmea-dashboard-panels",
    "nmea-dashboard-order",
    "nmea-bridge-map-enabled",
    "nmea-bridge-map-base-layer",
    "nmea-bridge-show-qr",
    "nmea-bridge-log-view",
    "nmea-bridge-log-filter",
    "nmea-bridge-log-nmea-types",
)
WEB_DASHBOARD_STRIP_STORAGE_KEYS = frozenset(
    {"nmea-bridge-web-token", "nmea-bridge-log-text"}
)
_WEB_DASHBOARD_MAX_BYTES = 256 * 1024
_VALID_WEB_DASHBOARD_MODES = frozenset({"classic", "gridstack"})


def _gridstack_layout_tile_count(raw_json: str) -> int:
    try:
        layout = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        return 0
    if not isinstance(layout, list):
        return 0
    return sum(1 for node in layout if isinstance(node, dict) and node.get("id"))


def _sanitize_web_dashboard_local_storage(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    total = 0
    allowed = frozenset(WEB_DASHBOARD_STORAGE_KEYS) - WEB_DASHBOARD_STRIP_STORAGE_KEYS
    for key, val in raw.items():
        if key not in allowed:
            continue
        if val is None:
            continue
        s = val if isinstance(val, str) else json.dumps(val, separators=(",", ":"))
        if not s:
            continue
        if key == "nmea-gridstack-layout-v2" and _gridstack_layout_tile_count(s) < 4:
            continue
        total += len(key) + len(s)
        if total > _WEB_DASHBOARD_MAX_BYTES:
            break
        out[str(key)] = s
    return out


def load_web_dashboard_layout() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("web_dashboard")
    if not isinstance(raw, dict):
        return {"layout_mode": "gridstack", "local_storage": {}}
    mode = str(raw.get("layout_mode") or "gridstack").strip().lower()
    if mode not in _VALID_WEB_DASHBOARD_MODES:
        mode = "gridstack"
    return {
        "layout_mode": mode,
        "local_storage": _sanitize_web_dashboard_local_storage(raw.get("local_storage")),
    }


def save_web_dashboard_layout(
    *,
    layout_mode: str,
    local_storage: dict[str, Any],
) -> None:
    mode = str(layout_mode or "gridstack").strip().lower()
    if mode not in _VALID_WEB_DASHBOARD_MODES:
        mode = "gridstack"
    clean = _sanitize_web_dashboard_local_storage(local_storage)
    data = _read_json()
    data["web_dashboard"] = {"layout_mode": mode, "local_storage": clean}
    _write_json(data)


def save_last_known_good(device_id: str, config: dict) -> None:
    did = (device_id or "").strip()
    if not did or not isinstance(config, dict):
        return
    data = _read_json()
    lkg = data.get("last_known_good")
    if not isinstance(lkg, dict):
        lkg = {}
    lkg[did] = dict(config)
    data["last_known_good"] = lkg
    _write_json(data)


def save_ntrip_prefs(prefs: dict[str, str | bool]) -> None:
    data = _read_json()
    data["ntrip"] = {
        "enabled": False,
        "caster": str(prefs.get("caster", "")).strip(),
        "mountpoint": str(prefs.get("mountpoint", "")).strip(),
        "username": str(prefs.get("username", "")).strip(),
        "password": str(prefs.get("password", "")),
    }
    _write_json(data)


_QR_OVERLAY_MODES = ("field", "standard", "minimal", "logfirst")


def _migrate_qr_overlay_from_connect_panels(data: dict[str, Any]) -> dict[str, Any] | None:
    """One-time import of per-layout pixel QR position into global qr_overlay."""
    raw_all = data.get("connect_panels")
    if not isinstance(raw_all, dict):
        return None
    for mode in _QR_OVERLAY_MODES:
        raw = raw_all.get(mode)
        if not isinstance(raw, dict):
            continue
        pos = raw.get("qr_float_pos")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            try:
                return {
                    "float_pos_pixels": [int(pos[0]), int(pos[1])],
                    "user_positioned": True,
                }
            except (TypeError, ValueError):
                continue
    return None


def load_qr_overlay_prefs() -> dict[str, Any]:
    data = _read_json()
    raw = data.get("qr_overlay")
    out: dict[str, Any] = {
        "float_pos_norm": None,
        "float_pos_pixels": None,
        "user_positioned": False,
    }
    if isinstance(raw, dict):
        norm = raw.get("float_pos_norm")
        if isinstance(norm, (list, tuple)) and len(norm) >= 2:
            try:
                nx = max(0.0, min(1.0, float(norm[0])))
                ny = max(0.0, min(1.0, float(norm[1])))
                out["float_pos_norm"] = (nx, ny)
                out["user_positioned"] = bool(raw.get("user_positioned", True))
            except (TypeError, ValueError):
                pass
        pix = raw.get("float_pos_pixels")
        if isinstance(pix, (list, tuple)) and len(pix) >= 2:
            try:
                out["float_pos_pixels"] = [int(pix[0]), int(pix[1])]
            except (TypeError, ValueError):
                pass
        if raw.get("user_positioned") is not None:
            out["user_positioned"] = bool(raw.get("user_positioned"))
    if out["float_pos_norm"] is None and out["float_pos_pixels"] is None:
        migrated = _migrate_qr_overlay_from_connect_panels(data)
        if migrated:
            out.update(migrated)
            payload: dict[str, Any] = {
                "user_positioned": bool(out.get("user_positioned")),
            }
            pix = out.get("float_pos_pixels")
            if isinstance(pix, (list, tuple)) and len(pix) >= 2:
                payload["float_pos_pixels"] = [int(pix[0]), int(pix[1])]
            data["qr_overlay"] = payload
            _write_json(data)
    return out


def save_qr_overlay_prefs(
    *,
    float_pos_norm: tuple[float, float] | list[float] | None = None,
    float_pos_pixels: list[int] | None = None,
    user_positioned: bool | None = None,
) -> None:
    prev = load_qr_overlay_prefs()
    norm_out = prev.get("float_pos_norm")
    if float_pos_norm is not None:
        try:
            nx = max(0.0, min(1.0, float(float_pos_norm[0])))
            ny = max(0.0, min(1.0, float(float_pos_norm[1])))
            norm_out = (nx, ny)
        except (TypeError, ValueError, IndexError):
            pass
    pix_out = prev.get("float_pos_pixels")
    if float_pos_pixels is not None and len(float_pos_pixels) >= 2:
        try:
            pix_out = [max(0, int(float_pos_pixels[0])), max(0, int(float_pos_pixels[1]))]
        except (TypeError, ValueError):
            pix_out = None
    positioned = (
        bool(user_positioned)
        if user_positioned is not None
        else bool(prev.get("user_positioned"))
    )
    data = _read_json()
    payload: dict[str, Any] = {"user_positioned": positioned}
    if norm_out is not None:
        payload["float_pos_norm"] = [norm_out[0], norm_out[1]]
    if pix_out is not None:
        payload["float_pos_pixels"] = pix_out
    data["qr_overlay"] = payload
    _write_json(data)


_TERMINAL_PING_KEY = "terminal_ping"
_TERMINAL_PING_PRESETS_KEY = "presets"
_TERMINAL_PING_ORDER_KEY = "order"
_TERMINAL_PING_PRESET_MAX = 32
_TERMINAL_PING_BUBBLE_MAX = 5
_PING_NAME_RE = re.compile(r"^[\w][\w \-./()]{0,31}$")


def _terminal_ping_block() -> dict[str, Any]:
    data = _read_json()
    raw = data.get(_TERMINAL_PING_KEY)
    if not isinstance(raw, dict):
        return {_TERMINAL_PING_PRESETS_KEY: {}, _TERMINAL_PING_ORDER_KEY: []}
    presets = raw.get(_TERMINAL_PING_PRESETS_KEY)
    order = raw.get(_TERMINAL_PING_ORDER_KEY)
    if not isinstance(presets, dict):
        presets = {}
    clean_presets: dict[str, str] = {}
    for name, host in presets.items():
        n = str(name).strip()
        h = str(host).strip()
        if n and h:
            clean_presets[n] = h
    if not isinstance(order, list):
        order = []
    clean_order: list[str] = []
    seen: set[str] = set()
    for item in order:
        n = str(item).strip()
        if n in clean_presets and n not in seen:
            clean_order.append(n)
            seen.add(n)
    for n in clean_presets:
        if n not in seen:
            clean_order.append(n)
    return {_TERMINAL_PING_PRESETS_KEY: clean_presets, _TERMINAL_PING_ORDER_KEY: clean_order}


def _write_terminal_ping_block(block: dict[str, Any]) -> None:
    data = _read_json()
    data[_TERMINAL_PING_KEY] = block
    _write_json(data)


def validate_terminal_ping_preset_name(name: str) -> Optional[str]:
    n = str(name or "").strip()
    if not n:
        return "Enter a preset name."
    if len(n) > 32:
        return "Name must be 32 characters or fewer."
    if not _PING_NAME_RE.match(n):
        return "Use letters, numbers, spaces, and - _ . / ( ) only."
    return None


def list_terminal_ping_preset_names() -> list[str]:
    block = _terminal_ping_block()
    return list(block[_TERMINAL_PING_ORDER_KEY])


def terminal_ping_host(preset_name: str) -> Optional[str]:
    block = _terminal_ping_block()
    return block[_TERMINAL_PING_PRESETS_KEY].get(str(preset_name).strip())


def save_terminal_ping_preset(name: str, host: str) -> Optional[str]:
    """Returns error message, or None on success."""
    err = validate_terminal_ping_preset_name(name)
    if err:
        return err
    h = str(host or "").strip()
    if not h:
        return "Enter an IP address or hostname."
    clean_name = str(name).strip()
    block = _terminal_ping_block()
    presets: dict[str, str] = dict(block[_TERMINAL_PING_PRESETS_KEY])
    order: list[str] = list(block[_TERMINAL_PING_ORDER_KEY])
    is_new = clean_name not in presets
    presets[clean_name] = h
    if is_new:
        order.append(clean_name)
    if len(presets) > _TERMINAL_PING_PRESET_MAX:
        return f"At most {_TERMINAL_PING_PRESET_MAX} ping presets."
    block[_TERMINAL_PING_PRESETS_KEY] = presets
    block[_TERMINAL_PING_ORDER_KEY] = order
    _write_terminal_ping_block(block)
    return None


def delete_terminal_ping_preset(name: str) -> bool:
    clean_name = str(name).strip()
    block = _terminal_ping_block()
    presets: dict[str, str] = dict(block[_TERMINAL_PING_PRESETS_KEY])
    if clean_name not in presets:
        return False
    del presets[clean_name]
    order = [n for n in block[_TERMINAL_PING_ORDER_KEY] if n != clean_name]
    block[_TERMINAL_PING_PRESETS_KEY] = presets
    block[_TERMINAL_PING_ORDER_KEY] = order
    _write_terminal_ping_block(block)
    return True


def terminal_ping_bubble_names() -> list[str]:
    return list_terminal_ping_preset_names()[:_TERMINAL_PING_BUBBLE_MAX]
