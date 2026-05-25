"""Qt tests for Connection Hub card selection."""
from __future__ import annotations

import unittest

from discovery_service import DiscoverySnapshot, NetworkCardInfo, SerialDeviceInfo
from ui.connection_hub import ConnectionHubWidget
from ui.qt_test_harness import close_all_qt_widgets, ensure_qt_app


class TestConnectionHubWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = ensure_qt_app([])

    @classmethod
    def tearDownClass(cls) -> None:
        close_all_qt_widgets()

    def test_snapshot_renders_and_click_emits(self) -> None:
        hub = ConnectionHubWidget()
        emitted: list[str] = []
        hub.selection_changed.connect(emitted.append)
        snap = DiscoverySnapshot(
            serial_devices=[
                SerialDeviceInfo("serial:a", "COM7", "Trimble", "", "Trimble", "available"),
                SerialDeviceInfo("serial:b", "COM9", "U-blox", "", "U-blox", "available"),
            ],
            network_cards=[
                NetworkCardInfo(
                    "net:udp:0.0.0.0:10110",
                    "UDP listen",
                    "udp_listen",
                    "0.0.0.0",
                    10110,
                    True,
                    0,
                    "ready",
                )
            ],
        )
        hub.set_snapshot(snap)
        self.assertEqual(len(hub._cards), 3)
        hub._on_card_clicked("serial:b")
        self.assertEqual(emitted, ["serial:b"])
        self.assertEqual(hub.selected_device_id(), "serial:b")

    def test_refresh_unlock_signals(self) -> None:
        hub = ConnectionHubWidget()
        refreshed: list[bool] = []
        unlocked: list[bool] = []
        hub.refresh_requested.connect(lambda: refreshed.append(True))
        hub.unlock_requested.connect(lambda: unlocked.append(True))
        hub.btn_refresh.click()
        hub.btn_unlock.click()
        self.assertEqual(refreshed, [True])
        self.assertEqual(unlocked, [True])

    def test_standalone_cards_viewport_two_rows(self) -> None:
        hub = ConnectionHubWidget(standalone=True)
        expected = (
            ConnectionHubWidget._CARD_ROW_HEIGHT * ConnectionHubWidget._CARDS_VISIBLE_ROWS
            + (ConnectionHubWidget._CARDS_VISIBLE_ROWS - 1) * 8
        )
        self.assertEqual(hub._card_scroll.minimumHeight(), expected)
        self.assertEqual(hub._card_scroll.maximumHeight(), expected)
        self.assertIsNone(hub._splitter)

    def test_column_count_wide(self) -> None:
        hub = ConnectionHubWidget()
        hub.resize(800, 400)
        self.assertGreaterEqual(hub._column_count_for_width(), 2)


if __name__ == "__main__":
    unittest.main()
