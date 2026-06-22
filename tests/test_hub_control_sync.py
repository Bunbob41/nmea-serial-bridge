"""Hub ↔ Control COM alignment (Modern Connection Hub)."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from discovery_service import DiscoverySnapshot, SerialDeviceInfo
from ui.qt_test_harness import close_all_qt_widgets, ensure_qt_app


class TestHubControlSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = ensure_qt_app(sys.argv)

    @classmethod
    def tearDownClass(cls) -> None:
        close_all_qt_widgets()

    def _snap(self) -> DiscoverySnapshot:
        return DiscoverySnapshot(
            serial_devices=[
                SerialDeviceInfo("serial:a", "COM3", "Trimble", "", "Trimble", "available"),
                SerialDeviceInfo("serial:b", "COM13", "U-blox", "", "U-blox", "available"),
            ],
            network_cards=[],
        )

    def test_lkg_without_com_still_updates_control(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        lkg = {"udp_host": "0.0.0.0", "udp_port": 10110, "net_mode": "udp_listen"}
        with patch("ui.ui_prefs.load_last_known_good", return_value=lkg):
            win._on_hub_selection("serial:b")
        self.assertEqual(win.com_cb.currentText().strip().upper(), "COM13")

    def test_start_uses_hub_when_operator_picked_tile(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        win._set_com_cb_port("COM3")
        hub._on_card_clicked("serial:b")
        win._manual_override_dirty = False
        self.assertTrue(win._should_apply_hub_for_start())

    def test_start_prefers_control_when_manual_override_dirty(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        win._set_com_cb_port("COM3")
        hub._on_card_clicked("serial:b")
        win._manual_override_dirty = True
        self.assertFalse(win._should_apply_hub_for_start())

    def test_launch_sync_moves_hub_to_control_preset(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        win._set_com_cb_port("COM3")
        win._sync_hub_selection_from_control_on_launch()
        self.assertEqual(hub.selected_device_id(), "serial:a")
        self.assertTrue(hub._cards["serial:a"].property("selected"))

    def test_reconcile_keeps_hub_pick_when_not_manual_override(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        win._set_com_cb_port("COM3")
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        win._manual_override_dirty = False
        win._apply_hub_discovery_snapshot(self._snap())
        self.assertEqual(hub.selected_device_id(), "serial:b")
        self.assertEqual(win.com_cb.currentText().strip().upper(), "COM13")

    def test_reconcile_respects_control_when_manual_override(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        win._set_com_cb_port("COM3")
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        win._manual_override_dirty = True
        win._apply_hub_discovery_snapshot(self._snap())
        self.assertEqual(hub.selected_device_id(), "serial:a")

    def test_serial_hub_lkg_does_not_restore_listen_port(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        win.udp_port.setText("14550")
        win._control_network_dirty = True
        lkg = {"com": "COM13", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 10110}
        with patch("ui.ui_prefs.load_last_known_good", return_value=lkg):
            win._on_hub_selection("serial:b")
        self.assertEqual(win.udp_port.text(), "14550")

    def test_start_hub_serial_preserves_control_listen_port(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        win.udp_port.setText("14550")
        win._control_network_dirty = True
        win._manual_override_dirty = False
        lkg = {"com": "COM13", "baud": 115200, "udp_host": "0.0.0.0", "udp_port": 10110}
        with patch("ui.ui_prefs.load_last_known_good", return_value=lkg):
            win._apply_hub_selection_for_start()
        self.assertEqual(win.udp_port.text(), "14550")
        self.assertEqual(win.com_cb.currentText().strip().upper(), "COM13")

    def test_preset_load_wins_over_hub_tile_on_reconcile(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub = win.connection_hub
        hub.set_snapshot(self._snap())
        hub._on_card_clicked("serial:b")
        win._apply_com_preset("COM3", 115200, "0.0.0.0", 14550)
        win._manual_override_dirty = True
        win._apply_hub_discovery_snapshot(self._snap())
        self.assertEqual(win.com_cb.currentText().strip().upper(), "COM3")


if __name__ == "__main__":
    unittest.main()
