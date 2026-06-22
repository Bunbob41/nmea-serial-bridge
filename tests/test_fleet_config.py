"""Fleet config validation and persistence."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bridge_core import NetMode
from core.fleet.config import (
    FLEET_MAX_STREAMS,
    FleetConfig,
    StreamDefinition,
    load_fleet_config,
    normalize_udp_listen_host,
    save_fleet_config,
    udp_listen_hosts_conflict,
    validate_fleet_config,
)


class TestFleetConfig(unittest.TestCase):
    def test_rejects_ninth_stream(self) -> None:
        streams = [
            StreamDefinition.new(f"S{i}", com=f"COM{i}", enabled=True)
            for i in range(FLEET_MAX_STREAMS + 1)
        ]
        errors = validate_fleet_config(FleetConfig(streams=streams))
        self.assertTrue(any("8" in e for e in errors))

    def test_rejects_duplicate_com(self) -> None:
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new("A", com="COM9", enabled=True),
                StreamDefinition.new("B", com="COM9", enabled=True, udp_port=10111),
            ]
        )
        errors = validate_fleet_config(cfg)
        self.assertTrue(any("COM9" in e for e in errors))

    def test_rejects_duplicate_udp_listen_port(self) -> None:
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110),
                StreamDefinition.new(
                    "B",
                    com="COM8",
                    enabled=True,
                    net_mode=NetMode.UDP_LISTEN.value,
                    udp_port=10110,
                ),
            ]
        )
        errors = validate_fleet_config(cfg)
        self.assertTrue(any("10110" in e for e in errors))

    def test_primary_exclusive(self) -> None:
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new("A", primary=True),
                StreamDefinition.new("B"),
            ]
        )
        cfg.set_primary(cfg.streams[1].id)
        self.assertFalse(cfg.streams[0].primary)
        self.assertTrue(cfg.streams[1].primary)

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fleet_config.json"
            cfg = FleetConfig(
                auto_start_on_launch=True,
                streams=[
                    StreamDefinition.new(
                        "SVP",
                        com="COM6",
                        baud=9600,
                        net_mode=NetMode.UDP_REMOTE.value,
                        udp_remote_port=10112,
                    )
                ],
            )
            save_fleet_config(cfg, path)
            loaded = load_fleet_config(path)
            self.assertTrue(loaded.auto_start_on_launch)
            self.assertEqual(loaded.streams[0].label, "SVP")




    def test_rejects_mirror_duplicate_com(self) -> None:
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new('A', com='COM7', enabled=True, udp_port=10110),
                StreamDefinition.new(
                    'B',
                    com='COM8',
                    enabled=True,
                    udp_port=10111,
                    serial_mirror_ports=['COM7'],
                ),
            ]
        )
        errors = validate_fleet_config(cfg)
        self.assertTrue(any('COM7' in e for e in errors))

    def test_caps_mirror_ports_at_two(self) -> None:
        from core.fleet.config import normalize_serial_mirror_ports

        ports = normalize_serial_mirror_ports(['COM8', 'COM9', 'COM10'], primary='COM7')
        self.assertEqual(ports, ['COM8', 'COM9'])

    def test_mavlink_mp_stream_defaults(self) -> None:
        from core.fleet.config import FLEET_MAVLINK_MP_UDP_PORT, mavlink_mp_stream

        s = mavlink_mp_stream()
        self.assertEqual(s.label, "MAVLink / MP")
        self.assertEqual(s.nmea_mode, "raw")
        self.assertEqual(s.udp_host, "0.0.0.0")
        self.assertEqual(s.udp_port, FLEET_MAVLINK_MP_UDP_PORT)
        self.assertTrue(s.udp_fanout)

    def test_udp_listen_host_conflict_wildcard(self) -> None:
        self.assertTrue(udp_listen_hosts_conflict("0.0.0.0", "127.0.0.1"))
        self.assertTrue(udp_listen_hosts_conflict("100.64.1.2", "0.0.0.0"))
        self.assertFalse(udp_listen_hosts_conflict("192.168.1.5", "10.0.0.5"))

    def test_rejects_conflicting_udp_listen_hosts_same_port(self) -> None:
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new(
                    "A",
                    com="COM7",
                    enabled=True,
                    net_mode=NetMode.UDP_LISTEN.value,
                    udp_host="0.0.0.0",
                    udp_port=14550,
                ),
                StreamDefinition.new(
                    "B",
                    com="COM8",
                    enabled=True,
                    net_mode=NetMode.UDP_LISTEN.value,
                    udp_host="127.0.0.1",
                    udp_port=14550,
                ),
            ]
        )
        errors = validate_fleet_config(cfg)
        self.assertTrue(any("14550" in e for e in errors))

    def test_normalize_udp_listen_host_defaults(self) -> None:
        self.assertEqual(normalize_udp_listen_host(""), "0.0.0.0")
        self.assertEqual(normalize_udp_listen_host("*"), "0.0.0.0")


class TestFleetBacklogLine(unittest.TestCase):
    def test_ok_when_running_and_clear(self) -> None:
        from core.fleet.types import StreamRuntimeState, WorkerState

        st = StreamRuntimeState(stream_id="a", worker_state=WorkerState.RUNNING)
        self.assertEqual(st.backlog_line(), "ok")

    def test_drop_and_queue_backlog(self) -> None:
        from core.fleet.types import FLEET_QUEUE_BACKLOG_DEPTH, StreamRuntimeState, WorkerState

        st = StreamRuntimeState(
            stream_id="a",
            worker_state=WorkerState.RUNNING,
            drops_n2s=3,
            drops_s2n=9,
            queue_s2n=FLEET_QUEUE_BACKLOG_DEPTH,
        )
        self.assertEqual(st.backlog_line(), "drop 12 q 0+12")

if __name__ == "__main__":
    unittest.main()