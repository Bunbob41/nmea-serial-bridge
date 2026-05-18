"""Survey HUD layout config helpers."""
from __future__ import annotations

import unittest

from ui.survey_hud_layout import (
    HUD_MIN_WINDOW_HEIGHT,
    HUD_MIN_WINDOW_WIDTH,
    default_layout,
    load_layout,
    sanitize_window_geometry,
)


class TestSanitizeWindowGeometry(unittest.TestCase):
    def test_tiny_saved_size_clears_customized(self) -> None:
        cfg = default_layout()
        cfg["window_customized"] = True
        cfg["window_width"] = 150
        cfg["window_height"] = 80
        out = sanitize_window_geometry(cfg)
        self.assertFalse(out["window_customized"])
        self.assertEqual(out["window_width"], 0)

    def test_valid_size_kept(self) -> None:
        cfg = default_layout()
        cfg["window_customized"] = True
        cfg["window_width"] = HUD_MIN_WINDOW_WIDTH
        cfg["window_height"] = HUD_MIN_WINDOW_HEIGHT
        out = sanitize_window_geometry(cfg)
        self.assertTrue(out["window_customized"])
        self.assertEqual(out["window_width"], HUD_MIN_WINDOW_WIDTH)

    def test_load_layout_keeps_box_scale(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from ui import survey_hud_layout as shl

        raw = default_layout()
        raw["box_scale"] = 1.35
        raw["layout_version"] = shl.LAYOUT_VERSION
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "survey_hud_layout.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with patch.object(shl, "CONFIG_PATH", path):
                loaded = load_layout()
        self.assertAlmostEqual(loaded["box_scale"], 1.35)


if __name__ == "__main__":
    unittest.main()
