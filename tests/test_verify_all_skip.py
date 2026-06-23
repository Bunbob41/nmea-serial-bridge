"""verify_all.py CI vs local skip policy."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import verify_all


class TestVerifyAllSkipPolicy(unittest.TestCase):
    def test_ci_host_skips_all_com_benches(self) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            skip = verify_all._skip_step_names()
        self.assertIn("com_free", skip)
        self.assertIn("bench_headless", skip)
        self.assertIn("bench_stress", skip)
        self.assertIn("bench_network", skip)
        self.assertIn("bench_fanout", skip)
        self.assertNotIn("unittest", skip)

    def test_verify_all_no_skip_overrides_ci(self) -> None:
        with patch.dict(
            os.environ,
            {"GITHUB_ACTIONS": "true", "VERIFY_ALL_NO_SKIP": "1"},
            clear=False,
        ):
            self.assertEqual(verify_all._skip_step_names(), frozenset())

    def test_local_host_without_ci_does_not_skip_com_by_default(self) -> None:
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("GITHUB_ACTIONS", "CI", "VERIFY_ALL_NO_SKIP")
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(verify_all, "port_has_listener", return_value=False):
                skip = verify_all._skip_step_names()
        self.assertEqual(skip, frozenset())


if __name__ == "__main__":
    unittest.main()
