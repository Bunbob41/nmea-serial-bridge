"""Connect tab — Network (UDP listen) option guide (popout)."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

_NETWORK_HELP_MARKDOWN = """\
## Network options on Connect

Default survey path: **UDP listen** on this PC → bridge → **COM** to your device.

---

### Listen host

Address the bridge **binds** on this PC (where senders aim UDP packets).

| Value | Typical use |
| ----- | ----------- |
| **0.0.0.0** | All network interfaces — normal for boat/LAN INS traffic |
| **127.0.0.1** | Loopback only — one-PC bench (simulator on same machine) |

The bridge does **not** dial out; your INS or simulator must send **to** this PC.

---

### Listen port

UDP port number (default **10110**). Must match what the INS, simulator, or Hypack-side
tool is configured to send to (e.g. `Survey-PC-IP:10110`).

---

### Fan-out

**UDP listen mode only.** Controls where **COM → network** data goes.

- **Checked (default):** Every UDP sender that has talked to the bridge this session
  receives the serial stream (good when several tools listen on the LAN).
- **Unchecked:** Only the **most recent** sender gets COM→net (one-to-one).

Does not change who can send **into** the bridge — only who gets data **out** from COM.

---

### Extra TCP output

**Optional.** Off by default.

When enabled and the bridge is **Running**, the app opens a **TCP server** on this PC
(port **10111** by default). Other programs connect as **TCP clients** to receive a
**copy** of the same COM→network bytes as your main UDP path.

Use for a logger, monitor, or test harness — **not** a replacement for UDP listen or Fan-out.

---

### Advanced network

Shows the full mode picker: **UDP remote**, **TCP server**, **TCP client**.

Leave off for the usual INS → UDP → COM workflow. Turn on only when you need a
non-listen path (see **Tools → Guide** for step-by-step TCP/UDP remote workflows).

---

**Quick check after Start:** status banner **Running**; bottom bar **Network** line shows
listen OK (or your advanced mode). Send test UDP to the listen port and confirm Hz > 0.
"""


def show_network_options_help(parent: QtWidgets.QWidget) -> QtWidgets.QDialog:
    """Non-modal guide for Listen host/port, Fan-out, Extra TCP output, Advanced."""
    existing = getattr(parent, "_network_help_dialog", None)
    if existing is not None:
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return existing

    dlg = QtWidgets.QDialog(parent)
    dlg.setObjectName("networkOptionsHelpDialog")
    dlg.setWindowTitle("Network options guide")
    dlg.setMinimumSize(520, 480)
    dlg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

    lay = QtWidgets.QVBoxLayout(dlg)
    intro = QtWidgets.QLabel(
        "What each setting in <b>Network (UDP listen)</b> does. "
        "Hover individual controls for short reminders."
    )
    intro.setWordWrap(True)
    intro.setObjectName("tabHint")
    lay.addWidget(intro)

    browser = QtWidgets.QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.setMarkdown(_NETWORK_HELP_MARKDOWN)
    lay.addWidget(browser, 1)

    row = QtWidgets.QHBoxLayout()
    btn_close = QtWidgets.QPushButton("Close")
    btn_close.clicked.connect(dlg.close)
    row.addStretch(1)
    row.addWidget(btn_close)
    lay.addLayout(row)

    def _clear_ref(*_args: object) -> None:
        if getattr(parent, "_network_help_dialog", None) is dlg:
            parent._network_help_dialog = None  # type: ignore[attr-defined]

    dlg.finished.connect(_clear_ref)
    parent._network_help_dialog = dlg  # type: ignore[attr-defined]
    dlg.show()
    return dlg


def create_network_help_button(parent: QtWidgets.QWidget) -> QtWidgets.QToolButton:
    """Compact control to place beside Fan-out / network checkboxes."""
    btn = QtWidgets.QToolButton(parent)
    btn.setObjectName("networkOptionsHelpBtn")
    btn.setText("?")
    btn.setToolTip("Open guide: Listen host/port, Fan-out, Extra TCP output, Advanced network")
    btn.setAutoRaise(True)
    btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(lambda: show_network_options_help(parent))
    return btn
