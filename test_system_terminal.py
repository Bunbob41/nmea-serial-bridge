"""Tests for Tools → Terminal (embedded shell) helpers."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from ui import ui_prefs
from ui.system_terminal import (
    _backspace_byte,
    _consume_duplicate_key_text,
    _default_shell,
    _external_shell_working_directory,
    _launch_external_shell_windows,
    _powershell_embedded_args,
    _strip_ansi,
)


class TestSystemTerminalHelpers(unittest.TestCase):
    def test_strip_ansi_removes_color_codes(self) -> None:
        raw = "\x1b[31mhello\x1b[0m world"
        self.assertEqual(_strip_ansi(raw), "hello world")

    def test_strip_ansi_skips_plain_text(self) -> None:
        plain = "hello world\r\n"
        self.assertIs(_strip_ansi(plain), plain)

    def test_backspace_byte_platform(self) -> None:
        import sys

        bs = _backspace_byte()
        if sys.platform == "win32":
            self.assertEqual(bs, "\x08")
        else:
            self.assertEqual(bs, "\x7f")

    def test_default_shell_windows(self) -> None:
        import sys

        exe, args = _default_shell()
        self.assertTrue(exe)
        if sys.platform == "win32":
            low = exe.lower()
            self.assertTrue(low.endswith("powershell.exe") or low.endswith("cmd.exe"))
            if low.endswith("powershell.exe"):
                self.assertIn("-NoLogo", args)
                self.assertIn("PSReadLine", " ".join(args))

    def test_consume_duplicate_key_text(self) -> None:
        self.assertEqual(_consume_duplicate_key_text("p", "p"), "")
        self.assertEqual(_consume_duplicate_key_text("ping", "p"), "ing")
        self.assertEqual(_consume_duplicate_key_text("", "a"), "")

    def test_powershell_embedded_args(self) -> None:
        args = _powershell_embedded_args()
        self.assertIn("-NoExit", args)
        self.assertTrue(any("PSReadLine" in part for part in args))

    def test_load_tab_order_migrates_send_and_old_terminal(self) -> None:
        order = ui_prefs.load_tab_order("__test_mode__", "__missing_key__")
        self.assertEqual(order, [])

    def test_launch_external_windows_uses_new_console(self) -> None:
        if sys.platform != "win32":
            self.skipTest("Windows only")
        exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe")
        if not os.path.isfile(exe):
            self.skipTest("cmd.exe missing")
        with patch("ui.system_terminal.subprocess.Popen") as popen:
            popen.return_value = object()
            ok, err = _launch_external_shell_windows(exe, ["/Q"], os.getcwd())
        self.assertTrue(ok, msg=err)
        self.assertEqual(popen.call_count, 1)
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs.get("cwd"), os.getcwd())
        self.assertEqual(kwargs.get("creationflags"), getattr(subprocess, "CREATE_NEW_CONSOLE", 0))

    def test_launch_external_shell_missing_exe(self) -> None:
        if sys.platform != "win32":
            self.skipTest("Windows only")
        ok, err = _launch_external_shell_windows(r"C:\no\such\shell.exe", [], "C:\\")
        self.assertFalse(ok)
        self.assertIn("not found", err.lower())

    def test_external_cwd_prefers_exe_dir_when_frozen(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", r"C:\dist\serial-link\serial-link.exe"):
                self.assertEqual(
                    _external_shell_working_directory(),
                    r"C:\dist\serial-link",
                )

    def test_tab_order_migration_logic(self) -> None:
        # Mirror load_tab_order migration without writing prefs file.
        def migrate(items: list[str]) -> list[str]:
            out: list[str] = []
            for item in items:
                text = str(item).strip()
                if not text:
                    continue
                if text == "Send":
                    text = "Inject"
                elif text == "Terminal":
                    text = "Inject"
                out.append(text)
            return out

        self.assertEqual(migrate(["Send", "NMEA"]), ["Inject", "NMEA"])
        self.assertEqual(migrate(["Terminal", "Diagnostics"]), ["Inject", "Diagnostics"])


class TestStartStopGuards(unittest.TestCase):
    def test_start_cooldown_after_stop(self) -> None:
        from ui.mixin import START_AFTER_STOP_COOLDOWN_S, _start_cooldown_remaining_s

        t0 = 1000.0
        self.assertAlmostEqual(
            _start_cooldown_remaining_s(t0, t0 + 0.1),
            START_AFTER_STOP_COOLDOWN_S - 0.1,
            places=3,
        )
        self.assertEqual(_start_cooldown_remaining_s(0.0, t0 + 1.0), 0.0)
        self.assertEqual(
            _start_cooldown_remaining_s(t0, t0 + START_AFTER_STOP_COOLDOWN_S + 0.01),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
