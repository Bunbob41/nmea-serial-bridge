"""NTRIP client helpers."""
from __future__ import annotations

import asyncio
import unittest

from ntrip_client import (
    NtripConfig,
    _read_http_header,
    build_ntrip_request,
    parse_caster_host,
)


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

    def test_read_http_header_keeps_body_tail(self) -> None:
        async def _run() -> None:
            payload = (
                b"HTTP/1.0 200 OK\r\nContent-Type: application/octet-stream\r\n\r\n"
                b"\xd3\x00\x08"
            )
            reader = asyncio.StreamReader()
            reader.feed_data(payload)
            reader.feed_eof()
            header, initial = await _read_http_header(reader)
            self.assertIn("200 OK", header)
            self.assertEqual(initial, b"\xd3\x00\x08")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
