# Contract: Smart Release

**Module**: `port_release.py` (no Qt); invoked from `ui/mixin.py`

## API

```python
@dataclass
class PortLockState:
    port: str
    locked: bool
    reason: str
    safe_to_release: bool
    last_attempt_ok: bool | None

def probe_com_lock(port: str, baud: int, *, timeout_s: float = 5.0) -> PortLockState:
    """Open/close probe; does not leave port open."""

def smart_release_com(
    port: str,
    baud: int,
    *,
    bridge_running: bool,
    bridge_com: str | None,
) -> PortLockState:
    """Release only if safe; blocked when bridge_running and port == bridge_com."""

def hint_udp_listen_busy(host: str, port: int) -> str | None:
    """Human message if port not bindable; None if OK."""
```

## Mixin binding

| UI control | Handler |
|------------|---------|
| **Unlock ports** | `_on_hub_unlock_ports()` |
| **Refresh discovery** | `_on_hub_refresh_discovery()` (starts worker; may call release only on user unlock) |

## Invariants

- Never close `bridge.serial_writer` from release module.
- Permission errors return actionable text (PuTTY, other bridge).

## Verification

- `test_port_release.py` — blocked when running, success on mock serial.
