# Implementation Plan: Linux Headless Bridge (Phase 1)

**Spec**: [`spec.md`](spec.md)  
**Target version**: v1.41.9+ (patch scaffold)

---

## Phase 1 — Scaffold (this session)

| Step | Task | Status |
|------|------|--------|
| 1 | Extract `web_facade_types.py`; move `BridgeAsyncThread` → `bridge_qt_thread.py` (drop PySide6 from `bridge_core` import path) | Done |
| 2 | `headless_bridge_runner.py` + `headless_facade.py` | Done |
| 3 | `serial_link_headless.py` CLI | Done |
| 4 | `requirements-linux-headless.txt`, `docs/LINUX_HEADLESS.md` | Done |
| 5 | `packaging/linux/` scripts + systemd unit | Done |
| 6 | `tests/test_serial_link_headless.py` | Done |
| 7 | CI `linux-headless` job + tar build | Done |
| 8 | Version + CHANGELOG | Done |

---

## Phase 2 — Hardening (days, not weeks)

1. **Bench script** — `bench_linux_udp.sh` or extend `bench_network_automation.py` for CI smoke without hardware (mock serial optional).
2. **Release automation** — attach Linux tar from `release.ps1` companion script or GitHub Actions `workflow_dispatch` release job.
3. **PyInstaller Linux** — evaluate one-folder build size vs tar.gz; only if operators reject venv.
4. **Web parity gaps** — fan-out toggle, TCP sink, inject tab via API if needed for Cube workflows.
5. **Firewall helper** — `ufw allow` snippet in docs when `--lan-bind` is used.

---

## Phase 3 — Fleet / edge (optional)

- Headless Fleet supervisor (reuse `core/fleet/` with `HeadlessBridgeRunner` instead of `BridgeAsyncThread`).
- Multi-instance systemd template (`serial-link@.service`).

---

## Files Touched (Phase 1)

| File | Change |
|------|--------|
| `web_facade_types.py` | **New** — shared Web DTOs |
| `bridge_qt_thread.py` | **New** — Qt bridge worker |
| `bridge_core.py` | Remove top-level PySide6 + `BridgeAsyncThread` |
| `ui/mixin.py`, `core/fleet/stream_worker.py` | Import `BridgeAsyncThread` from `bridge_qt_thread` |
| `app_facade.py` | Import DTOs from `web_facade_types` |
| `headless_bridge_runner.py` | **New** |
| `headless_facade.py` | **New** |
| `serial_link_headless.py` | **New** |
| `requirements-linux-headless.txt` | **New** |
| `docs/LINUX_HEADLESS.md` | **New** |
| `packaging/linux/*` | **New** |
| `tests/test_serial_link_headless.py` | **New** |
| `.github/workflows/ci.yml` | Linux job |
| `version.py`, `CHANGELOG.md` | Patch bump |

**Unchanged**: `bridge_headless.py` remains the short **bench self-test** (UDP inject + teardown), not the long-running product entry.

---

## Manual Release Steps (if CI artifact not uploaded to GitHub Release)

```bash
# On Ubuntu or WSL
./packaging/linux/build-release-tar.sh
# Upload dist/serial-link-vX.Y.Z-linux-headless.tar.gz via gh release upload
gh release upload vX.Y.Z dist/serial-link-vX.Y.Z-linux-headless.tar.gz --clobber
```

Windows release (`.\release.ps1`) is unchanged.

---

## Test Plan

| Check | Command |
|-------|---------|
| Headless unit tests | `python -m unittest tests.test_serial_link_headless` |
| Web API regression | `python -m unittest tests.test_web_api` |
| Windows compile | `python -m py_compile bridge_core.py bridge_qt_thread.py` |
| Full local (Windows) | `python verify_all.py` |
| Linux CI | GitHub Actions `linux-headless` job |

---

## Open Decisions (user)

| Topic | Phase 1 choice | Alternatives |
|-------|----------------|--------------|
| Distro pin | Ubuntu 22.04/24.04 documented | RHEL, Alpine |
| Fleet | Deferred | Headless multi-stream in Phase 3 |
| Binary vs tar.gz | **tar.gz + venv** | PyInstaller Linux |
| Release attach | CI artifact + manual `gh upload` | Fully automated in `release.ps1` |
