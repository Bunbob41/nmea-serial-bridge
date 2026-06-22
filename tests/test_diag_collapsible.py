"""Diagnostics ios-card expand/collapse (no stuck strip height)."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.tool_tabs import (
    _DIAG_CARD_EXPANDED_CAP,
    _DIAG_COLLAPSED_STRIP_MIN,
    _IosCollapsibleCard,
    _diag_card_natural_height,
    _diag_collapsed_strip_height,
)


class TestDiagCollapsible(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_expand_shows_body_after_blocked_check(self) -> None:
        card = _IosCollapsibleCard("Rotating file log", start_open=False)
        body = card._body
        bl = card.body_layout()
        bl.addWidget(QtWidgets.QLabel("line"))
        btn = card.toggle_button()
        btn.blockSignals(True)
        btn.setChecked(True)
        self.assertEqual(body.maximumHeight(), 0)
        card.set_expanded(True)
        card.show()
        self._app.processEvents()
        self.assertTrue(body.isVisibleTo(card))
        self.assertGreater(body.maximumHeight(), 0)

    def test_screen_log_stays_compact(self) -> None:
        card = _IosCollapsibleCard("On-screen log", start_open=True)
        bl = card.body_layout()
        bl.addWidget(QtWidgets.QPushButton("Clear live log panel"))
        card.show()
        self._app.processEvents()
        h = _diag_card_natural_height(card, "screen_log")
        self.assertLessEqual(h, _DIAG_CARD_EXPANDED_CAP["screen_log"])

    def test_toggle_open_close_heights(self) -> None:
        card = _IosCollapsibleCard("On-screen log", start_open=False)
        bl = card.body_layout()
        edit = QtWidgets.QPlainTextEdit()
        edit.setMinimumHeight(80)
        bl.addWidget(edit)
        card.show()
        self._app.processEvents()
        closed_h = card.height()
        card.set_expanded(True)
        self._app.processEvents()
        open_h = card.height()
        self.assertGreater(open_h, closed_h + 40)

        card.set_expanded(False)
        self._app.processEvents()
        self.assertLessEqual(card.height(), closed_h + 8)
        self.assertLessEqual(card.maximumHeight(), closed_h + 8)

    def test_collapsed_strip_respects_minimum(self) -> None:
        card = _IosCollapsibleCard("Rotating file log", start_open=False)
        card.show()
        self._app.processEvents()
        self.assertGreaterEqual(card.height(), _DIAG_COLLAPSED_STRIP_MIN)
        btn = card.toggle_button()
        m = card.layout().contentsMargins()
        self.assertGreaterEqual(_diag_collapsed_strip_height(btn, m), _DIAG_COLLAPSED_STRIP_MIN)


if __name__ == "__main__":
    unittest.main()
