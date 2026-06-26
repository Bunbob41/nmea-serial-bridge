"""Bundled operator manual paths and link resolution."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui.doc_viewer import (
    _href_to_doc_rel,
    normalize_doc_rel,
    resolve_bundled_doc,
)
from tests import REPO_ROOT


class TestDocViewerPaths(unittest.TestCase):
    def test_normalize_doc_rel(self) -> None:
        self.assertEqual(normalize_doc_rel("docs/GETTING_STARTED.md"), "docs/GETTING_STARTED.md")
        self.assertEqual(normalize_doc_rel("OPERATOR_GUIDE.md"), "docs/OPERATOR_GUIDE.md")
        self.assertEqual(normalize_doc_rel(""), "")

    def test_resolve_dev_tree(self) -> None:
        root = REPO_ROOT
        with patch("ui.doc_viewer.bundle_root", return_value=root):
            path = resolve_bundled_doc("docs/GETTING_STARTED.md")
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())

    def test_resolve_frozen_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            target = docs / "NORBIT_DCT.md"
            target.write_text("# DCT\n", encoding="utf-8")
            with patch.object(sys, "frozen", True, create=True):
                with patch.object(sys, "_MEIPASS", str(root), create=True):
                    path = resolve_bundled_doc("docs/NORBIT_DCT.md")
                    self.assertIsNotNone(path)
                    self.assertEqual(path.resolve(), target.resolve())

    def test_href_to_sibling_doc(self) -> None:
        current = Path("/x/docs/GETTING_STARTED.md")
        rel = _href_to_doc_rel("OPERATOR_GUIDE.md", current)
        self.assertEqual(rel, "docs/OPERATOR_GUIDE.md")


if __name__ == "__main__":
    unittest.main()
