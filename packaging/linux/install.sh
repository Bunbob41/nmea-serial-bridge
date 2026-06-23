#!/usr/bin/env bash
# Create a venv and install Linux headless dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found; install Python 3.10+." >&2
  exit 1
fi
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-linux-headless.txt
echo ""
echo "Installed. Run: ./packaging/linux/run-headless.sh --serial /dev/ttyUSB0"
echo "Docs: docs/LINUX_HEADLESS.md"
