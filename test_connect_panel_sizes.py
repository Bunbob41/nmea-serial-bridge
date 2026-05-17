"""Connect panel splitter: collapsed strips stay minimal; expanded sizes persist."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ui import connect_panels, ui_prefs


def _mock_row(expanded: bool) -> MagicMock:
    row = MagicMock()
    btn = MagicMock()
    btn.isChecked.return_value = expanded
    row.tool_button.return_value = btn
    return row


class _MockWin:
    def __init__(self, order: list[str], sizes: list[int], expanded: dict[str, bool]) -> None:
        self._ui_mode = "standard"
        self._connect_panel_order = order
        self._connect_panel_disclosures = {k: _mock_row(expanded[k]) for k in order}
        self._connect_panel_splitter = MagicMock()
        self._connect_panel_splitter.sizes.return_value = sizes


class ConnectPanelSizesTests(unittest.TestCase):
    def test_normalize_all_collapsed_opens_expanded(self) -> None:
        order = list(connect_panels.CONNECT_PANEL_KEYS)
        collapsed = {k: True for k in order}
        out_c, out_s, use_def = connect_panels._normalize_connect_launch_prefs(
            collapsed, {"run": 26, "hint": 28}, order
        )
        self.assertEqual(out_c, {})
        self.assertEqual(out_s, {})
        self.assertTrue(use_def)

    def test_normalize_keeps_partial_collapse(self) -> None:
        order = ["run", "quick_log", "connection"]
        collapsed = {"quick_log": True}
        sizes = {"run": 80, "connection": 260}
        out_c, out_s, use_def = connect_panels._normalize_connect_launch_prefs(collapsed, sizes, order)
        self.assertTrue(out_c.get("quick_log"))
        self.assertEqual(out_s, sizes)
        self.assertFalse(use_def)

    def test_persist_skips_collapsed_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs(
                    "standard",
                    ["run", "quick_log"],
                    {"quick_log": True},
                    sizes={"run": 200, "quick_log": 140},
                )
                win = _MockWin(
                    ["run", "quick_log"],
                    [26, 140],
                    {"run": False, "quick_log": True},
                )
                connect_panels._persist_connect_splitter_sizes(win)  # type: ignore[arg-type]
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["sizes"].get("run"), 200)
                self.assertEqual(loaded["sizes"].get("quick_log"), 140)

    def test_capture_before_collapse_keeps_expanded_height(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs("standard", ["quick_log"], {}, sizes={})
                win = _MockWin(["quick_log"], [180], {"quick_log": True})
                connect_panels._capture_expanded_size_from_splitter(win, "quick_log")  # type: ignore[arg-type]
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["sizes"].get("quick_log"), 180)

    def test_apply_sizes_uses_strip_for_collapsed(self) -> None:
        splitter = MagicMock()
        splitter.count.return_value = 2
        splitter.height.return_value = 500
        win = MagicMock()
        win._connect_panel_splitter = splitter
        win._connect_panel_order = ["run", "quick_log"]
        win._connect_panel_disclosures = {
            "run": _mock_row(True),
            "quick_log": _mock_row(False),
        }
        win._ui_mode = "standard"
        with patch.object(
            connect_panels,
            "load_connect_panel_prefs",
            return_value={"collapsed": {"quick_log": True}, "sizes": {"run": 80}},
        ):
            connect_panels._apply_connect_splitter_sizes(win)
        sizes_arg = splitter.setSizes.call_args[0][0]
        self.assertEqual(sizes_arg[1], connect_panels._COLLAPSED_STRIP_HEIGHT)


if __name__ == "__main__":
    unittest.main()
