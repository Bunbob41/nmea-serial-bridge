"""Pick ``python.exe`` for subprocesses when the app was started with ``pythonw.exe`` (Windows GUI)."""
from __future__ import annotations

import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

FROZEN_HELPER_FLAG = "--run-helper"


def subprocess_no_console_kwargs() -> dict:
    """Extra kwargs for ``subprocess`` calls so GUI-launched scripts do not flash consoles (Windows)."""
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not flag:
        return {}
    return {"creationflags": flag}


def stream_isatty(stream) -> bool:
    """True when *stream* is an interactive TTY; False when missing (frozen GUI / pythonw)."""
    if stream is None:
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _frozen_meipass() -> Optional[Path]:
    if not getattr(sys, "frozen", False):
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def cli_python_executable() -> str:
    """Interpreter to use for CLI subprocesses (unittest, verify scripts, etc.)."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    p = Path(sys.executable).resolve()
    if p.suffix.lower() == ".exe" and p.stem.lower() == "python":
        return str(p)
    if p.suffix.lower() == ".exe" and p.stem.lower() == "pythonw":
        alt = p.with_name("python.exe")
        if alt.is_file():
            return str(alt)
    return str(p)


def cli_python_gui_spawn() -> str:
    """Program for GUI-owned script runners (Diagnostics / preflight)."""
    if getattr(sys, "frozen", False):
        return cli_python_executable()
    exe = Path(cli_python_executable())
    if sys.platform == "win32" and exe.name.lower() == "python.exe":
        pyw = exe.with_name("pythonw.exe")
        if pyw.is_file():
            return str(pyw)
        pyw_path = shutil.which("pythonw.exe")
        if pyw_path:
            return str(Path(pyw_path).resolve())
    return str(exe)


def frozen_helper_program_args(script: str, args: Optional[Sequence[str]] = None) -> list[str]:
    """QProcess / argv tail for a bundled helper script in a frozen build."""
    tail = [FROZEN_HELPER_FLAG, Path(script).name, *(args or [])]
    if getattr(sys, "frozen", False):
        return tail
    root = Path(script).resolve().parent
    return [str(root / Path(script).name), *(args or [])]


def subprocess_script_argv(script: str | Path, extra: Optional[Sequence[str]] = None) -> list[str]:
    """Full argv for ``subprocess`` to run a project helper script."""
    path = Path(script)
    name = path.name
    extra_list = list(extra or [])
    exe = cli_python_executable()
    if getattr(sys, "frozen", False):
        return [exe, FROZEN_HELPER_FLAG, name, *extra_list]
    return [exe, str(path.resolve()), *extra_list]


def run_frozen_helper_if_requested() -> Optional[int]:
    """If ``sys.argv`` requests a bundled helper, run it and return an exit code."""
    if not getattr(sys, "frozen", False):
        return None
    argv = list(sys.argv)
    if len(argv) < 3 or argv[1] != FROZEN_HELPER_FLAG:
        return None
    script_name = Path(argv[2]).name
    script_args = argv[3:]
    root = _frozen_meipass()
    if root is None:
        print(f"[frozen helper] no _MEIPASS; cannot run {script_name}", file=sys.stderr)
        return 2
    script_path = root / script_name
    if not script_path.is_file():
        print(f"[frozen helper] missing script: {script_path}", file=sys.stderr)
        return 2
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    sys.argv = [str(script_path), *script_args]
    try:
        runpy.run_path(str(script_path), run_name="__main__")
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


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

    attach = getattr(proc, "setCreateProcessArgumentsModifier", None)
    if not callable(attach):
        # Older PySide6 builds: rely on pythonw.exe from cli_python_gui_spawn() instead.
        return
    attach(_modifier)
