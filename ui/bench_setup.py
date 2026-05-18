"""Bench / com0com setup helper UI (operator guide excerpt + stable dialog)."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.ui_prefs import load_bench_setup_prefs, save_bench_setup_prefs


def extract_operator_guide_section(path: Path, section_heading: str) -> str:
    """Return markdown from ``## 5. …`` until the next top-level ``## N.`` section."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    out: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("## ") and not line.startswith("###"):
            if capture:
                break
            if section_heading in line:
                capture = True
        if capture:
            out.append(line)
    return "\n".join(out).strip()


def show_bench_setup_dialog(
    parent: QtWidgets.QWidget,
    guide_text: str,
    *,
    on_open_full_guide: Callable[[], object],
    on_hide_pref_changed: Optional[Callable[[bool], object]] = None,
) -> Optional[QtWidgets.QDialog]:
    """Non-modal bench setup window (stays open until the user closes it)."""
    prefs = load_bench_setup_prefs()
    if bool(prefs.get("hide_dialog", False)):
        return None

    existing = getattr(parent, "_bench_setup_dialog", None)
    if existing is not None:
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return existing

    dlg = QtWidgets.QDialog(parent)
    dlg.setObjectName("benchSetupDialog")
    dlg.setWindowTitle("Bench pair setup")
    dlg.setMinimumSize(560, 440)
    dlg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

    lay = QtWidgets.QVBoxLayout(dlg)
    intro = QtWidgets.QLabel(
        "Install com0com and create a paired COM pair. Preflight output appears in "
        "<b>Connect → Quick terminal</b> below."
    )
    intro.setWordWrap(True)
    lay.addWidget(intro)

    browser = QtWidgets.QTextBrowser()
    browser.setOpenExternalLinks(True)
    body = guide_text.strip() or (
        "Guide section not found. Use **Open full guide** or open "
        "`docs/OPERATOR_GUIDE.md` section 5 in the project folder."
    )
    browser.setMarkdown(body)
    lay.addWidget(browser, 1)

    row = QtWidgets.QHBoxLayout()
    btn_guide = QtWidgets.QPushButton("Open full guide externally")
    btn_guide.setToolTip("Opens OPERATOR_GUIDE.md in your default editor or viewer")
    btn_guide.clicked.connect(on_open_full_guide)
    btn_close = QtWidgets.QPushButton("Close")
    btn_close.clicked.connect(dlg.close)
    row.addWidget(btn_guide)
    row.addStretch(1)
    row.addWidget(btn_close)
    lay.addLayout(row)

    chk_hide = QtWidgets.QCheckBox("Hide this setup window next time")
    chk_hide.setToolTip("When checked, Bench pair setup runs preflight without opening this window.")
    chk_hide.setChecked(bool(prefs.get("hide_dialog", False)))

    def _on_hide_toggled(on: bool) -> None:
        save_bench_setup_prefs(hide_dialog=bool(on))
        if on_hide_pref_changed is not None:
            on_hide_pref_changed(bool(on))

    chk_hide.toggled.connect(_on_hide_toggled)
    lay.addWidget(chk_hide)

    def _clear_ref(*_a: object) -> None:
        if getattr(parent, "_bench_setup_dialog", None) is dlg:
            parent._bench_setup_dialog = None  # type: ignore[attr-defined]

    dlg.finished.connect(_clear_ref)
    parent._bench_setup_dialog = dlg  # type: ignore[attr-defined]
    dlg.show()
    return dlg
