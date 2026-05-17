"""Start validation rules for UDP listen vs Advanced network modes."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from ui.mixin import BridgeLogicMixin


class _ValidateHost(BridgeLogicMixin, object):
    """Minimal host object for _validate_before_start (no Qt widgets)."""

    def __init__(self) -> None:
        self._worker = None
        self._starting = False
        self.com_cb = MagicMock()
        self.com_cb.currentText.return_value = "COM7"
        self.baud_edit = MagicMock()
        self.baud_edit.text.return_value = "115200"
        self.chk_advanced_net = MagicMock()
        self._active_preset_name = "Desk test"
        self.rb_udp_remote = MagicMock()
        self.rb_udp_listen = MagicMock()
        self.rb_tcp_server = MagicMock()
        self.rb_tcp_client = MagicMock()
        self.udp_port = MagicMock()
        self.udp_port.text.return_value = "10110"
        self.remote_host = MagicMock()
        self.remote_host.text.return_value = ""
        self.remote_port = MagicMock()
        self.remote_port.text.return_value = "10110"
        self.tcp_srv_port = MagicMock()
        self.tcp_srv_port.text.return_value = "4001"
        self.tcp_cli_host = MagicMock()
        self.tcp_cli_host.text.return_value = "127.0.0.1"
        self.tcp_cli_port = MagicMock()
        self.tcp_cli_port.text.return_value = "4001"


class TestStartValidation(unittest.TestCase):
    def test_udp_listen_required_without_advanced(self) -> None:
        w = _ValidateHost()
        w.chk_advanced_net.isChecked.return_value = False
        w.rb_udp_listen.isChecked.return_value = False
        w.rb_tcp_server.isChecked.return_value = True
        err = w._validate_before_start()
        self.assertIsNotNone(err)
        self.assertIn("UDP listen", err or "")

    def test_advanced_tcp_server_allowed(self) -> None:
        w = _ValidateHost()
        w.chk_advanced_net.isChecked.return_value = True
        w.rb_udp_listen.isChecked.return_value = False
        w.rb_tcp_server.isChecked.return_value = True
        w.rb_udp_remote.isChecked.return_value = False
        w.rb_tcp_client.isChecked.return_value = False
        self.assertIsNone(w._validate_before_start())


if __name__ == "__main__":
    unittest.main()
