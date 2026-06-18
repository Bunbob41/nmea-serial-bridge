import unittest

from nmea_codec import (
    NMEA_SENTENCE_TYPES,
    NmeaFilter,
    NmeaLineAssembler,
    NmeaMode,
    nmea_checksum_ok,
    nmea_sentence_type,
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

    def test_strict_reject_counts_ingress(self) -> None:
        asm = NmeaLineAssembler()
        filt = NmeaFilter(enabled_types={"GGA"})
        gga = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        r = asm.feed(gga + rmc, NmeaMode.STRICT, filt)
        self.assertEqual(r.ingress_lines, 2)
        self.assertEqual(r.ingress_fix_lines, 1)
        self.assertEqual(len(r.forward), 1)
        self.assertEqual(len(r.rejected), 1)


class TestNmeaSentenceType(unittest.TestCase):
    def test_sddpt_is_dpt_not_dbt(self) -> None:
        """Sounder depth: $SDDPT → type DPT (common sim output; not DBT)."""
        cs = 0
        body = "SDDPT,5.0,0.0"
        for ch in body:
            cs ^= ord(ch)
        line = f"${body}*{cs:02X}"
        self.assertEqual(nmea_sentence_type(line), "DPT")
        self.assertIn("DPT", NMEA_SENTENCE_TYPES)
        self.assertNotIn("DBT", NMEA_SENTENCE_TYPES)
        self.assertTrue(NmeaFilter(enabled_types={"DPT"}).allows_sentence(line))


class TestNmeaFilter(unittest.TestCase):
    def test_filter_gga_only(self) -> None:
        filt = NmeaFilter(enabled_types={"GGA"})
        asm = NmeaLineAssembler()
        gga = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        r1 = asm.feed(gga, NmeaMode.STRICT, filt)
        self.assertEqual(len(r1.forward), 1)
        r2 = asm.feed(rmc, NmeaMode.STRICT, filt)
        self.assertEqual(len(r2.forward), 0)
        self.assertTrue(r2.rejected)


class TestParseUtc(unittest.TestCase):
    def test_rmc(self) -> None:
        line = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        u = parse_nmea_utc(line)
        self.assertIsNotNone(u)
        self.assertIn("RMC", u or "")


if __name__ == "__main__":
    unittest.main()
