"""Tests for named connection presets."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bench_config as bc


class TestPathPresets(unittest.TestCase):
    def test_user_named_preset_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                bc.save_preset(
                    "My boat",
                    {
                        "com": "COM5",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "pc_ip": "10.0.0.5",
                        "ins_ip": "10.0.0.9",
                    },
                    boat_style=True,
                )
                d = bc.load_preset("My boat")
                self.assertEqual(d["com"], "COM5")
                self.assertEqual(d["pc_ip"], "10.0.0.5")
                self.assertIn("My boat", bc.list_preset_names())

    def test_preset_saves_nmea_mode_and_strict_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                bc.save_preset(
                    "Strict bench",
                    {
                        "com": "COM8",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "nmea_mode": "strict",
                        "nmea_types": ["GGA", "RMC"],
                    },
                )
                d = bc.load_preset("Strict bench")
                self.assertEqual(d["nmea_mode"], "strict")
                self.assertEqual(d["nmea_types"], ["GGA", "RMC"])
                bc.save_preset(
                    "Raw RTCM",
                    {
                        "com": "COM9",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "nmea_mode": "raw",
                    },
                )
                self.assertEqual(bc.load_preset("Raw RTCM")["nmea_mode"], "raw")

    def test_legacy_desk_migrates_to_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            user_path.write_text(
                json.dumps({"desk": {"com": "COM99", "baud": 9600, "udp_port": 9999}}),
                encoding="utf-8",
            )
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                with mock.patch.object(bc, "_load_merged_bench_json", return_value={"com": "COM7"}):
                    names = bc.list_preset_names()
                    d = bc.load_bench_defaults()
            self.assertIn("Desk test", names)
            self.assertEqual(d["com"], "COM99")

    def test_save_desk_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                bc.save_desk_preset(
                    {"com": "COM12", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 10110}
                )
                d = bc.load_bench_defaults()
            self.assertEqual(d["com"], "COM12")
            raw = json.loads(user_path.read_text(encoding="utf-8"))
            self.assertIn("presets", raw)

    def test_delete_keeps_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                with mock.patch.object(bc, "_builtin_presets", return_value={}):
                    user_path.write_text(
                        json.dumps(
                            {
                                "presets": {
                                    "Only": {
                                        "com": "COM1",
                                        "baud": 115200,
                                        "udp_host": "0.0.0.0",
                                        "udp_port": 1,
                                    }
                                }
                            }
                        ),
                        encoding="utf-8",
                    )
                    self.assertFalse(bc.delete_preset("Only"))
                    bc.save_preset(
                        "Second",
                        {"com": "COM2", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 2},
                    )
                    self.assertTrue(bc.delete_preset("Only"))
                    self.assertEqual(bc.list_preset_names(), ["Second"])

    def test_preset_reorder_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                with mock.patch.object(bc, "_builtin_presets", return_value={}):
                    bc.save_preset(
                        "Alpha",
                        {"com": "COM1", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 1},
                    )
                    bc.save_preset(
                        "Bravo",
                        {"com": "COM2", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 2},
                    )
                    bc.save_preset(
                        "Charlie",
                        {"com": "COM3", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 3},
                    )
                    self.assertEqual(bc.list_preset_names(), ["Alpha", "Bravo", "Charlie"])
                    self.assertTrue(bc.reorder_preset_names(["Charlie", "Alpha", "Bravo"]))
                    self.assertEqual(bc.list_preset_names(), ["Charlie", "Alpha", "Bravo"])

    def test_last_preset_tracks_save_for_startup_restore(self) -> None:
        """US1: cold launch reads last_preset via last_preset_name()."""
        with tempfile.TemporaryDirectory() as tmp:
            user_path = Path(tmp) / "path_presets.json"
            with mock.patch.object(bc, "USER_PRESETS_PATH", user_path):
                bc.save_preset(
                    "Boat / INS",
                    {
                        "com": "COM11",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "pc_ip": "192.168.1.4",
                    },
                    boat_style=True,
                )
                self.assertEqual(bc.last_preset_name(), "Boat / INS")
                raw = json.loads(user_path.read_text(encoding="utf-8"))
                self.assertEqual(raw.get("last_preset"), "Boat / INS")

    def test_builtin_norbit_dct_preset(self) -> None:
        """Built-ins from shipped bench_defaults.json only (no local override)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bench_defaults.json").write_text(
                (Path(__file__).resolve().parent / "bench_defaults.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            with mock.patch.object(bc, "_bench_defaults_roots", return_value=[root]):
                builtins = bc._builtin_presets()
        self.assertIn("NORBIT DCT", builtins)
        d = builtins["NORBIT DCT"]
        self.assertEqual(d["pc_ip"], "192.168.1.10")
        self.assertEqual(d["ins_ip"], "192.168.1.20")
        self.assertEqual(d["udp_port"], 40810)
        self.assertIn("NORBIT_DCT", d.get("notes", "").replace("\\", "/"))

    def test_builtin_cube_mavlink_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bench_defaults.json").write_text(
                (Path(__file__).resolve().parent / "bench_defaults.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            with mock.patch.object(bc, "_bench_defaults_roots", return_value=[root]):
                builtins = bc._builtin_presets()
                names = bc.list_preset_names()
            with mock.patch.object(bc, "USER_PRESETS_PATH", Path(tmp) / "empty.json"):
                with mock.patch.object(bc, "_bench_defaults_roots", return_value=[root]):
                    names_fresh = bc.list_preset_names()
        self.assertIn("Cube MAVLink", builtins)
        d = builtins["Cube MAVLink"]
        self.assertEqual(d["nmea_mode"], "raw")
        self.assertEqual(d["udp_port"], 14550)
        self.assertIn("Cube MAVLink", names_fresh)

    def test_bench_defaults_local_overrides_public(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bench_defaults.json").write_text(
                json.dumps({"com": "COM1", "production": {"pc_ip": "10.0.0.1"}}),
                encoding="utf-8",
            )
            (root / "bench_defaults.local.json").write_text(
                json.dumps({"com": "COM9", "production": {"pc_ip": "10.0.0.9"}}),
                encoding="utf-8",
            )
            with mock.patch.object(bc, "_bench_defaults_roots", return_value=[root]):
                merged = bc._load_merged_bench_json()
            self.assertEqual(merged["com"], "COM9")
            self.assertEqual(merged["production"]["pc_ip"], "10.0.0.9")


if __name__ == "__main__":
    unittest.main()
