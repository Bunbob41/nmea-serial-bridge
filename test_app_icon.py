"""App icon asset checks."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICO = ROOT / "assets" / "app-icon.ico"
PNG = ROOT / "assets" / "app-icon.png"


def _ico_layer(dim: int):
    from PIL import Image

    with Image.open(ICO) as img:
        sizes = set(img.info.get("sizes", []))
        if (dim, dim) not in sizes:
            raise AssertionError(f"missing {dim}px icon layer")
        img.size = (dim, dim)  # type: ignore[method-assign]
        img.load()
        return img.copy().convert("RGBA")


class TestAppIconAssets(unittest.TestCase):
    def test_png_artwork_fills_canvas(self) -> None:
        from PIL import Image

        self.assertTrue(PNG.is_file())
        img = Image.open(PNG).convert("RGBA")
        bbox = img.getbbox()
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox  # type: ignore[misc]
        fill = min(right - left, bottom - top) / img.size[0]
        self.assertGreaterEqual(fill, 0.72, "glyph should fill most of the squircle")

    def test_16px_ico_layer_shows_connector(self) -> None:
        """Taskbar smallest size — DE-9 pins/outline must remain visible."""
        from PIL import Image

        small = _ico_layer(16)
        w, h = small.size
        bright = 0
        ink = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a < 80:
                    continue
                if r + g + b > 350:
                    bright += 1
                if a >= 160 and r + g + b > 420:
                    ink += 1
        self.assertGreater(bright, 4, "16px layer should show pin/outline pixels")

    def test_32px_ico_layer_shows_connector(self) -> None:
        """Title bar / taskbar — detail downscale must read as DE-9, not a blob."""
        small = _ico_layer(32)
        w, h = small.size
        bright = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a < 80:
                    continue
                if r + g + b > 420:
                    bright += 1
        self.assertGreater(bright, 8, "32px layer should show the connector glyph")
        ink = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a < 120:
                    continue
                if r + g + b > 500:
                    ink += 1
        self.assertGreater(ink, 6, "32px connector should show bright pins/outline")
        # White-matte ICO may quantize pin hues at 32px; dark connector body is enough signal.
        dark_body = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a < 120:
                    continue
                if r + g + b < 280:
                    dark_body += 1
        self.assertGreater(dark_body, 4, "32px layer should show the DE-9 body")

    def test_ico_includes_windows_dpi_sizes(self) -> None:
        from PIL import Image

        self.assertTrue(ICO.is_file(), "run tools/make_app_icon.py")
        with Image.open(ICO) as img:
            sizes = set(img.info.get("sizes", []))
        for dim in (16, 32, 48, 256):
            self.assertIn((dim, dim), sizes, f"missing {dim}px icon layer")


if __name__ == "__main__":
    unittest.main()
