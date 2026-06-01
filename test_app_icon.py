"""App icon asset checks."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICO = ROOT / "assets" / "app-icon.ico"
PNG = ROOT / "assets" / "app-icon.png"


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

    def test_32px_shell_layer_has_bright_glyph(self) -> None:
        """Taskbar uses small ICO layers — shell tier must not be dark-on-dark."""
        from PIL import Image

        with Image.open(ICO) as img:
            self.assertIn((32, 32), set(img.info.get("sizes", [])))
            img.size = (32, 32)  # type: ignore[method-assign]
            small = img.copy().convert("RGBA")
        w, h = small.size
        bright = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a < 80:
                    continue
                if r + g + b > 420:
                    bright += 1
        self.assertGreater(bright, 40, "32px layer should show a bold light logo, not a speck")
        ink = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = small.getpixel((x, y))
                if a >= 200 and r + g + b > 500:
                    ink += 1
        self.assertGreater(ink, 80, "32px connector should cover a solid region of pixels")

    def test_ico_includes_windows_dpi_sizes(self) -> None:
        from PIL import Image

        self.assertTrue(ICO.is_file(), "run tools/make_app_icon.py")
        with Image.open(ICO) as img:
            sizes = set(img.info.get("sizes", []))
        for dim in (32, 48, 256):
            self.assertIn((dim, dim), sizes, f"missing {dim}px icon layer")


if __name__ == "__main__":
    unittest.main()
