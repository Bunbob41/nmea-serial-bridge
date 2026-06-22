"""Survey Dashboard trust evaluation (no Qt)."""
from __future__ import annotations

import unittest

from ui.stats_line import transport_alert_active
from ui.survey_dashboard import compute_trust_verdict, evaluate_p0_charter


class TestSurveyDashboard(unittest.TestCase):
    def test_transport_ok_when_idle_counters(self) -> None:
        rows = evaluate_p0_charter(
            {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 2, "s2n_q": 1},
            serial_line="Serial: COM7 @ 115200 — open",
            network_line="Network: UDP listen on ('0.0.0.0', 10110) — 1 peer",
            running=True,
            nmea_mode="passthrough",
            udp_fanout=True,
            serial_auto_reconnect=True,
        )
        by_id = {r.item_id: r for r in rows}
        self.assertEqual(by_id["transport"].status, "ok")
        self.assertFalse(transport_alert_active({"n2s_q": 2, "s2n_q": 1}))
        verdict = compute_trust_verdict(rows, {"hz_down": 2.0, "hz_up": 0.0}, running=True)
        self.assertEqual(verdict.headline, "Ready")

    def test_transport_warn_on_drops(self) -> None:
        rows = evaluate_p0_charter(
            {"drops_n2s": 3, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0},
            serial_line="Serial: COM7 — open",
            network_line="Network: listen",
            running=True,
            nmea_mode="passthrough",
            udp_fanout=True,
            serial_auto_reconnect=True,
        )
        self.assertEqual({r.item_id: r.status for r in rows}["transport"], "warn")
        verdict = compute_trust_verdict(rows, {}, running=True)
        self.assertEqual(verdict.headline, "Caution")

    def test_stopped_verdict(self) -> None:
        rows = evaluate_p0_charter(
            {},
            serial_line="Serial: —",
            network_line="Network: —",
            running=False,
            nmea_mode="passthrough",
            udp_fanout=True,
            serial_auto_reconnect=True,
        )
        verdict = compute_trust_verdict(rows, {}, running=False)
        self.assertEqual(verdict.headline, "Stopped")


if __name__ == "__main__":
    unittest.main()
