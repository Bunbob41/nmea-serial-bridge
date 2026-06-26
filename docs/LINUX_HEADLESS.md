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
cd serial-link-vX.Y.Z-linux-headless   # versioned folder from the tarball
./packaging/linux/install.sh
```

Or clone the repo to any path (e.g. `~/nmea-serial-bridge`) and run `install.sh` from there.

This creates `.venv/` and installs `requirements-linux-headless.txt` (no PySide6).

---

## Site config (recommended — Phase A)

Edit once, restart without long CLI flags. Copy the example:

```bash
mkdir -p ~/.config/serial-link
cp packaging/linux/bridge.json.example ~/.config/serial-link/bridge.json
```

**Local dashboard only** (same machine, no token):

```json
"web": {
  "host": "127.0.0.1",
  "port": 8765,
  "lan_bind": false
}
```

**Tailnet / remote PC** (open dashboard from another machine):

```json
"web": {
  "host": "0.0.0.0",
  "port": 8765,
  "lan_bind": true,
  "token": "pick-a-long-random-secret"
}
```

If `lan_bind` is true and `token` is omitted, a token is **auto-generated and printed** at startup.

**Bridge stays stopped** until you click **Start** in the dashboard unless `"bridge": { "autostart": true }` or `--start-bridge`.

Config search order: `--config` → `CONFIG_FILE` / `SERIAL_LINK_CONFIG` env → `~/.config/serial-link/bridge.json` → `/etc/serial-link/bridge.json`. CLI flags override file values when explicitly passed.

See `packaging/linux/README.md` and `headless.env.example` for systemd.

---

## Dashboard setup (Phase B — v1.43.0+)

When the bridge is **stopped**, the web dashboard shows a setup banner: pick serial port and UDP/TCP listen settings, click **Save configuration**, then **Start**.

To write those values back to `bridge.json` for the next reboot:

1. Stop the bridge if it is running.
2. Adjust settings in the dashboard.
3. Click **Save boot defaults** (headless only, when the config file is writable).

The dashboard reads `/meta` for `headless`, `config_path`, and `config_writable`. On headless Linux the API token is **not** in Tools → Phone — it is printed at service start (`journalctl --user -u serial-link-headless`) or in the terminal when you run interactively.

From a **Tailscale PC**, use `web.lan_bind: true` and the token from startup; localhost access does not require a token.

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

## systemd user service

Copy templates and set **`INSTALL_DIR`** to your extract path:

```bash
mkdir -p ~/.config/systemd/user ~/.config/serial-link
cp packaging/linux/bridge.json.example ~/.config/serial-link/bridge.json
cp packaging/linux/headless.env.example ~/.config/serial-link/headless.env
# Edit bridge.json (serial, tailnet token) and headless.env (INSTALL_DIR=/path/to/serial-link-vX.Y.Z-linux-headless)
cp packaging/linux/serial-link-headless.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now serial-link-headless.service
journalctl --user -u serial-link-headless -f
```

Startup prints dashboard URLs, API token, and **Bridge: STOPPED** until you Start from the web UI.

---

## Run (interactive)

```bash
./packaging/linux/run-headless.sh --serial /dev/ttyUSB0 --udp-port 10110
```

Open the dashboard: **http://127.0.0.1:8765/**

**No token on localhost** — default headless bind is `127.0.0.1` only; the dashboard works without an API token. You only need `--token` when using `--lan-bind` for phone/LAN access (the token is printed in the terminal at startup).

| Flag | Meaning |
|------|---------|
| `--serial` / `--com` | Serial device (default `/dev/ttyUSB0`) |
| `--baud` | Baud rate (default `115200`) |
| `--udp-host` | UDP listen bind (default `0.0.0.0`) |
| `--udp-port` | UDP listen port (default `10110`) |
| `--nmea-mode` | `passthrough`, `strict`, or `raw` |
| `--network-mode` | `udp_listen`, `udp_remote`, `tcp_client`, `tcp_server` |
| `--web-port` | Dashboard port (default `8765`) |
| `--config` | Site config JSON (see above) |
| `--lan-bind` | Remote dashboard on all interfaces (token auto-generated if omitted) |
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

## LAN / Tailnet access

Prefer **site config** (`web.lan_bind: true`) or CLI:

```bash
./packaging/linux/run-headless.sh --config ~/.config/serial-link/bridge.json
```

Startup prints **Tailnet/LAN URLs**, **API token**, and a **setup link** (`#bridge-token=…`). Open that URL from your tailnet PC, review settings while **Stopped**, then **Start**.

Allow the dashboard port through firewall if enabled: `sudo ufw allow 8765/tcp`.

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
