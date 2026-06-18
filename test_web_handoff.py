"""Web dashboard handoff — desktop Phone tab ↔ static dashboard copy."""
from __future__ import annotations

import sys
import unittest
from unittest import mock

from PySide6 import QtWidgets

from ui.connect_qr_overlay import _phone_tools_tab_active, refresh_connect_qr_overlay
from ui.tool_tabs import PHONE_API_TOKEN_HELP, build_phone_dashboard_tab


class TestWebHandoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_phone_tab_includes_api_token_help(self) -> None:
        win = QtWidgets.QWidget()
        scroll = build_phone_dashboard_tab(win)
        labels = scroll.findChildren(QtWidgets.QLabel)
        texts = [lb.text() for lb in labels]
        self.assertIn(PHONE_API_TOKEN_HELP, texts)
        self.assertTrue(any("Allow LAN / Tailscale" in t for t in texts))
        self.assertTrue(any("Generate" in t for t in texts))

    def test_restore_web_ui_prefs_refreshes_phone_qr(self) -> None:
        from ui.mixin import BridgeLogicMixin

        win = QtWidgets.QWidget()
        win.chk_web_enabled = QtWidgets.QCheckBox()
        win.spin_web_port = QtWidgets.QSpinBox()
        win.chk_web_lan = QtWidgets.QCheckBox()
        win.edit_web_token = QtWidgets.QLineEdit()
        win.edit_web_phone_url = QtWidgets.QLineEdit()
        win.chk_web_show_qr = QtWidgets.QCheckBox()
        calls: list[str] = []
        win._refresh_phone_tab_qr = lambda: calls.append("qr")  # type: ignore[attr-defined]

        prefs = {
            "enabled": True,
            "port": 8765,
            "lan_bind": True,
            "token": "bench-token-abc",
            "phone_base_url": "http://100.64.0.1:8765",
        }
        with mock.patch("ui.ui_prefs.load_web_ui_prefs", return_value=prefs):
            BridgeLogicMixin._restore_web_ui_prefs(win)  # type: ignore[arg-type]
        self.assertEqual(calls, ["qr"])
        self.assertTrue(win.chk_web_show_qr.isChecked())

    def test_phone_tools_tab_hides_floating_qr(self) -> None:
        win = QtWidgets.QWidget()
        win.resize(400, 300)
        nav = QtWidgets.QListWidget()
        nav.addItem("Presets")
        nav.addItem("Phone")
        nav.setCurrentRow(1)
        win._tools_nav = nav  # type: ignore[attr-defined]
        win._connect_qr_api_active = True
        win._connect_qr_user_hidden = False
        win._refresh_phone_tab_qr = mock.Mock()
        win._web_token_from_ui = lambda: "tok"
        win._build_phone_setup_url = lambda: "http://127.0.0.1:8765/#bridge-token=tok"
        win.chk_web_enabled = QtWidgets.QCheckBox()
        win.chk_web_enabled.setChecked(True)
        win.chk_web_lan = QtWidgets.QCheckBox()
        win.chk_web_lan.setChecked(True)

        with mock.patch("ui.connect_qr_overlay.connect_qr_should_show", return_value=True):
            with mock.patch("ui.token_qr.make_token_qr_pixmap", return_value=None):
                refresh_connect_qr_overlay(win)

        floater = getattr(win, "_connect_qr_overlay", None)
        self.assertIsNotNone(floater)
        if floater is not None:
            self.assertFalse(floater.isVisible())
        self.assertTrue(_phone_tools_tab_active(win))
        win._refresh_phone_tab_qr.assert_called_once()

    def test_modern_ui_skips_floating_qr(self) -> None:
        win = QtWidgets.QWidget()
        win._ui_mode = "modern"  # type: ignore[attr-defined]
        win.chk_web_enabled = QtWidgets.QCheckBox()
        win.chk_web_enabled.setChecked(True)
        win.chk_web_lan = QtWidgets.QCheckBox()
        win.chk_web_lan.setChecked(True)
        calls: list[str] = []
        win._refresh_phone_tab_qr = lambda: calls.append("qr")  # type: ignore[attr-defined]
        win._sync_modern_phone_qr_btn = mock.Mock()  # type: ignore[attr-defined]

        with mock.patch("ui.connect_qr_overlay.connect_qr_should_show", return_value=True):
            refresh_connect_qr_overlay(win)

        floater = getattr(win, "_connect_qr_overlay", None)
        if floater is not None:
            self.assertFalse(floater.isVisible())
        self.assertEqual(calls, ["qr"])
        win._sync_modern_phone_qr_btn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
