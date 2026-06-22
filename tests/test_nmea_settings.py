"""Modern NMEA settings page."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.modern import BridgeWindowModern


class TestModernNmeaSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_nmea_summary_defaults_passthrough(self) -> None:
        win = BridgeWindowModern()
        win.rb_nmea_passthrough.setChecked(True)
        win._sync_nmea_mode_ui()
        lbl = win.lbl_nmea_config_summary
        self.assertIn("Passthrough", lbl.text())
        self.assertEqual(lbl.property("summaryKind"), "ok")

    def test_survey_preset_enables_strict_and_types(self) -> None:
        win = BridgeWindowModern()
        win.rb_nmea_passthrough.setChecked(True)
        win._sync_nmea_mode_ui()
        from ui.nmea_settings import _apply_strict_types, _SURVEY_TYPES

        _apply_strict_types(win, _SURVEY_TYPES)
        self.assertTrue(win.rb_nmea_strict.isChecked())
        self.assertEqual(win.lbl_nmea_config_summary.property("summaryKind"), "strict")
        for st in ("GGA", "RMC", "ZDA"):
            self.assertTrue(win._nmea_type_checks[st].isChecked())
        self.assertIn("GGA", win.lbl_nmea_config_summary.text())

    def test_type_toggle_auto_selects_strict(self) -> None:
        win = BridgeWindowModern()
        win.rb_nmea_passthrough.setChecked(True)
        win._sync_nmea_mode_ui()
        win._nmea_type_checks["VTG"].setChecked(True)
        win._sync_nmea_mode_ui()
        self.assertTrue(win.rb_nmea_strict.isChecked())
        self.assertIn("VTG", win.lbl_nmea_config_summary.text())

    def test_checksum_only_strict_shows_warn_summary(self) -> None:
        win = BridgeWindowModern()
        from ui.nmea_settings import _apply_strict_types

        _apply_strict_types(win, frozenset())
        self.assertTrue(win.rb_nmea_strict.isChecked())
        self.assertEqual(win.lbl_nmea_config_summary.property("summaryKind"), "warn")


if __name__ == "__main__":
    unittest.main()
