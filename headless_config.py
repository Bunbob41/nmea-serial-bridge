"""Site config file + env resolution for Linux headless (Phase A)."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

def default_serial() -> str:
    return "/dev/ttyUSB0" if sys.platform != "win32" else "COM7"


_CONFIG_SEARCH = (
    Path("/etc/serial-link/bridge.json"),
    Path.home() / ".config" / "serial-link" / "bridge.json",
)



def _deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _pick(data: dict[str, Any], flat: str, *nested: str, default: Any = None) -> Any:
    if flat in data and data[flat] is not None:
        return data[flat]
    return _deep_get(data, *nested, default=default)


def load_site_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a JSON object: {path}")
    return data


def discover_config_path(explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        return Path(explicit).expanduser()
    for env_key in ("SERIAL_LINK_CONFIG", "CONFIG_FILE"):
        raw = (os.environ.get(env_key) or "").strip()
        if raw:
            return Path(raw).expanduser()
    for candidate in _CONFIG_SEARCH:
        if candidate.is_file():
            return candidate
    return None


def _env_bool(name: str) -> Optional[bool]:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    return int(raw)


def _env_str(name: str) -> Optional[str]:
    raw = os.environ.get(name)
    if raw is None:
        return None
    text = str(raw).strip()
    return text if text else None


@dataclass
class HeadlessRuntimeConfig:
    config_path: Optional[Path]
    serial: str
    baud: int
    udp_host: str
    udp_port: int
    network_mode: str
    remote_host: str
    remote_port: int
    nmea_mode: str
    web_host: str
    web_port: int
    lan_bind: bool
    token: str
    start_bridge: bool

    def as_namespace(self) -> argparse.Namespace:
        return argparse.Namespace(
            config=str(self.config_path) if self.config_path else None,
            serial=self.serial,
            baud=self.baud,
            udp_host=self.udp_host,
            udp_port=self.udp_port,
            network_mode=self.network_mode,
            remote_host=self.remote_host,
            remote_port=self.remote_port,
            nmea_mode=self.nmea_mode,
            web_host=self.web_host,
            web_port=self.web_port,
            lan_bind=self.lan_bind,
            token=self.token,
            start_bridge=self.start_bridge,
        )


def _base_from_defaults() -> HeadlessRuntimeConfig:
    return HeadlessRuntimeConfig(
        config_path=None,
        serial=default_serial(),
        baud=115200,
        udp_host="0.0.0.0",
        udp_port=10110,
        network_mode="udp_listen",
        remote_host="",
        remote_port=10110,
        nmea_mode="passthrough",
        web_host="127.0.0.1",
        web_port=8765,
        lan_bind=False,
        token="",
        start_bridge=False,
    )


def _apply_file(cfg: HeadlessRuntimeConfig, data: dict[str, Any], path: Path) -> HeadlessRuntimeConfig:
    port_val = _deep_get(data, "serial", "port")
    if port_val is not None:
        serial = str(port_val).strip()
    elif isinstance(data.get("serial"), str):
        serial = str(data["serial"]).strip()
    else:
        serial = cfg.serial
    baud = int(_pick(data, "baud", "serial", "baud", default=cfg.baud))
    udp_host = str(
        _pick(data, "udp_host", "network", "udp_host", default=cfg.udp_host) or cfg.udp_host
    ).strip()
    udp_port = int(_pick(data, "udp_port", "network", "udp_port", default=cfg.udp_port))
    network_mode = str(
        _pick(data, "network_mode", "network", "mode", default=cfg.network_mode) or cfg.network_mode
    ).strip()
    remote_host = str(
        _pick(data, "remote_host", "network", "remote_host", default=cfg.remote_host) or ""
    ).strip()
    remote_port = int(_pick(data, "remote_port", "network", "remote_port", default=cfg.remote_port))
    nmea_mode = str(_pick(data, "nmea_mode", default=cfg.nmea_mode) or cfg.nmea_mode).strip()
    web_host = str(_pick(data, "web_host", "web", "host", default=cfg.web_host) or cfg.web_host).strip()
    web_port = int(_pick(data, "web_port", "web", "port", default=cfg.web_port))
    lan_bind = bool(_pick(data, "lan_bind", "web", "lan_bind", default=cfg.lan_bind))
    token = str(_pick(data, "token", "web", "token", default=cfg.token) or "").strip()
    autostart = bool(_pick(data, "start_bridge", "bridge", "autostart", default=cfg.start_bridge))
    return HeadlessRuntimeConfig(
        config_path=path,
        serial=serial,
        baud=baud,
        udp_host=udp_host or "0.0.0.0",
        udp_port=udp_port,
        network_mode=network_mode,
        remote_host=remote_host,
        remote_port=remote_port,
        nmea_mode=nmea_mode,
        web_host=web_host or "127.0.0.1",
        web_port=web_port,
        lan_bind=lan_bind,
        token=token,
        start_bridge=autostart,
    )


def _apply_env(cfg: HeadlessRuntimeConfig) -> HeadlessRuntimeConfig:
    serial = _env_str("SERIAL_LINK_SERIAL") or cfg.serial
    baud = _env_int("SERIAL_LINK_BAUD")
    udp_host = _env_str("SERIAL_LINK_UDP_HOST")
    udp_port = _env_int("SERIAL_LINK_UDP_PORT")
    network_mode = _env_str("SERIAL_LINK_NETWORK_MODE")
    remote_host = _env_str("SERIAL_LINK_REMOTE_HOST")
    remote_port = _env_int("SERIAL_LINK_REMOTE_PORT")
    nmea_mode = _env_str("SERIAL_LINK_NMEA_MODE")
    web_host = _env_str("SERIAL_LINK_WEB_HOST")
    web_port = _env_int("SERIAL_LINK_WEB_PORT")
    lan_bind = _env_bool("SERIAL_LINK_LAN_BIND")
    token = _env_str("SERIAL_LINK_TOKEN")
    start_bridge = _env_bool("SERIAL_LINK_AUTOSTART")
    return HeadlessRuntimeConfig(
        config_path=cfg.config_path,
        serial=serial,
        baud=baud if baud is not None else cfg.baud,
        udp_host=udp_host if udp_host is not None else cfg.udp_host,
        udp_port=udp_port if udp_port is not None else cfg.udp_port,
        network_mode=network_mode if network_mode is not None else cfg.network_mode,
        remote_host=remote_host if remote_host is not None else cfg.remote_host,
        remote_port=remote_port if remote_port is not None else cfg.remote_port,
        nmea_mode=nmea_mode if nmea_mode is not None else cfg.nmea_mode,
        web_host=web_host if web_host is not None else cfg.web_host,
        web_port=web_port if web_port is not None else cfg.web_port,
        lan_bind=lan_bind if lan_bind is not None else cfg.lan_bind,
        token=token if token is not None else cfg.token,
        start_bridge=start_bridge if start_bridge is not None else cfg.start_bridge,
    )


def _cli_provided(argv: list[str], flag: str) -> bool:
    prefixes = (f"{flag}=", flag)
    for arg in argv:
        for prefix in prefixes:
            if arg == flag or arg.startswith(f"{flag}="):
                return True
    return False


def _apply_cli(cfg: HeadlessRuntimeConfig, args: argparse.Namespace, argv: list[str]) -> HeadlessRuntimeConfig:
    serial = args.serial if _cli_provided(argv, "--serial") or _cli_provided(argv, "--com") else cfg.serial
    baud = args.baud if _cli_provided(argv, "--baud") else cfg.baud
    udp_host = args.udp_host if _cli_provided(argv, "--udp-host") else cfg.udp_host
    udp_port = args.udp_port if _cli_provided(argv, "--udp-port") else cfg.udp_port
    network_mode = args.network_mode if _cli_provided(argv, "--network-mode") else cfg.network_mode
    remote_host = args.remote_host if _cli_provided(argv, "--remote-host") else cfg.remote_host
    remote_port = args.remote_port if _cli_provided(argv, "--remote-port") else cfg.remote_port
    nmea_mode = args.nmea_mode if _cli_provided(argv, "--nmea-mode") else cfg.nmea_mode
    web_host = args.web_host if _cli_provided(argv, "--web-host") else cfg.web_host
    web_port = args.web_port if _cli_provided(argv, "--web-port") else cfg.web_port
    lan_bind = args.lan_bind if _cli_provided(argv, "--lan-bind") else cfg.lan_bind
    token = args.token if _cli_provided(argv, "--token") else cfg.token
    start_bridge = args.start_bridge if _cli_provided(argv, "--start-bridge") else cfg.start_bridge
    config_path = cfg.config_path
    if _cli_provided(argv, "--config"):
        config_path = Path(str(args.config)).expanduser()
    return HeadlessRuntimeConfig(
        config_path=config_path,
        serial=str(serial).strip(),
        baud=int(baud),
        udp_host=str(udp_host).strip() or "0.0.0.0",
        udp_port=int(udp_port),
        network_mode=str(network_mode).strip(),
        remote_host=str(remote_host).strip(),
        remote_port=int(remote_port),
        nmea_mode=str(nmea_mode).strip(),
        web_host=str(web_host).strip() or "127.0.0.1",
        web_port=int(web_port),
        lan_bind=bool(lan_bind),
        token=str(token or "").strip(),
        start_bridge=bool(start_bridge),
    )


def ensure_lan_token(cfg: HeadlessRuntimeConfig) -> HeadlessRuntimeConfig:
    if not cfg.lan_bind:
        return cfg
    if cfg.token:
        return cfg
    token = secrets.token_urlsafe(24)
    return HeadlessRuntimeConfig(
        config_path=cfg.config_path,
        serial=cfg.serial,
        baud=cfg.baud,
        udp_host=cfg.udp_host,
        udp_port=cfg.udp_port,
        network_mode=cfg.network_mode,
        remote_host=cfg.remote_host,
        remote_port=cfg.remote_port,
        nmea_mode=cfg.nmea_mode,
        web_host=cfg.web_host,
        web_port=cfg.web_port,
        lan_bind=True,
        token=token,
        start_bridge=cfg.start_bridge,
    )


def resolve_headless_config(
    args: argparse.Namespace,
    *,
    argv: Optional[list[str]] = None,
) -> HeadlessRuntimeConfig:
    argv = list(argv if argv is not None else sys.argv[1:])
    cfg = _base_from_defaults()
    explicit = str(args.config).strip() if getattr(args, "config", None) else None
    if explicit:
        path = Path(explicit).expanduser()
        cfg = _apply_file(cfg, load_site_config(path), path)
    else:
        discovered = discover_config_path()
        if discovered is not None:
            cfg = _apply_file(cfg, load_site_config(discovered), discovered)
    cfg = _apply_env(cfg)
    cfg = _apply_cli(cfg, args, argv)
    cfg = ensure_lan_token(cfg)
    if cfg.lan_bind and cfg.web_host in ("127.0.0.1", "localhost"):
        cfg = HeadlessRuntimeConfig(
            config_path=cfg.config_path,
            serial=cfg.serial,
            baud=cfg.baud,
            udp_host=cfg.udp_host,
            udp_port=cfg.udp_port,
            network_mode=cfg.network_mode,
            remote_host=cfg.remote_host,
            remote_port=cfg.remote_port,
            nmea_mode=cfg.nmea_mode,
            web_host="0.0.0.0",
            web_port=cfg.web_port,
            lan_bind=True,
            token=cfg.token,
            start_bridge=cfg.start_bridge,
        )
    return cfg


def runtime_to_site_dict(cfg: HeadlessRuntimeConfig) -> dict[str, Any]:
    return {
        "serial": {"port": cfg.serial, "baud": cfg.baud},
        "network": {
            "mode": cfg.network_mode,
            "udp_host": cfg.udp_host,
            "udp_port": cfg.udp_port,
            "remote_host": cfg.remote_host,
            "remote_port": cfg.remote_port,
        },
        "nmea_mode": cfg.nmea_mode,
        "web": {
            "host": cfg.web_host,
            "port": cfg.web_port,
            "lan_bind": cfg.lan_bind,
            **({"token": cfg.token} if cfg.token else {}),
        },
        "bridge": {"autostart": cfg.start_bridge},
    }


def save_site_config(path: Path, cfg: HeadlessRuntimeConfig) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = runtime_to_site_dict(cfg)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
