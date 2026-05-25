"""Mediate Product Demo mutations on the live host window."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtWidgets

from ui.demo_snapshot import (
    OperatorSessionSnapshot,
    capture_operator_snapshot,
    restore_operator_snapshot,
)

ActionFn = Callable[[QtWidgets.QWidget], None]


class DemoHostGateway:
    def __init__(self) -> None:
        self._snapshot: Optional[OperatorSessionSnapshot] = None
        self.demo_started_bridge = False
        self.demo_stopped_user_bridge = False
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def snapshot(self) -> Optional[OperatorSessionSnapshot]:
        return self._snapshot

    @staticmethod
    def _bridge_active(host: QtWidgets.QWidget) -> bool:
        return getattr(host, "bridge", None) is not None or bool(
            getattr(host, "_starting", False)
        )

    def enter(self, host: QtWidgets.QWidget) -> None:
        if self._active:
            return
        self._snapshot = capture_operator_snapshot(host)
        self.demo_started_bridge = False
        self.demo_stopped_user_bridge = False
        self._active = True
        host._demo_session_active = True  # type: ignore[attr-defined]
        host._demo_gateway = self  # type: ignore[attr-defined]
        if hasattr(host, "_set_demo_status_chip"):
            host._set_demo_status_chip(True)  # type: ignore[attr-defined]

    def exit(self, host: QtWidgets.QWidget) -> None:
        if not self._active:
            return
        snap = self._snapshot
        started = self.demo_started_bridge
        stopped = self.demo_stopped_user_bridge
        self._active = False
        host._demo_session_active = False  # type: ignore[attr-defined]
        self._snapshot = None
        self.demo_started_bridge = False
        self.demo_stopped_user_bridge = False
        if snap is not None:
            restore_operator_snapshot(
                host,
                snap,
                demo_started_bridge=started,
                demo_stopped_user_bridge=stopped,
            )
        if hasattr(host, "_set_demo_status_chip"):
            host._set_demo_status_chip(False)  # type: ignore[attr-defined]

    def run_action(self, host: QtWidgets.QWidget, action: Optional[ActionFn]) -> None:
        if action is None:
            return
        before = self._bridge_active(host)
        try:
            action(host)
        except Exception as exc:
            if hasattr(host, "_log_ui"):
                host._log_ui(f"[Demo] Step error: {exc}")  # type: ignore[attr-defined]
        after = self._bridge_active(host)
        if not before and after:
            self.demo_started_bridge = True
        if before and not after:
            self.demo_stopped_user_bridge = True

    def reset_demo_script(self, dialog: QtWidgets.QDialog) -> None:
        """Rewind presenter index only — no host restore."""
        if hasattr(dialog, "_bootstrap_presenter"):
            dialog._bootstrap_presenter()  # type: ignore[attr-defined]
