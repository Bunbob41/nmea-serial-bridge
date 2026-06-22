"""Regression: frozen GUI builds have sys.stderr=None (console=False)."""
from __future__ import annotations

import sys
import unittest
from unittest import mock

import bridge_gui
import py_interpreter


class TestStreamIsatty(unittest.TestCase):
    def test_none_stream_is_false(self) -> None:
        self.assertFalse(py_interpreter.stream_isatty(None))

    def test_missing_isatty_is_false(self) -> None:
        self.assertFalse(py_interpreter.stream_isatty(object()))

    def test_isatty_oserror_is_false(self) -> None:
        class _Broken:
            def isatty(self) -> bool:
                raise OSError("not a tty")

        self.assertFalse(py_interpreter.stream_isatty(_Broken()))


class TestBridgeGuiConsoleGuard(unittest.TestCase):
    def test_no_minimize_when_stderr_is_none(self) -> None:
        with mock.patch.object(sys, "stderr", None):
            with mock.patch.object(sys, "platform", "win32"):
                self.assertFalse(bridge_gui._should_minimize_launch_console(foreground=False))

    def test_no_minimize_when_foreground(self) -> None:
        tty = mock.Mock()
        tty.isatty.return_value = True
        with mock.patch.object(sys, "stderr", tty):
            with mock.patch.object(sys, "platform", "win32"):
                self.assertFalse(bridge_gui._should_minimize_launch_console(foreground=True))


if __name__ == "__main__":
    unittest.main()
