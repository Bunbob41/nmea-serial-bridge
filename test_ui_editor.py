"""UI editor migrations and connect panel visibility."""
from __future__ import annotations

import unittest

from unittest.mock import MagicMock

from ui.connect_panels import DEFAULT_CONNECT_HIDDEN, sanitize_connect_panel_hidden
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
        hidden = migrate_topbar_hidden({"demo", "randomize_theme"})
        self.assertNotIn("demo", hidden)
        self.assertIn("randomize_theme", hidden)

    def test_default_connect_hidden_includes_ntrip(self) -> None:
        self.assertIn("ntrip", DEFAULT_CONNECT_HIDDEN)

    def test_required_connect_panels_never_hidden(self) -> None:
        out = sanitize_connect_panel_hidden(["connection", "ntrip", "run"])
        self.assertEqual(out, ["ntrip"])

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
        self.assertIn("reset_sizes", ids)

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
