"""Shared connection field validation for hub, override, and Field strip."""
from __future__ import annotations

import re
from typing import Any, Optional

# Survey / GNSS serial: common NMEA defaults through high-rate INS logging.
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

BAUD_PRESET_LABELS: tuple[str, ...] = tuple(str(b) for b in BAUD_PRESETS)
DEFAULT_BAUD = 115200


def com_port_sort_key(device: str) -> tuple[int, int, str]:
    """COM1 before COM3 before COM10 (not lexicographic COM1, COM10, COM3)."""
    raw = (device or "").strip().upper()
    match = re.match(r"^COM(\d+)$", raw)
    if match:
        return (0, int(match.group(1)), raw)
    return (1, 0, raw)


def sort_com_devices(devices: list[str]) -> list[str]:
    return sorted(devices, key=com_port_sort_key)


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


def is_allowed_baud(baud: int) -> bool:
    return baud in BAUD_PRESETS


def coerce_baud(baud: Optional[int], *, default: int = DEFAULT_BAUD) -> int:
    """Map saved/typed baud to a standard preset (nearest if legacy value)."""
    if baud is None:
        return default
    try:
        b = int(baud)
    except (TypeError, ValueError):
        return default
    if b in BAUD_PRESETS:
        return b
    if b <= 0:
        return default
    return min(BAUD_PRESETS, key=lambda p: abs(p - b))


def read_baud_widget(widget: Any) -> str:
    """Text from baud QComboBox (or legacy QLineEdit)."""
    current = getattr(widget, "currentText", None)
    if callable(current):
        return (current() or "").strip()
    text_fn = getattr(widget, "text", None)
    if callable(text_fn):
        return (text_fn() or "").strip()
    return ""


def write_baud_widget(widget: Any, baud: int | str | None) -> None:
    """Set baud on QComboBox or legacy QLineEdit."""
    try:
        raw = int(baud) if baud is not None else DEFAULT_BAUD
    except (TypeError, ValueError):
        raw = DEFAULT_BAUD
    label = str(coerce_baud(raw))
    setter = getattr(widget, "setCurrentText", None)
    if callable(setter):
        setter(label)
        return
    text_setter = getattr(widget, "setText", None)
    if callable(text_setter):
        text_setter(label)


def validate_baud(text: str) -> Optional[str]:
    baud = parse_baud(text)
    if baud is None:
        return "Choose a baud rate from the list."
    if not is_allowed_baud(baud):
        return f"Baud must be one of: {', '.join(BAUD_PRESET_LABELS)}."
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
