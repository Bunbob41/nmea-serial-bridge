"""Fleet configuration - load, save, validate."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from bridge_core import SERIAL_MIRROR_MAX_PORTS, NetMode, parse_serial_mirror_ports

FLEET_CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "fleet_config.json"
FLEET_SCHEMA_VERSION = 1
FLEET_MAX_STREAMS = 8
FLEET_UDP_PORT_FIRST = 10111
FLEET_UDP_PORT_LAST = 10118
_LABEL_MAX_LEN = 32

_VALID_NMEA = frozenset({"passthrough", "strict", "raw"})
_VALID_NET = frozenset(m.value for m in NetMode)


_STREAM_CONNECTION_FIELDS: tuple[str, ...] = (
    "com",
    "baud",
    "nmea_mode",
    "net_mode",
    "udp_host",
    "udp_port",
    "udp_remote_host",
    "udp_remote_port",
    "tcp_host",
    "tcp_port",
    "tcp_client_host",
    "tcp_client_port",
    "udp_fanout",
    "local_backup",
    "serial_mirror_ports",
    "serial_mirror_device_tx",
)


FLEET_MAVLINK_MP_UDP_PORT = 14550


def normalize_udp_listen_host(host: str) -> str:
    """Normalize UDP listen bind address for fleet/control comparisons."""
    value = (host or "0.0.0.0").strip() or "0.0.0.0"
    if value in ("*", "::"):
        return "0.0.0.0"
    return value


def udp_listen_hosts_conflict(host_a: str, host_b: str) -> bool:
    """True when two UDP listen binds would claim the same port on this PC."""
    a = normalize_udp_listen_host(host_a)
    b = normalize_udp_listen_host(host_b)
    if a == b:
        return True
    if a == "0.0.0.0" or b == "0.0.0.0":
        return True
    return False


def mavlink_mp_stream(**kwargs: Any) -> StreamDefinition:
    """Preset row: Cube MAVLink COM -> UDP listen for Mission Planner UDP Client."""
    defaults: dict[str, Any] = {
        "label": "MAVLink / MP",
        "nmea_mode": "raw",
        "net_mode": NetMode.UDP_LISTEN.value,
        "udp_host": "0.0.0.0",
        "udp_port": FLEET_MAVLINK_MP_UDP_PORT,
        "udp_fanout": True,
        "baud": 115200,
        "enabled": True,
        "local_backup": False,
    }
    defaults.update(kwargs)
    label = str(defaults.pop("label", "MAVLink / MP"))
    return StreamDefinition.new(label, **defaults)





def normalize_serial_mirror_ports(
    ports: list[str] | tuple[str, ...] | str,
    *,
    primary: str,
) -> list[str]:
    if isinstance(ports, (list, tuple)):
        raw = ",".join(str(p) for p in ports)
    else:
        raw = str(ports or "")
    return list(parse_serial_mirror_ports(raw, primary=primary, max_ports=SERIAL_MIRROR_MAX_PORTS))


def stream_com_ports(stream: StreamDefinition) -> set[str]:
    out = {(stream.com or "").strip().upper()}
    out.discard("")
    for port in stream.serial_mirror_ports or []:
        p = (port or "").strip().upper()
        if p:
            out.add(p)
    return out

def stream_connection_key(stream: StreamDefinition) -> str:
    payload = {k: stream.to_dict().get(k) for k in _STREAM_CONNECTION_FIELDS}
    payload["com"] = (stream.com or "").strip().upper()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass
class StreamDefinition:
    id: str
    label: str
    enabled: bool = True
    primary: bool = False
    com: str = ""
    baud: int = 115200
    nmea_mode: str = "passthrough"
    net_mode: str = NetMode.UDP_LISTEN.value
    udp_host: str = "0.0.0.0"
    udp_port: int = 10110
    udp_remote_host: str = "127.0.0.1"
    udp_remote_port: int = 10110
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 4001
    tcp_client_host: str = "127.0.0.1"
    tcp_client_port: int = 4001
    udp_fanout: bool = True
    local_backup: bool = False
    serial_mirror_ports: list[str] = field(default_factory=list)
    serial_mirror_device_tx: bool = False

    @classmethod
    def new(cls, label: str, **kwargs: Any) -> "StreamDefinition":
        return cls(id=uuid.uuid4().hex[:12], label=label.strip(), **kwargs)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StreamDefinition":
        data = dict(raw)
        data.setdefault("id", uuid.uuid4().hex[:12])
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FleetConfig:
    schema_version: int = FLEET_SCHEMA_VERSION
    auto_start_on_launch: bool = False
    streams: list[StreamDefinition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FleetConfig":
        streams_raw = raw.get("streams") or []
        streams = [
            StreamDefinition.from_dict(s)
            for s in streams_raw
            if isinstance(s, dict)
        ]
        return cls(
            schema_version=int(raw.get("schema_version", FLEET_SCHEMA_VERSION)),
            auto_start_on_launch=bool(raw.get("auto_start_on_launch", False)),
            streams=streams,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "auto_start_on_launch": self.auto_start_on_launch,
            "streams": [s.to_dict() for s in self.streams],
        }

    def primary_stream_id(self) -> Optional[str]:
        for s in self.streams:
            if s.primary:
                return s.id
        return None

    def set_primary(self, stream_id: str) -> None:
        for s in self.streams:
            s.primary = s.id == stream_id

    def stream_by_id(self, stream_id: str) -> Optional[StreamDefinition]:
        for s in self.streams:
            if s.id == stream_id:
                return s
        return None


def default_fleet_config() -> FleetConfig:
    return FleetConfig()


def load_fleet_config(path: Path = FLEET_CONFIG_PATH) -> FleetConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default_fleet_config()
    if not isinstance(raw, dict):
        return default_fleet_config()
    return FleetConfig.from_dict(raw)


def save_fleet_config(config: FleetConfig, path: Path = FLEET_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config.to_dict(), indent=2) + chr(10), encoding="utf-8")
    tmp.replace(path)



def fleet_listen_ports(config: FleetConfig) -> set[int]:
    ports: set[int] = set()
    for stream in config.streams:
        if not stream.enabled or stream.net_mode != NetMode.UDP_LISTEN.value:
            continue
        ports.add(int(stream.udp_port))
    return ports


def suggest_fleet_udp_port(
    config: FleetConfig,
    *,
    reserved_ports: set[int] | None = None,
) -> int:
    used = fleet_listen_ports(config)
    reserved = reserved_ports or set()
    for port in range(FLEET_UDP_PORT_FIRST, FLEET_UDP_PORT_LAST + 1):
        if port not in used and port not in reserved:
            return port
    return FLEET_UDP_PORT_FIRST



def validate_fleet_config_for_start(
    config: FleetConfig,
    *,
    stream_id: str | None = None,
) -> list[str]:
    """Validate only what matters for starting enabled stream(s)."""
    errors: list[str] = []
    if len(config.streams) > FLEET_MAX_STREAMS:
        errors.append(f"Fleet supports at most {FLEET_MAX_STREAMS} streams.")
    if sum(1 for s in config.streams if s.primary) > 1:
        errors.append("At most one stream may be marked Primary.")
    targets = [s for s in config.streams if s.enabled]
    if stream_id is not None:
        targets = [s for s in targets if s.id == stream_id]
    if stream_id is not None and not targets:
        return errors
    seen_com: dict[str, str] = {}
    listen_bindings: list[tuple[str, int, str]] = []
    for stream in targets:
        label = stream.label.strip() or stream.id
        if not stream.label.strip():
            errors.append(f"Stream {stream.id}: label is required.")
        elif len(stream.label.strip()) > _LABEL_MAX_LEN:
            errors.append(f"Stream {label}: label exceeds {_LABEL_MAX_LEN} characters.")
        if stream.nmea_mode not in _VALID_NMEA:
            errors.append(f"Stream {label}: invalid nmea_mode {stream.nmea_mode!r}.")
        if stream.net_mode not in _VALID_NET:
            errors.append(f"Stream {label}: invalid net_mode {stream.net_mode!r}.")
        com = (stream.com or "").strip().upper()
        if not com:
            errors.append(f"Stream {label}: COM port is required.")
        mirror_ports = normalize_serial_mirror_ports(stream.serial_mirror_ports, primary=com)
        if len(mirror_ports) > SERIAL_MIRROR_MAX_PORTS:
            errors.append(f"Stream {label}: at most {SERIAL_MIRROR_MAX_PORTS} serial mirror ports.")
        for mirror in mirror_ports:
            if mirror == com:
                errors.append(f"Stream {label}: mirror port cannot match primary COM.")
            elif mirror in seen_com:
                errors.append(f"Stream {label}: COM {mirror} already used by {seen_com[mirror]}.")
        if com in seen_com:
            errors.append(f"Stream {label}: COM {com} already used by {seen_com[com]}.")
        else:
            seen_com[com] = label
            for mirror in mirror_ports:
                seen_com[mirror] = f"{label} mirror"
        if stream.net_mode == NetMode.UDP_LISTEN.value:
            host = normalize_udp_listen_host(stream.udp_host)
            port = int(stream.udp_port)
            conflict = next(
                (
                    prev_label
                    for prev_host, prev_port, prev_label in listen_bindings
                    if prev_port == port and udp_listen_hosts_conflict(host, prev_host)
                ),
                None,
            )
            if conflict is not None:
                errors.append(
                    f"Stream {label}: UDP listen {host}:{port} "
                    f"conflicts with {conflict} on the same port."
                )
            else:
                listen_bindings.append((host, port, label))
    return errors


def validate_fleet_config(config: FleetConfig) -> list[str]:
    errors: list[str] = []
    if len(config.streams) > FLEET_MAX_STREAMS:
        errors.append(f"Fleet supports at most {FLEET_MAX_STREAMS} streams.")
    if sum(1 for s in config.streams if s.primary) > 1:
        errors.append("At most one stream may be marked Primary.")
    enabled = [s for s in config.streams if s.enabled]
    seen_com: dict[str, str] = {}
    listen_bindings: list[tuple[str, int, str]] = []
    for stream in config.streams:
        label = stream.label.strip() or stream.id
        if stream.enabled:
            if not stream.label.strip():
                errors.append(f"Stream {stream.id}: label is required.")
            elif len(stream.label.strip()) > _LABEL_MAX_LEN:
                errors.append(f"Stream {label}: label exceeds {_LABEL_MAX_LEN} characters.")
            if stream.nmea_mode not in _VALID_NMEA:
                errors.append(f"Stream {label}: invalid nmea_mode {stream.nmea_mode!r}.")
            if stream.net_mode not in _VALID_NET:
                errors.append(f"Stream {label}: invalid net_mode {stream.net_mode!r}.")
        if not stream.enabled:
            continue
        com = (stream.com or "").strip().upper()
        if not com:
            errors.append(f"Stream {label}: COM port is required.")
        mirror_ports = normalize_serial_mirror_ports(stream.serial_mirror_ports, primary=com)
        if len(mirror_ports) > SERIAL_MIRROR_MAX_PORTS:
            errors.append(f"Stream {label}: at most {SERIAL_MIRROR_MAX_PORTS} serial mirror ports.")
        for mirror in mirror_ports:
            if mirror == com:
                errors.append(f"Stream {label}: mirror port cannot match primary COM.")
            elif mirror in seen_com:
                errors.append(f"Stream {label}: COM {mirror} already used by {seen_com[mirror]}.")
        if com in seen_com:
            errors.append(f"Stream {label}: COM {com} already used by {seen_com[com]}.")
        else:
            seen_com[com] = label
            for mirror in mirror_ports:
                seen_com[mirror] = f"{label} mirror"
        if stream.net_mode == NetMode.UDP_LISTEN.value:
            host = normalize_udp_listen_host(stream.udp_host)
            port = int(stream.udp_port)
            conflict = next(
                (
                    prev_label
                    for prev_host, prev_port, prev_label in listen_bindings
                    if prev_port == port and udp_listen_hosts_conflict(host, prev_host)
                ),
                None,
            )
            if conflict is not None:
                errors.append(
                    f"Stream {label}: UDP listen {host}:{port} "
                    f"conflicts with {conflict} on the same port."
                )
            else:
                listen_bindings.append((host, port, label))
    return errors
