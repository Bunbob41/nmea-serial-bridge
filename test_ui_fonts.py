"""Monospace font selection (Windows legacy OEM faces)."""
from __future__ import annotations

import unittest

from ui.qt_test_harness import ensure_qt_app
from ui.fonts import monospace_ui_font


class TestUiFonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_qt_app()

    def test_monospace_uses_maple_mono_when_bundled(self) -> None:
        from ui.fonts import PRIMARY_FONT_FAMILY, ensure_bundled_fonts

        ensure_bundled_fonts()
        font = monospace_ui_font()
        self.assertEqual(font.family(), PRIMARY_FONT_FAMILY)

    def test_monospace_avoids_legacy_oem_family(self) -> None:
        font = monospace_ui_font()
        self.assertNotIn(font.family().lower(), {"8514oem", "terminal", "fixedsys"})

    def test_monospace_respects_point_size(self) -> None:
        font = monospace_ui_font(point_size=11)
        self.assertGreaterEqual(font.pointSize(), 9)


if __name__ == "__main__":
    unittest.main()
