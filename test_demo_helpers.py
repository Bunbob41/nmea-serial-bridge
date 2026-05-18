"""Product demo helpers — open Tools drawer tabs by alias."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.demo import _open_tools


class TestDemoHelpers(unittest.TestCase):
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

    def test_open_send_selects_terminal_tab(self) -> None:
        win = self._make_win(["Presets", "Terminal", "Diagnostics"])
        _open_tools(win, "send")
        self.assertTrue(win._drawer_btn.isChecked())  # type: ignore[attr-defined]
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "Terminal")

    def test_open_terminal_alias(self) -> None:
        win = self._make_win(["Presets", "Terminal", "Diagnostics"])
        _open_tools(win, "terminal")
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.currentIndex(), 1)

    def test_open_diag_aliases(self) -> None:
        win = self._make_win(["Presets", "Diagnostics"])
        _open_tools(win, "diagnostics")
        tabs = win._drawer_tabs  # type: ignore[attr-defined]
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "Diagnostics")


if __name__ == "__main__":
    unittest.main()
