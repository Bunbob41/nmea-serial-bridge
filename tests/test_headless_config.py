"""Tests for headless site config resolution."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from headless_config import (
    HeadlessRuntimeConfig,
    discover_config_path,
    load_site_config,
    resolve_headless_config,
    runtime_to_site_dict,
    save_site_config,
)
from serial_link_headless import build_arg_parser


class TestHeadlessSiteConfig(unittest.TestCase):
    def test_load_nested_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.json"
            path.write_text(
                json.dumps(
                    {
                        "serial": {"port": "/dev/ttyACM0", "baud": 9600},
                        "network": {"mode": "udp_listen", "udp_port": 20110},
                        "web": {"lan_bind": True, "token": "secret", "port": 9876},
                        "bridge": {"autostart": False},
                    }
                ),
                encoding="utf-8",
            )
            data = load_site_config(path)
            self.assertEqual(data["serial"]["port"], "/dev/ttyACM0")

    def test_resolve_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.json"
            path.write_text(
                json.dumps(
                    {
                        "serial": {"port": "/dev/gnss", "baud": 115200},
                        "network": {"udp_port": 10110},
                        "web": {"lan_bind": False, "port": 8765},
                    }
                ),
                encoding="utf-8",
            )
            parser = build_arg_parser()
            argv = ["--config", str(path)]
            args = parser.parse_args(argv)
            cfg = resolve_headless_config(args, argv=argv)
            self.assertEqual(cfg.serial, "/dev/gnss")
            self.assertEqual(cfg.udp_port, 10110)
            self.assertFalse(cfg.lan_bind)
            self.assertFalse(cfg.start_bridge)

    def test_cli_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.json"
            path.write_text(
                json.dumps({"serial": {"port": "/dev/ttyUSB0"}, "network": {"udp_port": 10110}}),
                encoding="utf-8",
            )
            parser = build_arg_parser()
            argv = ["--config", str(path), "--serial", "/dev/ttyUSB1"]
            args = parser.parse_args(argv)
            cfg = resolve_headless_config(args, argv=argv)
            self.assertEqual(cfg.serial, "/dev/ttyUSB1")

    def test_env_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.json"
            path.write_text(
                json.dumps({"serial": {"port": "/dev/ttyUSB0"}, "network": {"udp_port": 10110}}),
                encoding="utf-8",
            )
            parser = build_arg_parser()
            argv = ["--config", str(path)]
            args = parser.parse_args(argv)
            with patch.dict("os.environ", {"SERIAL_LINK_UDP_PORT": "14550"}):
                cfg = resolve_headless_config(args, argv=argv)
            self.assertEqual(cfg.udp_port, 14550)

    def test_lan_bind_generates_token(self) -> None:
        parser = build_arg_parser()
        argv = ["--lan-bind"]
        args = parser.parse_args(argv)
        cfg = resolve_headless_config(args, argv=argv)
        self.assertTrue(cfg.lan_bind)
        self.assertGreaterEqual(len(cfg.token), 16)

    def test_discover_config_path_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.json"
            path.write_text("{}", encoding="utf-8")
            with patch.dict("os.environ", {"CONFIG_FILE": str(path)}):
                found = discover_config_path()
            self.assertEqual(found, path)

    def test_runtime_to_site_dict_roundtrip(self) -> None:
        cfg = HeadlessRuntimeConfig(
            config_path=Path("/tmp/bridge.json"),
            serial="/dev/ttyUSB0",
            baud=115200,
            udp_host="0.0.0.0",
            udp_port=10110,
            network_mode="udp_listen",
            remote_host="",
            remote_port=0,
            nmea_mode="passthrough",
            web_host="0.0.0.0",
            web_port=8765,
            lan_bind=True,
            token="secret-token",
            start_bridge=False,
        )
        payload = runtime_to_site_dict(cfg)
        self.assertEqual(payload["serial"]["port"], "/dev/ttyUSB0")
        self.assertEqual(payload["web"]["token"], "secret-token")
        self.assertFalse(payload["bridge"]["autostart"])

    def test_save_site_config_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "bridge.json"
            cfg = HeadlessRuntimeConfig(
                config_path=path,
                serial="/dev/ttyACM0",
                baud=9600,
                udp_host="0.0.0.0",
                udp_port=20110,
                network_mode="udp_listen",
                remote_host="",
                remote_port=0,
                nmea_mode="strict",
                web_host="127.0.0.1",
                web_port=8765,
                lan_bind=False,
                token="",
                start_bridge=True,
            )
            save_site_config(path, cfg)
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["serial"]["port"], "/dev/ttyACM0")
            self.assertEqual(data["network"]["udp_port"], 20110)
            self.assertTrue(data["bridge"]["autostart"])


if __name__ == "__main__":
    unittest.main()
