# bridge_gui.py — entry point for Network ↔ COM bridge GUI
from __future__ import annotations

import argparse
import sys

from PySide6 import QtWidgets

from bridge_core import (  # noqa: F401 — re-export for older scripts
    NetMode,
    SerialNetBridge,
    configure_windows_event_loop_policy,
)
from ui.app_icon import apply_app_icon
from ui.registry import create_window
from ui.standard import BridgeWindowStandard

BridgeWindow = BridgeWindowStandard


def main() -> None:
    parser = argparse.ArgumentParser(description="NMEA UDP/TCP ↔ serial bridge")
    parser.add_argument(
        "--ui",
        choices=["standard", "minimal", "logfirst"],
        default=None,
        help="UI layout (default: saved choice, picker on first .exe run, else standard)",
    )
    parser.add_argument(
        "--pick-ui",
        action="store_true",
        help="Show layout picker dialog before opening the window",
    )
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    apply_app_icon(app)
    from ui.picker import load_saved_ui, resolve_ui_id

    show_picker = args.pick_ui or (
        args.ui is None and load_saved_ui() is None
    )
    ui_id = resolve_ui_id(args.ui, show_picker=show_picker)
    w = create_window(ui_id)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
