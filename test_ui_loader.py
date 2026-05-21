"""Tests for Qt Designer .ui runtime loader."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtWidgets

from ui.qt_test_harness import close_all_qt_widgets, ensure_qt_app
from ui.ui_loader import LayoutLoadError, load_widget, resource_dir


class TestUiLoader(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = ensure_qt_app([])

    @classmethod
    def tearDownClass(cls) -> None:
        close_all_qt_widgets()

    def test_resource_dir_points_at_ui_resources(self) -> None:
        rd = resource_dir()
        self.assertTrue((rd / "standard_connect_shell.ui").is_file())

    def test_load_standard_connect_shell(self) -> None:
        from ui.ui_loader import load_standard_connect_shell

        w = load_standard_connect_shell()
        self.assertIsNotNone(w.findChild(QtWidgets.QWidget, "connectPanelHost"))
        self.assertIsNotNone(w.findChild(QtWidgets.QWidget, "statusBannerHost"))

    def test_fixture_minimal_shell(self) -> None:
        fixture_dir = Path(__file__).resolve().parent / "tests" / "fixtures"
        with patch("ui.ui_loader.resource_dir", return_value=fixture_dir):
            w = load_widget("minimal_shell")
        self.assertIsNotNone(w.findChild(QtWidgets.QWidget, "connectPanelHost"))

    def test_missing_ui_raises(self) -> None:
        empty = Path(__file__).resolve().parent / "tests" / "fixtures" / "_empty"
        empty.mkdir(parents=True, exist_ok=True)
        try:
            with patch("ui.ui_loader.resource_dir", return_value=empty):
                with self.assertRaises(LayoutLoadError):
                    load_widget("does_not_exist")
        finally:
            if empty.is_dir():
                try:
                    empty.rmdir()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
