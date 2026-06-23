# Feature Specification: Linux Headless Bridge + Web Dashboard

**Feature Branch**: `011-linux-headless-bridge`

**Created**: 2026-06-23

**Status**: Phase 1 (scaffold)

**Input**: Ship the **fastest credible Linux product**: headless UDP/TCP ↔ serial bridge with the existing web dashboard for config, start/stop, and stats — downloadable from GitHub Releases. Lighter than the Windows PySide6 desktop app; not full Modern UI parity.

**Builds on**: Hybrid UI Web API ([`specs/005-hybrid-ui-webui/spec.md`](../005-hybrid-ui-webui/spec.md)), Phase B dashboard ([`specs/006-phase-b-dashboard/spec.md`](../006-phase-b-dashboard/spec.md)), baseline bridge ([`specs/001-baseline-spec/spec.md`](../001-baseline-spec/spec.md)).

**Baseline version at spec time**: v1.41.8 (`version.py`).

---

## Purpose

Survey and edge PCs on Linux need the same **Ethernet ↔ serial** bridge as Windows without porting the full Qt desktop. Phase 1 delivers:

1. A **headless Python entry point** (`serial_link_headless.py`) running `bridge_core` + FastAPI/uvicorn web dashboard.
2. **Operator docs** and **systemd** examples for field install.
3. A **GitHub Release artifact** (source tar.gz + install scripts) operators can download and run in minutes.

---

## Scope Boundaries

| In scope (Phase 1) | Out of scope |
|--------------------|--------------|
| UDP listen (primary), UDP remote, TCP client/server via web + CLI | PySide6 Modern / Field / Fleet GUI on Linux |
| NMEA passthrough, strict, raw binary modes | Kernel virtual COM, passive kernel sniff |
| Web dashboard at `GET /` (GridStack), `/status`, `/config`, start/stop | Full desktop Connect Hub / Fleet multi-stream |
| Serial discovery via `pyserial` (`/dev/ttyUSB*`, `/dev/ttyACM*`) | Windows-only port unlock heuristics parity |
| systemd user service example | Code signing, .deb/.rpm packaging |
| GitHub Release `serial-link-vX.Y.Z-linux-headless.tar.gz` | PyInstaller Linux one-folder (Phase 2 candidate) |
| Single-node deployment | Fleet supervisor / multi-stream orchestration |

---

## Target Platform

**Recommended**: **Ubuntu 22.04 LTS** and **24.04 LTS** (and Debian-derived distros with `python3.10+`).

**Rationale**:

- Long support window, common on survey edge boxes and cloud dev VMs.
- `python3-venv`, `pip`, and `systemd` are standard.
- USB serial (`usbserial`, `cdc_acm`) and `dialout` group are well documented.
- CI can validate on `ubuntu-latest` (24.04 family) without custom images.

Other glibc-based distros (Debian 12, Linux Mint) should work with the same install path; musl/Alpine is **best-effort** only in Phase 1.

---

## Serial on Linux

| Pattern | Typical device | Notes |
|---------|----------------|-------|
| USB-UART adapter | `/dev/ttyUSB0` | FTDI, Prolific, CH340 |
| USB CDC (GNSS, Arduino-class) | `/dev/ttyACM0` | Appears when cable enumerates |
| Onboard UART | `/dev/ttyS*` | Rare for survey USB workflows |

**Permissions**: user must be in the **`dialout`** group (or run as root — discouraged):

```bash
sudo usermod -aG dialout "$USER"
# log out and back in
```

**Locking**: only one process may open a serial device. Headless exposes COM lock probe via web API (`/ports/probe`) using the same `port_release` helpers as desktop.

---

## Deployment Model

| Mode | Use |
|------|-----|
| **Dev / bench** | `python serial_link_headless.py --serial /dev/ttyUSB0` |
| **Installed** | `packaging/linux/install.sh` → venv → `run-headless.sh` |
| **Field service** | `systemd` user unit `serial-link-headless.service` (Restart=on-failure) |

