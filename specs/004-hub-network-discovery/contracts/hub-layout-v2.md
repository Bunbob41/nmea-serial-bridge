# Contract: Connection Hub Layout v2

**Module**: `ui/connection_hub.py`, `ui/connect_panels.py`

## Layout

| Region | Widget | Scroll | Stretch |
|--------|--------|--------|---------|
| Toolbar | Refresh discovery, Unlock ports | No | Fixed |
| Card area | `QScrollArea` → grid | **Yes** | 1 |
| Manual override | `QGroupBox` | No | 0 |

## `ConnectionHubWidget` additions

```python
refresh_requested = QtCore.Signal()
unlock_requested = QtCore.Signal()

def set_quality(self, device_id: str | None, quality: TrafficQualitySnapshot | None) -> None: ...
def set_scan_busy(self, busy: bool) -> None: ...
```

## `connect_panels` rules

- `connection` panel default expanded height ≥ 360 px when window ≥ 900 px wide.
- Splitter sizes persist via existing `ui_prefs` connect panel prefs.
- **Do not** wrap `ConnectionHubWidget` in a second outer scroll (FR-401).

## Card grid

- `QGridLayout` columns: `max(1, min(3, floor(width / 240)))`.
- `EndpointCardWidget` minimum width 220 px; title elide middle if needed.

## Verification

- `test_connection_hub.py` — toolbar signals, grid column count at width.
- `test_connect_panel_sizes.py` — connection panel min height updated.
- Manual: SC-401 resize test in quickstart.
