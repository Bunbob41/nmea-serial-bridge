"""Global QR overlay preference helpers."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ui.ui_prefs as ui_prefs


class TestQrOverlayPrefs(unittest.TestCase):
    def test_save_and_load_normalized_position(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with mock.patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_qr_overlay_prefs(
                    float_pos_norm=(0.5, 0.42),
                    user_positioned=True,
                )
                prefs = ui_prefs.load_qr_overlay_prefs()
                self.assertEqual(prefs.get("float_pos_norm"), (0.5, 0.42))
                self.assertTrue(prefs.get("user_positioned"))

    def test_migrate_from_connect_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            path.write_text(
                json.dumps(
                    {
                        "connect_panels": {
                            "field": {"qr_float_pos": [400, 220]},
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(ui_prefs, "CONFIG_PATH", path):
                prefs = ui_prefs.load_qr_overlay_prefs()
                self.assertEqual(prefs.get("float_pos_pixels"), [400, 220])
                self.assertTrue(prefs.get("user_positioned"))


if __name__ == "__main__":
    unittest.main()
