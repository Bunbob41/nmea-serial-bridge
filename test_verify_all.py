"""verify_all traceback gate helpers."""
from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

import verify_all


class TestVerifyAllTracebackGate(unittest.TestCase):
    def test_has_traceback_detects_marker(self) -> None:
        self.assertTrue(verify_all._has_traceback("Traceback (most recent call last):\nboom"))
        self.assertFalse(verify_all._has_traceback("all good"))

    def test_run_reports_traceback_even_with_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "prints_traceback.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    print("Traceback (most recent call last):")
                    print("  File \\"demo.py\\", line 1, in <module>")
                    print("RuntimeError: synthetic")
                    """
                ),
                encoding="utf-8",
            )
            code, traceback_seen = verify_all.run("tb", [str(script)], echo_output=False)
            self.assertEqual(code, 0)
            self.assertTrue(traceback_seen)


if __name__ == "__main__":
    unittest.main()
