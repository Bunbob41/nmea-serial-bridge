"""Field layout — compact control strip defaults."""
from __future__ import annotations

import unittest

from ui.field import (
    _FIELD_DEFAULT_SPLITTER_SIZES,
    _FIELD_STRIP_MIN_CLOSED,
)


class TestFieldStripLayout(unittest.TestCase):
    def test_default_splitter_favors_log(self) -> None:
        log, strip = _FIELD_DEFAULT_SPLITTER_SIZES
        self.assertGreater(log, strip)
        self.assertLess(strip, 140)

    def test_closed_strip_minimum_is_compact(self) -> None:
        self.assertLessEqual(_FIELD_STRIP_MIN_CLOSED, 100)


if __name__ == "__main__":
    unittest.main()
