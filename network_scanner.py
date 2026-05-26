"""LAN discovery for Connection Hub — ARP table + bounded UDP probes (no Qt)."""
from __future__ import annotations

import re
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Sequence

from py_interpreter import subprocess_no_console_kwargs

DEFAULT_SURVEY_PORTS: tuple[int, ...] = (10110, 4001, 10111)
_PROBE_PAYLOAD = b"$PING\r\n"
_ARP_LINE_IP_RE = re.compile(
    r"^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+[0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5}",
    re.MULTILINE,
)
_IFACE_HEADER_RE = re.compile(
    r"^(?:(?:Ethernet|Wireless LAN|Wi-?Fi|Bluetooth|Tailscale|vEthernet).+adapter|Unknown adapter)\s+(.+?):\s*$",
    re.IGNORECASE,
)
_IPV4_ADDR_RE = re.compile(
    r"^\s*IPv4 Address[^:]*:\s*(\d{1,3}(?:\.\d{1,3}){3})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NetworkScanResult:
    host: str
    mac: str
    open_ports: tuple[int, ...]
    method: str
    label: str
    stale: bool
    last_seen_mono: float


def list_lan_hosts(*, arp_output: str | None = None) -> list[str]:
    """IPv4 addresses from Windows ARP table (mockable via arp_output)."""
    if arp_output is None:
        try:
            proc = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=3,
                errors="replace",
                **subprocess_no_console_kwargs(),
            )
            arp_output = proc.stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            arp_output = ""
    hosts: list[str] = []
    seen: set[str] = set()
    for line in (arp_output or "").splitlines():
        if line.strip().startswith("Interface"):
            continue
        m = _ARP_LINE_IP_RE.match(line)
        if not m:
            continue
        ip = m.group(1)
        if ip.startswith("224.") or ip.startswith("255."):
            continue
        if ip not in seen:
            seen.add(ip)
            hosts.append(ip)
    if "127.0.0.1" not in seen:
        hosts.insert(0, "127.0.0.1")
    return hosts[:64]


@dataclass(frozen=True)
class HostIpv4Interface:
    """Windows NIC name + IPv4 from ipconfig (for dashboard bind hints)."""

    label: str
    address: str


def list_host_ipv4_interfaces(*, ipconfig_output: str | None = None) -> list[HostIpv4Interface]:
    """IPv4 addresses on this PC's adapters (Ethernet, Wi‑Fi, Tailscale, etc.)."""
    if ipconfig_output is None:
        try:
            proc = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                timeout=4,
                errors="replace",
                **subprocess_no_console_kwargs(),
            )
            ipconfig_output = proc.stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            ipconfig_output = ""
    current_label = ""
    out: list[HostIpv4Interface] = []
    seen: set[tuple[str, str]] = set()
    for line in (ipconfig_output or "").splitlines():
        m_hdr = _IFACE_HEADER_RE.match(line.strip())
        if m_hdr:
            current_label = m_hdr.group(1).strip()
            continue
        if not current_label:
            continue
        m_ip = _IPV4_ADDR_RE.match(line)
        if not m_ip:
            continue
        ip = m_ip.group(1)
        if ip.startswith("127.") or ip.startswith("169.254."):
            continue
        key = (current_label, ip)
        if key in seen:
            continue
        seen.add(key)
        out.append(HostIpv4Interface(label=current_label, address=ip))
    return out


def probe_host_udp(
    host: str,
    ports: Sequence[int],
    *,
    timeout_s: float = 0.25,
    probe_payload: bytes = _PROBE_PAYLOAD,
) -> tuple[int, ...]:
    """Return ports where UDP send succeeded (best-effort; no listen bind)."""
    open_ports: list[int] = []
    for port in ports:
        try:
            port_i = int(port)
        except (TypeError, ValueError):
            continue
        if port_i < 1 or port_i > 65535:
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(timeout_s)
            sock.sendto(probe_payload, (host, port_i))
            try:
                sock.recvfrom(256)
            except socket.timeout:
                pass
            except OSError:
                pass
            open_ports.append(port_i)
        except OSError:
            pass
        finally:
            sock.close()
    return tuple(open_ports)


def scan_network(
    *,
    ports: Sequence[int] = DEFAULT_SURVEY_PORTS,
    max_hosts: int = 32,
    deadline_s: float = 6.0,
    skip_bind_port: int | None = None,
    arp_output: str | None = None,
) -> list[NetworkScanResult]:
    """Scan LAN hosts with ARP inventory + UDP probes within deadline."""
    start = time.monotonic()
    hosts = list_lan_hosts(arp_output=arp_output)[:max_hosts]
    ports_probe = [p for p in ports if p != skip_bind_port]
    if not ports_probe:
        ports_probe = list(ports)
    results: list[NetworkScanResult] = []
    for host in hosts:
        if time.monotonic() - start >= deadline_s:
            break
        open_ports = probe_host_udp(host, ports_probe)
        method = "udp_probe" if open_ports else "arp"
        port_hint = open_ports[0] if open_ports else (ports_probe[0] if ports_probe else 10110)
        label = f"{host}:{port_hint}"
        if open_ports:
            label = f"{host} (UDP {','.join(str(p) for p in open_ports)})"
        results.append(
            NetworkScanResult(
                host=host,
                mac="",
                open_ports=open_ports,
                method=method,
                label=label,
                stale=False,
                last_seen_mono=time.monotonic(),
            )
        )
    return results
