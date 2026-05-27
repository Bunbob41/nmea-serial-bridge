"""Guard against re-entrant layout switching crashes."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from ui.mixin import BridgeLogicMixin


class _FakeWindow:
    def _apply_theme(self, _theme: str, persist: bool = False) -> None:
        _ = persist

    def show(self) -> None:
        pass

    def raise_(self) -> None:
        pass

    def activateWindow(self) -> None:
        pass


class _LayoutHost(BridgeLogicMixin, object):
    def __init__(self) -> None:
        self.bridge = None
        self._worker = None
        self._ui_mode = "standard"
        self._theme_id = "slate"
        self._layout_switch_in_progress = False
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestUiLayoutSwitch(unittest.TestCase):
    def test_switch_layout_ignores_reentry(self) -> None:
        host = _LayoutHost()
        with patch("ui.mixin.save_ui_choice") as save_choice, patch(
            "ui.mixin.create_window", return_value=_FakeWindow()
        ) as create:
            host._switch_ui_layout("field")
            host._switch_ui_layout("field")
        self.assertTrue(host.closed)
        self.assertTrue(host._layout_switch_in_progress)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(save_choice.call_count, 1)


if __name__ == "__main__":
    unittest.main()
