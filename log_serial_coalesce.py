"""Serial COM write-timeout log coalescing (bridge engine + GUI live log share rules)."""
from __future__ import annotations

import time
from typing import Optional, Tuple

# C0 controls (especially BEL 0x07) can trigger Windows beeps when shown in text views.
_UI_SAFE_TRANSLATION = {ord(ch): " " for ch in map(chr, range(32)) if ch not in "\n\t\r"}


def ui_safe_text(text: str) -> str:
    """Strip control characters before showing text in the Qt log or status UI."""
    if not text:
        return ""
    return text.translate(_UI_SAFE_TRANSLATION)


def serial_timeout_line_suppress(
    last: Optional[str],
    last_mono: float,
    txt: str,
    now: Optional[float] = None,
    window_s: float = 2.5,
) -> Tuple[bool, Optional[str], float]:
    """Return ``(suppress_ui_log, new_last, new_mono)`` for duplicate timeout lines."""
    t = time.monotonic() if now is None else now
    if "Serial " not in txt or "timed out (open/write)" not in txt:
        return False, last, last_mono
    if last == txt and (t - last_mono) < window_s:
        return True, last, last_mono
    return False, txt, t
