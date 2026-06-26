"""Shared Web control-plane DTOs (no Qt). Used by desktop and headless facades."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional

WEB_LOG_MAX_LINES = 400


@dataclass
class WebSessionState:
    running: bool = False
    com_port: str = ""
    configured_com_port: str = ""
    baud: int = 115200
    udp_listen_host: str = "0.0.0.0"
    udp_listen_port: int = 10110
    nmea_mode: str = "passthrough"
    hz_net_to_com: Optional[float] = None
    hz_com_to_net: Optional[float] = None
    hz_inject: Optional[float] = None
    drops: int = 0
    rejects: int = 0
    drops_net_to_com: int = 0
    drops_com_to_net: int = 0
    rejects_net_to_com: int = 0
    rejects_com_to_net: int = 0
    queue_net_to_com: int = 0
    queue_com_to_net: int = 0
    lines_net_to_com: int = 0
    lines_com_to_net: int = 0
    transport_ok: bool = True
    gnss_summary: str = ""
    gnss_fix: str = ""
    gnss_sats: Optional[int] = None
    gnss_hdop: Optional[float] = None
    gnss_stale: bool = False
    gnss_quality: Optional[int] = None
    gnss_stream_idle: bool = False
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    position_lat_ddm: str = ""
    position_lon_ddm: str = ""
    position_source: str = ""
    position_stale: bool = True
    last_error: Optional[str] = None
    com_port_available: Optional[bool] = None
    com_port_lock_reason: str = ""
    com_lock_checking: bool = False
    updated_mono: float = 0.0
    session_running_s: float = 0.0
    com_active_total_s: float = 0.0
    last_com_to_net_age_s: Optional[float] = None
    serial_link_state: str = "closed"
    udp_peer_count: int = 0
    udp_peer_newest_in_s: Optional[float] = None
    udp_peer_stale: bool = False
    udp_peer_details: list[dict[str, Any]] = field(default_factory=list)
    net_mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebConfigPayload:
    com_port: str = ""
    baud: int = 115200
    udp_listen_host: str = "0.0.0.0"
    udp_listen_port: int = 10110
    nmea_mode: str = "passthrough"
    hub_device_id: Optional[str] = None
    manual_override: bool = False
    network_mode: str = "udp_listen"
    remote_host: str = ""
    remote_port: int = 10110

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebCommandResult:
    ok: bool
    message: str
    error_code: Optional[str] = None
    state: str = "stopped"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "error_code": self.error_code,
            "state": self.state,
        }


@dataclass
class SerialDeviceDto:
    device_id: str
    port: str
    description: str
    manufacturer: str
    match_keyword: str
    status: str  # available | stale | in_use

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkCardDto:
    device_id: str
    label: str
    mode_hint: str
    host: str
    port: int
    port_available: bool
    peer_count: int
    status: str  # ready | port_busy | running
    discovery_source: str = "passive"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebDiscoveryPayload:
    updated_mono: float = 0.0
    scan_note: str = ""
    scan_busy: bool = False
    serial_devices: List[Any] = field(default_factory=list)
    network_cards: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "updated_mono": self.updated_mono,
            "scan_note": self.scan_note,
            "scan_busy": self.scan_busy,
            "serial_devices": [
                (d.to_dict() if hasattr(d, "to_dict") else d) for d in self.serial_devices
            ],
            "network_cards": [
                (c.to_dict() if hasattr(c, "to_dict") else c) for c in self.network_cards
            ],
            "errors": list(self.errors),
        }


@dataclass
class WebMeta:
    version: str = ""
    lan_bind: bool = False
    token_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebLogLine:
    seq: int
    text: str
    kind: str
    mono: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebLogPayload:
    lines: List[WebLogLine] = field(default_factory=list)
    latest_seq: int = 0
    paused: bool = False
    paused_dropped: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lines": [ln.to_dict() for ln in self.lines],
            "latest_seq": self.latest_seq,
            "paused": self.paused,
            "paused_dropped": self.paused_dropped,
        }


def classify_web_log_line(text: str) -> str:
    """Lightweight tag for dashboard styling (not full desktop log filters)."""
    t = (text or "").strip()
    low = t.lower()
    if any(x in low for x in ("drop", "reject", "error", "fail", "cannot open", "timed out")):
        return "warn"
    if "→" in t or "n→s" in t or "s→n" in t or "| gps=" in t:
        return "traffic"
    if t.startswith("["):
        return "event"
    return "info"
