# Serial Link — deferred roadmap

Items bookmarked for later epics. **Not in active development** unless promoted to a `specs/00N-*` folder.

---

## MAVLink GPS injector (NMEA → MP map position)

**Status:** Bookmarked · **Priority:** P2 sandbox · **First discussed:** 2026-06  
**Trigger to start:** After core bridge/Cube/Tailnet workflows are stable; optional one-day MAVProxy bench validation on boat stack.

### Problem

Survey operators (e.g. Norbit-style stacks) want **Trimble/Applanix GNSS** to appear on **Mission Planner’s map** without wiring a second GPS module to the Cube’s GPS UART. Norbit often uses **MAVProxy** (`gpsinput`) to inject mavlink GPS into the stream MP consumes, while **DCT** uses NMEA on UDP **40810** separately.

Serial Link today:

- **Proven:** Cube COM ↔ UDP (Raw) + remote MP over **Tailscale** (full mavlink GCS).
- **Proven:** INS/Applanix NMEA → UDP listen → COM or DCT (`NORBIT DCT` preset, port **40810**).
- **Gap:** No NMEA → mavlink GPS injection; bridge is a **byte pipe**, not a mavlink router.

### Goal (v1 of this epic)

**MP map / telemetry shows survey GNSS** by emitting mavlink GPS messages on the **Cube bridge UDP fan-out**, while keeping **transparent raw passthrough** on the Cube COM leg.

**Explicitly defer v1:** Cube autopilot navigation on injected GPS (`GPS_TYPE_MAV`, `GPS_INPUT`, parameter tuning) — separate phase.

### Reference architecture

```text
Applanix/Trimble ──NMEA UDP (e.g. :40810)──► Serial Link
                                              │ parse GGA/RMC → latest fix
Cube COM ◄──────── raw MAVLink ────────────► Serial Link
                                              │
                                              ├── transparent COM ↔ UDP (unchanged)
                                              └── + GLOBAL_POSITION_INT / GPS_RAW_INT
                                                  @ ~5 Hz to UDP peers (MP)
```

DCT continues on **40810 NMEA** unchanged. Cube preset stays **Raw** on **14550** (or fleet port). Injector is an **optional mode**, off by default.

### Scope tiers (effort — one dev familiar with repo)

| Tier | Deliverable | Estimate |
| ---- | ----------- | -------- |
| **MVP** | GGA/RMC parser; encode 1–2 GPS mavlink msgs; inject to Cube-port UDP peers only; toggle + preset; unit tests | **1–2 weeks** |
| **Field-ready** | MAVLink v1/v2 wire compat; staleness alerts; fix-quality gating; sysid/compid; MP + tailnet bench proof; operator doc | **3–5 weeks** |
| **Autopilot on survey GPS** | `GPS_INPUT` to Cube, `GPS_TYPE_MAV`, RTK flags, conflict with onboard GPS, boat validation | **+2–4 weeks** |

### Technical notes (for resume)

- Repo has `nmea_codec.py`; **no mavlink encoder** today — add `pymavlink` or minimal v2 encoder (PyInstaller size tradeoff).
- Inject on **UDP egress** to MP clients; do not corrupt Cube↔COM byte stream.
- Cube mavlink is **v2** (`fd` frames). Use distinct component id for injected GPS.
- Risk: Cube also sending GPS — MP may need priority/dedup rules.
- **Pre-build validation:** one boat-PC day with **MAVProxy** + same Applanix/Cube wiring to confirm message types and rates.

### Likely files (when started)

- `mavlink_gps_inject.py` (or `nmea_to_mavlink.py`) — parse + encode + rate limit
- `bridge_core.py` — optional injector hook on `_send_net` / parallel timer
- `ui/mixin.py`, presets, Tools toggle
- `test_mavlink_gps_inject.py`, `docs/OPERATOR_GUIDE.md` § Norbit+Cube combined
- Optional preset: **Cube + Applanix GPS** (40810 NMEA source + 14550 mavlink)

### Related today

- [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) §5.6 (Cube / MP), §6.5 (survey stack theory)
- [NORBIT_DCT.md](NORBIT_DCT.md) (DCT on 40810)
- Presets: **Cube MAVLink**, **NORBIT DCT**, user **mp**
- Argo charter sandbox item #3 / MAVLink planner — intentionally **not** full MAVProxy clone

### Out of scope for this epic

- Full MAVProxy module parity (missions, scripts, console)
- MAVLink mission planner / post-processing
- Kernel virtual COM or passive sniff

---

## How to promote a bookmark

1. Copy this section into `specs/00N-mavlink-gps-inject/spec.md` (Spec Kit).
2. Run plan/tasks workflow per `.cursor/skills/speckit-*`.
3. Remove or mark **In progress** here when the spec folder exists.
