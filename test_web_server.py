"""Web control plane port helpers."""
from __future__ import annotations

import socket
import unittest

from web_server import port_is_free, port_is_in_use, wait_port_free


class TestWebServerPortHelpers(unittest.TestCase):
    def test_port_is_in_use_when_listening(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(8)
        try:
            port = sock.getsockname()[1]
            self.assertTrue(port_is_in_use(port, lan_bind=False))
            self.assertFalse(port_is_free(port, lan_bind=False))
        finally:
            sock.close()

    def test_wait_port_free_after_close(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        sock.close()
        self.assertTrue(wait_port_free(port, lan_bind=False, timeout=1.0))


if __name__ == "__main__":
    unittest.main()
