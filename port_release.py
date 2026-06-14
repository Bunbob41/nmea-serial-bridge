"""Smart COM / UDP port release helpers (no Qt)."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import serial

from discovery_service import probe_udp_port_available


@dataclass
class PortLockState:
    port: str
    locked: bool
    reason: str
    safe_to_release: bool
    last_attempt_ok: Optional[bool] = None


def probe_com_lock(port: str, baud: int, *, timeout_s: float = 5.0) -> PortLockState:
    port = (port or "").strip()
    if not port:
        return PortLockState("", False, "No COM port specified", True, None)
    result: list[bool] = []
    err: list[str] = []

    def _work() -> None:
        try:
            ser = serial.Serial(port=port, baudrate=baud, timeout=0, write_timeout=0)
            ser.close()
            result.append(True)
        except Exception as exc:
            err.append(str(exc))

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if result:
        return PortLockState(port, False, "Port available", True, True)
    if t.is_alive():
        return PortLockState(
            port,
            True,
            f"Timed out opening {port} after {timeout_s:.0f}s",
            True,
            False,
        )
    msg = err[0] if err else "Unknown error"
    low = msg.lower()
    if "access is denied" in low or "permission" in low or "in use" in low:
        return PortLockState(port, True, msg, True, False)
    return PortLockState(port, True, msg, True, False)


def smart_release_com(
    port: str,
    baud: int,
    *,
    bridge_running: bool,
    bridge_com: Optional[str] = None,
) -> PortLockState:
    port = (port or "").strip()
    if bridge_running and bridge_com and port.upper() == bridge_com.upper():
        return PortLockState(
            port,
            True,
            "Bridge is running on this COM — stop the bridge first",
            False,
            False,
        )
    state = probe_com_lock(port, baud)
    if state.last_attempt_ok:
        return PortLockState(
            port,
            False,
            f"{port} probed open/close OK",
            True,
            True,
        )
    return state


def serial_port_discovery_status(
    port: str,
    baud: int,
    *,
    bridge_running: bool = False,
    bridge_com: Optional[str] = None,
    timeout_s: float = 2.0,
) -> str:
    """Discovery card / hub status for a serial endpoint."""
    port = (port or "").strip()
    if not port:
        return "stale"
    if bridge_running and bridge_com and port.upper() == bridge_com.strip().upper():
        return "running"
    state = probe_com_lock(port, baud, timeout_s=timeout_s)
    if state.last_attempt_ok:
        return "ready"
    return "port_busy"


def hint_udp_listen_busy(host: str, port: int) -> Optional[str]:
    if probe_udp_port_available(host, port):
        return None
    return (
        f"UDP port {port} on {host} is in use. "
        "Stop the bridge or choose another listen port."
    )
