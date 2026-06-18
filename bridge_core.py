# bridge_core.py — async bridge engine (no GUI)
from __future__ import annotations

import asyncio
import errno
import logging
import sys
import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, List, Optional, Set

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
from nmea_position import feed_nmea_position
from core.local_logger import LocalSerialBackup, default_local_backup_dir
from survey_quality import (
    feed_nmea_navigation_quality,
    nav_metrics_should_reset,
    nav_quality_stream_idle_snapshot,
    nav_quality_stale,
)

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


def install_bridge_loop_exception_handler(loop: asyncio.AbstractEventLoop) -> None:
    """Suppress noisy WinError 10054 proactor shutdown callbacks (Python 3.14+ on Windows)."""
    if sys.platform != "win32":
        return
    default = loop.get_exception_handler()

    def _handler(
        active_loop: asyncio.AbstractEventLoop, context: dict[str, object]
    ) -> None:
        exc = context.get("exception")
        if isinstance(exc, ConnectionResetError):
            return
        if default is not None:
            default(active_loop, context)
        else:
            active_loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


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


def _lookup_serial_hwid(com: str) -> Optional[str]:
    import serial.tools.list_ports

    target = (com or "").strip().upper()
    if not target:
        return None
    for port in serial.tools.list_ports.comports():
        if (port.device or "").strip().upper() == target:
            hwid = (port.hwid or "").strip()
            return hwid if hwid else None
    return None


def _find_com_by_hwid(hwid: Optional[str]) -> Optional[str]:
    if not hwid:
        return None
    import serial.tools.list_ports

    for port in serial.tools.list_ports.comports():
        if (port.hwid or "").strip() == hwid:
            device = (port.device or "").strip()
            return device if device else None
    return None


