"""Connection discovery — serial ports and passive network context (no Qt)."""
from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass, field, replace
from typing import Any, Optional, Sequence

import serial.tools.list_ports

DEFAULT_KEYWORDS: tuple[str, ...] = (
    "Trimble",
    "GNSS",
    "U-blox",
    "ublox",
    "u-blox",
    "NovAtel",
    "Septentrio",
    "Leica",
    "Topcon",
    "Hemisphere",
    "SiRF",
    "Garmin",
)


@dataclass(frozen=True)
class SerialDeviceInfo:
    device_id: str
    port: str
    description: str
    manufacturer: str
    match_keyword: str
    status: str  # available | stale | in_use


@dataclass(frozen=True)
class NetworkCardInfo:
    device_id: str
    label: str
    mode_hint: str
    host: str
    port: int
    port_available: bool
    peer_count: int
    status: str  # ready | port_busy | running
    discovery_source: str = "passive"  # passive | arp | udp_probe


@dataclass
class DiscoverySnapshot:
    mono_ts: float = 0.0
    serial_devices: list[SerialDeviceInfo] = field(default_factory=list)
    network_cards: list[NetworkCardInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    scan_note: str = ""


def _combined_port_text(port: Any) -> str:
    return " ".join(filter(None, [port.description, port.manufacturer, port.hwid])).lower()


def _match_keyword(port: Any, keywords: Sequence[str]) -> Optional[str]:
    combined = _combined_port_text(port)
    for kw in keywords:
        if kw.lower() in combined:
            return kw
    return None


def serial_device_id(port: Any) -> str:
    hwid = (getattr(port, "hwid", None) or "").strip()
    if hwid:
        return f"serial:{hwid}"
    return f"serial:{port.device}"


def scan_serial_ports(
    *,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
    stable_counts: Optional[dict[str, int]] = None,
    stable_polls_required: int = 2,
    selected_port: Optional[str] = None,
) -> tuple[list[SerialDeviceInfo], dict[str, int]]:
    """Return stable serial devices and updated stability counters keyed by port."""
    counts = dict(stable_counts or {})
    out: list[SerialDeviceInfo] = []
    seen_ports: set[str] = set()

    for port in serial.tools.list_ports.comports():
        device = port.device
        seen_ports.add(device)
        kw = _match_keyword(port, keywords)
        if not kw:
            counts.pop(device, None)
            continue
        counts[device] = counts.get(device, 0) + 1
        if counts[device] < stable_polls_required:
            continue
        status = "available"
        out.append(
            SerialDeviceInfo(
                device_id=serial_device_id(port),
                port=device,
                description=(port.description or "").strip(),
                manufacturer=(port.manufacturer or "").strip(),
                match_keyword=kw,
                status=status,
            )
        )

    for p in list(counts.keys()):
        if p not in seen_ports:
            counts.pop(p, None)

    return out, counts


def list_all_serial_ports(
    *,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
    selected_port: Optional[str] = None,
) -> list[SerialDeviceInfo]:
    """List every COM port on this PC (no GNSS keyword filter, no stability wait).

    Used by the web dashboard and desktop Refresh — same source as ``serial.tools.list_ports``.
    ``match_keyword`` is set when the port looks survey/GNSS-related (badge only).
    """
    out: list[SerialDeviceInfo] = []
    for port in serial.tools.list_ports.comports():
        device = (port.device or "").strip()
        if not device:
            continue
        kw = _match_keyword(port, keywords) or ""
        desc = (port.description or "").strip()
        if not desc:
            desc = (port.manufacturer or "").strip() or "Serial port"
        out.append(
            SerialDeviceInfo(
                device_id=serial_device_id(port),
                port=device,
                description=desc,
                manufacturer=(port.manufacturer or "").strip(),
                match_keyword=kw,
                status="available",
            )
        )
    out.sort(key=lambda d: d.port)
    if selected_port:
        sel = selected_port.strip()
        out.sort(key=lambda d: (0 if d.port == sel else 1, d.port))
    return out


def probe_udp_port_available(host: str, port: int) -> bool:
    host = (host or "0.0.0.0").strip() or "0.0.0.0"
    try:
        port_i = int(port)
    except (TypeError, ValueError):
        return False
    if port_i < 0 or port_i > 65535:
        return False
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port_i))
        return True
    except (OSError, OverflowError):
        return False
    finally:
        sock.close()


