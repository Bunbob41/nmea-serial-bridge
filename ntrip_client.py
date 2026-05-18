"""Minimal NTRIP v1 client — RTCM stream for serial correction injection."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class NtripConfig:
    host: str
    port: int
    mountpoint: str
    username: str = ""
    password: str = ""
    use_tls: bool = False

    @property
    def enabled(self) -> bool:
        return bool(self.host.strip() and self.mountpoint.strip())


def build_ntrip_request(cfg: NtripConfig) -> bytes:
    mp = cfg.mountpoint.strip().lstrip("/")
    lines = [
        f"GET /{mp} HTTP/1.0",
        "User-Agent: NMEA-Serial-Bridge/1.0",
        "Accept: */*",
        "Connection: close",
    ]
    if cfg.username or cfg.password:
        token = base64.b64encode(f"{cfg.username}:{cfg.password}".encode("utf-8")).decode("ascii")
        lines.append(f"Authorization: Basic {token}")
    lines.extend(["", ""])
    return "\r\n".join(lines).encode("ascii")


def parse_caster_host(text: str, default_port: int = 2101) -> tuple[str, int]:
    raw = text.strip()
    if not raw:
        return "", default_port
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    host = (parsed.hostname or "").strip()
    port = parsed.port or default_port
    return host, int(port)


async def run_ntrip_forwarder(
    cfg: NtripConfig,
    on_chunk: Callable[[bytes], Awaitable[None]],
    on_log: Callable[[str], None],
    running: Callable[[], bool],
    *,
    reconnect_s: float = 5.0,
) -> None:
    """Connect to caster and forward RTCM chunks until ``running()`` is false."""
    if not cfg.enabled:
        return
    req = build_ntrip_request(cfg)
    while running():
        writer: asyncio.StreamWriter | None = None
        try:
            on_log(
                f"NTRIP: connecting {cfg.host}:{cfg.port} mount {cfg.mountpoint.strip().lstrip('/')}"
            )
            reader, writer = await asyncio.open_connection(cfg.host, cfg.port, ssl=cfg.use_tls)
            writer.write(req)
            await writer.drain()
            header, initial = await _read_http_header(reader)
            if not _header_ok(header):
                on_log(
                    f"NTRIP: caster rejected - "
                    f"{header.splitlines()[0] if header else 'no response'}"
                )
                await asyncio.sleep(reconnect_s)
                continue
            on_log("NTRIP: streaming corrections (RTCM -> COM)")
            if initial:
                await on_chunk(initial)
            while running():
                chunk = await reader.read(4096)
                if not chunk:
                    break
                await on_chunk(chunk)
            on_log("NTRIP: stream ended")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            on_log(f"NTRIP: {exc}")
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
        if running():
            await asyncio.sleep(reconnect_s)


async def _read_http_header(reader: asyncio.StreamReader) -> tuple[str, bytes]:
    """Return (header text, any bytes already read past the header blank line)."""
    buf = bytearray()
    while b"\r\n\r\n" not in buf and len(buf) < 8192:
        part = await reader.read(512)
        if not part:
            break
        buf.extend(part)
    sep = buf.find(b"\r\n\r\n")
    if sep < 0:
        return buf.decode("latin-1", errors="replace"), b""
    header = buf[: sep + 4].decode("latin-1", errors="replace")
    return header, bytes(buf[sep + 4 :])


def _header_ok(header: str) -> bool:
    first = (header.splitlines() or [""])[0].upper()
    return "200" in first and ("OK" in first or "ICY" in first)
