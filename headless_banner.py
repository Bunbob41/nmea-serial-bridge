"""Startup banner for headless CLI / journal."""
from __future__ import annotations

from headless_config import HeadlessRuntimeConfig
from web.token_setup import build_setup_url


def print_headless_startup_banner(
    *,
    version: str,
    cfg: HeadlessRuntimeConfig,
    bridge_running: bool,
) -> None:
    prefix = "[serial_link_headless]"
    print(f"{prefix} Serial Link headless v{version}")
    if cfg.config_path is not None:
        print(f"{prefix}   Config:     {cfg.config_path}")
    print(
        f"{prefix}   Serial:     {cfg.serial} @ {cfg.baud}  "
        f"nmea={cfg.nmea_mode}"
    )
    print(
        f"{prefix}   Network:    {cfg.network_mode} "
        f"{cfg.udp_host}:{cfg.udp_port}"
    )
    local_url = f"http://127.0.0.1:{cfg.web_port}/"
    print(f"{prefix}   Dashboard:  {local_url}", end="")
    if cfg.lan_bind:
        print("  (local probe)")
    else:
        print("  (localhost — no API token)")
    if cfg.lan_bind:
        try:
            from web.phone_url import suggest_phone_base_urls

            remote_urls = suggest_phone_base_urls(cfg.web_port)
        except Exception:
            remote_urls = []
        if remote_urls:
            print(f"{prefix}   Tailnet/LAN:  {remote_urls[0]}")
            for url in remote_urls[1:3]:
                print(f"{prefix}                 {url}")
        else:
            print(
                f"{prefix}   Tailnet/LAN:  http://<this-host-ip>:{cfg.web_port}/ "
                "(run: tailscale ip -4)"
            )
        print(f"{prefix}   API token:    {cfg.token}")
        setup = build_setup_url(
            remote_urls[0] if remote_urls else local_url,
            cfg.token,
        )
        print(f"{prefix}   Setup link:   {setup}")
    state = "RUNNING" if bridge_running else "STOPPED"
    hint = "open dashboard to review settings, then Start" if not bridge_running else "bridge active"
    print(f"{prefix}   Bridge:       {state} — {hint}")
