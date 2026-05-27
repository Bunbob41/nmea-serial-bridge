"""Tools sidebar order (Standard layout) for UI editor."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets

from ui.mixin import BridgeLogicMixin


class _ToolsNavHost:
    """Minimal host for BridgeLogicMixin tools-nav helpers."""

    def __init__(self) -> None:
        self._ui_mode = "standard"
        self._tab_catalog: dict[str, dict[str, tuple[QtWidgets.QWidget, str]]] = {
            "tools_tabs": {
                "Presets": (QtWidgets.QWidget(), "presets"),
                "Phone": (QtWidgets.QWidget(), "phone"),
                "NMEA": (QtWidgets.QWidget(), "nmea"),
            }
        }
        self._tab_hidden: dict[str, set[str]] = {"tools_tabs": set()}
        self._tools_nav = QtWidgets.QListWidget()
        self._tools_stack = QtWidgets.QStackedWidget()

    def _visible_tools_tab_names(self, key: str) -> list[str]:
        return BridgeLogicMixin._visible_tools_tab_names(self, key)  # type: ignore[misc]

    def _rebuild_tools_nav_from_state(self, key: str) -> None:
        BridgeLogicMixin._rebuild_tools_nav_from_state(self, key)  # type: ignore[misc]


class TestToolsNavLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_rebuild_applies_custom_order(self) -> None:
        host = _ToolsNavHost()
        order = ["NMEA", "Presets", "Phone"]
        with patch("ui.mixin.load_tab_order", return_value=order):
            host._rebuild_tools_nav_from_state("tools_tabs")
        labels = [host._tools_nav.item(i).text() for i in range(host._tools_nav.count())]
        self.assertEqual(labels, order)
        self.assertEqual(host._tools_stack.count(), len(order))

    def test_hidden_tabs_omitted(self) -> None:
        host = _ToolsNavHost()
        host._tab_hidden["tools_tabs"] = {"Phone"}
        with patch(
            "ui.mixin.load_tab_order",
            return_value=["Presets", "Phone", "NMEA"],
        ):
            host._rebuild_tools_nav_from_state("tools_tabs")
        labels = [host._tools_nav.item(i).text() for i in range(host._tools_nav.count())]
        self.assertEqual(labels, ["Presets", "NMEA"])

    def test_duplicate_saved_labels_do_not_duplicate_nav(self) -> None:
        inject = QtWidgets.QWidget()
        inject.setObjectName("injectPage")
        theme = QtWidgets.QWidget()
        theme.setObjectName("themePage")
        host = _ToolsNavHost()
        host._tab_catalog["tools_tabs"] = {
            "Inject": (inject, "inject"),
            "Theme": (theme, "theme"),
        }
        with patch(
            "ui.mixin.load_tab_order",
            return_value=["Inject", "Theme", "Inject"],
        ):
            host._rebuild_tools_nav_from_state("tools_tabs")
        labels = [host._tools_nav.item(i).text() for i in range(host._tools_nav.count())]
        self.assertEqual(labels, ["Inject", "Theme"])
        self.assertEqual(host._tools_stack.count(), 2)
        for row, expected in ((0, inject), (1, theme)):
            item = host._tools_nav.item(row)
            self.assertIsNotNone(item)
            idx = item.data(QtCore.Qt.ItemDataRole.UserRole)  # type: ignore[union-attr]
            host._tools_stack.setCurrentIndex(int(idx))
            self.assertIs(host._tools_stack.currentWidget(), expected)


if __name__ == "__main__":
    unittest.main()
