"""Tests for Linux headless entry point and façade."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from headless_facade import HeadlessBridgeFacade
from serial_link_headless import build_arg_parser, run_headless
from web_facade_types import WebConfigPayload

try:
    from fastapi.testclient import TestClient
    from web_api import create_app

    _HAS_WEB = True
except ImportError:
    _HAS_WEB = False


class TestSerialLinkHeadlessArgparse(unittest.TestCase):
    def test_defaults_linux_serial(self) -> None:
        with patch("sys.platform", "linux"):
            args = build_arg_parser().parse_args([])
        self.assertEqual(args.serial, "/dev/ttyUSB0")
        self.assertEqual(args.web_port, 8765)
        self.assertEqual(args.nmea_mode, "passthrough")

    def test_defaults_windows_serial(self) -> None:
        with patch("sys.platform", "win32"):
            args = build_arg_parser().parse_args([])
        self.assertEqual(args.serial, "COM7")

    def test_cli_overrides(self) -> None:
        args = build_arg_parser().parse_args(
            [
                "--serial",
                "/dev/ttyACM0",
                "--baud",
                "9600",
                "--udp-port",
                "20110",
                "--web-port",
                "9876",
                "--lan-bind",
                "--token",
                "test-token",
            ]
        )
        self.assertEqual(args.serial, "/dev/ttyACM0")
        self.assertEqual(args.baud, 9600)
        self.assertEqual(args.udp_port, 20110)
        self.assertEqual(args.web_port, 9876)
        self.assertTrue(args.lan_bind)
        self.assertEqual(args.token, "test-token")


class TestHeadlessFacade(unittest.TestCase):
    def test_commands_ready(self) -> None:
        facade = HeadlessBridgeFacade(WebConfigPayload(com_port="/dev/ttyUSB0"))
        self.assertTrue(facade.commands_ready())

    def test_apply_config_while_stopped(self) -> None:
        facade = HeadlessBridgeFacade(WebConfigPayload(com_port="/dev/ttyUSB0"))
        result = facade.apply_config({"baud": 9600, "udp_listen_port": 20110})
        self.assertTrue(result.ok)
        cfg = facade.get_config()
        self.assertEqual(cfg.baud, 9600)
        self.assertEqual(cfg.udp_listen_port, 20110)

    def test_start_without_serial_fails_validation(self) -> None:
        facade = HeadlessBridgeFacade(WebConfigPayload(com_port=""))
        result = facade.request_start()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "validation")


@unittest.skipUnless(_HAS_WEB, "fastapi not installed")
class TestHeadlessWebServer(unittest.TestCase):
    def test_dashboard_health_via_facade(self) -> None:
        facade = HeadlessBridgeFacade(
            WebConfigPayload(com_port="/dev/ttyUSB0", udp_listen_port=10110)
        )
        app = create_app(facade, version="test-headless", lan_token=None)
        client = TestClient(app)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ok"])
        meta = client.get("/meta")
        self.assertEqual(meta.status_code, 200)
        self.assertTrue(meta.json()["commands_ready"])
        status = client.get("/status")
        self.assertEqual(status.status_code, 200)
        body = status.json()
        self.assertFalse(body["running"])
        self.assertEqual(body["configured_com_port"], "/dev/ttyUSB0")

    def test_run_headless_starts_web_nonblocking(self) -> None:
        with patch("web_server.WebServerThread") as ServerCls, patch(
            "web_api.create_app"
        ) as create_app_mock:
            create_app_mock.return_value = object()
            server = ServerCls.return_value
            args = build_arg_parser().parse_args(["--web-port", "18765"])
            with patch("web_server.port_is_free", return_value=True):
                code = run_headless(args, block=False)
            self.assertEqual(code, 0)
            server.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
