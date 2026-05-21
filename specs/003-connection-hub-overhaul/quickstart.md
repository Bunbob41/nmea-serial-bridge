# Quickstart: Connection Hub Overhaul (dev verification)

## Phase A — Discovery service

```powershell
python -m unittest test_discovery_service.py test_auto_discovery.py -v
```

Plug/unplug GNSS USB; run one-off:

```powershell
python -c "from discovery_service import build_snapshot; print(build_snapshot(...))"
```

(After module exists.)

## Phase B — Connection Hub UI

1. `python bridge_gui.py` — Standard layout.
2. Connect tab → **Connection Hub** shows serial cards.
3. Click card → COM/baud filled; **Start** on Run panel.
4. Toggle **Manual override** → legacy UDP/TCP fields visible.

## Phase C — TCP sink + fan-out (SC-302)

1. Bridge Running: UDP listen :10110, fan-out on, TCP sink :10111 enabled.
2. Terminal A: `python bench_udp_test.py --seconds 30`
3. Terminal B: `python bench_fanout_probe.py --seconds 30`
4. Terminal C: TCP client `python bench_tcp_stress.py` or netcat to `127.0.0.1:10111` — confirm mirror receives serial-originated bytes.
5. `python -m unittest test_tcp_sink.py test_udp_fanout.py -v`

## Phase D — Regression

```powershell
python verify_all.py
python -m unittest discover -s . -p "test_*.py" -q
```

Free UDP 10110/10111 (quit OpenCPN) before verify.

## Field smoke (SC-303)

1. `python bridge_gui.py --ui field`
2. Start/Stop visible on strip; open HUD; 15 min with `bench_udp_test.py --hz 5 --seconds 900`

## Version

Expect **v1.5.0** in window title after release bump.
