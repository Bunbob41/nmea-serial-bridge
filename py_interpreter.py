"""Pick ``python.exe`` for subprocesses when the app was started with ``pythonw.exe`` (Windows GUI)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def subprocess_no_console_kwargs() -> dict:
    """Extra kwargs for ``subprocess`` calls so GUI-launched scripts do not flash consoles (Windows)."""
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not flag:
        return {}
    return {"creationflags": flag}


def cli_python_executable() -> str:
    """Interpreter to use for CLI subprocesses (unittest, verify scripts, etc.)."""
    p = Path(sys.executable).resolve()
    if p.suffix.lower() == ".exe" and p.stem.lower() == "python":
        return str(p)
    if p.suffix.lower() == ".exe" and p.stem.lower() == "pythonw":
        alt = p.with_name("python.exe")
        if alt.is_file():
            return str(alt)
    if getattr(sys, "frozen", False):
        for candidate in ("python.exe", "python3.exe", "python"):
            resolved = shutil.which(candidate)
            if resolved:
                return str(Path(resolved).resolve())
    return str(p)


def cli_python_gui_spawn() -> str:
    """Interpreter for GUI-owned script runners (no console window on Windows)."""
    exe = Path(cli_python_executable())
    if sys.platform == "win32" and exe.name.lower() == "python.exe":
        pyw = exe.with_name("pythonw.exe")
        if pyw.is_file():
            return str(pyw)
        pyw_path = shutil.which("pythonw.exe")
        if pyw_path:
            return str(Path(pyw_path).resolve())
    return str(exe)


def qprocess_attach_no_console(proc: object) -> None:
    """Hide console windows for QProcess children on Windows (Diagnostics / preflight)."""
    if sys.platform != "win32":
        return
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not flag:
        return
    try:
        from PySide6 import QtCore
    except ImportError:
        return

    def _modifier(args: QtCore.QProcess.CreateProcessArguments) -> None:
        args.flags |= int(flag)

    proc.setCreateProcessArgumentsModifier(_modifier)  # type: ignore[attr-defined]
