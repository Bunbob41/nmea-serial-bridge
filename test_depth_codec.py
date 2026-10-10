"""Unit tests for depth_codec.parse_depth_line."""
from __future__ import annotations

import unittest

from depth_codec import depth_display_field, parse_depth_line


def _with_checksum(body: str) -> str:
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


class TestDepthCodec(unittest.TestCase):
    def test_sddpt(self) -> None:
        line = _with_checksum("SDDPT,5.2,0.5")
        sample = parse_depth_line(line)
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 5.2)

    def test_sonarmite_ascii(self) -> None:
        # Ohmex SM3hardware.pdf p.16 sample: "id depth roll pitch heave battery qa flags".
        # Depth is field 1 (0.48 m); 8.9 is the battery voltage.
        sample = parse_depth_line("1 0.48 0 0 0 8.9 115 0")
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 0.48)

    def test_sonarmite_battery_glitch_does_not_change_depth(self) -> None:
        # Same sample block, battery reading 17.8 V: depth is still 0.48 m.
        sample = parse_depth_line("1 0.48 0 0 0 17.8 116 0")
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 0.48)

    def test_sonarmite_format0_example(self) -> None:
        sample = parse_depth_line("1 1.88 0 0 0.0 12.7 128 20")
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 1.88)

    def test_sonarmite_dfx_high_frequency_depth(self) -> None:
        # DFXhardware.pdf p.19: "id hdepth ldepth wtemp battery flags"; flags 7 = Hi+Lo+Wt seen.
        sample = parse_depth_line("1 28.55 29.25 15.15 10.9 7")
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 28.55)

    def test_sonarmite_no_reading_is_none(self) -> None:
        for line in (
            "0 0 0 0 0 0 0 0",          # Old layout, nulls: no transducer / out of water
            "1 0.48 0 0 0 8.9 4 0",     # qa below 5
            "1 0 0 0 0 8.9 115 0",      # depth 0
            "1 28.55 29.25 15.15 10.9 6",  # DFX, high-frequency depth not seen
            "1 0 0 0 0 0",              # DFX nulls
            "1 0.48 8.9",               # unknown layout (3 fields): never guessed
        ):
            with self.subTest(line=line):
                self.assertIsNone(parse_depth_line(line))

    def test_depth_display_field_preserves_decimals(self) -> None:
        sample = parse_depth_line("1 0.480 0 0 0 8.54 115 0")
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertEqual(depth_display_field(sample), "0.480")
        line = _with_checksum("SDDPT,7.56,0.5")
        sample2 = parse_depth_line(line)
        self.assertIsNotNone(sample2)
        assert sample2 is not None
        self.assertEqual(depth_display_field(sample2), "7.56")


if __name__ == "__main__":
    unittest.main()