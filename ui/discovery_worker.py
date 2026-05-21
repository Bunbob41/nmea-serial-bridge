"""Background discovery scan worker (serial + LAN network)."""
from __future__ import annotations

from typing import Any, Optional

from PySide6 import QtCore

from discovery_service import build_snapshot


class DiscoveryScanWorker(QtCore.QThread):
    snapshot_ready = QtCore.Signal(object, object)
    scan_failed = QtCore.Signal(str)

    def __init__(
        self,
        params: dict[str, Any],
        *,
        full_network_scan: bool = True,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._params = dict(params)
        self._full_network_scan = bool(full_network_scan)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            network_results = None
            if self._full_network_scan and not self._cancelled:
                from network_scanner import scan_network

                network_results = scan_network(
                    skip_bind_port=self._params.get("skip_bind_port"),
                    max_hosts=int(self._params.get("max_hosts", 32)),
                    deadline_s=float(self._params.get("deadline_s", 6.0)),
                )
            if self._cancelled:
                return
            snap, counts = build_snapshot(
                stable_counts=self._params.get("stable_counts"),
                presets=self._params.get("presets"),
                active_preset=self._params.get("active_preset"),
                bridge_stats=self._params.get("bridge_stats"),
                udp_host=str(self._params.get("udp_host") or "0.0.0.0"),
                udp_port=int(self._params.get("udp_port", 10110)),
                selected_port=self._params.get("selected_port"),
                network_scan_results=network_results,
            )
            if not self._cancelled:
                self.snapshot_ready.emit(snap, counts)
        except Exception as exc:
            if not self._cancelled:
                self.scan_failed.emit(str(exc))
