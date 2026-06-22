"""Fleet supervisor with mock workers."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from PySide6 import QtWidgets

from bridge_core import NetMode
from core.fleet.config import FleetConfig, StreamDefinition
from core.fleet.supervisor import FleetSupervisor
from core.fleet.types import StreamRuntimeState, WorkerState


class _MockWorker:
    def __init__(self, stream_id: str, parent=None) -> None:
        self.stream_id = stream_id
        self._state = StreamRuntimeState(stream_id=stream_id)

    def start(self, stream: StreamDefinition) -> None:
        self._state.worker_state = WorkerState.RUNNING
        self._state.active_com = (stream.com or "").strip().upper()
        from core.fleet.config import stream_connection_key

        self._state.connection_key = stream_connection_key(stream)

    def stop(self) -> None:
        self._state.worker_state = WorkerState.IDLE
        self._state.active_com = ""
        self._state.connection_key = ""

    def is_running(self) -> bool:
        return self._state.worker_state == WorkerState.RUNNING

    def is_active(self) -> bool:
        return self._state.worker_state in (
            WorkerState.STARTING,
            WorkerState.RUNNING,
            WorkerState.STOPPING,
        )

    def runtime_state(self) -> StreamRuntimeState:
        return self._state


class TestFleetSupervisor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def setUp(self) -> None:
        self._probe_patcher = patch(
            "core.fleet.supervisor.probe_udp_port_available",
            return_value=True,
        )
        self._probe_patcher.start()

    def tearDown(self) -> None:
        self._probe_patcher.stop()

    def test_start_all_skips_disabled(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        sup.replace_config(
            FleetConfig(
                streams=[
                    StreamDefinition.new("On", com="COM7", enabled=True, udp_port=10110),
                    StreamDefinition.new("Off", com="COM8", enabled=False, udp_port=10111),
                ]
            )
        )
        self.assertEqual(sup.start_all(), [])
        states = sup.runtime_states()
        ids = [s.id for s in sup.config().streams]
        self.assertEqual(states[ids[0]].worker_state, WorkerState.RUNNING)
        self.assertEqual(states[ids[1]].worker_state, WorkerState.IDLE)

    def test_stop_one_leaves_other_running(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        cfg = FleetConfig(
            streams=[
                StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110),
                StreamDefinition.new("B", com="COM8", enabled=True, udp_port=10111),
            ]
        )
        sup.replace_config(cfg)
        sup.start_all()
        sup.stop_stream(cfg.streams[0].id)
        self.assertEqual(
            sup.runtime_states()[cfg.streams[1].id].worker_state,
            WorkerState.RUNNING,
        )

    def test_replace_config_restarts_on_com_change(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110)
        sup.replace_config(FleetConfig(streams=[stream]))
        sup.start_stream(stream.id)
        self.assertEqual(sup.runtime_states()[stream.id].active_com, "COM7")
        updated = StreamDefinition(
            id=stream.id,
            label=stream.label,
            enabled=True,
            com="COM12",
            baud=stream.baud,
            nmea_mode=stream.nmea_mode,
            net_mode=stream.net_mode,
            udp_host=stream.udp_host,
            udp_port=stream.udp_port,
            udp_remote_host=stream.udp_remote_host,
            udp_remote_port=stream.udp_remote_port,
            tcp_host=stream.tcp_host,
            tcp_port=stream.tcp_port,
            tcp_client_host=stream.tcp_client_host,
            tcp_client_port=stream.tcp_client_port,
            udp_fanout=stream.udp_fanout,
            local_backup=stream.local_backup,
        )
        sup.replace_config(FleetConfig(streams=[updated]))
        self.assertEqual(sup.runtime_states()[stream.id].active_com, "COM12")

    def test_running_stream_for_com(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new("A", com="COM12", enabled=True, udp_port=10110)
        sup.replace_config(FleetConfig(streams=[stream]))
        sup.start_stream(stream.id)
        hit = sup.running_stream_for_com("COM12")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.label, "A")
        self.assertIsNone(sup.running_stream_for_com("COM7"))


    def test_running_stream_for_mirror_com(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new(
            'A',
            com='COM7',
            enabled=True,
            udp_port=10110,
            serial_mirror_ports=['COM12'],
        )
        sup.replace_config(FleetConfig(streams=[stream]))
        sup.start_stream(stream.id)
        hit = sup.running_stream_for_com('COM12')
        self.assertIsNotNone(hit)
        self.assertEqual(hit.label, 'A')

    def test_start_stream_rejects_busy_udp(self) -> None:
        self._probe_patcher.stop()
        with patch("core.fleet.supervisor.probe_udp_port_available", return_value=False):
            sup = FleetSupervisor(worker_cls=_MockWorker)
            stream = StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110)
            sup.replace_config(FleetConfig(streams=[stream]))
            errors = sup.start_stream(stream.id)
        self.assertEqual(len(errors), 1)
        self.assertIn("busy", errors[0].lower())


    def test_start_blocked_while_starting(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110)
        sup.replace_config(FleetConfig(streams=[stream]))
        worker = _MockWorker(stream.id, sup)
        sup._workers[stream.id] = worker
        worker._state.worker_state = WorkerState.STARTING
        worker._state.active_com = "COM7"
        errors = sup.start_stream(stream.id)
        self.assertEqual(len(errors), 1)
        self.assertIn("still starting", errors[0].lower())

    def test_control_bridge_com_conflict(self) -> None:
        class _Host(QtWidgets.QWidget):
            _starting = False
            bridge = None

            def __init__(self) -> None:
                super().__init__()

            def _is_bridge_running(self) -> bool:
                return False

            @property
            def com_cb(self):
                return self

            def currentText(self) -> str:
                return "COM7"

            def _fleet_control_start_conflict(self, stream: StreamDefinition):
                from ui.mixin import BridgeLogicMixin
                return BridgeLogicMixin._fleet_control_start_conflict(self, stream)

        host = _Host()
        host._starting = True
        sup = FleetSupervisor(host, worker_cls=_MockWorker)
        stream = StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10111)
        sup.replace_config(FleetConfig(streams=[stream]))
        errors = sup.start_stream(stream.id)
        self.assertEqual(len(errors), 1)
        self.assertIn("Control bridge", errors[0])



    def test_replace_config_stops_disabled_stream(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new("A", com="COM7", enabled=True, udp_port=10110)
        sup.replace_config(FleetConfig(streams=[stream]))
        sup.start_stream(stream.id)
        self.assertEqual(
            sup.runtime_states()[stream.id].worker_state,
            WorkerState.RUNNING,
        )
        disabled = StreamDefinition(
            id=stream.id,
            label=stream.label,
            enabled=False,
            com=stream.com,
            baud=stream.baud,
            nmea_mode=stream.nmea_mode,
            net_mode=stream.net_mode,
            udp_host=stream.udp_host,
            udp_port=stream.udp_port,
            udp_remote_host=stream.udp_remote_host,
            udp_remote_port=stream.udp_remote_port,
            tcp_host=stream.tcp_host,
            tcp_port=stream.tcp_port,
            tcp_client_host=stream.tcp_client_host,
            tcp_client_port=stream.tcp_client_port,
            udp_fanout=stream.udp_fanout,
            local_backup=stream.local_backup,
        )
        sup.replace_config(FleetConfig(streams=[disabled]))
        self.assertEqual(
            sup.runtime_states()[stream.id].worker_state,
            WorkerState.IDLE,
        )

    def test_start_all_ignores_disabled_empty_label(self) -> None:
        sup = FleetSupervisor(worker_cls=_MockWorker)
        sup.replace_config(
            FleetConfig(
                streams=[
                    StreamDefinition.new("On", com="COM7", enabled=True, udp_port=10110),
                    StreamDefinition(id="bad", label="", com="COM8", enabled=False, udp_port=10111),
                ]
            )
        )
        self.assertEqual(sup.start_all(), [])


    def test_wait_stream_start_uses_event_loop_not_msleep(self) -> None:
        from PySide6 import QtCore

        sup = FleetSupervisor(worker_cls=_MockWorker)
        stream = StreamDefinition.new('A', com='COM7', enabled=True, udp_port=10110)
        sup.replace_config(FleetConfig(streams=[stream]))
        worker = _MockWorker(stream.id, sup)
        sup._workers[stream.id] = worker
        worker._state.worker_state = WorkerState.RUNNING

        with patch.object(
            QtCore.QThread, 'msleep', side_effect=AssertionError('must not msleep')
        ):
            self.assertIsNone(sup._wait_stream_start_outcome(stream.id, timeout_s=1.0))

    def test_stop_timeout_leaves_error_state(self) -> None:
        from unittest.mock import MagicMock

        from core.fleet.stream_worker import ThreadStreamWorker

        hung = MagicMock()
        hung.isRunning.return_value = True
        hung.wait.return_value = False

        worker = ThreadStreamWorker("s1")
        worker._thread = hung
        worker._set_state(WorkerState.RUNNING)
        worker.stop()

        st = worker.runtime_state()
        self.assertEqual(st.worker_state, WorkerState.ERROR)
        self.assertIn("timed out", st.error_message.lower())
        self.assertFalse(worker.is_active())


    def test_stats_ui_coalesced_when_steady(self) -> None:
        from PySide6 import QtCore
        from core.fleet.stream_worker import ThreadStreamWorker
        from core.fleet.types import WorkerState

        worker = ThreadStreamWorker("s1")
        seen: list[int] = []
        worker.state_changed.connect(lambda *_a: seen.append(1))
        worker._set_state(WorkerState.RUNNING)
        seen.clear()
        stats = {"drops_n2s": 0, "drops_s2n": 0, "n2s_q": 0, "s2n_q": 0, "hz_up": 50.0}
        for _ in range(20):
            worker._on_stats(dict(stats))
        self.assertEqual(len(seen), 1)

if __name__ == "__main__":
    unittest.main()