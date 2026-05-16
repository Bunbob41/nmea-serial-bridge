from pathlib import Path

body = Path("_mixin_body.txt").read_text(encoding="utf-8")
idx = body.find("\ndef main()")
if idx >= 0:
    body = body[:idx]

head = '''# ui/mixin.py — bridge start/stop, logging, validation (shared by all UIs)
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

import asyncio
import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from bench_config import load_bench_defaults, load_production_defaults
from bridge_core import (
    BridgeAsyncThread,
    NetMode,
    SerialNetBridge,
    SERIAL_OPEN_TIMEOUT_S,
    START_WATCHDOG_MS,
    UI_LOG_FLUSH_MS,
    UI_LOG_MAX_LINES_PER_FLUSH,
    UI_LOG_PENDING_MAX,
    _FileSurveyLog,
    _friendly_serial_error,
    _nmea_line_bytes,
    _open_serial_port_timed,
    _parse_port,
)
from nmea_codec import NmeaFilter, NmeaMode
from nmea_static_edh import EDH_ALT_M, EDH_LAT_DEG, EDH_LON_DEG, build_gga, build_rmc


class BridgeLogicMixin:
    """Shared bridge GUI logic; subclasses must create widgets before _finalize_ui()."""

    def _init_bridge_state(self) -> None:
        self.bridge: Optional[SerialNetBridge] = None
        self._worker: Optional[BridgeAsyncThread] = None
        self._file_log: Optional[_FileSurveyLog] = None
        self._stopping = False
        self._start_gen = 0
        self._active_path: Optional[str] = None
        self._starting = False
        self._stop_guard_timer = QtCore.QTimer(self)
        self._stop_guard_timer.setSingleShot(True)
        self._stop_guard_timer.timeout.connect(self._stop_timeout_guard)
        self._start_watchdog_timer = QtCore.QTimer(self)
        self._start_watchdog_timer.setSingleShot(True)
        self._start_watchdog_timer.timeout.connect(self._start_watchdog_fired)
        self._pending_ui: Deque[str] = deque()
        self._ui_drops = 0
        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)
        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)

    def _finalize_ui(self) -> None:
        from ui.controls import wire_connection_controls
        wire_connection_controls(self)
        self.refresh_ports()
        self._mode_toggle()
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)
        self._stats_timer.start(400)
        self._on_ui_ready()

    def _on_ui_ready(self) -> None:
        pass

'''

Path("ui/mixin.py").write_text(head + body, encoding="utf-8")
print("wrote ui/mixin.py", len((head + body).splitlines()), "lines")
