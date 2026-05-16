"""Survey / file log line shape (regression for log accuracy)."""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from bridge_core import _FileSurveyLog


class TestSurveyFileLog(unittest.TestCase):
    def test_line_has_four_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "survey.log"
            log = _FileSurveyLog(path)
            try:
                log.write("UDP←127.0.0.1:1", "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47", "123519.00 UTC")
            finally:
                log.close()
            text = path.read_text(encoding="utf-8").strip()
        parts = [p.strip() for p in text.split("|")]
        self.assertEqual(len(parts), 4, msg=text)
        self.assertEqual(parts[2], "UDP←127.0.0.1:1")
        self.assertIn("GPGGA", parts[3])
        # PC time YYYY-MM-DD HH:MM:SS.mmm
        self.assertTrue(re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}", parts[0]), msg=parts[0])


if __name__ == "__main__":
    unittest.main()
