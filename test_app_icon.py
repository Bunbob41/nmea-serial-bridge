"""App icon asset checks."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICO = ROOT / "assets" / "app-icon.ico"
PNG = ROOT / "assets" / "app-icon.png"


class TestAppIconAssets(unittest.TestCase):
    def test_ico_includes_windows_dpi_sizes(self) -> None:
        from PIL import Image

        self.assertTrue(ICO.is_file(), "run tools/make_app_icon.py")
        img = Image.open(ICO)
        sizes = set(img.info.get("sizes", []))
        for dim in (32, 48, 256):
            self.assertIn((dim, dim), sizes, f"missing {dim}px icon layer")

    def test_png_artwork_fills_canvas(self) -> None:
        from PIL import Image

        self.assertTrue(PNG.is_file())
        img = Image.open(PNG).convert("RGBA")
        bbox = img.getbbox()
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox  # type: ignore[misc]
        fill = min(right - left, bottom - top) / img.size[0]
        self.assertGreaterEqual(fill, 0.72, "glyph should fill most of the squircle")


if __name__ == "__main__":
    unittest.main()
