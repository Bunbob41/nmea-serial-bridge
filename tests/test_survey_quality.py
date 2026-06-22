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
    format_gnss_status_tooltip,
    gnss_fix_label_hud_display,
    gnss_status_badge_quality,
    gnss_status_badge_stylesheet,
    nav_metrics_should_reset,
    nav_quality_stale,
    nav_quality_stream_idle_snapshot,
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

    def test_stream_idle_snapshot(self) -> None:
        idle = nav_quality_stream_idle_snapshot()
        self.assertEqual(idle["quality"], 0)
        self.assertEqual(idle["num_sats"], 0)
        self.assertEqual(idle["summary"], "No Data Stream")
        self.assertEqual(idle["fix_label"], GGA_FIX_LABELS[0])

    def test_nav_metrics_reset_zero_hz(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        self.assertTrue(
            nav_metrics_should_reset(traffic_hz=0.0, nav=snap, running=True)
        )

    def test_nav_metrics_reset_stale_gga(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        assert snap is not None
        snap["mono"] = time.monotonic() - 2.5
        self.assertTrue(
            nav_metrics_should_reset(traffic_hz=5.0, nav=snap, running=True)
        )

    def test_status_chip_stream_idle(self) -> None:
        idle = nav_quality_stream_idle_snapshot()
        text = format_gnss_status_chip(idle, running=True)
        self.assertIn("No Data Stream", text)

    def test_badge_stylesheet_rtk_green(self) -> None:
        ss = gnss_status_badge_stylesheet(4)
        self.assertIn("#D4EDDA", ss)
        self.assertIn("#155724", ss)
        self.assertIn("font-weight: bold", ss)

    def test_badge_stylesheet_gps_blue(self) -> None:
        ss = gnss_status_badge_stylesheet(1)
        self.assertIn("#CCE5FF", ss)
        self.assertIn("#004085", ss)

    def test_badge_stylesheet_idle_red(self) -> None:
        idle = nav_quality_stream_idle_snapshot()
        q = gnss_status_badge_quality(idle, running=True)
        self.assertEqual(q, 0)
        ss = gnss_status_badge_stylesheet(q)
        self.assertIn("#F8D7DA", ss)
        self.assertIn("#721C24", ss)

    def test_hud_badge_stream_idle_short_label(self) -> None:
        from survey_quality import gnss_status_hud_badge_text

        self.assertEqual(gnss_status_hud_badge_text(stream_idle=True), "Idle")

    def test_badge_stylesheet_hud_uses_compact_padding(self) -> None:
        ss = gnss_status_badge_stylesheet(0, hud=True)
        self.assertIn("padding: 0px 4px", ss)
        self.assertNotIn("padding: 6px", ss)
        self.assertIn("#fce8ea", ss)

    def test_badge_cleared_when_stopped(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        self.assertEqual(gnss_status_badge_quality(snap, running=False), None)
        self.assertEqual(gnss_status_badge_stylesheet(None), "")

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

    def test_status_tooltip_includes_fix_label(self) -> None:
        snap = update_nav_quality_from_line(_SAMPLE_RTK)
        assert snap is not None
        tip = format_gnss_status_tooltip(snap, running=True)
        self.assertIn("Fix: RTK fixed", tip)
        self.assertIn("Satellites:", tip)
        self.assertIn("HDOP:", tip)

    def test_hud_compact_fix_label(self) -> None:
        self.assertEqual(
            gnss_fix_label_hud_display("RTK fixed", narrow=True),
            "RTK-F",
        )
        self.assertEqual(
            gnss_fix_label_hud_display("RTK fixed", narrow=False),
            "RTK fixed",
        )


if __name__ == "__main__":
    unittest.main()
