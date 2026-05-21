"""Tests for BridgeAppFacade snapshot and config helpers."""
from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock

from app_facade import BridgeAppFacade, WebSessionState


class TestBridgeAppFacade(unittest.TestCase):
    def test_snapshot_updates_and_thread_reads(self) -> None:
        facade = BridgeAppFacade()
        facade._facade_publish_interval_s = 0
        facade.update_snapshot(running=True, com_port="COM7", baud=115200)
        self.assertTrue(facade.get_status().running)
        facade.update_snapshot(running=False)
        self.assertFalse(facade.get_status().running)

        def reader() -> None:
            for _ in range(20):
                _ = facade.get_status().com_port

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_get_config_without_window(self) -> None:
        facade = BridgeAppFacade()
        cfg = facade.get_config()
        self.assertEqual(cfg.com_port, "")

    def test_unsupported_config_patch(self) -> None:
        facade = BridgeAppFacade()
        win = MagicMock()
        win._is_bridge_running.return_value = False
        result = facade._apply_config_on_main(win, {"ntrip_caster": "x"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unsupported")


if __name__ == "__main__":
    unittest.main()