Bridge asyncio runs in a **background thread**; web server runs in **uvicorn thread** (same architecture as desktop Web API). No Qt main loop.

---

## Fleet

**Phase 1 decision: NO fleet.** Single bridge session per process. Multi-stream Fleet ([`specs/011-fleet-multi-stream/`](../011-fleet-multi-stream/spec.md)) remains Windows/desktop until a headless supervisor is specified in Phase 2+.

---

## GitHub Delivery (Phase 1)

**Chosen format**: **`serial-link-vX.Y.Z-linux-headless.tar.gz`**

Contents:

- Full application source (excluding `.git`, `dist/`, `.venv`)
- `requirements-linux-headless.txt` (no PySide6)
- `packaging/linux/install.sh`, `run-headless.sh`, example systemd unit
- `docs/LINUX_HEADLESS.md`

Install path on target host:

```bash
tar xzf serial-link-vX.Y.Z-linux-headless.tar.gz
cd serial-link-vX.Y.Z-linux-headless   # or repo folder name
./packaging/linux/install.sh
./packaging/linux/run-headless.sh --serial /dev/ttyUSB0
```

**Not Phase 1**: PyInstaller one-folder binary (larger build matrix), `pip install` from PyPI.

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| **FR-501** | Provide `serial_link_headless.py` entry point accepting serial path, baud, network mode, NMEA mode, web bind host/port, optional LAN bind + API token. |
| **FR-502** | Run `SerialNetBridge` from `bridge_core.py` without Qt GUI; bridge protocol logic remains in `bridge_core` / `nmea_codec.py`. |
| **FR-503** | Serve existing web dashboard and REST API (`web_api.py`, `web/static/`) on default port **8765**. |
| **FR-504** | Web client can **read status**, **read/patch config**, **start/stop** bridge with validation equivalent to desktop (stop before COM/network change). |
| **FR-505** | List serial devices on Linux via `serial.tools.list_ports` in discovery API. |
| **FR-506** | Document `dialout` group, systemd unit, firewall note for `--lan-bind`, and dashboard URL in `docs/LINUX_HEADLESS.md`. |
| **FR-507** | Ship `requirements-linux-headless.txt` without PySide6; Windows desktop build unchanged. |
| **FR-508** | CI job on `ubuntu-latest` runs headless unit tests and builds release tar.gz artifact. |
| **FR-509** | GitHub Release may attach `serial-link-vX.Y.Z-linux-headless.tar.gz` alongside Windows zip. |

---

## Acceptance Criteria (Phase 1)

1. On Ubuntu 22.04/24.04 with Python 3.10+: `pip install -r requirements-linux-headless.txt` succeeds without PySide6.
2. `python serial_link_headless.py` starts web server; `GET /health` returns `ok: true`.
3. `GET /` serves dashboard HTML; `GET /status` shows configured serial path and `running: false` before Start.
4. With a USB serial device and `dialout` membership, web **Start** opens the port and UDP listen accepts datagrams (bench UDP sender).
5. `python -m unittest tests.test_serial_link_headless` passes on Linux CI.
6. `packaging/linux/build-release-tar.sh` produces a versioned tar.gz; `install.sh` creates a working venv.
7. Windows `verify_all.py` / desktop GUI regression unchanged (BridgeAsyncThread moved to `bridge_qt_thread.py` only).

---

## Non-Goals / Deferred (Phase 2+)

- PyInstaller Linux binary, `.deb` package, cloud-init images
- Fleet multi-stream headless supervisor
- NTRIP UI, TCP sink mirror, serial mirror from web (desktop-only today)
- Tailscale detect button parity (passive discovery only on Linux)
- AppArmor/SELinux profiles

---

## Traceability

| Artifact | Role |
|----------|------|
| `serial_link_headless.py` | CLI entry |
| `headless_facade.py` | Web API façade (no Qt) |
| `headless_bridge_runner.py` | Asyncio bridge thread |
| `web_api.py` | Reused REST + static dashboard |
| `packaging/linux/*` | Install / systemd / release tar |
| `docs/LINUX_HEADLESS.md` | Operator quickstart |
