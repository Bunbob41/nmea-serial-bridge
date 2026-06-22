"""Hub serial status cache across lightweight discovery polls."""
from __future__ import annotations

import unittest

from discovery_service import (
    SerialDeviceInfo,
    apply_serial_status_cache,
    serial_probe_summary,
)


class TestDiscoveryCache(unittest.TestCase):
    def test_apply_serial_status_cache_keeps_probed_ports(self) -> None:
        devices = [
            SerialDeviceInfo("a", "COM7", "", "", "", "available"),
            SerialDeviceInfo("b", "COM9", "", "", "", "available"),
        ]
        out = apply_serial_status_cache(
            devices,
            {"COM7": "ready", "COM9": "port_busy"},
            selected_port="COM7",
            bridge_running=False,
        )
        self.assertEqual(out[0].status, "ready")
        self.assertEqual(out[1].status, "port_busy")

    def test_serial_probe_summary(self) -> None:
        devices = [
            SerialDeviceInfo("a", "COM7", "", "", "", "ready"),
            SerialDeviceInfo("b", "COM9", "", "", "", "port_busy"),
            SerialDeviceInfo("c", "COM13", "", "", "", "running"),
        ]
        self.assertIn("1 COM free", serial_probe_summary(devices))
        self.assertIn("1 busy", serial_probe_summary(devices))


if __name__ == "__main__":
    unittest.main()
