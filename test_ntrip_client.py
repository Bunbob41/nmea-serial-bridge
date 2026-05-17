"""NTRIP client helpers."""
from __future__ import annotations

import unittest

from ntrip_client import NtripConfig, build_ntrip_request, parse_caster_host


class TestNtripClient(unittest.TestCase):
    def test_build_request_includes_mount_and_auth(self) -> None:
        cfg = NtripConfig(
            host="caster.test",
            port=2101,
            mountpoint="MOUNT1",
            username="user",
            password="pass",
        )
        req = build_ntrip_request(cfg).decode("ascii")
        self.assertIn("GET /MOUNT1 HTTP/1.0", req)
        self.assertIn("Authorization: Basic", req)

    def test_parse_caster_host(self) -> None:
        host, port = parse_caster_host("rtk.example.com:2102")
        self.assertEqual(host, "rtk.example.com")
        self.assertEqual(port, 2102)


if __name__ == "__main__":
    unittest.main()
