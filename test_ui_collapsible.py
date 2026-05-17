"""Tests for disclosure collapse / dialog reflow."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.collapsible import DisclosureRow, enable_dialog_content_fit, reflow_window


class TestDisclosureReflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_collapse_shrinks_dialog(self) -> None:
        dlg = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dlg)
        body = QtWidgets.QWidget()
        bl = QtWidgets.QVBoxLayout(body)
        lbl = QtWidgets.QLabel("Line one\nLine two\nLine three\nLine four")
        lbl.setWordWrap(True)
        bl.addWidget(lbl)
        row = DisclosureRow("Details", body, dlg, start_open=False)
        lay.addWidget(row)
        enable_dialog_content_fit(dlg, min_width=320)
        dlg.show()
        self._app.processEvents()
        reflow_window(dlg)
        self._app.processEvents()
        closed_h = dlg.height()

        row.tool_button().setChecked(True)
        self._app.processEvents()
        reflow_window(dlg)
        self._app.processEvents()
        open_h = dlg.height()
        self.assertGreater(open_h, closed_h)

        row.tool_button().setChecked(False)
        self._app.processEvents()
        reflow_window(dlg)
        self._app.processEvents()
        self.assertLessEqual(dlg.height(), closed_h + 4)


if __name__ == "__main__":
    unittest.main()
