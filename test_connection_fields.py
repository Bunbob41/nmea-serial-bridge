"""Tests for shared connection field validation."""
from __future__ import annotations

import unittest

from ui.connection_fields import parse_baud, validate_baud, validate_udp_port


class TestConnectionFields(unittest.TestCase):
    def test_parse_baud_valid(self) -> None:
        self.assertEqual(parse_baud("115200"), 115200)

    def test_validate_baud_invalid(self) -> None:
        self.assertIsNotNone(validate_baud("abc"))

    def test_validate_udp_port_range(self) -> None:
        self.assertIsNotNone(validate_udp_port("99999"))


if __name__ == "__main__":
    unittest.main()
