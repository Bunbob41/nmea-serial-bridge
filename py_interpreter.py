"""Pick ``python.exe`` for subprocesses when the app was started with ``pythonw.exe`` (Windows GUI)."""
from __future__ import annotations

import sys
from pathlib import Path


def cli_python_executable() -> str:
    """Interpreter to use for CLI subprocesses (unittest, verify scripts, etc.)."""
    p = Path(sys.executable).resolve()
    if p.suffix.lower() == ".exe" and p.stem.lower() == "pythonw":
        alt = p.with_name("python.exe")
        if alt.is_file():
            return str(alt)
    return str(p)
