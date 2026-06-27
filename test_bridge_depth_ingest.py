import asyncio
import unittest

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode

_GGA = b"$GPGGA,032358.34,3600.42235,N,11846.36546,W,5,09,1.9,0.0,M,15.5,M,2.0,0000*51\r\n"
_GGA2 = b"$GPGGA,032359.34,3600.52235,N,11846.46546,W,5,09,1.9,0.0,M,15.5,M,2.0,0000*51\r\n"


def _sddpt(depth_m: float) -> str:
    body = f"SDDPT,{depth_m},0.0"
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


class TestBridgeDepthIngest(unittest.TestCase):
    def test_ingest_holds_depth_until_first_fix(self) -> None:
        loop = asyncio.new_event_loop()
        b = SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            udp_listen=("127.0.0.1", 10110),
            nmea_mode=NmeaMode.PASSTHROUGH,
            depth_com_enabled=True,
            depth_com_port="COM8",
        )
        b.running = True
        b._ingest_depth_line(_sddpt(4.0))
        self.assertEqual(b.sounding_stats()["sounding_count"], 0)
        b._ingest_net(_GGA, "UDP")
        self.assertEqual(b.sounding_stats()["sounding_count"], 1)
        b.abort_now()
        loop.close()

    def test_ingest_releases_on_subsequent_fix(self) -> None:
        loop = asyncio.new_event_loop()
        b = SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            udp_listen=("127.0.0.1", 10110),
            nmea_mode=NmeaMode.PASSTHROUGH,
            depth_com_enabled=True,
            depth_com_port="COM8",
        )
        b.running = True
        b._ingest_net(_GGA, "UDP")
        b._ingest_depth_line(_sddpt(5.0))
        self.assertEqual(b.sounding_stats()["sounding_count"], 0)
        b._ingest_net(_GGA2, "UDP")
        self.assertEqual(b.sounding_stats()["sounding_count"], 1)
        stats = b.sounding_stats()
        recent = stats["soundings_recent"]
        self.assertEqual(len(recent), 1)
        self.assertAlmostEqual(recent[0]["depth_m"], 5.0)
        b.abort_now()
        loop.close()


if __name__ == "__main__":
    unittest.main()
