"""Guide tab copy matches live UI control labels."""
from __future__ import annotations

import unittest

from ui import tool_tabs as tt


class TestGuideContent(unittest.TestCase):
    def test_guide_mentions_advanced_network_and_listen_fields(self) -> None:
        blob = " ".join(
            (
                tt._GUIDE_START,
                tt._GUIDE_UDP,
                tt._GUIDE_TCP_CLIENT,
                tt._GUIDE_TCP_SERVER,
                tt._GUIDE_CHECKLIST,
            )
        )
        self.assertIn("Advanced network (TCP / UDP remote / all modes)", blob)
        self.assertIn("Listen host", blob)
        self.assertIn("Start bridge", blob)
        self.assertIn("Tools → Phone", blob)

    def test_guide_does_not_reference_removed_product_demo(self) -> None:
        blob = " ".join((tt._GUIDE_START, tt._GUIDE_CHECKLIST))
        self.assertNotIn("Product demo", blob)
        self.assertNotIn("PRODUCT DEMO", blob)

    def test_guide_udp_remote_uses_host_port_not_target_ip(self) -> None:
        self.assertIn("UDP remote (fixed peer)", tt._GUIDE_UDP)
        self.assertNotIn("Target IP", tt._GUIDE_UDP)


if __name__ == "__main__":
    unittest.main()
