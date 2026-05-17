"""DEPRECATED — ui/mixin.py is maintained by hand.

This generator required _mixin_body.txt, which is not shipped. Do not use in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    body_path = Path("_mixin_body.txt")
    if not body_path.is_file():
        print("_gen_mixin.py: deprecated; edit ui/mixin.py directly.", file=sys.stderr)
        raise SystemExit(1)
    body = body_path.read_text(encoding="utf-8")
    idx = body.find("\ndef main()")
    if idx >= 0:
        body = body[:idx]
    header = '# ui/mixin.py — bridge start/stop, logging, validation (shared by all UIs)\n'
    Path("ui/mixin.py").write_text(header + body, encoding="utf-8")
    print("Wrote ui/mixin.py")
