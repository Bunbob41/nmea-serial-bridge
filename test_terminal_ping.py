"""Terminal quick-ping helpers and prefs."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import ui_prefs
from ui.terminal_ping import (
    ping_pty_command,
    ping_subprocess_args,
    sanitize_ping_host,
    suggested_ping_preset_name,
)


class TestTerminalPingHelpers(unittest.TestCase):
    def test_sanitize_accepts_ipv4_and_hostname(self) -> None:
        self.assertEqual(sanitize_ping_host("192.168.1.8"), "192.168.1.8")
        self.assertEqual(sanitize_ping_host("boat.tail-abc.ts.net"), "boat.tail-abc.ts.net")

    def test_sanitize_rejects_empty_and_spaces(self) -> None:
        self.assertIsNone(sanitize_ping_host(""))
        self.assertIsNone(sanitize_ping_host("bad host"))

    def test_ping_pty_command_windows(self) -> None:
        cmd = ping_pty_command("10.0.0.1", platform="win32")
        self.assertEqual(cmd, "ping -n 4 10.0.0.1\r\n")

    def test_ping_subprocess_args_unix(self) -> None:
        args = ping_subprocess_args("gw.local", platform="linux")
        self.assertEqual(args, ["ping", "-c", "4", "gw.local"])

    def test_suggested_preset_name_short_hostname(self) -> None:
        self.assertEqual(suggested_ping_preset_name("pi-nd", {}), "pi-nd")
        self.assertEqual(
            suggested_ping_preset_name("boat.tail-abc.ts.net", {}),
            "boat",
        )

    def test_suggested_preset_name_ipv4(self) -> None:
        self.assertEqual(suggested_ping_preset_name("192.168.1.8", {}), "192.168.1.8")

    def test_suggested_preset_name_existing_host(self) -> None:
        presets = {"noah": "noah.tail.ts.net", "INS": "192.168.1.20"}
        self.assertEqual(
            suggested_ping_preset_name("noah.tail.ts.net", presets),
            "noah",
        )
        self.assertEqual(
            suggested_ping_preset_name("192.168.1.20", presets),
            "INS",
        )


class TestTerminalPingPrefs(unittest.TestCase):
    def test_roundtrip_and_bubbles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                self.assertIsNone(ui_prefs.save_terminal_ping_preset("Boat AP", "192.168.1.8"))
                self.assertIsNone(ui_prefs.save_terminal_ping_preset("INS", "192.168.1.20"))
                names = ui_prefs.list_terminal_ping_preset_names()
                self.assertEqual(names, ["Boat AP", "INS"])
                self.assertEqual(ui_prefs.terminal_ping_host("Boat AP"), "192.168.1.8")
                bubbles = ui_prefs.terminal_ping_bubble_names()
                self.assertEqual(bubbles, ["Boat AP", "INS"])
                self.assertTrue(ui_prefs.delete_terminal_ping_preset("Boat AP"))
                self.assertEqual(ui_prefs.list_terminal_ping_preset_names(), ["INS"])
                self.assertFalse(ui_prefs.delete_terminal_ping_preset("Boat AP"))


if __name__ == "__main__":
    unittest.main()
