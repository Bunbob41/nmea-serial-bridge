# bridge_gui.py — Network (UDP / TCP) ↔ COM bridge, Windows PySide6
# Python 3.10+  |  pip install pyserial pyserial-asyncio PySide6
from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections import deque
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, Optional

import serial_asyncio
import serial.tools.list_ports
from PySide6 import QtCore, QtWidgets

# --- Constants ---
NET_TO_SERIAL_QUEUE_MAX = 512
SERIAL_TO_NET_QUEUE_MAX = 512
UI_LOG_PENDING_MAX = 2000
UI_LOG_FLUSH_MS = 120
UI_LOG_MAX_LINES_PER_FLUSH = 96
UI_VIEW_MAX_BLOCK_COUNT = 4000
FILE_LOG_MAX_BYTES = 10 * 1024 * 1024
FILE_LOG_BACKUP_COUNT = 5


class NetMode(str, Enum):
    UDP_LISTEN = "udp_listen"
    UDP_REMOTE = "udp_remote"
    TCP_SERVER = "tcp_server"
    TCP_CLIENT = "tcp_client"


def _parse_nmea_utc(line: str) -> Optional[str]:
    """Return a short UTC hint from RMC or ZDA, or None."""
    s = line.strip()
    if len(s) < 10 or s[0] != "$":
        return None
    parts = s.split(",")
    if len(parts) < 2:
        return None
    head = parts[0]
    if len(head) >= 6 and "RMC" in head:
        if len(parts) >= 10 and parts[1] and parts[9]:
            return f"{parts[9]} {parts[1]} UTC (RMC)"
        return None
    if "ZDA" in head:
        if len(parts) >= 5 and parts[1] and parts[2] and parts[3] and parts[4]:
            return f"{parts[4]}-{parts[2].zfill(2)}-{parts[3].zfill(2)} {parts[1]} UTC (ZDA)"
        return None
    return None


