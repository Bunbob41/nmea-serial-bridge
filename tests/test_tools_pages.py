"""Modern Tools page summaries."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets

from ui.backup_status import format_activity_page_status, format_presets_page_status
from ui.modern import BridgeWindowModern


class TestToolsPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_presets_summary_shows_session(self) -> None:
        win = BridgeWindowModern()
        line, _tip, kind = format_presets_page_status(win)
        self.assertTrue(
            line.startswith("Session UI:") or line.startswith("Loaded:"),
            line,
        )
        self.assertIn(kind, ("idle", "ok", "warn"))

    def test_presets_preview_before_load(self) -> None:
        from bench_config import load_preset
        from ui.backup_status import format_presets_page_status

        win = BridgeWindowModern()
        names = win.preset_list.count()
        self.assertGreater(names, 0)
        # Pick a preset that is not the active one if possible
        target_row = 0
        for i in range(win.preset_list.count()):
            item = win.preset_list.item(i)
            if item and item.text() != (win._active_preset_name or ""):
                target_row = i
                break
        win.preset_list.setCurrentRow(target_row)
        item = win.preset_list.currentItem()
        self.assertIsNotNone(item)
        name = item.text().strip()
        win._select_preset_for_editing(name)
        line, tip, kind = format_presets_page_status(win)
        data = load_preset(name)
        self.assertIn("Preview", line)
        self.assertIn(str(data.get("com", "")), line)
        self.assertEqual(kind, "warn")
        notes = str(data.get("notes") or "").strip()
        if notes:
            self.assertIn(notes, tip)

    def test_activity_summary_empty_when_stopped(self) -> None:
        win = BridgeWindowModern()
        line, _tip, kind = format_activity_page_status(win)
        self.assertIn("empty", line.lower())
        self.assertEqual(kind, "idle")

    def test_modern_tools_has_activity_sidebar_page(self) -> None:
        win = BridgeWindowModern()
        self.assertIn("activity", win._tools_section_index)
        page = win._tools_stack.widget(win._tools_section_index["activity"])
        self.assertEqual(page.objectName(), "modernLiveActivityPage")


if __name__ == "__main__":
    unittest.main()
