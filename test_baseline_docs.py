"""Docs alignment checks for baseline spec (fan-out, version line)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestBaselineDocs(unittest.TestCase):
    def test_readme_documents_fanout_modes(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("fan-out", text.lower())
        self.assertIn("Fan-out", text)

    def test_operator_guide_fanout_section(self) -> None:
        text = (ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("5.5", text)
        self.assertIn("fan-out", text.lower())

    def test_traceability_matrix_exists(self) -> None:
        path = ROOT / "specs" / "001-baseline-spec" / "traceability.md"
        self.assertTrue(path.is_file())
        body = path.read_text(encoding="utf-8")
        self.assertIn("FR-011", body)
        self.assertIn("FR-020", body)


if __name__ == "__main__":
    unittest.main()
