"""In-app operator manuals (bundled docs/*.md) — offline, no external browser."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from PySide6 import QtCore, QtGui, QtWidgets

_DOC_VIEWER_CSS = """
body {
  font-family: Maple Mono, Cascadia Mono, Consolas, sans-serif;
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
  padding: 2px 4px;
  background: #f5ecd8;
  color: #2a1e18;
}
h1, h2, h3, h4 { color: #3a1f13; margin: 12px 0 6px 0; }
h1 { font-size: 17px; }
h2 { font-size: 15px; }
p  { margin: 6px 0 8px 0; }
ul, ol { margin: 4px 0 10px 20px; }
li { margin-bottom: 4px; }
a  { color: #1a5fb4; text-decoration: underline; }
code { background: #2a2624; color: #f0ece6; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
pre  { background: #2a2624; color: #f0ece6; padding: 8px 10px; border-radius: 4px; overflow-x: auto; }
table { border-collapse: collapse; margin: 8px 0 12px 0; width: 100%; }
th, td { border: 1px solid #a09888; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #e8dfd0; }
hr { border: none; border-top: 1px solid #a09888; margin: 12px 0; }
blockquote { margin: 8px 0; padding: 6px 10px; border-left: 3px solid #8a7a66; color: #4a3f36; }
"""

_MD_LINK_RE = re.compile(r"\.md(?:#|$|\?)", re.IGNORECASE)


def bundle_root() -> Path:
    """Directory containing ``docs/`` (project root in dev, ``_MEIPASS`` when frozen)."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def docs_dir() -> Path:
    return bundle_root() / "docs"


def normalize_doc_rel(rel: str) -> str:
    s = unquote(str(rel or "").strip().replace("\\", "/"))
    if s.startswith("file:"):
        parsed = urlparse(s)
        s = unquote(parsed.path or "")
        if len(s) > 2 and s[0] == "/" and s[2] == ":":
            s = s[1:]
    s = s.lstrip("/")
    name = Path(s).name
    if not name.lower().endswith(".md"):
        return ""
    if s.startswith("docs/"):
        return s
    return f"docs/{name}"


def resolve_bundled_doc(rel: str) -> Optional[Path]:
    """Resolve ``docs/FOO.md`` under the bundle; returns None if missing or unsafe."""
    norm = normalize_doc_rel(rel)
    if not norm:
        return None
    root = docs_dir().resolve()
    path = (bundle_root() / norm).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def _href_to_doc_rel(href: str, current_doc: Path) -> str:
    raw = unquote(href.strip())
    if raw.startswith("file:"):
        parsed = urlparse(raw)
        raw = unquote(parsed.path or "")
        if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
    if "#" in raw:
        raw = raw.split("#", 1)[0]
    if not raw:
        return ""
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            rel = candidate.resolve().relative_to(docs_dir().resolve())
            return f"docs/{rel.as_posix()}"
        except ValueError:
            return normalize_doc_rel(candidate.name)
    if raw.startswith("docs/"):
        return normalize_doc_rel(raw)
    joined = (current_doc.parent / raw).resolve()
    try:
        rel = joined.relative_to(docs_dir().resolve())
        return f"docs/{rel.as_posix()}"
    except ValueError:
        return normalize_doc_rel(Path(raw).name)


class OperatorDocDialog(QtWidgets.QDialog):
    """Non-modal reader for bundled markdown manuals."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        path: Path,
        *,
        window_title: str,
    ) -> None:
        super().__init__(parent)
        self._current_path = path.resolve()
        self.setObjectName("operatorDocDialog")
        self.setWindowTitle(window_title)
        self.setMinimumSize(680, 520)
        self.resize(820, 640)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self._browser = QtWidgets.QTextBrowser()
        self._browser.setObjectName("docViewerBrowser")
        self._browser.setOpenExternalLinks(False)
        self._browser.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._browser.document().setDefaultStyleSheet(_DOC_VIEWER_CSS)
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        lay.addWidget(self._browser, 1)

        row = QtWidgets.QHBoxLayout()
        self._path_label = QtWidgets.QLabel()
        self._path_label.setObjectName("tabNote")
        self._path_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        row.addWidget(self._path_label, 1)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close)
        row.addWidget(btn_close)
        lay.addLayout(row)

        self.load_path(path)

    def load_path(self, path: Path) -> None:
        self._current_path = path.resolve()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._browser.setPlainText(f"Could not read document:\n{path}\n\n{exc}")
            self._path_label.setText(str(path))
            return
        self._browser.setMarkdown(text)
        self._path_label.setText(path.name)
        self.setWindowTitle(path.stem.replace("_", " ").title())

    def _on_anchor_clicked(self, url: QtCore.QUrl) -> None:
        scheme = (url.scheme() or "").lower()
        href = url.toString(QtCore.QUrl.UrlFormattingOption.FullyEncoded)
        if scheme in ("http", "https", "mailto"):
            QtGui.QDesktopServices.openUrl(url)
            return
        if _MD_LINK_RE.search(href) or href.lower().endswith(".md"):
            rel = _href_to_doc_rel(href, self._current_path)
            target = resolve_bundled_doc(rel) if rel else None
            if target is not None:
                self.load_path(target)
                return
        if scheme == "file":
            rel = _href_to_doc_rel(href, self._current_path)
            target = resolve_bundled_doc(rel) if rel else None
            if target is not None:
                self.load_path(target)
                return
        QtGui.QDesktopServices.openUrl(url)


def show_bundled_doc(
    parent: QtWidgets.QWidget,
    rel: str,
    *,
    window_title: str = "Manual",
) -> Optional[OperatorDocDialog]:
    """Open or focus the in-app manual viewer (offline)."""
    path = resolve_bundled_doc(rel)
    if path is None:
        QtWidgets.QMessageBox.information(
            parent,
            window_title,
            f"Document not found:\n{rel}\n\nExpected under:\n{docs_dir()}",
        )
        return None

    existing = getattr(parent, "_operator_doc_dialog", None)
    if isinstance(existing, OperatorDocDialog):
        existing.load_path(path)
        if window_title:
            existing.setWindowTitle(window_title)
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return existing

    dlg = OperatorDocDialog(parent, path, window_title=window_title)

    def _clear_ref(*_a: object) -> None:
        if getattr(parent, "_operator_doc_dialog", None) is dlg:
            parent._operator_doc_dialog = None  # type: ignore[attr-defined]

    dlg.finished.connect(_clear_ref)
    parent._operator_doc_dialog = dlg  # type: ignore[attr-defined]
    dlg.show()
    return dlg
