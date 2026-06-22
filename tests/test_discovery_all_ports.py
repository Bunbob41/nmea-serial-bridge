"""COM listing for web/desktop must include all ports, not GNSS-keyword-only."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from discovery_service import build_snapshot, list_all_serial_ports


class TestListAllSerialPorts(unittest.TestCase):
    @patch("discovery_service.serial.tools.list_ports.comports")
    def test_lists_non_gnss_ports(self, mock_comports: MagicMock) -> None:
        mock_comports.return_value = [
            MagicMock(
                device="COM3",
                description="com0com serial port",
                manufacturer="",
                hwid="",
            ),
            MagicMock(
                device="COM7",
                description="USB Serial Device",
                manufacturer="FTDI",
                hwid="USB\\VID",
            ),
        ]
        ports = list_all_serial_ports()
        names = [p.port for p in ports]
        self.assertEqual(names, ["COM3", "COM7"])
        self.assertEqual(ports[0].match_keyword, "")
        self.assertEqual(ports[1].match_keyword, "")

    @patch("discovery_service.serial.tools.list_ports.comports")
    def test_build_snapshot_uses_all_ports(self, mock_comports: MagicMock) -> None:
        mock_comports.return_value = [
            MagicMock(device="COM12", description="GNSS", manufacturer="Trimble", hwid="X"),
        ]
        snap, _ = build_snapshot()
        self.assertEqual(len(snap.serial_devices), 1)
        self.assertEqual(snap.serial_devices[0].port, "COM12")
        self.assertEqual(snap.serial_devices[0].match_keyword, "Trimble")


if __name__ == "__main__":
    unittest.main()
