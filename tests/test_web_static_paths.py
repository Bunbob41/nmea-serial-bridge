"""Frozen / PyInstaller static dashboard path resolution."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web_api import resolve_static_dir


class TestWebStaticPaths(unittest.TestCase):
    def test_dev_tree_finds_static(self) -> None:
        with patch.object(sys, "frozen", False, create=True):
            p = resolve_static_dir()
        self.assertIsNotNone(p)
        self.assertTrue((p / "index.html").is_file())

    def test_frozen_meipass_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static = root / "web" / "static"
            static.mkdir(parents=True)
            (static / "index.html").write_text("<html></html>", encoding="utf-8")
            with patch.object(sys, "frozen", True, create=True):
                with patch.object(sys, "_MEIPASS", str(root), create=True):
                    with patch.object(sys, "executable", str(root / "serial-link.exe"), create=True):
                        found = resolve_static_dir()
                        self.assertIsNotNone(found)
                        self.assertEqual(found.resolve(), static.resolve())

    def test_frozen_internal_folder_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            internal = root / "_internal"
            static = internal / "web" / "static"
            static.mkdir(parents=True)
            (static / "index.html").write_text("<html></html>", encoding="utf-8")
            with patch.object(sys, "frozen", True, create=True):
                with patch.object(sys, "_MEIPASS", str(internal), create=True):
                    with patch.object(sys, "executable", str(root / "serial-link.exe"), create=True):
                        found = resolve_static_dir()
                        self.assertIsNotNone(found)
                        self.assertEqual(found.resolve(), static.resolve())


if __name__ == "__main__":
    unittest.main()
