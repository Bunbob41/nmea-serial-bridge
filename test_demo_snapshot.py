"""Product Demo snapshot capture/restore and persistence guards."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from PySide6 import QtWidgets

from ui.demo import _apply_desk
from ui.demo_gateway import DemoHostGateway
from ui.demo_snapshot import capture_operator_snapshot, restore_operator_snapshot


def _make_host() -> QtWidgets.QWidget:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    del app
    win = QtWidgets.QWidget()
    win.com_cb = QtWidgets.QComboBox()
    win.com_cb.addItems(["COM3", "COM7"])
    win.com_cb.setCurrentText("COM7")
    win.baud_edit = QtWidgets.QComboBox()
    win.baud_edit.setEditable(True)
    win.baud_edit.addItem("115200")
    win.baud_edit.setCurrentText("115200")
    win.chk_advanced_net = QtWidgets.QCheckBox()
    win.rb_udp_listen = QtWidgets.QRadioButton()
    win.rb_udp_remote = QtWidgets.QRadioButton()
    win.rb_tcp_server = QtWidgets.QRadioButton()
    win.rb_tcp_client = QtWidgets.QRadioButton()
    win.rb_udp_listen.setChecked(True)
    win.udp_host = QtWidgets.QLineEdit("0.0.0.0")
    win.udp_port = QtWidgets.QLineEdit("10110")
    win.remote_host = QtWidgets.QLineEdit("192.168.1.1")
    win.remote_port = QtWidgets.QLineEdit("10110")
    win.tcp_srv_host = QtWidgets.QLineEdit("0.0.0.0")
    win.tcp_srv_port = QtWidgets.QLineEdit("9000")
    win.tcp_cli_host = QtWidgets.QLineEdit("127.0.0.1")
    win.tcp_cli_port = QtWidgets.QLineEdit("9001")
    win.chk_udp_fanout = QtWidgets.QCheckBox()
    win.chk_udp_fanout.setChecked(True)
    win.chk_tcp_sink_enable = QtWidgets.QCheckBox()
    win.tcp_sink_port = QtWidgets.QLineEdit("10111")
    win.rb_nmea_passthrough = QtWidgets.QRadioButton()
    win.rb_nmea_strict = QtWidgets.QRadioButton()
    win.rb_nmea_raw = QtWidgets.QRadioButton()
    win.rb_nmea_passthrough.setChecked(True)
    win._nmea_type_checks = {}
    win._active_preset_name = "Desk test"
    win.bridge = None
    win._starting = False
    win._mode_toggle = lambda *_a: None
    win._log_ui = lambda _t: None
    win._nmea_mode_label = lambda: "passthrough"
    win._apply_preset_data = mock.Mock()
    win._apply_preset_nmea_mode = mock.Mock()
    win._set_active_preset = mock.Mock()
    win._update_field_connect_summary = mock.Mock()
    win._refresh_nmea_status_chip = mock.Mock()
    win.start_bridge = mock.Mock()
    win.stop_bridge = mock.Mock()
    return win


class TestDemoSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_capture_restore_roundtrip(self) -> None:
        host = _make_host()
        snap = capture_operator_snapshot(host)
        self.assertEqual(snap.com_port, "COM7")
        self.assertEqual(snap.baud, 115200)
        self.assertEqual(snap.network_mode, "udp_listen")
        self.assertEqual(snap.nmea_mode, "passthrough")
        self.assertEqual(snap.active_preset_name, "Desk test")
        self.assertFalse(snap.bridge_was_running)

        host.com_cb.setCurrentText("COM3")
        host.udp_port.setText("9999")
        host.rb_nmea_strict.setChecked(True)
        host.rb_nmea_passthrough.setChecked(False)
        host._nmea_mode_label = lambda: "strict"

        restore_operator_snapshot(host, snap)
        host._apply_preset_data.assert_called()
        call_data = host._apply_preset_data.call_args[0][0]
        self.assertEqual(call_data["com"], "COM7")
        self.assertEqual(call_data["udp_port"], 10110)
        host._set_active_preset.assert_called_with("Desk test")

    def test_demo_preserves_path_presets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path_presets.json"
            path.write_text(
                json.dumps(
                    {
                        "presets": {
                            "Desk test": {
                                "com": "COM7",
                                "baud": 115200,
                                "udp_host": "0.0.0.0",
                                "udp_port": 10110,
                            }
                        },
                        "preset_order": ["Desk test"],
                        "last_preset": "Desk test",
                    }
                ),
                encoding="utf-8",
            )
            before = path.read_text(encoding="utf-8")

            host = _make_host()
            host._apply_bench_preset = mock.Mock(side_effect=_apply_desk)
            host._apply_preset_by_name = mock.Mock()
            host._set_active_preset = mock.Mock()
            host._demo_session_active = False

            gateway = DemoHostGateway()
            with mock.patch("bench_config.USER_PRESETS_PATH", path):
                with mock.patch("bench_config.save_preset") as save_mock:
                    gateway.enter(host)
                    self.assertTrue(host._demo_session_active)
                    gateway.run_action(host, _apply_desk)
                    gateway.exit(host)
                    save_mock.assert_not_called()
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_restore_bridge_running_flag(self) -> None:
        host = _make_host()
        snap = capture_operator_snapshot(host)
        self.assertFalse(snap.bridge_was_running)

        host.bridge = object()
        restore_operator_snapshot(host, snap)
        host.stop_bridge.assert_not_called()

        host.bridge = None
        snap_running = replace(capture_operator_snapshot(host), bridge_was_running=True)
        restore_operator_snapshot(host, snap_running)
        host.start_bridge.assert_called()

        host.start_bridge.reset_mock()
        host.bridge = object()
        restore_operator_snapshot(
            host,
            snap,
            demo_started_bridge=True,
        )
        host.stop_bridge.assert_called()

    def test_gateway_tracks_demo_started_bridge(self) -> None:
        host = _make_host()

        def _start(h: QtWidgets.QWidget) -> None:
            h.bridge = object()
            h._starting = False

        def _stop() -> None:
            host.bridge = None

        host.stop_bridge = _stop

        gateway = DemoHostGateway()
        gateway.enter(host)
        gateway.run_action(host, _start)
        self.assertTrue(gateway.demo_started_bridge)
        gateway.exit(host)
        self.assertIsNone(host.bridge)


if __name__ == "__main__":
    unittest.main()
