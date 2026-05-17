"""Raw (binary) bridge mode — no line assembly."""
import asyncio
import unittest

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode


class TestBridgeRawMode(unittest.TestCase):
    def test_raw_net_to_serial_no_newline_required(self) -> None:
        loop = asyncio.new_event_loop()
        b = SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=("127.0.0.1", 10110),
            nmea_mode=NmeaMode.RAW,
            loop=loop,
        )
        b.running = True
        payload = b"\x02\x00\xa0\x14\xff"
        b._ingest_net(payload, "UDP←('127.0.0.1', 9999)")
        self.assertEqual(b.net_to_serial.qsize(), 1)
        self.assertEqual(b.net_to_serial.get_nowait(), payload)

    def test_raw_serial_to_net(self) -> None:
        loop = asyncio.new_event_loop()
        b = SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            nmea_mode=NmeaMode.RAW,
            loop=loop,
        )
        b.running = True
        payload = b"\x01\x02\x03"
        b._ingest_serial(payload, "SER→NET")
        self.assertEqual(b.serial_to_net.qsize(), 1)
        self.assertEqual(b.serial_to_net.get_nowait(), payload)


if __name__ == "__main__":
    unittest.main()
