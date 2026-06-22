"""Fleet panel row summary helpers."""
from __future__ import annotations

import unittest

from bridge_core import NetMode
from core.fleet.config import StreamDefinition
from ui.fleet_panel import (
    com_summary,
    net_tooltip,
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

    def test_net_tooltip_tailscale_guidance(self) -> None:
        stream = StreamDefinition.new(
            "MAVLink",
            net_mode=NetMode.UDP_LISTEN.value,
            udp_host="0.0.0.0",
            udp_port=14550,
            udp_fanout=True,
        )
        tip = net_tooltip(stream)
        self.assertIn("Tailscale", tip)
        self.assertIn("14550", tip)

    def test_net_tooltip_warns_loopback(self) -> None:
        stream = StreamDefinition.new(
            "Bench",
            net_mode=NetMode.UDP_LISTEN.value,
            udp_host="127.0.0.1",
            udp_port=14550,
        )
        tip = net_tooltip(stream)
        self.assertIn("loopback", tip.lower())


if __name__ == "__main__":
    unittest.main()
