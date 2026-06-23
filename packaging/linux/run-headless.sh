#!/usr/bin/env bash
# Run Serial Link headless from the repo venv.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "Missing .venv — run ./packaging/linux/install.sh first." >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
exec python serial_link_headless.py "$@"
