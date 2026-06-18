"""Load and save named connection presets (built-ins + path_presets.json)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

_DEFAULTS: dict[str, Any] = {
    "com": "COM7",
    "baud": 115200,
    "udp_host": "0.0.0.0",
    "udp_port": 10110,
}

_PRODUCTION_DEFAULTS: dict[str, Any] = {
    "com": "COM3",
    "baud": 115200,
    "udp_host": "0.0.0.0",
    "udp_port": 10110,
    "pc_ip": "192.168.1.10",
    "subnet_mask": "255.255.255.0",
    "ins_ip": "192.168.1.20",
    "notes": "",
}

USER_PRESETS_PATH = Path.home() / ".cursor-udp-com-bridge" / "path_presets.json"

_PRESET_KEYS = (
    "com",
    "baud",
    "udp_host",
    "udp_port",
    "pc_ip",
    "subnet_mask",
    "ins_ip",
    "notes",
    "nmea_mode",
    "nmea_types",
    "udp_fanout",
)
_VALID_NMEA_MODES = frozenset({"passthrough", "strict", "raw"})
_LEGACY_DESK = ("desk", "bench")
_LEGACY_BOAT = ("boat", "production")
_BUILTIN_DESK = "Desk test"
_BUILTIN_BOAT = "Boat / INS"
_BUILTIN_NORBIT = "NORBIT DCT"
_BUILTIN_CUBE = "Cube MAVLink"
_BUILTIN_CUBE_GPS = "Cube GPS UART"
_NAME_RE = re.compile(r"^[\w][\w \-./()]{0,47}$")
_PRESET_ORDER_KEY = "preset_order"


def user_presets_path() -> Path:
    return USER_PRESETS_PATH


def _bench_defaults_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        roots.append(Path(sys.executable).resolve().parent)
    roots.append(Path(__file__).resolve().parent)
    return roots


def _bench_defaults_paths() -> list[Path]:
    """Load order: base JSON per root, then optional local override (not shipped in releases)."""
    paths: list[Path] = []
    for root in _bench_defaults_roots():
        paths.append(root / "bench_defaults.json")
        paths.append(root / "bench_defaults.local.json")
    return paths


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _load_merged_bench_json() -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in _bench_defaults_paths():
        merged.update(_load_json_file(path))
    return merged


def _load_user_file() -> dict[str, Any]:
    raw = _load_json_file(USER_PRESETS_PATH)
    return raw if isinstance(raw, dict) else {}


def _write_user_file(data: dict[str, Any]) -> Path:
    USER_PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_PRESETS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return USER_PRESETS_PATH


def _normalize_nmea_fields(data: dict[str, Any]) -> dict[str, Any]:
    from nmea_codec import NMEA_SENTENCE_TYPES

    mode = str(data.get("nmea_mode", "passthrough")).strip().lower()
    if mode not in _VALID_NMEA_MODES:
        mode = "passthrough"
    out: dict[str, Any] = {"nmea_mode": mode}
    raw_types = data.get("nmea_types")
    if isinstance(raw_types, list):
        allowed = set(NMEA_SENTENCE_TYPES)
        types = sorted(
            {
                str(t).strip().upper()
                for t in raw_types
                if str(t).strip().upper() in allowed
            }
        )
        if types:
            out["nmea_types"] = types
    return out


def _normalize_desk(data: dict[str, Any]) -> dict[str, Any]:
    base = {
        "com": str(data.get("com", "")).strip(),
        "baud": int(data.get("baud", 115200)),
        "udp_host": str(data.get("udp_host", "0.0.0.0")).strip() or "0.0.0.0",
        "udp_port": int(data.get("udp_port", 10110)),
        "udp_fanout": bool(data["udp_fanout"]) if "udp_fanout" in data else True,
    }
    base.update(_normalize_nmea_fields(data))
    return base


def _normalize_boat(data: dict[str, Any]) -> dict[str, Any]:
    out = _normalize_desk(data)
    out.update(
        {
            "pc_ip": str(data.get("pc_ip", "192.168.1.10")).strip() or "192.168.1.10",
            "subnet_mask": str(data.get("subnet_mask", "255.255.255.0")).strip()
            or "255.255.255.0",
            "ins_ip": str(data.get("ins_ip", "192.168.1.20")).strip() or "192.168.1.20",
            "notes": str(data.get("notes", "")).strip(),
        }
    )
    return out


def normalize_preset(data: dict[str, Any], *, boat_style: bool = False) -> dict[str, Any]:
    if boat_style or any(data.get(k) for k in ("pc_ip", "ins_ip", "subnet_mask", "notes")):
        return _normalize_boat(data)
    return _normalize_desk(data)


def validate_preset_name(name: str) -> Optional[str]:
    n = name.strip()
    if not n:
        return "Enter a preset name."
    if len(n) > 48:
        return "Name must be 48 characters or fewer."
    if not _NAME_RE.match(n):
        return "Use letters, numbers, spaces, and - _ . / ( ) only."
    return None


def _builtin_presets() -> dict[str, dict[str, Any]]:
    merged = _load_merged_bench_json()
    desk = _normalize_desk({**_DEFAULTS, **{k: merged[k] for k in _DEFAULTS if k in merged}})
    boat = _normalize_boat(_PRODUCTION_DEFAULTS)
    prod = merged.get("production")
    if isinstance(prod, dict):
        boat = _normalize_boat({**boat, **prod})
    norbit_block = merged.get("norbit_dct")
    if not isinstance(norbit_block, dict):
        norbit_block = {}
    norbit = _normalize_boat(
        {
            **boat,
            **{k: norbit_block[k] for k in _PRESET_KEYS if k in norbit_block},
            "pc_ip": str(norbit_block.get("pc_ip", "192.168.1.10")).strip() or "192.168.1.10",
            "ins_ip": str(norbit_block.get("ins_ip", "192.168.1.20")).strip() or "192.168.1.20",
            "notes": str(norbit_block.get("notes") or "").strip()
            or (
                "DCT / high-rate workflow: listen on udp_port (often 40810). "
                "Set pc_ip to this PC's IPv4; point DCT/INS UDP output at pc_ip:udp_port. "
                "See docs/NORBIT_DCT.md."
            ),
        }
    )
    cube_block = merged.get("cube_mavlink")
    if not isinstance(cube_block, dict):
        cube_block = {}
    cube = _normalize_desk(
        {
            **desk,
            **{k: cube_block[k] for k in _PRESET_KEYS if k in cube_block},
            "com": str(cube_block.get("com", "COM9")).strip() or "COM9",
            "baud": int(cube_block.get("baud", 115200)),
            "udp_port": int(cube_block.get("udp_port", 14550)),
            "nmea_mode": "raw",
            "notes": str(cube_block.get("notes") or "").strip()
            or (
                "Cube Orange MAVLink: Raw binary, UDP listen 14550. "
                "Mission Planner → UDP Client 127.0.0.1:14550. See docs/OPERATOR_GUIDE.md §5.6."
            ),
        }
    )
    cube_gps_block = merged.get("cube_gps_uart")
    if not isinstance(cube_gps_block, dict):
        cube_gps_block = {}
    cube_gps = _normalize_desk(
        {
            **desk,
            **{k: cube_gps_block[k] for k in _PRESET_KEYS if k in cube_gps_block},
            "com": str(cube_gps_block.get("com", "COM10")).strip() or "COM10",
            "baud": int(cube_gps_block.get("baud", 38400)),
            "udp_port": int(cube_gps_block.get("udp_port", 10110)),
            "nmea_mode": "passthrough",
            "udp_fanout": bool(cube_gps_block.get("udp_fanout", False)),
            "notes": str(cube_gps_block.get("notes") or "").strip()
            or (
                "GPS injection via dedicated Cube UART (Telem2/Serial4). "
                "ArduPilot params: SERIALx_PROTOCOL=5, SERIALx_BAUD=38, GPS_TYPE2=5. "
                "NMEA sim sends UDP → bridge forwards NMEA over UART → ArduPilot treats "
                "it as a secondary GPS source. "
                "Run a second Serial Link instance for MAVLink relay on the USB port."
            ),
        }
    )

    return {
        _BUILTIN_DESK: desk,
        _BUILTIN_BOAT: boat,
        _BUILTIN_NORBIT: norbit,
        _BUILTIN_CUBE: cube,
        _BUILTIN_CUBE_GPS: cube_gps,
    }


def _migrate_legacy_into_presets(raw: dict[str, Any], presets: dict[str, dict[str, Any]]) -> None:
    for legacy_key, builtin_name, boat in (
        (_LEGACY_DESK, _BUILTIN_DESK, False),
        (_LEGACY_BOAT, _BUILTIN_BOAT, True),
    ):
        block = raw.get(legacy_key[0])
        if not isinstance(block, dict):
            for alt in legacy_key[1:]:
                block = raw.get(alt)
                if isinstance(block, dict):
                    break
        if isinstance(block, dict):
            presets[builtin_name] = normalize_preset(block, boat_style=boat)


def _load_presets_map() -> dict[str, dict[str, Any]]:
    raw = _load_user_file()
    presets: dict[str, dict[str, Any]] = {}
    _migrate_legacy_into_presets(raw, presets)
    presets_raw = raw.get("presets")
    if isinstance(presets_raw, dict):
        for name, body in presets_raw.items():
            if isinstance(name, str) and isinstance(body, dict):
                presets[name.strip()] = normalize_preset(
                    body, boat_style=bool(body.get("pc_ip") or body.get("ins_ip"))
                )
    if not presets:
        presets = dict(_builtin_presets())
    else:
        for name, body in _builtin_presets().items():
            presets.setdefault(name, body)
    return presets


def _preset_order(raw: dict[str, Any], presets: dict[str, dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    raw_order = raw.get(_PRESET_ORDER_KEY)
    if isinstance(raw_order, list):
        for name in raw_order:
            clean = str(name).strip()
            if clean and clean in presets and clean not in seen:
                out.append(clean)
                seen.add(clean)
    for name in sorted(presets.keys(), key=str.lower):
        if name not in seen:
            out.append(name)
    return out


def list_preset_names() -> list[str]:
    raw = _load_user_file()
    presets = _load_presets_map()
    return _preset_order(raw, presets)


def load_preset(name: str) -> dict[str, Any]:
    presets = _load_presets_map()
    key = name.strip()
    if key in presets:
        return dict(presets[key])
    lower = {k.lower(): k for k in presets}
    hit = lower.get(key.lower())
    if hit:
        return dict(presets[hit])
    builtins = _builtin_presets()
    if key in builtins:
        return dict(builtins[key])
    raise KeyError(name)


def save_preset(name: str, data: dict[str, Any], *, boat_style: bool = False) -> Path:
    err = validate_preset_name(name)
    if err:
        raise ValueError(err)
    clean = normalize_preset(data, boat_style=boat_style)
    raw = _load_user_file()
    presets = _load_presets_map()
    clean_name = name.strip()
    is_new = clean_name not in presets
    presets[clean_name] = clean
    order = _preset_order(raw, presets)
    if is_new and clean_name not in order:
        order.append(clean_name)
    raw["presets"] = presets
    raw[_PRESET_ORDER_KEY] = order
    raw["last_preset"] = clean_name
    return _write_user_file(raw)


def delete_preset(name: str) -> bool:
    presets = _load_presets_map()
    key = name.strip()
    if key not in presets:
        lower = {k.lower(): k for k in presets}
        key = lower.get(key.lower(), key)
    if key not in presets or len(presets) <= 1:
        return False
    del presets[key]
    raw = _load_user_file()
    raw["presets"] = presets
    raw[_PRESET_ORDER_KEY] = [n for n in _preset_order(raw, presets) if n != key]
    if raw.get("last_preset") == key:
        raw["last_preset"] = next(iter(_preset_order(raw, presets)))
    _write_user_file(raw)
    return True


def reorder_preset_names(ordered_names: list[str]) -> bool:
    raw = _load_user_file()
    presets = _load_presets_map()
    if not presets:
        return False
    clean = [str(n).strip() for n in ordered_names if str(n).strip()]
    seen: set[str] = set()
    out: list[str] = []
    for name in clean:
        if name in presets and name not in seen:
            out.append(name)
            seen.add(name)
    for name in _preset_order(raw, presets):
        if name not in seen:
            out.append(name)
    raw["presets"] = presets
    raw[_PRESET_ORDER_KEY] = out
    _write_user_file(raw)
    return True


def last_preset_name() -> str:
    raw = _load_user_file()
    last = str(raw.get("last_preset", "")).strip()
    names = list_preset_names()
    if last and last in names:
        return last
    if _BUILTIN_DESK in names:
        return _BUILTIN_DESK
    return names[0] if names else _BUILTIN_DESK


def set_last_preset(name: str) -> None:
    raw = _load_user_file()
    raw["last_preset"] = name.strip()
    _write_user_file(raw)


def _find_preset_name(*hints: str) -> str:
    names = list_preset_names()
    for hint in hints:
        h = hint.lower()
        for n in names:
            if h in n.lower():
                return n
    return names[0] if names else _BUILTIN_DESK


def desk_udp_send_host(data: dict[str, Any] | None = None) -> str:
    d = data if data is not None else load_bench_defaults()
    bind_host = str(d.get("udp_host", "0.0.0.0"))
    return "127.0.0.1" if bind_host in ("0.0.0.0", "", "*") else bind_host


def load_bench_defaults() -> dict[str, Any]:
    return load_preset(_find_preset_name("desk", "bench", "com0com"))


def load_production_defaults() -> dict[str, Any]:
    return load_preset(_find_preset_name("boat", "ins", "production"))


def save_desk_preset(data: dict[str, Any]) -> Path:
    return save_preset(_BUILTIN_DESK, data, boat_style=False)


def save_boat_preset(data: dict[str, Any]) -> Path:
    return save_preset(_BUILTIN_BOAT, data, boat_style=True)
