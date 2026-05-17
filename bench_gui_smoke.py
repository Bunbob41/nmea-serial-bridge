#!/usr/bin/env python3
"""Construct each UI variant without showing (catches startup errors)."""
from __future__ import annotations

import sys

from PySide6 import QtWidgets

from ui.registry import UI_LABELS, UI_ORDER, create_window
from version import __version__


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    for ui_id in UI_ORDER:
        w = create_window(ui_id)
        assert w.btn_insert_sample is not None
        w._insert_send_sample()
        text = w.send_edit.toPlainText()
        if "GPGGA" not in text:
            print(f"[bench_gui_smoke] FAIL {ui_id}: sample insert missing GGA")
            return 1
        print(f"[bench_gui_smoke] OK {ui_id} — {UI_LABELS[ui_id]}")
    print(f"[bench_gui_smoke] All UIs OK v{__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
