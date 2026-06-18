#!/usr/bin/env python3
"""Build assets/app-icon.ico from assets/app-icon-source.png (dev + CI).

Source art is expected on a flat light/white matte. This script:
  1) flood-fills the outer white from the image edges (keeps white DB-9 pins),
  2) composites the glyph on a dark squircle matching the web/desktop theme,
  3) writes assets/app-icon.png and a multi-size Windows ICO (detail master only).
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "app-icon-source.png"
PNG = ROOT / "assets" / "app-icon.png"
ICO = ROOT / "assets" / "app-icon.ico"

# Match web dashboard --bg-card / Connect chrome
CANVAS_RGB = (26, 29, 39)  # #1a1d27
BORDER_RGB = (51, 65, 85)  # #334155 subtle edge
CANVAS_SIZE = 512
ARTWORK_SCALE = 0.92
CORNER_RADIUS_RATIO = 0.18
WHITE_KEY_TOLERANCE = 28

ICO_SIZES: tuple[tuple[int, int], ...] = (
    (16, 16),
    (20, 20),
    (24, 24),
    (32, 32),
    (40, 40),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
)


def _is_key_color(r: int, g: int, b: int, a: int, tol: int) -> bool:
    if a < 16:
        return True
    return r >= 255 - tol and g >= 255 - tol and b >= 255 - tol


def _flood_clear_border_white(img) -> None:
    """Turn outer white matte transparent; interior white pins stay opaque."""
    w, h = img.size
    px = img.load()
    tol = WHITE_KEY_TOLERANCE
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    def try_seed(x: int, y: int) -> None:
        if (x, y) in seen:
            return
        r, g, b, a = px[x, y]
        if _is_key_color(r, g, b, a, tol):
            seen.add((x, y))
            q.append((x, y))

    for x in range(w):
        try_seed(x, 0)
        try_seed(x, h - 1)
    for y in range(h):
        try_seed(0, y)
        try_seed(w - 1, y)

    while q:
        x, y = q.popleft()
        r, g, b, _a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                continue
            if (nx, ny) in seen:
                continue
            r2, g2, b2, a2 = px[nx, ny]
            if _is_key_color(r2, g2, b2, a2, tol):
                seen.add((nx, ny))
                q.append((nx, ny))


def _rounded_mask(size: int, radius: int):
    from PIL import Image, ImageDraw

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _prepare_artwork(src):
    from PIL import Image

    rgba = src.convert("RGBA")
    _flood_clear_border_white(rgba)
    bbox = rgba.getbbox()
    if not bbox:
        return None
    return rgba.crop(bbox)


def _compose_icon(source) -> object:
    from PIL import Image, ImageDraw

    size = CANVAS_SIZE
    canvas = Image.new("RGBA", (size, size), (*CANVAS_RGB, 255))
    radius = max(8, int(size * CORNER_RADIUS_RATIO))
    mask = _rounded_mask(size, radius)

    border = Image.new("RGBA", (size, size), 0)
    ImageDraw.Draw(border).rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius,
        outline=(*BORDER_RGB, 180),
        width=2,
    )
    canvas = Image.composite(border, canvas, border.split()[3])

    cropped = _prepare_artwork(source)
    if cropped is not None:
        pad = int(size * (1.0 - ARTWORK_SCALE) / 2)
        target = size - 2 * pad
        cw, ch = cropped.size
        scale = min(target / cw, target / ch)
        nw = max(1, int(cw * scale))
        nh = max(1, int(ch * scale))
        art = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
        ox = (size - nw) // 2
        oy = (size - nh) // 2
        canvas.alpha_composite(art, (ox, oy))

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), mask)
    return out


def _input_path() -> Path:
    if SOURCE.is_file():
        return SOURCE
    return PNG


def _save_ico(path: Path, master) -> None:
    """Write Windows-compatible multi-size ICO (BMP frames for shell/taskbar)."""
    from PIL import Image

    base = master.resize((256, 256), Image.Resampling.LANCZOS).convert("RGBA")
    # PNG-compressed ICO entries break Windows taskbar embedding (white placeholder).
    base.save(path, format="ICO", sizes=list(ICO_SIZES), bitmap_format="bmp")


def main() -> int:
    src_path = _input_path()
    if not src_path.is_file():
        print(
            f"[make_app_icon] missing {SOURCE} — add your connector art on a white/transparent matte "
            f"(see assets/README.md)"
        )
        return 1
    from PIL import Image

    src = Image.open(src_path)
    detail = _compose_icon(src)
    detail.save(PNG, optimize=True)
    _save_ico(ICO, detail)
    note = "from app-icon-source.png" if src_path == SOURCE else "from app-icon.png"
    print(f"[make_app_icon] wrote {PNG} and {ICO} (dark squircle BMP ICO, {note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
