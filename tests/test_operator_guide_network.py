"""Operator guide documents network P0 checklist (contract)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


from tests import REPO_ROOT

_GUIDE = REPO_ROOT / "docs" / "OPERATOR_GUIDE.md"
_GETTING = REPO_ROOT / "docs" / "GETTING_STARTED.md"


class TestOperatorGuideNetwork(unittest.TestCase):
    def test_operator_guide_has_network_reliability_section(self) -> None:
        text = _GUIDE.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(r"6\.4\s+Network reliability", re.IGNORECASE),
        )
        for phrase in (
            "Listen host",
            "Fan-out",
            "Extra TCP output",
            "TCP client",
            "Windows firewall",
            "Tailscale",
        ):
            self.assertIn(phrase, text)

    def test_getting_started_links_network_checklist(self) -> None:
        body = _GETTING.read_text(encoding="utf-8")
        self.assertIn("OPERATOR_GUIDE.md", body)
        self.assertIn("6.4", body)


if __name__ == "__main__":
    unittest.main()