def build_network_cards(
    *,
    presets: Optional[list[dict]] = None,
    active_preset: Optional[str] = None,
    bridge_stats: Optional[dict] = None,
    default_udp_host: str = "0.0.0.0",
    default_udp_port: int = 10110,
) -> list[NetworkCardInfo]:
    cards: list[NetworkCardInfo] = []
    stats = bridge_stats or {}
    peer_count = int(stats.get("udp_peers") or stats.get("udp_peer_count") or 0)
    running = bool(stats.get("running"))
    listen_host = str(stats.get("udp_listen_host") or default_udp_host)
    listen_port = int(stats.get("udp_listen_port") or default_udp_port)
    port_ok = probe_udp_port_available(listen_host, listen_port)

    if running and peer_count > 0:
        status = "running"
    elif not port_ok:
        status = "port_busy"
    else:
        status = "ready"

    cards.append(
        NetworkCardInfo(
            device_id=f"net:udp_listen:{listen_host}:{listen_port}",
            label=f"UDP listen {listen_host}:{listen_port}",
            mode_hint="udp_listen",
            host=listen_host,
            port=listen_port,
            port_available=port_ok,
            peer_count=peer_count,
            status=status,
        )
    )

    for preset in presets or []:
        name = str(preset.get("name") or "").strip()
        if not name or name == active_preset:
            continue
        host = str(preset.get("udp_host") or default_udp_host)
        try:
            port = int(preset.get("udp_port", default_udp_port))
        except (TypeError, ValueError):
            port = default_udp_port
        cards.append(
            NetworkCardInfo(
                device_id=f"net:preset:{name}",
                label=f"Preset: {name} ({host}:{port})",
                mode_hint="udp_listen",
                host=host,
                port=port,
                port_available=probe_udp_port_available(host, port),
                peer_count=0,
                status="ready",
            )
        )
    return cards


def merge_host_interface_cards(
    cards: list[NetworkCardInfo],
    interfaces: list,
    *,
    default_udp_port: int = 10110,
) -> list[NetworkCardInfo]:
    """Append this PC's NIC IPv4 addresses as bind hints (Windows ipconfig)."""
    from network_scanner import HostIpv4Interface

    seen = {(c.host, c.port) for c in cards}
    out = list(cards)
    for item in interfaces or []:
        if not isinstance(item, HostIpv4Interface):
            continue
        ip = item.address
        port = default_udp_port
        key = (ip, port)
        if key in seen:
            continue
        seen.add(key)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", item.label).strip("_") or "iface"
        out.append(
            NetworkCardInfo(
                device_id=f"net:iface:{slug}:{ip}",
                label=f"{item.label} ({ip})",
                mode_hint="bind_hint",
                host=ip,
                port=port,
                port_available=probe_udp_port_available(ip, port),
                peer_count=0,
                status="ready",
                discovery_source="host_nic",
            )
        )
    return out


def merge_discovered_network_cards(
    cards: list[NetworkCardInfo],
    network_scan_results: list,
    *,
    default_udp_port: int = 10110,
) -> list[NetworkCardInfo]:
    """Append LAN-discovered cards; dedupe by host+port."""
    from network_scanner import NetworkScanResult

    seen = {(c.host, c.port) for c in cards}
    out = list(cards)
    for item in network_scan_results or []:
        if not isinstance(item, NetworkScanResult):
            continue
        port = int(item.open_ports[0]) if item.open_ports else default_udp_port
        key = (item.host, port)
        if key in seen:
            continue
        seen.add(key)
        method = item.method if item.open_ports else "arp"
        out.append(
            NetworkCardInfo(
                device_id=f"net:discovered:{item.host}:{port}",
                label=item.label or f"LAN {item.host}:{port}",
                mode_hint="udp_listen",
                host=item.host,
                port=port,
                port_available=True,
                peer_count=0,
                status="ready",
                discovery_source=method,
            )
        )
    return out


def merge_tailscale_bind_cards(
    cards: list[NetworkCardInfo],
    *,
    default_udp_port: int = 10110,
) -> list[NetworkCardInfo]:
    """Append Tailscale IPv4 from ``tailscale ip -4`` when ipconfig misses the adapter."""
    try:
        from web.phone_url import _tailscale_ipv4
    except Exception:
        return cards
    seen = {(c.host, c.port) for c in cards}
    out = list(cards)
    for ip in _tailscale_ipv4():
        key = (ip, default_udp_port)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            NetworkCardInfo(
                device_id=f"net:tailscale:{ip}",
                label=f"Tailscale ({ip})",
                mode_hint="bind_hint",
                host=ip,
                port=default_udp_port,
                port_available=probe_udp_port_available(ip, default_udp_port),
                peer_count=0,
                status="ready",
                discovery_source="tailscale_cli",
            )
        )
    return out


