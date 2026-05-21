# Contract: Bridge Session

**Applies to**: One Running interval (FR-001, FR-002, FR-013)

## Preconditions

- Valid COM and network configuration selected
- COM not exclusively held by another application

## Operations

| Operation | Input | Outcome |
|-----------|-------|---------|
| Start | Operator Start | Serial open (or clear error); network bound/connected; state=Running |
| Stop | Operator Stop | Tasks torn down; COM released; UDP peers cleared |
| Status | — | Serial line + network line + NMEA mode visible |

## Postconditions (Stop)

- `udp_peer_count` = 0
- New Start begins with empty peer registry

## Errors

- COM in use → must not report healthy Running without open serial
