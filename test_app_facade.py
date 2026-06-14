"""Tests for BridgeAppFacade snapshot and config helpers."""
from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QWidget

from app_facade import (
    BridgeAppFacade,
    SerialDeviceDto,
    WebCommandResult,
    WebDiscoveryPayload,
    WebSessionState,
    classify_web_log_line,
)


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

    def test_window_via_parent_without_attach(self) -> None:
        app = QApplication.instance() or QApplication([])
        win = QWidget()
        win._is_bridge_running = lambda: False  # type: ignore[attr-defined]
        facade = BridgeAppFacade(win)
        self.assertIs(facade._window(), win)
        self.assertTrue(facade.commands_ready())

    def test_get_config_without_window(self) -> None:
        facade = BridgeAppFacade()
        cfg = facade.get_config()
        self.assertEqual(cfg.com_port, "")

    def test_apply_config_network_mode_tcp_client(self) -> None:
        facade = BridgeAppFacade()
        win = MagicMock()
        win._is_bridge_running.return_value = False
        win.com_cb.findText.return_value = 0
        win.chk_advanced_net = MagicMock()
        win.rb_udp_listen = MagicMock()
        win.rb_udp_remote = MagicMock()
        win.rb_tcp_client = MagicMock()
        win.rb_tcp_server = MagicMock()
        win.remote_host = MagicMock()
        win.remote_port = MagicMock()
        win.tcp_cli_host = MagicMock()
        win.tcp_cli_port = MagicMock()
        win.udp_host = MagicMock()
        win.udp_port = MagicMock()
        win._mode_toggle = MagicMock()
        result = facade._apply_config_on_main(
            win,
            {
                "network_mode": "tcp_client",
                "remote_host": "10.0.0.1",
                "remote_port": 5000,
                "udp_listen_host": "0.0.0.0",
                "udp_listen_port": 10110,
            },
        )
        self.assertTrue(result.ok)
        win.chk_advanced_net.setChecked.assert_called_with(True)
        win.rb_tcp_client.setChecked.assert_called_with(True)
        win.tcp_cli_host.setText.assert_called_with("10.0.0.1")
        win.tcp_cli_port.setText.assert_called_with("5000")
        win.rb_udp_listen.setChecked.assert_not_called()

    def test_read_config_tcp_client_remote_fields(self) -> None:
        facade = BridgeAppFacade()
        win = MagicMock()
        win.com_cb.currentText.return_value = "COM7"
        win.baud_edit = MagicMock()
        win.chk_advanced_net = MagicMock()
        win.chk_advanced_net.isChecked.return_value = True
        win.rb_tcp_server = MagicMock()
        win.rb_tcp_server.isChecked.return_value = False
        win.rb_tcp_client = MagicMock()
        win.rb_tcp_client.isChecked.return_value = True
        win.rb_udp_remote = MagicMock()
        win.rb_udp_remote.isChecked.return_value = False
        win.udp_host = MagicMock()
        win.udp_host.text.return_value = "0.0.0.0"
        win.udp_port = MagicMock()
        win.udp_port.text.return_value = "10110"
        win.tcp_cli_host = MagicMock()
        win.tcp_cli_host.text.return_value = "10.0.0.5"
        win.tcp_cli_port = MagicMock()
        win.tcp_cli_port.text.return_value = "4001"
        with patch("ui.connection_fields.read_baud_widget", return_value="115200"):
            with patch("ui.connection_fields.parse_baud", return_value=115200):
                cfg = facade._read_config_from_window(win)
        self.assertEqual(cfg.network_mode, "tcp_client")
        self.assertEqual(cfg.remote_host, "10.0.0.5")
        self.assertEqual(cfg.remote_port, 4001)

    def test_apply_config_com_port_wins_over_hub_lkg(self) -> None:
        facade = BridgeAppFacade()
        win = MagicMock()
        win._is_bridge_running.return_value = False
        win.com_cb.findText.return_value = -1
        win.connection_hub = MagicMock()
        applied: list[str] = []

        def hub_select(_device_id: str) -> None:
            win.com_cb.setCurrentText("COM1")

        win._on_hub_selection = MagicMock(side_effect=hub_select)
        win.com_cb.setCurrentText.side_effect = lambda t: applied.append(t)
        result = facade._apply_config_on_main(
            win,
            {"hub_device_id": "serial:bench", "com_port": "COM7"},
        )
        self.assertTrue(result.ok)
        win._on_hub_selection.assert_called_once()
        self.assertEqual(applied[-1], "COM7")

    def test_unsupported_config_patch(self) -> None:
        facade = BridgeAppFacade()
        win = MagicMock()
        win._is_bridge_running.return_value = False
        result = facade._apply_config_on_main(win, {"ntrip_caster": "x"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unsupported")

    def test_request_start_from_worker_thread(self) -> None:
        app = QApplication.instance() or QApplication([])
        facade = BridgeAppFacade()
        win = MagicMock()
        win._validate_before_start.return_value = None
        win._is_bridge_running.return_value = True
        facade.attach_window(win)
        result_box: dict[str, object] = {}

        def worker() -> None:
            result_box["result"] = facade.request_start()

        thread = threading.Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 5.0
        while thread.is_alive() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        thread.join(timeout=1.0)
        self.assertFalse(thread.is_alive())
        result = result_box.get("result")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.ok)
        win.start_bridge.assert_called_once()

    def test_get_config_from_worker_thread(self) -> None:
        app = QApplication.instance() or QApplication([])
        facade = BridgeAppFacade()
        win = MagicMock()
        win.com_cb.currentText.return_value = "COM7"
        win.baud_edit.currentText.return_value = "115200"
        win.udp_host.text.return_value = "0.0.0.0"
        win.udp_port.text.return_value = "10110"
        win.chk_advanced_net = None
        facade.attach_window(win)
        result_box: dict[str, object] = {}

        def worker() -> None:
            result_box["cfg"] = facade.get_config()

        thread = threading.Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 5.0
        while thread.is_alive() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        thread.join(timeout=1.0)
        self.assertFalse(thread.is_alive())
        cfg = result_box.get("cfg")
        self.assertIsNotNone(cfg)
        assert cfg is not None
        self.assertEqual(cfg.com_port, "COM7")


    # ------------------------------------------------------------------ discovery cache
    def test_discovery_cache_default_empty(self) -> None:
        facade = BridgeAppFacade()
        d = facade.get_discovery()
        self.assertIsInstance(d, WebDiscoveryPayload)
        self.assertEqual(len(d.serial_devices), 0)
        self.assertFalse(d.scan_busy)

    def test_discovery_cache_update_non_snapshot_is_ignored(self) -> None:
        facade = BridgeAppFacade()
        facade.update_discovery_snapshot("not-a-snapshot")
        d = facade.get_discovery()
        self.assertEqual(d.updated_mono, 0.0)

    def test_set_discovery_busy(self) -> None:
        facade = BridgeAppFacade()
        facade._set_discovery_busy(True)
        self.assertTrue(facade.get_discovery().scan_busy)
        facade._set_discovery_busy(False)
        self.assertFalse(facade.get_discovery().scan_busy)

    def test_discovery_cache_thread_safe(self) -> None:
        facade = BridgeAppFacade()

        def reader() -> None:
            for _ in range(50):
                _ = facade.get_discovery()

        def writer() -> None:
            for _ in range(50):
                facade._set_discovery_busy(_ % 2 == 0)

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_request_unlock_ports_no_window(self) -> None:
        facade = BridgeAppFacade()
        result = facade.request_unlock_ports()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unavailable")

    def test_unlock_ports_no_com_port(self) -> None:
        app = QApplication.instance() or QApplication([])
        facade = BridgeAppFacade()
        win = MagicMock()
        win.com_cb.currentText.return_value = ""
        facade.attach_window(win)
        result = facade.request_unlock_ports()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "validation")

    def test_request_refresh_discovery_no_window(self) -> None:
        facade = BridgeAppFacade()
        result = facade.request_refresh_discovery()
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unavailable")

    def test_request_refresh_discovery_from_worker_thread(self) -> None:
        app = QApplication.instance() or QApplication([])
        facade = BridgeAppFacade()
        win = MagicMock()
        win._on_hub_refresh_discovery = MagicMock()
        facade.attach_window(win)
        result_box: dict[str, object] = {}

        def worker() -> None:
            result_box["result"] = facade.request_refresh_discovery()

        thread = threading.Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 5.0
        while thread.is_alive() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        thread.join(timeout=1.0)
        self.assertFalse(thread.is_alive())
        result = result_box.get("result")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.ok)
        win._on_hub_refresh_discovery.assert_called_once()

    def test_web_log_buffer_append_and_poll(self) -> None:
        facade = BridgeAppFacade()
        facade.append_log_lines(["NET→COM | gps=— | $GPGGA"])
        facade.append_log_lines(["[DROP n→s] queue full"])
        payload = facade.get_logs(after_seq=0, limit=50)
        self.assertEqual(len(payload.lines), 2)
        self.assertEqual(payload.lines[0].kind, "traffic")
        self.assertEqual(payload.lines[1].kind, "warn")
        tail = facade.get_logs(after_seq=payload.lines[0].seq, limit=50)
        self.assertEqual(len(tail.lines), 1)

    def test_classify_web_log_line(self) -> None:
        self.assertEqual(classify_web_log_line("NET→COM | x"), "traffic")
        self.assertEqual(classify_web_log_line("[PAUSE] resumed"), "event")
        self.assertEqual(classify_web_log_line("serial open fail"), "warn")


if __name__ == "__main__":
    unittest.main()
