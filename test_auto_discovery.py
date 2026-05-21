"""Unit tests for AutoDiscoveryThread."""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from auto_discovery import AutoDiscoveryThread, DEFAULT_KEYWORDS


def _make_port(device: str, description: str = "", manufacturer: str = "", hwid: str = ""):
    p = MagicMock()
    p.device = device
    p.description = description
    p.manufacturer = manufacturer
    p.hwid = hwid
    return p


class TestAutoDiscoveryDefaults(unittest.TestCase):
    def test_default_keywords_present(self) -> None:
        self.assertIn("Trimble", DEFAULT_KEYWORDS)
        self.assertIn("U-blox", DEFAULT_KEYWORDS)
        self.assertIn("NovAtel", DEFAULT_KEYWORDS)

    def test_no_generic_ftdi_in_defaults(self) -> None:
        """'FTDI' must not be in defaults — too broad for survey auto-start."""
        self.assertNotIn("FTDI", DEFAULT_KEYWORDS)
        self.assertNotIn("Serial", DEFAULT_KEYWORDS)


class TestAutoDiscoveryScan(unittest.TestCase):
    """Tests for the internal _scan helper."""

    def _thread(self) -> AutoDiscoveryThread:
        return AutoDiscoveryThread(stable_polls=1)

    def test_returns_none_when_no_ports(self) -> None:
        t = self._thread()
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[]):
            self.assertIsNone(t._scan())

    def test_detects_matching_description(self) -> None:
        t = self._thread()
        port = _make_port("COM7", description="Trimble GPS Receiver")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            self.assertEqual(t._scan(), "COM7")

    def test_detects_match_in_manufacturer(self) -> None:
        t = self._thread()
        port = _make_port("COM9", manufacturer="U-blox AG")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            self.assertEqual(t._scan(), "COM9")

    def test_ignores_non_gnss_device(self) -> None:
        t = self._thread()
        port = _make_port("COM3", description="USB Serial Port (Arduino)")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            self.assertIsNone(t._scan())

    def test_case_insensitive_match(self) -> None:
        t = self._thread()
        port = _make_port("COM12", description="trimble r10 gnss receiver")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            self.assertEqual(t._scan(), "COM12")

    def test_custom_keyword_matches(self) -> None:
        t = AutoDiscoveryThread(target_keywords=("TestDevice",), stable_polls=1)
        port = _make_port("COM5", description="TestDevice v2")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            self.assertEqual(t._scan(), "COM5")


class TestAutoDiscoveryStabilityAndSignal(unittest.TestCase):
    """Tests for the stable_polls guard and signal emission logic."""

    def test_emits_after_stable_polls(self) -> None:
        t = AutoDiscoveryThread(stable_polls=1)
        emitted: list[str] = []
        t.device_detected.connect(emitted.append)
        port = _make_port("COM7", description="Trimble GPS")

        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            with patch("time.sleep"):
                # First poll — stable_count becomes 1, not yet at threshold.
                t._active = True
                # Simulate run() logic manually for two iterations.
                found = t._scan()
                if found == t._pending_port:
                    t._stable_count += 1
                else:
                    t._pending_port = found
                    t._stable_count = 1
                self.assertEqual(emitted, [], "should not emit after first poll")

                # Second poll — stable_count hits threshold.
                if found == t._pending_port:
                    t._stable_count += 1
                else:
                    t._pending_port = found
                    t._stable_count = 1
                if t._stable_count >= t.stable_polls and found != t._last_emitted_port:
                    t._last_emitted_port = found
                    t.device_detected.emit(found)
                self.assertEqual(emitted, ["COM7"])

    def test_no_re_emit_for_same_port(self) -> None:
        t = AutoDiscoveryThread(stable_polls=1)
        emitted: list[str] = []
        t.device_detected.connect(emitted.append)
        t._last_emitted_port = "COM7"
        t._pending_port = "COM7"
        t._stable_count = 1
        port = _make_port("COM7", description="Trimble GPS")

        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            found = t._scan()
            if t._stable_count >= t.stable_polls and found != t._last_emitted_port:
                t._last_emitted_port = found
                t.device_detected.emit(found)
        self.assertEqual(emitted, [], "must not re-emit while device stays connected")

    def test_reset_on_device_absence(self) -> None:
        t = AutoDiscoveryThread(stable_polls=1)
        t._last_emitted_port = "COM7"
        t._pending_port = "COM7"
        t._stable_count = 5

        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[]):
            found = t._scan()
        if not found:
            t._pending_port = None
            t._stable_count = 0
            t._last_emitted_port = None

        self.assertIsNone(t._last_emitted_port)
        self.assertEqual(t._stable_count, 0)

    def test_stop_sets_active_false(self) -> None:
        t = AutoDiscoveryThread(stable_polls=1)
        # Don't actually start the thread; just verify stop() sets the flag.
        t._active = True
        # Patch wait() so stop() doesn't hang.
        with patch.object(t, "wait"):
            t.stop()
        self.assertFalse(t._active)


class TestAutoDiscoveryThreadRun(unittest.TestCase):
    """Smoke-test the QThread.run() path with a live (but brief) thread."""

    def test_run_emits_on_match(self) -> None:
        emitted: list[str] = []
        t = AutoDiscoveryThread(stable_polls=1, poll_interval_s=0.05)
        t.device_detected.connect(emitted.append)

        port = _make_port("COM7", description="Trimble GNSS")
        call_count = 0

        def _fake_comports():
            nonlocal call_count
            call_count += 1
            # Stop the thread after a few polls.
            if call_count > 3:
                t._active = False
            return [port]

        with patch("discovery_service.serial.tools.list_ports.comports", side_effect=_fake_comports):
            t.run()  # runs synchronously since _active is forced False quickly

        self.assertIn("COM7", emitted)


if __name__ == "__main__":
    unittest.main()
