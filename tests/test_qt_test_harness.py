"""Tests for Qt shutdown exit normalization helpers."""
from __future__ import annotations

import unittest

from ui.qt_test_harness import unittest_output_indicates_ok


class TestUnittestOutputIndicatesOk(unittest.TestCase):
    def test_ok_run(self) -> None:
        out = "----------------------------------------------------------------------\nRan 3 tests in 0.01s\n\nOK\n"
        self.assertTrue(unittest_output_indicates_ok(out, ""))

    def test_failed_run(self) -> None:
        out = "Ran 2 tests in 0.01s\n\nFAILED (failures=1)\n"
        self.assertFalse(unittest_output_indicates_ok(out, ""))


if __name__ == "__main__":
    unittest.main()
