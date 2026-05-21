"""FastAPI contract tests for Web control plane."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app_facade import BridgeAppFacade, WebCommandResult, WebConfigPayload, WebSessionState

try:
    from fastapi.testclient import TestClient
    from web_api import create_app

    _HAS_WEB = True
except ImportError:
    _HAS_WEB = False


@unittest.skipUnless(_HAS_WEB, "fastapi not installed")
class TestWebApi(unittest.TestCase):
    def setUp(self) -> None:
        self.facade = BridgeAppFacade()
        self.facade.update_snapshot(
            running=False,
            com_port="COM7",
            baud=115200,
            udp_listen_port=10110,
        )
        self.app = create_app(self.facade, version="1.7.0-test", lan_token=None)
        self.client = TestClient(self.app)

    def test_health(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_status(self) -> None:
        r = self.client.get("/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["com_port"], "COM7")
        self.assertFalse(body["running"])

    def test_get_config(self) -> None:
        self.facade.get_config = MagicMock(  # type: ignore[method-assign]
            return_value=WebConfigPayload(com_port="COM9", baud=9600)
        )
        r = self.client.get("/config")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["com_port"], "COM9")

    def test_start_validation_error(self) -> None:
        self.facade.request_start = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(False, "bad baud", "validation", "stopped")
        )
        r = self.client.post("/bridge/start")
        self.assertEqual(r.status_code, 400)

    def test_stop_ok(self) -> None:
        self.facade.request_stop = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(True, "stopped", None, "stopped")
        )
        r = self.client.post("/bridge/stop")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_patch_running_guard(self) -> None:
        self.facade.apply_config = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(
                False, "Stop first", "running_guard", "running"
            )
        )
        r = self.client.patch("/config", json={"com_port": "COM8"})
        self.assertEqual(r.status_code, 409)

    def test_unsupported_patch_via_facade(self) -> None:
        win = MagicMock()
        win._is_bridge_running.return_value = False
        result = self.facade._apply_config_on_main(win, {"fanout": True})
        self.assertEqual(result.error_code, "unsupported")


if __name__ == "__main__":
    unittest.main()
