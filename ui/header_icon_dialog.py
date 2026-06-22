"""Import / reset custom Modern header chip icons."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from ui.header_bar_prefs import (
    CHIP_ICON_SCHEMA_VERSION,
    example_chip_icons_json,
    export_chip_icons_json,
    parse_chip_icons_import,
)


class HeaderChipIconDialog(QtWidgets.QDialog):
    def __init__(self, current: dict[str, str], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Customize header chip icons")
        self.setMinimumSize(520, 420)
        self._parsed: dict[str, str] = dict(current)

        intro = QtWidgets.QLabel(
            "Paste or import JSON (schema v"
            f"{CHIP_ICON_SCHEMA_VERSION}). Each icon is 1–4 characters — emoji recommended. "
            "See docs/HEADER_CHIP_ICONS.md for the full key list."
        )
        intro.setWordWrap(True)

        self._editor = QtWidgets.QPlainTextEdit()
        self._editor.setPlaceholderText(example_chip_icons_json())
        if current:
            self._editor.setPlainText(export_chip_icons_json(current))
        self._status = QtWidgets.QLabel("")
        self._status.setWordWrap(True)

        btn_load = QtWidgets.QPushButton("Import file…")
        btn_load.clicked.connect(self._on_import_file)
        btn_example = QtWidgets.QPushButton("Load example")
        btn_example.clicked.connect(
            lambda: self._editor.setPlainText(example_chip_icons_json())
        )
        btn_reset = QtWidgets.QPushButton("Reset to product defaults")
        btn_reset.clicked.connect(self._on_reset_defaults)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(btn_load)
        row.addWidget(btn_example)
        row.addWidget(btn_reset)
        row.addStretch(1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(intro)
        lay.addLayout(row)
        lay.addWidget(self._editor, 1)
        lay.addWidget(self._status)
        lay.addWidget(buttons)

    def icons(self) -> dict[str, str]:
        return dict(self._parsed)

    def _on_import_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import chip icons JSON",
            str(Path.home()),
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self._editor.setPlainText(text)
            self._status.setText(f"Loaded {path}")
        except OSError as exc:
            self._status.setText(f"Could not read file: {exc}")

    def _on_reset_defaults(self) -> None:
        self._editor.clear()
        self._parsed = {}
        self._status.setText("Cleared — product default icons will be used.")

    def _on_accept(self) -> None:
        text = self._editor.toPlainText().strip()
        if not text:
            self._parsed = {}
            self.accept()
            return
        try:
            self._parsed = parse_chip_icons_import(text)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            self._status.setText(f"Invalid JSON: {exc}")
            return
        self.accept()
