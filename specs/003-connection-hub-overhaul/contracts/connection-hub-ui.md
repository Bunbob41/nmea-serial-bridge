# Contract: Connection Hub UI

**Module**: `ui/connection_hub.py`

## Widgets

| Widget | Responsibility |
|--------|----------------|
| `EndpointCardWidget` | Displays one Serial or Network card; emits `clicked(device_id)` |
| `ConnectionHubWidget` | Grid of cards + selection state + refresh from `DiscoverySnapshot` |

## Signals (Qt)

```python
class ConnectionHubWidget(QtWidgets.QWidget):
    selection_changed = QtCore.Signal(str)  # device_id
    manual_override_requested = QtCore.Signal()
```

## Parent integration (`connect_panels.py`)

- Panel key `connection` body = `ConnectionHubWidget` + below it `ManualOverridePanel` (wraps legacy controls).
- `REQUIRED_CONNECT_PANELS` unchanged: `run`, `connection`.
- Expanded height cap `connection` may increase to ~400–480 px (within scroll).

## Mixin bindings

| Mixin method | Action |
|--------------|--------|
| `_on_discovery_snapshot(snapshot)` | Hub `set_snapshot` |
| `_on_hub_selection(device_id)` | Load LastKnownGood; set `com_cb` / network widgets |
| `_collect_bridge_config()` | Prefer hub selection unless override dirty |
| `_on_start_success()` | `save_last_known_good(device_id, config)` |

## Field layout (Phase 2)

- Minimum: link button “Connection hub…” switches to Standard tab Connect or opens dialog hosting `ConnectionHubWidget`.

## Verification

- `test_connection_hub.py`: QTest — snapshot renders N cards; click selects id.
- Manual: SC-301 timing walkthrough.
