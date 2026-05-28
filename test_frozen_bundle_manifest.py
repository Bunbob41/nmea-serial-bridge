"""Packaging manifest stays aligned with PyInstaller spec."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


class TestFrozenBundleManifest(unittest.TestCase):
    def test_spec_lists_bench_tcp_test_helper(self) -> None:
        spec = (Path(__file__).resolve().parent / "nmea_serial_bridge.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("bench_tcp_test.py", spec)

    def test_manifest_covers_network_automation_imports(self) -> None:
        from tools.frozen_bundle_manifest import FROZEN_HELPER_FILES

        required = {
            "bench_network_automation.py",
            "bench_tcp_test.py",
            "bench_udp_test.py",
            "nmea_static_sample.py",
            "bridge_core.py",
            "nmea_codec.py",
            "bench_config.py",
        }
        bundled = set(FROZEN_HELPER_FILES)
        missing = required - bundled
        self.assertFalse(missing, f"manifest missing: {sorted(missing)}")

    def test_spec_helper_blocks_include_manifest_files(self) -> None:
        from tools.frozen_bundle_manifest import FROZEN_HELPER_FILES

        spec = (Path(__file__).resolve().parent / "nmea_serial_bridge.spec").read_text(
            encoding="utf-8"
        )
        for name in FROZEN_HELPER_FILES:
            self.assertIn(name, spec, f"{name} not referenced in nmea_serial_bridge.spec")


if __name__ == "__main__":
    unittest.main()
