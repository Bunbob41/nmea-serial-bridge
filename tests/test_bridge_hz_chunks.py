"""Hz counters track NMEA sentences per second, not wire chunks per packet."""
from __future__ import annotations

import asyncio
import unittest

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode


class TestHzSentenceRate(unittest.IsolatedAsyncioTestCase):
    async def test_udp_datagram_counts_per_sentence(self) -> None:
        loop = asyncio.get_running_loop()
        bridge = SerialNetBridge(
            "COM1",
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=("127.0.0.1", 10110),
            loop=loop,
            nmea_mode=NmeaMode.PASSTHROUGH,
        )
        bridge.running = True
        gga = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        bridge.on_udp_datagram(gga + rmc, ("127.0.0.1", 9999))
        self.assertEqual(bridge.lines_remote_to_serial, 2)
        self.assertEqual(len(bridge._hz_remote_times), 2)

    async def test_serial_read_counts_per_sentence(self) -> None:
        loop = asyncio.get_running_loop()
        bridge = SerialNetBridge(
            "COM1",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            nmea_mode=NmeaMode.PASSTHROUGH,
        )
        bridge.running = True
        chunk = (
            b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
            b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        )
        bridge._ingest_serial(chunk, "SER→NET")
        self.assertEqual(bridge.lines_serial_to_net, 2)
        self.assertEqual(len(bridge._hz_serial_times), 2)

    async def test_repeated_sentences_increase_hz_ticks(self) -> None:
        loop = asyncio.get_running_loop()
        bridge = SerialNetBridge("COM1", 115200, NetMode.UDP_LISTEN, loop=loop)
        bridge.running = True
        line = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        for _ in range(8):
            bridge._ingest_serial(line, "SER→NET")
        self.assertEqual(len(bridge._hz_serial_times), 8)


    async def test_strict_reject_still_counts_ingress_hz(self) -> None:
        loop = asyncio.get_running_loop()
        from nmea_codec import NmeaFilter

        bridge = SerialNetBridge(
            "COM1",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            nmea_mode=NmeaMode.STRICT,
            nmea_filter=NmeaFilter(enabled_types={"GGA"}),
        )
        bridge.running = True
        gga = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        bridge.on_udp_datagram(gga + rmc, ("127.0.0.1", 9999))
        self.assertEqual(bridge.lines_remote_to_serial, 1)
        self.assertEqual(bridge.rejected_net_to_serial, 1)
        self.assertEqual(len(bridge._hz_remote_times), 2)
        self.assertEqual(len(bridge._hz_fix_n2s_times), 1)

    async def test_marine_burst_counts_one_gga_hz_per_datagram(self) -> None:
        """Typical 1 Hz INS burst: many sentences, one GGA position epoch per datagram."""
        loop = asyncio.get_running_loop()
        bridge = SerialNetBridge(
            "COM1",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            nmea_mode=NmeaMode.PASSTHROUGH,
        )
        bridge.running = True
        burst = (
            b"$HCHDT,123.4,T*00\r\n"
            b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
            b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
            b"$GPVTG,054.7,T,034.4,M,005.5,N,010.2,K*48\r\n"
        )
        bridge.on_udp_datagram(burst, ("127.0.0.1", 9999))
        self.assertEqual(len(bridge._hz_remote_times), 4)
        self.assertEqual(len(bridge._hz_fix_n2s_times), 1)
        self.assertEqual(bridge.hz_fix_to_serial(), 1.0)


if __name__ == "__main__":
    unittest.main()
