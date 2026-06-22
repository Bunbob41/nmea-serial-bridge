"""Control-character sanitization for UI text."""
import unittest

from log_serial_coalesce import ui_safe_text


class TestUiSafeText(unittest.TestCase):
    def test_strips_bel(self) -> None:
        self.assertEqual(ui_safe_text("hello\x07world"), "hello world")

    def test_keeps_newline(self) -> None:
        self.assertEqual(ui_safe_text("a\nb"), "a\nb")


if __name__ == "__main__":
    unittest.main()
