"""NMEA mode display labels."""
from __future__ import annotations

import unittest

from ui.nmea_display import nmea_mode_display_label


class TestNmeaDisplay(unittest.TestCase):
    def test_passthrough_short(self) -> None:
        self.assertEqual(nmea_mode_display_label("passthrough"), "PassThru")

    def test_other_modes(self) -> None:
        self.assertEqual(nmea_mode_display_label("strict"), "Strict")
        self.assertEqual(nmea_mode_display_label("raw"), "Raw")


if __name__ == "__main__":
    unittest.main()
