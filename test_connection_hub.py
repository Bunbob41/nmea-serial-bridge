"""Qt tests for Connection Hub card selection."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from discovery_service import DiscoverySnapshot, NetworkCardInfo, SerialDeviceInfo
from ui.connection_hub import ConnectionHubWidget


class TestConnectionHubWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not QtWidgets.QApplication.instance():
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

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


if __name__ == "__main__":
    unittest.main()
