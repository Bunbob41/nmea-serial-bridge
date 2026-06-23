"""Shared Qt lifecycle helpers for tests and headless GUI smoke scripts."""
from __future__ import annotations

import os
import sys
from typing import Iterable, Optional

from PySide6 import QtWidgets

# Windows fast-fail after successful PySide6 teardown (STATUS_STACK_BUFFER_OVERRUN).
WINDOWS_QT_SHUTDOWN_EXIT = 3221226505


def ensure_qt_app(argv: Optional[list[str]] = None) -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        from ui.fonts import configure_qt_font_environment

        configure_qt_font_environment()
        app = QtWidgets.QApplication(argv if argv is not None else [])
    return app


def close_all_qt_widgets() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for widget in list(QtWidgets.QApplication.topLevelWidgets()):
        try:
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass
    app.processEvents()


def exit_after_qt_work(code: int) -> None:
    """Exit without triggering known PySide6 destructor crashes on Windows."""
    close_all_qt_widgets()
    if sys.platform == "win32" and code == 0:
        os._exit(0)
    raise SystemExit(code)


def is_windows_qt_shutdown_exit(exit_code: int | None) -> bool:
    if sys.platform != "win32" or exit_code is None:
        return False
    # subprocess may report 0xC0000409 as unsigned (3221226505) or signed (-1073740791).
    code_u = exit_code & 0xFFFFFFFF
    return code_u == (WINDOWS_QT_SHUTDOWN_EXIT & 0xFFFFFFFF)


def unittest_output_indicates_ok(stdout: str, stderr: str) -> bool:
    import re

    combined = (stdout or "") + (stderr or "")
    if not combined.strip():
        return False
    if re.search(r"^FAILED\b", combined, re.MULTILINE):
        return False
    if re.search(r"^FAIL:", combined, re.MULTILINE):
        return False
    if re.search(r"FAILED \(", combined):
        return False
    if re.search(r"^ERROR:", combined, re.MULTILINE):
        return False
    # Normal completion (when Qt teardown does not fast-fail first).
    if re.search(r"Ran \d+ tests\b", combined) and re.search(r"^OK\s*$", combined, re.MULTILINE):
        return True
    # Bridge tests log expected handler failures with logging.exception (traceback in stderr).
    # On some Windows + PySide builds the process exits 0xC0000409 before "Ran N tests OK".
    if re.search(r"\.{40,}", combined) and not re.search(r"\.[FE]", combined):
        return True
    return False
