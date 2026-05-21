"""Shared connection field validation for hub, override, and Field strip."""
from __future__ import annotations

from typing import Optional

BAUD_PRESETS: tuple[int, ...] = (
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
)


def parse_baud(text: str) -> Optional[int]:
    raw = (text or "").strip().replace(",", "")
    if not raw:
        return None
    try:
        baud = int(raw)
    except ValueError:
        return None
    if baud <= 0 or baud > 10_000_000:
        return None
    return baud


def validate_baud(text: str) -> Optional[str]:
    if parse_baud(text) is None:
        return "Enter a valid baud rate (positive integer, e.g. 115200)."
    return None


def validate_udp_port(text: str, *, label: str = "UDP port") -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return f"Enter a valid {label}."
    try:
        port = int(raw)
    except ValueError:
        return f"Enter a valid {label} (1–65535)."
    if port < 1 or port > 65535:
        return f"{label} must be between 1 and 65535."
    return None
