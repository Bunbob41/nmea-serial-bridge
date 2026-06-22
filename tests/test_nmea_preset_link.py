"""NMEA ↔ preset link and strict start guard."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.nmea_preset_link import (
    describe_nmea_snapshot,
    extract_nmea_snapshot,
    format_nmea_preset_link,
    nmea_snapshot_from_parent,
    strict_checksum_only_start,
)


class TestNmeaPresetLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_extract_strict_types(self) -> None:
        mode, types = extract_nmea_snapshot(
            {"nmea_mode": "strict", "nmea_types": ["GGA", "RMC"]}
        )
        self.assertEqual(mode, "strict")
        self.assertEqual(types, frozenset({"GGA", "RMC"}))

    def test_describe_checksum_only(self) -> None:
        text = describe_nmea_snapshot("strict", frozenset())
        self.assertIn("checksum only", text.lower())

    def test_strict_guard_detects_empty_types(self) -> None:
        win = QtWidgets.QWidget()
        win.rb_nmea_strict = QtWidgets.QRadioButton()
        win.rb_nmea_strict.setChecked(True)
        win.rb_nmea_passthrough = QtWidgets.QRadioButton()
        win.rb_nmea_raw = QtWidgets.QRadioButton()
        win._nmea_type_checks = {
            "GGA": QtWidgets.QCheckBox(),
            "RMC": QtWidgets.QCheckBox(),
        }
        for cb in win._nmea_type_checks.values():
            cb.setChecked(False)

        def _mode() -> str:
            return "strict"

        win._nmea_mode_label = _mode  # type: ignore[method-assign]
        self.assertTrue(strict_checksum_only_start(win))

        win._nmea_type_checks["GGA"].setChecked(True)
        self.assertFalse(strict_checksum_only_start(win))

    def test_format_link_without_preset(self) -> None:
        win = QtWidgets.QWidget()
        win._active_preset_name = None
        win._selected_preset_name = lambda: None  # type: ignore[method-assign]
        win._nmea_mode_label = lambda: "passthrough"  # type: ignore[method-assign]
        win._nmea_type_checks = {}
        line, _tip, kind = format_nmea_preset_link(win)
        self.assertIn("No preset linked", line)
        self.assertEqual(kind, "idle")


class TestModernNmeaPresetIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_modern_nmea_has_preset_buttons(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        self.assertTrue(hasattr(win, "lbl_nmea_preset_link"))
        self.assertTrue(hasattr(win, "btn_nmea_save_preset"))
        self.assertTrue(hasattr(win, "btn_nmea_load_preset"))
        snap = nmea_snapshot_from_parent(win)
        self.assertIn(snap[0], ("passthrough", "strict", "raw"))


if __name__ == "__main__":
    unittest.main()
