#!/usr/bin/env bash
# Create a venv and install Linux headless dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$(dirname "$0")/venv.sh"
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found; install Python 3.10+ (e.g. apt install python3.12-venv)." >&2
  exit 1
fi
VENV_DIR="$(resolve_serial_link_venv "$ROOT")"
if [[ "$ROOT" == /mnt/* && -d "$ROOT/.venv" ]]; then
  echo "Removing broken repo .venv on /mnt/c (use Linux-side venv instead)." >&2
  rm -rf "$ROOT/.venv"
fi
if [[ ! -d "$VENV_DIR" ]]; then
  mkdir -p "$(dirname "$VENV_DIR")"
  "$PY" -m venv "$VENV_DIR"
fi
printf '%s\n' "$VENV_DIR" >"$ROOT/.serial-link-venv"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-linux-headless.txt
echo ""
echo "Installed into: $VENV_DIR"
if [[ "$VENV_DIR" != "$ROOT/.venv" ]]; then
  echo "(WSL /mnt/c: venv lives on Linux FS — see .serial-link-venv)"
fi
echo ""
echo "Next:"
echo "  mkdir -p ~/.config/serial-link"
echo "  cp packaging/linux/bridge.json.example ~/.config/serial-link/bridge.json"
echo "  # edit serial port; set web.lan_bind + web.token for tailnet dashboard"
echo "  ./packaging/linux/run-headless.sh"
echo "Docs: docs/LINUX_HEADLESS.md"
