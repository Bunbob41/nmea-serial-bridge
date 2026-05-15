# bridge_gui.py — Network (UDP / TCP) ↔ COM bridge, Windows PySide6
# Python 3.10+  |  pip install -r requirements.txt
from __future__ import annotations

import asyncio
import errno
import logging
import sys
import threading
import time
from datetime import datetime, timezone
from collections import deque
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, List, Optional

import serial
import serial_asyncio
from serial_asyncio import connection_for_serial
import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from nmea_codec import (
    NMEA_SENTENCE_TYPES,
    NmeaFilter,
    NmeaLineAssembler,
    NmeaMode,
    feed_nmea_times_from_lines,
    parse_nmea_utc,
)
from bench_config import load_bench_defaults, load_production_defaults
from nmea_static_edh import EDH_ALT_M, EDH_LAT_DEG, EDH_LON_DEG, build_gga, build_rmc
from version import __version__

# --- Constants ---
NET_TO_SERIAL_QUEUE_MAX = 512
SERIAL_TO_NET_QUEUE_MAX = 512
UI_LOG_PENDING_MAX = 2000
UI_LOG_FLUSH_MS = 50
UI_LOG_MAX_LINES_PER_FLUSH = 96
UI_VIEW_MAX_BLOCK_COUNT = 4000

# Survey / marine palette — structured for path → serial → network → action
BRIDGE_STYLESHEET = """
QWidget#BridgeRoot {
    background-color: #1a2420;
    color: #e8f2ea;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QLabel#appTitle {
    font-size: 15pt;
    font-weight: 600;
    color: #e8f8eb;
}
QLabel#appSubtitle {
    color: #9bb8a4;
    font-size: 9pt;
}
QFrame#statusBanner {
    border-radius: 8px;
    padding: 10px 12px;
    border: 1px solid #4a6b52;
    background-color: #243328;
}
QFrame#statusBanner[state="running"] {
    background-color: #1e3d28;
    border-color: #6fcf97;
}
QFrame#statusBanner[state="starting"] {
    background-color: #3d3a22;
    border-color: #d4c06a;
}
QFrame#statusBanner[state="failed"] {
    background-color: #3d2424;
    border-color: #c97a7a;
}
QLabel#statusBannerText {
    font-size: 12pt;
    font-weight: 600;
}
QLabel#intentHint {
    color: #c8e6d0;
    padding: 6px 4px;
    line-height: 1.35;
}
QPushButton#pathBench, QPushButton#pathProduction {
    text-align: left;
    padding: 12px 14px;
    border-radius: 8px;
    border: 2px solid #4a6b52;
    background-color: #2a3830;
    font-weight: 600;
}
QPushButton#pathBench:hover, QPushButton#pathProduction:hover {
    border-color: #7ab88a;
    background-color: #324a38;
}
QPushButton#pathBench[active="true"], QPushButton#pathProduction[active="true"] {
    border-color: #8ee0a0;
    background-color: #2d4a36;
}
QPushButton#btnStart {
    background-color: #2d6a3e;
    border: 1px solid #6fcf97;
    border-radius: 8px;
    font-size: 11pt;
    font-weight: 600;
    min-height: 44px;
    padding: 8px 16px;
}
QPushButton#btnStart:hover { background-color: #36824b; }
QPushButton#btnStart:disabled { background-color: #2a352c; color: #666; border-color: #444; }
QPushButton#btnStop {
    background-color: #4a3234;
    border: 1px solid #a07070;
    border-radius: 8px;
    font-size: 11pt;
    font-weight: 600;
    min-height: 44px;
    padding: 8px 16px;
}
QPushButton#btnStop:hover { background-color: #5c3e40; }
QTabWidget::pane {
    border: 1px solid #3d5244;
    border-radius: 6px;
    background: #222e26;
    top: -1px;
}
QTabBar::tab {
    background: #2a3830;
    color: #b0c8b8;
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #324a38;
    color: #e8f8eb;
}
QPlainTextEdit {
    background-color: #141c18;
    color: #d8ebe0;
    border: 1px solid #3d5244;
    border-radius: 6px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 9pt;
}
QStatusBar {
    background: #1e2a22;
    color: #b8d0c0;
    border-top: 1px solid #3d5244;
}
QGroupBox {
    border: 1px solid #3d5244;
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    color: #dcefe0;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #9fd4a8;
}
QPushButton {
    background-color: #324a38;
    color: #f0faf1;
    border: 1px solid #5a7d62;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover { background-color: #3d5c44; }
QPushButton:disabled { background-color: #252e28; color: #666; }
QComboBox, QLineEdit, QSpinBox, QPlainTextEdit#sendEdit {
    background-color: #1a2420;
    color: #e8f2ea;
    border: 1px solid #4a6b52;
    border-radius: 4px;
    padding: 4px 6px;
    min-height: 1.4em;
}
QRadioButton { spacing: 8px; color: #d0e8d8; }
QCheckBox { color: #d0e8d8; }
"""

FILE_LOG_MAX_BYTES = 10 * 1024 * 1024
FILE_LOG_BACKUP_COUNT = 5
DEFAULT_TCP_RECONNECT_S = 1.0
TCP_RECONNECT_MIN_S = 0.5
TCP_RECONNECT_MAX_S = 60.0
STOP_TIMEOUT_S = 4.0
CLOSE_TIMEOUT_S = 1.5
SERIAL_OPEN_TIMEOUT_S = 5.0
SERIAL_WRITE_TIMEOUT_S = 2.0
START_WATCHDOG_MS = 15_000
START_ASYNC_TIMEOUT_S = 10.0


