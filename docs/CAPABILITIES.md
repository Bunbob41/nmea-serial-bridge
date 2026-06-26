# System Capabilities & Architecture

**Product:** Serial Link (NMEA Serial Bridge) | **Target Version:** 1.43.0

Serial Link is a real-time, bidirectional bridge between physical serial endpoints (COM / TTY) and IP network transports. It features built-in NMEA validation, extensive observability, and dual execution modes (a full-featured Desktop GUI and a lightweight Headless Linux service).

## 1. Hardware & I/O Support

- **Universal Serial Transport:** Native support for RS232 adapters, USB-UART devices (FTDI, CH340, CDC-ACM), and standard GNSS receivers via asynchronous read/write chunks.
- **Windows COM Integration:** Advanced desktop support including COM exclusivity detection, intelligent auto-reconnect via Hardware ID (HWID) matching during USB re-enumeration, and native integration with virtual null-modem pairs like `com0com`.
- **Linux Hardware Endpoints:** Headless targeting for Ubuntu distros. Seamlessly binds to `/dev/ttyUSB0`, `/dev/ttyACM*`, and other kernel-exposed TTY devices.
- **Virtual Mirror Ports:** Software-level serial mirroring allows duplication of egress traffic to additional virtual COM ports for passive monitoring without requiring a second bridge instance.
- **Multi-Port Fleet (Desktop):** Run up to 8 parallel, isolated bridge workers simultaneously, each managing its own dedicated COM port and network routing mode.

## 2. Networking & Routing

- **UDP Listen & Fan-out:** Binds a datagram socket (default `0.0.0.0:10110`). Supports dynamic fan-out, broadcasting serial ingress to every registered peer on the session.
- **TCP / UDP Client & Server:** Flexible topologies including outbound UDP remote locking, TCP Server (active client replacement), and TCP Client with configurable auto-reconnect loops.
- **TCP Sink Mirror:** An independent, read-only TCP server (default `0.0.0.0:10111`) that taps and broadcasts serial-to-network egress for up to 8 downstream consumers.
- **NTRIP Correction Ingress:** Built-in NTRIP v1 client over TCP. Injects RTCM chunks directly into the serial port, bypassing standard NMEA assembly to ensure clean correction delivery.
- **LAN Discovery:** Automated network scanner builds snapshots of local NICs, active UDP listen readiness, and LAN host hints.

## 3. Data Processing & Validation

- **Passthrough Mode:** Buffers and splits incoming bytes on standard carriage returns, forwarding complete lines without checksum enforcement.
- **Strict Mode:** Enforces XOR checksum validation (`*HH`), rejects malformed/empty lines, extracts embedded sentences from garbage-prefixed buffers, and supports strict filtering against standard GNSS catalogs (GGA, RMC, ZDA, VTG, etc.).
- **Raw Binary Mode:** Bypasses line assembly for MAVLink, RTCM, and other non-NMEA payloads, allowing bytes to flow cleanly in both directions.
- **Traffic Management:** Dual independent `asyncio.Queue` buffers (capacity 512). Enforces backpressure, drops stale packets during overflow, and throttles observability metrics to prevent CPU bottlenecking.

## 4. Execution Modes & Control Planes

### Desktop GUI (PySide6)

- PyInstaller frozen deployments for Windows (~650 MB) bundling Qt, fonts, and static assets.
- Multiple operator layouts (Modern, Field, Log-First).
- Features include: System tray integration, preflight checklists, rotating file logs, black-box session backups, GridStack dashboarding, and a dedicated Survey HUD popout.

### Headless Linux Service (`serial_link_headless.py`)

- Lightweight, GUI-free runner designed for single-board computers and embedded Linux setups.
- Configured via CLI flags, environment variables, or site JSON (`~/.config/serial-link/bridge.json`, `/etc/serial-link/bridge.json`).
- Ships with `systemd` user unit templates and deployment scripts.
- v1.43.0+: dashboard configure-before-start and **Save boot defaults** (`POST /config/persist`).

### Web API & Dashboard

- Embedded ASGI web server (FastAPI/Uvicorn) delivering a GridStack/Leaflet.js dashboard.
- Fully accessible via standard REST endpoints (GET `/status`, POST `/bridge/start`, etc.).
- Secured via API tokens (`X-Bridge-Token`) with built-in QR code generation for rapid mobile device pairing on the bench.

## 5. Core Tech Stack

| Layer | Libraries |
|-------|-----------|
| Runtime | Python 3.10+ (`asyncio`) |
| Serial | `pyserial`, `pyserial-asyncio` |
| Desktop UI | PySide6 (Qt 6.5+) |
| Web | FastAPI, Uvicorn, GridStack, Leaflet |

## Related docs

- [Operator guide](OPERATOR_GUIDE.md) — field workflows
- [Linux headless](LINUX_HEADLESS.md) — Pi / systemd / tailnet
- [README](../README.md) — install and run
