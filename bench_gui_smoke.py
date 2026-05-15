#!/usr/bin/env python3
"""Construct BridgeWindow without showing UI (catches startup AttributeErrors)."""
from __future__ import annotations

import sys

from PySide6 import QtWidgets

from bridge_gui import BridgeWindow
from version import __version__


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    w = BridgeWindow()
    assert w.btn_insert_sample is not None
    w._insert_send_sample()
    text = w.send_edit.toPlainText()
    if "GPGGA" not in text or "GPRMC" not in text:
        print("[bench_gui_smoke] FAIL: sample insert missing GGA/RMC")
        return 1
    print(f"[bench_gui_smoke] OK v{__version__} — window builds, EDH sample inserts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
