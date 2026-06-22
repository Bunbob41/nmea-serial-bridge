"""Tests for phone dashboard setup URLs."""
import unittest

from web.token_setup import build_setup_url, normalize_base_url, parse_token_from_text


class TestTokenSetup(unittest.TestCase):
    def test_normalize_adds_http(self) -> None:
        self.assertEqual(normalize_base_url("100.1.2.3:8765"), "http://100.1.2.3:8765")

    def test_build_setup_url_fragment(self) -> None:
        url = build_setup_url("http://100.108.156.78:8765", "abc/def+token")
        self.assertTrue(url.startswith("http://100.108.156.78:8765/#bridge-token="))
        self.assertIn("abc%2Fdef%2Btoken", url)

    def test_parse_token_from_setup_url(self) -> None:
        url = build_setup_url("http://100.1.2.3:8765", "my-secret-token-xyz")
        self.assertEqual(parse_token_from_text(url), "my-secret-token-xyz")

    def test_parse_token_raw(self) -> None:
        raw = "a" * 32
        self.assertEqual(parse_token_from_text(raw), raw)

    def test_parse_token_hash_only(self) -> None:
        self.assertEqual(parse_token_from_text("#bridge-token=abc123"), "abc123")


if __name__ == "__main__":
    unittest.main()
