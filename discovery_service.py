"""Connection discovery — serial ports and passive network context (no Qt)."""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
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


@dataclass
class DiscoverySnapshot:
    mono_ts: float = 0.0
    serial_devices: list[SerialDeviceInfo] = field(default_factory=list)
    network_cards: list[NetworkCardInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


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
) -> tuple[DiscoverySnapshot, dict[str, int]]:
    serial_devices, counts = scan_serial_ports(
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
    errors: list[str] = []
    for card in network_cards:
        if card.status == "port_busy":
            errors.append(f"UDP port {card.port} in use on {card.host}")
    return (
        DiscoverySnapshot(
            mono_ts=time.monotonic(),
            serial_devices=serial_devices,
            network_cards=network_cards,
            errors=errors,
        ),
        counts,
    )
