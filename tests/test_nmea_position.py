"""NMEA position parsing for web map / future HUD."""
from __future__ import annotations

import unittest

from nmea_position import (
    feed_nmea_position,
    nmea_dm_to_decimal,
    parse_gga_position,
    parse_rmc_position,
)

_SAMPLE_GGA = (
    "$GPGGA,032358.34,3600.42235,N,11846.36546,W,5,09,1.9,0.0,M,15.5,M,2.0,0000*51"
)
_SAMPLE_RMC = (
    "$GPRMC,032358.34,A,3600.42235,N,11846.36546,W,0.0,0.0,240526,,,A*6E"
)


class TestNmeaPosition(unittest.TestCase):
    def test_dm_to_decimal(self) -> None:
        self.assertAlmostEqual(nmea_dm_to_decimal("3600.42235", "N") or 0, 36.007039, places=5)
        self.assertAlmostEqual(nmea_dm_to_decimal("11846.36546", "W") or 0, -118.772757, places=5)

    def test_parse_gga(self) -> None:
        pos = parse_gga_position(_SAMPLE_GGA)
        assert pos is not None
        self.assertEqual(pos.source, "gga")
        self.assertAlmostEqual(pos.lat, 36.007039, places=5)
        self.assertAlmostEqual(pos.lon, -118.772757, places=5)

    def test_parse_rmc(self) -> None:
        pos = parse_rmc_position(_SAMPLE_RMC)
        assert pos is not None
        self.assertEqual(pos.source, "rmc")

    def test_feed_updates_state(self) -> None:
        state: list = [None]
        feed_nmea_position([(_SAMPLE_GGA + "\r\n").encode()], state)
        assert state[0] is not None
        self.assertAlmostEqual(state[0]["lat"], 36.007039, places=5)

    def test_ddm_display_matches_simulator(self) -> None:
        from nmea_position import format_dm_field

        self.assertEqual(format_dm_field("4436.77826", "N"), "44° 36.77826' N")
        self.assertEqual(format_dm_field("12013.66857", "W"), "120° 13.66857' W")

    def test_gga_wire_fields_in_position_dict(self) -> None:
        pos = parse_gga_position(
            "$GPGGA,123519,4436.77826,N,12013.66857,W,1,08,0.9,545.4,M,46.9,M,,*47"
        )
        assert pos is not None
        d = pos.to_dict()
        self.assertEqual(d["lat_dm"], "4436.77826")
        self.assertEqual(d["lon_dm"], "12013.66857")


if __name__ == "__main__":
    unittest.main()
