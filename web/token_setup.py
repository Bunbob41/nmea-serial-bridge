"""Dashboard setup links — URL fragment carries API token across devices."""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote, unquote


def normalize_base_url(base: str) -> str:
    """Ensure http(s) base without trailing slash."""
    b = (base or "").strip().rstrip("/")
    if not b:
        return ""
    if "://" not in b:
        b = "http://" + b
    return b


def build_setup_url(base_url: str, token: str) -> str:
    """One-tap onboarding: open this URL on a device to save the API token."""
    base = normalize_base_url(base_url)
    t = quote((token or "").strip(), safe="")
    return f"{base}/#bridge-token={t}"


def parse_token_from_text(text: str) -> Optional[str]:
    """Extract API token from a setup link, URL fragment, or raw pasted token."""
    s = (text or "").strip()
    if not s:
        return None
    if "bridge-token=" in s:
        frag = s.split("#", 1)[1] if "#" in s else s
        for part in frag.split("&"):
            if part.startswith("bridge-token="):
                return unquote(part.split("=", 1)[1])
        m = frag.split("bridge-token=", 1)
        if len(m) > 1:
            return unquote(m[1].split("&", 1)[0])
    if len(s) >= 20 and " " not in s and "\n" not in s and "\t" not in s:
        return s
    return None
