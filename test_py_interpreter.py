"""Tests for subprocess Python resolution."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import py_interpreter


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
