"""Qt bridge worker thread (desktop / Fleet). Kept separate so bridge_core stays GUI-free."""
from __future__ import annotations

import asyncio
import traceback
from typing import Callable, Optional

from PySide6 import QtCore

from bridge_core import (
    START_ASYNC_TIMEOUT_S,
    BridgeBuildFn,
    SerialNetBridge,
    configure_windows_event_loop_policy,
    install_bridge_loop_exception_handler,
)


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
        if loop is None:
            return

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

    def call_on_loop(self, fn: Callable[[], None]) -> None:
        loop = self._loop
        if loop:
            loop.call_soon_threadsafe(fn)
