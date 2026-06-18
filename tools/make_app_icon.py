#!/usr/bin/env python3
"""Build assets/app-icon.ico from assets/app-icon.png (dev + CI).

Source art is expected on a flat light/white matte. This script:
  1) flood-fills the outer white from the image edges (keeps white DB-9 pins),
  2) composites the glyph on a dark squircle matching the web/desktop theme,
  3) writes a high-contrast variant for small Windows shell sizes (taskbar),
  4) writes assets/app-icon.png and assets/app-icon.ico.
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
# Shell (16–48px): slightly lifted tile + bright glyph so taskbar/title bar read clearly
SHELL_CANVAS_RGB = (36, 42, 58)  # #242a3a
SHELL_BORDER_RGB = (120, 140, 175)
SHELL_RING_RGB = (148, 163, 184)  # #94a3b8
CANVAS_SIZE = 512
ARTWORK_SCALE_DETAIL = 0.92
# Shell: scale ink (not loose bbox) to fill the tile — thin D-sub lines vanish otherwise
SHELL_INK_FILL = 0.88
SHELL_DILATE_PX = 14
CORNER_RADIUS_RATIO = 0.18
WHITE_KEY_TOLERANCE = 28
INK_ALPHA_MIN = 160
# ICO layers at or below this edge use the shell (high-contrast) master
SHELL_MAX_PX = 48


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


def _luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _remap_art_for_shell(art) -> object:
    """Lift mid/dark connector tones so the logo survives 16–32px shell scaling."""
    from PIL import Image

    out = art.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 24:
                continue
            lum = _luminance(r, g, b)
            if lum >= 200:
                px[x, y] = (255, 255, 255, 255)
            elif lum >= 70:
                px[x, y] = (245, 248, 255, 255)
            else:
                px[x, y] = (255, 255, 255, 255)
    return out


def _ink_bbox(img, *, alpha_min: int = INK_ALPHA_MIN) -> tuple[int, int, int, int] | None:
    """Bounding box of actual connector pixels, not transparent padding in the crop."""
    px = img.convert("RGBA").load()
    w, h = img.size
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        for x in range(w):
            if px[x, y][3] >= alpha_min:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < min_x:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


def _thicken_shell_art(art, *, radius: int) -> object:
    """Bold strokes for taskbar — thin source art otherwise disappears at 16–32px."""
    from PIL import Image, ImageFilter

    if radius <= 0:
        return art
    out = art.copy()
    alpha = out.split()[3]
    for _ in range(radius):
        alpha = alpha.filter(ImageFilter.MaxFilter(3))
    out.putalpha(alpha)
    rgb = Image.new("RGBA", out.size, (255, 255, 255, 0))
    rgb.paste(out, (0, 0), alpha)
    return _remap_art_for_shell(rgb)


def _prepare_artwork(src, *, shell: bool):
    from PIL import Image

    rgba = src.convert("RGBA")
    _flood_clear_border_white(rgba)
    bbox = rgba.getbbox()
    if not bbox:
        return None
    cropped = rgba.crop(bbox)
    if shell:
        ink = _ink_bbox(cropped)
        if ink is not None:
            cropped = cropped.crop(ink)
        cropped = _thicken_shell_art(cropped, radius=SHELL_DILATE_PX)
    return cropped


def _compose_icon(source, *, shell: bool = False) -> object:
    from PIL import Image, ImageDraw

    size = CANVAS_SIZE
    canvas_rgb = SHELL_CANVAS_RGB if shell else CANVAS_RGB
    border_rgb = SHELL_BORDER_RGB if shell else BORDER_RGB
    canvas = Image.new("RGBA", (size, size), (*canvas_rgb, 255))
    radius = max(8, int(size * CORNER_RADIUS_RATIO))
    mask = _rounded_mask(size, radius)

    border = Image.new("RGBA", (size, size), 0)
    draw = ImageDraw.Draw(border)
    outline_w = max(2, size // 128) if shell else 2
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius,
        outline=(*border_rgb, 220 if shell else 180),
        width=outline_w,
    )
    canvas = Image.composite(border, canvas, border.split()[3])

    if shell:
        ring = Image.new("RGBA", (size, size), 0)
        ImageDraw.Draw(ring).rounded_rectangle(
            (2, 2, size - 3, size - 3),
            radius=max(6, radius - 2),
            outline=(*SHELL_RING_RGB, 140),
            width=max(2, size // 64),
        )
        canvas = Image.alpha_composite(canvas, ring)

    cropped = _prepare_artwork(source, shell=shell)
    if cropped is not None:
        if shell:
            pad = int(size * (1.0 - SHELL_INK_FILL) / 2)
            target = size - 2 * pad
        else:
            pad = int(size * (1.0 - ARTWORK_SCALE_DETAIL) / 2)
            target = size - 2 * pad
        cw, ch = cropped.size
        scale = min(target / cw, target / ch)
        nw = max(1, int(cw * scale))
        nh = max(1, int(ch * scale))
        resample = Image.Resampling.NEAREST if shell else Image.Resampling.LANCZOS
        art = cropped.resize((nw, nh), resample)
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


def _ico_layers(detail, shell) -> tuple[list, list[tuple[int, int]]]:
    from PIL import Image

    sizes = [
        (16, 16),
        (20, 20),
        (24, 24),
        (32, 32),
        (40, 40),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ]
    layers: list = []
    for dim in sizes:
        master = shell if dim[0] <= SHELL_MAX_PX else detail
        resample = Image.Resampling.NEAREST if dim[0] <= SHELL_MAX_PX else Image.Resampling.LANCZOS
        layers.append(master.resize(dim, resample))
    return layers, sizes


def _save_ico(path: Path, layers: list, sizes: list[tuple[int, int]]) -> None:
    """Write multi-size ICO (Pillow: primary frame should be the largest)."""
    order = sorted(range(len(layers)), key=lambda i: layers[i].size[0], reverse=True)
    primary = layers[order[0]]
    rest = [layers[i] for i in order[1:]]
    ordered_sizes = [sizes[i] for i in order]
    primary.save(
        path,
        format="ICO",
        sizes=ordered_sizes,
        append_images=rest,
    )


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
    detail = _compose_icon(src, shell=False)
    shell = _compose_icon(src, shell=True)
    detail.save(PNG, optimize=True)
    layers, sizes = _ico_layers(detail, shell)
    _save_ico(ICO, layers, sizes)
    note = "from app-icon-source.png" if src_path == SOURCE else "from app-icon.png"
    print(
        f"[make_app_icon] wrote {PNG} and {ICO} "
        f"(detail + shell<={SHELL_MAX_PX}px, {note})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
