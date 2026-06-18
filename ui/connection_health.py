"""Compact connection health chip for Modern header (Serial · Network · NMEA · state)."""
from __future__ import annotations

import re
from typing import Literal

HealthKind = Literal["idle", "ok", "warn", "error"]

_SERIAL_COM_RE = re.compile(r"Serial:\s*(\S+)", re.IGNORECASE)
_UDP_LISTEN_RE = re.compile(
    r"Network:\s*UDP listen\s+[\d.]+:(\d+)(?:\s*—\s*(.+))?",
    re.IGNORECASE,
)
_UDP_REMOTE_RE = re.compile(r"Network:\s*UDP →\s+[\d.]+:(\d+)", re.IGNORECASE)
_TCP_SERVER_RE = re.compile(
    r"Network:\s*TCP server\s+[\d.]+:(\d+)(?:\s*—\s*(.+))?",
    re.IGNORECASE,
)
_TCP_CLIENT_RE = re.compile(
    r"Network:\s*TCP (?:client connecting to|connected to|reconnecting)[^:]*:[\d.]+:(\d+)",
    re.IGNORECASE,
)


def _serial_health(line: str) -> HealthKind:
    low = (line or "").strip().lower()
    if not low or "stopped" in low or "not started" in low:
        return "idle"
    if any(token in low for token in ("error", "timeout", "cannot open", "not found")):
        return "error"
    if any(token in low for token in ("disconnected", "reconnect", "retry", "opening")):
        return "warn"
    if "open" in low or "reconnected" in low:
        return "ok"
    if "starting" in low:
        return "warn"
    return "warn"


def _network_health(line: str) -> HealthKind:
    low = (line or "").strip().lower()
    if not low or "stopped" in low or "not started" in low:
        return "idle"
    if any(token in low for token in ("error", "failed", "refused", "timed out")):
        return "error"
    if any(token in low for token in ("waiting", "connecting", "reconnecting", "starting")):
        return "warn"
    if "open" in low or "listen" in low or "connected" in low or "peer" in low or "→" in line:
        return "ok"
    return "warn"


def _serial_short(line: str, *, fallback_com: str = "COM") -> str:
    text = (line or "").strip()
    low = text.lower()
    if not text or "stopped" in low or "closed" in low:
        com = (fallback_com or "COM").strip() or "COM"
        return com if not com.startswith("(") else "COM"
    match = _SERIAL_COM_RE.search(text)
    if match:
        token = match.group(1).rstrip("@")
        if token.lower() not in ("stopped", "starting", "opening", "closed", "error"):
            return token
    if "disconnected" in low:
        return "Serial retry"
    if "opening" in low:
        return "Opening…"
    return fallback_com or "COM"


def _network_short(line: str, *, fallback_port: str = "10110") -> str:
    text = (line or "").strip()
    if not text or "stopped" in text.lower():
        port = (fallback_port or "10110").strip() or "10110"
        return f"UDP:{port}"
    match = _UDP_LISTEN_RE.search(text)
    if match:
        return f"UDP:{match.group(1)}"
    match = _UDP_REMOTE_RE.search(text)
    if match:
        return f"UDP→:{match.group(1)}"
    match = _TCP_SERVER_RE.search(text)
    if match:
        return f"TCP:{match.group(1)}"
    match = _TCP_CLIENT_RE.search(text)
    if match:
        return f"TCP→:{match.group(1)}"
    if "udp listen" in text.lower():
        return "UDP listen"
    if "udp" in text.lower():
        return "UDP"
    if "tcp" in text.lower():
        return "TCP"
    return "Network"


def _nmea_short(mode: str) -> str:
    label = (mode or "passthrough").strip().lower()
    if label == "raw":
        return "raw"
    if label.startswith("strict"):
        return "strict"
    return "pass"


def _session_short(*, running: bool, starting: bool) -> tuple[str, HealthKind]:
    if running:
        return "Run", "ok"
    if starting:
        return "Start…", "warn"
    return "Stop", "idle"


def _overall_health(parts: tuple[HealthKind, ...]) -> HealthKind:
    if "error" in parts:
        return "error"
    if "warn" in parts:
        return "warn"
    if all(p == "idle" for p in parts[:3]):
        return "idle"
    return "ok"


def format_connection_health_chip(
    *,
    serial_line: str,
    network_line: str,
    nmea_mode: str,
    running: bool,
    starting: bool = False,
    fallback_com: str = "COM",
    fallback_udp_port: str = "10110",
) -> tuple[str, HealthKind, str]:
    """Return (chip_text, healthKind, tooltip) for the Modern header pill."""
    serial_h = _serial_health(serial_line)
    network_h = _network_health(network_line)
    session_label, session_h = _session_short(running=running, starting=starting)

    serial = _serial_short(serial_line, fallback_com=fallback_com)
    network = _network_short(network_line, fallback_port=fallback_udp_port)
    nmea = _nmea_short(nmea_mode)

    chip = f"{serial} · {network} · {nmea} · {session_label}"
    kind = _overall_health((serial_h, network_h, session_h))

    tooltip = (
        f"Serial — {serial_line or 'stopped'}\n"
        f"Network — {network_line or 'stopped'}\n"
        f"NMEA — {nmea_mode or 'passthrough'}\n"
        f"Session — {'Running' if running else 'Starting…' if starting else 'Stopped'}"
    )
    return chip, kind, tooltip
