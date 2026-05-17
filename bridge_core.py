# bridge_core.py — async bridge engine (no GUI)
from __future__ import annotations

import asyncio
import errno
import logging
import sys
import threading
import time
from collections import deque
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, List, Optional

import serial
import serial_asyncio
from serial_asyncio import connection_for_serial
from PySide6 import QtCore

from log_serial_coalesce import serial_timeout_line_suppress, ui_safe_text

from nmea_codec import (
    NMEA_SENTENCE_TYPES,
    NmeaFilter,
    NmeaLineAssembler,
    NmeaMode,
    feed_nmea_times_from_lines,
    format_binary_log_preview,
    parse_nmea_utc,
)
from survey_quality import feed_nmea_navigation_quality, nav_quality_stale

NET_TO_SERIAL_QUEUE_MAX = 512
SERIAL_TO_NET_QUEUE_MAX = 512
UI_LOG_PENDING_MAX = 2000
UI_LOG_FLUSH_MS = 50
UI_LOG_MAX_LINES_PER_FLUSH = 96
UI_VIEW_MAX_BLOCK_COUNT = 4000

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
STATS_EMIT_MIN_INTERVAL_S = 0.20
UI_EVENT_LOG_MIN_INTERVAL_S = 0.40
# com0com / driver often splits one COM write into several read() calls; coalesce for HUD wire Hz.
SERIAL_WIRE_HZ_COALESCE_S = 0.12
SERIAL_RECONNECT_INTERVAL_S = 2.0


def rolling_hz_last_second(times: deque[float], window_s: float = 1.0) -> float:
    """How many timestamps fall within the last ``window_s`` seconds (monotonic clock)."""
    now = time.monotonic()
    cutoff = now - window_s
    while times and times[0] < cutoff:
        times.popleft()
    return float(len(times))


def configure_windows_event_loop_policy() -> None:
    """Selector policy is deprecated on Python 3.14+; bridge uses a dedicated asyncio thread."""
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


def file_log_retention_hint(max_mb: int, backup_count: int) -> str:
    """Rough on-disk span for operator planning (POSPAC / post-processing)."""
    total_mb = max_mb * (1 + max(0, backup_count))
    # Typical survey NMEA ~50–120 B/line; 1–20 Hz → wide range.
    low_min = int((max_mb * 1024 * 1024) / max(20 * 120, 1) / 60)
    high_min = int((max_mb * 1024 * 1024) / max(1 * 50, 1) / 60)
    return (
        f"~{max_mb} MB per file × {1 + backup_count} files ≈ {total_mb} MB on disk. "
        f"One file often lasts ~{low_min}–{high_min} min at 1–20 Hz NMEA "
        f"(RTCM/corrections or high-rate traffic fill much faster)."
    )


