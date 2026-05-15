"""Load bench_defaults.json for GUI presets and bench scripts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def _load_json() -> dict[str, Any]:
    path = Path(__file__).with_name("bench_defaults.json")
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_bench_defaults() -> dict[str, Any]:
    data = dict(_DEFAULTS)
    loaded = _load_json()
    data.update({k: loaded[k] for k in data if k in loaded})
    return data


def load_production_defaults() -> dict[str, Any]:
    data = dict(_PRODUCTION_DEFAULTS)
    loaded = _load_json()
    prod = loaded.get("production")
    if isinstance(prod, dict):
        data.update({k: prod[k] for k in data if k in prod})
    return data
