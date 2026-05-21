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
    return sys.platform == "win32" and exit_code == WINDOWS_QT_SHUTDOWN_EXIT


def unittest_output_indicates_ok(stdout: str, stderr: str) -> bool:
    import re

    combined = (stdout or "") + (stderr or "")
    if not combined.strip():
        return False
    if re.search(r"\b(FAIL:|ERROR:|FAILED \()", combined):
        return False
    if re.search(r"^FAILED\b", combined, re.MULTILINE):
        return False
    return bool(re.search(r"Ran \d+ tests\b", combined)) and "OK" in combined
