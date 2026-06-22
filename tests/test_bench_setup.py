"""Bench setup helper tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui.bench_setup import extract_operator_guide_section


class BenchSetupTests(unittest.TestCase):
    def test_extract_section_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.md"
            path.write_text(
                "## 4. Other\n"
                "skip\n"
                "## 5. Desk / bench workflow\n"
                "bench body\n"
                "### 5.1 child\n"
                "detail\n"
                "## 6. Boat\n"
                "boat\n",
                encoding="utf-8",
            )
            text = extract_operator_guide_section(path, "5. Desk / bench workflow")
            self.assertIn("bench body", text)
            self.assertIn("### 5.1 child", text)
            self.assertNotIn("## 6. Boat", text)
            self.assertNotIn("## 4. Other", text)


if __name__ == "__main__":
    unittest.main()
