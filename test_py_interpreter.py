"""Tests for subprocess Python resolution."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import py_interpreter


class TestSubprocessNoConsole(unittest.TestCase):
    def test_returns_creationflags_on_windows(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            with mock.patch.object(
                py_interpreter.subprocess,
                "CREATE_NO_WINDOW",
                0x08000000,
                create=True,
            ):
                kw = py_interpreter.subprocess_no_console_kwargs()
        self.assertEqual(kw.get("creationflags"), 0x08000000)

    def test_empty_off_windows(self) -> None:
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(py_interpreter.subprocess_no_console_kwargs(), {})


class TestCliPythonGuiSpawn(unittest.TestCase):
    def test_python_exe_maps_to_pythonw_for_gui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            py = root / "python.exe"
            pyw = root / "pythonw.exe"
            py.write_bytes(b"")
            pyw.write_bytes(b"")
            with mock.patch.object(sys, "platform", "win32"):
                with mock.patch.object(py_interpreter, "cli_python_executable", return_value=str(py)):
                    got = Path(py_interpreter.cli_python_gui_spawn())
            self.assertEqual(got.resolve(), pyw.resolve())


class TestCliPythonExecutable(unittest.TestCase):
    def test_pythonw_maps_to_python_exe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyw = root / "pythonw.exe"
            py = root / "python.exe"
            pyw.write_bytes(b"")
            py.write_bytes(b"")
            with mock.patch.object(sys, "executable", str(pyw)):
                got = Path(py_interpreter.cli_python_executable())
            self.assertEqual(got.resolve(), py.resolve())


if __name__ == "__main__":
    unittest.main()
