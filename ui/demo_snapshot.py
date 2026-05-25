"""Capture and restore operator session state around Product Demo."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from PySide6 import QtWidgets

from ui.connection_fields import read_baud_widget


@dataclass(frozen=True)
class OperatorSessionSnapshot:
    com_port: str
    baud: int
    network_mode: str
    udp_host: str
    udp_port: int
    remote_host: str
    remote_port: int
    tcp_srv_host: str
    tcp_srv_port: int
    tcp_cli_host: str
    tcp_cli_port: int
    udp_fanout: bool
    tcp_sink_enabled: bool
    tcp_sink_port: int
    nmea_mode: str
    nmea_types: tuple[str, ...]
    active_preset_name: Optional[str]
    survey_pc_ip: str
    survey_subnet: str
    survey_ins_ip: str
    survey_notes: str
    bridge_was_running: bool
    bridge_was_starting: bool
    main_tab_index: Optional[int]
    tools_nav_row: Optional[int]
    field_drawer_open: Optional[bool]
    captured_at_monotonic: float


def _network_mode_from_host(host: QtWidgets.QWidget) -> str:
    if not host.chk_advanced_net.isChecked():  # type: ignore[attr-defined]
        return "udp_listen"
    if host.rb_udp_remote.isChecked():  # type: ignore[attr-defined]
        return "udp_remote"
    if host.rb_tcp_server.isChecked():  # type: ignore[attr-defined]
        return "tcp_server"
    return "tcp_client"


def _parse_port_text(text: str, default: int = 0) -> int:
    try:
        return int(str(text).strip())
    except ValueError:
        return default


def _nmea_types_from_host(host: QtWidgets.QWidget) -> tuple[str, ...]:
    checks = getattr(host, "_nmea_type_checks", None)
    if not checks:
        return ()
    if hasattr(host, "_nmea_mode_label"):
        if host._nmea_mode_label() != "strict":  # type: ignore[attr-defined]
            return ()
    return tuple(st for st, cb in checks.items() if cb.isChecked())


def capture_operator_snapshot(host: QtWidgets.QWidget) -> OperatorSessionSnapshot:
    try:
        baud = int(read_baud_widget(host.baud_edit))  # type: ignore[attr-defined]
    except ValueError:
        baud = 0

    fanout_chk = getattr(host, "chk_udp_fanout", None)
    sink_chk = getattr(host, "chk_tcp_sink_enable", None)
    tcp_sink_port = 0
    if getattr(host, "tcp_sink_port", None) is not None:
        tcp_sink_port = _parse_port_text(host.tcp_sink_port.text(), 0)  # type: ignore[attr-defined]

    main_tab_index: Optional[int] = None
    main_tabs = getattr(host, "_main_tabs", None)
    if main_tabs is not None:
        main_tab_index = int(main_tabs.currentIndex())

    tools_nav_row: Optional[int] = None
    tools_nav = getattr(host, "_tools_nav", None)
    if tools_nav is not None:
        tools_nav_row = int(tools_nav.currentRow())

    field_drawer_open: Optional[bool] = None
    drawer = getattr(host, "_drawer_btn", None)
    if drawer is not None:
        field_drawer_open = bool(drawer.isChecked())

    active = getattr(host, "_active_preset_name", None)
    survey_pc = ""
    survey_subnet = "255.255.255.0"
    survey_ins = ""
    survey_notes = ""
    if hasattr(host, "preset_pc_ip"):
        survey_pc = host.preset_pc_ip.text().strip()  # type: ignore[attr-defined]
        survey_subnet = host.preset_subnet.text().strip()  # type: ignore[attr-defined]
        survey_ins = host.preset_ins_ip.text().strip()  # type: ignore[attr-defined]
        survey_notes = host.preset_notes.toPlainText().strip()  # type: ignore[attr-defined]

    return OperatorSessionSnapshot(
        com_port=host.com_cb.currentText().strip(),  # type: ignore[attr-defined]
        baud=baud,
        network_mode=_network_mode_from_host(host),
        udp_host=host.udp_host.text().strip(),  # type: ignore[attr-defined]
        udp_port=_parse_port_text(host.udp_port.text(), 10110),  # type: ignore[attr-defined]
        remote_host=host.remote_host.text().strip(),  # type: ignore[attr-defined]
        remote_port=_parse_port_text(host.remote_port.text(), 0),  # type: ignore[attr-defined]
        tcp_srv_host=host.tcp_srv_host.text().strip(),  # type: ignore[attr-defined]
        tcp_srv_port=_parse_port_text(host.tcp_srv_port.text(), 0),  # type: ignore[attr-defined]
        tcp_cli_host=host.tcp_cli_host.text().strip(),  # type: ignore[attr-defined]
        tcp_cli_port=_parse_port_text(host.tcp_cli_port.text(), 0),  # type: ignore[attr-defined]
        udp_fanout=fanout_chk is None or fanout_chk.isChecked(),
        tcp_sink_enabled=sink_chk is not None and sink_chk.isChecked(),
        tcp_sink_port=tcp_sink_port,
        nmea_mode=host._nmea_mode_label() if hasattr(host, "_nmea_mode_label") else "passthrough",  # type: ignore[attr-defined]
        nmea_types=_nmea_types_from_host(host),
        active_preset_name=active.strip() if active else None,
        survey_pc_ip=survey_pc,
        survey_subnet=survey_subnet,
        survey_ins_ip=survey_ins,
        survey_notes=survey_notes,
        bridge_was_running=getattr(host, "bridge", None) is not None,
        bridge_was_starting=bool(getattr(host, "_starting", False)),
        main_tab_index=main_tab_index,
        tools_nav_row=tools_nav_row,
        field_drawer_open=field_drawer_open,
        captured_at_monotonic=time.monotonic(),
    )


def _apply_network_mode(host: QtWidgets.QWidget, mode: str) -> None:
    advanced = mode != "udp_listen"
    host.chk_advanced_net.setChecked(advanced)  # type: ignore[attr-defined]
    if mode == "udp_listen":
        host.rb_udp_listen.setChecked(True)  # type: ignore[attr-defined]
    elif mode == "udp_remote":
        host.rb_udp_remote.setChecked(True)  # type: ignore[attr-defined]
    elif mode == "tcp_server":
        host.rb_tcp_server.setChecked(True)  # type: ignore[attr-defined]
    else:
        host.rb_tcp_client.setChecked(True)  # type: ignore[attr-defined]
    if hasattr(host, "_mode_toggle"):
        host._mode_toggle()  # type: ignore[attr-defined]


def restore_operator_snapshot(
    host: QtWidgets.QWidget,
    snap: OperatorSessionSnapshot,
    *,
    demo_started_bridge: bool = False,
    demo_stopped_user_bridge: bool = False,
) -> None:
    """Restore Connect fields and bridge run state from a captured snapshot."""
    preset_data: dict[str, Any] = {
        "com": snap.com_port,
        "baud": snap.baud,
        "udp_host": snap.udp_host,
        "udp_port": snap.udp_port,
        "udp_fanout": snap.udp_fanout,
        "tcp_sink_enabled": snap.tcp_sink_enabled,
        "tcp_sink_port": snap.tcp_sink_port or 10111,
        "pc_ip": snap.survey_pc_ip,
        "subnet_mask": snap.survey_subnet,
        "ins_ip": snap.survey_ins_ip,
        "notes": snap.survey_notes,
        "nmea_mode": snap.nmea_mode,
    }
    if snap.nmea_types:
        preset_data["nmea_types"] = list(snap.nmea_types)

    if hasattr(host, "_apply_preset_data"):
        host._apply_preset_data(preset_data, name=snap.active_preset_name, log=False)  # type: ignore[attr-defined]
    else:
        if hasattr(host, "_apply_com_preset"):
            host._apply_com_preset(  # type: ignore[attr-defined]
                snap.com_port,
                snap.baud,
                snap.udp_host,
                snap.udp_port,
            )

    host.udp_host.setText(snap.udp_host)  # type: ignore[attr-defined]
    host.udp_port.setText(str(snap.udp_port))  # type: ignore[attr-defined]
    host.remote_host.setText(snap.remote_host)  # type: ignore[attr-defined]
    host.remote_port.setText(str(snap.remote_port) if snap.remote_port else "")  # type: ignore[attr-defined]
    host.tcp_srv_host.setText(snap.tcp_srv_host)  # type: ignore[attr-defined]
    host.tcp_srv_port.setText(str(snap.tcp_srv_port) if snap.tcp_srv_port else "")  # type: ignore[attr-defined]
    host.tcp_cli_host.setText(snap.tcp_cli_host)  # type: ignore[attr-defined]
    host.tcp_cli_port.setText(str(snap.tcp_cli_port) if snap.tcp_cli_port else "")  # type: ignore[attr-defined]

    fanout_chk = getattr(host, "chk_udp_fanout", None)
    if fanout_chk is not None:
        fanout_chk.setChecked(snap.udp_fanout)
    sink_chk = getattr(host, "chk_tcp_sink_enable", None)
    if sink_chk is not None:
        sink_chk.setChecked(snap.tcp_sink_enabled)
    if getattr(host, "tcp_sink_port", None) is not None and snap.tcp_sink_port:
        host.tcp_sink_port.setText(str(snap.tcp_sink_port))  # type: ignore[attr-defined]

    _apply_network_mode(host, snap.network_mode)

    if hasattr(host, "_apply_preset_nmea_mode"):
        host._apply_preset_nmea_mode(preset_data)  # type: ignore[attr-defined]

    if snap.active_preset_name and hasattr(host, "_set_active_preset"):
        host._set_active_preset(snap.active_preset_name)  # type: ignore[attr-defined]
    elif hasattr(host, "_set_active_preset"):
        host._set_active_preset(None)  # type: ignore[attr-defined]

    main_tabs = getattr(host, "_main_tabs", None)
    if main_tabs is not None and snap.main_tab_index is not None:
        idx = max(0, min(snap.main_tab_index, main_tabs.count() - 1))
        main_tabs.setCurrentIndex(idx)

    tools_nav = getattr(host, "_tools_nav", None)
    if tools_nav is not None and snap.tools_nav_row is not None:
        row = max(0, min(snap.tools_nav_row, tools_nav.count() - 1))
        tools_nav.setCurrentRow(row)

    drawer = getattr(host, "_drawer_btn", None)
    if drawer is not None and snap.field_drawer_open is not None:
        drawer.setChecked(snap.field_drawer_open)

    if hasattr(host, "_update_field_connect_summary"):
        host._update_field_connect_summary()  # type: ignore[attr-defined]
    if hasattr(host, "_refresh_nmea_status_chip"):
        host._refresh_nmea_status_chip()  # type: ignore[attr-defined]

    running = getattr(host, "bridge", None) is not None or bool(
        getattr(host, "_starting", False)
    )
    want_running = snap.bridge_was_running or snap.bridge_was_starting

    if want_running and not running:
        if hasattr(host, "start_bridge"):
            host.start_bridge()  # type: ignore[attr-defined]
    elif not want_running and running:
        if demo_started_bridge or demo_stopped_user_bridge:
            if hasattr(host, "stop_bridge"):
                host.stop_bridge()  # type: ignore[attr-defined]

    if hasattr(host, "_log_ui"):
        preset_bit = f" preset «{snap.active_preset_name}»" if snap.active_preset_name else ""
        host._log_ui(  # type: ignore[attr-defined]
            f"[Demo] Restored your session{preset_bit} "
            f"({snap.com_port} @ {snap.baud}, {snap.network_mode}, NMEA {snap.nmea_mode})."
        )
