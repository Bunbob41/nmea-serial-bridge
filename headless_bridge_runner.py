"""Background asyncio bridge thread without Qt (Linux headless / bench)."""
from __future__ import annotations

import asyncio
import threading
import traceback
from typing import Callable, Optional

from bridge_core import (
    START_ASYNC_TIMEOUT_S,
    BridgeBuildFn,
    SerialNetBridge,
    configure_windows_event_loop_policy,
    install_bridge_loop_exception_handler,
)


class HeadlessBridgeRunner:
    """Run SerialNetBridge on a dedicated asyncio loop in a plain thread."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self.bridge: Optional[SerialNetBridge] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._start_event = threading.Event()
        self._start_ok = False
        self.on_log: Callable[[str], None] = lambda _msg: None
        self.on_stats: Callable[[dict], None] = lambda _stats: None
        self.on_start_done: Callable[[bool], None] = lambda _ok: None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def bridge_running(self) -> bool:
        bridge = self.bridge
        return bool(bridge is not None and bridge.running)

    def start(self, build: BridgeBuildFn, *, join_timeout: float = 15.0) -> bool:
        if self.is_alive():
            return False
        self._start_event.clear()
        self._start_ok = False
        self.bridge = None

        def _run() -> None:
            configure_windows_event_loop_policy()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            install_bridge_loop_exception_handler(loop)
            self._loop = loop
            started_ok = False
            try:
                self.bridge = build(loop)
                started_ok = bool(
                    loop.run_until_complete(
                        asyncio.wait_for(self.bridge.start(), timeout=START_ASYNC_TIMEOUT_S)
                    )
                )
                self._start_ok = started_ok
                self.on_start_done(started_ok)
                if started_ok:
                    loop.run_forever()
            except Exception as exc:
                tb = traceback.format_exc()
                self.on_log(f"Bridge thread: {exc!r}\n{tb}")
                self._start_ok = False
                self.on_start_done(False)
            finally:
                self._start_event.set()
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
                self._loop = None

        self._thread = threading.Thread(target=_run, name="headless-bridge", daemon=True)
        self._thread.start()
        if not self._start_event.wait(timeout=max(1.0, join_timeout)):
            return False
        return bool(self._start_ok)

    def stop(self, *, join_timeout: float = 5.0) -> None:
        loop = self._loop
        bridge = self.bridge
        if loop is not None:

            def _stop() -> None:
                if bridge is not None:
                    try:
                        bridge.abort_now()
                    except Exception:
                        pass
                try:
                    loop.stop()
                except Exception:
                    pass

            try:
                loop.call_soon_threadsafe(_stop)
            except RuntimeError:
                pass
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.5, join_timeout))
        self._thread = None
        self.bridge = None
        self._loop = None
