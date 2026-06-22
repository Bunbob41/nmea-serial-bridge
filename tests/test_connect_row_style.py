"""Connect section row style (pill / seamless / outline / accent)."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui.collapsible import DisclosureRow
from ui.connect_panels import _configure_connect_disclosure_row
from ui.connect_row_style import (
    CONNECT_ROW_SEAMLESS,
    apply_connect_row_style,
    normalize_connect_row_style,
)


class TestConnectRowStyle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_normalize_connect_row_style(self) -> None:
        self.assertEqual(normalize_connect_row_style("Seamless"), CONNECT_ROW_SEAMLESS)
        self.assertEqual(normalize_connect_row_style("bogus"), "pill")

    def test_apply_connect_row_style_sets_host_property(self) -> None:
        host = QtWidgets.QWidget()
        host.setObjectName("connectPanelHost")
        win = QtWidgets.QWidget()
        win._connect_panel_host = host  # noqa: SLF001 — test stub
        style_id = apply_connect_row_style(win, CONNECT_ROW_SEAMLESS)
        self.assertEqual(style_id, CONNECT_ROW_SEAMLESS)
        self.assertEqual(host.property("connectRowStyle"), CONNECT_ROW_SEAMLESS)

    def test_configure_connect_disclosure_row_disables_autoraise(self) -> None:
        body = QtWidgets.QWidget()
        row = DisclosureRow("Test", body, button_object_name="connectPanelDisclosure")
        _configure_connect_disclosure_row(row)
        self.assertFalse(row.tool_button().autoRaise())


if __name__ == "__main__":
    unittest.main()
