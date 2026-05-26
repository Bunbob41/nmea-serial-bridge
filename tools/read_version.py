"""Read __version__ from version.py (for static asset cache bust)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_app_version() -> str:
    text = (ROOT / "version.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not m:
        raise RuntimeError("Could not read __version__ from version.py")
    return m.group(1)
