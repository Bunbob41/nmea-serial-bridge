"""P0 reliability — COM lock probes and serial re-enumeration."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from bridge_core import SerialNetBridge, _find_com_by_hwid, _lookup_serial_hwid
from discovery_service import SerialDeviceInfo, annotate_serial_lock_status
from port_release import PortLockState, serial_port_discovery_status


class TestSerialPortDiscoveryStatus(unittest.TestCase):
    @patch("port_release.probe_com_lock")
    def test_ready_when_probe_ok(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = PortLockState("COM7", False, "ok", True, True)
        self.assertEqual(
            serial_port_discovery_status("COM7", 115200, bridge_running=False),
            "ready",
        )

    @patch("port_release.probe_com_lock")
    def test_busy_when_locked(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = PortLockState("COM7", True, "denied", True, False)
        self.assertEqual(
            serial_port_discovery_status("COM7", 115200, bridge_running=False),
            "port_busy",
        )

    def test_running_when_bridge_on_same_com(self) -> None:
        self.assertEqual(
            serial_port_discovery_status(
                "COM7", 115200, bridge_running=True, bridge_com="COM7"
            ),
            "running",
        )


class TestAnnotateSerialLocks(unittest.TestCase):
    @patch("port_release.serial_port_discovery_status", return_value="port_busy")
    def test_selected_port_probed(self, _mock: MagicMock) -> None:
        dev = SerialDeviceInfo("serial:hw", "COM7", "GPS", "", "Trimble", "available")
        out = annotate_serial_lock_status(
            [dev],
            selected_port="COM7",
            baud=115200,
            probe_all=False,
        )
        self.assertEqual(out[0].status, "port_busy")

    @patch("port_release.serial_port_discovery_status", return_value="ready")
    def test_non_selected_skipped_without_probe_all(self, mock_status: MagicMock) -> None:
        dev = SerialDeviceInfo("serial:hw", "COM8", "GPS", "", "Trimble", "available")
        out = annotate_serial_lock_status(
            [dev],
            selected_port="COM7",
            baud=115200,
            probe_all=False,
        )
        self.assertEqual(out[0].status, "available")
        mock_status.assert_not_called()


class TestSerialHwidRemap(unittest.TestCase):
    def test_lookup_and_find_round_trip(self) -> None:
        port = MagicMock()
        port.device = "COM12"
        port.hwid = "USB\\VID_1234"
        with patch("bridge_core.serial.tools.list_ports.comports", return_value=[port]):
            self.assertEqual(_lookup_serial_hwid("COM12"), "USB\\VID_1234")
            self.assertEqual(_find_com_by_hwid("USB\\VID_1234"), "COM12")

    def test_maybe_remap_updates_com(self) -> None:
        bridge = SerialNetBridge.__new__(SerialNetBridge)
        bridge.com = "COM7"
        bridge.baud = 115200
        bridge._serial_hwid = "USB\\VID_1234"
        bridge._ui_log = MagicMock()
        with patch("bridge_core._find_com_by_hwid", return_value="COM12"):
            ok = bridge._maybe_remap_com_after_reenum("Cannot open COM7: port not found")
        self.assertTrue(ok)
        self.assertEqual(bridge.com, "COM12")

    def test_try_remap_by_hwid_without_error_text(self) -> None:
        bridge = SerialNetBridge.__new__(SerialNetBridge)
        bridge.com = "COM7"
        bridge._serial_hwid = "USB\\VID_1234"
        bridge._ui_log = MagicMock()
        with patch("bridge_core._find_com_by_hwid", return_value="COM12"):
            ok = bridge._try_remap_com_by_hwid()
        self.assertTrue(ok)
        self.assertEqual(bridge.com, "COM12")


if __name__ == "__main__":
    unittest.main()
