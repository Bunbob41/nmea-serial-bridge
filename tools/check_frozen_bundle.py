#!/usr/bin/env python3
"""Verify PyInstaller dist includes helpers, web stack, and dashboard static assets."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.frozen_bundle_manifest import (  # noqa: E402
    FROZEN_HELPER_FILES,
    FROZEN_PYTHON_PACKAGES,
    FROZEN_STATIC_FILES,
)


def _internal_root(dist: Path) -> Path:
    internal = dist / "_internal"
    return internal if internal.is_dir() else dist


def check_frozen_bundle(dist: Path) -> list[str]:
    internal = _internal_root(dist)
    errors: list[str] = []
    if not internal.is_dir():
        return [f"missing dist folder: {internal}"]

    for rel in FROZEN_HELPER_FILES:
        if not (internal / rel).is_file():
            errors.append(f"missing helper: {rel}")

    for rel in FROZEN_STATIC_FILES:
        if not (internal / rel).is_file():
            errors.append(f"missing static: {rel}")

    for pkg in FROZEN_PYTHON_PACKAGES:
        if not any(internal.rglob(f"{pkg}/__init__.py")) and not any(
            internal.rglob(f"{pkg}/*.py")
        ):
            errors.append(f"missing python package: {pkg}")

    return errors


def main() -> int:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/serial-link")
    errors = check_frozen_bundle(dist)
    if errors:
        for line in errors:
            print(f"[check_frozen_bundle] FAIL {line}", file=sys.stderr)
        return 1
    print(f"[check_frozen_bundle] OK under {_internal_root(dist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
