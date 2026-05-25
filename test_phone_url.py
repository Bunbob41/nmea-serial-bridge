"""Tests for phone dashboard URL helpers."""
import unittest

from web.phone_url import (
    is_loopback_base,
    normalize_phone_base_url,
    suggest_phone_base_urls,
)


class TestPhoneUrl(unittest.TestCase):
    def test_loopback_detected(self) -> None:
        self.assertTrue(is_loopback_base("http://127.0.0.1:8765"))
        self.assertFalse(is_loopback_base("http://100.1.2.3:8765"))

    def test_normalize_strips_token_fragment(self) -> None:
        raw = "http://127.0.0.1:8765/#bridge-token=abc"
        self.assertEqual(normalize_phone_base_url(raw), "http://127.0.0.1:8765")

    def test_suggest_includes_port(self) -> None:
        urls = suggest_phone_base_urls(8765)
        for u in urls:
            self.assertIn(":8765", u)
            self.assertFalse(is_loopback_base(u))


if __name__ == "__main__":
    unittest.main()
