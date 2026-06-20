"""Fleet panel row summary helpers."""
from __future__ import annotations

import unittest

from bridge_core import NetMode
from core.fleet.config import StreamDefinition
from ui.fleet_panel import (
    com_summary,
    stream_mirror_summary,
    stream_mode_summary,
)


class FleetPanelSummaryTests(unittest.TestCase):
    def test_com_summary_uppercases_port(self) -> None:
        stream = StreamDefinition.new("GPS", com="com7", baud=57600)
        self.assertEqual(com_summary(stream), "COM7 @ 57600")

    def test_stream_mode_summary_raw_fanout(self) -> None:
        stream = StreamDefinition.new(
            "MAVLink",
            nmea_mode="raw",
            net_mode=NetMode.UDP_LISTEN.value,
            udp_fanout=True,
        )
        self.assertEqual(stream_mode_summary(stream), "Raw · fan-out")

    def test_stream_mode_summary_passthrough(self) -> None:
        stream = StreamDefinition.new("NMEA", nmea_mode="passthrough", udp_fanout=False)
        self.assertEqual(stream_mode_summary(stream), "PassThru")

    def test_stream_mirror_summary_with_device_tx(self) -> None:
        stream = StreamDefinition.new(
            "Sniff",
            com="COM7",
            serial_mirror_ports=["COM12"],
            serial_mirror_device_tx=True,
        )
        self.assertEqual(stream_mirror_summary(stream), "COM12 +TX")

    def test_stream_mirror_summary_empty(self) -> None:
        stream = StreamDefinition.new("Plain")
        self.assertEqual(stream_mirror_summary(stream), "—")


if __name__ == "__main__":
    unittest.main()
