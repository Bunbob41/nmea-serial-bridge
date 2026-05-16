"""Tests for bridge metrics helpers."""
import unittest
from collections import deque
from unittest.mock import patch

import bridge_core


class TestRollingHz(unittest.TestCase):
    def test_empty(self) -> None:
        dq: deque[float] = deque()
        with patch.object(bridge_core.time, "monotonic", return_value=100.0):
            self.assertEqual(bridge_core.rolling_hz_last_second(dq), 0.0)

    def test_counts_only_recent_window(self) -> None:
        dq = deque([99.0, 99.5, 100.2])
        with patch.object(bridge_core.time, "monotonic", return_value=100.3):
            hz = bridge_core.rolling_hz_last_second(dq)
        self.assertEqual(hz, 2.0)
        self.assertEqual(list(dq), [99.5, 100.2])

    def test_all_old_cleared(self) -> None:
        dq = deque([1.0, 2.0, 3.0])
        with patch.object(bridge_core.time, "monotonic", return_value=100.0):
            hz = bridge_core.rolling_hz_last_second(dq)
        self.assertEqual(hz, 0.0)
        self.assertEqual(len(dq), 0)


if __name__ == "__main__":
    unittest.main()
