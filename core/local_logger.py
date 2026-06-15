"""Non-blocking local raw backup for COM→network ingress (black-box safeguard)."""
from __future__ import annotations

import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# Bounded queue — drops are counted; serial read loop never blocks on file I/O.
# ~8 MiB headroom at max 4096 B serial reads (USV burst / dual-frequency GNSS).
_QUEUE_MAX = 8192
_WRITER_JOIN_S = 8.0
_ERROR_COOLDOWN_S = 15.0


def default_local_backup_dir() -> Path:
    """Directory beside the app / repo for per-session .raw backups."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "logs"
    return Path(__file__).resolve().parent.parent / "logs"


def _open_binary_write(path: Path) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    return os.open(str(path), flags, 0o644)


def _allocate_session_path(base_dir: Path, *, now: datetime | None = None) -> Path:
    dt = now or datetime.now()
    stem = f"backup_{dt.strftime('%Y%m%d_%H%M')}"
    candidate = base_dir / f"{stem}.raw"
    if not candidate.exists():
        return candidate
    for n in range(2, 100):
        alt = base_dir / f"{stem}_{n:02d}.raw"
        if not alt.exists():
            return alt
    return base_dir / f"{stem}_{int(time.time())}.raw"


class LocalSerialBackup:
    """Dedicated writer thread: raw COM chunks, fsync per write, crash-safe."""

    def __init__(
        self,
        base_dir: Path,
        *,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._on_error = on_error
        self._queue: queue.Queue[tuple[bytes, bool] | None] = queue.Queue(maxsize=_QUEUE_MAX)
        self._thread: threading.Thread | None = None
        self._fd: int | None = None
        self._path: Path | None = None
        self._running = False
        self._bytes_written = 0
        self._chunks_dropped = 0
        self._error: str | None = None
        self._last_error_mono = 0.0
        self._lock = threading.Lock()

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def start_session(self) -> Optional[Path]:
        """Open a new timestamped file and start the background writer."""
        with self._lock:
            if self._running:
                return self._path
            try:
                self._base_dir.mkdir(parents=True, exist_ok=True)
                path = _allocate_session_path(self._base_dir)
                fd = _open_binary_write(path)
            except OSError as exc:
                self._set_error(f"Local backup could not open file: {exc}")
                return None
            self._path = path
            self._fd = fd
            self._bytes_written = 0
            self._chunks_dropped = 0
            self._error = None
            self._running = True
            self._thread = threading.Thread(
                target=self._writer_loop,
                name="local-serial-backup",
                daemon=True,
            )
            self._thread.start()
            return path

    def append(self, data: bytes) -> None:
        """Enqueue raw bytes from the serial read loop (must not block)."""
        if not data or not self._running or self._error:
            return
        try:
            self._queue.put_nowait((data, False))
        except queue.Full:
            self._chunks_dropped += 1
            self._report_error_throttled(
                "Local backup queue full — dropping serial chunks (network path unaffected)."
            )

    def close(self) -> dict[str, object]:
        """Flush, fsync, and close the session file."""
        with self._lock:
            if not self._running:
                return self.snapshot()
            self._running = False
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
            thread = self._thread
        if thread is not None:
            thread.join(timeout=_WRITER_JOIN_S)
        with self._lock:
            self._close_fd()
            self._thread = None
        return self.snapshot()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            try:
                qdepth = self._queue.qsize()
            except Exception:
                qdepth = 0
            return {
                "active": self._running and self._fd is not None and not self._error,
                "path": str(self._path) if self._path else "",
                "bytes": self._bytes_written,
                "dropped": self._chunks_dropped,
                "error": self._error or "",
                "queue_depth": qdepth,
                "queue_max": _QUEUE_MAX,
            }

    def _set_error(self, message: str) -> None:
        self._error = message
        self._report_error_throttled(message)

    def _report_error_throttled(self, message: str) -> None:
        now = time.monotonic()
        if now - self._last_error_mono < _ERROR_COOLDOWN_S:
            return
        self._last_error_mono = now
        if self._on_error:
            try:
                self._on_error(message)
            except Exception:
                pass

    def _close_fd(self) -> None:
        fd = self._fd
        self._fd = None
        if fd is None or fd < 0:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    def _writer_loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                if not self._running:
                    break
                continue
            if item is None:
                break
            data, _shutdown = item
            if not data:
                continue
            fd = self._fd
            if fd is None:
                continue
            try:
                os.write(fd, data)
                os.fsync(fd)
                self._bytes_written += len(data)
            except OSError as exc:
                self._set_error(f"Local backup write failed: {exc}")
                self._close_fd()
                break
