# Contract: Traffic Quality on Hub Cards

**Modules**: `discovery_service.py` or `ui/hub_quality.py` (pure fn), `ui/connection_hub.py`

## Snapshot builder

```python
@dataclass(frozen=True)
class TrafficQualitySnapshot:
    state: str  # idle | ok | warn
    hz_up: float
    hz_down: float
    drops_s2n: int
    drops_n2s: int
    rej_s2n: int
    rej_n2s: int
    nav_stale: bool
    summary: str

def quality_from_bridge_stats(stats: dict) -> TrafficQualitySnapshot:
    """Map merged stats dict from mixin._merge_bridge_stats."""
```

## UI mapping

| state | Chip style | Subtitle example |
|-------|------------|------------------|
| idle | neutral | "Stopped" |
| ok | positive | "↑1.0 Hz · OK" |
| warn | warning | "↑1.0 Hz · 3 drops · 2 rej" |

## Update path

- `BridgeLogicMixin._stats_from_bridge` → `connection_hub.set_quality(selected_id, snapshot)` when Running.
- Coalesce: max once per 2 s unless transition idle↔ok↔warn.

## Verification

- `test_hub_quality.py` or tests in `test_connection_hub.py` for `quality_from_bridge_stats` thresholds.
