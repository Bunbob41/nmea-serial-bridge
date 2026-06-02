"""Tests for phone dashboard URL helpers."""
import unittest
from unittest.mock import patch

from web.phone_url import (
    _parse_tailscale_stdout_ipv4,
    _tailscale_ipv4,
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

    def test_parse_tailscale_mixed_output(self) -> None:
        raw = "100.64.1.2\nfd7a:115c:a1e0::1\n"
        self.assertEqual(_parse_tailscale_stdout_ipv4(raw), ["100.64.1.2"])

    def test_tailscale_ipv4_falls_back_when_dash4_fails(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            class R:
                returncode = 1 if cmd[-1] == "-4" else 0
                stdout = "100.99.88.77\n" if cmd[-1] == "ip" else ""

            return R()

        with patch("web.phone_url.subprocess.run", side_effect=fake_run):
            ips = _tailscale_ipv4()
        self.assertEqual(ips, ["100.99.88.77"])
        self.assertEqual(calls[0], ["tailscale", "ip", "-4"])
        self.assertEqual(calls[1], ["tailscale", "ip"])


if __name__ == "__main__":
    unittest.main()
