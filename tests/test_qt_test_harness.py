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

    def test_verbose_ok_without_summary(self) -> None:
        out = "test_alpha (mod.Test.test_alpha) ... ok\n" * 120
        self.assertTrue(unittest_output_indicates_ok(out, ""))

    def test_dot_mode_inline_failure(self) -> None:
        out = "..." * 40 + "F" + "..." * 10
        self.assertFalse(unittest_output_indicates_ok(out, ""))

    def test_false_in_traceback_does_not_count_as_dot_failure(self) -> None:
        out = "AssertionError: False is not true\n" + ("." * 80)
        self.assertTrue(unittest_output_indicates_ok(out, ""))


if __name__ == "__main__":
    unittest.main()
