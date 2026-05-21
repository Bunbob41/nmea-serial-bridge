# Contract: TCP Sink Mirror

**Module**: `bridge_core.py` — `TcpSinkConfig`, methods on `SerialNetBridge`

## Configuration

```python
@dataclass
class TcpSinkConfig:
    enabled: bool = False
    bind_host: str = "0.0.0.0"
    bind_port: int = 10111
    max_clients: int = 8
```

Passed to `SerialNetBridge(..., tcp_sink: TcpSinkConfig | None = None)`.

## Behavior

| Event | Action |
|-------|--------|
| `start()` | If enabled, `asyncio.start_server` on sink port; failure → log + disable sink only |
| `_send_net(data)` | After primary UDP/TCP send completes, `_mirror_to_tcp_sink(data)` |
| Client connect | Add writer to bounded set |
| Write failure | Remove client; increment optional `sink_drops` stat |
| `abort_now()` | Close server; clear clients |

## Invariants

- Primary `NetMode` and UDP fan-out (`_udp_peers`) behavior unchanged when sink enabled.
- Sink receives **same bytes** as serial→net path post-codec (identical to primary egress chunk).
- Sink does NOT read from network toward serial (mirror outbound only).

## Stats keys (for hub network card)

- `tcp_sink_clients`: int
- `tcp_sink_drops`: int
- `tcp_sink_enabled`: bool

## Verification

- `test_tcp_sink.py`: mock server; verify UDP fan-out + sink both receive payload.
- Manual: `quickstart.md` SC-302 procedure.
