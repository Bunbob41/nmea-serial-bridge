"""Terminal tab quick-ping helpers (host validation + shell command)."""
from __future__ import annotations

import ipaddress
import re
import sys
from collections.abc import Mapping
from typing import Optional

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


def _ping_preset_label_from_host(host: str) -> str:
    """Short default preset name for a ping target (IP kept as-is; FQDN → first label)."""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    if "." in host:
        return host.split(".", 1)[0]
    return host


def suggested_ping_preset_name(
    host: str,
    preset_hosts: Optional[Mapping[str, str]] = None,
) -> str:
    """Default Save-preset label for the current ping host (not the last combo selection)."""
    clean = sanitize_ping_host(host)
    if not clean:
        return str(host or "").strip()
    if preset_hosts is None:
        from ui import ui_prefs

        preset_hosts = {
            name: ui_prefs.terminal_ping_host(name) or ""
            for name in ui_prefs.list_terminal_ping_preset_names()
        }
    for name, saved_host in preset_hosts.items():
        if saved_host == clean:
            return name
    return _ping_preset_label_from_host(clean)
