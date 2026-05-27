"""Network options guide (Connect tab)."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.network_help import _NETWORK_HELP_MARKDOWN, show_network_options_help


class TestNetworkHelp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_help_markdown_covers_options(self) -> None:
        text = _NETWORK_HELP_MARKDOWN.lower()
        for phrase in (
            "listen host",
            "listen port",
            "fan-out",
            "extra tcp output",
            "advanced network",
        ):
            self.assertIn(phrase, text)

    def test_show_network_help_creates_dialog(self) -> None:
        win = QtWidgets.QWidget()
        dlg = show_network_options_help(win)
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.windowTitle(), "Network options guide")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
