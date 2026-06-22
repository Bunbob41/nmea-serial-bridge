"""bench_config preset helpers."""
from __future__ import annotations

import unittest

import bench_config as bc


class TestBenchConfigHelpers(unittest.TestCase):
    def test_desk_udp_send_host_local_bind(self) -> None:
        self.assertEqual(
            bc.desk_udp_send_host({"udp_host": "0.0.0.0", "udp_port": 10110}),
            "127.0.0.1",
        )
        self.assertEqual(
            bc.desk_udp_send_host({"udp_host": "192.168.5.2", "udp_port": 10110}),
            "192.168.5.2",
        )


if __name__ == "__main__":
    unittest.main()
