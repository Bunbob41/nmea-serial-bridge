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
from ui.registry import UI_DEFAULT, create_window
from ui.standard import BridgeWindowStandard

BridgeWindow = BridgeWindowStandard


def main() -> None:
    parser = argparse.ArgumentParser(description="NMEA UDP/TCP ↔ serial bridge")
    parser.add_argument(
        "--ui",
        choices=["standard", "minimal", "logfirst"],
        default=None,
        help="UI layout (default: standard, or last choice from launcher)",
    )
    args = parser.parse_args()
    ui_id = args.ui or UI_DEFAULT
    app = QtWidgets.QApplication(sys.argv)
    w = create_window(ui_id)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
