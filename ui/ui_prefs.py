"""Persisted lightweight UI preferences."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        if text == "Send":
            text = "Terminal"
        out.append(text)
    return out


def save_tab_order(ui_mode: str, key: str, order: list[str]) -> None:
    clean = [str(x).strip() for x in order if str(x).strip()]
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
        if text:
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
    if backups not in (3, 5, 10):
        backups = 5
    return {"max_mb": max_mb, "backups": backups}


def save_file_log_prefs(max_mb: int, backups: int) -> None:
    data = _read_json()
    data["file_log"] = {"max_mb": int(max_mb), "backups": int(backups)}
    _write_json(data)


def load_ntrip_prefs() -> dict[str, str | bool]:
    data = _read_json()
    raw = data.get("ntrip")
    if not isinstance(raw, dict):
        return {
            "enabled": False,
            "caster": "",
            "mountpoint": "",
            "username": "",
            "password": "",
        }
    return {
        "enabled": bool(raw.get("enabled", False)),
        "caster": str(raw.get("caster", "")).strip(),
        "mountpoint": str(raw.get("mountpoint", "")).strip(),
        "username": str(raw.get("username", "")).strip(),
        "password": str(raw.get("password", "")),
    }


_CONNECT_PANEL_DEFAULT_ORDER = [
    "run",
    "hint",
    "quick_log",
    "quick_terminal",
    "connection",
    "ntrip",
]
_CONNECT_TOOLBAR_DEFAULT_ORDER = [
    "ui_editor",
    "expand_all",
    "collapse_all",
    "reset_sizes",
]


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
        }
    raw = raw_all.get(ui_mode)
    if not isinstance(raw, dict):
        return {
            "order": list(_CONNECT_PANEL_DEFAULT_ORDER),
            "collapsed": {},
            "sizes": {},
            "hidden": [],
            "toolbar_order": list(_CONNECT_TOOLBAR_DEFAULT_ORDER),
        }
    order_raw = raw.get("order")
    order = [str(x).strip() for x in order_raw] if isinstance(order_raw, list) else []
    if not order:
        order = list(_CONNECT_PANEL_DEFAULT_ORDER)
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
        hidden = [str(x).strip() for x in hidden_raw if str(x).strip()]
    toolbar_raw = raw.get("toolbar_order")
    toolbar_order = (
        [str(x).strip() for x in toolbar_raw if str(x).strip()]
        if isinstance(toolbar_raw, list)
        else list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
    )
    if not toolbar_order:
        toolbar_order = list(_CONNECT_TOOLBAR_DEFAULT_ORDER)
    return {
        "order": order,
        "collapsed": collapsed,
        "sizes": sizes,
        "hidden": hidden,
        "toolbar_order": toolbar_order,
    }


def save_connect_panel_prefs(
    ui_mode: str,
    order: list[str],
    collapsed: dict[str, bool],
    *,
    sizes: dict[str, int] | None = None,
    hidden: list[str] | None = None,
    toolbar_order: list[str] | None = None,
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
    raw_all[ui_mode] = {
        "order": [str(x).strip() for x in order if str(x).strip()],
        "collapsed": {str(k).strip(): bool(v) for k, v in collapsed.items() if str(k).strip()},
        "sizes": size_out,
        "hidden": hidden_out,
        "toolbar_order": toolbar_out,
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


def save_ntrip_prefs(prefs: dict[str, str | bool]) -> None:
    data = _read_json()
    data["ntrip"] = {
        "enabled": bool(prefs.get("enabled", False)),
        "caster": str(prefs.get("caster", "")).strip(),
        "mountpoint": str(prefs.get("mountpoint", "")).strip(),
        "username": str(prefs.get("username", "")).strip(),
        "password": str(prefs.get("password", "")),
    }
    _write_json(data)
