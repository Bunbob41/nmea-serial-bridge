# Research: Fleet Multi-Stream

**Feature**: [`spec.md`](spec.md)  
**Date**: 2026-06-18

---

## Decision 1: Worker hosting model

### Context

Each fleet row needs one `SerialNetBridge` on an asyncio loop. Today the GUI uses `BridgeAsyncThread` (one QThread per bridge). Fleet needs up to 8.

### Options considered

| Option | Summary |
|--------|---------|
| **A. N × QThread in one process** | Reuse `BridgeAsyncThread`; supervisor on Qt main thread |
| **B. N × subprocess** | `bridge_worker.py` or frozen child; IPC for stats |
| **C. Contract-first hybrid** | `StreamWorker` interface; thread v1, process v2 |

### Decision

**C — Contract-first; ship A in v1.**

### Rationale

- Constitution already standardizes **asyncio on background thread, Qt on main** — Option A is proven.
- Operator trust requires **one app, one tray, one config file** — Option A is lightest RAM (~one Python + Qt).
- USB serial driver hangs are rare but real; **Option B** is the v2 hardening path without rewriting Fleet UI.
- Defining `StreamWorker` now prevents Fleet tab from importing `BridgeAsyncThread` directly (constitution I).

### Consequences

- Plan MUST introduce `core/fleet/` (or `fleet/`) with supervisor + `ThreadStreamWorker`.
- Tests MUST mock `StreamWorker` for UI and validation layers.
- v2 task: `ProcessStreamWorker` implementing same contract + IPC smoke test.

---

## Decision 2: Network pattern default

### Context

Fleet runs on **Survey PC** with wired sensors. Operator unsure between global UDP listen vs client.

### Decision

**Per-stream `net_mode` — no fleet-wide default.** Reuse `NetMode` from `bridge_core` per row.

### Rationale

- TSS1 → Hypack on **another** PC may be UDP **client** to `192.168.x.x`.
- Applanix → logging tool on **same** LAN may be UDP **listen** on survey PC.
- Mixing both on one boat is normal; global default would be wrong half the time.

### Operator guidance (copy for UI hints)

| Situation | Suggested mode |
|-----------|----------------|
| Tool on another PC connects **to** survey PC | UDP listen (unique port per stream) |
| Survey PC pushes **to** known INS/logger IP | UDP remote / TCP client |
| Consumer on same PC | UDP listen on `127.0.0.1` or documented localhost port |

---

## Decision 3: Primary stream vs thin pipes

### Decision

**Option 2** — at most one `primary` stream; only Primary uses Survey HUD / survey-grade hooks.

### Rationale

- Matches real boat: one GNSS/motion reference (Applanix-class), several byte pipes (SVP, AML, aux).
- Avoids 8× HUD / map cost and UI clutter.
- Thin rows stay **data not stats** — last RX, state, drops only.

### Consequences

- `BridgeLogicMixin` / HUD must resolve **active bridge** from supervisor when fleet mode has a primary.
- Single-bridge Modern Control path unchanged when fleet unused or no primary running.

---

## Decision 4: Monitoring scope v1

### Decision

**Per-stream only.** No CPU/RAM/disk widget on Fleet tab.

### Rationale

Operator quote: *“we want data not stats”* — meaning sensor **data flow**, not host telemetry.

### Per-stream signals (minimum)

| Signal | Purpose |
|--------|---------|
| State | stopped / starting / running / error |
| Last RX age | silent cable detection |
| Drop count | backpressure trust |
| Rate hint | Hz (NMEA) or B/s (raw) — coalesced 1–2 Hz UI refresh |

---

## Decision 5: Single-instance lock

### Decision

**Keep lock** on supervisor process; fleet replaces multi-GUI workaround.

### Rationale

Lock was added for zombie web/discovery/tray on layout switch — still valid.
Parallel Cube MAVLink + GPS UART (CHANGELOG) is satisfied by **two fleet rows**, not two exes.

---

## Decision 6: UI placement

### Decision

**Fleet tab in Modern** only for v1.

### Rationale

Operator confirmed; Modern is default layout; avoids 3× UI parity cost (Standard/Field/Modern).

---

## Open questions for `/speckit-plan` (non-blocking)

1. Web API: disable per-stream servers and expose fleet status on existing port, or defer web entirely in fleet v1?
2. Discovery service: single scan shared across fleet COM rows, or unchanged global behavior?
3. Local backup `.raw`: per-stream subfolder naming convention (`logs/{fleet_id}/{stream_id}/`).

---

## References

- `bridge_core.py` — `SerialNetBridge`, `BridgeAsyncThread`
- `bridge_headless.py` — headless single-bridge pattern (worker seed)
- `bridge_gui.py` — `QLockFile` single instance
- CHANGELOG v1.35.x — Cube GPS UART “second instance” preset intent
