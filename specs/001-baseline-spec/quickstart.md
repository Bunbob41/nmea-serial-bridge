# Quickstart: Baseline Verification

Validate baseline behavior in ~15 minutes on a bench PC (com0com optional for serial leg).

## Prerequisites

- Bridge app installed (source or frozen exe)
- com0com pair **or** one physical COM
- Python 3.10+ on PATH for bench scripts

## Steps

1. **Launch** Standard layout → load bench preset → confirm UDP listen port (e.g. 10110).
2. **Fan-out** — leave **Fan-out — send serial data to all UDP peers** checked (default).
3. **Start bridge** → status shows Running + UDP listen.
4. **Client A** — `python bench_udp_test.py --seconds 2` (registers peer, sends NMEA).
5. **Client B** — second terminal: `python bench_fanout_probe.py --register-only` then run com0com echo or `bench_udp_test` on serial side to generate COM→net traffic.
6. **Observe** — both clients receive serial-originated UDP when fan-out on; status shows `2 peers` after second sender.
7. **Single-link** — Stop → Start, uncheck fan-out, repeat with two senders; only the **last** sender receives serial→net.
8. **Automated** — `python -m unittest test_udp_fanout.py -v`
9. **Suite** — `python verify_all.py`

## Success

- SC-002: completed without second bridge instance
- SC-004: two clients receive traffic with fan-out enabled within 5 s of serial activity

See [traceability.md](./traceability.md) for FR mapping.
