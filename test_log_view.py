"""Live log view presets and line filtering."""
from __future__ import annotations

import unittest

from ui.log_view import (
    PRESET_OPS,
    PRESET_SURVEY,
    PRESET_WARN,
    LogViewState,
    log_line_allowed,
    state_from_preset,
)


class TestLogView(unittest.TestCase):
    def test_survey_preset_allows_gga_rmc_not_zda(self) -> None:
        st = state_from_preset(PRESET_SURVEY)
        gga = "UDP← | $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        rmc = "UDP← | $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        zda = "UDP← | $GPZDA,123519,12,01,1990,00,00*68"
        self.assertTrue(log_line_allowed(gga, st))
        self.assertTrue(log_line_allowed(rmc, st))
        self.assertFalse(log_line_allowed(zda, st))

    def test_warn_only_shows_drops(self) -> None:
        st = state_from_preset(PRESET_WARN)
        self.assertTrue(log_line_allowed("[DROP net→com] queue full", st))
        self.assertFalse(log_line_allowed("UDP← | $GPGGA,123", st))

    def test_ops_allows_ui_events(self) -> None:
        st = state_from_preset(PRESET_OPS)
        self.assertTrue(log_line_allowed("=== BRIDGE RUNNING ===", st))
        self.assertFalse(st.verbose)

    def test_sentence_filter_when_verbose(self) -> None:
        st = LogViewState(verbose=True, sentence_types=frozenset({"GGA"}))
        rmc = "UDP← | $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        self.assertFalse(log_line_allowed(rmc, st))

    def test_legacy_sentence_migration(self) -> None:
        st = LogViewState.from_dict({"log_sentence": "GGA", "verbose": True})
        self.assertIn("GGA", st.sentence_types)

    def test_detect_preset_roundtrip(self) -> None:
        st = state_from_preset(PRESET_OPS)
        self.assertEqual(st.detect_preset(), PRESET_OPS)


if __name__ == "__main__":
    unittest.main()
