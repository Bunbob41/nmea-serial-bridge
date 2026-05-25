"""UI editor migrations and connect panel visibility."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets
from unittest.mock import MagicMock

from ui.connect_panels import (
    DEFAULT_CONNECT_HIDDEN,
    RECOMMENDED_CONNECT_PANEL_ORDER,
    connect_panel_layout_changed,
    connect_toolbar_order_changed,
    sanitize_connect_panel_hidden,
)
from ui.survey_top_bar import normalize_topbar_order
from ui.ui_editor import (
    MAIN_TAB_HINTS,
    build_connect_panel_editor_rows,
    build_connect_toolbar_rows,
    build_main_tab_editor_rows,
    migrate_topbar_hidden,
    migrate_topbar_order,
)


class TestUiEditor(unittest.TestCase):
    def test_migrate_demo_to_ui_editor(self) -> None:
        order = migrate_topbar_order(["view", "demo", "hud"])
        self.assertEqual(order[0], "view")
        self.assertIn("ui_editor", order)
        self.assertNotIn("demo", order)

    def test_migrate_hidden_drops_demo(self) -> None:
        hidden = migrate_topbar_hidden({"demo", "randomize_theme", "hidden_tabs"})
        self.assertNotIn("demo", hidden)
        self.assertNotIn("hidden_tabs", hidden)
        self.assertIn("randomize_theme", hidden)

    def test_migrate_order_drops_hidden_tabs_chip(self) -> None:
        order = migrate_topbar_order(["view", "hidden_tabs", "hud"])
        self.assertNotIn("hidden_tabs", order)
        self.assertIn("hud", order)

    def test_migrate_order_matches_normalize(self) -> None:
        raw = ["view", "demo", "hidden_tabs", "hud", "ui_editor"]
        self.assertEqual(migrate_topbar_order(raw), normalize_topbar_order(raw))

    def test_recommended_connect_order_puts_connection_second(self) -> None:
        self.assertEqual(RECOMMENDED_CONNECT_PANEL_ORDER[0], "run")
        self.assertEqual(RECOMMENDED_CONNECT_PANEL_ORDER[1], "connection")

    def test_ui_editor_dialog_builds(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        from ui.ui_editor import UiEditorDialog

        class W(QtWidgets.QWidget):
            _ui_mode = "standard"
            _connect_panel_widgets = {
                "run": QtWidgets.QWidget(),
                "connection": QtWidgets.QWidget(),
            }
            _tab_catalog = {
                "main_tabs": {
                    "Connect": (QtWidgets.QWidget(), ""),
                    "Log": (QtWidgets.QWidget(), ""),
                    "Tools": (QtWidgets.QWidget(), ""),
                }
            }
            _tab_hidden = {"main_tabs": set()}

        dlg = UiEditorDialog(W())
        self.assertGreaterEqual(dlg._tabs.count(), 3)

    def test_ntrip_not_in_connect_panel_catalog(self) -> None:
        from ui.connect_panels import CONNECT_PANEL_KEYS, OMITTED_CONNECT_PANELS

        self.assertNotIn("ntrip", CONNECT_PANEL_KEYS)
        self.assertIn("ntrip", OMITTED_CONNECT_PANELS)
        self.assertNotIn("ntrip", DEFAULT_CONNECT_HIDDEN)

    def test_required_connect_panels_never_hidden(self) -> None:
        out = sanitize_connect_panel_hidden(["connection", "hint", "run"])
        self.assertEqual(out, ["hint"])

    def test_connect_panel_rows_keep_required_visible(self) -> None:
        rows = build_connect_panel_editor_rows("standard")
        by_id = {r[0]: r for r in rows}
        self.assertTrue(by_id["run"][3])
        self.assertTrue(by_id["connection"][3])

    def test_connect_toolbar_rows_present(self) -> None:
        rows = build_connect_toolbar_rows("standard")
        ids = [r[0] for r in rows]
        self.assertIn("ui_editor", ids)
        self.assertIn("expand_all", ids)
        self.assertIn("collapse_all", ids)
        self.assertNotIn("reset_sizes", ids)

    def test_connect_layout_changed_only_when_order_or_hidden_differs(self) -> None:
        prefs = {
            "order": ["run", "connection", "hint"],
            "hidden": ["quick_log"],
        }
        self.assertFalse(
            connect_panel_layout_changed(
                ["run", "connection", "hint"], ["quick_log"], prefs
            )
        )
        self.assertTrue(
            connect_panel_layout_changed(
                ["connection", "run", "hint"], ["quick_log"], prefs
            )
        )
        self.assertFalse(
            connect_toolbar_order_changed(
                ["ui_editor", "expand_all", "collapse_all"], prefs
            )
        )

    def test_main_tab_rows_use_tab_names_not_empty_tooltips(self) -> None:
        catalog = {
            "Connect": (MagicMock(), ""),
            "Log": (MagicMock(), ""),
            "Terminal": (MagicMock(), "Inject test NMEA while Running"),
        }
        rows = build_main_tab_editor_rows(catalog, set())
        by_id = {r[0]: r for r in rows}
        self.assertEqual(by_id["Connect"][1], "Connect")
        self.assertTrue(by_id["Connect"][2])  # subtitle from MAIN_TAB_HINTS
        self.assertIn("COM", by_id["Connect"][2])
        self.assertIn("Inject", by_id["Terminal"][2])


if __name__ == "__main__":
    unittest.main()
