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
        sample = parse_depth_line("1 0.48 0 0 0 8.9 115 0")
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.depth_m, 8.9)

    def test_depth_display_field_preserves_decimals(self) -> None:
        sample = parse_depth_line("1 0.48 0 0 0 8.54 115 0")
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertEqual(depth_display_field(sample), "8.54")
        line = _with_checksum("SDDPT,7.56,0.5")
        sample2 = parse_depth_line(line)
        self.assertIsNotNone(sample2)
        assert sample2 is not None
        self.assertEqual(depth_display_field(sample2), "7.56")


if __name__ == "__main__":
    unittest.main()