def _feed_nmea_times(data: bytes, state: list) -> None:
    """state is single-element list holding last Optional[str] GPS UTC."""
    try:
        text = data.decode(errors="replace")
    except Exception:
        return
    for line in text.splitlines():
        u = _parse_nmea_utc(line)
        if u:
            state[0] = u


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
        loop: Optional[asyncio.AbstractEventLoop] = None,
        ui_log: Optional[Callable[[str], None]] = None,
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

        self.loop = loop or asyncio.get_event_loop()
        self._ui_log = ui_log or (lambda *_a, **_k: None)
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

        self.running = False
        self._tasks: list[asyncio.Task] = []

    def _gps_utc(self) -> str:
        return self._gps_state[0] or ""

    def _emit_stats(self) -> None:
        self._stats_cb(
            {
                "drops_n2s": self.drops_net_to_serial,
                "drops_s2n": self.drops_serial_to_net,
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

    def _try_put_net_to_serial(self, data: bytes, direction: str) -> None:
        _feed_nmea_times(data, self._gps_state)
        try:
            self.net_to_serial.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_net_to_serial += 1
            self._emit_stats()
            self._log(f"{direction} [DROP n→s]", data, to_ui=True)
        else:
            self._log(direction, data)

    def _try_put_serial_to_net(self, data: bytes, direction: str) -> None:
        _feed_nmea_times(data, self._gps_state)
        try:
            self.serial_to_net.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_serial_to_net += 1
            self._emit_stats()
            self._log(f"{direction} [DROP s→n]", data, to_ui=True)
        else:
            self._log(direction, data)

    def on_udp_datagram(self, data: bytes, addr) -> None:
        self.last_udp_addr = addr
        self._try_put_net_to_serial(data, f"UDP←{addr}")

    def schedule_net_to_serial(self, data: bytes, tag: str = "INJECT→SER") -> None:
        if not self.running or not data:
            return

        def _go() -> None:
            self._try_put_net_to_serial(data, tag)

        self.loop.call_soon(_go)

    def schedule_serial_to_net(self, data: bytes, tag: str = "INJECT→NET") -> None:
        if not self.running or not data:
            return

        def _go() -> None:
            self._try_put_serial_to_net(data, tag)

        self.loop.call_soon(_go)

    async def start(self) -> None:
        self._ui_log(f"Opening serial {self.com} @ {self.baud}")
        try:
            self.serial_reader, self.serial_writer = await serial_asyncio.open_serial_connection(
                url=self.com, baudrate=self.baud
            )
        except Exception as e:
            self._ui_log(f"Serial open error: {e}")
            return

        self.running = True

        self._tasks.append(asyncio.create_task(self._pump_net_to_serial(), name="pump_n2s"))
        self._tasks.append(asyncio.create_task(self._pump_serial_to_net_queue(), name="pump_s2n_out"))
        self._tasks.append(asyncio.create_task(self._serial_read_loop(), name="serial_read"))

        if self.mode == NetMode.UDP_LISTEN and self.udp_listen:
            self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPRecvProtocol(self), local_addr=self.udp_listen
            )
            self._ui_log(f"UDP listen on {self.udp_listen}")
        elif self.mode == NetMode.UDP_REMOTE and self.udp_remote:
            self.udp_transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPRecvProtocol(self), remote_addr=self.udp_remote
            )
            self._ui_log(f"UDP connected mode to {self.udp_remote}")
        elif self.mode == NetMode.TCP_SERVER:
            self._tcp_server = await asyncio.start_server(
                self._on_tcp_client, host=self.tcp_bind_host, port=self.tcp_bind_port
            )
            self._tasks.append(asyncio.create_task(self._serve_tcp_forever(), name="tcp_serve"))
            self._ui_log(f"TCP server listening {self.tcp_bind_host}:{self.tcp_bind_port}")
        elif self.mode == NetMode.TCP_CLIENT:
            self._tcp_client_task = asyncio.create_task(self._tcp_client_runner(), name="tcp_client")
            self._tasks.append(self._tcp_client_task)
            self._ui_log(f"TCP client → {self.tcp_client_host}:{self.tcp_client_port}")

    async def _serve_tcp_forever(self) -> None:
        assert self._tcp_server is not None
        async with self._tcp_server:
            await self._tcp_server.serve_forever()

    async def _on_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info("peername")
        self._ui_log(f"TCP client connected {addr}")
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
                self._try_put_net_to_serial(data, f"TCP←{addr}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._ui_log(f"TCP read error: {e}")
        finally:
            self._ui_log(f"TCP peer disconnected {addr}")
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
                self.tcp_reader, self.tcp_writer = await asyncio.open_connection(
                    self.tcp_client_host, self.tcp_client_port
                )
                addr = (self.tcp_client_host, self.tcp_client_port)
                self._ui_log(f"TCP connected to {addr}")
                await self._tcp_read_loop(addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._ui_log(f"TCP client error: {e}")
            finally:
                self.tcp_reader = None
                self.tcp_writer = None
            if self.running:
                await asyncio.sleep(1.0)

    async def _serial_read_loop(self) -> None:
        assert self.serial_reader is not None
        while self.running:
            try:
                data = await self.serial_reader.read(4096)
            except Exception as e:
                self._ui_log(f"Serial read error: {e}")
                break
            if not data:
                await asyncio.sleep(0.01)
                continue
            self._try_put_serial_to_net(data, "SER→NET")

    async def _pump_net_to_serial(self) -> None:
        while self.running:
            chunk = await self.net_to_serial.get()
            if not self.serial_writer:
                continue
            try:
                self.serial_writer.write(chunk)
                await self.serial_writer.drain()
            except Exception as e:
                self._ui_log(f"Serial write error: {e}")

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
                    self._ui_log(f"UDP send error: {e}")
        elif self.mode in (NetMode.TCP_SERVER, NetMode.TCP_CLIENT) and self.tcp_writer:
            try:
                self.tcp_writer.write(data)
                await self.tcp_writer.drain()
            except Exception as e:
                self._ui_log(f"TCP send error: {e}")

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

        self._ui_log("Bridge stopped")


class BridgeWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Network ↔ COM Bridge (Windows)")
        self.resize(980, 560)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.bridge: Optional[SerialNetBridge] = None
        self._file_log: Optional[_FileSurveyLog] = None

        self._pending_ui: Deque[str] = deque()
        self._ui_drops = 0

        root = QtWidgets.QHBoxLayout()
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_settings_tab(), "Connection")
        tabs.addTab(self._build_send_tab(), "Send")
        tabs.addTab(self._build_log_tab(), "Log / QA")
        root.addWidget(tabs, 1)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(UI_VIEW_MAX_BLOCK_COUNT)
        root.addWidget(self.log_view, 1)
        self.setLayout(root)

        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)

        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)
        self._stats_timer.start(400)

        self._asyncio_timer = QtCore.QTimer()
        self._asyncio_timer.timeout.connect(self._pump_asyncio)
        self._asyncio_timer.start(50)

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

        self.start_btn = QtWidgets.QPushButton("Start bridge")
        self.stop_btn = QtWidgets.QPushButton("Stop bridge")
        self.stop_btn.setEnabled(False)
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(self.start_btn)
        row2.addWidget(self.stop_btn)
        rw = QtWidgets.QWidget()
        rw.setLayout(row2)
        form.addRow(rw)

        self.lbl_stats = QtWidgets.QLabel("Drops n→s: 0 | Drops s→n: 0 | q n→s: 0 | q s→n: 0 | UI log drops: 0")
        self.lbl_stats.setWordWrap(True)
        form.addRow(self.lbl_stats)

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn.clicked.connect(self.stop_bridge)
        for rb in (self.rb_udp_listen, self.rb_udp_remote, self.rb_tcp_server, self.rb_tcp_client):
            rb.toggled.connect(self._mode_toggle)

        return w

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

    def _stats_from_bridge(self, d: dict) -> None:
        self.lbl_stats.setText(
            f"Drops n→s: {d['drops_n2s']} | Drops s→n: {d['drops_s2n']} | "
            f"q n→s: {d['n2s_q']} | q s→n: {d['s2n_q']} | UI log drops: {self._ui_drops}"
        )

    def _tick_stats(self) -> None:
        if self.bridge:
            self._stats_from_bridge(
                {
                    "drops_n2s": self.bridge.drops_net_to_serial,
                    "drops_s2n": self.bridge.drops_serial_to_net,
                    "n2s_q": self.bridge.net_to_serial.qsize(),
                    "s2n_q": self.bridge.serial_to_net.qsize(),
                }
            )
        else:
            self.lbl_stats.setText(
                f"Drops n→s: 0 | Drops s→n: 0 | q n→s: 0 | q s→n: 0 | UI log drops: {self._ui_drops}"
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
            self._log_ui("No COM selected")
            return
        try:
            baud = int(self.baud_edit.text())
        except ValueError:
            self._log_ui("Invalid baud")
            return

        if self.chk_file_log.isChecked():
            try:
                self._file_log = _FileSurveyLog(Path(self.file_log_path.text().strip()))
            except Exception as e:
                self._log_ui(f"File log error: {e}")
                self._file_log = None
        else:
            self._file_log = None

        udp_listen = None
        udp_remote = None
        mode: NetMode

        if self.rb_udp_listen.isChecked():
            mode = NetMode.UDP_LISTEN
            try:
                udp_listen = (self.udp_host.text().strip(), int(self.udp_port.text()))
            except ValueError:
                self._log_ui("Invalid UDP listen")
                return
        elif self.rb_udp_remote.isChecked():
            mode = NetMode.UDP_REMOTE
            try:
                udp_remote = (self.remote_host.text().strip(), int(self.remote_port.text()))
            except ValueError:
                self._log_ui("Invalid UDP remote")
                return
        elif self.rb_tcp_server.isChecked():
            mode = NetMode.TCP_SERVER
            try:
                tcp_bh = self.tcp_srv_host.text().strip()
                tcp_bp = int(self.tcp_srv_port.text())
            except ValueError:
                self._log_ui("Invalid TCP server port")
                return
        else:
            mode = NetMode.TCP_CLIENT
            try:
                tcp_ch = self.tcp_cli_host.text().strip()
                tcp_cp = int(self.tcp_cli_port.text())
            except ValueError:
                self._log_ui("Invalid TCP client")
                return

        if mode == NetMode.TCP_SERVER:
            self.bridge = SerialNetBridge(
                com,
                baud,
                mode,
                tcp_bind_host=tcp_bh,
                tcp_bind_port=tcp_bp,
                loop=self.loop,
                ui_log=self._log_ui,
                stats_cb=self._stats_from_bridge,
                file_log=self._file_log,
            )
        elif mode == NetMode.TCP_CLIENT:
            self.bridge = SerialNetBridge(
                com,
                baud,
                mode,
                tcp_client_host=tcp_ch,
                tcp_client_port=tcp_cp,
                loop=self.loop,
                ui_log=self._log_ui,
                stats_cb=self._stats_from_bridge,
                file_log=self._file_log,
            )
        else:
            self.bridge = SerialNetBridge(
                com,
                baud,
                mode,
                udp_listen=udp_listen,
                udp_remote=udp_remote,
                loop=self.loop,
                ui_log=self._log_ui,
                stats_cb=self._stats_from_bridge,
                file_log=self._file_log,
            )

        self.loop.create_task(self.bridge.start())
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_bridge(self) -> None:
        if self.bridge:
            b = self.bridge
            self.bridge = None

            async def _stop() -> None:
                await b.stop()
                if self._file_log:
                    self._file_log.close()
                    self._file_log = None
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

            self.loop.create_task(_stop())
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _pump_asyncio(self) -> None:
        try:
            self.loop.call_soon(self.loop.stop)
            self.loop.run_forever()
        except Exception as e:
            self._log_ui(f"Asyncio pump error: {e}")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    w = BridgeWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
