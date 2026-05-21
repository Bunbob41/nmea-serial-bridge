# Contract: UDP Listen Fan-Out

**Applies to**: `NetMode.UDP_LISTEN` only (FR-011, FR-012, FR-013, FR-020)

## Registration

- Any inbound datagram from address `A` adds `A` to the peer set for the session.
- First peer: status `peer (host, port)`; additional: `N peers`.

## Serial → network

| `udp_fanout` | Behavior |
|--------------|----------|
| true (default) | `sendto(data, peer)` for each peer in set |
| false | `sendto(data, last_udp_addr)` only |

## Peer removal

- Failed `sendto` for a peer removes that peer from the set.
- Stop/abort clears entire set.

## Non-applicability

- UDP remote and TCP modes: single endpoint; no fan-out.

## Verification

- Automated: `test_udp_fanout.py`
- Manual: [quickstart.md](../quickstart.md)
