# Data Model: UI & Workflow Journey Modernization

**Feature**: `008-ui-journey-modernization` | **Date**: 2026-05-24

## OperatorSessionSnapshot

Captured from the host main window **once** when Product Demo opens; restored on demo exit.

| Field | Type | Notes |
|-------|------|-------|
| `com_port` | string | `com_cb.currentText()` |
| `baud` | int | From baud widget |
| `network_mode` | enum | `udp_listen` \| `udp_remote` \| `tcp_client` \| `tcp_server` |
| `udp_host` | string | Listen bind |
| `udp_port` | int | Listen port |
| `remote_host` | string | When advanced remote/client |
| `remote_port` | int | When applicable |
| `tcp_srv_host` | string | TCP server mode |
| `tcp_srv_port` | int | |
| `tcp_cli_host` | string | TCP client mode |
| `tcp_cli_port` | int | |
| `udp_fanout` | bool | |
| `tcp_sink_enabled` | bool | |
| `tcp_sink_port` | int | |
| `nmea_mode` | enum | `passthrough` \| `strict` \| `raw` |
| `nmea_types` | list[string] | Strict checkboxes only |
| `active_preset_name` | string \| null | Display name, not file contents |
| `bridge_was_running` | bool | `host.bridge is not None` |
| `bridge_was_starting` | bool | `host._starting` |
| `main_tab_index` | int \| null | Standard layout |
| `tools_nav_row` | int \| null | If Tools visible |
| `field_drawer_open` | bool \| null | Field layout |
| `captured_at_monotonic` | float | Diagnostics only |

**Validation**: All string ports numeric 1–65535 when restored; COM non-empty optional if was empty before.

**Lifecycle**: `idle → captured → demo_active → restoring → idle`

---

## DemoSessionState

Owned by `ProductDemoDialog`; never written to disk.

| Field | Type | Notes |
|-------|------|-------|
| `presenter_index` | int | Manual script position |
| `auto_running` | bool | `DemoRunner.running()` |
| `phase_label` | string | Manual / Auto / Complete |
| `demo_started_bridge` | bool | True if demo invoked `start_bridge` |
| `demo_stopped_bridge_for_exit` | bool | Track for restore policy |
| `snapshot` | OperatorSessionSnapshot \| null | Set at open |
| `prefs_write_blocked` | bool | Gateway flag |

---

## DemoHostGateway (behavioral entity)

Not persisted; mediates host mutations during demo.

| Operation | Preconditions | Effects |
|-----------|---------------|---------|
| `enter(host)` | No active demo | Capture snapshot; set `host._demo_session_active` |
| `run_step_action(fn)` | demo active | Execute `fn(host)`; log `[Demo]` |
| `exit(host)` | demo active | Stop runner/diag; restore snapshot; clear flag |
| `reset_demo_script()` | demo active | Reset presenter index only; no host restore |

**Invariants**:

- While `prefs_write_blocked`, `save_preset`, `push_recent_session`, and connect-panel size capture MUST NOT persist demo-side effects.
- `bench_config.save_preset` MUST NOT be called from demo steps without gateway override (boat preset step uses `_apply_production_preset` today—must not save file).

---

## UiAuditItem

| Field | Type | Notes |
|-------|------|-------|
| `audit_id` | string | e.g. `STD-CONNECT-01` |
| `layout` | enum | standard \| field \| minimal \| logfirst \| web |
| `area` | string | Connect, Tools/Phone, Demo, … |
| `issue_type` | enum | copy \| layout \| placeholder \| dead_control |
| `severity` | enum | P0 \| P1 \| P2 |
| `status` | enum | open \| fixed \| deferred |
| `verifier` | string | human or test id |

---

## RecentSessionEntry (existing — alignment)

Already stored in `ui_prefs.json`; audit ensures display string includes `nmea_mode` (implemented v1.9.79+). No schema change required.

---

## LayoutPreferenceBundle (existing — migration)

`connect_panels` prefs: order, collapsed, sizes, toolbar_order, hidden.

**Migration rules**:

- Drop unknown toolbar keys (`reset_sizes`)
- Ignore saved panel heights below `_MIN_VALID_SAVED_HEIGHT`

---

## Relationships

```text
Host Window (BridgeLogicMixin)
  ├─ owns bridge session (bridge_core)     ← snapshot records running state
  ├─ persists via ui_prefs / bench_config  ← blocked during DemoSessionState.prefs_write_blocked
  └─ ProductDemoDialog
        ├─ DemoSessionState (presenter UI)
        ├─ DemoRunner (auto-play timing)
        └─ DemoHostGateway → OperatorSessionSnapshot
```
