#!/usr/bin/env python3
"""Verify a PyInstaller dist folder includes Web API deps and dashboard static files."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/serial-link")
    internal = root / "_internal"
    if not internal.is_dir():
        internal = root
    errors: list[str] = []
    static = internal / "web" / "static" / "index.html"
    if not static.is_file():
        errors.append(f"missing dashboard static: {static}")
    for pkg in ("fastapi", "uvicorn"):
        if not any(internal.rglob(f"{pkg}/__init__.py")) and not any(
            internal.rglob(f"{pkg}/*.py")
        ):
            errors.append(f"missing packaged module tree: {pkg}")
    if errors:
        for line in errors:
            print(f"[check_frozen_web] FAIL {line}", file=sys.stderr)
        return 1
    print(f"[check_frozen_web] OK under {internal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
