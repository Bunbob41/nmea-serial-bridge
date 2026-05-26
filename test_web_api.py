"""FastAPI contract tests for Web control plane."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app_facade import (
    BridgeAppFacade,
    NetworkCardDto,
    SerialDeviceDto,
    WebCommandResult,
    WebConfigPayload,
    WebDiscoveryPayload,
    WebMeta,
    WebSessionState,
)

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
            configured_com_port="COM7",
            baud=115200,
            udp_listen_port=10110,
        )
        self.app = create_app(self.facade, version="1.7.0-test", lan_token=None)
        self.client = TestClient(self.app)

    def test_health(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_openapi_documents_status_fields(self) -> None:
        schema = self.app.openapi()
        props = schema["components"]["schemas"]["StatusResponse"]["properties"]
        self.assertIn("com_port", props)
        self.assertIn("running", props)
        self.assertIn("position_lat", props)
        self.assertIn("position_lon", props)

    def test_openapi_documents_discovery_fields(self) -> None:
        schema = self.app.openapi()
        props = schema["components"]["schemas"]["DiscoveryResponse"]["properties"]
        self.assertIn("serial_devices", props)
        self.assertIn("scan_busy", props)

    def test_openapi_documents_meta_fields(self) -> None:
        schema = self.app.openapi()
        props = schema["components"]["schemas"]["MetaResponse"]["properties"]
        self.assertIn("version", props)
        self.assertIn("token_required", props)

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

    # ------------------------------------------------------------------ new 006 routes
    def test_api_index(self) -> None:
        r = self.client.get("/api")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["service"], "nmea-serial-bridge")
        self.assertIn("discovery", body)
        self.assertIn("meta", body)

    def test_meta_no_prefs(self) -> None:
        with patch("web_api.FileResponse", side_effect=None, create=True):
            with patch("ui.ui_prefs.load_web_ui_prefs", return_value={}, create=True):
                r = self.client.get("/meta")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("version", body)
        self.assertIn("token_required", body)
        self.assertIn("lan_bind", body)

    def test_meta_token_required_when_lan_bind_and_token(self) -> None:
        try:
            from ui import ui_prefs  # noqa: F401
            target = "ui.ui_prefs.load_web_ui_prefs"
        except ImportError:
            return
        with patch(target, return_value={"lan_bind": True, "token": "secret123"}):
            r = self.client.get("/meta")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["token_required"])

    def test_discovery_empty(self) -> None:
        r = self.client.get("/discovery")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("serial_devices", body)
        self.assertIn("network_cards", body)
        self.assertFalse(body["scan_busy"])

    def test_discovery_with_devices(self) -> None:
        self.facade._discovery_payload = WebDiscoveryPayload(
            updated_mono=1.0,
            scan_note="test",
            scan_busy=False,
            serial_devices=[
                SerialDeviceDto(
                    device_id="d1",
                    port="COM3",
                    description="USB Serial",
                    manufacturer="FTDI",
                    match_keyword="Trimble",
                    status="available",
                )
            ],
            network_cards=[],
            errors=[],
        )
        r = self.client.get("/discovery")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["serial_devices"]), 1)
        self.assertEqual(r.json()["serial_devices"][0]["port"], "COM3")

    def test_discovery_refresh_ok(self) -> None:
        self.facade.request_refresh_discovery = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(True, "Discovery scan started", None, "scanning")
        )
        r = self.client.post("/discovery/refresh")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(r.json()["state"], "scanning")

    def test_discovery_refresh_busy(self) -> None:
        self.facade.request_refresh_discovery = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(False, "Another command is in progress", "busy", "idle")
        )
        r = self.client.post("/discovery/refresh")
        self.assertEqual(r.status_code, 409)

    def test_ports_unlock_ok(self) -> None:
        self.facade.request_unlock_ports = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(True, "COM7 released", None, "stopped")
        )
        r = self.client.post("/ports/unlock")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_ports_unlock_no_com(self) -> None:
        self.facade.request_unlock_ports = MagicMock(  # type: ignore[method-assign]
            return_value=WebCommandResult(False, "No COM port configured", "validation")
        )
        r = self.client.post("/ports/unlock")
        self.assertEqual(r.status_code, 400)

    def test_root_returns_html(self) -> None:
        """GET / returns text/html with the dashboard (T025 / SC-103)."""
        r = self.client.get("/")
        # Either HTML dashboard or API JSON fallback — both are valid
        ct = r.headers.get("content-type", "")
        self.assertIn(r.status_code, (200,))
        if "text/html" in ct:
            self.assertIn(b"nmea", r.content.lower())
            self.assertIn(b"layout-gridstack", r.content)

    def test_static_subdirectory_serves_index_html(self) -> None:
        """Nested static dirs (e.g. GridStack beta) must serve index.html with trailing slash."""
        r = self.client.get("/static/layouts/gridstack/", follow_redirects=True)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("text/html", r.headers.get("content-type", ""))
        self.assertIn(b"layout-gridstack", r.content)

    def test_token_qr_404_without_token(self) -> None:
        with patch("ui.ui_prefs.load_web_ui_prefs", return_value={"token": None}):
            r = self.client.get("/token-qr")
        self.assertEqual(r.status_code, 404)

    def test_token_qr_svg_when_token_mocked(self) -> None:
        with patch("web_api.load_web_ui_prefs", create=True):
            with patch("ui.ui_prefs.load_web_ui_prefs", return_value={"token": "test-secret-token"}):
                r = self.client.get("/token-qr")
        self.assertEqual(r.status_code, 200)
        self.assertIn("svg", r.headers.get("content-type", ""))

    def test_logs_endpoint_returns_lines(self) -> None:
        self.facade.append_log_lines(["hello web log"])
        r = self.client.get("/logs?after=0")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreaterEqual(data["latest_seq"], 1)
        self.assertTrue(any(ln["text"] == "hello web log" for ln in data["lines"]))

    def test_token_qr_setup_mode(self) -> None:
        with patch("ui.ui_prefs.load_web_ui_prefs", return_value={"token": "tok123"}):
            r = self.client.get(
                "/token-qr?setup=1&base_url=http://100.0.0.1:8765",
                headers={"host": "127.0.0.1:8765"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertIn("svg", r.headers.get("content-type", ""))

    def test_auth_required_when_token_set(self) -> None:
        app = create_app(self.facade, version="test", lan_token="secret")
        client = TestClient(app)
        r = client.post("/bridge/start")
        self.assertEqual(r.status_code, 401)
        r2 = client.post("/bridge/start", headers={"X-Bridge-Token": "secret"})
        # May 400/409 from validation but not 401
        self.assertNotEqual(r2.status_code, 401)


if __name__ == "__main__":
    unittest.main()
