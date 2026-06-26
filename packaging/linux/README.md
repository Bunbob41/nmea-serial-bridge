# Linux headless packaging

Operator guide: **`docs/LINUX_HEADLESS.md`**

## Quick start

```bash
tar xzf serial-link-vX.Y.Z-linux-headless.tar.gz
cd serial-link-vX.Y.Z-linux-headless
./packaging/linux/install.sh
cp packaging/linux/bridge.json.example ~/.config/serial-link/bridge.json
mkdir -p ~/.config/serial-link
# edit serial port + set web.lan_bind/token for tailnet access
./packaging/linux/run-headless.sh
```

## Files

| File | Purpose |
|------|---------|
| `install.sh` | Create `.venv`, install headless deps |
| `run-headless.sh` | Activate venv, load `CONFIG_FILE`, run headless |
| `build-release-tar.sh` | Build release tarball |
| `bridge.json.example` | Site config template |
| `headless.env.example` | systemd `EnvironmentFile` template |
| `serial-link-headless.service` | Example user systemd unit |

## Config precedence

1. CLI flags (when explicitly passed)
2. `SERIAL_LINK_*` environment variables
3. Site config JSON (`--config`, `CONFIG_FILE`, or auto-discovered paths)
4. Built-in defaults

Bridge **does not start** until you click **Start** in the dashboard unless `bridge.autostart` / `--start-bridge` is set.
