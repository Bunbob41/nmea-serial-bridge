# bridge_gui.py — Network (UDP / TCP) ↔ COM bridge, Windows PySide6
# Python 3.10+  |  pip install -r requirements.txt
from __future__ import annotations

import asyncio
import errno
import logging
import sys
import time
from collections import deque
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, List, Optional

import qasync
import serial
import serial_asyncio
import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from nmea_codec import NmeaLineAssembler, NmeaMode, feed_nmea_times_from_lines, parse_nmea_utc
from version import __version__

# --- Constants ---
NET_TO_SERIAL_QUEUE_MAX = 512
SERIAL_TO_NET_QUEUE_MAX = 512
UI_LOG_PENDING_MAX = 2000
UI_LOG_FLUSH_MS = 120
UI_LOG_MAX_LINES_PER_FLUSH = 96
UI_VIEW_MAX_BLOCK_COUNT = 4000
FILE_LOG_MAX_BYTES = 10 * 1024 * 1024
FILE_LOG_BACKUP_COUNT = 5
DEFAULT_TCP_RECONNECT_S = 1.0
TCP_RECONNECT_MIN_S = 0.5
TCP_RECONNECT_MAX_S = 60.0


def _friendly_serial_error(exc: BaseException, port: str) -> str:
    msg = str(exc).strip()
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
        self._tasks: list[asyncio.Task] = []
        self._serial_open = False
        self._network_ready = False

    def _set_status(self, serial_line: str, network_line: str) -> None:
        self._status_cb(serial_line, network_line)

    def _gps_utc(self) -> str:
        return self._gps_state[0] or ""

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

    def _log(self, direction: str, data: bytes, *, to_ui: bool = True) -> None:
        preview = data.decode(errors="replace").rstrip().replace("\r", "\\r")
        gps = self._gps_utc()
        if self._file_log:
            try:
                self._file_log.write(direction, preview, gps)
            except Exception:
                pass
        if to_ui:
            self._ui_log(f"{direction} | gps={gps or '—'} | {preview}")

    def _enqueue_net_to_serial(self, data: bytes, direction: str) -> None:
        try:
            self.net_to_serial.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_net_to_serial += 1
            self._emit_stats()
            self._log(f"{direction} [DROP n→s]", data, to_ui=True)
        else:
            self._log(direction, data)

    def _enqueue_serial_to_net(self, data: bytes, direction: str) -> None:
        try:
            self.serial_to_net.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_serial_to_net += 1
            self._emit_stats()
            self._log(f"{direction} [DROP s→n]", data, to_ui=True)
        else:
            self._log(direction, data)

    def _ingest_net(self, data: bytes, direction: str) -> None:
        result = self._asm_n2s.feed(data, self.nmea_mode)
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        for reason in result.rejected:
            self.rejected_net_to_serial += 1
            self._emit_stats()
            self._log_text(f"{direction} [REJECT] {reason}")
        for line in result.forward:
            self._enqueue_net_to_serial(line, direction)

    def _ingest_serial(self, data: bytes, direction: str) -> None:
        result = self._asm_s2n.feed(data, self.nmea_mode)
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

    async def start(self) -> bool:
        self._set_status(f"Serial: opening {self.com} @ {self.baud}…", "Network: starting…")
        self._ui_log(f"Opening serial {self.com} @ {self.baud}")
        try:
            self.serial_reader, self.serial_writer = await serial_asyncio.open_serial_connection(
                url=self.com, baudrate=self.baud
            )
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
                self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                    lambda: UDPRecvProtocol(self), local_addr=self.udp_listen
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
        while self.running:
            try:
                data = await self.serial_reader.read(4096)
            except Exception as e:
                self._ui_log(_friendly_serial_error(e, self.com))
                break
            if not data:
                await asyncio.sleep(0.01)
                continue
            self._ingest_serial(data, "SER→NET")

    async def _pump_net_to_serial(self) -> None:
        while self.running:
            chunk = await self.net_to_serial.get()
            if not self.serial_writer:
                continue
            try:
                self.serial_writer.write(chunk)
                await self.serial_writer.drain()
            except Exception as e:
                self._ui_log(_friendly_serial_error(e, self.com))

    async def _pump_serial_to_net_queue(self) -> None:
        while self.running:
            chunk = await self.serial_to_net.get()
            await self._send_net(chunk)

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
            except Exception as e:
                self._ui_log(_friendly_network_error(e, "TCP send"))

    async def stop(self) -> None:
        self.running = False

        for t in list(self._tasks):
            t.cancel()
        self._tasks.clear()

        if self._tcp_reader_task and not self._tcp_reader_task.done():
            self._tcp_reader_task.cancel()
        self._tcp_reader_task = None

        if self._tcp_server:
            self._tcp_server.close()
            try:
                await self._tcp_server.wait_closed()
            except Exception:
                pass
            self._tcp_server = None

        if self._tcp_client_task and not self._tcp_client_task.done():
            self._tcp_client_task.cancel()
            try:
                await self._tcp_client_task
            except asyncio.CancelledError:
                pass
        self._tcp_client_task = None

        if self.tcp_writer:
            try:
                self.tcp_writer.close()
                await self.tcp_writer.wait_closed()
            except Exception:
                pass
        self.tcp_reader = None
        self.tcp_writer = None

        if self.udp_transport:
            try:
                self.udp_transport.close()
            except Exception:
                pass
            self.udp_transport = None

        if self.serial_writer:
            try:
                self.serial_writer.close()
                await self.serial_writer.wait_closed()
            except Exception:
                pass
        self.serial_writer = None
        self.serial_reader = None
        self._serial_open = False
        self._network_ready = False
        self._asm_n2s.reset()
        self._asm_s2n.reset()

        self._set_status("Serial: closed", "Network: stopped")
        self._ui_log("Bridge stopped")


