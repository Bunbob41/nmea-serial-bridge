"""Theme quick-pick context menu."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6 import QtWidgets

from ui.theme_quick_menu import (
    BUILTIN_THEME_QUICK_PICK_IDS,
    populate_theme_quick_pick_menu,
)
from ui.theme_choice import THEME_SLATE


class TestThemeQuickPickMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_builtin_palette_ids_exclude_random(self) -> None:
        self.assertIn(THEME_SLATE, BUILTIN_THEME_QUICK_PICK_IDS)
        self.assertNotIn("random_current", BUILTIN_THEME_QUICK_PICK_IDS)

    def test_populate_menu_adds_builtin_and_studio(self) -> None:
        host = MagicMock()
        host._theme_id = THEME_SLATE
        menu = QtWidgets.QMenu()
        populate_theme_quick_pick_menu(menu, host)
        labels = [a.text() for a in menu.actions() if not a.isSeparator()]
        self.assertIn("Built-in palettes", labels)
        self.assertIn("Open Theme studio…", labels)
        builtin = next(a for a in menu.actions() if a.text() == "Built-in palettes")
        sub_labels = [a.text() for a in builtin.menu().actions()]
        self.assertGreaterEqual(len(sub_labels), 6)


if __name__ == "__main__":
    unittest.main()