class _FileSurveyLog:
    """Rotating file: PC time | last GPS UTC | direction | payload."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = FILE_LOG_MAX_BYTES,
        backup_count: int = FILE_LOG_BACKUP_COUNT,
    ):
        self.path = path
        self._logger = logging.getLogger(f"survey_bridge.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            path,
            maxBytes=max(1024 * 1024, int(max_bytes)),
            backupCount=max(0, int(backup_count)),
            encoding="utf-8",
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
        serial_auto_reconnect: bool = True,
        ui_log_verbose: Optional[Callable[[], bool]] = None,
        ui_log_hex: Optional[Callable[[], bool]] = None,
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
        self.serial_auto_reconnect = bool(serial_auto_reconnect)
        self._ui_log_verbose = ui_log_verbose or (lambda: False)
        self._ui_log_hex = ui_log_hex or (lambda: False)
        self._last_network_status = "Network: starting…"

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
        self._nav_quality_state: list[Optional[dict]] = [None]

        self.net_to_serial: asyncio.Queue[bytes] = asyncio.Queue(maxsize=NET_TO_SERIAL_QUEUE_MAX)
        self.serial_to_net: asyncio.Queue[bytes] = asyncio.Queue(maxsize=SERIAL_TO_NET_QUEUE_MAX)

        self.drops_net_to_serial = 0
        self.drops_serial_to_net = 0
        self.rejected_net_to_serial = 0
        self.rejected_serial_to_net = 0

        # QA: complete NMEA sentences (after assembly), not raw UDP datagrams.
        self.lines_remote_to_serial = 0  # UDP/TCP ingress only (excludes GUI inject)
        self.lines_gui_to_serial = 0  # Send tab / explicit inject → COM
        self.lines_serial_to_net = 0  # COM → network path
        self._hz_remote_times: deque[float] = deque()
        self._hz_gui_times: deque[float] = deque()
        self._hz_serial_times: deque[float] = deque()

        self._asm_n2s = NmeaLineAssembler()
        self._asm_s2n = NmeaLineAssembler()

        self.running = False
        self._teardown = False
        self._tasks: list[asyncio.Task] = []
        self._serial_open = False
        self._network_ready = False
        self._serial_io_err_last_msg: Optional[str] = None
        self._serial_io_err_last_mono: float = 0.0
        self._last_stats_emit_mono: float = 0.0
        self._pending_stats_emit: Optional[asyncio.Handle] = None
        self._ui_event_log_state: dict[str, tuple[float, int]] = {}

    def _set_status(self, serial_line: str, network_line: str) -> None:
        self._last_network_status = network_line
        self._status_cb(serial_line, network_line)

    def _gps_utc(self) -> str:
        return self._gps_state[0] or ""

    def navigation_quality(self) -> Optional[dict]:
        """Latest GGA-based survey quality snapshot, or None if no GGA seen."""
        return self._nav_quality_state[0]

    def navigation_quality_stats(self) -> dict:
        """Stats-bar / HUD fields from latest GGA (excludes internal monotonic timestamp)."""
        nav = self._nav_quality_state[0]
        if not nav:
            return {}
        out = {k: v for k, v in nav.items() if k != "mono"}
        out["nav_stale"] = nav_quality_stale(nav)
        return out

    def _ui_log_serial_coalesced(self, msg: str, window_s: float = 2.5) -> None:
        """Throttle identical serial-path errors (burst traffic or shutdown overlap)."""
        if not msg:
            return
        suppress, self._serial_io_err_last_msg, self._serial_io_err_last_mono = (
            serial_timeout_line_suppress(
                self._serial_io_err_last_msg,
                self._serial_io_err_last_mono,
                msg,
                window_s=window_s,
            )
        )
        if not suppress:
            self._ui_log(msg)

    def _underlying_serial(self) -> Optional[serial.Serial]:
        writer = self.serial_writer
        if not writer:
            return None
        ser = getattr(writer.transport, "serial", None)
        return ser if isinstance(ser, serial.Serial) else None

    async def inject_correction_bytes(self, chunk: bytes) -> None:
        """Inject RTCM/correction bytes onto COM (e.g. NTRIP) without counting as NMEA ingress."""
        if not chunk:
            return
        await self._write_serial_bytes(chunk)

    async def _write_serial_bytes(self, chunk: bytes) -> None:
        """Write to COM. On Windows, bypass pyserial-asyncio poll writer (can stall under Qt)."""
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

    def hz_remote_to_serial(self) -> float:
        """Rolling ~1 s rate of network receive chunks (UDP datagram / TCP read), not NMEA lines."""
        return rolling_hz_last_second(self._hz_remote_times)

    def hz_serial_to_net(self) -> float:
        """Rolling ~1 s rate of serial read chunks toward network, not NMEA lines."""
        return rolling_hz_last_second(self._hz_serial_times)

    def hz_gui_to_serial(self) -> float:
        """Rolling ~1 s rate of GUI inject batches toward COM, not lines per batch."""
        return rolling_hz_last_second(self._hz_gui_times)

    def _note_serial_wire_hz(self, now: float) -> None:
        """One wire-Hz tick per serial read burst (avoids com0com echo inflating From COM)."""
        if (
            self._hz_serial_times
            and (now - self._hz_serial_times[-1]) < SERIAL_WIRE_HZ_COALESCE_S
        ):
            return
        self._hz_serial_times.append(now)

    def _emit_stats(self) -> None:
        self._last_stats_emit_mono = time.monotonic()
        self._stats_cb(
            {
                "drops_n2s": self.drops_net_to_serial,
                "drops_s2n": self.drops_serial_to_net,
                "rej_n2s": self.rejected_net_to_serial,
                "rej_s2n": self.rejected_serial_to_net,
                "n2s_q": self.net_to_serial.qsize(),
                "s2n_q": self.serial_to_net.qsize(),
                "hz_down": self.hz_remote_to_serial(),
                "hz_gui": self.hz_gui_to_serial(),
                "hz_up": self.hz_serial_to_net(),
                "lines_down": self.lines_remote_to_serial,
                "lines_up": self.lines_serial_to_net,
                **self.navigation_quality_stats(),
            }
        )

    def _schedule_stats_emit(self) -> None:
        """Coalesce hot-path stats updates to avoid flooding Qt queued signals."""
        now = time.monotonic()
        due_in = STATS_EMIT_MIN_INTERVAL_S - (now - self._last_stats_emit_mono)
        if due_in <= 0:
            self._emit_stats()
            return
        if self._pending_stats_emit is not None and not self._pending_stats_emit.cancelled():
            return

        def _fire() -> None:
            self._pending_stats_emit = None
            self._emit_stats()

        self._pending_stats_emit = self.loop.call_later(due_in, _fire)

    def _ui_log_event_limited(self, key: str, msg: str, *, window_s: float = UI_EVENT_LOG_MIN_INTERVAL_S) -> None:
        """Rate-limit repeated high-volume events and include suppression count."""
        now = time.monotonic()
        last_mono, suppressed = self._ui_event_log_state.get(key, (0.0, 0))
        if now - last_mono < window_s:
            self._ui_event_log_state[key] = (last_mono, suppressed + 1)
            return
        if suppressed:
            msg = f"{msg} (+{suppressed} similar suppressed)"
        self._ui_event_log_state[key] = (now, 0)
        self._ui_log(msg)

    def _log(self, direction: str, data: bytes, *, to_ui: bool = True, always: bool = False) -> None:
        if self.nmea_mode == NmeaMode.RAW:
            preview = format_binary_log_preview(data)
        else:
            preview = ui_safe_text(
                data.decode(errors="replace").rstrip().replace("\r", "\\r")
            )
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
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "drop_n2s",
                (
                    f"{direction} [DROP n→s] queue full "
                    f"(drops={self.drops_net_to_serial}, q={self.net_to_serial.qsize()})"
                ),
            )
        else:
            self._log(direction, data)

    def _enqueue_serial_to_net(self, data: bytes, direction: str) -> None:
        try:
            self.serial_to_net.put_nowait(data)
        except asyncio.QueueFull:
            self.drops_serial_to_net += 1
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "drop_s2n",
                (
                    f"{direction} [DROP s→n] queue full "
                    f"(drops={self.drops_serial_to_net}, q={self.serial_to_net.qsize()})"
                ),
            )
        else:
            self._log(direction, data)

    def _ingest_net(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        now = time.monotonic()
        if direction.startswith(("UDP", "TCP")):
            self._hz_remote_times.append(now)
        elif direction.startswith(("GUI", "INJECT")):
            self._hz_gui_times.append(now)
        if self.nmea_mode == NmeaMode.RAW:
            if direction.startswith(("UDP", "TCP")):
                self.lines_remote_to_serial += 1
            elif direction.startswith(("GUI", "INJECT")):
                self.lines_gui_to_serial += 1
            self._enqueue_net_to_serial(data, direction)
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_n2s.feed(data, self.nmea_mode, filt)
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        feed_nmea_navigation_quality(result.forward, self._nav_quality_state)
        for reason in result.rejected:
            self.rejected_net_to_serial += 1
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "reject_n2s",
                f"{direction} [REJECT] {reason}",
            )
        for line in result.forward:
            if direction.startswith(("UDP", "TCP")):
                self.lines_remote_to_serial += 1
            elif direction.startswith(("GUI", "INJECT")):
                self.lines_gui_to_serial += 1
            self._enqueue_net_to_serial(line, direction)

    def _ingest_serial(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        if direction.startswith("SER"):
            self._note_serial_wire_hz(time.monotonic())
        if self.nmea_mode == NmeaMode.RAW:
            if direction.startswith("SER"):
                self.lines_serial_to_net += 1
            self._enqueue_serial_to_net(data, direction)
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_s2n.feed(data, self.nmea_mode, filt)
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        feed_nmea_navigation_quality(result.forward, self._nav_quality_state)
        for reason in result.rejected:
            self.rejected_serial_to_net += 1
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "reject_s2n",
                f"{direction} [REJECT] {reason}",
            )
        for line in result.forward:
            if direction.startswith("SER"):
                self.lines_serial_to_net += 1
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
        self._teardown = False
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
        self._tasks.append(asyncio.create_task(self._serial_lifecycle_loop(), name="serial_lifecycle"))

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

    async def _close_serial_streams(self) -> None:
        writer = self.serial_writer
        self.serial_writer = None
        self.serial_reader = None
        self._serial_open = False
        if writer is not None:
            await self._await_closed(writer, "Serial")

    async def _try_reopen_serial(self) -> bool:
        try:
            self.serial_reader, self.serial_writer = await self._open_serial_stream()
        except asyncio.TimeoutError:
            self._ui_log_serial_coalesced(
                f"Serial reconnect timed out opening {self.com} ({SERIAL_OPEN_TIMEOUT_S:.0f}s)"
            )
            return False
        except Exception as e:
            self._ui_log_serial_coalesced(_friendly_serial_error(e, self.com))
            return False
        self._serial_open = True
        self._set_status(
            f"Serial: {self.com} @ {self.baud} — open (reconnected)",
            self._last_network_status,
        )
        self._ui_log(f"Serial reconnected on {self.com} @ {self.baud}")
        return True

    async def _serial_read_until_disconnect(self) -> bool:
        """Read until error/EOF. Returns True if the session ended unexpectedly (retry)."""
        assert self.serial_reader is not None
        disconnected = False
        while self.running:
            try:
                data = await asyncio.wait_for(self.serial_reader.read(4096), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if self.running and not self._teardown:
                    self._ui_log_serial_coalesced(_friendly_serial_error(e, self.com))
                disconnected = True
                break
            if not data:
                if self.running and not self._teardown:
                    disconnected = True
                break
            self._ingest_serial(data, "SER→NET")
        return disconnected

    async def _serial_lifecycle_loop(self) -> None:
        """Keep COM open while running; reopen after USB/COM glitches if enabled."""
        try:
            while self.running:
                if not self._serial_open or self.serial_reader is None:
                    if not await self._try_reopen_serial():
                        if not self.serial_auto_reconnect:
                            break
                        self._set_status(
                            f"Serial: {self.com} — reconnecting every "
                            f"{SERIAL_RECONNECT_INTERVAL_S:.0f}s…",
                            self._last_network_status,
                        )
                        await asyncio.sleep(SERIAL_RECONNECT_INTERVAL_S)
                        continue
                try:
                    need_retry = await self._serial_read_until_disconnect()
                except asyncio.CancelledError:
                    raise
                if not self.running:
                    break
                await self._close_serial_streams()
                if not need_retry or not self.serial_auto_reconnect:
                    break
                self._ui_log(
                    f"Serial session ended on {self.com} — retry in "
                    f"{SERIAL_RECONNECT_INTERVAL_S:.0f}s"
                )
                self._set_status(
                    f"Serial: disconnected — retry in {SERIAL_RECONNECT_INTERVAL_S:.0f}s…",
                    self._last_network_status,
                )
                await asyncio.sleep(SERIAL_RECONNECT_INTERVAL_S)
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
                except asyncio.TimeoutError:
                    if self.running and not self._teardown:
                        self._ui_log_serial_coalesced(
                            _friendly_serial_error(asyncio.TimeoutError(), self.com)
                        )
                except Exception as e:
                    if self.running and not self._teardown:
                        self._ui_log_serial_coalesced(_friendly_serial_error(e, self.com))
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
    """Run SerialNetBridge on a plain asyncio loop (same as bridge_headless)."""

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


