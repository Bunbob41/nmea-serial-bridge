# Quickstart: Connection Hub Phase 2 (dev verification)

**Prerequisites**: Phase 1 hub shipped (v1.5.x+), com0com bench pair, Python 3.10+.

## Phase A — Network scanner (unit)

```powershell
python -m unittest test_network_scanner.py test_port_release.py -v
```

Mock ARP sample:

```powershell
python -c "from network_scanner import list_lan_hosts; print(list_lan_hosts(arp_output=open('tests/fixtures/arp_sample.txt').read()))"
```

(Add fixture during implement.)

## Phase B — Discovery refresh (UI)

1. `python bridge_gui.py` — Standard layout.
2. Connect → **Connection Hub** → **Refresh discovery**.
3. Expect serial cards + **discovered** network cards (LAN ARP + UDP probe) within ~8 s.
4. **Unlock ports** after holding COM with PuTTY — should report success or “Stop bridge first” if Running.

## Phase C — Layout / clipping (SC-401)

1. Window 900×380; expand **Serial & network** panel.
2. Confirm COM port text on selected card is not horizontally clipped.
3. Drag splitter — card grid grows; only card area scrolls.

## Phase D — Traffic quality (SC-405)

1. Start bridge; `python bench_udp_test.py --seconds 30`.
2. Active card shows **OK** / Hz subtitle.
3. Stop UDP sender briefly or enable strict rejects — card shows **warn** within 2 s.

## Phase E — LAN discovery (SC-404)

1. Two terminals: `python bench_udp_test.py` and `python bench_fanout_probe.py` (different source ports).
2. Refresh discovery — two distinguishable network-related cards or labels.
3. Select card → Start uses matching listen configuration.

## Phase F — Regression

```powershell
python verify_all.py
python tools/run_unittests.py
```

Quit OpenCPN / stop bridge so UDP 10110 is free before verify.

## Version

Expect **v1.6.0** in window title after release.
