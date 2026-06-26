#!/usr/bin/env python3
"""Serial Link headless service — bridge + web dashboard (no PySide6 GUI)."""
from __future__ import annotations

import argparse
import signal
import sys
import threading
from typing import Optional

from headless_banner import print_headless_startup_banner
from headless_config import default_serial, resolve_headless_config
from headless_facade import HeadlessBridgeFacade
from web_facade_types import WebConfigPayload


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Serial Link headless bridge with web dashboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--config",
        default=None,
        help="Site config JSON (also SERIAL_LINK_CONFIG, CONFIG_FILE, or ~/.config/serial-link/bridge.json)",
    )
    p.add_argument("--serial", "--com", dest="serial", default=default_serial())
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--udp-host", default="0.0.0.0", help="UDP listen bind host")
    p.add_argument("--udp-port", type=int, default=10110)
    p.add_argument(
        "--network-mode",
        choices=("udp_listen", "udp_remote", "tcp_client", "tcp_server"),
        default="udp_listen",
    )
    p.add_argument("--remote-host", default="", help="Peer host (remote/tcp modes)")
    p.add_argument("--remote-port", type=int, default=10110)
    p.add_argument(
        "--nmea-mode",
        choices=("passthrough", "strict", "raw"),
        default="passthrough",
    )
    p.add_argument("--web-host", default="127.0.0.1", help="Web dashboard bind host")
    p.add_argument("--web-port", type=int, default=8765)
    p.add_argument(
        "--lan-bind",
        action="store_true",
        help="Listen on all interfaces (0.0.0.0) for phone/LAN/tailnet dashboard access",
    )
    p.add_argument(
        "--token",
        default="",
        help="API token for remote dashboard (auto-generated when --lan-bind and omitted)",
    )
    p.add_argument(
        "--start-bridge",
        action="store_true",
        help="Start bridging immediately (default: stopped until dashboard Start)",
    )
    return p


def _seed_web_prefs(*, host: str, port: int, lan_bind: bool, token: str) -> None:
    try:
        from ui.ui_prefs import load_web_ui_prefs, save_web_ui_prefs

        prefs = load_web_ui_prefs()
        prefs["enabled"] = True
        prefs["host"] = host
        prefs["port"] = int(port)
        prefs["lan_bind"] = bool(lan_bind)
        if lan_bind and token:
            prefs["token"] = token
        elif not lan_bind:
            prefs["lan_bind"] = False
        save_web_ui_prefs(prefs)
    except Exception:
        pass


def run_headless(
    args: argparse.Namespace,
    *,
    block: bool = True,
    stop_event: Optional[threading.Event] = None,
    argv: Optional[list[str]] = None,
) -> int:
    from version import __version__
    from web_api import create_app
    from web_server import WebServerThread, port_is_free

    cfg = resolve_headless_config(args, argv=argv)
    args = cfg.as_namespace()

    config = WebConfigPayload(
        com_port=str(args.serial).strip(),
        baud=int(args.baud),
        udp_listen_host=str(args.udp_host).strip() or "0.0.0.0",
        udp_listen_port=int(args.udp_port),
        nmea_mode=str(args.nmea_mode),
        network_mode=str(args.network_mode),
        remote_host=str(args.remote_host).strip(),
        remote_port=int(args.remote_port),
    )
    facade = HeadlessBridgeFacade(config)
    lan_bind = bool(args.lan_bind)
    token = str(args.token).strip() or None
    web_host = str(args.web_host)
    facade.set_site_context(
        config_path=cfg.config_path,
        web_port=int(cfg.web_port),
        lan_bind=lan_bind,
        token=token or "",
        autostart=bool(args.start_bridge),
    )
    _seed_web_prefs(
        host=web_host,
        port=int(args.web_port),
        lan_bind=lan_bind,
        token=token or "",
    )
    if not port_is_free(int(args.web_port), lan_bind=lan_bind, host=web_host):
        print(f"[serial_link_headless] Web port {args.web_port} is already in use.")
        return 2
    app = create_app(
        facade,
        version=__version__,
        lan_token=token if lan_bind else None,
        headless=True,
        config_path=str(cfg.config_path) if cfg.config_path else None,
        config_writable=cfg.config_path is not None,
    )
    server = WebServerThread()
    try:
        server.start(
            app,
            host=web_host,
            port=int(args.web_port),
            lan_bind=lan_bind,
        )
    except Exception as exc:
        print(f"[serial_link_headless] Web server failed: {exc}")
        return 1

    bridge_running = False
    if args.start_bridge:
        result = facade.request_start()
        if not result.ok:
            print(f"[serial_link_headless] Auto-start failed: {result.message}")
            server.stop()
            return 1
        bridge_running = True

    print_headless_startup_banner(
        version=__version__,
        cfg=cfg,
        bridge_running=bridge_running,
    )

    if not block:
        return 0
    done = stop_event or threading.Event()

    def _handle_signal(_signum: int, _frame: object) -> None:
        done.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        done.wait()
    finally:
        facade.shutdown()
        server.stop()
    return 0


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_arg_parser()
    argv_list = list(argv if argv is not None else sys.argv[1:])
    args = parser.parse_args(argv_list)
    raise SystemExit(run_headless(args, argv=argv_list))


if __name__ == "__main__":
    main()
