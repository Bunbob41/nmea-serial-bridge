"""Build SerialNetBridge from StreamDefinition."""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

from bridge_core import NetMode, SerialMirrorConfig, SerialNetBridge
from core.fleet.config import StreamDefinition, normalize_serial_mirror_ports
from nmea_codec import NmeaMode


def _nmea_mode(value: str) -> NmeaMode:
    key = (value or "passthrough").strip().lower()
    return {
        "passthrough": NmeaMode.PASSTHROUGH,
        "strict": NmeaMode.STRICT,
        "raw": NmeaMode.RAW,
    }.get(key, NmeaMode.PASSTHROUGH)


def make_bridge_builder(
    stream: StreamDefinition,
    *,
    ui_log: Callable[[str], None],
    status_cb: Callable[[str, str], None],
    stats_cb: Callable[[dict], None],
    ui_log_verbose: Callable[[], bool] | None = None,
    local_backup_dir: Optional[str] = None,
):
    mode = NetMode(stream.net_mode)
    nmea = _nmea_mode(stream.nmea_mode)
    verbose = ui_log_verbose or (lambda: False)

    def build(loop: asyncio.AbstractEventLoop) -> SerialNetBridge:
        com = stream.com.strip()
        mirror_ports = tuple(
            normalize_serial_mirror_ports(stream.serial_mirror_ports, primary=com)
        )
        serial_mirror = None
        if mirror_ports:
            serial_mirror = SerialMirrorConfig(
                ports=mirror_ports,
                include_device_tx=bool(stream.serial_mirror_device_tx),
            )
        common = dict(
            loop=loop,
            ui_log=ui_log,
            ui_log_verbose=verbose,
            status_cb=status_cb,
            stats_cb=stats_cb,
            nmea_mode=nmea,
            udp_fanout=bool(stream.udp_fanout),
            enable_local_backup=bool(stream.local_backup),
            local_backup_dir=local_backup_dir,
            serial_auto_reconnect=True,
            serial_mirror=serial_mirror,
        )
        baud = int(stream.baud)
        if mode == NetMode.TCP_SERVER:
            return SerialNetBridge(
                com,
                baud,
                mode,
                tcp_bind_host=stream.tcp_host.strip() or "0.0.0.0",
                tcp_bind_port=int(stream.tcp_port),
                **common,
            )
        if mode == NetMode.TCP_CLIENT:
            return SerialNetBridge(
                com,
                baud,
                mode,
                tcp_client_host=stream.tcp_client_host.strip() or "127.0.0.1",
                tcp_client_port=int(stream.tcp_client_port),
                **common,
            )
        if mode == NetMode.UDP_REMOTE:
            return SerialNetBridge(
                com,
                baud,
                mode,
                udp_remote=(
                    stream.udp_remote_host.strip() or "127.0.0.1",
                    int(stream.udp_remote_port),
                ),
                **common,
            )
        host = stream.udp_host.strip() or "0.0.0.0"
        return SerialNetBridge(
            com,
            baud,
            mode,
            udp_listen=(host, int(stream.udp_port)),
            **common,
        )

    return build
