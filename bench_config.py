"""Load bench_defaults.json for GUI preset and bench scripts."""
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


def load_bench_defaults() -> dict[str, Any]:
    path = Path(__file__).with_name("bench_defaults.json")
    data = dict(_DEFAULTS)
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k: loaded[k] for k in data if k in loaded})
        except (OSError, json.JSONDecodeError):
            pass
    return data
