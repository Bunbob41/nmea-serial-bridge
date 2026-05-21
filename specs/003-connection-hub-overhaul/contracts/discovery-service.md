# Contract: DiscoveryService

**Module**: `discovery_service.py` (no Qt imports)

## API

```python
def scan_serial_ports(
    *,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
    stable_counts: dict[str, int],
    stable_polls_required: int = 2,
) -> tuple[list[SerialDeviceInfo], dict[str, int]]:
    """Returns devices and updated stability counters."""

def probe_udp_port_available(host: str, port: int) -> bool:
    """True if bind would succeed (port free)."""

def build_network_cards(
    *,
    presets: list[dict],
    active_preset: str | None,
    bridge_stats: dict | None,
    default_udp_host: str,
    default_udp_port: int,
) -> list[NetworkCardInfo]:
    """Passive/network contextual cards."""

def build_snapshot(
    *,
    keywords: Sequence[str],
    stable_counts: dict[str, int],
    presets: list[dict],
    active_preset: str | None,
    bridge_stats: dict | None,
    udp_host: str,
    udp_port: int,
) -> DiscoverySnapshot:
    """Single entry for UI poll."""
```

## Threading

- Callable from any thread; UI must marshal to main thread before QWidget updates.
- No global mutable state inside service except passed-in `stable_counts` dict owned by mixin.

## Compatibility

- Keyword list and stability semantics MUST remain compatible with `test_auto_discovery.py` expectations (migrate tests to new module).

## Verification

- `test_discovery_service.py` — parity with prior auto_discovery tests + network probe mocks.
