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
5. **Client B** — second terminal: `python bench_fanout_probe.py --seconds 20` (registers + listens). Generate COM→net via com0com paired port or live serial.
6. **Procedure detail** — see `docs/OPERATOR_GUIDE.md` §5.5.
7. **Observe** — both clients receive serial-originated UDP when fan-out on; status shows `2 peers` after second sender.
8. **Single-link** — Stop → Start, uncheck fan-out, repeat with two senders; only the **last** sender receives serial→net.
9. **Automated** — `python -m unittest test_udp_fanout.py test_baseline_docs.py -v`
10. **Suite** — `python verify_all.py` (see traceability **Environmental waivers** if OpenCPN holds UDP 10110)
11. **SC-003 (optional long)** — [sc003-hud-stress-validation.md](./sc003-hud-stress-validation.md): HUD + `bench_udp_test.py --hz 5 --seconds 1800`

## Success

- SC-002: completed without second bridge instance
- SC-004: two clients receive traffic with fan-out enabled within 5 s of serial activity
- SC-003: HUD stress procedure documented and runnable per sc003-hud-stress-validation.md

See [traceability.md](./traceability.md) for FR mapping (including FR-021 auto-discovery).
