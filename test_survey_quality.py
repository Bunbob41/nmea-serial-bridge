"""Survey GNSS quality assessment from NMEA GGA (POSPac-style thresholds)."""
from __future__ import annotations

import time
import unittest

from survey_quality import (
    GGA_FIX_LABELS,
    NavQualityLevel,
    assess_navigation_quality,
    format_gnss_stats_segment,
    format_gnss_status_chip,
    nav_quality_stale,
    parse_gga_fields,
    update_nav_quality_from_line,
)

_SAMPLE_RTK = (
    "$GPGGA,123519,4807.038,N,01131.000,E,4,12,0.9,545.4,M,46.9,M,,*6A"
)
_SAMPLE_WEAK = (
    "$GPGGA,123519,4807.038,N,01131.000,E,1,04,3.8,545.4,M,46.9,M,,*47"
)


class SurveyQualityTests(unittest.TestCase):
    def test_parse_gga_fields(self) -> None:
        f = parse_gga_fields(_SAMPLE_RTK)
        assert f is not None
        self.assertEqual(f.quality, 4)
        self.assertEqual(f.num_sats, 12)
        self.assertAlmostEqual(f.hdop, 0.9)

    def test_rtk_good(self) -> None:
        f = parse_gga_fields(_SAMPLE_RTK)
        assert f is not None
        a = assess_navigation_quality(f)
        self.assertEqual(a.level, NavQualityLevel.GOOD)
        self.assertEqual(a.fix_label, GGA_FIX_LABELS[4])

    def test_autonomous_high_hdop_warn(self) -> None:
        f = parse_gga_fields(_SAMPLE_WEAK)
        assert f is not None
        a = assess_navigation_quality(f)
        self.assertIn(a.level, (NavQualityLevel.WARN, NavQualityLevel.BAD, NavQualityLevel.OK))

    def test_no_fix_bad(self) -> None:
        line = "$GPGGA,123519,4807.038,N,01131.000,E,0,00,99.9,545.4,M,46.9,M,,*00"
        f = parse_gga_fields(line)
        assert f is not None
        self.assertEqual(assess_navigation_quality(f).level, NavQualityLevel.BAD)

    def test_update_from_line(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        self.assertIsNotNone(snap)
        assert snap is not None
        self.assertEqual(snap["level"], "good")
        self.assertIn("RTK", snap["fix_label"])

    def test_stale_detection(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        assert snap is not None
        snap["mono"] = time.monotonic() - 5.0
        self.assertTrue(nav_quality_stale(snap))

    def test_stats_segment(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        assert snap is not None
        seg = format_gnss_stats_segment(snap)
        self.assertIn("GNSS:", seg)
        self.assertIn("RTK", seg)

    def test_status_chip_running(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        text = format_gnss_status_chip(snap, running=True)
        self.assertIn("GNSS:", text)
        self.assertNotIn("no recent", text)

    def test_status_chip_raw_mode(self) -> None:
        text = format_gnss_status_chip(None, running=True, raw_mode=True)
        self.assertIn("n/a (raw)", text)


if __name__ == "__main__":
    unittest.main()
