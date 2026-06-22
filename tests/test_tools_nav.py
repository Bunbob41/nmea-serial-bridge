"""Tools drawer / nav helpers."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.tools_nav import open_tools_tab


class TestToolsNav(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def _make_win(self, labels: list[str]) -> QtWidgets.QWidget:
        win = QtWidgets.QWidget()
        btn = QtWidgets.QPushButton()
        btn.setCheckable(True)
        btn.setChecked(False)
        win._drawer_btn = btn  # type: ignore[attr-defined]
        tabs = QtWidgets.QTabWidget()
        for label in labels:
            tabs.addTab(QtWidgets.QWidget(), label)
        win._drawer_tabs = tabs  # type: ignore[attr-defined]
        return win

    def test_open_send_selects_inject_tab(self) -> None:
        win = self._make_win(["Presets", "Terminal", "Inject", "Diagnostics"])
        open_tools_tab(win, "send")
        self.assertTrue(win._drawer_btn.isChecked())  # type: ignore[attr-defined]
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "Inject")

    def test_open_terminal_alias(self) -> None:
        win = self._make_win(["Presets", "Terminal", "Inject", "Diagnostics"])
        open_tools_tab(win, "terminal")
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "Terminal")

    def test_open_guide_alias(self) -> None:
        win = self._make_win(["Presets", "Guide"])
        open_tools_tab(win, "guide")
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "Guide")


if __name__ == "__main__":
    unittest.main()
