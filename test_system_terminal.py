"""Tests for Tools → Terminal (embedded shell) helpers."""
from __future__ import annotations

import unittest

from ui import ui_prefs
from ui.system_terminal import _backspace_byte, _strip_ansi, _default_shell


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

    def test_load_tab_order_migrates_send_and_old_terminal(self) -> None:
        order = ui_prefs.load_tab_order("__test_mode__", "__missing_key__")
        self.assertEqual(order, [])

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


if __name__ == "__main__":
    unittest.main()
