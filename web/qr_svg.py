"""Minimal fallback QR SVG (text payload) when qrcode package is not installed."""
from __future__ import annotations

import html


def token_to_svg(token: str, *, size: int = 200) -> str:
    """Non-scannable fallback: large monospace token for manual entry."""
    safe = html.escape(token)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <rect width="100%" height="100%" fill="#fff"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
        font-family="monospace" font-size="10" fill="#000">{safe}</text>
</svg>"""
