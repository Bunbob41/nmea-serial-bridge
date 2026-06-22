"""Guard against re-entrant layout switching crashes."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from ui.layout_cycle import other_layout_ids
from ui.mixin import BridgeLogicMixin


class TestLayoutCycleMenu(unittest.TestCase):
    def test_other_layout_ids_excludes_current(self) -> None:
        self.assertEqual(other_layout_ids("field"), ("modern",))
        self.assertEqual(other_layout_ids("modern"), ("field",))
        self.assertEqual(other_layout_ids("standard"), ("modern",))

    def test_refresh_switch_layout_menu_shows_two_targets(self) -> None:
        host = object.__new__(BridgeLogicMixin)
        host._ui_mode = "modern"
        host.bridge = None
        host._worker = None
        act_field = MagicMock()
        act_standard = MagicMock()
        act_modern = MagicMock()
        host._layout_switch_actions = {
            "standard": act_standard,
            "field": act_field,
            "modern": act_modern,
        }
        host._refresh_switch_layout_menu()
        act_standard.setVisible.assert_called_with(False)
        act_field.setVisible.assert_called_with(True)
        act_modern.setVisible.assert_called_with(False)


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
        self.quit_requested = False
        self._stats_timer = type("_T", (), {"stop": lambda self: None})()
        self._stats_popout_window = None
        self._dashboard_window = None

    def close(self) -> None:
        self.closed = True

    def _request_application_quit(self) -> None:
        self.quit_requested = True


class TestUiLayoutSwitch(unittest.TestCase):
    def test_switch_layout_ignores_reentry(self) -> None:
        host = _LayoutHost()
        with patch("ui.mixin.save_ui_choice") as save_choice, patch(
            "ui.mixin.create_window", return_value=_FakeWindow()
        ) as create, patch.object(host, "_teardown_all_background_work") as teardown, patch(
            "ui.tray_support.destroy_tray_icon"
        ):
            self.assertTrue(host._switch_ui_layout("field"))
            self.assertFalse(host._switch_ui_layout("field"))
        self.assertTrue(host.closed)
        self.assertTrue(host._layout_switch_in_progress)
        self.assertFalse(host.quit_requested)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(save_choice.call_count, 1)
        teardown.assert_called()

    def test_switch_layout_returns_false_when_bridge_running(self) -> None:
        host = _LayoutHost()
        host.bridge = object()
        with patch.object(host, "_close_auxiliary_windows"), patch(
            "ui.mixin.create_window", return_value=_FakeWindow()
        ) as create, patch("ui.mixin.QtWidgets.QMessageBox.information"):
            self.assertFalse(host._switch_ui_layout("field"))
        self.assertFalse(host.closed)
        create.assert_not_called()

    def test_switch_layout_stops_background_before_new_window(self) -> None:
        host = _LayoutHost()
        calls: list[str] = []

        def _teardown(**_kwargs: object) -> None:
            calls.append("teardown")

        def _create(_ui: str) -> _FakeWindow:
            calls.append("create")
            return _FakeWindow()

        with patch("ui.mixin.save_ui_choice"), patch(
            "ui.mixin.create_window", side_effect=_create
        ), patch.object(host, "_teardown_all_background_work", side_effect=_teardown), patch(
            "ui.tray_support.destroy_tray_icon"
        ):
            host._switch_ui_layout("field")
        self.assertEqual(calls, ["teardown", "create"])

    def test_close_event_during_layout_switch_does_not_quit_app(self) -> None:
        host = _LayoutHost()
        host._layout_switch_in_progress = True
        event = type("_E", (), {"accept": lambda self: None, "ignore": lambda self: None})()
        with patch.object(host, "_teardown_all_background_work"):
            host.closeEvent(event)  # type: ignore[arg-type]
        self.assertFalse(host.quit_requested)


if __name__ == "__main__":
    unittest.main()
