"""Background uvicorn thread for Web control plane."""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

_LOG = logging.getLogger(__name__)


class WebServerThread:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._server: Any = None
        self._host = "127.0.0.1"
        self._port = 8765

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, app: Any, *, host: str, port: int, lan_bind: bool) -> None:
        if self.running:
            self.stop(join_timeout=2.0)
        if lan_bind and host in ("127.0.0.1", "localhost"):
            bind_host = "0.0.0.0"
        else:
            bind_host = host or "127.0.0.1"
        self._host = bind_host
        self._port = int(port)

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
        )
        self._server = uvicorn.Server(config)

        def _run() -> None:
            try:
                self._server.run()
            except Exception:
                _LOG.exception("Web server thread exited")

        self._thread = threading.Thread(target=_run, name="bridge-web-ui", daemon=True)
        self._thread.start()
        _LOG.info("Web control plane listening on http://%s:%s", bind_host, self._port)

    def stop(self, *, join_timeout: float = 2.0) -> None:
        server = self._server
        thread = self._thread
        if server is not None:
            server.should_exit = True
        if thread is not None and thread.is_alive():
            thread.join(timeout=join_timeout)
        self._thread = None
        self._server = None
