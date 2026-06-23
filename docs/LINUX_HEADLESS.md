# Linux Headless Serial Link

Run **Serial Link** on Linux without the Windows desktop GUI: a background **UDP/TCP ↔ serial** bridge plus the same **web dashboard** used on Windows (Tools → Phone).

**Entry point**: `serial_link_headless.py`  
**Default dashboard**: [http://127.0.0.1:8765/](http://127.0.0.1:8765/)

Download the Linux tarball from [GitHub Releases](https://github.com/Bunbob41/nmea-serial-bridge/releases) (`serial-link-vX.Y.Z-linux-headless.tar.gz`) or clone this repo.

---

## Requirements

- **Ubuntu 22.04 / 24.04 LTS** (or similar glibc distro)
- **Python 3.10+**
- USB serial drivers (usually built-in: `ftdi_sio`, `ch341`, `cdc_acm`)
- User in group **`dialout`** for `/dev/ttyUSB*` and `/dev/ttyACM*`

---

## Quick install

```bash
tar xzf serial-link-vX.Y.Z-linux-headless.tar.gz
cd nmea-serial-bridge   # or extracted folder name
./packaging/linux/install.sh
```

This creates `.venv/` and installs `requirements-linux-headless.txt` (no PySide6).

---

## Serial permissions

```bash
# Add your user to the dialout group
sudo usermod -aG dialout "$USER"
# Log out and back in, then verify:
groups
ls -l /dev/ttyUSB0 /dev/ttyACM0
```

If Start fails with “Permission denied” or “could not open port”, fix group membership before running as root.

---

## Run (interactive)

```bash
./packaging/linux/run-headless.sh --serial /dev/ttyUSB0 --udp-port 10110
```

Open the dashboard: **http://127.0.0.1:8765/**

| Flag | Meaning |
|------|---------|
| `--serial` / `--com` | Serial device (default `/dev/ttyUSB0`) |
| `--baud` | Baud rate (default `115200`) |
| `--udp-host` | UDP listen bind (default `0.0.0.0`) |
| `--udp-port` | UDP listen port (default `10110`) |
| `--nmea-mode` | `passthrough`, `strict`, or `raw` |
| `--network-mode` | `udp_listen`, `udp_remote`, `tcp_client`, `tcp_server` |
| `--web-port` | Dashboard port (default `8765`) |
| `--lan-bind` | Listen on all interfaces (use with `--token`) |
| `--start-bridge` | Start bridging immediately (default: use dashboard Start) |

Example — INS UDP to GNSS serial:

```bash
./packaging/linux/run-headless.sh \
  --serial /dev/ttyUSB0 \
  --baud 115200 \
  --udp-port 10110 \
  --nmea-mode passthrough
```

---

## systemd user service

Copy and edit the example unit:

```bash
mkdir -p ~/.config/systemd/user
cp packaging/linux/serial-link-headless.service ~/.config/systemd/user/
# Edit ExecStart serial path and ports
systemctl --user daemon-reload
systemctl --user enable --now serial-link-headless.service
systemctl --user status serial-link-headless.service
```

Logs: `journalctl --user -u serial-link-headless -f`

---

## LAN / phone access

By default the dashboard binds to **localhost only**. To open from a phone on the same Wi‑Fi:

```bash
./packaging/linux/run-headless.sh \
  --serial /dev/ttyUSB0 \
  --lan-bind \
  --token 'choose-a-long-random-token'
```

Then open `http://<this-pc-lan-ip>:8765/` and paste the token when prompted.

Allow the port through the host firewall if enabled, e.g. `sudo ufw allow 8765/tcp`.

---

## API (same as Windows)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness |
| `GET /status` | Running, Hz, drops, GNSS summary |
| `GET /config` | Current configuration |
| `PATCH /config` | Update config (stop bridge first) |
| `POST /bridge/start` | Start |
| `POST /bridge/stop` | Stop |
| `GET /discovery` | Serial ports + network cards |

See `specs/005-hybrid-ui-webui/quickstart.md` for details.

---

## What is not included on Linux

- PySide6 **Modern / Field / Fleet** desktop UI
- Windows COM unlock / com0com workflows
- Frozen `.exe` (use Python venv or Phase 2 binary if shipped later)
- Fleet multi-stream supervisor (single bridge per process in Phase 1)

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Dashboard unreachable | `ss -tlnp \| grep 8765`; firewall |
| Cannot open `/dev/ttyUSB0` | `dialout` group, cable, `dmesg \| tail` |
| UDP no traffic | INS sends to **this PC’s IP:port**; bridge **listens** |
| Port busy | Only one process per serial device; `fuser /dev/ttyUSB0` |

For full operator workflows (NMEA modes, boat vs bench), see [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — desktop-focused but protocol behavior is the same.