def _friendly_serial_error(exc: BaseException, port: str) -> str:
    msg = str(exc).strip()
    if isinstance(exc, asyncio.TimeoutError):
        return f"Serial {port}: timed out (open/write)."
    if isinstance(exc, PermissionError) or (
        isinstance(exc, OSError) and getattr(exc, "winerror", None) in (5, 13)
    ):
        return (
            f"Cannot open {port}: access denied or port in use. "
            "Close PuTTY, another bridge, or any other app using that COM port, then try again."
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


def _retention_duration_label(minutes: int) -> str:
    if minutes < 90:
        return f"{minutes} min"
    if minutes < 36 * 60:
        return f"{minutes // 60} h"
    return f"{minutes // (24 * 60)} d"


def file_log_retention_hint(max_mb: int, backup_count: int) -> str:
    """Rough on-disk span for operator planning (POSPAC / post-processing)."""
    kept = max(0, int(backup_count))
    # Typical survey NMEA ~50–120 B/line; 1–20 Hz → wide range per file.
    busy_min = int((max_mb * 1024 * 1024) / max(20 * 120, 1) / 60)
    quiet_min = int((max_mb * 1024 * 1024) / max(1 * 50, 1) / 60)
    busy_lbl = _retention_duration_label(busy_min)
    quiet_lbl = _retention_duration_label(quiet_min)
    if kept == 0:
        return (
            f"Single file only (~{max_mb} MB cap). When the log reaches {max_mb} MB it is cleared "
            f"and logging continues at the same path (lines already in that file are discarded). "
            f"Often refills in {busy_lbl}–{quiet_lbl} at 1–20 Hz NMEA "
            f"(RTCM or heavy traffic fills sooner)."
        )
    file_count = 1 + kept
    total_mb = max_mb * file_count
    roll_word = "copy" if kept == 1 else "copies"
    return (
        f"When the active log reaches {max_mb} MB it is renamed (e.g. .log.1) and a new file starts. "
        f"You keep {kept} older rotated {roll_word} — {file_count} files total, about {total_mb} MB on disk. "
        f"Each file often lasts {busy_lbl}–{quiet_lbl} at 1–20 Hz NMEA "
        f"(RTCM or heavy traffic fills sooner)."
    )


def _purge_rotated_log_siblings(path: Path) -> None:
    """Remove bridge_survey.log.1, .log.2, … left from a previous retention setting."""
    base = str(path)
    i = 1
    while True:
        sibling = Path(f"{base}.{i}")
        if not sibling.is_file():
            break
        sibling.unlink()
        i += 1


class _SurveyRotatingFileHandler(RotatingFileHandler):
    """Stdlib RotatingFileHandler; backup_count=0 would never roll — we truncate instead."""

    def __init__(self, *args, single_file_only: bool = False, **kwargs):
        self._single_file_only = single_file_only
        if single_file_only:
            kwargs["backupCount"] = 0
        super().__init__(*args, **kwargs)

    def doRollover(self) -> None:
        if self._single_file_only:
            if self.stream:
                self.stream.close()
                self.stream = None
            enc = self.encoding or "utf-8"
            with open(self.baseFilename, "w", encoding=enc):
                pass
            if not self.delay:
                self.stream = self._open()
            return
        super().doRollover()


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
        kept = max(0, int(backup_count))
        single = kept == 0
        if single:
            _purge_rotated_log_siblings(path)
        fh = _SurveyRotatingFileHandler(
            path,
            maxBytes=max(1024 * 1024, int(max_bytes)),
            backupCount=kept if not single else 0,
            encoding="utf-8",
            single_file_only=single,
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


@dataclass
class TcpSinkConfig:
    """Optional TCP mirror of serial→net egress (independent of primary NetMode)."""

    enabled: bool = False
    bind_host: str = "0.0.0.0"
    bind_port: int = 10111
    max_clients: int = 8


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
        udp_fanout: bool = True,
        tcp_sink: Optional[TcpSinkConfig] = None,
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
        enable_local_backup: bool = False,
        local_backup_dir: Optional[Path] = None,
        wire_tap_cb: Optional[Callable[[str, bytes], None]] = None,
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
        self._status_cb = self._wrap_bridge_callback(
            status_cb or (lambda *_a, **_k: None), "status"
        )
        self._stats_cb = self._wrap_bridge_callback(
            stats_cb or (lambda *_a, **_k: None), "stats"
        )
        self._file_log = file_log
        self._enable_local_backup = bool(enable_local_backup)
        self._local_backup_dir = local_backup_dir
        self._local_backup: Optional[LocalSerialBackup] = None
        self._last_backup_session_summary: Optional[dict[str, object]] = None
        self._wire_tap_cb = (
            self._wrap_bridge_callback(wire_tap_cb, "wire_tap")
            if wire_tap_cb is not None
            else None
        )

        self.serial_reader: Optional[asyncio.StreamReader] = None
        self.serial_writer: Optional[asyncio.StreamWriter] = None
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self._tcp_server: Optional[asyncio.Server] = None
        self.tcp_reader: Optional[asyncio.StreamReader] = None
        self.tcp_writer: Optional[asyncio.StreamWriter] = None
        self._tcp_client_task: Optional[asyncio.Task] = None
        self._tcp_reader_task: Optional[asyncio.Task] = None

        self.last_udp_addr = None
        # Fan-out: every UDP sender that contacts us during a session is remembered
        # and receives the serial→net stream.  Cleared on stop/abort.
        self._udp_fanout: bool = bool(udp_fanout)
        self._tcp_sink: Optional[TcpSinkConfig] = tcp_sink if tcp_sink and tcp_sink.enabled else None
        self._tcp_sink_server: Optional[asyncio.Server] = None
        self._tcp_sink_writers: Set[asyncio.StreamWriter] = set()
        self._tcp_sink_drops: int = 0
        self._udp_peers: set[tuple] = set()
        self._gps_state: list[Optional[str]] = [None]
        self._nav_quality_state: list[Optional[dict]] = [None]
        self._position_state: list[Optional[dict]] = [None]
        self._last_nmea_forward_mono: float = 0.0

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
        self._hz_fix_n2s_times: deque[float] = deque()
        self._hz_fix_s2n_times: deque[float] = deque()

        self._asm_n2s = NmeaLineAssembler()
        self._asm_s2n = NmeaLineAssembler()

        self.running = False
        self._teardown = False
        self._tasks: list[asyncio.Task] = []
        self._serial_open = False
        self._serial_hwid: Optional[str] = None
        self._network_ready = False
        self._serial_io_err_last_msg: Optional[str] = None
        self._serial_io_err_last_mono: float = 0.0
        self._last_stats_emit_mono: float = 0.0
        self._pending_stats_emit: Optional[asyncio.Handle] = None
        self._ui_event_log_state: dict[str, tuple[float, int]] = {}
        self._serial_write_lock: Optional[asyncio.Lock] = None

    def _wrap_bridge_callback(
        self, cb: Callable[..., None], label: str
    ) -> Callable[..., None]:
        """Keep Qt/UI callback failures from aborting ingest or asyncio startup."""

        def _wrapped(*args: object, **kwargs: object) -> None:
            try:
                cb(*args, **kwargs)
            except Exception as exc:
                logging.getLogger("survey_bridge").exception(
                    "%s callback failed", label
                )
                self._ui_log_event_limited(
                    f"cb_{label}",
                    f"[{label}] UI callback error: {exc!r}",
                )

        return _wrapped

    def _set_status(self, serial_line: str, network_line: str) -> None:
        self._last_network_status = network_line
        self._status_cb(serial_line, network_line)

    def _gps_utc(self) -> str:
        return self._gps_state[0] or ""

    def navigation_quality(self) -> Optional[dict]:
        """Latest GGA-based survey quality snapshot, or None if no GGA seen."""
        if self._nav_metrics_inactive():
            return nav_quality_stream_idle_snapshot() if self.running else None
        return self._nav_quality_state[0]

    def navigation_position(self) -> Optional[dict]:
        """Latest WGS84 fix from GGA/RMC (reserved for Survey HUD map integration)."""
        if self.nmea_mode == NmeaMode.RAW or not self.running:
            return None
        if self._nav_metrics_inactive():
            return None
        pos = self._position_state[0]
        if not pos:
            return None
        stale = nav_quality_stale(self._nav_quality_state[0])
        return {
            "lat": float(pos["lat"]),
            "lon": float(pos["lon"]),
            "source": str(pos.get("source") or ""),
            "stale": stale,
        }

    def navigation_position_stats(self) -> dict:
        """Web `/status` and stats coalescing — position_* keys (HUD may use navigation_position())."""
        if self.nmea_mode == NmeaMode.RAW:
            return {}
        if not self.running:
            return {}
        if self._nav_metrics_inactive():
            return {"position_stale": True}
        pos = self._position_state[0]
        if not pos:
            return {"position_stale": True}
        stale = nav_quality_stale(self._nav_quality_state[0])
        return {
            "position_lat": float(pos["lat"]),
            "position_lon": float(pos["lon"]),
            "position_source": str(pos.get("source") or ""),
            "position_stale": stale,
        }

    def navigation_quality_stats(self) -> dict:
        """Stats-bar / HUD fields from latest GGA (excludes internal monotonic timestamp)."""
        if self._nav_metrics_inactive():
            return nav_quality_stream_idle_snapshot() if self.running else {}
        nav = self._nav_quality_state[0]
        if not nav:
            return {}
        out = {k: v for k, v in nav.items() if k != "mono"}
        out["nav_stale"] = False
        return out

    def _nmea_traffic_hz(self) -> float:
        """Max rolling 1 s Hz on any parsed NMEA path (UDP/TCP, inject, COM)."""
        return max(
            self.hz_remote_to_serial(),
            self.hz_gui_to_serial(),
            self.hz_serial_to_net(),
        )

    def _nav_metrics_inactive(self) -> bool:
        last_mono = self._last_nmea_forward_mono or None
        if last_mono is not None and last_mono <= 0.0:
            last_mono = None
        return nav_metrics_should_reset(
            traffic_hz=self._nmea_traffic_hz(),
            nav=self._nav_quality_state[0],
            last_nmea_mono=last_mono,
            running=self.running,
        )

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
        self._tap_local_backup(chunk)
        if self._serial_write_lock is None:
            self._serial_write_lock = asyncio.Lock()
        async with self._serial_write_lock:
            await self._write_serial_bytes_locked(chunk)

    async def _write_serial_bytes_locked(self, chunk: bytes) -> None:
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
        """Rolling ~1 s rate of sentences received net→COM (before strict drops)."""
        return rolling_hz_last_second(self._hz_remote_times)

    def hz_serial_to_net(self) -> float:
        """Rolling ~1 s rate of sentences received COM→net (before strict drops)."""
        return rolling_hz_last_second(self._hz_serial_times)

    def hz_fix_to_serial(self) -> float:
        """Rolling ~1 s rate of GGA fixes received net→COM (survey GNSS Hz)."""
        return rolling_hz_last_second(self._hz_fix_n2s_times)

    def hz_fix_from_serial(self) -> float:
        """Rolling ~1 s rate of GGA fixes received COM→net."""
        return rolling_hz_last_second(self._hz_fix_s2n_times)

    def hz_gui_to_serial(self) -> float:
        """Rolling ~1 s rate of inject sentences received toward COM."""
        return rolling_hz_last_second(self._hz_gui_times)

    @property
    def udp_peer_count(self) -> int:
        """Number of distinct UDP peers registered for fan-out this session."""
        return len(self._udp_peers)

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
                "hz_fix_down": self.hz_fix_to_serial(),
                "hz_gui": self.hz_gui_to_serial(),
                "hz_up": self.hz_serial_to_net(),
                "hz_fix_up": self.hz_fix_from_serial(),
                "lines_down": self.lines_remote_to_serial,
                "lines_up": self.lines_serial_to_net,
                "udp_peers": self.udp_peer_count,
                "running": self.running,
                "udp_listen_host": self.udp_listen[0] if self.udp_listen else "",
                "udp_listen_port": self.udp_listen[1] if self.udp_listen else 0,
                "tcp_sink_clients": len(self._tcp_sink_writers),
                "tcp_sink_drops": self._tcp_sink_drops,
                "tcp_sink_enabled": bool(self._tcp_sink),
                **self.navigation_quality_stats(),
                **self.navigation_position_stats(),
                **self._local_backup_stats(),
            }
        )

    def _local_backup_stats(self) -> dict[str, object]:
        backup = self._local_backup
        if backup is None:
            return {
                "local_backup_active": False,
                "local_backup_path": "",
                "local_backup_bytes": 0,
                "local_backup_dropped": 0,
                "local_backup_error": "",
                "local_backup_queue_depth": 0,
                "local_backup_queue_max": 0,
            }
        snap = backup.snapshot()
        return {
            "local_backup_active": bool(snap.get("active")),
            "local_backup_path": str(snap.get("path") or ""),
            "local_backup_bytes": int(snap.get("bytes") or 0),
            "local_backup_dropped": int(snap.get("dropped") or 0),
            "local_backup_error": str(snap.get("error") or ""),
            "local_backup_queue_depth": int(snap.get("queue_depth") or 0),
            "local_backup_queue_max": int(snap.get("queue_max") or 0),
        }

    def _notify_backup_health_change(self) -> None:
        """Thread-safe stats refresh when the backup writer errors or saturates."""
        loop = self.loop
        if loop.is_running():
            loop.call_soon_threadsafe(self._schedule_stats_emit)

    def _tap_local_backup(self, data: bytes) -> None:
        """Record raw COM traffic (reads and writes) before decode/queue (non-blocking)."""
        backup = self._local_backup
        if backup is None or not data:
            return
        try:
            backup.append(data)
        except Exception:
            pass

    def _start_local_backup(self) -> None:
        if not self._enable_local_backup:
            return
        base = self._local_backup_dir or default_local_backup_dir()
        backup = LocalSerialBackup(
            base,
            on_error=lambda msg: (
                self._ui_log_event_limited("local_backup", msg),
                self._notify_backup_health_change(),
            ),
        )
        path = backup.start_session()
        if path is None:
            self._local_backup = None
            self._ui_log("Local black-box backup disabled — could not open backup file.")
            self._notify_backup_health_change()
            return
        self._local_backup = backup
        self._ui_log(f"Local black-box backup: {path}")

    def _stop_local_backup(self) -> None:
        backup = self._local_backup
        if backup is None:
            return
        try:
            snap = backup.close()
            self._last_backup_session_summary = dict(snap)
            path = snap.get("path") or ""
            nbytes = int(snap.get("bytes") or 0)
            dropped = int(snap.get("dropped") or 0)
            if path:
                extra = f" ({dropped} chunks dropped)" if dropped else ""
                self._ui_log(f"Local backup closed — {nbytes} bytes → {path}{extra}")
        except Exception:
            self._last_backup_session_summary = None
        self._local_backup = None

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

    def _note_ingress_hz(self, times: deque[float], now: float, count: int) -> None:
        """Append one rolling-Hz tick per complete sentence seen on the wire."""
        if count <= 0:
            return
        for _ in range(count):
            times.append(now)

    def _ingest_net(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        now = time.monotonic()
        if self.nmea_mode == NmeaMode.RAW:
            if direction.startswith(("UDP", "TCP")):
                self._hz_remote_times.append(now)
            elif direction.startswith(("GUI", "INJECT")):
                self._hz_gui_times.append(now)
            if direction.startswith(("UDP", "TCP")):
                self.lines_remote_to_serial += 1
            elif direction.startswith(("GUI", "INJECT")):
                self.lines_gui_to_serial += 1
            self._enqueue_net_to_serial(data, direction)
            if self._wire_tap_cb is not None:
                self._wire_tap_cb("net→com", data)
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_n2s.feed(data, self.nmea_mode, filt)
        if result.forward:
            self._last_nmea_forward_mono = now
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        feed_nmea_navigation_quality(result.forward, self._nav_quality_state)
        feed_nmea_position(result.forward, self._position_state)
        for reason in result.rejected:
            self.rejected_net_to_serial += 1
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "reject_n2s",
                f"{direction} [REJECT] {reason}",
            )
            if self._wire_tap_cb is not None:
                self._wire_tap_cb("reject", reason.encode("utf-8", errors="replace"))
        if direction.startswith(("UDP", "TCP")):
            self._note_ingress_hz(self._hz_remote_times, now, result.ingress_lines)
            self._note_ingress_hz(self._hz_fix_n2s_times, now, result.ingress_fix_lines)
        elif direction.startswith(("GUI", "INJECT")):
            self._note_ingress_hz(self._hz_gui_times, now, result.ingress_lines)
        for line in result.forward:
            if direction.startswith(("UDP", "TCP")):
                self.lines_remote_to_serial += 1
            elif direction.startswith(("GUI", "INJECT")):
                self.lines_gui_to_serial += 1
            self._enqueue_net_to_serial(line, direction)
            if self._wire_tap_cb is not None:
                raw = line if isinstance(line, bytes) else line.encode("utf-8", errors="replace")
                self._wire_tap_cb("net→com", raw)

    def _ingest_serial(self, data: bytes, direction: str) -> None:
        if not self.running:
            return
        now = time.monotonic()
        if self.nmea_mode == NmeaMode.RAW:
            if direction.startswith("SER"):
                self.lines_serial_to_net += 1
                self._hz_serial_times.append(now)
            self._enqueue_serial_to_net(data, direction)
            if self._wire_tap_cb is not None:
                self._wire_tap_cb("com→net", data)
            return
        filt = self.nmea_filter if self.nmea_mode == NmeaMode.STRICT else None
        result = self._asm_s2n.feed(data, self.nmea_mode, filt)
        if result.forward:
            self._last_nmea_forward_mono = time.monotonic()
        feed_nmea_times_from_lines(result.forward, self._gps_state)
        feed_nmea_navigation_quality(result.forward, self._nav_quality_state)
        feed_nmea_position(result.forward, self._position_state)
        for reason in result.rejected:
            self.rejected_serial_to_net += 1
            self._schedule_stats_emit()
            self._ui_log_event_limited(
                "reject_s2n",
                f"{direction} [REJECT] {reason}",
            )
            if self._wire_tap_cb is not None:
                self._wire_tap_cb("reject", reason.encode("utf-8", errors="replace"))
        if direction.startswith("SER"):
            self._note_ingress_hz(self._hz_serial_times, now, result.ingress_lines)
            self._note_ingress_hz(self._hz_fix_s2n_times, now, result.ingress_fix_lines)
        for line in result.forward:
            if direction.startswith("SER"):
                self.lines_serial_to_net += 1
            self._enqueue_serial_to_net(line, direction)
            if self._wire_tap_cb is not None:
                raw = line if isinstance(line, bytes) else line.encode("utf-8", errors="replace")
                self._wire_tap_cb("com→net", raw)

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
        try:
            is_new_peer = addr not in self._udp_peers
            self._udp_peers.add(addr)
            self.last_udp_addr = addr
            if is_new_peer and self.mode == NetMode.UDP_LISTEN and self.udp_listen:
                host, port = self.udp_listen
                n = len(self._udp_peers)
                peer_label = f"{n} peers" if n > 1 else f"peer {addr}"
                self._set_status(
                    f"Serial: {self.com} @ {self.baud} — open",
                    f"Network: UDP listen {host}:{port} — {peer_label}",
                )
            self._ingest_net(data, f"UDP←{addr}")
        except Exception as exc:
            logging.getLogger("survey_bridge").exception("UDP datagram handler failed")
            self._ui_log_event_limited(
                "udp_handler",
                f"UDP←{addr} handler error: {exc!r}",
            )

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
        self._serial_hwid = _lookup_serial_hwid(self.com)
        self.running = True
        self._start_local_backup()
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

        if self._tcp_sink:
            try:
                self._tcp_sink_server = await asyncio.start_server(
                    self._on_tcp_sink_client,
                    host=self._tcp_sink.bind_host,
                    port=self._tcp_sink.bind_port,
                )
                self._tasks.append(
                    asyncio.create_task(self._serve_tcp_sink_forever(), name="tcp_sink_serve")
                )
                self._ui_log(
                    f"TCP sink mirror on {self._tcp_sink.bind_host}:{self._tcp_sink.bind_port}"
                )
            except Exception as e:
                self._ui_log(
                    f"TCP sink disabled: {_friendly_network_error(e, 'TCP sink')}"
                )
                self._tcp_sink = None

        return True

    async def _serve_tcp_sink_forever(self) -> None:
        assert self._tcp_sink_server is not None
        async with self._tcp_sink_server:
            await self._tcp_sink_server.serve_forever()

    async def _on_tcp_sink_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        cfg = self._tcp_sink
        if cfg is None:
            try:
                writer.close()
            except Exception:
                pass
            return
        if len(self._tcp_sink_writers) >= cfg.max_clients:
            try:
                writer.close()
            except Exception:
                pass
            return
        self._tcp_sink_writers.add(writer)
        self._schedule_stats_emit()
        try:
            await reader.read()
        except Exception:
            pass
        finally:
            self._tcp_sink_writers.discard(writer)
            self._schedule_stats_emit()

    async def _mirror_to_tcp_sink(self, data: bytes) -> None:
        if not self._tcp_sink_writers:
            return
        dead: list[asyncio.StreamWriter] = []
        for writer in list(self._tcp_sink_writers):
            try:
                writer.write(data)
                await writer.drain()
            except Exception:
                dead.append(writer)
        for writer in dead:
            self._tcp_sink_writers.discard(writer)
            self._tcp_sink_drops += 1
        if dead:
            self._schedule_stats_emit()

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

    def _reset_serial_decode_state(self) -> None:
        """Drop partial line assembly after COM glitches so reconnect cannot splice bytes."""
        self._asm_n2s.reset()
        self._asm_s2n.reset()
        self._serial_io_err_last_msg = None
        self._serial_io_err_last_mono = 0.0

    async def _close_serial_streams(self) -> None:
        writer = self.serial_writer
        self.serial_writer = None
        self.serial_reader = None
        self._serial_open = False
        if writer is not None:
            await self._await_closed(writer, "Serial")

    def _try_remap_com_by_hwid(self) -> bool:
        """Follow adapter when Windows reassigns COM after USB replug."""
        if not self._serial_hwid:
            self._serial_hwid = _lookup_serial_hwid(self.com)
        if not self._serial_hwid:
            return False
        new_com = _find_com_by_hwid(self._serial_hwid)
        if not new_com or new_com.upper() == self.com.upper():
            return False
        old = self.com
        self.com = new_com
        self._ui_log(f"Serial adapter re-enumerated: {old} → {new_com}")
        return True

    def _maybe_remap_com_after_reenum(self, err_text: str) -> bool:
        """USB unplug/replug may change COM number while hwid stays stable."""
        low = (err_text or "").lower()
        if not any(
            token in low
            for token in (
                "not found",
                "no such file",
                "does not exist",
                "cannot find",
                "file not found",
            )
        ):
            return False
        return self._try_remap_com_by_hwid()

    async def _try_reopen_serial(self) -> bool:
        for attempt in range(3):
            try:
                self.serial_reader, self.serial_writer = await self._open_serial_stream()
            except asyncio.TimeoutError:
                if attempt < 2 and self._try_remap_com_by_hwid():
                    continue
                self._ui_log_serial_coalesced(
                    f"Serial reconnect timed out opening {self.com} ({SERIAL_OPEN_TIMEOUT_S:.0f}s)"
                )
                return False
            except Exception as e:
                err = _friendly_serial_error(e, self.com)
                if attempt < 2 and (
                    self._maybe_remap_com_after_reenum(err) or self._try_remap_com_by_hwid()
                ):
                    continue
                self._ui_log_serial_coalesced(err)
                return False
            self._serial_open = True
            if not self._serial_hwid:
                self._serial_hwid = _lookup_serial_hwid(self.com)
            self._reset_serial_decode_state()
            self._set_status(
                f"Serial: {self.com} @ {self.baud} — open (reconnected)",
                self._last_network_status,
            )
            self._ui_log(f"Serial reconnected on {self.com} @ {self.baud}")
            return True
        return False

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
                    err = _friendly_serial_error(e, self.com)
                    if self._maybe_remap_com_after_reenum(err):
                        disconnected = True
                        break
                    self._ui_log_serial_coalesced(err)
                disconnected = True
                break
            if not data:
                if self.running and not self._teardown:
                    disconnected = True
                break
            self._tap_local_backup(data)
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
                        self._try_remap_com_by_hwid()
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
                self._reset_serial_decode_state()
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
                        err = _friendly_serial_error(e, self.com)
                        self._maybe_remap_com_after_reenum(err)
                        self._ui_log_serial_coalesced(err)
                        await self._close_serial_streams()
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
            if self.mode == NetMode.UDP_LISTEN:
                if self._udp_fanout:
                    # Fan-out: send to every peer that has contacted us this session.
                    dead: list[tuple] = []
                    for peer in list(self._udp_peers):
                        try:
                            self.udp_transport.sendto(data, peer)
                        except Exception as e:
                            self._ui_log(_friendly_network_error(e, f"UDP send→{peer}"))
                            dead.append(peer)
                    for peer in dead:
                        self._udp_peers.discard(peer)
                        if self.last_udp_addr == peer:
                            self.last_udp_addr = next(iter(self._udp_peers), None)
                elif self.last_udp_addr:
                    # Single-link: reply only to the most recent sender.
                    try:
                        self.udp_transport.sendto(data, self.last_udp_addr)
                    except Exception as e:
                        self._ui_log(_friendly_network_error(e, f"UDP send→{self.last_udp_addr}"))
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
        if self._tcp_sink:
            await self._mirror_to_tcp_sink(data)

    def abort_now(self) -> None:
        """Synchronous teardown — must not block the Qt thread (no wait_closed on serial)."""
        self._teardown = True
        self.running = False
        self._udp_peers.clear()
        self.last_udp_addr = None

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

        if self._tcp_sink_server:
            try:
                self._tcp_sink_server.close()
            except Exception:
                pass
            self._tcp_sink_server = None
        for w in list(self._tcp_sink_writers):
            try:
                w.close()
            except Exception:
                pass
        self._tcp_sink_writers.clear()

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
        self._reset_serial_decode_state()
        self._stop_local_backup()

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
        self._reset_serial_decode_state()
        self._nav_quality_state[0] = None
        self._position_state[0] = None

        self._stop_local_backup()
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
        install_bridge_loop_exception_handler(loop)
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
            tb = traceback.format_exc()
            self.log_msg.emit(f"Bridge thread: {exc!r}\n{tb}")
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


