"""Mission Quick Export zip tests."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from ui.mission_export import (
    build_mission_summary_text,
    export_session_backup_copy,
    export_session_nmea_csv,
    export_session_track_kml,
    quick_export_mission_zip,
    resolve_session_backup_path,
    suggest_quick_export_path,
)
from ui.mission_session import MissionSessionRecord


class TestMissionExport(unittest.TestCase):
    def test_summary_text_includes_duration_and_hz(self) -> None:
        text = build_mission_summary_text(
            MissionSessionRecord(
                started_mono=0.0,
                ended_mono=120.0,
                duration_s=120.0,
                backup_path=r"C:\logs\backup.raw",
                total_bytes=50_000,
                total_dropped=0,
                avg_hz_up=12.5,
                throughput_buckets=[1000, 2000],
                health_ticks=["ok", "ok"],
            )
        )
        self.assertIn("Duration:", text)
        self.assertIn("12.50", text)
        self.assertIn("50,000", text)

    def test_quick_export_creates_zip_with_backup_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "backup_20260614_1645.nmea"
            raw.write_bytes(b"$GPGGA" * 200)
            record = MissionSessionRecord(
                started_mono=0.0,
                ended_mono=60.0,
                duration_s=60.0,
                backup_path=str(raw),
                total_bytes=raw.stat().st_size,
                total_dropped=0,
                avg_hz_up=10.0,
            )
            zip_path = quick_export_mission_zip(record, dest_dir=Path(tmp) / "out")
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                self.assertIn("mission_summary.txt", names)
                self.assertIn(raw.name, names)
                summary = zf.read("mission_summary.txt").decode("utf-8")
                self.assertIn("Mission Summary", summary)

    def test_resolve_accepts_legacy_raw_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "backup_20260614_1645.raw"
            raw.write_bytes(b"$GPGGA")
            record = MissionSessionRecord(
                started_mono=0.0,
                ended_mono=1.0,
                duration_s=1.0,
                backup_path=str(raw),
                total_bytes=raw.stat().st_size,
                total_dropped=0,
                avg_hz_up=0.0,
            )
            self.assertEqual(resolve_session_backup_path(record), raw)

    def test_export_session_backup_copy_to_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "backup.nmea"
            source.write_bytes(b"$GPRMC,1,2,3*11\r\n")
            record = MissionSessionRecord(
                started_mono=0.0,
                ended_mono=1.0,
                duration_s=1.0,
                backup_path=str(source),
                total_bytes=source.stat().st_size,
                total_dropped=0,
                avg_hz_up=0.0,
            )
            dest = Path(tmp) / "handoff.log"
            out = export_session_backup_copy(source, dest)
            self.assertEqual(out, dest)
            self.assertEqual(dest.read_bytes(), source.read_bytes())
            suggested = suggest_quick_export_path(record, dest_dir=Path(tmp))
            self.assertTrue(str(suggested).endswith(".nmea"))

    def test_export_session_nmea_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "backup.nmea"
            source.write_text("$GPGGA,1,2,3,4,5,6,7*00\n$GPRMC,1,2,3,4,5,6,7,8*00\n", encoding="utf-8")
            dest = Path(tmp) / "out.csv"
            export_session_nmea_csv(source, dest)
            text = dest.read_text(encoding="utf-8")
            self.assertIn("sentence_type", text)
            self.assertIn("GGA", text)

    def test_export_session_track_kml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "backup.nmea"
            source.write_text(
                "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n",
                encoding="utf-8",
            )
            dest = Path(tmp) / "track.kml"
            export_session_track_kml(source, dest)
            body = dest.read_text(encoding="utf-8")
            self.assertIn("<kml", body)
            self.assertIn("LineString", body)


if __name__ == "__main__":
    unittest.main()
