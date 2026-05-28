"""Background uvicorn thread for Web control plane."""
from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Any, Optional

_LOG = logging.getLogger(__name__)


def _probe_host(lan_bind: bool, host: str) -> str:
    # LAN bind listens on all interfaces; loopback probe is enough on Windows.
    return "127.0.0.1"


def port_is_in_use(port: int, *, lan_bind: bool, host: str = "127.0.0.1") -> bool:
    """Return True if something is already accepting TCP on this port (local probe)."""
    probe = _probe_host(lan_bind, host)
    try:
        with socket.create_connection((probe, int(port)), timeout=0.2):
            return True
    except OSError:
        return False


def port_is_free(port: int, *, lan_bind: bool, host: str = "127.0.0.1") -> bool:
    """Return True if the Web API port is not accepting connections yet."""
    return not port_is_in_use(port, lan_bind=lan_bind, host=host)


def wait_port_free(
    port: int,
    *,
    lan_bind: bool,
    host: str = "127.0.0.1",
    timeout: float = 3.0,
) -> bool:
    """Wait until the Web API bind address is available (after stop/restart)."""
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        if port_is_free(port, lan_bind=lan_bind, host=host):
            return True
        time.sleep(0.08)
    return port_is_free(port, lan_bind=lan_bind, host=host)


class WebServerThread:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._server: Any = None
        self._host = "127.0.0.1"
        self._port = 8765
        self._start_error: Optional[str] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        app: Any,
        *,
        host: str,
        port: int,
        lan_bind: bool,
        listen_timeout: float = 5.0,
    ) -> None:
        if self.running:
            self.stop(join_timeout=3.0)
        if lan_bind and host in ("127.0.0.1", "localhost"):
            bind_host = "0.0.0.0"
        else:
            bind_host = host or "127.0.0.1"
        self._host = bind_host
        self._port = int(port)
        self._start_error = None

        if port_is_in_use(self._port, lan_bind=lan_bind, host=host):
            raise OSError(
                10048,
                f"Port {self._port} is already in use on {bind_host}",
            )

        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError(
                "uvicorn is not installed; pip install -r requirements-web.txt"
            ) from exc

        config = uvicorn.Config(
            app,
            host=bind_host,
            port=self._port,
            log_level="warning",
            access_log=False,
            log_config=None,
            use_colors=False,
        )
        self._server = uvicorn.Server(config)

        def _run() -> None:
            try:
                self._server.run()
            except OSError as exc:
                self._start_error = str(exc)
                _LOG.warning("Web server bind failed on %s:%s: %s", bind_host, self._port, exc)
            except Exception:
                self._start_error = "Web server exited unexpectedly"
                _LOG.exception("Web server thread exited")

        self._thread = threading.Thread(target=_run, name="bridge-web-ui", daemon=True)
        self._thread.start()
        if not self._wait_until_listening(listen_timeout):
            self.stop(join_timeout=3.0)
            detail = self._start_error or f"Port {self._port} did not become ready in time"
            raise RuntimeError(detail)
        _LOG.info("Web control plane listening on http://%s:%s", bind_host, self._port)

    def _wait_until_listening(self, timeout: float) -> bool:
        probe = "127.0.0.1"
        deadline = time.monotonic() + max(0.1, timeout)
        while time.monotonic() < deadline:
            if self._start_error:
                return False
            if self._thread is not None and not self._thread.is_alive():
                return False
            try:
                with socket.create_connection((probe, self._port), timeout=0.2):
                    return True
            except OSError:
                time.sleep(0.08)
        return False

    def stop(self, *, join_timeout: float = 3.0) -> None:
        server = self._server
        thread = self._thread
        if server is not None:
            server.should_exit = True
        if thread is not None and thread.is_alive():
            thread.join(timeout=join_timeout)
        self._thread = None
        self._server = None
        self._start_error = None
