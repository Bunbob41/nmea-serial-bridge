import unittest

from nmea_codec import (
    NmeaLineAssembler,
    NmeaMode,
    nmea_checksum_ok,
    parse_nmea_utc,
)


class TestNmeaChecksum(unittest.TestCase):
    def test_valid_gga(self) -> None:
        line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        self.assertTrue(nmea_checksum_ok(line))

    def test_invalid_checksum(self) -> None:
        line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00"
        self.assertFalse(nmea_checksum_ok(line))

    def test_missing_star(self) -> None:
        self.assertFalse(nmea_checksum_ok("$GPGGA,123519*"))


class TestLineAssembler(unittest.TestCase):
    def test_tcp_fragmentation(self) -> None:
        asm = NmeaLineAssembler()
        line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        a = asm.feed(line[:20].encode(), NmeaMode.PASSTHROUGH)
        self.assertEqual(a.forward, [])
        b = asm.feed(line[20:].encode(), NmeaMode.PASSTHROUGH)
        self.assertEqual(len(b.forward), 1)
        self.assertIn("$GPGGA", b.forward[0].decode())

    def test_strict_drops_bad(self) -> None:
        asm = NmeaLineAssembler()
        bad = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00\r\n"
        r = asm.feed(bad, NmeaMode.STRICT)
        self.assertEqual(r.forward, [])
        self.assertTrue(r.rejected)

    def test_strict_drops_non_nmea(self) -> None:
        asm = NmeaLineAssembler()
        r = asm.feed(b"HELLO\r\n", NmeaMode.STRICT)
        self.assertEqual(r.forward, [])
        self.assertTrue(any("not NMEA" in x for x in r.rejected))

    def test_passthrough_non_nmea(self) -> None:
        asm = NmeaLineAssembler()
        r = asm.feed(b"HELLO\r\n", NmeaMode.PASSTHROUGH)
        self.assertEqual(len(r.forward), 1)

    def test_lf_only(self) -> None:
        asm = NmeaLineAssembler()
        line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n"
        r = asm.feed(line.encode(), NmeaMode.PASSTHROUGH)
        self.assertEqual(len(r.forward), 1)
        self.assertTrue(r.forward[0].endswith(b"\r\n"))


class TestParseUtc(unittest.TestCase):
    def test_rmc(self) -> None:
        line = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        u = parse_nmea_utc(line)
        self.assertIsNotNone(u)
        self.assertIn("RMC", u or "")


if __name__ == "__main__":
    unittest.main()
