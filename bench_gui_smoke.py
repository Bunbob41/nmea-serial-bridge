#!/usr/bin/env python3
"""Construct each UI variant without showing (catches startup errors)."""
from __future__ import annotations

import sys

from ui.qt_test_harness import close_all_qt_widgets, ensure_qt_app, exit_after_qt_work
from ui.registry import UI_LABELS, UI_ORDER, create_window
from version import __version__


def main() -> int:
    ensure_qt_app(sys.argv)
    windows = []
    rc = 0
    try:
        for ui_id in UI_ORDER:
            w = create_window(ui_id)
            windows.append(w)
            assert w.btn_insert_sample is not None
            w._insert_send_sample()
            text = w.send_edit.toPlainText()
            if "GPGGA" not in text:
                print(f"[bench_gui_smoke] FAIL {ui_id}: sample insert missing GGA")
                rc = 1
                break
            print(f"[bench_gui_smoke] OK {ui_id} — {UI_LABELS[ui_id]}")
        if rc == 0:
            print(f"[bench_gui_smoke] All UIs OK v{__version__}")
    finally:
        for w in windows:
            try:
                w.close()
            except RuntimeError:
                pass
        close_all_qt_widgets()
    exit_after_qt_work(rc)


if __name__ == "__main__":
    main()
