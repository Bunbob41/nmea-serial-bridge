#!/usr/bin/env python3
"""Serial Link headless service — bridge + web dashboard (no PySide6 GUI)."""
from __future__ import annotations

import argparse
import signal
import sys
import threading
from typing import Optional

from headless_facade import HeadlessBridgeFacade
from web_facade_types import WebConfigPayload


def _default_serial() -> str:
    if sys.platform == "win32":
        return "COM7"
    return "/dev/ttyUSB0"


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Serial Link headless bridge with web dashboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--serial", "--com", dest="serial", default=_default_serial())
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
        help="Listen on all interfaces (0.0.0.0) for phone/LAN dashboard access",
    )
    p.add_argument("--token", default="", help="Optional API token (required when --lan-bind)")
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
        if token:
            prefs["token"] = token
        save_web_ui_prefs(prefs)
    except Exception:
        pass


def run_headless(
    args: argparse.Namespace,
    *,
    block: bool = True,
    stop_event: Optional[threading.Event] = None,
) -> int:
    from version import __version__
    from web_api import create_app
    from web_server import WebServerThread, port_is_free

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
    if lan_bind and not token:
        print("[serial_link_headless] Warning: --lan-bind without --token exposes an open API.")
    _seed_web_prefs(
        host=str(args.web_host),
        port=int(args.web_port),
        lan_bind=lan_bind,
        token=token or "",
    )
    if not port_is_free(int(args.web_port), lan_bind=lan_bind, host=str(args.web_host)):
        print(f"[serial_link_headless] Web port {args.web_port} is already in use.")
        return 2
    app = create_app(facade, version=__version__, lan_token=token if lan_bind else None)
    server = WebServerThread()
    try:
        server.start(
            app,
            host=str(args.web_host),
            port=int(args.web_port),
            lan_bind=lan_bind,
        )
    except Exception as exc:
        print(f"[serial_link_headless] Web server failed: {exc}")
        return 1
    bind_note = "LAN" if lan_bind else "localhost"
    print(
        f"[serial_link_headless] v{__version__} — dashboard ({bind_note}): "
        f"http://127.0.0.1:{int(args.web_port)}/"
    )
    print(
        f"[serial_link_headless] serial={config.com_port} @ {config.baud} "
        f"network={config.network_mode}"
    )
    if args.start_bridge:
        result = facade.request_start()
        if not result.ok:
            print(f"[serial_link_headless] Auto-start failed: {result.message}")
            server.stop()
            return 1
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
    args = parser.parse_args(argv)
    raise SystemExit(run_headless(args))


if __name__ == "__main__":
    main()