def resolve_network_bind_from_device_id(
    device_id: str,
    *,
    default_udp_port: int = 10110,
) -> Optional[tuple[str, int]]:
    """Parse net:* device_id into (udp_listen_host, udp_listen_port) for web PATCH."""
    did = (device_id or "").strip()
    if not did.startswith("net:"):
        return None
    prefix = "net:udp_listen:"
    if did.startswith(prefix):
        rest = did[len(prefix) :]
        if ":" not in rest:
            return None
        host, port_s = rest.rsplit(":", 1)
        try:
            port = int(port_s)
        except (TypeError, ValueError):
            port = default_udp_port
        return host, port
    if did.startswith("net:discovered:"):
        parts = did.split(":")
        if len(parts) < 5:
            return None
        host = parts[2]
        try:
            port = int(parts[3])
        except (TypeError, ValueError):
            port = default_udp_port
        return host, port
    if did.startswith("net:iface:"):
        host = did.rsplit(":", 1)[-1]
        if host and "." in host:
            return host, default_udp_port
    if did.startswith("net:tailscale:"):
        host = did[len("net:tailscale:") :].strip()
        if host and "." in host:
            return host, default_udp_port
    if did.startswith("net:preset:"):
        rest = did[len("net:preset:") :]
        if not rest:
            return None
        try:
            from ui.ui_prefs import load_preset

            data = load_preset(rest)
            if data:
                host = str(data.get("udp_host") or "0.0.0.0").strip() or "0.0.0.0"
                port = int(data.get("udp_port", default_udp_port))
                return host, port
        except Exception:
            return None
    return None


def annotate_serial_lock_status(
    devices: list[SerialDeviceInfo],
    *,
    selected_port: Optional[str],
    baud: int,
    bridge_running: bool = False,
    bridge_com: Optional[str] = None,
    probe_all: bool = False,
) -> list[SerialDeviceInfo]:
    """Probe COM exclusivity for hub cards (selected port always; all ports on full refresh)."""
    from port_release import serial_port_discovery_status

    sel = (selected_port or "").strip()
    out: list[SerialDeviceInfo] = []
    for dev in devices:
        if not probe_all and (not sel or dev.port != sel):
            out.append(dev)
            continue
        status = serial_port_discovery_status(
            dev.port,
            baud,
            bridge_running=bridge_running,
            bridge_com=bridge_com,
        )
        out.append(replace(dev, status=status))
    return out


def build_snapshot(
    *,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
    stable_counts: Optional[dict[str, int]] = None,
    presets: Optional[list[dict]] = None,
    active_preset: Optional[str] = None,
    bridge_stats: Optional[dict] = None,
    udp_host: str = "0.0.0.0",
    udp_port: int = 10110,
    selected_port: Optional[str] = None,
    network_scan_results: Optional[list] = None,
    probe_baud: int = 115200,
    bridge_running: bool = False,
    bridge_com: Optional[str] = None,
    probe_serial_locks: bool = False,
) -> tuple[DiscoverySnapshot, dict[str, int]]:
    serial_devices = list_all_serial_ports(
        keywords=keywords,
        selected_port=selected_port,
    )
    serial_devices = annotate_serial_lock_status(
        serial_devices,
        selected_port=selected_port,
        baud=int(probe_baud or 115200),
        bridge_running=bridge_running,
        bridge_com=bridge_com,
        probe_all=bool(probe_serial_locks),
    )
    _, counts = scan_serial_ports(
        keywords=keywords,
        stable_counts=stable_counts,
        selected_port=selected_port,
    )
    network_cards = build_network_cards(
        presets=presets,
        active_preset=active_preset,
        bridge_stats=bridge_stats,
        default_udp_host=udp_host,
        default_udp_port=udp_port,
    )
    network_cards = merge_discovered_network_cards(
        network_cards,
        network_scan_results or [],
        default_udp_port=udp_port,
    )
    try:
        from network_scanner import list_host_ipv4_interfaces

        network_cards = merge_host_interface_cards(
            network_cards,
            list_host_ipv4_interfaces(),
            default_udp_port=udp_port,
        )
    except Exception:
        pass
    try:
        network_cards = merge_tailscale_bind_cards(
            network_cards,
            default_udp_port=udp_port,
        )
    except Exception:
        pass
    errors: list[str] = []
    for dev in serial_devices:
        if dev.status == "port_busy":
            errors.append(f"{dev.port} is in use by another program")
    for card in network_cards:
        if card.status == "port_busy":
            errors.append(f"UDP port {card.port} in use on {card.host}")
    scan_note = ""
    if network_scan_results is not None:
        n = len([r for r in network_scan_results if r])
        scan_note = f"LAN scan: {n} host(s)" if n else "LAN scan: no extra hosts"
    return (
        DiscoverySnapshot(
            mono_ts=time.monotonic(),
            serial_devices=serial_devices,
            network_cards=network_cards,
            errors=errors,
            scan_note=scan_note,
        ),
        counts,
    )
