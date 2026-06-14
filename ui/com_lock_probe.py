"""Background COM exclusivity probe (keeps GUI thread responsive)."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore

from port_release import probe_com_lock

# Primitives only — dataclasses through queued signals can fail to deliver on some PySide builds.
_PROBE_TIMEOUT_S = 1.5


class ComLockProbeWorker(QtCore.QThread):
    result_ready = QtCore.Signal(str, str, int, bool, str, bool)

    def __init__(
        self,
        port: str,
        baud: int,
        *,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._port = (port or "").strip()
        self._baud = int(baud)

    def run(self) -> None:
        port = self._port
        baud = self._baud
        if not port or port.startswith("("):
            self.result_ready.emit(port, port, baud, False, "No COM port selected", False)
            return
        try:
            state = probe_com_lock(port, baud, timeout_s=_PROBE_TIMEOUT_S)
            self.result_ready.emit(
                port,
                state.port,
                baud,
                bool(state.locked),
                str(state.reason or ""),
                bool(state.last_attempt_ok),
            )
        except Exception as exc:
            self.result_ready.emit(
                port,
                port,
                baud,
                True,
                str(exc),
                False,
            )
