#!/usr/bin/env python3
"""Build assets/app-icon.ico from assets/app-icon.png (dev + CI)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / "assets" / "app-icon.png"
ICO = ROOT / "assets" / "app-icon.ico"


def main() -> int:
    if not PNG.is_file():
        print(f"[make_app_icon] missing {PNG}")
        return 1
    from PIL import Image

    img = Image.open(PNG).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ICO, sizes=sizes)
    print(f"[make_app_icon] wrote {ICO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
