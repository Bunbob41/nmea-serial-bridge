import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from nmea_position import nmea_dm_to_decimal, parse_gga_position
from session_sounding_replay import (
    format_export_timestamp,
    nmea_utc_to_epoch,
    replay_soundings_from_lines,
)
from ui.mission_export import export_session_soundings_kml, export_session_survey_csv
from ui.mission_session import MissionSessionRecord


def _gga(lat_dm: str, lon_dm: str, t: str) -> str:
    body = f"GPGGA,{t},{lat_dm},N,{lon_dm},W,1,08,1.0,0.0,M,0.0,M,,"
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


def _rmc(lat_dm: str, lon_dm: str, t: str, date: str) -> str:
    body = f"GPRMC,{t},A,{lat_dm},N,{lon_dm},W,0.0,0.0,{date},0.0,E"
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


def _sddpt(depth_m: float) -> str:
    body = f"SDDPT,{depth_m},0.0"
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


class TestSessionSoundingReplay(unittest.TestCase):
    def test_lon_uses_three_degree_digits(self) -> None:
        self.assertAlmostEqual(
            nmea_dm_to_decimal("12013.66857", "W", is_latitude=False) or 0,
            -120.227809,
            places=5,
        )
        pos = parse_gga_position(
            "$GPGGA,123519,4436.77826,N,12013.66857,W,1,08,0.9,545.4,M,46.9,M,,*47"
        )
        assert pos is not None
        self.assertAlmostEqual(pos.lon, -120.227809, places=5)

    def test_depth_pairs_with_next_fix_in_stream(self) -> None:
        lines = [
            _gga("4442.10932", "12015.54222", "011513.00"),
            _sddpt(7.0),
            _gga("4442.08878", "12015.59487", "011514.17"),
        ]
        rows = replay_soundings_from_lines(lines)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["lat"], 44.701479, places=5)
        self.assertAlmostEqual(rows[0]["lon"], -120.259914, places=5)
        self.assertAlmostEqual(rows[0]["depth_m"], 7.0)
        self.assertIn("011514.17", rows[0]["timestamp"])

    def test_depths_before_next_fix_share_that_fix(self) -> None:
        lines = [_gga("3600.00000", "11800.00000", "120000.00")]
        for i in range(48):
            lines.append(_sddpt(float(i)))
        lines.append(_gga("3600.01000", "11800.01000", "120001.00"))
        rows = replay_soundings_from_lines(lines)
        self.assertEqual(len(rows), 48)
        lats = {round(float(r["lat"]), 6) for r in rows}
        lons = {round(float(r["lon"]), 6) for r in rows}
        self.assertEqual(len(lats), 1)
        self.assertEqual(len(lons), 1)
        self.assertAlmostEqual(rows[0]["lat"], 36.000167, places=5)
        self.assertAlmostEqual(rows[0]["lon"], -118.000167, places=5)

    def test_timestamp_uses_rmc_date_with_gga_time(self) -> None:
        lines = [
            _rmc("3600.00000", "11800.00000", "120000.00", "250625"),
            _sddpt(5.0),
            _gga("3600.00000", "11800.00000", "120000.00"),
        ]
        rows = replay_soundings_from_lines(lines)
        self.assertEqual(len(rows), 1)
        epoch = nmea_utc_to_epoch("250625", "120000.00")
        assert epoch is not None
        expected = format_export_timestamp("120000.00", utc_date="250625", epoch=epoch)
        self.assertEqual(rows[0]["timestamp"], expected)
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 25)

    def test_export_kml_placemarks_are_contiguous(self) -> None:
        lines = [_gga("3600.00000", "11800.00000", "120000.00")]
        for i in range(3):
            lines.append(_sddpt(5.0 + i))
        lines.append(_gga("3600.01000", "11800.01000", "120001.00"))
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "sess.nmea"
            backup.write_text("\n".join(lines) + "\n", encoding="utf-8")
            record = MissionSessionRecord(0, 1, 1, str(backup), 0, 0, 1.0)
            kml = Path(tmp) / "out.kml"
            export_session_soundings_kml(record, kml)
            body = kml.read_text(encoding="utf-8")
            self.assertIn("Sounding 1", body)
            self.assertIn("Sounding 2", body)
            self.assertIn("Sounding 3", body)
            self.assertNotIn("Sounding 25", body)
            csv_path = Path(tmp) / "out.csv"
            export_session_survey_csv(record, csv_path)
            csv_body = csv_path.read_text(encoding="utf-8")
            self.assertIn("depth_m", csv_body)
            self.assertIn("120001.00", csv_body)
            self.assertEqual(csv_body.count("\n"), 4)


if __name__ == "__main__":
    unittest.main()
