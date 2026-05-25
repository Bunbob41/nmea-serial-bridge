"""Phone dashboard base URL helpers (Tailscale / LAN — not 127.0.0.1)."""
from __future__ import annotations

import socket
import subprocess
import sys
from typing import List
from urllib.parse import urlparse

from web.token_setup import normalize_base_url


def is_loopback_base(url: str) -> bool:
    """True if URL host is localhost (unreachable from phone on tailnet)."""
    base = normalize_base_url(url)
    if not base:
        return True
    try:
        host = urlparse(base).hostname or ""
    except Exception:
        return True
    host = host.lower()
    return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")


def normalize_phone_base_url(text: str) -> str:
    """Base URL only — strip #bridge-token and accidental pasted setup links."""
    s = (text or "").strip()
    if not s:
        return ""
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    if "bridge-token=" in s and "://" not in s:
        return ""
    return normalize_base_url(s)


def _tailscale_ipv4() -> List[str]:
    out: List[str] = []
    try:
        kwargs: dict = {
            "capture_output": True,
            "text": True,
            "timeout": 3,
            "errors": "replace",
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(["tailscale", "ip", "-4"], **kwargs)
        for line in (proc.stdout or "").splitlines():
            ip = line.strip().split()[0] if line.strip() else ""
            if ip and "." in ip:
                out.append(ip)
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return out


def _hostname_ipv4() -> List[str]:
    out: List[str] = []
    try:
        for res in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = res[4][0]
            if ip and not ip.startswith("127."):
                out.append(ip)
    except OSError:
        pass
    return out


def suggest_phone_base_urls(port: int) -> List[str]:
    """Prefer Tailscale (100.x) then private LAN addresses."""
    seen: set[str] = set()
    ordered_ips: List[str] = []

    def add_ip(ip: str) -> None:
        if not ip or ip in seen or ip.startswith("127."):
            return
        seen.add(ip)
        ordered_ips.append(ip)

    for ip in _tailscale_ipv4():
        add_ip(ip)
    for ip in _hostname_ipv4():
        add_ip(ip)

    def sort_key(ip: str) -> tuple:
        if ip.startswith("100."):
            return (0, ip)
        if ip.startswith("192.168."):
            return (1, ip)
        if ip.startswith("10."):
            return (2, ip)
        return (3, ip)

    ordered_ips.sort(key=sort_key)
    return [f"http://{ip}:{port}" for ip in ordered_ips]
