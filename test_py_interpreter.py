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


class TestQprocessAttachNoConsole(unittest.TestCase):
    def test_skips_when_modifier_api_missing(self) -> None:
        class _Proc:
            pass

        proc = _Proc()
        with mock.patch.object(sys, "platform", "win32"):
            with mock.patch.object(
                py_interpreter.subprocess,
                "CREATE_NO_WINDOW",
                0x08000000,
                create=True,
            ):
                py_interpreter.qprocess_attach_no_console(proc)
        self.assertFalse(hasattr(proc, "_modifier_called"))

    def test_attaches_modifier_when_available(self) -> None:
        class _Args:
            flags = 0

        class _Proc:
            def setCreateProcessArgumentsModifier(self, fn) -> None:
                self._fn = fn

        proc = _Proc()
        with mock.patch.object(sys, "platform", "win32"):
            with mock.patch.object(
                py_interpreter.subprocess,
                "CREATE_NO_WINDOW",
                0x08000000,
                create=True,
            ):
                py_interpreter.qprocess_attach_no_console(proc)
        args = _Args()
        proc._fn(args)
        self.assertEqual(args.flags & 0x08000000, 0x08000000)


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

    def test_frozen_app_uses_path_python_when_sys_executable_is_app(self) -> None:
        app = Path(r"C:\tmp\nmea-serial-bridge.exe")
        with mock.patch.object(sys, "executable", str(app)):
            with mock.patch.object(sys, "frozen", True, create=True):
                with mock.patch.object(py_interpreter.shutil, "which", return_value=r"C:\Python314\python.exe"):
                    got = Path(py_interpreter.cli_python_executable())
        self.assertEqual(got, Path(r"C:\Python314\python.exe"))


if __name__ == "__main__":
    unittest.main()
