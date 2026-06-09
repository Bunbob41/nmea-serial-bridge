"""Tests for app-wide stylesheet helpers."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui.styles import apply_global_contrast_guard, bridge_stylesheet


class TestGlobalContrastGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_message_box_rules_are_injected(self) -> None:
        app = self._app
        app.setProperty("_bridge_base_stylesheet", None)
        app.setStyleSheet("QLabel { color: #123456; }")
        apply_global_contrast_guard(app)
        css = app.styleSheet()
        self.assertIn("QMessageBox", css)
        self.assertIn("QToolTip", css)
        self.assertIn("BRIDGE_GLOBAL_CONTRAST_GUARD", css)

    def test_reapply_does_not_duplicate_guard_block(self) -> None:
        app = self._app
        app.setProperty("_bridge_base_stylesheet", None)
        app.setStyleSheet("QLabel { color: #abcdef; }")
        apply_global_contrast_guard(app)
        once = app.styleSheet()
        apply_global_contrast_guard(app)
        twice = app.styleSheet()
        self.assertEqual(once, twice)
        self.assertEqual(twice.count("BRIDGE_GLOBAL_CONTRAST_GUARD"), 1)


class TestConnectSectionStyles(unittest.TestCase):
    def test_standard_stylesheet_includes_connect_section_rules(self) -> None:
        css = bridge_stylesheet("standard", "maroon_classic")
        self.assertIn("connectGroupBox", css)
        self.assertIn("connectSectionBody", css)
        self.assertIn("connectPanelRow", css)

    def test_standard_stylesheet_includes_visible_scrollbars(self) -> None:
        css = bridge_stylesheet("standard", "maroon_classic")
        self.assertIn("QScrollBar::handle:vertical", css)
        self.assertIn("QComboBox QAbstractItemView", css)
        self.assertIn("endpointCard", css)


if __name__ == "__main__":
    unittest.main()