def configure_windows_event_loop_policy() -> None:
    """Selector policy is deprecated on Python 3.14+; qasync QEventLoop does not need it."""
    if sys.platform != "win32":
        return
    if sys.version_info >= (3, 14):
        return
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _open_serial_port_timed(port: str, baud: int, timeout_s: float) -> serial.Serial:
    """Open COM in a daemon thread so a stuck driver cannot freeze the Qt loop forever."""
    result: list[serial.Serial] = []
    err: list[BaseException] = []

    def _work() -> None:
        try:
            result.append(
                serial.Serial(port=port, baudrate=baud, timeout=0, write_timeout=0)
            )
        except BaseException as exc:
            err.append(exc)

    t = threading.Thread(target=_work, name=f"open-{port}", daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        raise asyncio.TimeoutError(f"opening {port} timed out after {timeout_s:.0f}s")
    if err:
        raise err[0]
    if not result:
        raise RuntimeError(f"opening {port} failed with no error")
    return result[0]


def _friendly_serial_error(exc: BaseException, port: str) -> str:
    msg = str(exc).strip()
    if isinstance(exc, asyncio.TimeoutError):
        return f"Serial {port}: timed out (open/write)."
    if isinstance(exc, PermissionError) or (
        isinstance(exc, OSError) and getattr(exc, "winerror", None) in (5, 13)
    ):
        return (
            f"Cannot open {port}: access denied or port in use. "
            "Close Mission Planner, PuTTY, another bridge, or the device manager test dialog, then try again."
        )
    if isinstance(exc, FileNotFoundError) or (
        isinstance(exc, OSError) and getattr(exc, "winerror", None) == 2
    ):
        return f"Cannot open {port}: port not found. Refresh the port list and check USB/cable."
    if isinstance(exc, serial.SerialException):
        low = msg.lower()
        if "access is denied" in low or "permission" in low:
            return (
                f"Cannot open {port}: access denied or port in use. "
                "Close any other app using this COM port, then try again."
            )
        if "could not open port" in low and "no such file" in low:
            return f"Cannot open {port}: port not found. Refresh ports and reconnect the device."
        if "being used" in low or "in use" in low:
            return f"Cannot open {port}: port is already in use by another program."
    return f"Cannot open {port}: {msg or type(exc).__name__}"


def _friendly_network_error(exc: BaseException, context: str) -> str:
    msg = str(exc).strip()
    if isinstance(exc, OSError):
        if exc.errno in (errno.EADDRINUSE, 10048):  # WSAEADDRINUSE on Windows
            return f"{context}: address or port already in use. Pick another port or stop the other program."
        if exc.errno in (errno.EADDRNOTAVAIL, 10049):
            return f"{context}: cannot bind to that address on this PC."
        if exc.errno in (errno.EACCES, 10013):
            return f"{context}: permission denied (firewall or privileged port?)."
    if isinstance(exc, ConnectionRefusedError):
        return f"{context}: connection refused — nothing listening on that host/port."
    if isinstance(exc, asyncio.TimeoutError):
        return f"{context}: timed out."
    if isinstance(exc, ConnectionResetError):
        return f"{context}: connection reset by peer."
    return f"{context}: {msg or type(exc).__name__}"


def _parse_port(text: str, label: str) -> int:
    p = int(text.strip())
    if not 1 <= p <= 65535:
        raise ValueError(f"{label} must be between 1 and 65535")
    return p


class NetMode(str, Enum):
    UDP_LISTEN = "udp_listen"
    UDP_REMOTE = "udp_remote"
    TCP_SERVER = "tcp_server"
    TCP_CLIENT = "tcp_client"


def _nmea_line_bytes(text: str) -> bytes:
    line = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not line:
        return b""
    return (line + "\r\n").encode("utf-8", errors="replace")


class _SurveyFileFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = time.localtime(record.created)
        t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
        return f"{t}.{int(record.msecs):03d}"


class _FileSurveyLog:
    """Rotating file: PC time | last GPS UTC | direction | payload."""

    def __init__(self, path: Path):
        self.path = path
        self._logger = logging.getLogger(f"survey_bridge.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            path, maxBytes=FILE_LOG_MAX_BYTES, backupCount=FILE_LOG_BACKUP_COUNT, encoding="utf-8"
        )
        fmt = _SurveyFileFormatter("%(asctime)s | %(gps)s | %(direction)s | %(message)s")
        fh.setFormatter(fmt)
        self._logger.addHandler(fh)
        self._logger.propagate = False

    def close(self) -> None:
        for h in list(self._logger.handlers):
            h.close()
            self._logger.removeHandler(h)

    def write(self, direction: str, preview: str, gps_utc: str) -> None:
        self._logger.info(
            "%s",
            preview,
            extra={"gps": gps_utc or "—", "direction": direction},
        )


class UDPRecvProtocol(asyncio.DatagramProtocol):
    def __init__(self, bridge: "SerialNetBridge"):
        self.bridge = bridge

    def datagram_received(self, data: bytes, addr) -> None:
        self.bridge.on_udp_datagram(data, addr)


class SerialNetBridge:
    """Bidirectional serial ↔ network with bounded queues and drop counters."""

    def __init__(
        self,
        com: str,
        baud: int,
        mode: NetMode,
        udp_listen: Optional[tuple[str, int]] = None,
        udp_remote: Optional[tuple[str, int]] = None,
        tcp_bind_host: str = "0.0.0.0",
        tcp_bind_port: int = 4001,
        tcp_client_host: str = "127.0.0.1",
        tcp_client_port: int = 4001,
        tcp_reconnect_delay: float = DEFAULT_TCP_RECONNECT_S,
        nmea_mode: NmeaMode = NmeaMode.PASSTHROUGH,
        nmea_filter: Optional[NmeaFilter] = None,
        ui_log_verbose: Optional[Callable[[], bool]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        ui_log: Optional[Callable[[str], None]] = None,
        status_cb: Optional[Callable[[str, str], None]] = None,
        stats_cb: Optional[Callable[[dict], None]] = None,
        file_log: Optional[_FileSurveyLog] = None,
    ):
        self.com = com
        self.baud = baud
        self.mode = mode
        self.udp_listen = udp_listen
        self.udp_remote = udp_remote
        self.tcp_bind_host = tcp_bind_host
        self.tcp_bind_port = tcp_bind_port
        self.tcp_client_host = tcp_client_host
        self.tcp_client_port = tcp_client_port
        self.tcp_reconnect_delay = max(TCP_RECONNECT_MIN_S, min(TCP_RECONNECT_MAX_S, tcp_reconnect_delay))
        self.nmea_mode = nmea_mode
        self.nmea_filter = nmea_filter or NmeaFilter()
        self._ui_log_verbose = ui_log_verbose or (lambda: False)

        self.loop = loop or asyncio.get_event_loop()
        self._ui_log = ui_log or (lambda *_a, **_k: None)
        self._status_cb = status_cb or (lambda *_a, **_k: None)
        self._stats_cb = stats_cb or (lambda *_a, **_k: None)
        self._file_log = file_log

        self.serial_reader: Optional[asyncio.StreamReader] = None
        self.serial_writer: Optional[asyncio.StreamWriter] = None
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self._tcp_server: Optional[asyncio.Server] = None
        self.tcp_reader: Optional[asyncio.StreamReader] = None
        self.tcp_writer: Optional[asyncio.StreamWriter] = None
        self._tcp_client_task: Optional[asyncio.Task] = None
        self._tcp_reader_task: Optional[asyncio.Task] = None

        self.last_udp_addr = None
        self._gps_state: list[Optional[str]] = [None]

        self.net_to_serial: asyncio.Queue[bytes] = asyncio.Queue(maxsize=NET_TO_SERIAL_QUEUE_MAX)
        self.serial_to_net: asyncio.Queue[bytes] = asyncio.Queue(maxsize=SERIAL_TO_NET_QUEUE_MAX)

        self.drops_net_to_serial = 0
        self.drops_serial_to_net = 0
        self.rejected_net_to_serial = 0
        self.rejected_serial_to_net = 0

        self._asm_n2s = NmeaLineAssembler()
        self._asm_s2n = NmeaLineAssembler()

        self.running = False
        self._teardown = False
        self._tasks: list[asyncio.Task] = []
        self._serial_open = False
        self._network_ready = False

    def _set_status(self, serial_line: str, network_line: str) -> None:
        self._status_cb(serial_line, network_line)

    def _gps_utc(self) -> str:
        return self._gps_state[0] or ""


    def _underlying_serial(self) -> Optional[serial.Serial]:
        writer = self.serial_writer
        if not writer:
            return None
        ser = getattr(writer.transport, "serial", None)
        return ser if isinstance(ser, serial.Serial) else None

    async def _write_serial_bytes(self, chunk: bytes) -> None:
        """Write to COM. On Windows, bypass pyserial-asyncio poll writer (can stall under qasync)."""
        if not self.running or not chunk or not self.serial_writer:
            return
        if sys.platform == "win32":
            ser = self._underlying_serial()
            if ser is not None:

                def _blocking_write() -> None:
                    ser.write(chunk)
                    ser.flush()

                await asyncio.wait_for(
                    asyncio.to_thread(_blocking_write), timeout=SERIAL_WRITE_TIMEOUT_S
                )
                return
        self.serial_writer.write(chunk)
        await asyncio.wait_for(self.serial_writer.drain(), timeout=SERIAL_WRITE_TIMEOUT_S)

    def _emit_stats(self) -> None:
        self._stats_cb(
            {
                "drops_n2s": self.drops_net_to_serial,
                "drops_s2n": self.drops_serial_to_net,
                "rej_n2s": self.rejected_net_to_serial,
                "rej_s2n": self.rejected_serial_to_net,
                "n2s_q": self.net_to_serial.qsize(),
                "s2n_q": self.serial_to_net.qsize(),
            }
        )

    def _log(self, direction: str, data: bytes, *, to_ui: bool = True, always: bool = False) -> None:
        preview = data.decode(errors="replace").rstrip().replace("\r", "\\r")
        gps = self._gps_utc()
        if self._file_log:
            try:
                self._file_log.write(direction, preview, gps)
            except Exception:
                pass
        if to_ui and (always or self._ui_log_verbose()):
            self._ui_log(f"{direction} | gps={gps or '—'} | {preview}")

    def _enqueue_net_to_serial(self, data: bytes, direction: str) -> None:
        try:
            self.net_to_serial.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_net_to_serial += 1
            self._emit_stats()
            self._log(f"{direction} [DROP n→s]", data, to_ui=True, always=True)
        else:
            self._log(direction, data)

    def _enqueue_serial_to_net(self, data: bytes, direction: str) -> None:
        try:
            self.serial_to_net.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_serial_to_net += 1
            self._emit_stats()
            self._log(f"{direction} [DROP s→n]", data, to_ui=True, always=True)
        else:
            self._log(direction, data)

    def _ingest_net(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_n2s.feed(data, self.nmea_mode, filt)
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        for reason in result.rejected:
            self.rejected_net_to_serial += 1
            self._emit_stats()
            self._log_text(f"{direction} [REJECT] {reason}")
        for line in result.forward:
            self._enqueue_net_to_serial(line, direction)

    def _ingest_serial(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_s2n.feed(data, self.nmea_mode, filt)
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        for reason in result.rejected:
            self.rejected_serial_to_net += 1
            self._emit_stats()
            self._log_text(f"{direction} [REJECT] {reason}")
        for line in result.forward:
            self._enqueue_serial_to_net(line, direction)

    def _log_text(self, msg: str) -> None:
        gps = self._gps_utc()
        if self._file_log:
            try:
                self._file_log.write(msg, msg, gps)
            except Exception:
                pass
        self._ui_log(f"{msg} | gps={gps or '—'}")

    def on_udp_datagram(self, data: bytes, addr) -> None:
        if not self.running:
            return
        if self.last_udp_addr != addr and self.mode == NetMode.UDP_LISTEN and self.udp_listen:
            host, port = self.udp_listen
            self._set_status(
                f"Serial: {self.com} @ {self.baud} — open",
                f"Network: UDP listen {host}:{port} — peer {addr}",
            )
        self.last_udp_addr = addr
        self._ingest_net(data, f"UDP←{addr}")

    def schedule_net_to_serial(self, data: bytes, tag: str = "INJECT→SER") -> None:
        if not self.running or not data:
            return

        def _go() -> None:
            self._ingest_net(data, tag)

        self.loop.call_soon(_go)

    def schedule_serial_to_net(self, data: bytes, tag: str = "INJECT→NET") -> None:
        if not self.running or not data:
            return

        def _go() -> None:
            self._ingest_serial(data, tag)

        self.loop.call_soon(_go)


    async def _open_serial_stream(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open COM without hanging the Qt loop (thread join timeout, not wait_for on a stuck thread)."""
        loop = self.loop
        ser = await asyncio.to_thread(
            _open_serial_port_timed, self.com, self.baud, SERIAL_OPEN_TIMEOUT_S
        )
        reader = asyncio.StreamReader(loop=loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
        transport, _ = await asyncio.wait_for(
            connection_for_serial(loop, lambda: protocol, ser),
            timeout=SERIAL_OPEN_TIMEOUT_S,
        )
        writer = asyncio.StreamWriter(transport, protocol, reader, loop)
        return reader, writer

    async def start(self) -> bool:
        self._set_status(f"Serial: opening {self.com} @ {self.baud}…", "Network: starting…")
        self._ui_log(f"Opening serial {self.com} @ {self.baud}")
        try:
            self.serial_reader, self.serial_writer = await self._open_serial_stream()
        except asyncio.TimeoutError:
            err = (
                f"Timed out opening {self.com} after {SERIAL_OPEN_TIMEOUT_S:.0f}s. "
                "Close Tera Term, NMEA Simulator, or PuTTY on that COM port, then try again."
            )
            self._ui_log(err)
            self._set_status(f"Serial: timeout — {self.com}", "Network: not started")
            return False
        except Exception as e:
            err = _friendly_serial_error(e, self.com)
            self._ui_log(err)
            self._set_status(f"Serial: error — {self.com}", "Network: not started")
            return False

        self._serial_open = True
        self.running = True
        self._set_status(f"Serial: {self.com} @ {self.baud} — open", "Network: opening…")

        self._tasks.append(asyncio.create_task(self._pump_net_to_serial(), name="pump_n2s"))
        self._tasks.append(asyncio.create_task(self._pump_serial_to_net_queue(), name="pump_s2n_out"))
        self._tasks.append(asyncio.create_task(self._serial_read_loop(), name="serial_read"))

        try:
            if self.mode == NetMode.UDP_LISTEN and self.udp_listen:
                self.udp_transport, _ = await asyncio.wait_for(
                    self.loop.create_datagram_endpoint(
                        lambda: UDPRecvProtocol(self), local_addr=self.udp_listen
                    ),
                    timeout=SERIAL_OPEN_TIMEOUT_S,
                )
                host, port = self.udp_listen
                self._network_ready = True
                self._ui_log(f"UDP listen on {self.udp_listen}")
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: UDP listen {host}:{port} — waiting for peer",
                )
            elif self.mode == NetMode.UDP_REMOTE and self.udp_remote:
                self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                    lambda: UDPRecvProtocol(self), remote_addr=self.udp_remote
                )
                host, port = self.udp_remote
                self._network_ready = True
                self._ui_log(f"UDP remote peer {self.udp_remote}")
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: UDP → {host}:{port}",
                )
            elif self.mode == NetMode.TCP_SERVER:
                self._tcp_server = await asyncio.start_server(
                    self._on_tcp_client, host=self.tcp_bind_host, port=self.tcp_bind_port
                )
                self._tasks.append(asyncio.create_task(self._serve_tcp_forever(), name="tcp_serve"))
                self._network_ready = True
                self._ui_log(f"TCP server listening {self.tcp_bind_host}:{self.tcp_bind_port}")
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP server {self.tcp_bind_host}:{self.tcp_bind_port} — waiting for client",
                )
            elif self.mode == NetMode.TCP_CLIENT:
                self._tcp_client_task = asyncio.create_task(self._tcp_client_runner(), name="tcp_client")
                self._tasks.append(self._tcp_client_task)
                self._ui_log(f"TCP client → {self.tcp_client_host}:{self.tcp_client_port}")
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP client connecting to {self.tcp_client_host}:{self.tcp_client_port}…",
                )
        except Exception as e:
            ctx = {
                NetMode.UDP_LISTEN: "UDP listen",
                NetMode.UDP_REMOTE: "UDP remote",
                NetMode.TCP_SERVER: "TCP server",
                NetMode.TCP_CLIENT: "TCP client",
            }.get(self.mode, "Network")
            err = _friendly_network_error(e, ctx)
            self._ui_log(err)
            if self.mode == NetMode.UDP_LISTEN and self.udp_listen:
                host, port = self.udp_listen
                self._ui_log(
                    f"Hint: only the bridge may LISTEN on UDP :{port}. "
                    f"Other apps must SEND to 127.0.0.1:{port} (or unicast to this PC), not bind the same port."
                )
            await self.stop()
            return False

        return True

    async def _serve_tcp_forever(self) -> None:
        assert self._tcp_server is not None
        async with self._tcp_server:
            await self._tcp_server.serve_forever()

    async def _on_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info("peername")
        self._ui_log(f"TCP client connected {addr}")
        self._set_status(
            f"Serial: {self.com} @ {self.baud} — open",
            f"Network: TCP client connected from {addr}",
        )
        if self._tcp_reader_task and not self._tcp_reader_task.done():
            self._tcp_reader_task.cancel()
        if self.tcp_writer:
            try:
                self.tcp_writer.close()
                await self.tcp_writer.wait_closed()
            except Exception:
                pass
        self.tcp_reader = reader
        self.tcp_writer = writer
        self._tcp_reader_task = asyncio.create_task(self._tcp_read_loop(addr), name="tcp_read")

    async def _tcp_read_loop(self, addr) -> None:
        assert self.tcp_reader is not None
        try:
            while self.running:
                data = await self.tcp_reader.read(4096)
                if not data:
                    break
                self._ingest_net(data, f"TCP←{addr}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._ui_log(_friendly_network_error(e, "TCP read"))
        finally:
            self._ui_log(f"TCP peer disconnected {addr}")
            if self.running and self.mode == NetMode.TCP_SERVER:
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP server {self.tcp_bind_host}:{self.tcp_bind_port} — waiting for client",
                )
            if self.tcp_writer:
                try:
                    self.tcp_writer.close()
                    await self.tcp_writer.wait_closed()
                except Exception:
                    pass
            self.tcp_reader = None
            self.tcp_writer = None

    async def _tcp_client_runner(self) -> None:
        while self.running:
            try:
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP connecting to {self.tcp_client_host}:{self.tcp_client_port}…",
                )
                self.tcp_reader, self.tcp_writer = await asyncio.open_connection(
                    self.tcp_client_host, self.tcp_client_port
                )
                addr = (self.tcp_client_host, self.tcp_client_port)
                self._network_ready = True
                self._ui_log(f"TCP connected to {addr}")
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP connected to {addr}",
                )
                await self._tcp_read_loop(addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._ui_log(_friendly_network_error(e, "TCP client"))
            finally:
                self.tcp_reader = None
                self.tcp_writer = None
            if self.running:
                delay = self.tcp_reconnect_delay
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: TCP reconnecting in {delay:.1f}s…",
                )
                await asyncio.sleep(delay)

    async def _serial_read_loop(self) -> None:
        assert self.serial_reader is not None
        try:
            while self.running:
                try:
                    data = await asyncio.wait_for(self.serial_reader.read(4096), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._ui_log(_friendly_serial_error(e, self.com))
                    break
                if not data:
                    continue
                self._ingest_serial(data, "SER→NET")
        except asyncio.CancelledError:
            pass

    async def _pump_net_to_serial(self) -> None:
        try:
            while self.running:
                try:
                    chunk = await asyncio.wait_for(self.net_to_serial.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                try:
                    await self._write_serial_bytes(chunk)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self.running and not self._teardown:
                        self._ui_log(_friendly_serial_error(e, self.com))
        except asyncio.CancelledError:
            pass

    async def _pump_serial_to_net_queue(self) -> None:
        try:
            while self.running:
                try:
                    chunk = await asyncio.wait_for(self.serial_to_net.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                try:
                    await self._send_net(chunk)
                except asyncio.CancelledError:
                    break
        except asyncio.CancelledError:
            pass

    async def _send_net(self, data: bytes) -> None:
        if self.mode in (NetMode.UDP_LISTEN, NetMode.UDP_REMOTE) and self.udp_transport:
            if self.mode == NetMode.UDP_LISTEN and self.last_udp_addr:
                self.udp_transport.sendto(data, self.last_udp_addr)
            else:
                try:
                    self.udp_transport.sendto(data)
                except Exception as e:
                    self._ui_log(_friendly_network_error(e, "UDP send"))
        elif self.mode in (NetMode.TCP_SERVER, NetMode.TCP_CLIENT) and self.tcp_writer:
            try:
                self.tcp_writer.write(data)
                await self.tcp_writer.drain()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._ui_log(_friendly_network_error(e, "TCP send"))

    def abort_now(self) -> None:
        """Synchronous teardown — must not block the Qt thread (no wait_closed on serial)."""
        self._teardown = True
        self.running = False

        while not self.net_to_serial.empty():
            try:
                self.net_to_serial.get_nowait()
            except asyncio.QueueEmpty:
                break
        while not self.serial_to_net.empty():
            try:
                self.serial_to_net.get_nowait()
            except asyncio.QueueEmpty:
                break

        for t in list(self._tasks):
            try:
                t.cancel()
            except Exception:
                pass
        self._tasks.clear()

        if self._tcp_reader_task and not self._tcp_reader_task.done():
            try:
                self._tcp_reader_task.cancel()
            except Exception:
                pass
        self._tcp_reader_task = None

        if self._tcp_client_task and not self._tcp_client_task.done():
            try:
                self._tcp_client_task.cancel()
            except Exception:
                pass
        self._tcp_client_task = None

        if self.udp_transport:
            try:
                self.udp_transport.close()
            except Exception:
                pass
            self.udp_transport = None

        if self._tcp_server:
            try:
                self._tcp_server.close()
            except Exception:
                pass
            self._tcp_server = None

        for w in (self.tcp_writer, self.serial_writer):
            if w is not None:
                try:
                    w.close()
                except Exception:
                    pass
        ser = self._underlying_serial()
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
        self.tcp_reader = None
        self.tcp_writer = None
        self.serial_reader = None
        self.serial_writer = None

        self._serial_open = False
        self._network_ready = False
        self._asm_n2s.reset()
        self._asm_s2n.reset()
        self._teardown = False

    async def _await_closed(self, writer: Optional[asyncio.StreamWriter], label: str) -> None:
        if not writer:
            return
        try:
            writer.close()
            if sys.platform == "win32" and label == "Serial":
                return
            await asyncio.wait_for(writer.wait_closed(), timeout=CLOSE_TIMEOUT_S)
        except asyncio.TimeoutError:
            self._ui_log(f"{label}: close timed out (port may be held by another program)")
        except Exception:
            pass

    async def _cancel_tasks(self, tasks: list[asyncio.Task]) -> None:
        pending = [t for t in tasks if t and not t.done()]
        for t in pending:
            t.cancel()
        if pending:
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=CLOSE_TIMEOUT_S)
            except asyncio.TimeoutError:
                self._ui_log("Background tasks did not exit cleanly (timed out)")

    async def _stop_inner(self) -> None:
        if not self.running and not self.udp_transport and not self.serial_writer:
            return
        self.running = False
        if self.udp_transport:
            try:
                self.udp_transport.close()
            except Exception:
                pass
            self.udp_transport = None

        if self._tcp_server:
            self._tcp_server.close()
            try:
                await asyncio.wait_for(self._tcp_server.wait_closed(), timeout=CLOSE_TIMEOUT_S)
            except Exception:
                pass
            self._tcp_server = None

        await self._await_closed(self.tcp_writer, "TCP")
        self.tcp_reader = None
        self.tcp_writer = None

        to_cancel: list[asyncio.Task] = list(self._tasks)
        if self._tcp_reader_task and not self._tcp_reader_task.done():
            to_cancel.append(self._tcp_reader_task)
        if self._tcp_client_task and not self._tcp_client_task.done():
            to_cancel.append(self._tcp_client_task)
        await self._cancel_tasks(to_cancel)
        self._tasks.clear()
        self._tcp_reader_task = None
        self._tcp_client_task = None

        writer = self.serial_writer
        self.serial_writer = None
        self.serial_reader = None
        await self._await_closed(writer, "Serial")

        self._serial_open = False
        self._network_ready = False
        self._asm_n2s.reset()
        self._asm_s2n.reset()

        self._set_status("Serial: closed", "Network: stopped")
        self._ui_log("Bridge stopped")

    async def stop(self) -> None:
        try:
            await asyncio.wait_for(self._stop_inner(), timeout=STOP_TIMEOUT_S)
        except asyncio.TimeoutError:
            self._ui_log("Stop timed out — forcing port release.")
            self.abort_now()


BridgeBuildFn = Callable[[asyncio.AbstractEventLoop], SerialNetBridge]


class BridgeAsyncThread(QtCore.QThread):
    """Run SerialNetBridge on a plain asyncio loop (same as bridge_headless — avoids qasync timer bugs)."""

    log_msg = QtCore.Signal(str)
    status_msg = QtCore.Signal(str, str)
    stats_msg = QtCore.Signal(dict)
    start_done = QtCore.Signal(bool)

    def __init__(self, build: BridgeBuildFn) -> None:
        super().__init__()
        self._build = build
        self.bridge: Optional[SerialNetBridge] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self) -> None:
        configure_windows_event_loop_policy()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            self.bridge = self._build(loop)
            ok = loop.run_until_complete(
                asyncio.wait_for(self.bridge.start(), timeout=START_ASYNC_TIMEOUT_S)
            )
            self.start_done.emit(ok)
            if ok:
                loop.run_forever()
        except Exception as exc:
            self.log_msg.emit(f"Bridge thread: {exc!r}")
            self.start_done.emit(False)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
            self._loop = None

    def request_stop(self) -> None:
        loop = self._loop
        bridge = self.bridge
        if not loop or not bridge:
            return

        def _stop() -> None:
            try:
                bridge.abort_now()
            except Exception:
                pass
            loop.stop()

        loop.call_soon_threadsafe(_stop)

    def call_on_loop(self, fn: Callable[[], None]) -> None:
        loop = self._loop
        if loop:
            loop.call_soon_threadsafe(fn)


class BridgeWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BridgeRoot")
        self.setStyleSheet(BRIDGE_STYLESHEET)
        self.setWindowTitle(f"Network ↔ COM Bridge v{__version__}")
        self.resize(980, 560)

        self.bridge: Optional[SerialNetBridge] = None
        self._worker: Optional[BridgeAsyncThread] = None
        self._file_log: Optional[_FileSurveyLog] = None
        self._stopping = False
        self._start_gen = 0
        self._pending_start_gen = 0
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

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(UI_VIEW_MAX_BLOCK_COUNT)
        self.log_view.setPlaceholderText("Live log: bridge status and traffic appear here while running.")

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_settings_tab(), "Connect")
        tabs.addTab(self._build_nmea_tab(), "NMEA")
        tabs.addTab(self._build_send_tab(), "Send")
        tabs.addTab(self._build_log_tab(), "Diagnostics")

        log_panel = QtWidgets.QWidget()
        log_lay = QtWidgets.QVBoxLayout(log_panel)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_hdr = QtWidgets.QHBoxLayout()
        self.chk_show_log = QtWidgets.QCheckBox("Show live log")
        self.chk_verbose_log = QtWidgets.QCheckBox("Show every sentence (verbose)")
        self.chk_verbose_log.setToolTip(
            "When off, only bridge status, errors, drops, and rejects appear. "
            "Turn on to see each NMEA line as it moves."
        )
        self.chk_show_log.setChecked(True)
        self.chk_verbose_log.setChecked(True)
        self.btn_clear_log = QtWidgets.QPushButton("Clear log")
        log_hdr.addWidget(self.chk_show_log)
        log_hdr.addWidget(self.chk_verbose_log)
        log_hdr.addStretch(1)
        log_hdr.addWidget(self.btn_clear_log)
        log_lay.addLayout(log_hdr)
        log_lay.addWidget(self.log_view, 1)
        self.chk_show_log.toggled.connect(self._toggle_log_panel)
        self.btn_clear_log.clicked.connect(self.log_view.clear)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.addWidget(tabs)
        self._splitter.addWidget(log_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([580, 400])
        log_panel.setVisible(True)

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.lbl_stats = QtWidgets.QLabel("Drops 0/0 | Reject 0/0")
        self.statusBar.addWidget(self.status_serial, 2)
        self.statusBar.addWidget(self.status_network, 2)
        self.statusBar.addPermanentWidget(self.lbl_stats)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 4)
        outer.addWidget(self._splitter)
        outer.addWidget(self.statusBar)

        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)

        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)

        self.refresh_ports()
        self._mode_toggle()
        QtCore.QTimer.singleShot(0, self._start_ui_timers)

    def _start_ui_timers(self) -> None:
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)
        self._stats_timer.start(400)

    def _preflight_com(self, com: str, baud: int) -> Optional[str]:
        """Quick COM probe on GUI thread before async start."""
        try:
            ser = _open_serial_port_timed(com, baud, SERIAL_OPEN_TIMEOUT_S)
            ser.close()
            return None
        except Exception as exc:
            return _friendly_serial_error(exc, com)

    def _toggle_log_panel(self, visible: bool) -> None:
        self._splitter.widget(1).setVisible(visible)
        if visible:
            self._splitter.setSizes([520, 360])
        else:
            self._splitter.setSizes([900, 0])

    def _polish_widget(self, w: QtWidgets.QWidget) -> None:
        style = w.style()
        style.unpolish(w)
        style.polish(w)

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_banner.setProperty("state", state)
        self._polish_widget(self.status_banner)
        text = title if not detail else f"{title}\n{detail}"
        self.status_banner_text.setText(text)

    def _set_active_path(self, path: Optional[str]) -> None:
        self._active_path = path
        self.btn_bench_preset.setProperty("active", path == "bench")
        self.btn_production_preset.setProperty("active", path == "production")
        self._polish_widget(self.btn_bench_preset)
        self._polish_widget(self.btn_production_preset)
        self._refresh_intent_hint()

    def _refresh_intent_hint(self) -> None:
        if self.rb_udp_remote.isChecked():
            self.intent_hint.setText(
                "⚠ Wrong mode: UDP remote is for talking to a fixed peer. "
                "For INS/simulator tests use Desk or Boat path (UDP listen)."
            )
            return
        if not self.rb_udp_listen.isChecked() and self.chk_advanced_net.isChecked():
            self.intent_hint.setText(
                "TCP mode selected — only use if your device speaks TCP, not UDP NMEA."
            )
            return
        if self._active_path == "bench":
            com = self.com_cb.currentText() or "COM?"
            self.intent_hint.setText(
                f"Desk test: bridge owns {com}. Send UDP to 127.0.0.1:{self.udp_port.text()}. "
                f"Watch the paired com0com port (e.g. COM12), not {com}. "
                f"Do not open Tera Term on {com}."
            )
        elif self._active_path == "production":
            d = load_production_defaults()
            self.intent_hint.setText(
                f"Boat: INS sends UDP to {d.get('pc_ip', 'PC IP')}:{self.udp_port.text()} → "
                f"{self.com_cb.currentText() or 'COM?'}. "
                "Close Mission Planner on that COM while bridging."
            )
        else:
            self.intent_hint.setText(
                "Choose Desk test or Boat / INS above, then Start. "
                "The bridge listens on UDP; your device must send NMEA to this PC."
            )

    def _validate_before_start(self) -> Optional[str]:
        if self._worker and self._worker.isRunning():
            return "Bridge is still stopping. Wait a moment, then try again."
        if self._starting:
            return "Start already in progress."
        if not self.com_cb.currentText().strip():
            return "Select a COM port (Refresh ports if the list is empty)."
        if self._active_path is None:
            return "Choose Desk test or Boat / INS first — this sets the correct UDP mode."
        if self.rb_udp_remote.isChecked():
            return (
                "UDP remote is wrong for INS/bench. Click Desk test or Boat / INS, "
                "or enable Advanced and select UDP listen."
            )
        if not self.rb_udp_listen.isChecked():
            return "For standard NMEA UDP, select UDP listen (use Desk/Boat path or Advanced)."
        try:
            baud = int(self.baud_edit.text())
            if baud <= 0:
                raise ValueError
        except ValueError:
            return "Enter a valid baud rate (e.g. 115200)."
        try:
            _parse_port(self.udp_port.text(), "UDP port")
        except ValueError as e:
            return str(e)
        return None

    def _apply_com_preset(self, com: str, baud: int, udp_host: str, udp_port: int) -> None:
        idx = self.com_cb.findText(com)
        if idx >= 0:
            self.com_cb.setCurrentIndex(idx)
        else:
            self.com_cb.addItem(com)
            self.com_cb.setCurrentText(com)
        self.baud_edit.setText(str(baud))
        self.rb_udp_listen.setChecked(True)
        self.udp_host.setText(udp_host)
        self.udp_port.setText(str(udp_port))
        self.rb_nmea_passthrough.setChecked(True)
        self.chk_show_log.setChecked(True)
        self._toggle_log_panel(True)
        self.chk_verbose_log.setChecked(True)
        self._mode_toggle()
        self._refresh_intent_hint()

    def _apply_bench_preset(self) -> None:
        """Bench: UDP listen -> COM from bench_defaults.json (com0com / localhost)."""
        d = load_bench_defaults()
        com = str(d["com"])
        baud = int(d["baud"])
        udp_host = str(d["udp_host"])
        udp_port = int(d["udp_port"])
        self._apply_com_preset(com, baud, udp_host, udp_port)
        self._set_active_path("bench")
        self._log_ui(
            f"Bench preset: {com} + UDP LISTEN {udp_host}:{udp_port}. "
            f"Test with 127.0.0.1:{udp_port} (python nmea_static_edh.py). "
            f"Watch paired COM (e.g. COM12), not {com}."
        )

    def _apply_production_preset(self) -> None:
        """Boat: INS UDP -> bridge -> physical COM -> Cube (edit production in bench_defaults.json)."""
        d = load_production_defaults()
        com = str(d["com"])
        baud = int(d["baud"])
        udp_host = str(d["udp_host"])
        udp_port = int(d["udp_port"])
        pc_ip = str(d.get("pc_ip", "192.168.1.10"))
        ins_ip = str(d.get("ins_ip", ""))
        mask = str(d.get("subnet_mask", "255.255.255.0"))
        notes = str(d.get("notes", "")).strip()
        self._apply_com_preset(com, baud, udp_host, udp_port)
        self._set_active_path("production")
        lines = [
            f"Production preset: {com} @ {baud}, UDP LISTEN {udp_host}:{udp_port}.",
            f"Survey PC Ethernet: {pc_ip} / {mask} (static recommended).",
            f"Configure INS NMEA UDP output -> {pc_ip}:{udp_port} (INS often {ins_ip}).",
            "Start bridge BEFORE opening Mission Planner on the Cube COM.",
            "MP sees position via the autopilot UART — not this PC's COM GPS.",
        ]
        if notes:
            lines.append(notes)
        self._log_ui("\n".join(lines))

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(w)
        outer.setSpacing(10)

        title = QtWidgets.QLabel("NMEA Serial Bridge")
        title.setObjectName("appTitle")
        sub = QtWidgets.QLabel(
            f"v{__version__} — Ethernet NMEA (UDP) in, serial NMEA out to autopilot / bench"
        )
        sub.setObjectName("appSubtitle")
        sub.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(sub)

        self.status_banner = QtWidgets.QFrame()
        self.status_banner.setObjectName("statusBanner")
        self.status_banner.setProperty("state", "stopped")
        bl = QtWidgets.QVBoxLayout(self.status_banner)
        self.status_banner_text = QtWidgets.QLabel("Stopped")
        self.status_banner_text.setObjectName("statusBannerText")
        self.status_banner_text.setWordWrap(True)
        bl.addWidget(self.status_banner_text)
        outer.addWidget(self.status_banner)

        self.intent_hint = QtWidgets.QLabel()
        self.intent_hint.setObjectName("intentHint")
        self.intent_hint.setWordWrap(True)
        outer.addWidget(self.intent_hint)

        path_box = QtWidgets.QGroupBox("1 — Choose path")
        path_lay = QtWidgets.QHBoxLayout(path_box)
        self.btn_bench_preset = QtWidgets.QPushButton(
            "Desk test\ncom0com · 127.0.0.1\n(bench_defaults.json)"
        )
        self.btn_bench_preset.setObjectName("pathBench")
        self.btn_production_preset = QtWidgets.QPushButton(
            "Boat / INS\nLAN UDP → Cube COM\n(production block)"
        )
        self.btn_production_preset.setObjectName("pathProduction")
        path_lay.addWidget(self.btn_bench_preset)
        path_lay.addWidget(self.btn_production_preset)
        outer.addWidget(path_box)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        form_host = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(form_host)
        scroll.setWidget(form_host)
        outer.addWidget(scroll, 1)

        ser_box = QtWidgets.QGroupBox("2 — Serial (bridge owns this COM)")
        ser_form = QtWidgets.QFormLayout(ser_box)
        self.com_cb = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh ports")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.com_cb, 1)
        row.addWidget(self.refresh_btn)
        cw = QtWidgets.QWidget()
        cw.setLayout(row)
        ser_form.addRow("COM port:", cw)
        self.baud_edit = QtWidgets.QLineEdit("115200")
        ser_form.addRow("Baud:", self.baud_edit)
        form.addRow(ser_box)

        net_box = QtWidgets.QGroupBox("3 — Network (UDP listen on this PC)")
        net_outer = QtWidgets.QVBoxLayout(net_box)
        udp_row = QtWidgets.QFormLayout()
        self.udp_host = QtWidgets.QLineEdit("0.0.0.0")
        self.udp_port = QtWidgets.QLineEdit("10110")
        udp_row.addRow("Listen on:", self.udp_host)
        udp_row.addRow("UDP port:", self.udp_port)
        net_outer.addLayout(udp_row)
        self.chk_advanced_net = QtWidgets.QCheckBox("Show advanced modes (TCP / UDP remote)")
        net_outer.addWidget(self.chk_advanced_net)
        self._advanced_net = QtWidgets.QWidget()
        adv_lay = QtWidgets.QVBoxLayout(self._advanced_net)
        mode_box = QtWidgets.QGroupBox("Mode")
        mode_lay = QtWidgets.QVBoxLayout(mode_box)
        self.mode_group = QtWidgets.QButtonGroup(self)
        self.rb_udp_listen = QtWidgets.QRadioButton("UDP listen (standard)")
        self.rb_udp_remote = QtWidgets.QRadioButton("UDP remote")
        self.rb_tcp_server = QtWidgets.QRadioButton("TCP server")
        self.rb_tcp_client = QtWidgets.QRadioButton("TCP client")
        self.rb_udp_listen.setChecked(True)
        for rb in (self.rb_udp_listen, self.rb_udp_remote, self.rb_tcp_server, self.rb_tcp_client):
            self.mode_group.addButton(rb)
            mode_lay.addWidget(rb)
        adv_lay.addWidget(mode_box)
        self._udp_box = QtWidgets.QGroupBox("UDP remote fields")
        udp_form = QtWidgets.QFormLayout(self._udp_box)
        self.remote_host = QtWidgets.QLineEdit("192.168.1.100")
        self.remote_port = QtWidgets.QLineEdit("10110")
        udp_form.addRow("Remote host:", self.remote_host)
        udp_form.addRow("Remote port:", self.remote_port)
        adv_lay.addWidget(self._udp_box)
        self._tcp_srv_box = QtWidgets.QGroupBox("TCP server")
        tcp_srv_form = QtWidgets.QFormLayout(self._tcp_srv_box)
        self.tcp_srv_host = QtWidgets.QLineEdit("0.0.0.0")
        self.tcp_srv_port = QtWidgets.QLineEdit("4001")
        tcp_srv_form.addRow("Bind host:", self.tcp_srv_host)
        tcp_srv_form.addRow("Port:", self.tcp_srv_port)
        adv_lay.addWidget(self._tcp_srv_box)
        self._tcp_cli_box = QtWidgets.QGroupBox("TCP client")
        tcp_cli_form = QtWidgets.QFormLayout(self._tcp_cli_box)
        self.tcp_cli_host = QtWidgets.QLineEdit("127.0.0.1")
        self.tcp_cli_port = QtWidgets.QLineEdit("4001")
        tcp_cli_form.addRow("Host:", self.tcp_cli_host)
        tcp_cli_form.addRow("Port:", self.tcp_cli_port)
        adv_lay.addWidget(self._tcp_cli_box)
        self.tcp_reconnect_spin = QtWidgets.QDoubleSpinBox()
        self.tcp_reconnect_spin.setRange(TCP_RECONNECT_MIN_S, TCP_RECONNECT_MAX_S)
        self.tcp_reconnect_spin.setSingleStep(0.5)
        self.tcp_reconnect_spin.setDecimals(1)
        self.tcp_reconnect_spin.setSuffix(" s")
        self.tcp_reconnect_spin.setValue(DEFAULT_TCP_RECONNECT_S)
        adv_lay.addWidget(self.tcp_reconnect_spin)
        self._advanced_net.setVisible(False)
        net_outer.addWidget(self._advanced_net)
        form.addRow(net_box)

        act_box = QtWidgets.QGroupBox("4 — Run")
        act_lay = QtWidgets.QHBoxLayout(act_box)
        self.start_btn = QtWidgets.QPushButton("Start bridge")
        self.start_btn.setObjectName("btnStart")
        self.stop_btn = QtWidgets.QPushButton("Stop bridge")
        self.stop_btn.setObjectName("btnStop")
        self.stop_btn.setEnabled(False)
        act_lay.addWidget(self.start_btn, 2)
        act_lay.addWidget(self.stop_btn, 1)
        outer.addWidget(act_box)

        self.lbl_bridge_state = QtWidgets.QLabel("")
        self.lbl_bridge_state.hide()

        self.btn_bench_preset.clicked.connect(self._apply_bench_preset)
        self.btn_production_preset.clicked.connect(self._apply_production_preset)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn.clicked.connect(self.stop_bridge)
        self.chk_advanced_net.toggled.connect(self._on_advanced_net_toggle)
        for rb in (self.rb_udp_listen, self.rb_udp_remote, self.rb_tcp_server, self.rb_tcp_client):
            rb.toggled.connect(self._mode_toggle)

        self._connection_widgets = [
            self.btn_bench_preset,
            self.btn_production_preset,
            self.com_cb,
            self.refresh_btn,
            self.baud_edit,
            self.chk_advanced_net,
            self.rb_udp_listen,
            self.rb_udp_remote,
            self.rb_tcp_server,
            self.rb_tcp_client,
            self.udp_host,
            self.udp_port,
            self.remote_host,
            self.remote_port,
            self.tcp_srv_host,
            self.tcp_srv_port,
            self.tcp_cli_host,
            self.tcp_cli_port,
            self.tcp_reconnect_spin,
        ]
        self._set_status_banner("stopped", "Stopped", "Choose a path, then Start bridge.")
        self._refresh_intent_hint()
        return w

    def _on_advanced_net_toggle(self, checked: bool) -> None:
        self._advanced_net.setVisible(checked)
        self._mode_toggle()

    def _build_nmea_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)

        self.nmea_mode_group = QtWidgets.QButtonGroup(self)
        self.rb_nmea_passthrough = QtWidgets.QRadioButton(
            "Passthrough — rebuild lines only (recommended for first test)"
        )
        self.rb_nmea_strict = QtWidgets.QRadioButton(
            "Strict — valid checksum + only checked sentence types below"
        )
        self.rb_nmea_passthrough.setChecked(True)
        self.nmea_mode_group.addButton(self.rb_nmea_passthrough)
        self.nmea_mode_group.addButton(self.rb_nmea_strict)
        v.addWidget(self.rb_nmea_passthrough)
        v.addWidget(self.rb_nmea_strict)

        types_box = QtWidgets.QGroupBox("Sentence types to allow (Strict mode only)")
        grid = QtWidgets.QGridLayout(types_box)
        self._nmea_type_checks: dict[str, QtWidgets.QCheckBox] = {}
        defaults_on = {"GGA", "RMC", "ZDA"}
        for i, st in enumerate(NMEA_SENTENCE_TYPES):
            cb = QtWidgets.QCheckBox(st)
            cb.setChecked(st in defaults_on)
            cb.setToolTip(f"Allow ${st} sentences (e.g. $GP{st})")
            self._nmea_type_checks[st] = cb
            grid.addWidget(cb, i // 3, i % 3)
        v.addWidget(types_box)

        hint = QtWidgets.QLabel(
            "If no boxes are checked in Strict mode, all valid NMEA types are allowed. "
            "Passthrough ignores the checkboxes."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addStretch(1)

        self._nmea_widgets = [self.rb_nmea_passthrough, self.rb_nmea_strict, *self._nmea_type_checks.values()]
        return w

    def _selected_nmea_mode(self) -> NmeaMode:
        return NmeaMode.STRICT if self.rb_nmea_strict.isChecked() else NmeaMode.PASSTHROUGH

    def _selected_nmea_filter(self) -> NmeaFilter:
        enabled = {st for st, cb in self._nmea_type_checks.items() if cb.isChecked()}
        return NmeaFilter(enabled_types=enabled)

    def _build_send_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        hint = QtWidgets.QLabel(
            "Edit NMEA below, then Send. Connect tab must show Running first."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.send_edit = QtWidgets.QPlainTextEdit()
        self.send_edit.setObjectName("sendEdit")
        self.send_edit.setPlaceholderText("NMEA here — gray placeholder text is NOT sent.")
        self.send_edit.setPlainText('$GPGGA,080339.81,3841.1448,N,12104.9514,W,1,10,0.9,255.0,M,-25.0,M,,*5E')
        self.send_edit.setFixedHeight(100)
        v.addWidget(self.send_edit)
        row = QtWidgets.QHBoxLayout()
        self.btn_insert_sample = QtWidgets.QPushButton("Insert EDH sample GGA")
        self.btn_insert_sample.clicked.connect(self._insert_send_sample)
        row.addWidget(self.btn_insert_sample)
        row.addStretch(1)
        v.addLayout(row)
        row2 = QtWidgets.QHBoxLayout()
        self.btn_send_ser = QtWidgets.QPushButton("Send -> serial")
        self.btn_send_net = QtWidgets.QPushButton("Send -> network")
        self.btn_send_both = QtWidgets.QPushButton("Send -> both")
        row2.addWidget(self.btn_send_ser)
        row2.addWidget(self.btn_send_net)
        row2.addWidget(self.btn_send_both)
        v.addLayout(row2)
        self.btn_send_ser.clicked.connect(lambda: self._send_manual("serial"))
        self.btn_send_net.clicked.connect(lambda: self._send_manual("net"))
        self.btn_send_both.clicked.connect(lambda: self._send_manual("both"))
        return w

    def _insert_send_sample(self) -> None:
        when = datetime.now(timezone.utc)
        gga = build_gga(when, EDH_LAT_DEG, EDH_LON_DEG, EDH_ALT_M)
        rmc = build_rmc(when, EDH_LAT_DEG, EDH_LON_DEG)
        self.send_edit.setPlainText(f"{gga}\r\n{rmc}")

    def _build_log_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        self.chk_file_log = QtWidgets.QCheckBox("Enable rotating file log")
        form.addRow(self.chk_file_log)
        row = QtWidgets.QHBoxLayout()
        self.file_log_path = QtWidgets.QLineEdit(str(Path.home() / "bridge_survey.log"))
        self.btn_browse = QtWidgets.QPushButton("Browse…")
        row.addWidget(self.file_log_path, 1)
        row.addWidget(self.btn_browse)
        rw = QtWidgets.QWidget()
        rw.setLayout(row)
        form.addRow("Log file path:", rw)
        self.btn_browse.clicked.connect(self._browse_log)
        self.btn_clear_ui = QtWidgets.QPushButton("Clear on-screen log")
        self.btn_clear_ui.clicked.connect(self.log_view.clear)
        form.addRow(self.btn_clear_ui)
        return w

    def _browse_log(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Survey log file", self.file_log_path.text(), "Log files (*.log);;All files (*)")
        if path:
            self.file_log_path.setText(path)

    def _mode_toggle(self, *_args) -> None:
        m_udp_l = self.rb_udp_listen.isChecked()
        m_udp_r = self.rb_udp_remote.isChecked()
        m_tcp_s = self.rb_tcp_server.isChecked()
        m_tcp_c = self.rb_tcp_client.isChecked()

        self._udp_box.setVisible(m_udp_l or m_udp_r)
        self.udp_host.setEnabled(m_udp_l)
        self.udp_port.setEnabled(m_udp_l or m_udp_r)
        self.remote_host.setEnabled(m_udp_r)
        self.remote_port.setEnabled(m_udp_r)

        self._tcp_srv_box.setVisible(m_tcp_s)
        self._tcp_cli_box.setVisible(m_tcp_c)
        self.tcp_srv_host.setEnabled(m_tcp_s)
        self.tcp_srv_port.setEnabled(m_tcp_s)
        self.tcp_cli_host.setEnabled(m_tcp_c)
        self.tcp_cli_port.setEnabled(m_tcp_c)
        self._refresh_intent_hint()
        self.tcp_reconnect_spin.setEnabled(m_tcp_c)

    def _enqueue_ui(self, line: str) -> None:
        while len(self._pending_ui) >= UI_LOG_PENDING_MAX:
            self._pending_ui.popleft()
            self._ui_drops += 1
        self._pending_ui.append(line)

    def _flush_ui_log(self) -> None:
        if not self._pending_ui:
            return
        n = min(UI_LOG_MAX_LINES_PER_FLUSH, len(self._pending_ui))
        chunk = [self._pending_ui.popleft() for _ in range(n)]
        self.log_view.appendPlainText("\n".join(chunk))
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _log_ui(self, txt: str) -> None:
        self._enqueue_ui(txt)

    def _update_status_bar(self, serial_line: str, network_line: str) -> None:
        self.status_serial.setText(serial_line)
        self.status_network.setText(network_line)

    def _set_connection_locked(self, locked: bool) -> None:
        for w in self._connection_widgets:
            w.setEnabled(not locked)
        for w in getattr(self, "_nmea_widgets", []):
            w.setEnabled(not locked)
        self.start_btn.setEnabled(not locked)
        self.stop_btn.setEnabled(locked)

    def _stats_from_bridge(self, d: dict) -> None:
        self.lbl_stats.setText(
            f"Drops {d['drops_n2s']}/{d['drops_s2n']} | "
            f"Reject {d['rej_n2s']}/{d['rej_s2n']} | "
            f"Q {d['n2s_q']}/{d['s2n_q']}"
        )

    def _tick_stats(self) -> None:
        if self.bridge:
            self._stats_from_bridge(
                {
                    "drops_n2s": self.bridge.drops_net_to_serial,
                    "drops_s2n": self.bridge.drops_serial_to_net,
                    "rej_n2s": self.bridge.rejected_net_to_serial,
                    "rej_s2n": self.bridge.rejected_serial_to_net,
                    "n2s_q": self.bridge.net_to_serial.qsize(),
                    "s2n_q": self.bridge.serial_to_net.qsize(),
                }
            )
        else:
            self.lbl_stats.setText("Drops 0/0 | Reject 0/0 | Q 0/0")

    def refresh_ports(self) -> None:
        self.com_cb.clear()
        for p in serial.tools.list_ports.comports():
            self.com_cb.addItem(p.device)

    def _send_manual(self, where: str) -> None:
        if not self.bridge or not self.bridge.running:
            self._log_ui(
                "Send: bridge not running — Connect tab: choose path, Start, wait for Running."
            )
            return
        raw = self.send_edit.toPlainText()
        data = _nmea_line_bytes(raw)
        if not data:
            self._log_ui(
                "Send: box is empty — type/paste NMEA in tab 3, or click Insert EDH sample GGA."
            )
            return
        self._log_ui(f"Send: {len(data)} bytes -> {where}")
        b = self.bridge
        w = self._worker

        def _do() -> None:
            if not b.running:
                return
            if where == "serial":
                b.schedule_net_to_serial(data, "GUI→SER")
            elif where == "net":
                b.schedule_serial_to_net(data, "GUI→NET")
            else:
                b.schedule_net_to_serial(data, "GUI→SER")
                b.schedule_serial_to_net(data, "GUI→NET")

        if w:
            w.call_on_loop(_do)
        else:
            _do()

    def start_bridge(self) -> None:
        err = self._validate_before_start()
        if err:
            self._log_ui(err)
            QtWidgets.QMessageBox.warning(self, "Cannot start", err)
            return
        com = self.com_cb.currentText().strip()
        try:
            baud = int(self.baud_edit.text())
            if baud <= 0:
                raise ValueError("baud must be positive")
        except ValueError:
            self._log_ui("Invalid baud rate — enter a positive number (e.g. 115200).")
            QtWidgets.QMessageBox.warning(self, "Cannot start", "Enter a valid baud rate.")
            return

        if self.chk_file_log.isChecked():
            try:
                self._file_log = _FileSurveyLog(Path(self.file_log_path.text().strip()))
            except Exception as e:
                self._log_ui(f"File log error: {e}")
                QtWidgets.QMessageBox.warning(self, "File log", f"Could not open log file:\n{e}")
                self._file_log = None
        else:
            self._file_log = None

        udp_listen = None
        udp_remote = None
        mode: NetMode
        tcp_reconnect = self.tcp_reconnect_spin.value()

        try:
            if self.rb_udp_listen.isChecked():
                mode = NetMode.UDP_LISTEN
                udp_listen = (self.udp_host.text().strip(), _parse_port(self.udp_port.text(), "UDP port"))
            elif self.rb_udp_remote.isChecked():
                mode = NetMode.UDP_REMOTE
                host = self.remote_host.text().strip()
                if not host:
                    raise ValueError("UDP remote host is required")
                udp_remote = (host, _parse_port(self.remote_port.text(), "UDP remote port"))
            elif self.rb_tcp_server.isChecked():
                mode = NetMode.TCP_SERVER
                tcp_bh = self.tcp_srv_host.text().strip()
                tcp_bp = _parse_port(self.tcp_srv_port.text(), "TCP server port")
            else:
                mode = NetMode.TCP_CLIENT
                tcp_ch = self.tcp_cli_host.text().strip()
                if not tcp_ch:
                    raise ValueError("TCP client host is required")
                tcp_cp = _parse_port(self.tcp_cli_port.text(), "TCP client port")
        except ValueError as e:
            self._log_ui(str(e))
            QtWidgets.QMessageBox.warning(self, "Cannot start", str(e))
            return

        if self._worker and self._worker.isRunning():
            self._log_ui("Stop the bridge before starting again.")
            return

        file_log = self._file_log
        nmea_mode = self._selected_nmea_mode()
        nmea_filter = self._selected_nmea_filter()
        verbose = self.chk_verbose_log.isChecked

        def build(loop: asyncio.AbstractEventLoop) -> SerialNetBridge:
            common = dict(
                loop=loop,
                ui_log=self._worker.log_msg.emit,
                ui_log_verbose=verbose,
                status_cb=self._worker.status_msg.emit,
                stats_cb=self._worker.stats_msg.emit,
                file_log=file_log,
                tcp_reconnect_delay=tcp_reconnect,
                nmea_mode=nmea_mode,
                nmea_filter=nmea_filter,
            )
            if mode == NetMode.TCP_SERVER:
                return SerialNetBridge(
                    com, baud, mode, tcp_bind_host=tcp_bh, tcp_bind_port=tcp_bp, **common
                )
            if mode == NetMode.TCP_CLIENT:
                return SerialNetBridge(
                    com, baud, mode, tcp_client_host=tcp_ch, tcp_client_port=tcp_cp, **common
                )
            return SerialNetBridge(
                com, baud, mode, udp_listen=udp_listen, udp_remote=udp_remote, **common
            )

        self._set_connection_locked(True)
        self._update_status_bar("Serial: starting…", "Network: starting…")
        self._starting = True
        self._set_status_banner("starting", "Starting…", f"Opening {com} and UDP :{self.udp_port.text()}")
        self._start_gen += 1
        gen = self._start_gen
        self._log_ui(f"Start: opening {com} @ {baud} (background thread)…")

        self._worker = BridgeAsyncThread(build)
        self._worker.log_msg.connect(self._log_ui)
        self._worker.status_msg.connect(self._update_status_bar)
        self._worker.stats_msg.connect(self._stats_from_bridge)
        self._worker.start_done.connect(lambda ok: self._on_worker_start_done(ok, gen))
        self._start_watchdog_timer.start(START_WATCHDOG_MS)
        self._worker.start()

    def _on_worker_start_done(self, ok: bool, gen: int) -> None:
        self._start_watchdog_timer.stop()
        if gen != self._start_gen:
            return
        worker = self._worker
        if ok and worker and worker.bridge:
            self.bridge = worker.bridge
            self._on_bridge_started(self.bridge)
            return
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._worker = None
        self.bridge = None
        self._fail_start_ui(
            "Serial or network could not be opened. See the live log for details."
        )

    def _fail_start_ui(self, message: str) -> None:
        self.bridge = None
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._worker.wait(2000)
        self._worker = None
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self._update_status_bar("Serial: stopped", "Network: stopped")
        self._starting = False
        self._set_status_banner("failed", "Start failed", message)
        self.start_btn.setText("Start bridge")
        QtWidgets.QMessageBox.critical(self, "Bridge failed to start", message)

    def _start_watchdog_fired(self) -> None:
        worker = self._worker
        b = self.bridge or (worker.bridge if worker else None)
        if b and b.running and b._network_ready:
            return
        self._start_gen += 1
        self._log_ui(
            "Start timed out (>15s).\n"
            "Close the app, run: python com_free.py, then launch again."
        )
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._fail_start_ui(
            "Start timed out after 15 seconds.\n\n"
            "Close any app using the COM port, run python com_free.py, then try again."
        )

    def _on_bridge_started(self, b: SerialNetBridge) -> None:
        self._starting = False
        self._set_status_banner("running", "Running", f"{b.com} @ {b.baud} — UDP listen :{b.udp_listen[1] if b.udp_listen else '?'}")
        self.start_btn.setText("Running…")
        if b.mode == NetMode.UDP_LISTEN and b.udp_listen:
            host, port = b.udp_listen
            dest = f"127.0.0.1:{port}" if host in ("0.0.0.0", "", "::") else f"{host}:{port}"
            self._log_ui(
                "=== BRIDGE RUNNING ===\n"
                f"UDP listen {host}:{port} -> {b.com} @ {b.baud}.\n"
                "The bridge is idle until NMEA arrives — that is normal.\n"
                f"Send traffic to {dest} (e.g. python nmea_static_edh.py), or Tab 3 Send -> serial.\n"
                f"Watch paired COM (e.g. COM12) in Tera Term — not {b.com}."
            )
        else:
            self._log_ui(
                f"=== BRIDGE RUNNING === {b.com} @ {b.baud} ({b.mode.value}). "
                "Idle until data moves on the wire."
            )

    def stop_bridge(self) -> None:
        if self._stopping:
            self._finish_stop_ui()
            return
        worker = self._worker
        self.bridge = None
        self._worker = None
        if not worker:
            self._finish_stop_ui()
            return

        self._stopping = True
        self._update_status_bar("Serial: stopping…", "Network: stopping…")
        self._log_ui("Stopping bridge…")
        worker.request_stop()
        worker.wait(4000)
        self._finish_stop_ui()
        self._start_gen += 1
        self._start_watchdog_timer.stop()

    def _stop_timeout_guard(self) -> None:
        if not self._stopping:
            return
        self._log_ui(
            "Stop took too long — UI reset. Close Tera Term/PuTTY on the COM port, then try again."
        )
        self._finish_stop_ui()

    def _finish_stop_ui(self) -> None:
        """Re-enable controls on the Qt main thread after async stop."""
        self._stop_guard_timer.stop()
        self._stopping = False
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self.stop_btn.setText("■  Stop bridge")
        self._starting = False
        self.start_btn.setText("Start bridge")
        self._set_status_banner("stopped", "Stopped", "Choose a path and Start when ready.")
        self._update_status_bar("Serial: stopped", "Network: stopped")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        running = self.bridge and self.bridge.running
        worker = self._worker
        if running or (worker and worker.isRunning()):
            event.ignore()
            self.bridge = None
            if worker:
                worker.request_stop()
                worker.wait(4000)
            self._worker = None
            self._finish_stop_ui()
            self._start_gen += 1
            QtCore.QTimer.singleShot(200, self.close)
            return
        event.accept()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    w = BridgeWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
