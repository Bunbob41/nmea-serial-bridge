# Contract: Network Scanner

**Module**: `network_scanner.py` (no Qt imports)

## API

```python
@dataclass(frozen=True)
class NetworkScanResult:
    host: str
    mac: str
    open_ports: tuple[int, ...]
    method: str
    label: str
    stale: bool
    last_seen_mono: float

def list_lan_hosts(*, arp_output: str | None = None) -> list[str]:
    """IPv4 addresses on local subnet from ARP table (mockable)."""

def probe_host_udp(
    host: str,
    ports: Sequence[int],
    *,
    timeout_s: float = 0.25,
    probe_payload: bytes = b"$PING\r\n",
) -> tuple[int, ...]:
    """Return ports that responded (recv or no error on send)."""

def scan_network(
    *,
    ports: Sequence[int] = (10110, 4001, 10111),
    max_hosts: int = 32,
    deadline_s: float = 6.0,
    skip_bind_port: int | None = None,
) -> list[NetworkScanResult]:
    """Full scan with budget; skip_bind_port avoids probing while bridge listens."""
```

## Integration

- `discovery_service.build_snapshot(..., network_scan_results=...)` converts results to `NetworkCardInfo`.
- Called only from `DiscoveryScanWorker` thread or tests.

## Invariants

- No `bind()` on `skip_bind_port` when set.
- Scan completes or returns partial results before `deadline_s`.
- Stdlib only (`subprocess`, `socket`, `ipaddress`, `re`).

## Verification

- `test_network_scanner.py` — mocked ARP output, mocked UDP, budget timeout.
