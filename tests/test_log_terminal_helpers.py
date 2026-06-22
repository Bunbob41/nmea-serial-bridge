"""Bridge terminal helpers — hex preview and log sentence filter."""
import unittest

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import (
    NmeaMode,
    format_binary_log_preview,
    log_line_matches_sentence_filter,
)
from ui.log_view import (
    LogViewState,
    PRESET_OPS,
    format_wire_tap_live_log_line,
    log_line_allowed,
)


class TestFormatBinaryLogPreview(unittest.TestCase):
    def test_short_payload(self) -> None:
        self.assertEqual(format_binary_log_preview(b"\x02\x00\xa0"), "02 00 a0 (3 B)")

    def test_truncates(self) -> None:
        data = bytes(range(40))
        out = format_binary_log_preview(data, max_bytes=4)
        self.assertIn("(40 B)", out)
        self.assertIn("…", out)


class TestLogSentenceFilter(unittest.TestCase):
    def test_all_passes(self) -> None:
        line = "UDP← | gps=— | $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        self.assertTrue(log_line_matches_sentence_filter(line, ""))

    def test_gga_only(self) -> None:
        gga = "SER→NET | gps=— | $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        rmc = "SER→NET | gps=— | $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        self.assertTrue(log_line_matches_sentence_filter(gga, "GGA"))
        self.assertFalse(log_line_matches_sentence_filter(rmc, "GGA"))

    def test_non_nmea_lines_pass(self) -> None:
        self.assertTrue(log_line_matches_sentence_filter("=== BRIDGE RUNNING ===", "GGA"))


class TestBridgeRawHexLog(unittest.TestCase):
    def test_verbose_hex_preview(self) -> None:
        loop = __import__("asyncio").new_event_loop()
        lines: list[str] = []
        try:
            b = SerialNetBridge(
                "COM99",
                115200,
                NetMode.UDP_LISTEN,
                udp_listen=("127.0.0.1", 10110),
                nmea_mode=NmeaMode.RAW,
                loop=loop,
                ui_log=lines.append,
                ui_log_verbose=lambda: True,
                ui_log_hex=lambda: True,
            )
            b.running = True
            payload = b"\x02\x00\xa0\x14"
            b._ingest_net(payload, "UDP←('127.0.0.1', 9999)")
            self.assertEqual(1, len(lines))
            self.assertIn("02 00 a0 14 (4 B)", lines[0])
        finally:
            loop.close()


class TestWireTapLiveLogLine(unittest.TestCase):
    def test_com_net_hex_preview(self) -> None:
        line = format_wire_tap_live_log_line(
            "com→net",
            b"\xfd\x09\x00",
            hex_mode=True,
        )
        self.assertIn("SER→NET", line)
        self.assertIn("fd 09 00", line)

    def test_ops_preset_allows_hex_wire_line(self) -> None:
        line = format_wire_tap_live_log_line("com→net", b"\xfd\x09", hex_mode=True)
        state = LogViewState(preset=PRESET_OPS, verbose=False)
        self.assertTrue(log_line_allowed(line, state))


if __name__ == "__main__":
    unittest.main()
