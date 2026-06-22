"""Tests for port_release smart release."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from port_release import PortLockState, smart_release_com


class TestSmartReleaseCom(unittest.TestCase):
    def test_blocked_when_bridge_running_on_same_com(self) -> None:
        state = smart_release_com(
            "COM7",
            115200,
            bridge_running=True,
            bridge_com="COM7",
        )
        self.assertFalse(state.safe_to_release)
        self.assertIn("stop", state.reason.lower())

    @patch("port_release.probe_com_lock")
    def test_probe_when_not_running(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = PortLockState("COM7", False, "OK", True, True)
        state = smart_release_com("COM7", 115200, bridge_running=False, bridge_com=None)
        self.assertTrue(state.last_attempt_ok)

    @patch("port_release.probe_com_lock")
    def test_denied_probe_not_last_attempt_ok(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = PortLockState(
            "COM7",
            True,
            "Access is denied",
            True,
            False,
        )
        state = smart_release_com("COM7", 115200, bridge_running=False, bridge_com=None)
        self.assertFalse(state.last_attempt_ok)


class TestProbeComLock(unittest.TestCase):
    def test_denied_last_attempt_false(self) -> None:
        state = PortLockState(
            "COM7",
            True,
            "could not open port 'COM7': PermissionError(13, 'Access is denied.')",
            True,
            False,
        )
        self.assertFalse(bool(state.last_attempt_ok))


if __name__ == "__main__":
    unittest.main()
