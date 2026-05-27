"""Terminal tab quick-ping helpers (host validation + shell command)."""
from __future__ import annotations

import re
import sys

_HOST_RE = re.compile(
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]{0,252}[a-zA-Z0-9])?$"
)


def sanitize_ping_host(raw: str) -> str | None:
    host = str(raw or "").strip()
    if not host or len(host) > 253:
        return None
    if not _HOST_RE.match(host):
        return None
    return host


def ping_pty_command(host: str, *, platform: str | None = None) -> str | None:
    """Shell line to send to an interactive PTY (includes line ending)."""
    clean = sanitize_ping_host(host)
    if not clean:
        return None
    plat = platform or sys.platform
    if plat == "win32":
        return f"ping -n 4 {clean}\r\n"
    return f"ping -c 4 {clean}\n"


def ping_subprocess_args(host: str, *, platform: str | None = None) -> list[str] | None:
    clean = sanitize_ping_host(host)
    if not clean:
        return None
    plat = platform or sys.platform
    if plat == "win32":
        return ["ping", "-n", "4", clean]
    return ["ping", "-c", "4", clean]