class BridgeWindow(QtWidgets.QWidget):
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__()
        self.setWindowTitle(f"Network ↔ COM Bridge v{__version__}")
        self.resize(980, 560)
        self.loop = loop or asyncio.get_event_loop()

        self.bridge: Optional[SerialNetBridge] = None
        self._file_log: Optional[_FileSurveyLog] = None

        self._pending_ui: Deque[str] = deque()
        self._ui_drops = 0

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(UI_VIEW_MAX_BLOCK_COUNT)

        root = QtWidgets.QHBoxLayout()
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_settings_tab(), "Connection")
        tabs.addTab(self._build_nmea_tab(), "NMEA")
        tabs.addTab(self._build_send_tab(), "Send")
        tabs.addTab(self._build_log_tab(), "Log / QA")
        root.addWidget(tabs, 1)
        root.addWidget(self.log_view, 1)

        self.statusBar = QtWidgets.QStatusBar()
        self.status_serial = QtWidgets.QLabel("Serial: stopped")
        self.status_network = QtWidgets.QLabel("Network: stopped")
        self.statusBar.addWidget(self.status_serial, 1)
        self.statusBar.addPermanentWidget(self.status_network, 1)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 4)
        outer.addLayout(root)
        outer.addWidget(self.statusBar)

        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)

        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)
        self._stats_timer.start(400)

        self.refresh_ports()
        self._mode_toggle()

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)

        self.com_cb = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh ports")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.com_cb, 1)
        row.addWidget(self.refresh_btn)
        cw = QtWidgets.QWidget()
        cw.setLayout(row)
        form.addRow("COM port:", cw)

        self.baud_edit = QtWidgets.QLineEdit("115200")
        form.addRow("Baud:", self.baud_edit)

        self.mode_group = QtWidgets.QButtonGroup(self)
        self.rb_udp_listen = QtWidgets.QRadioButton("UDP listen")
        self.rb_udp_remote = QtWidgets.QRadioButton("UDP remote (fixed)")
        self.rb_tcp_server = QtWidgets.QRadioButton("TCP server (listen)")
        self.rb_tcp_client = QtWidgets.QRadioButton("TCP client (connect)")
        self.rb_udp_listen.setChecked(True)
        for rb in (self.rb_udp_listen, self.rb_udp_remote, self.rb_tcp_server, self.rb_tcp_client):
            self.mode_group.addButton(rb)
        form.addRow(self.rb_udp_listen)
        form.addRow(self.rb_udp_remote)
        form.addRow(self.rb_tcp_server)
        form.addRow(self.rb_tcp_client)

        self.udp_host = QtWidgets.QLineEdit("0.0.0.0")
        self.udp_port = QtWidgets.QLineEdit("10110")
        form.addRow("UDP bind host:", self.udp_host)
        form.addRow("UDP bind / local port:", self.udp_port)

        self.remote_host = QtWidgets.QLineEdit("192.168.1.100")
        self.remote_port = QtWidgets.QLineEdit("10110")
        form.addRow("UDP remote host:", self.remote_host)
        form.addRow("UDP remote port:", self.remote_port)

        self.tcp_srv_host = QtWidgets.QLineEdit("0.0.0.0")
        self.tcp_srv_port = QtWidgets.QLineEdit("4001")
        form.addRow("TCP server bind host:", self.tcp_srv_host)
        form.addRow("TCP server port:", self.tcp_srv_port)

        self.tcp_cli_host = QtWidgets.QLineEdit("127.0.0.1")
        self.tcp_cli_port = QtWidgets.QLineEdit("4001")
        form.addRow("TCP client host:", self.tcp_cli_host)
        form.addRow("TCP client port:", self.tcp_cli_port)

        self.tcp_reconnect_spin = QtWidgets.QDoubleSpinBox()
        self.tcp_reconnect_spin.setRange(TCP_RECONNECT_MIN_S, TCP_RECONNECT_MAX_S)
        self.tcp_reconnect_spin.setSingleStep(0.5)
        self.tcp_reconnect_spin.setDecimals(1)
        self.tcp_reconnect_spin.setSuffix(" s")
        self.tcp_reconnect_spin.setValue(DEFAULT_TCP_RECONNECT_S)
        self.tcp_reconnect_spin.setToolTip("Delay before TCP client retries after disconnect or refused connection.")
        form.addRow("TCP client reconnect:", self.tcp_reconnect_spin)

        self.start_btn = QtWidgets.QPushButton("Start bridge")
        self.stop_btn = QtWidgets.QPushButton("Stop bridge")
        self.stop_btn.setEnabled(False)
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(self.start_btn)
        row2.addWidget(self.stop_btn)
        rw = QtWidgets.QWidget()
        rw.setLayout(row2)
        form.addRow(rw)

        self.lbl_stats = QtWidgets.QLabel(
            "Drops n→s: 0 | Drops s→n: 0 | Reject n→s: 0 | Reject s→n: 0 | q n→s: 0 | q s→n: 0 | UI log drops: 0"
        )
        self.lbl_stats.setWordWrap(True)
        form.addRow(self.lbl_stats)

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn.clicked.connect(self.stop_bridge)
        for rb in (self.rb_udp_listen, self.rb_udp_remote, self.rb_tcp_server, self.rb_tcp_client):
            rb.toggled.connect(self._mode_toggle)

        self._connection_widgets = [
            self.com_cb,
            self.refresh_btn,
            self.baud_edit,
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

        return w

    def _build_nmea_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        self.nmea_mode_group = QtWidgets.QButtonGroup(self)
        self.rb_nmea_passthrough = QtWidgets.QRadioButton("Passthrough (line assembly only)")
        self.rb_nmea_strict = QtWidgets.QRadioButton("Strict (NMEA/AIS checksum + $/! sentences only)")
        self.rb_nmea_passthrough.setChecked(True)
        self.nmea_mode_group.addButton(self.rb_nmea_passthrough)
        self.nmea_mode_group.addButton(self.rb_nmea_strict)
        form.addRow(self.rb_nmea_passthrough)
        form.addRow(self.rb_nmea_strict)
        hint = QtWidgets.QLabel(
            "TCP streams are reassembled into lines before forwarding. "
            "Strict mode drops lines with bad checksums or non-NMEA text (logged as REJECT)."
        )
        hint.setWordWrap(True)
        form.addRow(hint)
        self._nmea_widgets = [self.rb_nmea_passthrough, self.rb_nmea_strict]
        return w

    def _selected_nmea_mode(self) -> NmeaMode:
        return NmeaMode.STRICT if self.rb_nmea_strict.isChecked() else NmeaMode.PASSTHROUGH

    def _build_send_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        self.send_edit = QtWidgets.QPlainTextEdit()
        self.send_edit.setPlaceholderText("Type NMEA or raw text; \\r\\n added if missing.")
        self.send_edit.setFixedHeight(100)
        v.addWidget(self.send_edit)
        row = QtWidgets.QHBoxLayout()
        self.btn_send_ser = QtWidgets.QPushButton("Send → serial")
        self.btn_send_net = QtWidgets.QPushButton("Send → network")
        self.btn_send_both = QtWidgets.QPushButton("Send → both")
        row.addWidget(self.btn_send_ser)
        row.addWidget(self.btn_send_net)
        row.addWidget(self.btn_send_both)
        v.addLayout(row)
        self.btn_send_ser.clicked.connect(lambda: self._send_manual("serial"))
        self.btn_send_net.clicked.connect(lambda: self._send_manual("net"))
        self.btn_send_both.clicked.connect(lambda: self._send_manual("both"))
        return w

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

        self.udp_host.setEnabled(m_udp_l)
        self.udp_port.setEnabled(m_udp_l or m_udp_r)
        self.remote_host.setEnabled(m_udp_r)
        self.remote_port.setEnabled(m_udp_r)

        self.tcp_srv_host.setEnabled(m_tcp_s)
        self.tcp_srv_port.setEnabled(m_tcp_s)
        self.tcp_cli_host.setEnabled(m_tcp_c)
        self.tcp_cli_port.setEnabled(m_tcp_c)
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
            f"Drops n→s: {d['drops_n2s']} | Drops s→n: {d['drops_s2n']} | "
            f"Reject n→s: {d['rej_n2s']} | Reject s→n: {d['rej_s2n']} | "
            f"q n→s: {d['n2s_q']} | q s→n: {d['s2n_q']} | UI log drops: {self._ui_drops}"
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
            self.lbl_stats.setText(
                f"Drops n→s: 0 | Drops s→n: 0 | Reject n→s: 0 | Reject s→n: 0 | "
                f"q n→s: 0 | q s→n: 0 | UI log drops: {self._ui_drops}"
            )

    def refresh_ports(self) -> None:
        self.com_cb.clear()
        for p in serial.tools.list_ports.comports():
            self.com_cb.addItem(p.device)

    def _send_manual(self, where: str) -> None:
        raw = self.send_edit.toPlainText()
        data = _nmea_line_bytes(raw)
        if not data:
            self._log_ui("Send: empty")
            return
        if not self.bridge or not self.bridge.running:
            self._log_ui("Send: bridge not running")
            return
        if where == "serial":
            self.bridge.schedule_net_to_serial(data, "GUI→SER")
        elif where == "net":
            self.bridge.schedule_serial_to_net(data, "GUI→NET")
        else:
            self.bridge.schedule_net_to_serial(data, "GUI→SER")
            self.bridge.schedule_serial_to_net(data, "GUI→NET")

    def start_bridge(self) -> None:
        com = self.com_cb.currentText()
        if not com:
            self._log_ui("No COM port selected — click Refresh ports or connect the device.")
            QtWidgets.QMessageBox.warning(self, "Cannot start", "Select a COM port first.")
            return
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

        common = dict(
            loop=self.loop,
            ui_log=self._log_ui,
            status_cb=self._update_status_bar,
            stats_cb=self._stats_from_bridge,
            file_log=self._file_log,
            tcp_reconnect_delay=tcp_reconnect,
            nmea_mode=self._selected_nmea_mode(),
        )

        if mode == NetMode.TCP_SERVER:
            self.bridge = SerialNetBridge(
                com, baud, mode, tcp_bind_host=tcp_bh, tcp_bind_port=tcp_bp, **common
            )
        elif mode == NetMode.TCP_CLIENT:
            self.bridge = SerialNetBridge(
                com, baud, mode, tcp_client_host=tcp_ch, tcp_client_port=tcp_cp, **common
            )
        else:
            self.bridge = SerialNetBridge(
                com, baud, mode, udp_listen=udp_listen, udp_remote=udp_remote, **common
            )

        self._set_connection_locked(True)
        self._update_status_bar("Serial: starting…", "Network: starting…")
        self.loop.create_task(self._run_start())

    async def _run_start(self) -> None:
        b = self.bridge
        if not b:
            return
        ok = await b.start()
        if not ok:
            self.bridge = None
            if self._file_log:
                self._file_log.close()
                self._file_log = None
            self._set_connection_locked(False)
            self._update_status_bar("Serial: stopped", "Network: stopped")
            QtWidgets.QMessageBox.critical(
                self,
                "Bridge failed to start",
                "Serial or network could not be opened. See the log for details.",
            )

    def stop_bridge(self) -> None:
        if self.bridge:
            b = self.bridge
            self.bridge = None
            self._set_connection_locked(True)
            self.stop_btn.setEnabled(False)
            self._update_status_bar("Serial: stopping…", "Network: stopping…")
            self.loop.create_task(self._stop_bridge_task(b))
        else:
            self._set_connection_locked(False)

    async def _stop_bridge_task(self, bridge: SerialNetBridge) -> None:
        await bridge.stop()
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self._update_status_bar("Serial: stopped", "Network: stopped")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.bridge and self.bridge.running:
            event.ignore()
            self._set_connection_locked(True)
            self._update_status_bar("Serial: stopping…", "Network: stopping…")

            async def _shutdown_then_close() -> None:
                b = self.bridge
                self.bridge = None
                if b:
                    await b.stop()
                if self._file_log:
                    self._file_log.close()
                    self._file_log = None
                self.close()

            self.loop.create_task(_shutdown_then_close())
            return
        event.accept()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    w = BridgeWindow(loop=loop)
    w.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
