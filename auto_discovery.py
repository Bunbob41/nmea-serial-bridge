"""Background GNSS/serial device scanner (legacy Qt thread).

Serial matching is delegated to ``discovery_service.scan_serial_ports``.
For UI card grids use ``discovery_service.build_snapshot`` on a timer
(see ``BridgeLogicMixin._poll_discovery_snapshot``).

Emits ``device_detected(port_name)`` when a matching USB-serial adapter
appears and has been stable for *stable_polls* consecutive scans.  This
prevents false triggers during Windows USB enumeration churn (a device
briefly appears then disappears during driver negotiation).

The signal fires once per plug-in event and resets only after the device
has been absent for at least one poll cycle, so reconnecting the same
cable emits again correctly.

Usage::

    thread = AutoDiscoveryThread(parent=self)
    thread.device_detected.connect(self._on_auto_device_detected)
    thread.start()
    # … on shutdown …
    thread.stop()
"""
from __future__ import annotations

import time
from typing import Optional

from PySide6 import QtCore

from discovery_service import DEFAULT_KEYWORDS, scan_serial_ports


class AutoDiscoveryThread(QtCore.QThread):
    """Poll USB-serial ports at *poll_interval_s* second intervals.

    Emits ``device_detected(port_name: str)`` when a matching device is seen
    for *stable_polls* consecutive scans.  Requires at least one absent poll
    before re-emitting for the same port, so a hot-reload or driver reset
    will trigger again correctly.
    """

    device_detected = QtCore.Signal(str)

    def __init__(
        self,
        target_keywords: Optional[tuple[str, ...]] = None,
        poll_interval_s: float = 2.0,
        stable_polls: int = 2,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.target_keywords: tuple[str, ...] = (
            target_keywords if target_keywords is not None else DEFAULT_KEYWORDS
        )
        self.poll_interval_s: float = max(0.5, float(poll_interval_s))
        self.stable_polls: int = max(1, int(stable_polls))

        self._active: bool = True
        self._last_emitted_port: Optional[str] = None
        self._pending_port: Optional[str] = None
        self._stable_count: int = 0
        self._scan_stable_counts: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scan(self) -> Optional[str]:
        """Return the device path of the first matching port, or None."""
        devices, self._scan_stable_counts = scan_serial_ports(
            keywords=self.target_keywords,
            stable_counts=self._scan_stable_counts,
            stable_polls_required=self.stable_polls,
        )
        if devices:
            return devices[0].port
        return None

    # ------------------------------------------------------------------
    # QThread interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        while self._active:
            found = self._scan()
            if found:
                if found == self._pending_port:
                    self._stable_count += 1
                else:
                    # New candidate — restart stability counter.
                    self._pending_port = found
                    self._stable_count = 1

                if (
                    self._stable_count >= self.stable_polls
                    and found != self._last_emitted_port
                ):
                    self._last_emitted_port = found
                    self.device_detected.emit(found)
            else:
                # Device gone — reset so next plug-in triggers again.
                self._pending_port = None
                self._stable_count = 0
                self._last_emitted_port = None

            time.sleep(self.poll_interval_s)

    def stop(self) -> None:
        """Request the polling loop to exit and wait for the thread."""
        self._active = False
        self.wait(int(self.poll_interval_s * 1000 + 500))
