# nmea-serial-bridge

Windows desktop app that **bidirectionally bridges** NMEA-style (text) traffic between **UDP/TCP** and a **serial COM port**. Built for survey / USV-style workflows: feed a simulator or network GNSS/INS stream to a physical or virtual COM port (for example toward an autopilot UART path), and return serial traffic to the network.

**Stack:** Python 3.10+, [PySide6](https://doc.qt.io/qtforpython/), [pyserial-asyncio](https://pyserial-asyncio.readthedocs.io/).

## Features

- **Network modes (pick one per session)**  
  - **UDP listen** — bind a local host/port; replies to serial go to the **last UDP sender** (good for bench simulators).  
  - **UDP remote** — fixed peer; datagrams go to that host/port.  
  - **TCP server** — listen for inbound connections (**one active client**; a new connection replaces the previous reader).  
  - **TCP client** — outbound connect with automatic **reconnect** (1 s backoff) while the bridge is running.

- **Serial** — COM pick list, baud, refresh ports.

- **Queues & backpressure** — bounded queues between network and serial; **drop counters** if one side is faster than the other (drops are logged, not silent).

- **Live UI log** — throttled/batched updates and a capped document size so the window stays usable under load.

- **Optional rotating file log** — tab *Log / QA*: enable file logging, set path, browse. Lines include **PC time**, **last parsed GPS UTC** from **RMC / ZDA** (when present in the stream), **direction**, and payload preview.

- **Send tab** — inject lines (CR/LF normalized to `\r\n`); send toward **serial**, **network**, or **both**.

## Requirements

- **Windows** (primary target).  
- **Python 3.10+**  
- USB/RS‑232 drivers for your COM device as usual.

## Install

From a clone of this repo:

```powershell
cd nmea-serial-bridge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python bridge_gui.py
```

1. Open the **Connection** tab: choose **COM**, **baud**, and **network mode** + addresses.  
2. Optionally configure **Log / QA** (rotating file log).  
3. **Start bridge** — watch the right-hand log and the **drop / queue** stats line.  
4. Use **Send** for manual injections while running.  
5. **Stop bridge** when finished (file log is closed cleanly).

## Notes

- **Virtual COM** (e.g. com0com) is fine for testing; the app only sees a COM name Windows exposes.  
- **Asyncio + Qt** uses a small timer-driven event-loop pump (not `qasync`); adequate for this prototype, but if you hit edge cases under extreme rates, consider migrating to `qasync` later.  
- This tool forwards **bytes**; it does **not** replace proper **autopilot failsafes**, electrical **RS‑232 ↔ TTL** level shifting, or mission **QA** procedures — it is a **transport bridge** with logging hooks.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

## Disclaimer

Use at your own risk on operational hardware. Validate behavior on a bench before depending on it for navigation or survey positioning.
